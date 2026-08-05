# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.0] - 2026-08-05

### Added

- **The report format is a question, not an assumption.** `/analysis` now asks
  depth *and* report format in one prompt — Markdown, Codex, Both, or none —
  with the proposal pre-selected so accepting is a keystroke. v2.4.0 shipped
  both renderers and a `--report=` flag but only ever *stated* the format in
  prose; choosing Codex meant knowing the flag existed.
- **`--report=both`** writes Markdown and Codex from one run. They share a
  stem, and a collision in either format blocks the write.

### Fixed

- **Codex reports are built through `/chapterwise:format`, not beside it.**
  The renderer hand-rolled its YAML and imitated the format command. It now
  hands the assembled document to `CodexAutoFixer` — the engine behind that
  command — and validates the result against the Codex V1.3 schema.
- **Codex reports were invalid, and nothing noticed.** `sourceFile`,
  `entryCount`, and `scopePath` break the schema's attribute-key rule
  (`^[a-z][a-z0-9_-]*$`). They are now `source_file`, `entry_count`, and
  `scope_path`. Reports written by v2.4.0 should be regenerated with
  `--report-only`.
- **No nested codex document could ever validate.** The V1.3 schema recursed
  into children with `$ref: "#"`, which carries the root's
  `required: [metadata]` — so every child node failed for lacking metadata it
  is not supposed to have. Children now reference a `node` definition where
  metadata is optional. This is why generators never validated their own
  output: it would have failed on everything.
- **YAML timestamps no longer fail validation.** PyYAML resolves an unquoted
  `created: 2025-01-26` into a date object; the spec calls the field a string.
  The validator normalizes dates before checking, so a well-formed document no
  longer fails on how it was written.
- **Validation errors name the node that broke.** A `oneOf` failure used to
  report an entire subtree as "not valid under any of the given schemas". It
  now descends to the deepest cause: `children.2.children.0.images.4: 'url' is
  a required property`.
- **Analysis files had an invalid root id.** It was `<filename>-analysis` with
  the filename verbatim, so any manuscript with a space in its name — most of
  them — produced an id the analysis schema rejects. The stem is now
  slugified, and a legacy invalid id is repaired on the next write.
- **Report ids survive the formatter.** They were `uuid5`, which is
  deterministic but not v4-shaped, so the auto-fixer would have replaced every
  one of them on sight. They are now derived deterministically *and* v4-shaped,
  and a regenerated codex report is byte-identical.

## [2.4.0] - 2026-08-04

### Added

- **Analysis resolution.** Granularity is now depth in the codex tree rather than one
  pass per file. `--depth` takes `root`, an integer, `leaf`, `auto`, `all`, or a comma
  list — `--depth root,leaf` gives a whole-work synthesis *and* a pass over every leaf.
  A dome script holding 9 acts and 36 beats yields 37 analyses instead of 1.
- **Scoped entries.** Results carry a `scope` (`root` or `node:<id>`) plus `scopeName`,
  `scopePath`, `scopeDepth` and `scopeIndex`, and all live in the same `.analysis.json`
  sibling. No new file paths, so `chapterwise-web`, `chapterwise-app` and
  `staleness_checker` need no changes. An entry with no `scope` reads as `root`.
- **`scripts/codex_scan.py`** — structural scan (`scan`) and node resolution (`nodes`).
  `/analysis` now reads a manuscript's shape *before* asking anything, and proposes with
  the numbers that justify it. Structure only, so it stays cheap on long manuscripts.
- **`scripts/analysis_report.py`** — exports readable reports to `<source_dir>/analysis/`
  in markdown or Codex V1.3. A formatter, not an analyst: it never calls a model, so
  regenerating is free and the report cannot drift from the stored results. It walks the
  source tree to emit in document order. `--report-only` re-renders or switches format
  without re-analyzing.
- Report and depth choices persist to `analysis-recipe` — asked once, not every run.

### Changed

- `/analysis` proposes rather than interrogates. One question with the recommendation
  preselected, and any flag suppresses its own question so the command stays scriptable.
- Analysis history is kept **per scope**.
- Entry ids gained a scope suffix; the analysis schema already permitted one.
- `analysis/` documented as a deliverable folder alongside `atlas/` and `reader/`, as
  against `.chapterwise/` for machine state and reference inputs.

### Fixed

- **Analysis history no longer destroys scoped results.** `add_analysis_result()` marked
  every entry in a module stale and trimmed the list to three. That was correct when a
  module held one analysis per file, but writing 37 scoped entries through it kept 3 and
  deleted 34 — it treated other nodes' analyses as older versions of the one being
  written. Staling and trimming now partition by scope.
- **`immersive_design`'s scene-level output shape is reachable.** It shipped in v2.1.0
  defining two shapes, whole-show and scene, but the runner only ever analyzed whole
  files — so for a dome script, which is one file containing its scenes, the scene shape
  could not be produced. Modules with multiple shapes now select by scope.
- **Analysis entries record the model that actually ran.** `analysis_writer.py` defaulted
  to `claude-sonnet-4` and its CLI could not pass anything else, so every `.analysis.json`
  the plugin had written carried that stamp regardless of what produced it. Resolution is
  now `--model` → payload `model` key → `CHAPTERWISE_ANALYSIS_MODEL` → `unknown`. No
  concrete model name is a fallback: an unreported model writes `unknown`, which is
  honest, where a plausible wrong name is not.
- Entry ids collided when many entries were written inside the same second — timestamps
  are second-resolution and a scoped run writes dozens.

## [2.3.0] - 2026-08-04

### Fixed

- **The `immersive` course is reachable again.** It was added to
  `module_loader.py` in v2.1.0 but never wired into `/analysis`, which offered
  four courses and described itself as having four. The course existed in code
  and could not be selected from the picker; `immersive_design` was only
  reachable by naming it directly or through `--all` / `--plan`. It now appears
  in the picker, the `analysis list` output, the `--plan` summary, and the
  progress-language table.
- **`/analysis` claimed 31 modules.** There are 33.
- **`/pipeline` hid `--skip-analysis`.** The flag was described in the body but
  missing from `argument-hint`, so it never surfaced in the command's own help.
- **`/index` documented a `--scan` flag that does not exist.**
  `index_generator.py` has no such argument and the generator always scans. The
  use-case table now describes what actually happens.
- **Three commands were missing their namespaced triggers.**
  `chapterwise:spreadsheet`, `chapterwise:convert-to-markdown`, and
  `chapterwise:format-regen-ids` now exist, matching every sibling command.
- **`/research-deep` could not be invoked by its own filename.** Its only
  triggers were `research:deep` and `chapterwise:research:deep`, so
  `research-deep` (the name the file and the skill actually carry) did not
  resolve. Both forms now work.

### Changed

- **`plugins/chapterwise/README.md` is now a full command reference.** It was a
  40-line stub listing 20 of the 24 commands with one-line descriptions. It now
  documents every command with arguments, workflow, inputs and outputs, worked
  examples, and caveats, plus the Codex V1.3 format, project layout, the
  staleness model, all 33 analysis modules grouped by course, the
  `.analysis.json` shape, and how to author a custom module.
- **Root `README.md`** carries working install instructions (add the
  marketplace, then install from it) and links to the reference rather than
  duplicating it.

### Removed

- **Redundant root `.claude-plugin/plugin.json`.** This repo is a marketplace;
  the stub declared the whole repo an empty plugin with no `commands/` beside
  it, and had drifted to 2.1.0 while the real manifest read 2.2.0.

## [2.2.0] - 2026-08-04

### Added

- **Codex V1.3 support** across schemas, scripts, and commands. The plugin had been
  emitting V1.2 while the published spec moved to V1.3.
- **Content array documentation in `/format`** — the command that formats arbitrary
  documents now knows the V1.3 content array: item fields, the `text` / `blockquote` /
  `diagram` / `spreadsheet` types, `width` layout, and the extended include resolver.
  Previously `width` and the new content types were documented only inside `/diagram`
  and `/spreadsheet`, so `/format` never emitted them.
- **`scripts/codex_version.py`** — single source of truth for `CURRENT_FORMAT_VERSION`
  and `SUPPORTED_FORMAT_VERSIONS`. Every script that stamps a `formatVersion` now
  imports it instead of hardcoding a literal.
- **`tests/test_codex_version.py`** — 26 tests covering version constants, V1.3 schema
  acceptance (content arrays, widths, include extensions), auto-fixer version handling,
  and a drift guard that fails the build if any script hardcodes a version stamp again.

### Fixed

- **Auto-fixer silently downgraded V1.3 documents.** `_ensure_v1_metadata` rewrote any
  `formatVersion` outside `['1.0','1.1','1.2']` to `'1.2'`, so a valid V1.3 file was
  quietly reverted on every run. It now recognizes 1.3, and never rewrites a document
  that already declares a supported version — the fixer repairs integrity, it does not
  migrate between versions.
- **Codex schema rejected valid V1.3 files.** The `formatVersion` enum capped at `1.2`.
- **`scrivener_file_writer.py` stamped `formatVersion: "2.1"`** on generated
  `.index.codex.yaml` files — the plugin's own version number, not a codex format
  version, and not a valid value under any spec revision.

### Changed

- Schemas renamed to track the spec they implement: `codex-v1.3.schema.json`,
  `analysis-v1.3.schema.json`, `research-v1.3.schema.json`. `schema_validator.py` and
  all docs updated. Analysis and research schemas accept `1.2` and `1.3` so existing
  `.analysis.json` files keep validating.
- Codex schema gained `metadata.iconset`, top-level `key` / `display` / `animation_url`,
  and V1.3 content-section fields (`width` enum, `include` with diagram and spreadsheet
  extensions).
- New documents are stamped `1.3`. Documents declaring `1.0`–`1.2` remain valid and are
  left as they are.

### Note

`.spreadsheet.yaml` files carry their own independent `formatVersion: "1.0"`, matching
`chapterwise-web`'s generator. That value is unrelated to the codex spec version and was
deliberately left alone.

## [2.1.0] - 2026-08-04

### Added

- **immersive_design** module — immersive experience design for dome shows, planetarium
  pieces, and projection installations. Identifies and proposes immersive effects,
  maps crescendo/lull rhythm, and flags vestibular comfort risk. Runs at whole-show
  level (arc, motion budget, breath coverage, the landing) and scene level (effects in
  play, proposed effects, rhythm, local comfort load).
- **references/immersive-effects.md** — catalog of 59 named effects across nine
  categories. Each carries mechanic, target reaction, arc position, comfort risk,
  caveats, and a sourcing confidence tag. Expanded from the previous 19-name list;
  all 19 legacy names preserved.
- **references/immersive-comfort.md** — vestibular thresholds (~20°/s rotation,
  multi-axis rotation as the robust risk finding, earth-fixed horizon as the primary
  mitigation), fulldome pacing numbers, attention-cue hierarchy, and arc models.
  Marks every claim as measured / guideline / consensus rather than presenting
  practitioner consensus as settled fact.
- **immersive** course grouping.
- Test suite covering module discovery, catalog field integrity, closed vocabularies,
  and standing guards against reintroducing retired vocabulary.

### Changed

- **gag_analysis renamed to comedy_analysis.** The module analyzes comedy; the name
  came from an unrelated meaning of "gag" used in immersive design. Category moved
  from `Specialized Analysis` to `Writing Craft`. Prompt content unchanged.
- The word "gag" no longer appears anywhere in the plugin. Immersive techniques are
  called **effects**.
- `/atlas` no longer uses billing vocabulary. Passes were previously annotated
  `(free)` and `(paid)`, with a "cost estimate" in credits and a "Free entity preview"
  option — all inherited from the web app's billing model. Plugin users bring their own
  compute, so passes now describe scale of work and the preview option is a scope
  choice rather than a tier.

### Fixed

- `immersive_design` declares `category: Immersive Design`, matching chapterwise-core
  exactly, where the plugin previously diverged.

## [1.0.0] - 2026-01-25

### Added

- Initial release as Claude Code plugin
- **format** skill - Convert content to Chapterwise Codex V1.2 format
  - Auto-fixer for common integrity issues
  - UUID generation and validation
  - Timecode auto-calculation
  - YAML/JSON recovery
- **explode** skill - Extract children into separate files
  - Type-based filtering
  - Custom output patterns
  - Auto-fix on extracted files
- **implode** skill - Merge included files back into parent
  - Recursive include resolution
  - Source file cleanup
  - Empty folder deletion
- **index** skill - Generate project index files
  - Auto-discovery of content
  - Pattern-based include/exclude
  - Display configuration
- **lite** skill - Codex Lite (Markdown with frontmatter)
  - Frontmatter validation
  - Word count calculation
  - Title extraction from H1

### Notes

- Packaged from project-scoped skills at `.claude/skills/chapterwise-codex:*`
- Compatible with Claude Code 1.0.33+
- Requires Python 3.8+ for helper scripts
