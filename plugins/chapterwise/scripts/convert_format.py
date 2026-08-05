#!/usr/bin/env python3
"""
Convert Format - Codex <-> Markdown (Codex Lite) Conversion

Two-way conversion between full Codex format and Codex Lite (Markdown with YAML frontmatter).

Usage:
    python convert_format.py <input_file> --to-codex [--output <file>]
    python convert_format.py <input_file> --to-markdown [--output <file>]

Examples:
    # Convert markdown to codex
    python convert_format.py document.md --to-codex

    # Convert codex to markdown
    python convert_format.py story.codex.yaml --to-markdown

    # Specify output file
    python convert_format.py document.md --to-codex -o output.codex.yaml
"""

import os
import sys
import re
import uuid
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

# Codex format version (single source of truth).
try:
    from codex_version import CURRENT_FORMAT_VERSION
except ImportError:  # standalone execution outside the scripts directory
    CURRENT_FORMAT_VERSION = '1.3'

logger = logging.getLogger(__name__)


# Codex Lite field mappings
# These fields map directly between codex root and markdown frontmatter
CODEX_LITE_ROOT_FIELDS = {
    'type', 'name', 'title', 'summary', 'id',
    'status', 'featured', 'image', 'images', 'tags', 'body'
}

CODEX_LITE_METADATA_FIELDS = {
    'author': 'author',
    'updated': 'last_updated',
    'description': 'description',
    'license': 'license'
}


def generate_uuid() -> str:
    """Generate a UUID v4."""
    return str(uuid.uuid4())


def is_codex_file(file_path: str) -> bool:
    """Check if file is a codex file."""
    lower = file_path.lower()
    return any(lower.endswith(ext) for ext in ['.codex.yaml', '.codex.yml', '.codex.json', '.codex'])


def is_markdown_file(file_path: str) -> bool:
    """Check if file is a markdown file."""
    return file_path.lower().endswith('.md')


class CodexMarkdownConverter:
    """Convert between Codex and Markdown formats."""

    def convert_codex_to_markdown(self, codex_data: Dict[str, Any]) -> Tuple[str, List[str]]:
        """
        Convert Codex to Markdown (Codex Lite).

        Extracts frontmatter fields and body from codex format,
        creates a standard markdown file with YAML frontmatter.

        Returns:
            Tuple of (markdown_text, warnings)
        """
        warnings = []
        frontmatter: Dict[str, Any] = {}

        # Check for children - they won't be converted
        children = codex_data.get('children', [])
        if children and len(children) > 0:
            warnings.append(f"This codex has {len(children)} children that will not be included in the markdown file.")

        # Map root fields to frontmatter
        for field in CODEX_LITE_ROOT_FIELDS:
            if field == 'body':
                continue  # Body goes after frontmatter
            if field in codex_data and codex_data[field] is not None:
                value = codex_data[field]
                # Handle tags - convert array to comma-delimited if simple strings
                if field == 'tags' and isinstance(value, list):
                    if all(isinstance(t, str) for t in value):
                        frontmatter[field] = ', '.join(value)
                    else:
                        frontmatter[field] = value
                else:
                    frontmatter[field] = value

        # Map metadata fields to frontmatter
        metadata = codex_data.get('metadata', {})
        if metadata:
            for codex_key, fm_key in CODEX_LITE_METADATA_FIELDS.items():
                if codex_key in metadata and metadata[codex_key] is not None:
                    frontmatter[fm_key] = metadata[codex_key]

        # Map attributes to frontmatter (if any)
        attributes = codex_data.get('attributes', [])
        if attributes and isinstance(attributes, list):
            for attr in attributes:
                if isinstance(attr, dict) and 'key' in attr and attr.get('value') is not None:
                    frontmatter[attr['key']] = attr['value']

        # Build markdown content
        markdown = ''

        # Add frontmatter if we have any fields
        if frontmatter:
            import yaml
            fm_yaml = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False).strip()
            markdown = f"---\n{fm_yaml}\n---\n\n"

        # Add title as H1 if we have name/title
        title = codex_data.get('name') or codex_data.get('title')
        if title:
            markdown += f"# {title}\n\n"

        # Add body content
        body = codex_data.get('body', '')
        if body:
            markdown += body.strip() + '\n'

        return markdown, warnings

    def convert_markdown_to_codex(self, md_content: str, source_file_name: str) -> Tuple[Dict[str, Any], List[str]]:
        """
        Convert Markdown (Codex Lite) to Codex.

        Parses YAML frontmatter and body from markdown,
        maps fields to proper codex structure.

        Returns:
            Tuple of (codex_dict, warnings)
        """
        warnings = []

        # Extract frontmatter
        frontmatter, body = self._extract_frontmatter(md_content)

        # Extract title from first H1 if not in frontmatter
        title = frontmatter.get('name') or frontmatter.get('title')
        body_content = body

        # Check for H1 heading in body
        h1_match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
        if h1_match:
            h1_title = h1_match.group(1).strip()
            # If no title in frontmatter, use H1 as title
            if not title:
                title = h1_title
            # Always remove H1 from body to avoid duplication (it becomes the title field)
            body_content = re.sub(r'^#\s+.+\n*', '', body, count=1).strip()

        # Build codex structure
        basename = Path(source_file_name).stem

        codex: Dict[str, Any] = {
            'metadata': {
                'formatVersion': CURRENT_FORMAT_VERSION,
                'documentVersion': '1.0.0',
                'created': datetime.utcnow().isoformat() + 'Z',
                'source': 'markdown-lite',
                'sourceFile': Path(source_file_name).name
            },
            'type': frontmatter.get('type', 'document'),
            'name': frontmatter.get('name') or title or basename,
            'title': title or basename
        }

        # Map metadata fields from frontmatter
        metadata = codex['metadata']
        if frontmatter.get('author'):
            metadata['author'] = frontmatter['author']
        if frontmatter.get('last_updated'):
            metadata['updated'] = frontmatter['last_updated']
        if frontmatter.get('description'):
            metadata['description'] = frontmatter['description']
        if frontmatter.get('license'):
            metadata['license'] = frontmatter['license']

        # Map root fields
        if frontmatter.get('summary'):
            codex['summary'] = frontmatter['summary']
        if frontmatter.get('id'):
            codex['id'] = frontmatter['id']
        else:
            codex['id'] = generate_uuid()
        if frontmatter.get('status'):
            codex['status'] = frontmatter['status']
        if 'featured' in frontmatter:
            codex['featured'] = bool(frontmatter['featured'])
        if frontmatter.get('image'):
            codex['image'] = frontmatter['image']
        if frontmatter.get('images'):
            codex['images'] = frontmatter['images']

        # Handle tags - support comma-delimited string or array
        if frontmatter.get('tags'):
            codex['tags'] = self._parse_tags(frontmatter['tags'])

        # Add body
        if body_content and body_content.strip():
            codex['body'] = body_content.strip()

        # Collect remaining frontmatter fields as attributes
        known_fields = (
            CODEX_LITE_ROOT_FIELDS |
            set(CODEX_LITE_METADATA_FIELDS.values()) |
            {'author', 'last_updated', 'description', 'license'}
        )

        attributes = []
        for key, value in frontmatter.items():
            if key not in known_fields:
                attr_name = key.replace('_', ' ').title()
                attributes.append({
                    'key': key,
                    'name': attr_name,
                    'value': value
                })

        if attributes:
            codex['attributes'] = attributes

        return codex, warnings

    def _extract_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Extract YAML frontmatter from markdown content."""
        import yaml

        frontmatter: Dict[str, Any] = {}
        body = content

        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                fm_text = parts[1].strip()
                body = parts[2].strip()

                try:
                    frontmatter = yaml.safe_load(fm_text) or {}
                except yaml.YAMLError as e:
                    logger.warning(f"Failed to parse frontmatter: {e}")

        return frontmatter, body

    def _parse_tags(self, tags: Any) -> List[str]:
        """Parse tags from various formats."""
        if isinstance(tags, str):
            return [t.strip() for t in tags.split(',') if t.strip()]
        elif isinstance(tags, list):
            return [str(t) if not isinstance(t, str) else t for t in tags]
        return []


def convert_to_markdown(input_path: str, output_path: Optional[str] = None, keep_original: bool = True) -> Tuple[bool, str, List[str]]:
    """
    Convert a codex file to markdown.

    Returns:
        Tuple of (success, output_path, warnings)
    """
    import yaml

    if not os.path.exists(input_path):
        return False, '', [f"File not found: {input_path}"]

    if not is_codex_file(input_path):
        return False, '', [f"Not a codex file: {input_path}"]

    # Read and parse codex file
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    is_json = input_path.lower().endswith('.json')

    try:
        if is_json:
            import json
            codex_data = json.loads(content)
        else:
            codex_data = yaml.safe_load(content)
    except Exception as e:
        return False, '', [f"Failed to parse codex file: {e}"]

    # Convert
    converter = CodexMarkdownConverter()
    markdown, warnings = converter.convert_codex_to_markdown(codex_data)

    # Determine output path
    if not output_path:
        dir_path = os.path.dirname(input_path)
        base_name = os.path.basename(input_path)
        # Remove codex extensions
        for ext in ['.codex.yaml', '.codex.yml', '.codex.json', '.codex']:
            if base_name.lower().endswith(ext):
                base_name = base_name[:-len(ext)]
                break
        output_path = os.path.join(dir_path, f"{base_name}.md")

    # Check if output exists
    if os.path.exists(output_path):
        warnings.append(f"Output file will be overwritten: {output_path}")

    # Write markdown
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)

    # Delete original if requested
    if not keep_original:
        try:
            os.remove(input_path)
        except Exception as e:
            warnings.append(f"Could not delete original file: {e}")

    return True, output_path, warnings


def convert_to_codex(input_path: str, output_path: Optional[str] = None, output_format: str = 'yaml', keep_original: bool = True) -> Tuple[bool, str, List[str]]:
    """
    Convert a markdown file to codex.

    Returns:
        Tuple of (success, output_path, warnings)
    """
    import yaml

    if not os.path.exists(input_path):
        return False, '', [f"File not found: {input_path}"]

    if not is_markdown_file(input_path):
        return False, '', [f"Not a markdown file: {input_path}"]

    # Read markdown file
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Convert
    converter = CodexMarkdownConverter()
    codex_data, warnings = converter.convert_markdown_to_codex(content, input_path)

    # Determine output path
    if not output_path:
        dir_path = os.path.dirname(input_path)
        base_name = Path(input_path).stem
        ext = '.codex.yaml' if output_format == 'yaml' else '.codex.json'
        output_path = os.path.join(dir_path, f"{base_name}{ext}")

    # Check if output exists
    if os.path.exists(output_path):
        warnings.append(f"Output file will be overwritten: {output_path}")

    # Write codex file
    if output_format == 'json':
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(codex_data, f, indent=2, ensure_ascii=False)
    else:
        # Create custom Dumper to avoid modifying global yaml state
        class CodexDumper(yaml.SafeDumper):
            pass

        def str_representer(dumper, data):
            if '\n' in data or len(data) > 80:
                return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
            return dumper.represent_scalar('tag:yaml.org,2002:str', data)

        CodexDumper.add_representer(str, str_representer)

        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(codex_data, f, Dumper=CodexDumper, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)

    # Delete original if requested
    if not keep_original:
        try:
            os.remove(input_path)
        except Exception as e:
            warnings.append(f"Could not delete original file: {e}")

    return True, output_path, warnings


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Convert between Codex and Markdown (Codex Lite) formats',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Convert markdown to codex (YAML)
    python convert_format.py document.md --to-codex

    # Convert markdown to codex (JSON)
    python convert_format.py document.md --to-codex --format json

    # Convert codex to markdown
    python convert_format.py story.codex.yaml --to-markdown

    # Specify output file
    python convert_format.py document.md --to-codex -o output.codex.yaml

    # Delete original after conversion
    python convert_format.py document.md --to-codex --delete-original
        """
    )

    parser.add_argument('input', help='Input file path')

    direction_group = parser.add_mutually_exclusive_group(required=True)
    direction_group.add_argument('--to-codex', action='store_true', help='Convert markdown to codex')
    direction_group.add_argument('--to-markdown', action='store_true', help='Convert codex to markdown')

    parser.add_argument('-o', '--output', help='Output file path (auto-generated if not specified)')
    parser.add_argument('--format', choices=['yaml', 'json'], default='yaml', help='Output format for codex (default: yaml)')
    parser.add_argument('--delete-original', action='store_true', help='Delete original file after conversion')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    input_path = args.input
    keep_original = not args.delete_original

    if args.to_codex:
        print(f"Converting to Codex: {input_path}")
        success, output_path, warnings = convert_to_codex(
            input_path,
            args.output,
            args.format,
            keep_original
        )
    else:  # args.to_markdown
        print(f"Converting to Markdown: {input_path}")
        success, output_path, warnings = convert_to_markdown(
            input_path,
            args.output,
            keep_original
        )

    # Show warnings
    for warning in warnings:
        print(f"  Warning: {warning}")

    if success:
        print(f"  Output: {output_path}")
        if not keep_original:
            print(f"  Deleted original file")
        sys.exit(0)
    else:
        print(f"  Failed: {warnings[0] if warnings else 'Unknown error'}")
        sys.exit(1)


if __name__ == '__main__':
    main()
