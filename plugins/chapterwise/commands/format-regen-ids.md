---
description: "Regenerate all IDs in a codex file"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
triggers:
  - regenerate ids
  - regen ids
  - new ids
  - fresh ids
  - duplicate ids
  - chapterwise:format-regen-ids
argument-hint: "[file.codex.yaml]"
---

# Regenerate All IDs

Regenerate ALL IDs in a codex file, even if they're already valid. This is useful when:
- Duplicating/forking content that needs unique IDs
- Ensuring completely fresh IDs after import
- Resetting IDs after copy/paste operations

## Usage

Run the auto-fixer with the `--re-id` flag:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py <file.codex.yaml> --re-id
```

### Options

```bash
# Regenerate IDs in a single file
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py /path/to/file.codex.yaml --re-id

# Dry run (preview without changes)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py /path/to/file.codex.yaml --re-id --dry-run

# Regenerate IDs in all files in a directory
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py /path/to/directory --re-id --recursive

# Verbose output
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py /path/to/file.codex.yaml --re-id --verbose
```

## What Gets Regenerated

- All `id` fields on nodes/entities
- All `targetId` fields in relations

## Workflow

1. User asks to regenerate IDs or mentions duplicating content
2. If no file specified, ask which file
3. Run the auto-fixer with `--re-id` flag
4. Report the number of IDs regenerated
5. Warn user that relation targetIds now point to new IDs (may need manual update if referencing external files)

---

## Error Handling

| Situation | Response |
|-----------|----------|
| File not found | "File not found: {path}" |
| Invalid YAML/JSON syntax | "Cannot parse {path} — check for syntax errors." |
| No IDs found to regenerate | "No id or targetId fields found in {path}." |
| Write permission denied | "Cannot write to {path} — check file permissions." |
| Missing PyYAML dependency | "Missing PyYAML. Install with: `pip3 install pyyaml`" |

## Language Rules

Follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all shared rules.

| Phase | Verb | Example |
|-------|------|---------|
| Start | Scanning | "Scanning {file} for IDs..." |
| Processing | Slicing | "Slicing old IDs... regenerating {N} fresh UUIDs." |
| Completion | Done | "Done. {N} IDs regenerated in {file}." |
