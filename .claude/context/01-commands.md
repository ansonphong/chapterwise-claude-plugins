# Slash Commands (23 commands)

All commands are markdown files in `commands/` with YAML frontmatter defining `description`, `triggers`, `allowed-tools`, and `argument-hint`. Auto-discovered by Claude Code.

## Core Pipeline

| Command | Triggers | Description |
|---------|----------|-------------|
| `/import` | import, import pdf/docx/scrivener/ulysses/manuscript/book/project | Import manuscripts from any format into codex |
| `/import-scrivener` | scrivener import, scrivener to codex, convert scrivener, import .scriv | Scrivener-specific import with full .scriv parsing |
| `/analysis` | analysis, analyze, analysis summary/characters/list/help | Run AI analysis with 32 modules, course picker, genre-aware planning |
| `/atlas` | atlas, build/generate/story/character/update atlas | Build cross-chapter story atlas from manuscript |
| `/reader` | reader, build reader, codex reader | Generate static HTML reader from project |
| `/pipeline` | pipeline, run/full pipeline | Run full chain: import, analysis, atlas, reader |
| `/status` | status, chapterwise/project status | Show project status and staleness dashboard |

## Research

| Command | Triggers | Description |
|---------|----------|-------------|
| `/research` | research | Research any topic, generate structured codex reference files |
| `/research:deep` | research:deep | Deep multi-document research compendium with web search |

## Insert

| Command | Triggers | Description |
|---------|----------|-------------|
| `/insert` | insert into codex, insert note/scene, add to manuscript, batch insert | Insert notes by semantic location with review markers |

## Codex Utilities

| Command | Triggers | Description |
|---------|----------|-------------|
| `/format` | codex format/yaml, fix codex, auto-fix | Format content as Codex V1.3 YAML |
| `/format-folder` | fix/autofix/format codex folder, batch fix | Auto-fix all codex files in a folder |
| `/format-regen-ids` | regenerate/regen/new/fresh ids | Regenerate all IDs in a codex file |
| `/explode` | explode/split/modularize codex, extract children | Split codex into separate child files |
| `/implode` | implode/merge/consolidate/combine codex | Merge separate codex files back into one |
| `/index` | generate/create/codex index | Generate index.codex.yaml for a project |
| `/convert-to-codex` | convert/markdown/md to codex | Convert Markdown to Codex YAML |
| `/convert-to-markdown` | convert/codex to markdown, export to md | Convert Codex to Markdown with frontmatter |
| `/markdown` | codex markdown, add chapterwise frontmatter | Create Markdown files with ChapterWise frontmatter |

## Content & Metadata

| Command | Triggers | Description |
|---------|----------|-------------|
| `/generate-tags` | generate/auto/extract/create tags | Auto-generate tags from codex or markdown content |
| `/update-word-count` | update/count/calculate word count | Update word_count attributes in codex files |
| `/diagram` | diagram, mermaid, create diagram | Create Mermaid diagrams in Codex format |
| `/spreadsheet` | spreadsheet, data table, csv to codex | Create spreadsheets in Codex format |

## Command Conventions

- Use `AskUserQuestion` for all user-facing decisions (never inline text prompts)
- Use `Task` tool for parallel batch work (3+ modules or 10+ files)
- Reference `${CLAUDE_PLUGIN_ROOT}` for paths to scripts, modules, references
- Every command reads `references/principles.md` and `references/language-rules.md`
