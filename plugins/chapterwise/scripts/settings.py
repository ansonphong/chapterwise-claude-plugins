#!/usr/bin/env python3
"""
Project settings — the declared configuration for a Chapterwise project.

    echo '{"path": "."}' | python3 settings.py get
    echo '{"path": ".", "updates": {"analysis": {"report_format": "both"}}}' \
      | python3 settings.py set
    echo '{"source": "chapter.codex.yaml"}' | python3 settings.py resolve
    echo '{"path": ".", "section": "reader"}' | python3 settings.py resolve
    echo '{}' | python3 settings.py defaults

Settings live in `.chapterwise/settings.json` and answer "what should this
project do by default" — which report format, which folder, which reader
template. One file, one section per command (`analysis`, `atlas`, `reader`), so
there is one place to look rather than one per command. Declared once and
committed.

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

# Analysis reports default to codex in an `analysis/` folder beside the
# manuscript. Structured output is the better default for a format-native tool:
# it re-imports, renders in the web app, and can be analyzed further.
# `--report=markdown` is one flag away.
DEFAULTS: Dict[str, Any] = {
    'version': SETTINGS_VERSION,
    'analysis': {
        'report': True,
        'report_format': 'codex',
        'output_dir': 'analysis',
        'depth': 'auto',
    },
    'atlas': {
        'output_dir': 'atlas',
        'sections': ['characters', 'timeline', 'themes', 'plot-structure',
                     'locations', 'relationships'],
    },
    'reader': {
        'output_dir': 'reader',
        'template': 'minimal',
        'theme': 'light',
    },
    'research': {
        'output_dir': 'research',
        'format': 'codex-md',
        'depth': 'standard',
    },
}

VALID = {
    'analysis.report_format': ('markdown', 'codex', 'both'),
    'analysis.report': (True, False),
    'reader.template': ('minimal', 'academic', 'custom'),
    'reader.theme': ('light', 'dark'),
    'research.format': ('codex-md', 'codex-json'),
    'research.depth': ('standard', 'deep'),
}

# Every section has an `output_dir`, resolved by the same rules. The only thing
# that differs is what "relative" is relative to, and that follows from what the
# artifact belongs to: an analysis report describes one manuscript and sits
# beside it; an atlas, a reader and a research file belong to the project.
#
# Whether output is visible or tucked into `.chapterwise/` is a value, not a
# rule — set `output_dir` to `.chapterwise/research` and it is hidden; set it to
# `research` and it is not. That choice is the user's, per section.
OUTPUT_DIRS = {
    'analysis': ('output_dir', 'file'),
    'atlas': ('output_dir', 'project'),
    'reader': ('output_dir', 'project'),
    'research': ('output_dir', 'project'),
}

# Renamed for consistency: every section says `output_dir`. A settings file
# written before that is migrated on read and normalised on the next write.
LEGACY_KEYS = {'analysis': {'report_dir': 'output_dir'}}

# Settings-shaped keys that earlier versions left in `*-recipe/recipe.yaml`.
# Dotted keys read into the recipe's nested blocks.
RECIPE_INHERITANCE = {
    'analysis': ('analysis-recipe', {
        'report_format': 'report_format',
        'report_enabled': 'report',
        'depth': 'depth',
    }),
    'atlas': ('atlas-recipe', {
        'sections': 'sections',
    }),
    'reader': ('reader-recipe', {
        'design.template': 'template',
        'design.theme': 'theme',
    }),
}

# `/research` kept its preferences in `.claude/chapterwise.local.md`, a second
# configuration surface in a different format that predated this file. It is
# retired: research is a section here like everything else.


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


def _dig(data: Dict[str, Any], dotted: str) -> Any:
    for part in dotted.split('.'):
        if not isinstance(data, dict) or part not in data:
            return None
        data = data[part]
    return data


def _recipe_settings(project_root: Path) -> Dict[str, Any]:
    """Settings-shaped keys left in older `*-recipe` folders."""
    found: Dict[str, Any] = {}
    for section, (folder, aliases) in RECIPE_INHERITANCE.items():
        recipe = project_root / SETTINGS_DIR / folder / 'recipe.yaml'
        if not recipe.exists():
            continue
        try:
            import yaml
            data = yaml.safe_load(recipe.read_text(encoding='utf-8')) or {}
        except Exception:
            continue
        for dotted, name in aliases.items():
            value = _dig(data, dotted)
            if value is not None:
                found.setdefault(section, {})[name] = value
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
    if explicit is not None:
        explicit = _migrate_legacy_keys(explicit)
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


def _migrate_legacy_keys(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Rename keys an earlier version wrote, so nothing is silently ignored."""
    for section, renames in LEGACY_KEYS.items():
        block = settings.get(section)
        if not isinstance(block, dict):
            continue
        for old, new in renames.items():
            if old in block:
                block.setdefault(new, block.pop(old))
    return settings


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
    raw = str(report_dir or DEFAULTS['analysis']['output_dir']).strip()
    return _resolve(source, raw, 'file')


def resolve_project_dir(path: Path, output_dir: str, default: str = '') -> Path:
    """
    Where a whole-project artifact belongs — an atlas, a reader.

    Same three forms as `resolve_report_dir`, except a bare name is relative to
    the project root rather than to any one file, because these are built once
    for the project rather than per manuscript.
    """
    return _resolve(path, str(output_dir or default).strip(), 'project')


def _resolve(path: Path, raw: str, relative_to: str) -> Path:
    path = Path(path).expanduser().resolve()
    if raw.startswith('~'):
        return Path(os.path.expanduser(raw))
    if raw.startswith('/'):
        return find_project_root(path) / raw.lstrip('/')
    if raw.startswith('./'):
        raw = raw[2:]
    if relative_to == 'project':
        return find_project_root(path) / raw
    return (path if path.is_dir() else path.parent) / raw


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

    current = _migrate_legacy_keys(_read_json(file_path) or {})
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
    """
    Everything one command needs, with paths already turned into real paths.

    `section` selects which command is asking — `analysis` (the default),
    `atlas`, or `reader`. `source` is a manuscript for analysis and may be any
    path inside the project for the others.
    """
    section = data.get('section', 'analysis')
    if section not in OUTPUT_DIRS:
        raise ValueError(f"Unknown section {section!r}. "
                         f"Use one of: {', '.join(OUTPUT_DIRS)}")

    source = Path(data.get('source') or data.get('path') or '.').expanduser().resolve()
    effective, sources, file_path, found = load(source)
    values = dict(effective.get(section, {}))

    dir_key, relative_to = OUTPUT_DIRS[section]
    resolver = resolve_report_dir if relative_to == 'file' else resolve_project_dir
    values[dir_key] = str(resolver(source, values.get(dir_key)))

    return {
        'found': found,
        'section': section,
        'path': str(file_path),
        'source': str(source),
        'projectRoot': str(find_project_root(source)),
        'sources': {k: v for k, v in sources.items() if k.startswith(f'{section}.')},
        'configured': [k for k, v in sources.items()
                       if v != 'default' and k.startswith(f'{section}.')],
        **values,
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
