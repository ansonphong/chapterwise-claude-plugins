# ChapterWise Claude Plugin

Complete writing toolkit for ChapterWise — import any manuscript, run AI analysis, build story atlases, create custom readers. Supports PDF, DOCX, Scrivener, Ulysses, Markdown, and more.

This repository is a **Claude Code plugin marketplace**. The plugin itself lives in
[`plugins/chapterwise/`](plugins/chapterwise); the marketplace manifest at
[`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) points at it.

## Installation

Add the marketplace, then install the plugin from it — two steps:

```
/plugin marketplace add ansonphong/chapterwise-plugins
/plugin install chapterwise@chapterwise-plugins
```

Or from your shell:

```bash
claude plugin marketplace add ansonphong/chapterwise-plugins
claude plugin install chapterwise@chapterwise-plugins
```

Restart Claude Code (or start a new session) to load the commands.

### Managing the install

```
/plugin disable chapterwise@chapterwise-plugins
/plugin enable  chapterwise@chapterwise-plugins
/plugin update  chapterwise@chapterwise-plugins
```

### Local Development

Point `--plugin-dir` at the **plugin** directory, not the repo root:

```bash
claude --plugin-dir /path/to/chapterwise-plugins/plugins/chapterwise
```

## Commands

24 slash commands. When the plugin is installed alongside others, use the namespaced
form (`/chapterwise:import`) to avoid trigger collisions; the bare form works when
there is no conflict.

### Core Pipeline

| Command | Description |
|---------|-------------|
| `/import` | Import manuscripts and content into ChapterWise |
| `/analysis` | Analyze Codex files with intelligent module selection |
| `/atlas` | Build a story atlas from your manuscript |
| `/reader` | Build a static HTML reader for your project |
| `/research` | Research any topic and generate structured codex reference files |
| `/research-deep` | Deep research — generate a multi-document compendium on any topic |

### Manuscript Tools

| Command | Description |
|---------|-------------|
| `/insert` | Insert notes into Codex manuscripts by location |
| `/status` | Show project status and staleness overview |
| `/pipeline` | Run full pipeline: Import, Analysis, Atlas, Reader |
| `/index` | Generate an index.codex.yaml for your project |

### Format Tools

| Command | Description |
|---------|-------------|
| `/format` | Format content as Chapterwise Codex |
| `/explode` | Split a codex file into separate child files |
| `/implode` | Merge separate codex files back into one document |
| `/markdown` | Create Markdown files with ChapterWise frontmatter |
| `/convert-to-codex` | Convert Markdown files to Codex YAML format |
| `/convert-to-markdown` | Convert Codex files to Markdown with frontmatter |

### Utilities

| Command | Description |
|---------|-------------|
| `/generate-tags` | Auto-generate tags from content in codex or markdown files |
| `/update-word-count` | Update word count metadata in codex files |
| `/format-folder` | Auto-fix all codex files in a folder |
| `/format-regen-ids` | Regenerate all IDs in a codex file |
| `/diagram` | Create Mermaid diagrams in Codex format |
| `/spreadsheet` | Create spreadsheets in Codex format |

### Specialized

| Command | Description |
|---------|-------------|
| `/import-scrivener` | Import a Scrivener project into ChapterWise |
| `/feedback-inbox` | Review and work on user feedback from the database |

## What's Inside

| Component | Count | Location |
|-----------|-------|----------|
| Slash commands | 24 | `plugins/chapterwise/commands/` |
| Analysis modules | 33 | `plugins/chapterwise/modules/` |
| Python scripts | 28 | `plugins/chapterwise/scripts/` |
| Format converters | 7 | `plugins/chapterwise/patterns/` |
| Reader templates | 2 | `plugins/chapterwise/templates/` |
| Codex schemas | 3 | `schemas/` |

Converters cover PDF, DOCX, HTML, plaintext, Markdown folders, Scrivener, and Ulysses.

## Codex Format Overview

Every Codex file has this structure:

```yaml
metadata:
  formatVersion: "1.3"
  documentVersion: "1.0.0"

id: "unique-uuid"
type: "any-type"  # character, location, chapter, recipe, meeting, etc.
name: "Display Name"
summary: "One-line description"
status: draft

body: |
  Extended content in Markdown...

attributes:
  - key: some_key
    value: "some value"
    dataType: string

children:
  - id: "child-uuid"
    type: "child-type"
    name: "Child Name"
    # ...same structure recursively
```

Schemas live in [`schemas/`](schemas): `codex-v1.3.schema.json`,
`analysis-v1.3.schema.json`, `research-v1.3.schema.json`.

## Requirements

- Python 3.8+
- PyYAML (`pip install pyyaml`)
- Optional, per source format: PyMuPDF (PDF), python-docx (DOCX), beautifulsoup4 (HTML)

## Development

```bash
python3 -m pytest tests/ -v
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Links

- [ChapterWise App](https://chapterwise.app)
- [Plugin Repository](https://github.com/ansonphong/chapterwise-plugins)
- [Changelog](CHANGELOG.md)
