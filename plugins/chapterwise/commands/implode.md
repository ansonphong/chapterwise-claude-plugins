---
description: Merge separate codex files back into one document
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
triggers:
  - implode codex
  - merge includes
  - consolidate codex
  - inline includes
  - combine codex files
argument-hint: "[file.codex.yaml]"
---

# Codex Imploder - Merge Includes Back Into Parent

Resolve `include:` directives in a codex file, reading the referenced files and merging their content back into the parent document. This is the **inverse of the Explode operation**.

## When to Apply

Apply this command when the user asks to:
- Merge included codex files back into a single parent document
- Consolidate modular files for distribution or archival
- Resolve `include:` directives by inlining their content

## Script Location

```
${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py
```

## Quick Start

```bash
# Merge all includes back into parent
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py story.codex.yaml

# Preview what would be merged (no changes made)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py story.codex.yaml --dry-run

# Merge and delete source files
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py story.codex.yaml --delete-sources
```

## What It Does

1. **Reads** the input codex file
2. **Finds** all `include:` directives in the children array
3. **Reads** each referenced file
4. **Merges** their content back into the parent (removing standalone metadata)
5. **Optionally deletes** the source files after merge
6. **Optionally deletes** empty folders
7. **Creates backup** of original file (unless disabled)

## Before/After Example

**Before (story.codex.yaml with includes):**
```yaml
metadata:
  formatVersion: "1.3"
  exploded:
    timestamp: "2026-01-24T..."
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

**Separate files:**
- `./characters/Hero.codex.yaml` (contains character data with its own metadata)
- `./locations/Castle.codex.yaml` (contains location data with its own metadata)

**Run:** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py story.codex.yaml`

**After (story.codex.yaml - consolidated):**
```yaml
metadata:
  formatVersion: "1.3"
  imploded:
    timestamp: "2026-01-24T..."
    merged_count: 2

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

## Command-Line Usage

```bash
# Basic: merge all includes
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py story.codex.yaml

# Preview what would be merged (no changes made)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py story.codex.yaml --dry-run

# Merge and delete the original included files
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py story.codex.yaml --delete-sources

# Also delete folders that become empty
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py story.codex.yaml --delete-sources --delete-empty-folders

# Recursive: resolve nested includes (includes within included files)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py story.codex.yaml --recursive

# Skip backup creation
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py story.codex.yaml --no-backup

# Verbose output
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py story.codex.yaml -v

# Combine options
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py story.codex.yaml --recursive --delete-sources --delete-empty-folders -v
```

## Options Reference

| Flag | Description | Default |
|------|-------------|---------|
| `--dry-run` | Preview without making changes | `false` |
| `--delete-sources` | Delete included files after merging | `false` |
| `--delete-empty-folders` | Delete folders that become empty | `false` |
| `--recursive` | Resolve nested includes | `false` |
| `--no-backup` | Skip backup of original file | Creates backup |
| `-v, --verbose` | Detailed logging | Quiet |

## Python API Usage

```python
from implode_codex import CodexImploder

imploder = CodexImploder()

result = imploder.implode(
    input_path="story.codex.yaml",
    options={
        "dry_run": False,
        "delete_sources": True,
        "delete_empty_folders": True,
        "recursive": False,
        "backup": True,
        "verbose": True
    }
)

if result["success"]:
    print(f"Merged {result['merged_count']} includes")
    for file_path in result["merged_files"]:
        print(f"  - {file_path}")
    if result["deleted_files"]:
        print(f"Deleted {len(result['deleted_files'])} source files")
else:
    print(f"Failed: {result['errors']}")
```

## Helper Methods

```python
# Check how many includes a file has
count = CodexImploder.get_include_count("story.codex.yaml")
print(f"Found {count} includes")

# Get list of include paths
paths = CodexImploder.get_include_paths("story.codex.yaml")
for path in paths:
    print(f"  - {path}")
```

## Workflow Patterns

### Archive a Project
```bash
# Consolidate everything into one file for archival
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py project.codex.yaml --recursive --delete-sources --delete-empty-folders
```

### Create Distribution Copy
```bash
# Make a self-contained copy without modifying originals
cp project.codex.yaml project-dist.codex.yaml
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py project-dist.codex.yaml --recursive
```

### Preview Before Merging
```bash
# Always preview first with large projects
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py project.codex.yaml --dry-run -v
# Then execute
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py project.codex.yaml
```

## Include Path Resolution

| Path Format | Resolution |
|-------------|------------|
| `/characters/Hero.codex.yaml` | Relative to parent file's directory |
| `./characters/Hero.codex.yaml` | Relative to parent file's directory |
| `../shared/Template.codex.yaml` | Resolved relative to parent |

## What Gets Merged

- **Included:** All node data (id, type, name, body, attributes, children, etc.)
- **Excluded:** The `metadata` block from included files (it's for standalone use only)

## Tips

- **Start with `--dry-run`** to preview what will be merged
- **Use `--recursive`** if your included files also have includes
- **Backup is automatic** unless you use `--no-backup`
- **Metadata updates:** `exploded` metadata is removed, `imploded` metadata is added
- **Run auto-fixer** after imploding to ensure the merged file is valid

---

## Error Handling

| Situation | Response |
|-----------|----------|
| File not found | "File not found: {path}" |
| Include target missing | "Included file not found: {include_path} — skipping." |
| No include directives found | "No include directives found in {path}." |
| Invalid YAML/JSON in included file | "Cannot parse included file {path} — skipping." |
| Missing PyYAML dependency | "Missing PyYAML. Install with: `pip3 install pyyaml`" |

## Language Rules

Follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all shared rules.

| Phase | Verb | Example |
|-------|------|---------|
| Start | Scanning | "Scanning {file} for includes..." |
| Processing | Folding | "Folding {N} files back into parent..." |
| Completion | Done | "Done. {N} includes merged into {file}." |

## Explode/Implode Cycle

```
1. Start with inline content
2. Run explode to modularize:
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py project.codex.yaml --types character,location
3. Work on individual files
4. Run implode to consolidate:
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py project.codex.yaml --delete-sources
5. Back to single file
```
