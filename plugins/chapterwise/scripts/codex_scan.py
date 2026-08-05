#!/usr/bin/env python3
"""
Structural scan and node resolution for codex files.

Analysis needs to know the shape of a manuscript before it can ask a useful
question about it. This reads the tree — depth, counts, types, where content
actually sits — without pulling whole chapters into a response, so it stays
cheap on a 300-chapter novel.

Two actions:

    scan   tree shape plus a suggested resolution and the reason for it
    nodes  resolve a --depth selector to the concrete nodes to analyze

Both take stdin JSON, per .claude/rules/scripts.md Pattern A.

    echo '{"path":"show.codex.yaml"}' | codex_scan.py scan
    echo '{"path":"show.codex.yaml","depth":"root,leaf"}' | codex_scan.py nodes
"""
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError:
    print(json.dumps({'error': 'Missing PyYAML. Install with: pip3 install pyyaml'}))
    sys.exit(1)

ROOT_SCOPE = 'root'
PATH_SEPARATOR = ' › '  # ›

# `auto` will not propose a level with fewer nodes than this (not worth the
# ceremony) or more than this (a runaway pass count the user did not ask for).
AUTO_MIN_NODES = 2
AUTO_MAX_NODES = 200


def load_codex(path: Path) -> Dict[str, Any]:
    """Load a codex file. Handles .codex.yaml, .codex.json and .codex.md."""
    text = path.read_text(encoding='utf-8')
    suffix = path.name.lower()

    if suffix.endswith('.json'):
        return json.loads(text)

    if suffix.endswith('.md'):
        # Codex Lite: YAML frontmatter plus a markdown body.
        if text.startswith('---'):
            _, fm, body = text.split('---', 2)
            data = yaml.safe_load(fm) or {}
            data.setdefault('body', body.strip())
            data.setdefault('name', path.stem)
            return data
        return {'name': path.stem, 'body': text, 'type': 'document'}

    return yaml.safe_load(text)


def node_content_size(node: Dict[str, Any]) -> int:
    """
    Characters of analyzable content on a node.

    Counts `body` and the `content` block array. Both matter: a dome script's
    beats have an empty body and carry everything in `content` (visual, cues,
    experience), so counting body alone would report them as empty.
    """
    total = len(node.get('body') or '')
    total += len(node.get('summary') or '')

    for block in node.get('content') or []:
        if isinstance(block, dict):
            total += len(str(block.get('value') or ''))
        elif isinstance(block, str):
            total += len(block)

    return total


def node_content(node: Dict[str, Any]) -> str:
    """Analyzable text of a single node, without its children."""
    parts = []
    if node.get('summary'):
        parts.append(f"Summary: {node['summary']}")
    if node.get('body'):
        parts.append(str(node['body']))

    for block in node.get('content') or []:
        if isinstance(block, dict):
            label = block.get('name') or block.get('key') or 'Content'
            parts.append(f"{label}: {block.get('value', '')}")
        elif isinstance(block, str):
            parts.append(block)

    for attr in node.get('attributes') or []:
        if isinstance(attr, dict) and attr.get('key'):
            parts.append(f"{attr.get('name') or attr['key']}: {attr.get('value')}")

    return '\n\n'.join(str(p) for p in parts if p)


def walk(node: Dict[str, Any], depth: int = 0, trail: Optional[List[str]] = None,
         index: int = 0) -> List[Dict[str, Any]]:
    """Flatten the tree, in document order, recording depth and path."""
    trail = trail or []
    name = str(node.get('name') or node.get('title') or node.get('id') or 'Untitled')
    here = trail + [name]

    record = {
        'node': node,
        'id': node.get('id'),
        'name': name,
        'type': node.get('type'),
        'depth': depth,
        'index': index,
        'path': PATH_SEPARATOR.join(here),
        'childCount': len(node.get('children') or []),
        'contentSize': node_content_size(node),
    }

    out = [record]
    for i, child in enumerate(node.get('children') or []):
        out.extend(walk(child, depth + 1, here, i))
    return out


def summarize(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per-depth summary of the tree."""
    levels: Dict[int, Dict[str, Any]] = {}
    for r in records:
        level = levels.setdefault(r['depth'], {
            'depth': r['depth'], 'count': 0, 'types': set(),
            'withContent': 0, 'leaves': 0,
        })
        level['count'] += 1
        if r['type']:
            level['types'].add(r['type'])
        if r['contentSize'] > 0:
            level['withContent'] += 1
        if r['childCount'] == 0:
            level['leaves'] += 1

    return [
        {**lv, 'types': sorted(lv['types'])}
        for lv in (levels[d] for d in sorted(levels))
    ]


def suggest_depth(levels: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Propose a resolution: the deepest level where every node bears content and
    the count is workable. Ties break shallower — a smaller proposal is easier
    to say yes to than an unexpected 200-pass run.
    """
    candidates = [
        lv for lv in levels
        if lv['depth'] > 0
        and lv['count'] == lv['withContent']
        and AUTO_MIN_NODES <= lv['count'] <= AUTO_MAX_NODES
    ]

    if not candidates:
        return {
            'suggestedDepth': ROOT_SCOPE,
            'suggestedReason': 'no level below the root has content on every node',
        }

    best = max(candidates, key=lambda lv: lv['depth'])
    types = '/'.join(best['types']) or 'node'
    return {
        'suggestedDepth': best['depth'],
        'suggestedReason': (
            f"{best['count']} content-bearing {types} nodes at depth {best['depth']}"
        ),
    }


def root_attributes(root: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for attr in root.get('attributes') or []:
        if isinstance(attr, dict) and attr.get('key'):
            out[attr['key']] = attr.get('value')
    return out


def scan(data: Dict[str, Any]) -> Dict[str, Any]:
    path = Path(data['path']).expanduser()
    root = load_codex(path)
    records = walk(root)
    levels = summarize(records)
    leaves = [r for r in records if r['childCount'] == 0]
    leaf_depths = sorted({r['depth'] for r in leaves})

    result = {
        'path': str(path),
        'root': {
            'id': root.get('id'),
            'type': root.get('type'),
            'name': records[0]['name'],
        },
        'totalNodes': len(records),
        'maxDepth': max(r['depth'] for r in records),
        'levels': levels,
        'leafCount': len(leaves),
        'leafDepth': leaf_depths[0] if len(leaf_depths) == 1 else leaf_depths,
        'attributes': root_attributes(root),
    }
    result.update(suggest_depth(levels))
    return result


def parse_depth(selector: Any, levels: List[Dict[str, Any]],
                suggested: Any) -> List[Any]:
    """
    Normalize a --depth selector to a list of tokens.

    Accepts `root`, an integer, `leaf`, `auto`, `all`, and comma lists such as
    `root,leaf` — whole-show synthesis plus every scene.
    """
    if selector is None:
        selector = 'auto'

    tokens = [t.strip() for t in str(selector).split(',') if t.strip()]
    resolved: List[Any] = []

    for token in tokens:
        low = token.lower()
        if low == 'auto':
            resolved.append(ROOT_SCOPE if suggested == ROOT_SCOPE else int(suggested))
        elif low == 'all':
            resolved.append(ROOT_SCOPE)
            resolved.append('leaf')
        elif low in (ROOT_SCOPE, 'leaf'):
            resolved.append(low)
        else:
            try:
                resolved.append(int(low))
            except ValueError:
                raise ValueError(
                    f"unrecognized depth {token!r} — "
                    "expected root, an integer, leaf, auto, all, or a comma list"
                )

    # Preserve order, drop repeats.
    seen, out = set(), []
    for r in resolved:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def nodes(data: Dict[str, Any]) -> Dict[str, Any]:
    path = Path(data['path']).expanduser()
    root = load_codex(path)
    records = walk(root)
    levels = summarize(records)
    suggested = suggest_depth(levels)['suggestedDepth']
    tokens = parse_depth(data.get('depth'), levels, suggested)

    selected: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for token in tokens:
        if token == ROOT_SCOPE:
            matches = [records[0]]
        elif token == 'leaf':
            matches = [r for r in records if r['childCount'] == 0]
        else:
            matches = [r for r in records if r['depth'] == token]
        selected.extend(matches)

    # A node can be picked twice — `leaf` and an explicit depth can overlap.
    # Keep document order, first occurrence wins.
    deduped, seen = [], set()
    for r in sorted(selected, key=lambda r: records.index(r)):
        key = id(r['node'])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    out = []
    for position, r in enumerate(deduped):
        is_root = r['depth'] == 0
        if is_root:
            scope = ROOT_SCOPE
        elif r['id']:
            scope = f"node:{r['id']}"
        else:
            # An id-less node is an auto-fixer gap. Address it structurally
            # rather than silently skipping it, and say so.
            structural = f"{r['depth']}.{r['index']}"
            scope = f"node@{structural}"
            warnings.append(f"node {r['path']!r} has no id — addressed as {scope}")

        out.append({
            'scope': scope,
            'id': r['id'],
            'name': r['name'],
            'type': r['type'],
            'path': r['path'],
            'depth': r['depth'],
            'index': position,
            'contentSize': r['contentSize'],
            'content': node_content(r['node']),
        })

    for w in warnings:
        logger.warning(w)

    return {
        'path': str(path),
        'depth': data.get('depth', 'auto'),
        'resolved': [str(t) for t in tokens],
        'count': len(out),
        'warnings': warnings,
        'nodes': out,
    }


ACTIONS = {'scan': scan, 'nodes': nodes}


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'scan'

    if action not in ACTIONS:
        print(json.dumps({'error': f"Unknown action {action!r}. Use: {', '.join(ACTIONS)}"}))
        sys.exit(1)

    try:
        payload = json.loads(sys.stdin.read() or '{}')
    except json.JSONDecodeError as exc:
        print(json.dumps({'error': f'Invalid JSON on stdin: {exc}'}))
        sys.exit(1)

    if not payload.get('path'):
        print(json.dumps({'error': 'Missing required field: path'}))
        sys.exit(1)

    try:
        print(json.dumps(ACTIONS[action](payload), indent=2, ensure_ascii=False, default=str))
    except FileNotFoundError:
        print(json.dumps({'error': f"File not found: {payload['path']}"}))
        sys.exit(1)
    except ValueError as exc:
        print(json.dumps({'error': str(exc)}))
        sys.exit(1)
