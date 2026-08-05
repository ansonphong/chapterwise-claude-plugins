# Plugin Overview

ChapterWise is a Claude Code plugin (v2.0.0) providing a complete writing toolkit -- manuscript import, AI analysis, story atlas generation, research, and static reader builds. It lives under `plugins/chapterwise/`.

## Manifest

`plugins/chapterwise/.claude-plugin/plugin.json` declares the plugin. A duplicate lives at the repo root `.claude-plugin/plugin.json`. Name: `chapterwise`, author: Anson Phong, license: MIT.

## Directory Structure

```
plugins/chapterwise/
├── .claude-plugin/plugin.json    # Plugin manifest
├── commands/          # 23 slash command files (YAML frontmatter + markdown body)
├── modules/           # 32 analysis modules + _output-format.md partial
├── scripts/           # 26 Python utility scripts (stdin JSON / argparse / library)
├── patterns/          # 7 format converters + common/ utilities
├── templates/         # Reader HTML templates (minimal-reader, academic-reader)
├── references/        # principles.md, language-rules.md, insert reference docs
├── schemas/           # recipe.schema.yaml
└── requirements.txt   # Python deps (pyyaml, optional pymupdf/python-docx/bs4)
schemas/               # Repo-root JSON schemas (codex-v1.3, analysis-v1.3, research-v1.3)
```

## Auto-Discovery

- **Commands** -- any `.md` file in `commands/` with YAML frontmatter (including `triggers:`) is auto-discovered by Claude Code. No manifest registration needed.
- **Modules** -- `module_loader.py` discovers `.md` files from three paths: built-in (`modules/`), user global (`~/.claude/analyze/modules/`), project-local (`.chapterwise/analysis-modules/`). Files starting with `_` are skipped.
- **Converters** -- `patterns/*.py` are invoked by the `/import` command based on format detection by `format_detector.py`.

## Environment

- `${CLAUDE_PLUGIN_ROOT}` resolves to `plugins/chapterwise/` at runtime
- Scripts use stdin JSON / stdout JSON pattern (errors to stderr)
- Requires Python 3.8+ and PyYAML; optional deps for specific formats (PyMuPDF, python-docx, beautifulsoup4)

## Recipe System (Internal)

Recipes track state across multi-step operations (import, analysis, atlas, reader). Stored in `.chapterwise/<type>-recipe/recipe.yaml` in the user's project. The word "recipe" is never exposed to users -- it is an internal implementation detail.

## User Preferences

Per-project preferences stored in `.claude/chapterwise.local.md` (YAML frontmatter + markdown notes) in the user's project. Read at command start; created on first use.
