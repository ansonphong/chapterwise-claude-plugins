---
description: "Split a codex file into separate child files"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
triggers:
  - explode codex
  - split codex
  - modularize codex
  - extract children
  - break up codex
argument-hint: "[file.codex.yaml] [--types type1,type2]"
---

# Codex Exploder - Modularize Large Files

Extract children from a codex file into separate standalone files and replace them with `include:` directives. This enables true modularity, team collaboration, and git-friendly smaller files.

## When to Apply

Apply this command when the user asks to:
- Split a large codex file into separate files per child element
- Modularize a monolithic codex document for team collaboration
- Extract specific child types into their own files
- Organize codex children into type-based folder structures

## Script Location

```
${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py
```

## Quick Start

```bash
# Extract all characters and locations
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml --types character,location

# Preview without making changes
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml --types character --dry-run

# Extract ALL direct children
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml
```

## What It Does

1. **Reads** the input codex file
2. **Extracts** matching children based on type filter
3. **Creates** standalone codex files for each extracted child
4. **Replaces** extracted children with `include:` directives
5. **Runs auto-fixer** on all extracted files (unless disabled)
6. **Creates backup** of original file (unless disabled)

## Before/After Example

**Before (story.codex.yaml):**
```yaml
metadata:
  formatVersion: "1.3"

id: story-001
type: story

children:
  - id: char-001
    type: character
    name: "Hero"
    body: |
      The protagonist of our story...

  - id: loc-001
    type: location
    name: "Castle"
    body: |
      An ancient fortress...

  - id: chapter-001
    type: chapter
    name: "Chapter 1"
```

**Run:** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml --types character,location`

**After (story.codex.yaml):**
```yaml
metadata:
  formatVersion: "1.3"
  exploded:
    timestamp: "2026-01-24T..."
    extracted_types: ["character", "location"]
    extracted_count: 2

id: story-001
type: story

children:
  - include: "/characters/Hero.codex.yaml"
  - include: "/locations/Castle.codex.yaml"
  - id: chapter-001
    type: chapter
    name: "Chapter 1"
```

**New files created:**
- `./characters/Hero.codex.yaml`
- `./locations/Castle.codex.yaml`

## Command-Line Usage

```bash
# Basic: extract specific types
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml --types character,location

# Custom output pattern with placeholders
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml --types character --output-pattern "./nodes/{type}/{name}.codex.yaml"

# Preview what would be extracted (no changes made)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml --types character --dry-run

# Extract ALL direct children (no type filter)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml

# Disable auto-fix on extracted files
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml --types character --no-auto-fix

# Force overwrite existing files
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml --types character --force

# Verbose output
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml -v
```

## Output Pattern Placeholders

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{type}` | Node's type field | `character`, `location` |
| `{name}` | Node's name (sanitized) | `hero-character` |
| `{id}` | Node's ID | `a1b2c3d4-...` |
| `{index}` | Position in children array | `0`, `1`, `2` |

**Default pattern:** `./{type}s/{name}.codex.yaml`

## Options Reference

| Flag | Description | Default |
|------|-------------|---------|
| `--types` | Comma-separated types to extract | All children |
| `--output-pattern` | Path pattern with placeholders | `./{type}s/{name}.codex.yaml` |
| `--format` | Output format: `yaml` or `json` | `yaml` |
| `--dry-run` | Preview without making changes | `false` |
| `--no-backup` | Skip backup of original file | Creates backup |
| `--no-auto-fix` | Skip auto-fixer on extracted files | Runs auto-fix |
| `--force` | Overwrite existing files | Skip existing |
| `-v, --verbose` | Detailed logging | Quiet |

## Python API Usage

```python
from explode_codex import CodexExploder

exploder = CodexExploder()

result = exploder.explode(
    input_path="story.codex.yaml",
    types=["character", "location"],
    output_pattern="./{type}s/{name}.codex.yaml",
    options={
        "dry_run": False,
        "backup": True,
        "format": "yaml",
        "verbose": True,
        "auto_fix": True,
        "force": False
    }
)

if result["success"]:
    print(f"Extracted {result['extracted_count']} nodes")
    for file_path in result["extracted_files"]:
        print(f"  - {file_path}")
else:
    print(f"Failed: {result['errors']}")
```

## Workflow Pattern

```
1. Build your codex with all content inline
2. When it gets large, run explode to modularize:
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py myproject.codex.yaml --types character,location
3. Edit individual files as needed
4. Parent file auto-includes them via include directives
5. Run auto-fixer on edits as usual
```

## Tips

- **Start with `--dry-run`** to preview what will be extracted
- **Use type-based folders** like `./characters/`, `./locations/` for organization
- **Extracted files are complete codex files** - they can be loaded independently
- **Include paths use `/`** for repo-relative or `./` for file-relative
- **Backup files** are created with `.backup` extension by default
- **Run auto-fixer** after exploding to ensure all files are valid

## Common Use Cases

| Scenario | Command |
|----------|---------|
| Extract all characters | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml --types character` |
| Extract characters and locations | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml --types character,location` |
| Extract everything | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml` |
| Preview extraction | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml --dry-run` |
| Custom folder structure | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml --output-pattern "./content/{type}/{name}.codex.yaml"` |

---

## Error Handling

| Situation | Response |
|-----------|----------|
| File not found | "File not found: {path}" |
| No children to extract | "No children found in {path} matching the specified types." |
| Output file already exists | "File already exists: {output_path} — use --force to overwrite." |
| Invalid YAML/JSON syntax | "Cannot parse {path} — check for syntax errors." |
| Missing PyYAML dependency | "Missing PyYAML. Install with: `pip3 install pyyaml`" |

## Language Rules

Follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all shared rules.

| Phase | Verb | Example |
|-------|------|---------|
| Start | Scanning | "Scanning {file} for children..." |
| Processing | Slicing | "Slicing {N} children into separate files..." |
| Completion | Done | "Done. {N} files extracted to {folder}." |
