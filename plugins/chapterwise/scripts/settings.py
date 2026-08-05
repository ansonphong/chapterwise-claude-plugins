#!/usr/bin/env python3
"""
Project settings — the declared configuration for a Chapterwise project.

    echo '{"path": "."}' | python3 settings.py get
    echo '{"path": ".", "updates": {"analysis": {"report_format": "both"}}}' \
      | python3 settings.py set
    echo '{"source": "chapter.codex.yaml"}' | python3 settings.py resolve
    echo '{}' | python3 settings.py defaults

Settings live in `.chapterwise/settings.json` and answer "what should this
project do by default" — which report format, which folder, how deep. They are
declared once and committed.

That is a different thing from the `*-recipe` folders next to them, which
record what a command *did* on its last run so work is not redone. Settings are
intent; recipes are history. When a recipe from an older version carries
settings-shaped keys, `get` folds them in so nothing is lost.

Resolution order, lowest to highest:

    plugin defaults → .chapterwise/settings.json → command flags

A flag always wins and is never written back on its own — a one-off run should
not silently redefine the project.
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

SETTINGS_DIR = '.chapterwise'
SETTINGS_FILE = 'settings.json'
SETTINGS_VERSION = 1

# Codex, in an `analysis/` folder beside the manuscript. Structured output is
# the better default for a format-native tool: it re-imports, renders in the
# web app, and can be analyzed further. `--report=markdown` is one flag away.
DEFAULTS: Dict[str, Any] = {
    'version': SETTINGS_VERSION,
    'analysis': {
        'report': True,
        'report_format': 'codex',
        'report_dir': 'analysis',
        'depth': 'auto',
    },
}

VALID = {
    'analysis.report_format': ('markdown', 'codex', 'both'),
    'analysis.report': (True, False),
}

# Keys older `analysis-recipe` files used for the same settings.
RECIPE_ALIASES = {
    'report_format': ('analysis', 'report_format'),
    'report_enabled': ('analysis', 'report'),
    'depth': ('analysis', 'depth'),
}


def find_project_root(start: Path) -> Path:
    """
    Walk up for the project root.

    `.chapterwise/` wins because it is the thing this plugin creates. An
    `index.codex.yaml` marks a Chapterwise project that has not been configured
    yet, and `.git` catches a repository that is neither. Failing all three,
    the starting folder is the project — a single loose manuscript still works.
    """
    start = start if start.is_dir() else start.parent
    for candidate in [start, *start.parents]:
        if (candidate / SETTINGS_DIR).is_dir():
            return candidate
        if (candidate / 'index.codex.yaml').exists():
            return candidate
        if (candidate / '.git').exists():
            return candidate
    return start


def settings_path(project_root: Path) -> Path:
    return project_root / SETTINGS_DIR / SETTINGS_FILE


def _merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in (overlay or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None


def _recipe_settings(project_root: Path) -> Dict[str, Any]:
    """Settings-shaped keys left in an older analysis-recipe."""
    recipe = project_root / SETTINGS_DIR / 'analysis-recipe' / 'recipe.yaml'
    if not recipe.exists():
        return {}
    try:
        import yaml
        data = yaml.safe_load(recipe.read_text(encoding='utf-8')) or {}
    except Exception:
        return {}

    found: Dict[str, Any] = {}
    for key, (section, name) in RECIPE_ALIASES.items():
        if key in data and data[key] is not None:
            found.setdefault(section, {})[name] = data[key]
    return found


def validate(settings: Dict[str, Any]) -> list:
    """Return a list of problems. Empty means usable."""
    problems = []
    for dotted, allowed in VALID.items():
        section, key = dotted.split('.')
        if key not in settings.get(section, {}):
            continue
        value = settings[section][key]
        if value not in allowed:
            problems.append(
                f"{dotted}: {value!r} is not one of "
                + ', '.join(repr(a) for a in allowed))
    return problems


def load(path: Path) -> Tuple[Dict[str, Any], Dict[str, str], Path, bool]:
    """
    Effective settings, plus where each value came from.

    The provenance map is what lets a command tell "you configured this" from
    "this is just the default", which is the difference between offering to
    save settings and pestering someone who already has.
    """
    root = find_project_root(Path(path).expanduser().resolve())
    file_path = settings_path(root)

    explicit = _read_json(file_path) if file_path.exists() else None
    inherited = _recipe_settings(root) if explicit is None else {}

    effective = _merge(DEFAULTS, inherited)
    effective = _merge(effective, explicit or {})

    sources: Dict[str, str] = {}
    for section, values in DEFAULTS.items():
        if not isinstance(values, dict):
            continue
        for key in values:
            dotted = f'{section}.{key}'
            if key in (explicit or {}).get(section, {}):
                sources[dotted] = 'settings'
            elif key in inherited.get(section, {}):
                sources[dotted] = 'recipe'
            else:
                sources[dotted] = 'default'

    return effective, sources, file_path, explicit is not None


def resolve_report_dir(source: Path, report_dir: str) -> Path:
    """
    Where a report for `source` belongs.

    Three forms, matching how codex `include` paths already resolve so there is
    one rule to learn rather than two:

      `analysis`, `./analysis`   beside the analyzed file  (the default)
      `/reports`                 from the project root
      `~/Documents/reports`      a literal path on disk

    A leading `/` means the project root, not the filesystem root — same as an
    `include`. Use `~` when you genuinely mean somewhere else on the machine.
    """
    raw = str(report_dir or DEFAULTS['analysis']['report_dir']).strip()

    if raw.startswith('~'):
        return Path(os.path.expanduser(raw))
    if raw.startswith('/'):
        return find_project_root(source) / raw.lstrip('/')
    if raw.startswith('./'):
        raw = raw[2:]
    return source.parent / raw


# ── actions ──────────────────────────────────────────────────────────────────

def action_get(data: Dict[str, Any]) -> Dict[str, Any]:
    effective, sources, file_path, found = load(Path(data.get('path', '.')))
    return {
        'found': found,
        'path': str(file_path),
        'projectRoot': str(file_path.parent.parent),
        'settings': effective,
        'sources': sources,
        'configured': [k for k, v in sources.items() if v != 'default'],
        'problems': validate(effective),
    }


def action_set(data: Dict[str, Any]) -> Dict[str, Any]:
    updates = data.get('updates')
    if not isinstance(updates, dict) or not updates:
        raise ValueError('Missing updates: pass the settings to write')

    root = find_project_root(Path(data.get('path', '.')).expanduser().resolve())
    file_path = settings_path(root)

    current = _read_json(file_path) or {}
    if not current:
        # Fold in anything an older recipe was carrying, so writing settings
        # for the first time does not quietly reset choices already made.
        current = _merge(_recipe_settings(root), {'version': SETTINGS_VERSION})

    merged = _merge(current, updates)
    merged['version'] = SETTINGS_VERSION

    problems = validate(_merge(DEFAULTS, merged))
    if problems:
        raise ValueError('; '.join(problems))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + '\n',
                         encoding='utf-8')
    return {'written': True, 'path': str(file_path), 'settings': merged}


def action_resolve(data: Dict[str, Any]) -> Dict[str, Any]:
    """Everything the analysis path needs for one source file."""
    source = Path(data['source']).expanduser().resolve()
    effective, sources, file_path, found = load(source)
    analysis = effective.get('analysis', {})
    return {
        'found': found,
        'path': str(file_path),
        'source': str(source),
        'report': analysis.get('report', True),
        'report_format': analysis.get('report_format'),
        'report_dir': str(resolve_report_dir(source, analysis.get('report_dir'))),
        'depth': analysis.get('depth'),
        'sources': sources,
    }


def action_defaults(_data: Dict[str, Any]) -> Dict[str, Any]:
    return {'settings': DEFAULTS, 'valid': {k: list(v) for k, v in VALID.items()}}


ACTIONS = {
    'get': action_get,
    'set': action_set,
    'resolve': action_resolve,
    'defaults': action_defaults,
}


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'get'
    if action not in ACTIONS:
        print(json.dumps({'error': f"Unknown action {action!r}. "
                                   f"Use one of: {', '.join(ACTIONS)}"}))
        sys.exit(1)

    try:
        payload = json.loads(sys.stdin.read() or '{}')
    except json.JSONDecodeError as exc:
        print(json.dumps({'error': f'Invalid JSON on stdin: {exc}'}))
        sys.exit(1)

    try:
        print(json.dumps(ACTIONS[action](payload), indent=2, ensure_ascii=False))
    except (KeyError, ValueError, OSError) as exc:
        print(json.dumps({'error': str(exc)}))
        sys.exit(1)
    sys.exit(0)
