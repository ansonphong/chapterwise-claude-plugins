#!/usr/bin/env python3
"""
Computes sourceHash for staleness detection.
Checks if existing analysis is fresh or stale.

Uses .analysis.json format (proper Codex V1.3 structure).
"""
import hashlib
import json
import re
from pathlib import Path
from typing import Optional, Tuple


def compute_source_hash(content: str) -> str:
    """Compute SHA-256 hash, return first 16 chars."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def get_analysis_file_path(source_path: Path) -> Path:
    """Convert source.codex.yaml -> source.analysis.json

    Analysis files use JSON for faster parsing (5-30x faster than YAML).
    """
    source_path = Path(source_path).resolve()
    name = source_path.name

    # Remove .codex.yaml, .codex.json, .codex.md extensions
    base_name = re.sub(r'\.codex\.(yaml|yml|json|md)$', '', name, flags=re.IGNORECASE)

    # If no codex extension found, just use the stem
    if base_name == name:
        base_name = source_path.stem

    return source_path.parent / f"{base_name}.analysis.json"


def get_current_source_hash(source_path: Path) -> Optional[str]:
    """Read source file and compute its hash."""
    source_path = Path(source_path)
    if not source_path.exists():
        return None
    content = source_path.read_text(encoding='utf-8')
    return compute_source_hash(content)


def _get_attribute(node: dict, key: str) -> Optional[str]:
    """Get attribute value from codex node's attributes array."""
    for attr in node.get('attributes', []):
        if attr.get('key') == key:
            return attr.get('value')
    return None


def get_analysis_source_hash(analysis_path: Path) -> Optional[str]:
    """Read sourceHash from existing analysis file (from attributes array)."""
    if not analysis_path.exists():
        return None

    try:
        with open(analysis_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        return _get_attribute(content, 'sourceHash')
    except (json.JSONDecodeError, AttributeError, KeyError):
        return None


def get_module_latest_hash(analysis_path: Path, module_name: str) -> Optional[str]:
    """Get the sourceHash from the latest entry of a specific module.

    Structure (proper Codex V1.3):
    - children[]: analysis-module nodes (id = module_name)
      - children[]: analysis-entry nodes (sorted newest first)
        - attributes[]: includes sourceHash
    """
    if not analysis_path.exists():
        return None

    try:
        with open(analysis_path, 'r', encoding='utf-8') as f:
            content = json.load(f)

        # Find module in children
        for child in content.get('children', []):
            if child.get('id') == module_name and child.get('type') == 'analysis-module':
                # Get entries (children of module)
                entries = child.get('children', [])
                if entries:
                    # First entry is most recent
                    return _get_attribute(entries[0], 'sourceHash')
        return None
    except (json.JSONDecodeError, AttributeError, TypeError, KeyError):
        return None


def is_analysis_stale(source_path: Path, module_name: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check if analysis is stale for a source file.

    Returns: (is_stale, current_hash, existing_hash)
    """
    source_path = Path(source_path)
    analysis_path = get_analysis_file_path(source_path)
    current_hash = get_current_source_hash(source_path)

    if current_hash is None:
        return (True, None, None)

    if module_name:
        existing_hash = get_module_latest_hash(analysis_path, module_name)
    else:
        existing_hash = get_analysis_source_hash(analysis_path)

    is_stale = current_hash != existing_hash
    return (is_stale, current_hash, existing_hash)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: staleness_checker.py <source_file> [module_name]")
        sys.exit(1)

    source_path = Path(sys.argv[1])
    module_name = sys.argv[2] if len(sys.argv) > 2 else None

    is_stale, current, existing = is_analysis_stale(source_path, module_name)

    result = {
        'source': str(source_path),
        'module': module_name,
        'isStale': is_stale,
        'currentHash': current,
        'existingHash': existing,
        'analysisFile': str(get_analysis_file_path(source_path))
    }
    print(json.dumps(result, indent=2))
