---
description: "Convert Markdown files to Codex YAML format"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
triggers:
  - convert to codex
  - markdown to codex
  - md to codex
  - convert md to codex yaml
  - chapterwise:convert-to-codex
argument-hint: "[input.md]"
---

# Convert Markdown to Codex

Convert Codex Lite (Markdown with YAML frontmatter) files to full Codex format.

## When to Use

- Converting simple markdown documents to structured codex format
- Upgrading Codex Lite files to full Codex for additional features (children, relations)
- Importing markdown content into a Chapterwise project

## Usage

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py <input.md> --to-codex [options]
```

### Options

```bash
# Basic conversion (creates .codex.yaml)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py document.md --to-codex

# Output as JSON instead of YAML
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py document.md --to-codex --format json

# Specify output file
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py document.md --to-codex -o output.codex.yaml

# Delete original markdown after conversion
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py document.md --to-codex --delete-original

# Verbose output
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py document.md --to-codex -v
```

## Conversion Mapping

### Frontmatter to Codex

| Markdown Frontmatter | Codex Location |
|---------------------|----------------|
| `type` | `type` |
| `name`, `title` | `name`, `title` |
| `id` | `id` (or auto-generated) |
| `summary` | `summary` |
| `status` | `status` |
| `featured` | `featured` |
| `image`, `images` | `image`, `images` |
| `tags` | `tags` (parsed from comma-delimited or array) |
| `author` | `metadata.author` |
| `last_updated` | `metadata.updated` |
| `description` | `metadata.description` |
| `license` | `metadata.license` |
| Other fields | `attributes` array |

### Body Content

- First H1 heading becomes `title` (if not in frontmatter)
- Remaining content becomes `body` field

## Example

**Input: `chapter-01.md`**
```markdown
---
type: chapter
name: The Beginning
tags: introduction, setup
author: John Smith
---

# The Beginning

It was a dark and stormy night...
```

**Output: `chapter-01.codex.yaml`**
```yaml
metadata:
  formatVersion: "1.3"
  documentVersion: "1.0.0"
  created: "2024-01-01T00:00:00Z"
  source: markdown-lite
  sourceFile: chapter-01.md
  author: John Smith

type: chapter
name: The Beginning
title: The Beginning
id: "550e8400-e29b-41d4-a716-446655440000"

tags:
  - introduction
  - setup

body: |
  It was a dark and stormy night...
```

## Workflow

1. User asks to convert markdown to codex
2. If no file specified, ask which file
3. Ask for output format preference (YAML or JSON)
4. Run conversion
5. Report success and output file path
6. Optionally run auto-fixer on the result

---

## Error Handling

| Situation | Response |
|-----------|----------|
| File not found | "File not found: {path}" |
| No YAML frontmatter detected | "No frontmatter found in {path} — treating entire file as body content." |
| Unsupported input format | "Expected a .md file but got {ext}. Convert manually or rename." |
| Output file already exists | "Output file already exists: {output_path} — overwrite? (y/n)" |
| Missing PyYAML dependency | "Missing PyYAML. Install with: `pip3 install pyyaml`" |

## Language Rules

Follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all shared rules.

| Phase | Verb | Example |
|-------|------|---------|
| Start | Scanning | "Scanning {file}..." |
| Processing | Assembling | "Assembling codex from markdown frontmatter..." |
| Completion | Done | "Done. {output_file} created." |
