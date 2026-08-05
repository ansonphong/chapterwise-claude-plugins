# ChapterWise Plugins — Claude Code Writing Toolkit

Complete writing toolkit for manuscript import, AI analysis, story atlas generation, and custom readers. 24 slash commands, 33 analysis modules (5 courses), 28 Python scripts, 7 format converters.

## Architecture

```
plugins/chapterwise/
├── .claude-plugin/plugin.json   # Plugin manifest (auto-discovered)
├── commands/                    # Slash commands (YAML frontmatter + markdown)
├── modules/                     # 33 analysis modules (5 courses)
├── scripts/                     # Python utilities (stdin JSON → stdout JSON)
├── patterns/                    # Format conversion patterns + common utilities
├── templates/                   # Reader HTML templates (minimal, academic)
├── references/                  # principles.md, language-rules.md, insert specs, immersive-effects/comfort
└── schemas/                     # Codex V1.3, analysis, research, recipe schemas
```

## Core Principles

1. **LLM Judgment, User Override** — Agent decides, user overrides. Cascade: plugin defaults → `.claude/chapterwise.local.md` → command variant → prompt language.
2. **Clean Defaults, Rich Options** — Zero config first run.
3. **Data Over Flare** — Progress messages include real data, no theatrical language. See `references/language-rules.md`.

## Conventions

- **Commands** are markdown with YAML frontmatter in `commands/`. Auto-discovered.
- **Scripts** use stdin/stdout JSON: `echo '{"key":"value"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/script.py`
- **Never say "recipe" to the user** — internal system only.
- **Cooking verbs** — scan, slice, source, distill, gather, assemble. Action verbs with technical nouns and real data.
- **Validation after output** — run `codex_validator.py` after generating codex, silent on success.
- **User preferences** in `.claude/chapterwise.local.md` (user's project, not this repo).

## Brand Voice

> **Canonical reference:** `../../.claude/references/brand-voice.md` — read before writing ANY user-facing text.

A confident technical mentor who treats writing as engineering. Philosophy first, features second. Developer metaphors are the identity ("IDE for Writers," "debug your plot"), not decoration. Honest capability, zero hype. Chaos → Clarity. Ownership always (open formats, no lock-in). Never theatrical, never condescending, never vague. Writer-facing text says "manuscript" not "file," "chapter" not "node," "project" not "repo." Analysis reads like editorial feedback. Errors: "[What went wrong] — [What to do about it]." Progress: specific data, no filler.

Plugin output is the most voice-intensive surface — analysis reports, progress messages, command descriptions, and atlas narratives all speak directly to writers. See also `references/language-rules.md` for cooking-verb conventions.

## Modular Rules

See `.claude/rules/` for topic-specific rules:
- `commands.md` — command file structure, triggers, allowed tools
- `scripts.md` — JSON stdin/stdout patterns, error handling
- `testing.md` — pytest, TDD, structure mirroring
- `codex-format.md` — Codex V1.3, Codex Lite, validation, schema resolution

## Context

- `.claude/context/` — internal architecture docs for this repo
- `../../.claude/context/chapterwise-plugins.md` — cross-repo summary in parent
- `../../.claude/references/chapterwise-plugins.md` — exhaustive reference in parent

## Plans

Plans are centralized in the parent workspace, NOT in this repo:
- Active plans: `../../plans/plugins/`
- Archives: `../../plans/plugins/_archive/`

## Post-Plan Workflow

After implementing any plan:
1. Update `.claude/context/` files to reflect new reality
2. Add dated one-liner to Recent Changes below
3. Update parent context: `../../.claude/context/chapterwise-plugins.md`
4. Archive the plan in `../../plans/plugins/_archive/`
5. Update `../../.claude/STATUS.md` and `../../plans/exec-order.md`

## Recent Changes

- **2026-08-05** — v2.6.0. Project configuration became a declared file rather than a thing inferred from run history. `.chapterwise/settings.json` holds what a project does by default — report format, report folder, depth — resolved `plugin defaults → settings.json → flags`. A flag wins for its run and is never written back. `settings.py get` returns a `sources` map marking each value `default` / `recipe` / `settings`, which is what lets `/analysis` ask only about unconfigured values: the first real run offers to save what you chose, and a configured project is never asked again. The default report format changed from markdown to **codex** into an `analysis/` folder beside the analyzed file. New `--report-dir`; paths resolve like codex `include` paths (bare/`./` beside the file, leading `/` from the project root, `~` literal). Settings-shaped keys left in an older `analysis-recipe` are honoured until a settings file exists and folded in when one is written — settings are intent, recipes are history, and the two had been conflated.

- **2026-08-05** — v2.5.0. The report format became a question. v2.4.0 shipped both renderers but only ever *stated* the format in its proposal, so choosing codex meant knowing the flag existed; `/analysis` now asks depth and format in one prompt (Markdown / Codex / Both / none), and `--report=both` writes the pair. Codex reports are now produced **through** `/chapterwise:format` — the assembled document goes to `CodexAutoFixer` and is then schema-validated — rather than imitating it. Wiring that validation exposed four things it had been hiding: codex reports carried attribute keys the V1.3 schema forbids (`sourceFile` → `source_file`); **no nested codex document could validate at all**, because the schema recursed into children with `$ref: "#"` and dragged the root's `required: [metadata]` with it; analysis files carried a root id built from the raw filename, invalid for any manuscript with a space in its name; and report ids were `uuid5`, deterministic but not v4-shaped, so the auto-fixer would have replaced every one. Validation errors now name the node that broke instead of dumping the subtree. Regenerate v2.4.0 codex reports with `--report-only`.

- **2026-08-04** — v2.4.0. Analysis granularity became depth in the codex tree rather than one pass per file. `--depth root,leaf` on a dome script gives a whole-show read plus all 36 beats, scoped into one `.analysis.json`. This made `immersive_design`'s scene-level output shape reachable — it shipped in v2.1.0 defining two shapes, but a dome script is one file containing its scenes, so the runner could never produce the scene half. Two new scripts: `codex_scan.py` (structure-first scan, so `/analysis` proposes with real numbers instead of asking blind) and `analysis_report.py` (deterministic markdown/codex reports into `<source_dir>/analysis/`, never calls a model). Fixed a data-loss bug: analysis history staled and trimmed a module's whole entry list, so 37 scoped writes kept 3 and deleted 34. Plan: `../../plans/plugins/analysis-resolution/`.

- **2026-08-04** — v2.3.0. Documentation drift swept out of the command files, and one shipped-but-unreachable feature restored. The `immersive` course landed in `module_loader.py` in v2.1.0 but was never wired into `/analysis` — the picker offered four courses and the prose said four, so `immersive_design` could only be reached by naming it directly or via `--all`/`--plan`. It is now in the picker, `analysis list`, the `--plan` summary, and the language table. Also fixed: `/analysis` claimed 31 modules (33); `/pipeline` described `--skip-analysis` but omitted it from `argument-hint`; `/index` documented a `--scan` flag `index_generator.py` has never had; `/spreadsheet`, `/convert-to-markdown`, and `/format-regen-ids` were missing their `chapterwise:` triggers; `/research-deep` did not answer to its own filename. `plugins/chapterwise/README.md` went from a 40-line stub to the full command reference (all 24 commands with arguments, workflow, outputs, examples; plus format, modules, and custom-module authoring), and the redundant root `.claude-plugin/plugin.json` stub is gone.

- **2026-08-04** — v2.2.0. Codex **V1.3** upgrade. The plugin had been emitting V1.2 while the published spec moved on. Schemas renamed to `*-v1.3.schema.json` and taught the V1.3 content array (`width`, `diagram`/`spreadsheet` types, extended `include` resolution for `.mermaid`/`.mmd`/`.csv`/`.xlsx`/`.spreadsheet.yaml`). `/format` now documents the content array — previously `width` and the new types existed only in `/diagram` and `/spreadsheet`, so the general formatter never emitted them. New `scripts/codex_version.py` is the single source of truth for the version; every stamping script imports it. Fixed: the auto-fixer silently downgraded V1.3 documents to 1.2 on every run, and `scrivener_file_writer.py` stamped the plugin's own version (`2.1`) as a codex `formatVersion`. Note: `.spreadsheet.yaml` keeps its own independent `formatVersion: "1.0"` — unrelated to the codex spec.
- **2026-08-04** — v2.1.0. Added `immersive_design` module for dome shows and immersive experiences, backed by two new reference files (`immersive-effects.md`, 59 effects; `immersive-comfort.md`, vestibular thresholds and fulldome pacing). Renamed `gag_analysis` → `comedy_analysis`; the word "gag" is gone from the plugin, and the immersive unit is an "effect". New `immersive` course. Removed all billing vocabulary from `/atlas` — plugin users bring their own compute, so free/paid pass framing had no meaning here. Design spec: `../../plans/plugins/2026-08-04-immersive-design-module.md`.

## Output Locations

Where a generated file goes follows one rule — **input vs. output**, not hidden vs.
readable:

| Location | Contents |
|---|---|
| `.chapterwise/` | machine state and reference *inputs* — `*-recipe`, `research/`, `analysis-modules/` |
| top-level, visible | deliverables derived *from* the manuscript — `atlas/`, `reader/`, `analysis/` |

`research/` is readable and still hidden, because it is material consulted *while*
writing. An analysis report is derived *from* the manuscript, so it is visible, committed,
and handed to collaborators. Do not bury a deliverable in `.chapterwise/`.

## Vocabulary Guards

Two standing rules, enforced by `tests/test_immersive_design.py`:

1. **Never say "gag."** It is theme-park jargon and fails the writer-facing vocabulary rule. Immersive techniques are **effects**; comedy analysis is **comedy**.
2. **Never mention credits, paid/free tiers, or billing.** Those are `chapterwise-web` concepts. A plugin user is spending their own tokens. Where cost matters, describe the **scale of work** — passes, chapters, modules — not a price. ("Credits" in the attribution sense — model credits, web-source citations in `/research` — is a different word and is fine.)
