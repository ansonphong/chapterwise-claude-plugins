# Python Scripts (26 scripts)

All scripts live in `plugins/chapterwise/scripts/`. Three interface patterns: stdin JSON (preferred for new scripts), CLI argparse, and library-only (imported). All output JSON to stdout, errors to stderr. Exit 0 on success.

## Recipe & Plan Management
- `recipe_manager.py` -- Create/load/list/validate/update recipe folders in `.chapterwise/<type>-recipe/`. Commands: create, load, list, validate, update.
- `recipe_validator.py` -- Validate recipe.yaml files and cross-recipe consistency. Output: `{valid, issues, cross_recipe_issues}`.
- `run_recipe.py` -- Execute a saved import recipe (re-run an import with saved settings).

## Validation & Integrity
- `codex_validator.py` -- Validate and auto-fix `.codex.yaml` and `.md` files. Checks parsing, UUIDs, references, orphans. Supports `fix: true` mode.
- `schema_validator.py` -- Library-only. JSON Schema validation against `schemas/` at repo root. Used by other scripts internally.
- `auto_fixer.py` -- Auto-fix Codex V1.3 integrity issues (missing IDs, timestamps, structural problems). CLI and stdin JSON interfaces.
- `lite_helper.py` -- Validate and fix Markdown frontmatter (Codex Lite). Supports `--init` to add frontmatter to bare markdown.

## Analysis Pipeline
- `module_loader.py` -- Discover and load analysis modules. Commands: list, get, courses, recommend. Genre-aware module selection.
- `analysis_writer.py` -- Write analysis results to `.analysis.json` in Codex V1.3 format. Handles history (up to 3 entries per module).
- `staleness_checker.py` -- Compute SHA-256 sourceHash, detect if existing analysis is fresh or stale.

## Import & Format Detection
- `format_detector.py` -- Detect manuscript source format from file path. Returns format, confidence, details. Supports: pdf, docx, scrivener, ulysses, markdown, plaintext, html, rtf, epub, final_draft, fountain.
- `chapter_detector.py` -- Thin wrapper delegating to `patterns/common/chapter_detector.py`. Detects chapter boundaries in extracted text.
- `structure_analyzer.py` -- Thin wrapper delegating to `patterns/common/structure_analyzer.py`. Analyzes manuscript structure.

## Scrivener Tools
- `scrivener_import.py` -- Main orchestrator for Scrivener-to-Codex conversion. Supports markdown/yaml/json output.
- `scrivener_parser.py` -- Parse .scrivx XML project structure files.
- `scrivener_file_writer.py` -- Write parsed Scrivener content to disk in chosen format.
- `rtf_converter.py` -- Convert RTF to Markdown/HTML. Methods: striprtf (default), pandoc, raw.

## Codex Operations
- `explode_codex.py` -- Extract children from a codex file into separate files by type. Supports `--types`, `--output-pattern`, `--dry-run`.
- `implode_codex.py` -- Merge included/referenced files back into parent codex. Supports `--delete-sources`, `--recursive`.
- `convert_format.py` -- Two-way conversion between Codex YAML and Codex Lite (Markdown with frontmatter).
- `index_generator.py` -- Generate `index.codex.yaml` by scanning directory structure.

## Content & Metadata
- `tag_generator.py` -- Auto-generate tags from body fields using text analysis (TF-IDF). Supports `--count`, `--min-count`.
- `word_count.py` -- Recursively count words in body fields and update `word_count` attributes.
- `note_parser.py` -- Parse notes, separate instructions from content, split batch files into individual notes.
- `location_finder.py` -- Index codex files and extract semantic location hints. Subcommands: scan, index, deep, hints.
- `insert_engine.py` -- Core insertion engine with format detection, backup creation, and INSERT markers for review.

## Interface Convention

Scripts invoked from commands use: `echo '{"key":"value"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/script.py [action]`
