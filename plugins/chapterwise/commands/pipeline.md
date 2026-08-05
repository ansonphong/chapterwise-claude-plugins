---
description: "Run full pipeline: Import, Analysis, Atlas, Reader"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, AskUserQuestion, Task
triggers:
  - pipeline
  - run pipeline
  - full pipeline
  - import analyze atlas reader
  - chapterwise:pipeline
argument-hint: "[source-file] [--skip-reader] [--skip-atlas] [--skip-analysis]"
---

# ChapterWise Pipeline

## Overview

Run the full transformation chain with sensible defaults. One command to go from manuscript to complete ChapterWise project with analysis, atlas, and reader. Each step checks for existing fresh results and skips if nothing has changed.

## Step 0: Parse Arguments

- **Source file/path**: required for first run, optional for subsequent runs
- `--skip-reader`: stop after atlas (3 steps instead of 4)
- `--skip-atlas`: stop after analysis (2 steps instead of 4)
- `--skip-analysis`: import only (1 step)

Determine the total step count based on flags:
- Default: 4 steps (Import → Analysis → Atlas → Reader)
- `--skip-reader`: 3 steps
- `--skip-atlas`: 2 steps (also skips reader)

If no source file provided, check for an existing import recipe:
```bash
echo '{"project_path": ".", "type": "import"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py load
```
If found, use the existing project. If not found and no source provided: "Please provide a source file: /pipeline my-novel.pdf"

## Step 1: Import

Report: "Step 1/{total}: Import"

### Check Existing Import
```bash
echo '{"project_path": ".", "type": "import"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py load
```

- **If fresh** (source unchanged): "Import is fresh. Skipping."
- **If stale** (source changed): "Source changed. Re-importing." → Run import with existing preferences
- **If new**: Run the full import workflow from `import.md`

### Pipeline Import Mode

When running as part of the pipeline, use abbreviated defaults to minimize interaction:
- Structure: flat (unless parts detected, then folders_per_part)
- Format: markdown (Codex Lite)
- Front/back matter: exclude
- Skip the full interview — use defaults, only ask if something is ambiguous

### Post-Step Validation

Run validators after import completes:
```bash
echo '{"path": "OUTPUT_DIR", "fix": true}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/codex_validator.py
echo '{"recipe_path": ".chapterwise/import-recipe/"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_validator.py
```

If validation fails with unfixable issues, report and ask whether to continue.

## Step 2: Analysis

Report: "Step 2/{total}: Analysis"

### Auto-Configure

- Detect genre from imported content (read first few chapters, check existing analysis)
- Select recommended modules for the genre:
  ```bash
  echo '{"genre": "DETECTED_GENRE"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/module_loader.py recommend
  ```
- Report: "{N} modules selected for {genre}."

### Execute

Run analysis using the recommended module set. Use parallel Task agents for chapter-level modules.

Progress messaging per Language Guide:
- "Quick taste... summary, characters, tags on {N} chapters."
- "Slow roasting structure... three-act, story beats, pacing."
- "Done. {N} modules across {N} chapters."

### Post-Step Validation

```bash
echo '{"recipe_path": ".chapterwise/analysis-recipe/"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_validator.py
```

## Step 3: Atlas

Report: "Step 3/{total}: Atlas"

If `--skip-atlas` was specified: "Skipping atlas." → Jump to Step 5.

### Auto-Configure

- Build default atlas: "Story Atlas" for fiction, "Reference Atlas" for nonfiction
- Use default sections based on genre:
  - Fiction: characters, timeline, themes, plot_structure, locations, relationships
  - Nonfiction: topic_map, themes, key_concepts
- Accept defaults without prompting

### Execute

Run the atlas build pipeline from `atlas.md`:
- Pass 0: Scan project
- Pass 1: Extract entities (reuse analysis data)
- Pass 2: Analyze cross-chapter (parallel agents)
- Pass 3: Synthesize sections

Progress per Language Guide:
- "Extracting entities... {N} characters, {M} locations."
- "Synthesizing {N} sections..."
- "Done. {atlas_name} — {N} sections."

### Post-Step Validation

```bash
echo '{"path": "ATLAS_DIR", "fix": true}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/codex_validator.py
echo '{"recipe_path": ".chapterwise/atlas-recipe/"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_validator.py
```

## Step 4: Reader

Report: "Step 4/{total}: Reader"

If `--skip-reader` was specified: "Skipping reader." → Jump to Step 5.

### Auto-Configure

- Use minimal template by default
- Include manuscript content + atlas if available
- Accept all defaults

### Execute

Build the reader from `reader.md`:
- Copy template files
- Parse all content
- Generate manifest
- Write HTML reader

Progress: "Building reader... {N} chapters, {word_count} words."

### Post-Step Validation

Validate reader output and recipe:
```bash
echo '{"recipe_path": ".chapterwise/reader-recipe/"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_validator.py
```

## Step 5: Summary

Report final state using the `/status` output format:

```
Pipeline complete.

{Title} — {chapters} chapters, {words} words

  Import     ✓  {format}, {structure}
  Analysis   ✓  {N} modules
  Atlas      ✓  {atlas_name} — {N} sections
  Reader     ✓  Open reader/index.html to preview

{files_created} files created.
```

Include validation summary:
- "All validations passed." (ideal)
- "{N} issues auto-fixed during pipeline." (acceptable)
- "Warning: {N} issues need manual review." (flag to user)

## Pipeline Defaults

The pipeline uses sensible defaults to minimize interaction:

| Step | Default |
|------|---------|
| Import structure | Flat (or folders_per_part if parts detected) |
| Import format | Markdown (Codex Lite) |
| Analysis modules | Genre-recommended set |
| Atlas type | Story Atlas (fiction) / Reference Atlas (nonfiction) |
| Atlas sections | All recommended for genre |
| Reader template | Minimal |

## Error Handling

- **Step failure**: Report the error, ask "Continue with remaining steps?"
- **Partial results**: Each step saves its recipe independently. Re-running `/pipeline` skips completed fresh steps.
- **Missing source**: "Please provide a source file: /pipeline my-novel.pdf"
- **Missing dependencies**: Report exact `pip3 install` command, offer to continue after install

## Language Rules

Read and follow `${CLAUDE_PLUGIN_ROOT}/references/principles.md` — especially **LLM Judgment, User Override**.
Follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all shared messaging rules.

**Pipeline-specific:**
- Use "Step N/{total}: {name}" headers for each step
- Per-step progress follows each command's specific language rules
- Final summary is data-oriented (like /status)
