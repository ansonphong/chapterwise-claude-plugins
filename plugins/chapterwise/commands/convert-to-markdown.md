---
description: "Convert Codex files to Markdown with frontmatter"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
triggers:
  - convert to markdown
  - codex to markdown
  - export markdown
  - codex to md
  - simplify codex
  - export to md
argument-hint: "[input.codex.yaml]"
---

# Convert Codex to Markdown

Convert full Codex format to Codex Lite (Markdown with YAML frontmatter). This creates a simplified, portable version of your content.

## When to Use

- Exporting content for external use (blogs, documentation, etc.)
- Creating simpler versions of content that don't need children/relations
- Converting for use with standard markdown tools
- Sharing content outside the Chapterwise ecosystem

## Warning: Children Not Included

**Important:** Codex files with `children` will lose that hierarchy when converted to markdown. Only the root entity's fields are converted. You'll be warned if children exist.

## Usage

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py <input.codex.yaml> --to-markdown [options]
```

### Options

```bash
# Basic conversion
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py story.codex.yaml --to-markdown

# Specify output file
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py story.codex.yaml --to-markdown -o output.md

# Delete original codex after conversion
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py story.codex.yaml --to-markdown --delete-original

# Verbose output
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py story.codex.yaml --to-markdown -v
```

## Conversion Mapping

### Codex to Frontmatter

| Codex Field | Markdown Frontmatter |
|-------------|---------------------|
| `type` | `type` |
| `name`, `title` | `name`, `title` |
| `id` | `id` |
| `summary` | `summary` |
| `status` | `status` |
| `featured` | `featured` |
| `image`, `images` | `image`, `images` |
| `tags` | `tags` (as comma-delimited string) |
| `metadata.author` | `author` |
| `metadata.updated` | `last_updated` |
| `metadata.description` | `description` |
| `metadata.license` | `license` |
| `attributes[].key/value` | Key-value pairs in frontmatter |

### Content

- `name` or `title` becomes H1 heading
- `body` becomes markdown body content

### Not Converted

- `children` (warning shown)
- `relations`
- `metadata.formatVersion`, `metadata.documentVersion`

## Example

**Input: `character.codex.yaml`**
```yaml
metadata:
  formatVersion: "1.3"
  author: Jane Doe

type: character
name: Alice
id: "550e8400-e29b-41d4-a716-446655440000"
summary: The protagonist

tags:
  - hero
  - main-character

attributes:
  - key: age
    value: 25
  - key: role
    value: Protagonist

body: |
  Alice is a brave young woman...

children:
  - type: arc
    name: Redemption Arc
```

**Output: `character.md`**
```markdown
---
type: character
name: Alice
id: 550e8400-e29b-41d4-a716-446655440000
summary: The protagonist
tags: hero, main-character
author: Jane Doe
age: 25
role: Protagonist
---

# Alice

Alice is a brave young woman...
```

*(Warning: 1 child not included)*

## Workflow

1. User asks to convert codex to markdown
2. If no file specified, ask which file
3. Check for children and warn if present
4. Run conversion
5. Report success, output path, and any warnings

---

## Error Handling

| Situation | Response |
|-----------|----------|
| File not found | "File not found: {path}" |
| Invalid codex format | "Cannot parse {path} — check for YAML/JSON syntax errors." |
| Children present (data loss warning) | "Warning: {N} children will not be included in markdown output." |
| Output file already exists | "Output file already exists: {output_path} — overwrite? (y/n)" |
| Missing PyYAML dependency | "Missing PyYAML. Install with: `pip3 install pyyaml`" |

## Language Rules

Follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all shared rules.

| Phase | Verb | Example |
|-------|------|---------|
| Start | Scanning | "Scanning {file}..." |
| Processing | Reducing | "Reducing codex to markdown frontmatter..." |
| Completion | Done | "Done. {output_file} created." |
