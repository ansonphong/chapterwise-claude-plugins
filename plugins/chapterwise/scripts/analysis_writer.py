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
import re
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

# Recorded when the caller does not report which model produced the analysis.
# Never guess a model name here — a wrong name is worse than an honest blank,
# because the entry is a provenance record.
UNKNOWN_MODEL = 'unknown'

# A codex file can hold many analyzable nodes — a dome script is one file with
# 36 beats inside. Each node's analysis is a separate entry in the same module,
# distinguished by scope. Entries written before scopes existed carry no scope
# attribute and are treated as ROOT_SCOPE, so old files keep working untouched.
ROOT_SCOPE = 'root'

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


def analysis_file_id(source_filename: str) -> str:
    """
    Root id for an analysis file, as `<slug>-analysis`.

    The analysis schema constrains this to `^[a-zA-Z0-9_-]+-analysis$`, so a
    manuscript whose filename contains spaces or punctuation — which is most
    of them — cannot contribute its stem verbatim.
    """
    base_name = Path(source_filename).stem.replace('.codex', '')
    slug = re.sub(r'[^A-Za-z0-9_]+', '-', base_name).strip('-')
    return f'{slug or "manuscript"}-analysis'


def create_analysis_file_structure(source_path: Path, source_hash: str) -> Dict:
    """Create initial structure for a new analysis file (Codex V1.3 format)."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    source_filename = os.path.basename(source_path)

    return {
        'metadata': {
            'formatVersion': CURRENT_FORMAT_VERSION,
            'created': now,
            'updated': now
        },
        'id': analysis_file_id(source_filename),
        'type': 'analysis',
        'name': 'Analysis Results',
        'attributes': [
            {'key': 'sourceFile', 'value': source_filename},
            {'key': 'sourceHash', 'value': source_hash}
        ],
        'children': []
    }


def _scope_slug(scope: str) -> str:
    """
    Short token appended to an entry id to keep scoped entries distinct.

    Must satisfy the analysis schema's entry-id pattern, which allows a
    trailing `-[a-z0-9]+` only — hence alphanumerics, no separators.
    """
    slug = re.sub(r'[^A-Za-z0-9]+', '', scope).lower()
    return slug[:24] or ROOT_SCOPE


def create_analysis_entry(
    source_hash: str,
    model: str,
    body: str,
    summary: str = '',
    children: List[Dict] = None,
    tags: List[str] = None,
    entry_attributes: List[Dict] = None,
    scope: str = ROOT_SCOPE,
    scope_name: Optional[str] = None,
    scope_path: Optional[str] = None,
    scope_depth: Optional[int] = None,
    scope_index: Optional[int] = None
) -> Dict:
    """Create a single analysis entry node (Codex V1.3 format)."""
    now = datetime.now(timezone.utc)
    # Timestamps are second-resolution, and a scoped run writes dozens of
    # entries well inside one second — the scope keeps ids distinct.
    entry_id = f"entry-{now.strftime('%Y%m%dT%H%M%SZ')}-{_scope_slug(scope)}"

    entry = {
        'id': entry_id,
        'type': 'analysis-entry',
        'status': 'published',
        'attributes': [
            {'key': 'model', 'value': model},
            {'key': 'sourceHash', 'value': source_hash},
            {'key': 'analysisStatus', 'value': 'current'},
            {'key': 'timestamp', 'value': now.isoformat().replace('+00:00', 'Z')},
            {'key': 'scope', 'value': scope}
        ],
        'body': body
    }

    # Node metadata is meaningless for a whole-file entry.
    if scope != ROOT_SCOPE:
        if scope_name:
            _set_attribute(entry, 'scopeName', scope_name)
        if scope_path:
            _set_attribute(entry, 'scopePath', scope_path)
        if scope_depth is not None:
            _set_attribute(entry, 'scopeDepth', scope_depth)
        if scope_index is not None:
            _set_attribute(entry, 'scopeIndex', scope_index)

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


def resolve_model(
    model: Optional[str] = None,
    analysis_content: Optional[Dict[str, Any]] = None
) -> str:
    """
    Determine which model to record on an analysis entry.

    Precedence: explicit argument, then the payload's own "model" key, then
    the CHAPTERWISE_ANALYSIS_MODEL environment variable, then UNKNOWN_MODEL.
    Blank and whitespace-only values are treated as absent.
    """
    candidates = [
        model,
        (analysis_content or {}).get('model'),
        os.environ.get('CHAPTERWISE_ANALYSIS_MODEL'),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return UNKNOWN_MODEL


def entry_scope(entry: Dict[str, Any]) -> str:
    """
    Scope of an existing entry.

    Entries written before scopes existed have no scope attribute; they were
    whole-file analyses, so they read as ROOT_SCOPE.
    """
    value = _get_attribute(entry, 'scope')
    return value if isinstance(value, str) and value.strip() else ROOT_SCOPE


def _trim_history_per_scope(entries: List[Dict], history_depth: int) -> List[Dict]:
    """
    Keep the newest `history_depth` entries *for each scope*, preserving the
    overall newest-first order.

    Trimming the flat list instead would delete other nodes' analyses: a
    36-beat script writes 37 entries into one module node, and a flat
    `entries[:3]` would keep three of them.
    """
    kept, seen = [], {}
    for entry in entries:
        scope = entry_scope(entry)
        seen[scope] = seen.get(scope, 0) + 1
        if seen[scope] <= history_depth:
            kept.append(entry)
    return kept


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
    model: Optional[str] = None,
    history_depth: int = DEFAULT_HISTORY_DEPTH,
    scope: str = ROOT_SCOPE,
    scope_name: Optional[str] = None,
    scope_path: Optional[str] = None,
    scope_depth: Optional[int] = None,
    scope_index: Optional[int] = None
) -> Path:
    """
    Add analysis result to the .analysis.json file.
    Creates file if doesn't exist, prepends to module's children (history).

    The recorded model is resolved, in order, from: the explicit `model`
    argument, a "model" key in the analysis payload (the agent reporting
    itself), the CHAPTERWISE_ANALYSIS_MODEL environment variable, and
    finally UNKNOWN_MODEL.
    """
    model = resolve_model(model, analysis_content)
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

    # Repair a root id written before the id was slugified. Files created by
    # earlier versions carry the raw filename, spaces and all, which the
    # analysis schema rejects.
    expected_id = analysis_file_id(os.path.basename(source_path))
    if not re.fullmatch(r'[A-Za-z0-9_-]+-analysis', str(data.get('id', ''))):
        data['id'] = expected_id

    # Update root sourceHash attribute
    _set_attribute(data, 'sourceHash', source_hash)

    # Update metadata.updated
    data.setdefault('metadata', {})['updated'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Get or create module node
    module_node = _get_or_create_module(data, module_name)

    # Stale only the scope being rewritten. Other scopes are different nodes,
    # not older versions of this one.
    for entry in module_node.get('children', []):
        if entry_scope(entry) == scope:
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
        entry_attributes=analysis_content.get('attributes', []),
        scope=scope,
        scope_name=scope_name,
        scope_path=scope_path,
        scope_depth=scope_depth,
        scope_index=scope_index
    )

    # Prepend, then trim history per scope. Trimming the flat list would
    # discard other nodes' analyses entirely.
    entries = module_node.setdefault('children', [])
    entries.insert(0, new_entry)
    module_node['children'] = _trim_history_per_scope(entries, history_depth)

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
    argv = sys.argv[1:]

    # Pull flags out before positional parsing.
    FLAGS = ('--model', '--scope', '--scope-name', '--scope-path',
             '--scope-depth', '--scope-index')
    flags = {}
    positional = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        matched = next((f for f in FLAGS if arg == f or arg.startswith(f + '=')), None)
        if matched:
            if arg == matched:
                if i + 1 >= len(argv):
                    logger.error(f"{matched} requires a value")
                    sys.exit(1)
                flags[matched] = argv[i + 1]
                i += 2
            else:
                flags[matched] = arg.split('=', 1)[1]
                i += 1
            continue
        positional.append(arg)
        i += 1

    cli_model = flags.get('--model')

    def _int_flag(name):
        raw = flags.get(name)
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError:
            logger.error(f"{name} must be an integer, got {raw!r}")
            sys.exit(1)

    if len(positional) < 3:
        logger.error("Usage: analysis_writer.py <source_file> <module_name> <analysis_json> [flags]")
        logger.error("       analysis_writer.py <source_file> <module_name> - [flags]  (reads stdin)")
        logger.error("")
        logger.error("Flags: --model NAME")
        logger.error("       --scope root|node:<id>   --scope-name NAME   --scope-path PATH")
        logger.error("       --scope-depth N          --scope-index N")
        logger.error("")
        logger.error("Scope addresses a node inside the source file. Omit it for a")
        logger.error("whole-file analysis. Each scope keeps its own history.")
        logger.error("")
        logger.error("The model is recorded as provenance. Report the model that actually")
        logger.error("produced the analysis — via --model, a \"model\" key in the payload, or")
        logger.error("CHAPTERWISE_ANALYSIS_MODEL. Unreported models are recorded as 'unknown'.")
        sys.exit(1)

    source_path = Path(positional[0])
    module_name = positional[1]

    if positional[2] == '-':
        analysis_json = sys.stdin.read()
    else:
        analysis_json = positional[2]

    analysis_content = json.loads(analysis_json)

    resolved = resolve_model(cli_model, analysis_content)
    if resolved == UNKNOWN_MODEL:
        logger.warning(
            "No model reported — recording 'unknown'. "
            "Pass --model, include a \"model\" key, or set CHAPTERWISE_ANALYSIS_MODEL."
        )

    scope = flags.get('--scope') or ROOT_SCOPE
    output_path = add_analysis_result(
        source_path, module_name, analysis_content,
        model=cli_model,
        scope=scope,
        scope_name=flags.get('--scope-name'),
        scope_path=flags.get('--scope-path'),
        scope_depth=_int_flag('--scope-depth'),
        scope_index=_int_flag('--scope-index'),
    )
    logger.info(f"Written to: {output_path} (model: {resolved}, scope: {scope})")
