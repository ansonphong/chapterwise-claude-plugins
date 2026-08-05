#!/usr/bin/env python3
"""
Assemble a readable report from stored analysis results.

This is a formatter, not an analyst. It never calls a model — it reads the
.analysis.json sibling and re-renders it. Three things follow, all of them
wanted: regenerating costs nothing, the report cannot drift from the stored
results, and switching format is a re-render rather than a re-run.

Entries are stored newest-first and flat. The source tree is walked so the
report comes out in document order — show order, not write order.

    echo '{"source":"show.codex.yaml","module":"immersive_design",
           "format":"markdown"}' | analysis_report.py

Output lands in <source_dir>/analysis/, alongside atlas/ and reader/ — the
convention for deliverables derived from the manuscript, as against
.chapterwise/ which holds machine state and reference inputs.
"""
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))
from codex_scan import ROOT_SCOPE, load_codex, walk  # noqa: E402
from staleness_checker import get_analysis_file_path  # noqa: E402

try:
    import yaml
except ImportError:
    print(json.dumps({'error': 'Missing PyYAML. Install with: pip3 install pyyaml'}))
    sys.exit(1)

try:
    from codex_version import CURRENT_FORMAT_VERSION
except ImportError:
    CURRENT_FORMAT_VERSION = '1.3'

REPORT_DIR = 'analysis'
FORMATS = ('markdown', 'codex')


def attrs_of(node: Dict[str, Any]) -> Dict[str, Any]:
    return {a['key']: a.get('value') for a in node.get('attributes', []) or []
            if isinstance(a, dict) and a.get('key')}


def entry_scope(entry: Dict[str, Any]) -> str:
    value = attrs_of(entry).get('scope')
    return value if isinstance(value, str) and value.strip() else ROOT_SCOPE


def current_entries(analysis: Dict[str, Any], module: str) -> Dict[str, Dict]:
    """Newest current entry per scope, keyed by scope."""
    for child in analysis.get('children', []) or []:
        if child.get('id') == module and child.get('type') == 'analysis-module':
            out: Dict[str, Dict] = {}
            for entry in child.get('children', []) or []:
                if attrs_of(entry).get('analysisStatus') != 'current':
                    continue
                out.setdefault(entry_scope(entry), entry)
            return out
    return {}


def module_display_name(analysis: Dict[str, Any], module: str) -> str:
    for child in analysis.get('children', []) or []:
        if child.get('id') == module:
            return child.get('name') or module.replace('_', ' ').title()
    return module.replace('_', ' ').title()


def ordered_scopes(source_path: Path, entries: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """
    Walk the source tree and pair each node with its entry.

    Order comes from the manuscript, not from the analysis file — that is the
    whole point of re-reading the source here.
    """
    root = load_codex(source_path)
    records = walk(root)
    out = []

    for r in records:
        scope = ROOT_SCOPE if r['depth'] == 0 else (
            f"node:{r['id']}" if r['id'] else None)
        if scope and scope in entries:
            out.append({**r, 'scope': scope, 'entry': entries[scope]})

    # Entries whose node is gone from the source (renamed or deleted) would
    # otherwise vanish silently from the report.
    placed = {o['scope'] for o in out}
    for scope, entry in entries.items():
        if scope not in placed:
            a = attrs_of(entry)
            out.append({
                'scope': scope, 'entry': entry, 'depth': 1, 'index': 0,
                'name': a.get('scopeName') or scope,
                'path': a.get('scopePath') or scope,
                'type': None, 'orphan': True,
            })

    return out


# ── markdown ─────────────────────────────────────────────────────────────────

def render_markdown(ctx: Dict[str, Any]) -> str:
    lines = [
        f"# {ctx['moduleName']} — {ctx['sourceName']}",
        '',
        f"*{ctx['entryCount']} analyses · generated {ctx['generated']} · "
        f"model: {ctx['model']}*",
        '',
    ]

    for item in ctx['items']:
        entry = item['entry']
        if item['scope'] == ROOT_SCOPE:
            lines += ['## Overview', '']
        else:
            heading = '#' * min(item['depth'] + 1, 5)
            label = item['name']
            if item.get('orphan'):
                label += '  *(node no longer in source)*'
            lines += [f"{heading} {label}", '']
            if item.get('path'):
                lines += [f"*{item['path']}*", '']

        if entry.get('summary'):
            lines += [f"**{entry['summary']}**", '']
        if entry.get('body'):
            lines += [str(entry['body']).strip(), '']

        for child in entry.get('children', []) or []:
            content = child.get('content') or child.get('body') or ''
            if child.get('name'):
                sub = '#' * min(item['depth'] + 2, 6)
                lines += [f"{sub} {child['name']}", '']
            if content:
                lines += [str(content).strip(), '']

        metrics = {k: v for k, v in attrs_of(entry).items()
                   if k not in ('model', 'sourceHash', 'analysisStatus', 'timestamp',
                                'scope', 'scopeName', 'scopePath', 'scopeDepth',
                                'scopeIndex')}
        if metrics:
            lines += ['| Metric | Value |', '| --- | --- |']
            lines += [f"| {k} | {v} |" for k, v in metrics.items()]
            lines.append('')

        if entry.get('tags'):
            lines += ['`' + '` `'.join(str(t) for t in entry['tags']) + '`', '']

    return '\n'.join(lines).rstrip() + '\n'


# ── codex ────────────────────────────────────────────────────────────────────

def render_codex(ctx: Dict[str, Any]) -> str:
    """
    Codex V1.3 report. Structure follows commands/format.md — every node carries
    a UUID id, metadata.formatVersion is set, and the tree mirrors the source.
    """
    import uuid

    children = []
    for item in ctx['items']:
        entry = item['entry']
        node = {
            'id': str(uuid.uuid4()),
            'type': 'analysis-section',
            'name': 'Overview' if item['scope'] == ROOT_SCOPE else item['name'],
            'attributes': [
                {'key': 'scope', 'value': item['scope'], 'dataType': 'string'},
            ],
        }
        if item.get('path'):
            node['attributes'].append(
                {'key': 'scopePath', 'value': item['path'], 'dataType': 'string'})
        if item.get('orphan'):
            node['attributes'].append(
                {'key': 'orphan', 'value': True, 'dataType': 'boolean'})
        if entry.get('summary'):
            node['summary'] = entry['summary']
        if entry.get('body'):
            node['body'] = entry['body']
        if entry.get('tags'):
            node['tags'] = list(entry['tags'])

        subs = []
        for child in entry.get('children', []) or []:
            subs.append({
                'id': str(uuid.uuid4()),
                'type': 'analysis-subsection',
                'name': child.get('name') or 'Section',
                'body': child.get('content') or child.get('body') or '',
            })
        if subs:
            node['children'] = subs

        children.append(node)

    doc = {
        'metadata': {
            'formatVersion': CURRENT_FORMAT_VERSION,
            'created': ctx['generatedISO'],
            'updated': ctx['generatedISO'],
        },
        'id': str(uuid.uuid4()),
        'type': 'analysis-report',
        'name': f"{ctx['moduleName']} — {ctx['sourceName']}",
        'summary': (f"{ctx['entryCount']} {ctx['moduleName']} analyses of "
                    f"{ctx['sourceName']}, in document order."),
        'attributes': [
            {'key': 'module', 'value': ctx['module'], 'dataType': 'string'},
            {'key': 'sourceFile', 'value': ctx['sourceFile'], 'dataType': 'string'},
            {'key': 'generated', 'value': ctx['generatedISO'], 'dataType': 'string'},
            {'key': 'model', 'value': ctx['model'], 'dataType': 'string'},
            {'key': 'entryCount', 'value': ctx['entryCount'], 'dataType': 'int'},
        ],
        'children': children,
    }
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)


RENDERERS = {'markdown': render_markdown, 'codex': render_codex}
EXTENSIONS = {'markdown': '.md', 'codex': '.codex.yaml'}


def build(data: Dict[str, Any]) -> Dict[str, Any]:
    source_path = Path(data['source']).expanduser().resolve()
    module = data['module']
    fmt = data.get('format', 'markdown')
    if fmt not in FORMATS:
        raise ValueError(f"Unknown format {fmt!r}. Use one of: {', '.join(FORMATS)}")

    analysis_path = get_analysis_file_path(source_path)
    if not analysis_path.exists():
        raise FileNotFoundError(f"No analysis found for {source_path.name}")

    analysis = json.loads(analysis_path.read_text(encoding='utf-8'))
    entries = current_entries(analysis, module)
    if not entries:
        raise ValueError(
            f"No current {module} results in {analysis_path.name} — run the analysis first")

    items = ordered_scopes(source_path, entries)
    generated = data.get('generated') or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    generated_iso = (data.get('generatedISO')
                     or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))

    models = {attrs_of(i['entry']).get('model') for i in items}
    models.discard(None)

    ctx = {
        'module': module,
        'moduleName': module_display_name(analysis, module),
        'sourceName': source_path.name.split('.codex')[0],
        'sourceFile': source_path.name,
        'entryCount': len(items),
        'generated': generated,
        'generatedISO': generated_iso,
        'model': ', '.join(sorted(models)) or 'unknown',
        'items': items,
    }

    rendered = RENDERERS[fmt](ctx)

    slug = source_path.name.split('.codex')[0].lower().replace(' ', '-')
    slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
    filename = f"{slug}-{module.replace('_', '-')}-{generated}{EXTENSIONS[fmt]}"
    out_path = source_path.parent / REPORT_DIR / filename

    if out_path.exists() and not data.get('force'):
        return {
            'status': 'exists',
            'path': str(out_path),
            'message': f"Report already exists: {out_path}",
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding='utf-8')

    return {
        'status': 'written',
        'path': str(out_path),
        'format': fmt,
        'module': module,
        'entryCount': len(items),
        'scopes': [i['scope'] for i in items],
        'bytes': len(rendered.encode('utf-8')),
    }


if __name__ == '__main__':
    try:
        payload = json.loads(sys.stdin.read() or '{}')
    except json.JSONDecodeError as exc:
        print(json.dumps({'error': f'Invalid JSON on stdin: {exc}'}))
        sys.exit(1)

    for field in ('source', 'module'):
        if not payload.get(field):
            print(json.dumps({'error': f'Missing required field: {field}'}))
            sys.exit(1)

    try:
        result = build(payload)
    except (FileNotFoundError, ValueError) as exc:
        print(json.dumps({'error': str(exc)}))
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result['status'] == 'written' else 2)
