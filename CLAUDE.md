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

1. **LLM Judgment, User Override** — Agent decides, user overrides. Cascade: plugin defaults → `.chapterwise/settings.json` → command variant → prompt language.
2. **Clean Defaults, Rich Options** — Zero config first run.
3. **Data Over Flare** — Progress messages include real data, no theatrical language. See `references/language-rules.md`.

## Conventions

- **Commands** are markdown with YAML frontmatter in `commands/`. Auto-discovered.
- **Scripts** use stdin/stdout JSON: `echo '{"key":"value"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/script.py`
- **Never say "recipe" to the user** — internal system only.
- **Cooking verbs** — scan, slice, source, distill, gather, assemble. Action verbs with technical nouns and real data.
- **Validation after output** — run `codex_validator.py` after generating codex, silent on success.
- **Project settings** in `.chapterwise/settings.json` (user's project, not this repo). One section per command — `analysis`, `atlas`, `reader`, `research`. Read and write via `scripts/settings.py`, never by hand-parsing.

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

- **2026-08-05** — v2.10.0. One pattern, no special cases. v2.9.0 folded research into settings but left it alone in defaulting to `.chapterwise/`, reasoning that research is an input rather than a deliverable — fine as something a *writer* chooses, wrong as a shape only one section has. Every section that writes output now has an `output_dir` resolved by identical rules, and nothing is hidden by default; `research` lands in a visible `research/` folder, and any section can be tucked away with `"output_dir": ".chapterwise/…"`. `analysis.report_dir` renamed to `analysis.output_dir` so the key is the same everywhere (flag `--output-dir`); a settings file written by 2.6–2.9 is migrated on read and normalised on the next write rather than silently ignored. The only remaining difference between sections is what "relative" means, and that follows from what the artifact belongs to: an analysis report describes one manuscript and sits beside it, while an atlas, a reader and research belong to the project.

- **2026-08-05** — v2.9.0. One configuration surface. `/research` kept its preferences in `.claude/chapterwise.local.md` — a second config file in a different format (markdown frontmatter) with its own key vocabulary, for one command. Retired: research is now a `.chapterwise/settings.json` section like the rest, with `default_depth` → `depth` and `output_path` → `output_dir` so key names mean the same thing everywhere, and both values validated at write time. `references/principles.md` documents the cascade in terms of `settings.json`/`settings.py`; the cascade itself is unchanged (plugin defaults → settings → command variant → prompt language, prompt language still winning for one run without mutating what is saved). Research output stays under `.chapterwise/` on purpose — it is material consulted *while* writing, unlike atlases, readers and analysis reports which are derived *from* the manuscript. Guards assert no doc still points at the retired file and that the sections documented in `principles.md` match `DEFAULTS` in code.

- **2026-08-05** — v2.8.0. Settings extended past `/analysis` to `/atlas` and `/reader` — one `.chapterwise/settings.json`, one section per command, rather than a config surface per command. `settings.py resolve` takes a `section` and returns that section's values with paths already resolved plus a scoped `sources`/`configured`; configuring one section leaves the others asking. Both commands now skip their question when a value is configured (`/atlas` its structure question, `/reader` template selection) and offer once to save after a first successful build. Output paths know what they belong to: an analysis report resolves relative to the manuscript it describes, an atlas and a reader relative to the project root, since those are built once for the project. `reader.template` and `reader.theme` are validated at write time. Choices left in older `reader-recipe` (`design.template`, `design.theme`) and `atlas-recipe` (`sections`) are honoured and folded forward. `/research` still keeps its preferences in `.claude/chapterwise.local.md` — a separate older surface, not folded in.

- **2026-08-05** — v2.7.0. Settings became universal across `/analysis` rather than true of one route. v2.6.0 wired them into the single-file path only; the course picker, `--plan`, and the `--all`/`--glob` batches never exported a report at all, so a configured `report_format` was ignored by three of the four routes. New **Section 0: Preflight** in `commands/analysis.md` states the contract once — resolve settings before asking (0a), what may be asked (0b), every route exports reports (0c), the save offer is once per project not once per file (0d) — and Sections 1, 2, 5 and 6 defer to it. Batch runs now state report volume before starting. Doc guards in `tests/test_settings.py` assert each route section references the preflight steps and that the documented settings block matches `DEFAULTS` in code.

- **2026-08-05** — v2.6.0. Project configuration became a declared file rather than a thing inferred from run history. `.chapterwise/settings.json` holds what a project does by default — report format, report folder, depth — resolved `plugin defaults → settings.json → flags`. A flag wins for its run and is never written back. `settings.py get` returns a `sources` map marking each value `default` / `recipe` / `settings`, which is what lets `/analysis` ask only about unconfigured values: the first real run offers to save what you chose, and a configured project is never asked again. The default report format changed from markdown to **codex** into an `analysis/` folder beside the analyzed file. New `--report-dir`; paths resolve like codex `include` paths (bare/`./` beside the file, leading `/` from the project root, `~` literal). Settings-shaped keys left in an older `analysis-recipe` are honoured until a settings file exists and folded in when one is written — settings are intent, recipes are history, and the two had been conflated.

- **2026-08-05** — v2.5.0. The report format became a question. v2.4.0 shipped both renderers but only ever *stated* the format in its proposal, so choosing codex meant knowing the flag existed; `/analysis` now asks depth and format in one prompt (Markdown / Codex / Both / none), and `--report=both` writes the pair. Codex reports are now produced **through** `/chapterwise:format` — the assembled document goes to `CodexAutoFixer` and is then schema-validated — rather than imitating it. Wiring that validation exposed four things it had been hiding: codex reports carried attribute keys the V1.3 schema forbids (`sourceFile` → `source_file`); **no nested codex document could validate at all**, because the schema recursed into children with `$ref: "#"` and dragged the root's `required: [metadata]` with it; analysis files carried a root id built from the raw filename, invalid for any manuscript with a space in its name; and report ids were `uuid5`, deterministic but not v4-shaped, so the auto-fixer would have replaced every one. Validation errors now name the node that broke instead of dumping the subtree. Regenerate v2.4.0 codex reports with `--report-only`.

- **2026-08-04** — v2.4.0. Analysis granularity became depth in the codex tree rather than one pass per file. `--depth root,leaf` on a dome script gives a whole-show read plus all 36 beats, scoped into one `.analysis.json`. This made `immersive_design`'s scene-level output shape reachable — it shipped in v2.1.0 defining two shapes, but a dome script is one file containing its scenes, so the runner could never produce the scene half. Two new scripts: `codex_scan.py` (structure-first scan, so `/analysis` proposes with real numbers instead of asking blind) and `analysis_report.py` (deterministic markdown/codex reports into `<source_dir>/analysis/`, never calls a model). Fixed a data-loss bug: analysis history staled and trimmed a module's whole entry list, so 37 scoped writes kept 3 and deleted 34. Plan: `../../plans/plugins/analysis-resolution/`.

- **2026-08-04** — v2.3.0. Documentation drift swept out of the command files, and one shipped-but-unreachable feature restored. The `immersive` course landed in `module_loader.py` in v2.1.0 but was never wired into `/analysis` — the picker offered four courses and the prose said four, so `immersive_design` could only be reached by naming it directly or via `--all`/`--plan`. It is now in the picker, `analysis list`, the `--plan` summary, and the language table. Also fixed: `/analysis` claimed 31 modules (33); `/pipeline` described `--skip-analysis` but omitted it from `argument-hint`; `/index` documented a `--scan` flag `index_generator.py` has never had; `/spreadsheet`, `/convert-to-markdown`, and `/format-regen-ids` were missing their `chapterwise:` triggers; `/research-deep` did not answer to its own filename. `plugins/chapterwise/README.md` went from a 40-line stub to the full command reference (all 24 commands with arguments, workflow, outputs, examples; plus format, modules, and custom-module authoring), and the redundant root `.claude-plugin/plugin.json` stub is gone.

- **2026-08-04** — v2.2.0. Codex **V1.3** upgrade. The plugin had been emitting V1.2 while the published spec moved on. Schemas renamed to `*-v1.3.schema.json` and taught the V1.3 content array (`width`, `diagram`/`spreadsheet` types, extended `include` resolution for `.mermaid`/`.mmd`/`.csv`/`.xlsx`/`.spreadsheet.yaml`). `/format` now documents the content array — previously `width` and the new types existed only in `/diagram` and `/spreadsheet`, so the general formatter never emitted them. New `scripts/codex_version.py` is the single source of truth for the version; every stamping script imports it. Fixed: the auto-fixer silently downgraded V1.3 documents to 1.2 on every run, and `scrivener_file_writer.py` stamped the plugin's own version (`2.1`) as a codex `formatVersion`. Note: `.spreadsheet.yaml` keeps its own independent `formatVersion: "1.0"` — unrelated to the codex spec.
- **2026-08-04** — v2.1.0. Added `immersive_design` module for dome shows and immersive experiences, backed by two new reference files (`immersive-effects.md`, 59 effects; `immersive-comfort.md`, vestibular thresholds and fulldome pacing). Renamed `gag_analysis` → `comedy_analysis`; the word "gag" is gone from the plugin, and the immersive unit is an "effect". New `immersive` course. Removed all billing vocabulary from `/atlas` — plugin users bring their own compute, so free/paid pass framing had no meaning here. Design spec: `../../plans/plugins/2026-08-04-immersive-design-module.md`.

## Output Locations

**Every command that writes output has an `output_dir` setting, and they all behave
identically.** Same key, same path rules — bare and `./` relative, a leading `/` from the
project root, `.chapterwise/…` always the project's `.chapterwise/`, `~` literal. The only thing that differs is what "relative" is relative to,
and that follows from what the artifact belongs to: an analysis report describes one
manuscript and sits beside it; an atlas, a reader and research belong to the project.

| Location | Contents |
|---|---|
| `.chapterwise/` | machine state the user does not author — `*-recipe`, `settings.json`, `analysis-modules/` |
| top-level, visible | generated output — `analysis/`, `atlas/`, `reader/`, `research/` |

**Visible or hidden is a value, not a rule.** Nothing generated is hidden by default. A
writer who wants research (or reports, or anything else) out of the way sets
`"output_dir": ".chapterwise/research"`. Do not bake that choice into a command, and do
not give one section a shape the others do not have — that was the v2.9.0 mistake.

## Vocabulary Guards

Two standing rules, enforced by `tests/test_immersive_design.py`:

1. **Never say "gag."** It is theme-park jargon and fails the writer-facing vocabulary rule. Immersive techniques are **effects**; comedy analysis is **comedy**.
2. **Never mention credits, paid/free tiers, or billing.** Those are `chapterwise-web` concepts. A plugin user is spending their own tokens. Where cost matters, describe the **scale of work** — passes, chapters, modules — not a price. ("Credits" in the attribution sense — model credits, web-source citations in `/research` — is a different word and is fine.)
