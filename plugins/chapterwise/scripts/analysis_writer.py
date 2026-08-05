#!/usr/bin/env python3
"""
Writes analysis results to .analysis.json files.
Uses proper Codex V1.3 format with children arrays and attributes.

Structure matches chapterwise-app file-based analysis system:
- Root: type "analysis" with sourceFile/sourceHash in attributes
- Children: type "analysis-module" (one per module)
- Grandchildren: type "analysis-entry" (history, newest first)
"""
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add scripts directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))
from staleness_checker import get_analysis_file_path, compute_source_hash

# Codex format version (single source of truth).
try:
    from codex_version import CURRENT_FORMAT_VERSION
except ImportError:  # standalone execution outside the scripts directory
    CURRENT_FORMAT_VERSION = '1.3'

DEFAULT_HISTORY_DEPTH = 3

# Use shared schema validator
try:
    # Add parent scripts directory to path for cross-plugin imports
    _codex_scripts = Path(__file__).parent.parent.parent / 'chapterwise' / 'scripts'
    if str(_codex_scripts) not in sys.path:
        sys.path.insert(0, str(_codex_scripts))
    from schema_validator import validate_analysis as _validate_analysis
except ImportError:
    # Fallback if schema_validator not available
    def _validate_analysis(data: dict) -> Tuple[bool, List[str]]:
        return True, []  # Skip validation


def generate_uuid() -> str:
    """Generate a UUID v4 string."""
    return str(uuid.uuid4())


def _get_attribute(node: dict, key: str) -> Optional[str]:
    """Get attribute value from node's attributes array."""
    for attr in node.get('attributes', []):
        if attr.get('key') == key:
            return attr.get('value')
    return None


def _set_attribute(node: dict, key: str, value: Any) -> None:
    """Set attribute value in node's attributes array."""
    attrs = node.setdefault('attributes', [])
    for attr in attrs:
        if attr.get('key') == key:
            attr['value'] = value
            return
    attrs.append({'key': key, 'value': value})


def create_analysis_file_structure(source_path: Path, source_hash: str) -> Dict:
    """Create initial structure for a new analysis file (Codex V1.3 format)."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    source_filename = os.path.basename(source_path)
    base_name = Path(source_filename).stem.replace('.codex', '')

    return {
        'metadata': {
            'formatVersion': CURRENT_FORMAT_VERSION,
            'created': now,
            'updated': now
        },
        'id': f'{base_name}-analysis',
        'type': 'analysis',
        'name': 'Analysis Results',
        'attributes': [
            {'key': 'sourceFile', 'value': source_filename},
            {'key': 'sourceHash', 'value': source_hash}
        ],
        'children': []
    }


def create_analysis_entry(
    source_hash: str,
    model: str,
    body: str,
    summary: str = '',
    children: List[Dict] = None,
    tags: List[str] = None,
    entry_attributes: List[Dict] = None
) -> Dict:
    """Create a single analysis entry node (Codex V1.3 format)."""
    now = datetime.now(timezone.utc)
    entry_id = f"entry-{now.strftime('%Y%m%dT%H%M%SZ')}"

    entry = {
        'id': entry_id,
        'type': 'analysis-entry',
        'status': 'published',
        'attributes': [
            {'key': 'model', 'value': model},
            {'key': 'sourceHash', 'value': source_hash},
            {'key': 'analysisStatus', 'value': 'current'},
            {'key': 'timestamp', 'value': now.isoformat().replace('+00:00', 'Z')}
        ],
        'body': body
    }

    if summary:
        entry['summary'] = summary

    if children:
        entry['children'] = children

    if tags:
        entry['tags'] = tags

    # Add any additional attributes from the analysis result
    if entry_attributes:
        for attr in entry_attributes:
            _set_attribute(entry, attr.get('key'), attr.get('value'))

    return entry


def _get_or_create_module(data: Dict[str, Any], module_name: str) -> Dict[str, Any]:
    """Find or create a module node in children array."""
    children = data.setdefault('children', [])

    # Find existing module by id
    for child in children:
        if child.get('id') == module_name and child.get('type') == 'analysis-module':
            return child

    # Create new module node (proper codex format)
    module_node = {
        'id': module_name,
        'type': 'analysis-module',
        'name': module_name.replace('-', ' ').replace('_', ' ').title(),
        'children': []  # Entries added as children
    }
    children.append(module_node)
    return module_node


def add_analysis_result(
    source_path: Path,
    module_name: str,
    analysis_content: Dict[str, Any],
    model: str = 'claude-sonnet-4',
    history_depth: int = DEFAULT_HISTORY_DEPTH
) -> Path:
    """
    Add analysis result to the .analysis.json file.
    Creates file if doesn't exist, prepends to module's children (history).
    """
    source_path = Path(source_path)
    analysis_path = get_analysis_file_path(source_path)
    source_content = source_path.read_text(encoding='utf-8')
    source_hash = compute_source_hash(source_content)

    # Load or create analysis file
    if analysis_path.exists():
        try:
            with open(analysis_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = create_analysis_file_structure(source_path, source_hash)
    else:
        data = create_analysis_file_structure(source_path, source_hash)

    # Update root sourceHash attribute
    _set_attribute(data, 'sourceHash', source_hash)

    # Update metadata.updated
    data.setdefault('metadata', {})['updated'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Get or create module node
    module_node = _get_or_create_module(data, module_name)

    # Mark old entries as stale
    for entry in module_node.get('children', []):
        _set_attribute(entry, 'analysisStatus', 'stale')
        entry['status'] = 'draft'  # Demote to draft

    # Create new entry
    new_entry = create_analysis_entry(
        source_hash=source_hash,
        model=model,
        body=analysis_content.get('body', ''),
        summary=analysis_content.get('summary', ''),
        children=analysis_content.get('children', []),
        tags=analysis_content.get('tags', []),
        entry_attributes=analysis_content.get('attributes', [])
    )

    # Prepend to history and trim to depth
    entries = module_node.setdefault('children', [])
    entries.insert(0, new_entry)
    module_node['children'] = entries[:history_depth]

    # Validate before writing
    is_valid, errors = _validate_analysis(data)
    if not is_valid:
        logger.warning(f"Analysis validation issues: {errors}")
        # Continue anyway - validation is advisory

    # Ensure parent directory exists
    analysis_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file as JSON
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return analysis_path


if __name__ == '__main__':
    if len(sys.argv) < 4:
        logger.error("Usage: analysis_writer.py <source_file> <module_name> <analysis_json>")
        logger.error("       analysis_writer.py <source_file> <module_name> - (reads from stdin)")
        sys.exit(1)

    source_path = Path(sys.argv[1])
    module_name = sys.argv[2]

    if sys.argv[3] == '-':
        analysis_json = sys.stdin.read()
    else:
        analysis_json = sys.argv[3]

    analysis_content = json.loads(analysis_json)

    output_path = add_analysis_result(source_path, module_name, analysis_content)
    logger.info(f"Written to: {output_path}")
