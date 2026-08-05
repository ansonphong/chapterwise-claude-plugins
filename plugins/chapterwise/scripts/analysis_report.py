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

Output lands in the resolved `analysis.output_dir` — by default `analysis/`
beside the manuscript. Every command that writes output has the same setting
and resolves it by the same rules; whether output is visible or tucked into
.chapterwise/ is the user's choice, per section.
"""
import hashlib
import json
import logging
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

# The codex report is produced through the plugin's own format machinery rather
# than beside it — see render_codex. Both are optional so the markdown path
# still works in a stripped-down checkout.
try:
    from auto_fixer import CodexAutoFixer
except ImportError:  # pragma: no cover - only when the fixer is absent
    CodexAutoFixer = None

try:
    from schema_validator import validate_codex
except ImportError:  # pragma: no cover - only when jsonschema is absent
    validate_codex = None

from settings import DEFAULTS as SETTING_DEFAULTS  # noqa: E402
from settings import load as load_settings  # noqa: E402
from settings import resolve_file_dir  # noqa: E402

REPORT_DIR = SETTING_DEFAULTS['analysis']['output_dir']
RENDERABLE = ('markdown', 'codex')
FORMATS = RENDERABLE + ('both',)


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

def _opens_with_heading(content: str, name: str) -> bool:
    """True when content's first line is a markdown heading naming this section."""
    first = (content.lstrip().split('\n', 1)[0] if content else '').strip()
    if not first.startswith('#'):
        return False
    return first.lstrip('#').strip().casefold() == name.strip().casefold()


def report_slug(source_filename: str) -> str:
    """
    Filename-safe slug for a report, from the manuscript's filename.

    Runs of punctuation collapse to a single hyphen, the same way
    `analysis_writer.analysis_file_id` does — a manuscript called
    "Chrysalis - Dome Show Script" is one hyphen, not three. The two functions
    slug the same input for different files and had drifted apart.
    """
    base = source_filename.split('.codex')[0].lower()
    return re.sub(r'[^a-z0-9_]+', '-', base).strip('-') or 'manuscript'


def stable_id(*parts: str) -> str:
    """
    Deterministic, v4-shaped UUID for a report node.

    Two constraints meet here. Regenerating a report from unchanged results
    must produce an identical file, so ids are derived from what the node *is*
    rather than minted fresh. And the auto-fixer — the format authority this
    script defers to — treats anything that is not v4-shaped as a broken id and
    replaces it. A plain uuid5 satisfies the first and fails the second, so the
    digest is stamped with the v4 version and variant bits.
    """
    digest = hashlib.sha1(
        ('chapterwise:analysis-report:' + '|'.join(parts)).encode('utf-8')).digest()
    raw = bytearray(digest[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40   # version 4
    raw[8] = (raw[8] & 0x3F) | 0x80   # RFC 4122 variant
    return str(uuid.UUID(bytes=bytes(raw)))


def _yaml_scalar(value: str) -> str:
    """Quote a frontmatter scalar safely."""
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


def render_markdown(ctx: Dict[str, Any]) -> str:
    # Codex Lite frontmatter — makes the report a valid codex document rather
    # than loose markdown, so the rest of the toolchain can read it back.
    title = f"{ctx['moduleName']} — {ctx['sourceName']}"
    body_lines = [
        '',
        f"# {title}",
        '',
        f"*{ctx['entryCount']} analyses · generated {ctx['generated']} · "
        f"model: {ctx['model']}*",
        '',
    ]

    lines = body_lines
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
            content = str(child.get('content') or child.get('body') or '').strip()
            # Modules commonly open a child with its own heading. Emitting the
            # child name as well would print the title twice.
            if child.get('name') and not _opens_with_heading(content, child['name']):
                sub = '#' * min(item['depth'] + 2, 6)
                lines += [f"{sub} {child['name']}", '']
            if content:
                lines += [content, '']

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

    body = '\n'.join(lines).rstrip() + '\n'

    # Frontmatter last, so word_count reflects the body it describes.
    frontmatter = [
        '---',
        f"id: {stable_id(ctx['sourceFile'], ctx['module'], ctx['generated'])}",
        f"name: {_yaml_scalar(title)}",
        'type: analysis-report',
        f"summary: {_yaml_scalar(ctx['summary'])}",
        f"module: {ctx['module']}",
        f"source_file: {_yaml_scalar(ctx['sourceFile'])}",
        f"generated: {ctx['generatedISO']}",
        f"model: {_yaml_scalar(ctx['model'])}",
        f"entry_count: {ctx['entryCount']}",
        f"word_count: {len(body.split())}",
        'status: published',
        f"tags: analysis, {ctx['module'].replace('_', '-')}, report",
        '---',
    ]
    return '\n'.join(frontmatter) + body


# ── codex ────────────────────────────────────────────────────────────────────

class _BlockDumper(yaml.SafeDumper):
    """Literal block scalars for long text — the shape /chapterwise:format writes."""


def _block_str(dumper, data):
    if '\n' in data or len(data) > 80:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


_BlockDumper.add_representer(str, _block_str)


def render_codex(ctx: Dict[str, Any]) -> str:
    """
    Codex V1.3 report, emitted through the plugin's own format machinery.

    The document is assembled here and then handed to `CodexAutoFixer` — the
    same engine behind `/chapterwise:format` — rather than being hand-rolled
    all the way to disk. That is deliberate: a generator that imitates its own
    format command is how the two drift apart. Attribute keys are lowercase
    because the Codex V1.3 schema requires it; the fixer would otherwise
    rewrite them.
    """
    children = []
    for item in ctx['items']:
        entry = item['entry']
        node = {
            'id': stable_id(ctx['sourceFile'], ctx['module'], item['scope']),
            'type': 'analysis-section',
            'name': 'Overview' if item['scope'] == ROOT_SCOPE else item['name'],
            'attributes': [
                {'key': 'scope', 'value': item['scope'], 'dataType': 'string'},
            ],
        }
        if item.get('path'):
            node['attributes'].append(
                {'key': 'scope_path', 'value': item['path'], 'dataType': 'string'})
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
                'id': stable_id(ctx['sourceFile'], ctx['module'], item['scope'],
                                child.get('name') or str(len(subs))),
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
        'id': stable_id(ctx['sourceFile'], ctx['module'], ctx['generated']),
        'type': 'analysis-report',
        'name': f"{ctx['moduleName']} — {ctx['sourceName']}",
        'summary': ctx['summary'],
        'attributes': [
            {'key': 'module', 'value': ctx['module'], 'dataType': 'string'},
            {'key': 'source_file', 'value': ctx['sourceFile'], 'dataType': 'string'},
            {'key': 'generated', 'value': ctx['generatedISO'], 'dataType': 'string'},
            {'key': 'model', 'value': ctx['model'], 'dataType': 'string'},
            {'key': 'entry_count', 'value': ctx['entryCount'], 'dataType': 'int'},
        ],
        'children': children,
    }

    if CodexAutoFixer is not None:
        doc, fixes = CodexAutoFixer().auto_fix_codex(None, doc)
        for fix in fixes:
            logger.info('format: %s', fix)

    return yaml.dump(doc, Dumper=_BlockDumper, sort_keys=False,
                     allow_unicode=True, width=100, default_flow_style=False)


RENDERERS = {'markdown': render_markdown, 'codex': render_codex}
EXTENSIONS = {'markdown': '.md', 'codex': '.codex.yaml'}

# Codex Lite requires these in frontmatter; the codex path is schema-checked.
LITE_REQUIRED = ('id', 'type', 'name')


def validate_output(fmt: str, rendered: str) -> Tuple[bool, List[str]]:
    """
    Check a rendered report against the format it claims to be.

    A report is a codex document, so it is validated like one. Skipping this
    is what let the codex renderer ship attribute keys the V1.3 schema
    forbids — nothing downstream was ever asked to read it back.
    """
    if fmt == 'codex':
        if validate_codex is None:
            return True, []
        try:
            return validate_codex(yaml.safe_load(rendered))
        except yaml.YAMLError as exc:
            return False, [f'Report is not parseable YAML: {exc}']

    if not rendered.startswith('---\n'):
        return False, ['Codex Lite report is missing its frontmatter']
    try:
        frontmatter = yaml.safe_load(rendered.split('---', 2)[1]) or {}
    except yaml.YAMLError as exc:
        return False, [f'Frontmatter is not parseable YAML: {exc}']
    missing = [f for f in LITE_REQUIRED if not frontmatter.get(f)]
    return (not missing), [f'Frontmatter is missing {f}' for f in missing]


def build(data: Dict[str, Any]) -> Dict[str, Any]:
    source_path = Path(data['source']).expanduser().resolve()
    module = data['module']

    # Explicit payload beats project settings beats plugin defaults. Nothing
    # here writes settings back — a one-off `format` should not redefine the
    # project. See settings.py.
    project, _sources, settings_file, configured = load_settings(source_path)
    analysis_settings = project.get('analysis', {})

    fmt = data.get('format') or analysis_settings.get('report_format')
    if fmt not in FORMATS:
        raise ValueError(f"Unknown format {fmt!r}. Use one of: {', '.join(FORMATS)}")

    # `report_dir` was the payload key before every section standardised on
    # `output_dir`; still accepted so an older caller is not silently ignored.
    output_dir = resolve_file_dir(
        source_path,
        data.get('output_dir') or data.get('report_dir')
        or analysis_settings.get('output_dir'))

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
        'summary': (f"{len(items)} {module_display_name(analysis, module)} analyses of "
                    f"{source_path.name}, in document order."),
        'moduleName': module_display_name(analysis, module),
        'sourceName': source_path.name.split('.codex')[0],
        'sourceFile': source_path.name,
        'entryCount': len(items),
        'generated': generated,
        'generatedISO': generated_iso,
        'model': ', '.join(sorted(models)) or 'unknown',
        'items': items,
    }

    stem = f"{report_slug(source_path.name)}-{module.replace('_', '-')}-{generated}"

    wanted = RENDERABLE if fmt == 'both' else (fmt,)
    targets = [(f, output_dir / f"{stem}{EXTENSIONS[f]}") for f in wanted]

    collisions = [p for _, p in targets if p.exists()]
    if collisions and not data.get('force'):
        return {
            'status': 'exists',
            'path': str(collisions[0]),
            'paths': [str(p) for p in collisions],
            'message': ('Report already exists: '
                        + ', '.join(str(p) for p in collisions)),
        }

    outputs = []
    for one_format, out_path in targets:
        rendered = RENDERERS[one_format](ctx)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding='utf-8')
        valid, issues = validate_output(one_format, rendered)
        outputs.append({
            'format': one_format,
            'path': str(out_path),
            'bytes': len(rendered.encode('utf-8')),
            'valid': valid,
            'issues': issues,
        })
        for issue in issues:
            logger.warning('%s: %s', out_path.name, issue)

    return {
        'status': 'written',
        'path': outputs[0]['path'],
        'paths': [o['path'] for o in outputs],
        'format': fmt,
        'module': module,
        'entryCount': len(items),
        'scopes': [i['scope'] for i in items],
        'bytes': outputs[0]['bytes'],
        'valid': all(o['valid'] for o in outputs),
        'issues': [f"{o['format']}: {i}" for o in outputs for i in o['issues']],
        'outputs': outputs,
        'outputDir': str(output_dir),
        'settingsConfigured': configured,
        'settingsPath': str(settings_file),
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
