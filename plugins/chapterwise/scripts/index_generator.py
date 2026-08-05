#!/usr/bin/env python3
"""
Index Generator for Chapterwise Codex Projects
Generates index.codex.yaml files by scanning directory structure.

Usage:
    python index_generator.py <path> [--dry-run] [--include-md] [-v]

Examples:
    python index_generator.py .
    python index_generator.py /path/to/project --dry-run
"""

import os
import sys
import re
import uuid
import argparse
import logging
import fnmatch
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Codex format version (single source of truth).
try:
    from codex_version import CURRENT_FORMAT_VERSION
except ImportError:  # standalone execution outside the scripts directory
    CURRENT_FORMAT_VERSION = '1.3'

logger = logging.getLogger(__name__)

# Default patterns
DEFAULT_INCLUDE = [
    "**/*.codex.yaml",
    "**/*.codex.json",
]

DEFAULT_EXCLUDE = [
    "**/node_modules/**",
    "**/.git/**",
    "**/.*",
    "**/_ARCHIVE/**",
    "**/dist/**",
    "**/build/**",
    "**/venv/**",
    "**/__pycache__/**",
]

# File extension to type mapping
EXTENSION_TYPE_MAP = {
    ".codex.yaml": "codex",
    ".codex.yml": "codex",
    ".codex.json": "codex",
    ".codex": "codex",
    ".md": "markdown",
    ".txt": "text",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
}

# Default type styles
DEFAULT_TYPE_STYLES = {
    "character": {"emoji": "👤", "color": "#10B981"},
    "location": {"emoji": "📍", "color": "#3B82F6"},
    "chapter": {"emoji": "📖", "color": "#8B5CF6"},
    "scene": {"emoji": "🎬", "color": "#F59E0B"},
    "item": {"emoji": "🔮", "color": "#EC4899"},
    "faction": {"emoji": "🏛️", "color": "#6366F1"},
    "timeline": {"emoji": "📅", "color": "#14B8A6"},
    "codex": {"emoji": "📄", "color": "#6B7280"},
    "markdown": {"emoji": "📝", "color": "#6B7280"},
    "folder": {"emoji": "📁", "color": "#F59E0B"},
}


class IndexGenerator:
    """
    Generates index.codex.yaml files for Chapterwise Git projects.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.include_patterns = DEFAULT_INCLUDE.copy()
        self.exclude_patterns = DEFAULT_EXCLUDE.copy()
        self.include_markdown = False
        self.scanned_files = []
        self.scanned_folders = []

    def generate_index(
        self,
        root_path: str,
        project_name: str = None,
        project_title: str = None,
        summary: str = None,
        include_markdown: bool = False,
        dry_run: bool = False,
        verbose: bool = False
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Generate an index.codex.yaml structure for a directory.

        Args:
            root_path: Root directory to scan
            project_name: Project identifier (defaults to folder name)
            project_title: Display title (defaults to project_name)
            summary: Project description
            include_markdown: Include .md files in patterns
            dry_run: Don't write file, just return structure
            verbose: Enable detailed logging

        Returns:
            Tuple of (index_structure, list_of_scanned_files)
        """
        root = Path(root_path).resolve()

        if not root.exists():
            raise ValueError(f"Path does not exist: {root}")

        if not root.is_dir():
            raise ValueError(f"Path is not a directory: {root}")

        # Set up patterns
        self.include_markdown = include_markdown
        if include_markdown:
            self.include_patterns.append("**/*.md")

        # Derive project name from folder if not provided
        if project_name is None:
            project_name = root.name.lower().replace(" ", "-")

        if project_title is None:
            project_title = root.name

        # Build the index structure
        index = {
            "metadata": {
                "formatVersion": CURRENT_FORMAT_VERSION,
                "documentVersion": "1.0.0",
                "created": datetime.utcnow().isoformat() + "Z",
            },
            "id": "index-root",
            "type": "index",
            "name": project_name,
            "title": project_title,
            "summary": summary or f"Index for {project_title}",
            "status": "private",
            "patterns": {
                "include": self.include_patterns,
                "exclude": self.exclude_patterns,
            },
            "display": {
                "defaultView": "tree",
                "sortBy": "order",
                "groupBy": "folder",
                "showHidden": False,
            },
            "children": [],
        }

        # Scan directory structure
        self.scanned_files = []
        self.scanned_folders = []
        index["children"] = self._scan_directory(root, root)

        self.logger.info(f"Scanned {len(self.scanned_files)} files, {len(self.scanned_folders)} folders")

        return index, self.scanned_files

    def _should_include(self, path: Path, root: Path) -> bool:
        """Check if a path matches include patterns and not exclude patterns."""
        rel_path = str(path.relative_to(root))

        # Check exclude patterns first
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(f"/{rel_path}", pattern):
                return False
            # Also check just the filename for patterns like ".*"
            if fnmatch.fnmatch(path.name, pattern):
                return False

        # Check include patterns
        for pattern in self.include_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(path.name, pattern.split("/")[-1]):
                return True

        return False

    def _get_file_type(self, path: Path) -> str:
        """Determine file type from extension."""
        name = path.name.lower()

        # Check compound extensions first
        for ext, file_type in EXTENSION_TYPE_MAP.items():
            if name.endswith(ext):
                return file_type

        # Default to the extension without dot
        suffix = path.suffix.lower()
        return suffix[1:] if suffix else "unknown"

    def _scan_directory(self, directory: Path, root: Path, depth: int = 0) -> List[Dict[str, Any]]:
        """
        Recursively scan a directory and build children structure.

        Args:
            directory: Current directory to scan
            root: Root directory for relative path calculation
            depth: Current recursion depth

        Returns:
            List of child nodes
        """
        children = []

        try:
            entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            self.logger.warning(f"Permission denied: {directory}")
            return children

        order = 1
        for entry in entries:
            # Skip hidden files/folders (starting with .)
            if entry.name.startswith("."):
                continue

            # Skip index files themselves
            if entry.name in ["index.codex.yaml", "index.codex.json", ".index.codex.yaml", ".index.codex.json"]:
                continue

            rel_path = entry.relative_to(root)

            if entry.is_dir():
                # Check if folder should be excluded
                if self._should_exclude_folder(entry, root):
                    continue

                self.scanned_folders.append(str(rel_path))

                # Recursively scan subfolder
                sub_children = self._scan_directory(entry, root, depth + 1)

                # Only include folder if it has content or we're at depth 0
                if sub_children or depth == 0:
                    folder_node = {
                        "name": entry.name,
                        "order": order,
                        "children": sub_children if sub_children else [],
                    }
                    children.append(folder_node)
                    order += 1

            elif entry.is_file():
                # Check if file matches patterns
                if not self._should_include(entry, root):
                    continue

                self.scanned_files.append(str(rel_path))

                # Build file node - NO type field (auto-detected)
                file_node = {
                    "name": self._get_display_name(entry),
                    "_filename": entry.name,
                    "order": order,
                }
                children.append(file_node)
                order += 1

        return children

    def _should_exclude_folder(self, folder: Path, root: Path) -> bool:
        """Check if a folder should be excluded."""
        rel_path = str(folder.relative_to(root))
        folder_name = folder.name.lower()

        # Common folders to always exclude
        always_exclude = {
            "node_modules", ".git", "__pycache__", "venv", ".venv",
            "dist", "build", "_archive", ".archive", ".claude"
        }

        if folder_name in always_exclude:
            return True

        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(rel_path, pattern.rstrip("*/")):
                return True
            if fnmatch.fnmatch(f"{rel_path}/", pattern):
                return True

        return False

    def _get_display_name(self, path: Path) -> str:
        """Get display name for a file (without codex extensions)."""
        name = path.name

        # Remove compound extensions
        for ext in [".codex.yaml", ".codex.yml", ".codex.json", ".codex"]:
            if name.lower().endswith(ext):
                return name[:-len(ext)]

        # Remove simple extension
        return path.stem

    def write_index(self, index: Dict[str, Any], output_path: str) -> bool:
        """
        Write index structure to a YAML file.

        Args:
            index: Index structure to write
            output_path: Path to write to

        Returns:
            True if successful
        """
        try:
            import yaml

            # Custom representer for multiline strings
            def str_representer(dumper, data):
                if '\n' in data or len(data) > 80:
                    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
                return dumper.represent_scalar('tag:yaml.org,2002:str', data)

            yaml.add_representer(str, str_representer)

            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(index, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)

            self.logger.info(f"Wrote index to: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to write index: {e}")
            return False


# ============================================================================
# Command-Line Interface
# ============================================================================

def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Generate index.codex.yaml for Chapterwise Git projects',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate index for current directory
    python index_generator.py .

    # Generate for specific path with custom name
    python index_generator.py /path/to/project --name my-project

    # Preview without writing (dry run)
    python index_generator.py . --dry-run

    # Include markdown files
    python index_generator.py . --include-md

    # Verbose output
    python index_generator.py . -v
        """
    )

    parser.add_argument('path', help='Root directory to scan')
    parser.add_argument('--name', help='Project name (defaults to folder name)')
    parser.add_argument('--title', help='Project title (defaults to name)')
    parser.add_argument('--summary', help='Project summary/description')
    parser.add_argument('--include-md', action='store_true', help='Include markdown files')
    parser.add_argument('-d', '--dry-run', action='store_true', help='Preview without writing')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-o', '--output', help='Output file path (defaults to <path>/index.codex.yaml)')

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    # Resolve path
    root_path = Path(args.path).resolve()

    if not root_path.exists():
        print(f"Error: Path does not exist: {root_path}")
        sys.exit(1)

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Scanning: {root_path}")

    # Generate index
    generator = IndexGenerator()

    try:
        index, scanned_files = generator.generate_index(
            root_path=str(root_path),
            project_name=args.name,
            project_title=args.title,
            summary=args.summary,
            include_markdown=args.include_md,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Report results
    print(f"\nScan Results:")
    print(f"   Files: {len(generator.scanned_files)}")
    print(f"   Folders: {len(generator.scanned_folders)}")

    if args.verbose:
        print(f"\nScanned files:")
        for f in generator.scanned_files[:20]:
            print(f"   - {f}")
        if len(generator.scanned_files) > 20:
            print(f"   ... and {len(generator.scanned_files) - 20} more")

    # Write or preview
    if args.dry_run:
        import yaml
        print(f"\nGenerated index (preview):\n")
        print(yaml.dump(index, default_flow_style=False, allow_unicode=True, sort_keys=False))
        print("\nDry run - no files written")
    else:
        output_path = args.output or str(root_path / "index.codex.yaml")

        if generator.write_index(index, output_path):
            print(f"\nIndex written to: {output_path}")
        else:
            print(f"\nFailed to write index")
            sys.exit(1)


if __name__ == '__main__':
    main()
