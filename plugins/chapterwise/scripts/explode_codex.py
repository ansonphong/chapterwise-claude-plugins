#!/usr/bin/env python3
"""
Codex Exploder Service - Extract and Modularize Codex Children

This service extracts direct children from a codex file based on node type,
saves each as a standalone codex file, and replaces them with include
directives in the parent file.

This enables:
- True modularity: each node in its own file
- Team collaboration: multiple people working on different files
- Git-friendly: smaller files, better conflict resolution
- Organized structure: nodes grouped by type

Command-line usage:
    python explode_codex.py <input_file> [options]

Examples:
    # Extract all characters and locations
    python explode_codex.py story.codex.yaml --types character,location

    # Custom output pattern
    python explode_codex.py story.codex.yaml --types character --output-pattern "./nodes/{type}/{name}.codex.yaml"

    # Dry run to preview
    python explode_codex.py story.codex.yaml --types character --dry-run

    # Disable auto-fix
    python explode_codex.py story.codex.yaml --types character --no-auto-fix
"""

import os
import sys
import yaml
import json
import re
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

# Codex format version (single source of truth).
try:
    from codex_version import CURRENT_FORMAT_VERSION
except ImportError:  # standalone execution outside the scripts directory
    CURRENT_FORMAT_VERSION = '1.3'

# Setup path for plugin execution - import auto_fixer from same directory
script_dir = Path(__file__).resolve().parent

# Add scripts directory to path for auto_fixer import
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

# Import auto-fixer for post-processing
try:
    from auto_fixer import CodexAutoFixer
except ImportError:
    # Fallback: try importing via importlib
    import importlib.util
    auto_fixer_path = script_dir / 'auto_fixer.py'
    if auto_fixer_path.exists():
        spec = importlib.util.spec_from_file_location("auto_fixer", auto_fixer_path)
        auto_fixer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auto_fixer_module)
        CodexAutoFixer = auto_fixer_module.CodexAutoFixer
    else:
        # Ultimate fallback - no auto-fixing available
        CodexAutoFixer = None


def get_yaml_dumper_with_pipe_format():
    """Create a custom YAML dumper that uses pipe syntax for long strings."""
    class CustomDumper(yaml.SafeDumper):
        pass

    def str_representer(dumper, data):
        if isinstance(data, str) and (len(data) > 80 or '\n' in data):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    CustomDumper.add_representer(str, str_representer)
    return CustomDumper


logger = logging.getLogger(__name__)


class CodexExploder:
    """
    Service to extract direct children from codex files into separate files
    and replace them with include directives.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.extracted_files = []
        self.extraction_map = {}
        self.errors = []

    def explode(
        self,
        input_path: str,
        types: Optional[List[str]] = None,
        output_pattern: str = "./{type}s/{name}.codex.yaml",
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract direct children from a codex file and save them as separate files.

        Args:
            input_path: Path to the input codex file
            types: List of node types to extract (None = all direct children)
            output_pattern: Pattern for output file paths (supports {type}, {name}, {id}, {index})
            options: Additional options:
                - dry_run: bool - Preview without making changes
                - backup: bool - Create backup of original file (default: True)
                - format: str - Output format 'yaml' or 'json' (default: 'yaml')
                - verbose: bool - Detailed logging
                - auto_fix: bool - Run auto_fixer on extracted files (default: True)
                - force: bool - Overwrite existing files

        Returns:
            Dict with extraction results:
                - success: bool
                - extracted_count: int
                - extracted_files: List[str]
                - extraction_map: Dict[str, str] (child_id -> file_path)
                - auto_fix_results: Dict (if auto_fix enabled)
                - errors: List[str]
        """
        options = options or {}
        dry_run = options.get('dry_run', False)
        backup = options.get('backup', True)
        output_format = options.get('format', 'yaml')
        verbose = options.get('verbose', False)
        auto_fix = options.get('auto_fix', True)
        force = options.get('force', False)

        # Reset state
        self.extracted_files = []
        self.extraction_map = {}
        self.errors = []

        # Configure logging
        if verbose:
            self.logger.setLevel(logging.DEBUG)

        try:
            # Read input file
            input_path_obj = Path(input_path).resolve()
            if not input_path_obj.exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")

            self.logger.info(f"Reading codex file: {input_path_obj}")

            with open(input_path_obj, 'r', encoding='utf-8') as f:
                if input_path_obj.suffix.lower() in ['.yaml', '.yml']:
                    codex_data = yaml.safe_load(f)
                elif input_path_obj.suffix.lower() == '.json':
                    codex_data = json.load(f)
                else:
                    raise ValueError(f"Unsupported file format: {input_path_obj.suffix}")

            # Validate V1.0 format
            if not self._is_v1_format(codex_data):
                self.logger.warning("Input file is not V1.0 format - attempting to use anyway")

            # Check for children
            if 'children' not in codex_data or not isinstance(codex_data['children'], list):
                raise ValueError("No 'children' array found in codex file")

            if not codex_data['children']:
                self.logger.warning("Children array is empty - nothing to extract")
                return {
                    'success': True,
                    'extracted_count': 0,
                    'extracted_files': [],
                    'extraction_map': {},
                    'errors': []
                }

            # Extract matching children
            extracted_children, remaining_children = self._extract_children(
                codex_data['children'],
                types
            )

            if not extracted_children:
                self.logger.warning(f"No children matched the specified types: {types}")
                return {
                    'success': True,
                    'extracted_count': 0,
                    'extracted_files': [],
                    'extraction_map': {},
                    'errors': []
                }

            self.logger.info(f"Found {len(extracted_children)} children to extract")

            # Process each extracted child
            for idx, child in enumerate(extracted_children):
                try:
                    output_path = self._resolve_output_path(
                        child,
                        idx,
                        output_pattern,
                        input_path_obj,
                        output_format
                    )

                    # Check if file exists
                    if output_path.exists() and not force and not dry_run:
                        self.logger.warning(f"File already exists: {output_path} (use --force to overwrite)")
                        self.errors.append(f"File exists: {output_path}")
                        continue

                    if dry_run:
                        self.logger.info(f"[DRY RUN] Would extract: {child.get('name', 'Untitled')} -> {output_path}")
                    else:
                        # Create extracted codex file
                        extracted_codex = self._create_extracted_codex(
                            child,
                            codex_data.get('metadata', {}),
                            str(input_path_obj)
                        )

                        # Create directory if needed
                        output_path.parent.mkdir(parents=True, exist_ok=True)

                        # Write file
                        self._write_codex_file(output_path, extracted_codex, output_format)

                        self.logger.info(f"✓ Extracted: {child.get('name', 'Untitled')} -> {output_path}")
                        self.extracted_files.append(str(output_path))

                    # Store mapping
                    child_id = child.get('id', f'child_{idx}')
                    self.extraction_map[child_id] = str(output_path)

                except Exception as e:
                    error_msg = f"Failed to extract child {idx}: {e}"
                    self.logger.error(error_msg)
                    self.errors.append(error_msg)

            # Update parent file with include directives
            if not dry_run and self.extracted_files:
                include_directives = []

                for child in extracted_children:
                    child_id = child.get('id', '')
                    if child_id in self.extraction_map:
                        output_path = Path(self.extraction_map[child_id])
                        include_path = self._generate_include_path(output_path, input_path_obj)
                        include_directives.append({'include': include_path})
                    else:
                        # Keep original child if extraction failed
                        include_directives.append(child)

                # Replace extracted children with includes, keep remaining
                codex_data['children'] = include_directives + remaining_children

                # Update metadata
                if 'metadata' not in codex_data:
                    codex_data['metadata'] = {}

                codex_data['metadata']['updated'] = datetime.utcnow().isoformat() + 'Z'
                codex_data['metadata']['exploded'] = {
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'extracted_types': types or 'all',
                    'extracted_count': len(self.extracted_files)
                }

                # Create backup
                if backup:
                    backup_path = input_path_obj.with_suffix(input_path_obj.suffix + '.backup')
                    self.logger.info(f"Creating backup: {backup_path}")
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        if input_path_obj.suffix.lower() in ['.yaml', '.yml']:
                            yaml.dump(codex_data, f, Dumper=get_yaml_dumper_with_pipe_format(),
                                    default_flow_style=False, allow_unicode=True, sort_keys=False)
                        else:
                            json.dump(codex_data, f, indent=2, ensure_ascii=False)

                # Write updated parent file
                self._write_codex_file(input_path_obj, codex_data, output_format)
                self.logger.info(f"✓ Updated parent file with {len(include_directives)} include directives")

            # Run auto-fixer on extracted files
            auto_fix_results = {}
            if auto_fix and self.extracted_files and not dry_run:
                self.logger.info(f"Running auto-fixer on {len(self.extracted_files)} extracted files...")
                auto_fix_results = self._auto_fix_extracted_files(self.extracted_files, verbose)

            return {
                'success': True,
                'extracted_count': len(self.extracted_files),
                'extracted_files': self.extracted_files,
                'extraction_map': self.extraction_map,
                'auto_fix_results': auto_fix_results,
                'errors': self.errors
            }

        except Exception as e:
            self.logger.error(f"Explosion failed: {e}", exc_info=True)
            return {
                'success': False,
                'extracted_count': 0,
                'extracted_files': [],
                'extraction_map': {},
                'auto_fix_results': {},
                'errors': [str(e)] + self.errors
            }

    def _is_v1_format(self, data: Dict[Any, Any]) -> bool:
        """Check if codex data is in V1.0 format."""
        return (
            isinstance(data, dict) and
            'metadata' in data and
            isinstance(data['metadata'], dict) and
            data['metadata'].get('formatVersion') == '1.0'
        )

    def _extract_children(
        self,
        children: List[Dict[Any, Any]],
        types: Optional[List[str]]
    ) -> Tuple[List[Dict[Any, Any]], List[Dict[Any, Any]]]:
        """
        Extract children matching specified types from direct children only.

        Returns:
            Tuple of (extracted_children, remaining_children)
        """
        if not types:
            # Extract all direct children
            return children, []

        # Normalize types to lowercase for case-insensitive matching
        types_lower = [t.lower() for t in types]

        extracted = []
        remaining = []

        for child in children:
            if not isinstance(child, dict):
                remaining.append(child)
                continue

            child_type = child.get('type', '').lower()

            if child_type in types_lower:
                extracted.append(child)
            else:
                remaining.append(child)

        return extracted, remaining

    def _create_extracted_codex(
        self,
        child: Dict[Any, Any],
        parent_metadata: Dict[Any, Any],
        parent_path: str
    ) -> Dict[Any, Any]:
        """
        Create a standalone codex file from a child node.
        """
        # Build metadata
        metadata = {
            'formatVersion': CURRENT_FORMAT_VERSION,
            'documentVersion': '1.0.0',
            'created': datetime.utcnow().isoformat() + 'Z',
            'extractedFrom': parent_path
        }

        # Inherit author and license from parent
        if 'author' in parent_metadata:
            metadata['author'] = parent_metadata['author']
        if 'license' in parent_metadata:
            metadata['license'] = parent_metadata['license']

        # Create codex structure
        extracted_codex = {'metadata': metadata}

        # Copy all child data
        for key, value in child.items():
            if key != 'metadata':  # Don't copy child's metadata if it has one
                extracted_codex[key] = value

        # Ensure required fields exist
        if 'id' not in extracted_codex:
            import uuid
            extracted_codex['id'] = str(uuid.uuid4())

        if 'type' not in extracted_codex:
            extracted_codex['type'] = 'node'

        if 'name' not in extracted_codex and 'title' not in extracted_codex:
            extracted_codex['name'] = 'Untitled'

        return extracted_codex

    def _resolve_output_path(
        self,
        child: Dict[Any, Any],
        index: int,
        pattern: str,
        parent_path: Path,
        output_format: str
    ) -> Path:
        """
        Resolve output path from pattern with placeholders.
        """
        # Get child data
        child_type = child.get('type', 'node')
        child_name = child.get('name') or child.get('title', 'Untitled')
        child_id = child.get('id', f'child_{index}')

        # Sanitize name for filename
        safe_name = self._sanitize_filename(child_name)

        # Replace placeholders
        output_str = pattern
        output_str = output_str.replace('{type}', child_type)
        output_str = output_str.replace('{name}', safe_name)
        output_str = output_str.replace('{id}', child_id)
        output_str = output_str.replace('{index}', str(index))

        # Ensure correct extension
        output_path = Path(output_str)
        if output_format == 'yaml' and output_path.suffix not in ['.yaml', '.yml']:
            output_path = output_path.with_suffix('.codex.yaml')
        elif output_format == 'json' and output_path.suffix != '.json':
            output_path = output_path.with_suffix('.codex.json')

        # Resolve relative to parent directory if not absolute
        if not output_path.is_absolute():
            output_path = (parent_path.parent / output_path).resolve()

        # Handle duplicate filenames
        if output_path.exists():
            counter = 1
            base = output_path.stem
            while output_path.exists():
                output_path = output_path.with_stem(f"{base}-{counter}")
                counter += 1

        return output_path

    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize a name for use as a filename.
        """
        # Remove or replace invalid filename characters
        # Keep: letters, numbers, spaces, hyphens, underscores
        safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)

        # Replace multiple spaces with single space
        safe_name = re.sub(r'\s+', ' ', safe_name)

        # Trim and replace spaces with hyphens
        safe_name = safe_name.strip().replace(' ', '-')

        # Limit length
        if len(safe_name) > 100:
            safe_name = safe_name[:100]

        # Ensure not empty
        if not safe_name:
            safe_name = 'untitled'

        return safe_name

    def _generate_include_path(self, output_path: Path, parent_path: Path) -> str:
        """
        Generate relative include path from parent to output file.
        """
        try:
            # Try to get relative path
            rel_path = output_path.relative_to(parent_path.parent)
            # Convert to POSIX style (forward slashes) and add leading slash
            include_path = '/' + str(rel_path).replace('\\', '/')
        except ValueError:
            # If files are on different drives or can't be made relative, use absolute
            include_path = str(output_path).replace('\\', '/')

        return include_path

    def _write_codex_file(self, path: Path, data: Dict[Any, Any], format: str) -> None:
        """
        Write codex data to file with proper formatting.
        """
        with open(path, 'w', encoding='utf-8') as f:
            if format == 'yaml':
                yaml.dump(
                    data,
                    f,
                    Dumper=get_yaml_dumper_with_pipe_format(),
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    width=120
                )
            else:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def _auto_fix_extracted_files(self, file_paths: List[str], verbose: bool) -> Dict[str, Any]:
        """
        Run auto_fixer on all extracted files.

        Returns:
            Dict with auto-fix results for each file
        """
        results = {
            'total_files': len(file_paths),
            'fixed_files': 0,
            'failed_files': 0,
            'total_fixes': 0,
            'file_details': {}
        }

        if CodexAutoFixer is None:
            self.logger.warning("Auto-fixer not available - skipping")
            return results

        fixer = CodexAutoFixer()

        for file_path in file_paths:
            try:
                self.logger.debug(f"Auto-fixing: {file_path}")

                # Read file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)

                # Apply auto-fixes
                fixed_content, fixes = fixer.auto_fix_codex(None, content)

                if fixes:
                    # Write fixed content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        yaml.dump(
                            fixed_content,
                            f,
                            Dumper=get_yaml_dumper_with_pipe_format(),
                            default_flow_style=False,
                            allow_unicode=True,
                            sort_keys=False,
                            width=120
                        )

                    results['fixed_files'] += 1
                    results['total_fixes'] += len(fixes)
                    results['file_details'][file_path] = {
                        'fixes_applied': len(fixes),
                        'fixes': fixes if verbose else None
                    }

                    self.logger.info(f"  ✓ Auto-fixed {file_path}: {len(fixes)} fixes applied")
                else:
                    self.logger.debug(f"  ✓ No fixes needed for {file_path}")

            except Exception as e:
                self.logger.error(f"  ✗ Auto-fix failed for {file_path}: {e}")
                results['failed_files'] += 1
                results['file_details'][file_path] = {
                    'error': str(e)
                }

        return results


# ============================================================================
# Command-Line Interface
# ============================================================================

def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Extract and modularize codex children into separate files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all characters and locations
  python explode_codex.py story.codex.yaml --types character,location

  # Custom output pattern
  python explode_codex.py story.codex.yaml --types character --output-pattern "./nodes/{type}/{name}.codex.yaml"

  # Dry run to preview
  python explode_codex.py story.codex.yaml --types character --dry-run

  # Extract all direct children
  python explode_codex.py story.codex.yaml

  # Disable auto-fix
  python explode_codex.py story.codex.yaml --types character --no-auto-fix
        """
    )

    parser.add_argument(
        'input_file',
        help='Path to input codex file'
    )

    parser.add_argument(
        '--types',
        help='Comma-separated list of node types to extract (e.g., "character,location")'
    )

    parser.add_argument(
        '--output-pattern',
        default='./{type}s/{name}.codex.yaml',
        help='Output path pattern with placeholders: {type}, {name}, {id}, {index} (default: "./{type}s/{name}.codex.yaml")'
    )

    parser.add_argument(
        '--format',
        choices=['yaml', 'json'],
        default='yaml',
        help='Output file format (default: yaml)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be extracted without making changes'
    )

    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Do not create backup of original file'
    )

    parser.add_argument(
        '--no-auto-fix',
        action='store_true',
        help='Do not run auto-fixer on extracted files'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing files'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Detailed logging'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    # Parse types
    types = None
    if args.types:
        types = [t.strip() for t in args.types.split(',')]

    # Build options
    options = {
        'dry_run': args.dry_run,
        'backup': not args.no_backup,
        'format': args.format,
        'verbose': args.verbose,
        'auto_fix': not args.no_auto_fix,
        'force': args.force
    }

    # Run exploder
    print("=" * 60)
    print("Codex Exploder - Extract and Modularize Children")
    print("=" * 60)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")

    print(f"\nInput: {args.input_file}")
    print(f"Types: {', '.join(types) if types else 'all direct children'}")
    print(f"Pattern: {args.output_pattern}")
    print(f"Format: {args.format}")
    print(f"Auto-fix: {'enabled' if not args.no_auto_fix else 'disabled'}")
    print()

    exploder = CodexExploder()
    result = exploder.explode(
        args.input_file,
        types=types,
        output_pattern=args.output_pattern,
        options=options
    )

    # Print results
    print("\n" + "=" * 60)
    if result['success']:
        print(f"✅ Explosion complete!")
        print(f"   Extracted: {result['extracted_count']} nodes")

        if result['extracted_files']:
            print(f"\n📁 Extracted files:")
            for file_path in result['extracted_files']:
                print(f"   - {file_path}")

        if result.get('auto_fix_results') and result['auto_fix_results'].get('total_fixes', 0) > 0:
            auto_fix = result['auto_fix_results']
            print(f"\n🔧 Auto-fix results:")
            print(f"   Fixed files: {auto_fix['fixed_files']}/{auto_fix['total_files']}")
            print(f"   Total fixes: {auto_fix['total_fixes']}")

        if result['errors']:
            print(f"\n⚠️  Warnings ({len(result['errors'])}):")
            for error in result['errors']:
                print(f"   - {error}")
    else:
        print(f"❌ Explosion failed!")
        if result['errors']:
            print(f"\nErrors:")
            for error in result['errors']:
                print(f"   - {error}")
        sys.exit(1)

    print("=" * 60)


if __name__ == '__main__':
    main()
