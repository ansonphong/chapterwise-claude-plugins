---
description: "Analyze Codex files with intelligent module selection"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, AskUserQuestion, Task
triggers:
  - analysis
  - analysis summary
  - analysis characters
  - analysis list
  - analysis help
  - analyze
  - chapterwise:analysis
argument-hint: "[module] [file] [--flags]"
---

# ChapterWise Analysis

## Overview

Run AI analysis on any Codex file using 33 specialized modules. Analysis reads a chapter's content, applies a focused analytical lens (characters, structure, pacing, style, themes, and more), and saves results to a `.analysis.json` file alongside the source. Results are versioned — re-running a module on an unchanged file is detected and skipped unless forced.

Analysis can be run on a single file, batched across a folder, or run as a full multi-module plan across the entire project. The plan mode scans the manuscript, selects modules that matter for this genre, groups them into courses, and runs them in the right order.

---

## Command Routing

Inspect the arguments and route to the appropriate path:

| Invocation | Route |
|------------|-------|
| `analysis` (no args) | Interactive course picker — see Section 1 |
| `analysis <module> [file]` | Direct analysis — see Section 2 |
| `analysis list` | Module list grouped by course — see Section 3 |
| `analysis help <module>` | Module details — see Section 4 |
| `analysis --plan` | Genre-aware module planning — see Section 5 |
| `analysis --all [--glob pattern]` | Batch all modules on a file or folder — see Section 6 |
| `analysis <module> --glob pattern` | Batch a single module across matched files — see Section 6 |
| `analysis <module> [file] --report-only` | Re-render an existing report — see Step 2i |

**Every route reads `.chapterwise/settings.json` first — see Section 0.** Settings belong
to the project, so the course picker, a batch, and a single-file run all behave the same.

### Flags

| Flag | Effect |
|------|--------|
| `--depth root\|N\|leaf\|auto\|all` | Resolution. Comma lists allowed: `--depth root,leaf` analyzes the whole file **and** every leaf. Default `auto` |
| `--report[=markdown\|codex\|both]` | Export a report. Default from settings, then `codex` |
| `--output-dir <path>` | Where the report goes. Relative = beside the file; leading `/` = project root |
| `--no-report` | Analyze only, no export |
| `--report-only` | Re-render the report from stored results; runs no analysis |
| `--force` | Skip staleness checks and overwrite an existing report |
| `--dry-run` | Show what would run; write nothing |

**Any flag suppresses its question.** Passing `--depth` and `--report` together runs the
whole thing without prompting — this command has to be scriptable. So does a configured
setting: see *Settings* below.

### Settings

`.chapterwise/settings.json` holds what this project does by default. It is read before
anything is asked, and written only when the user says to:

```json
{
  "version": 1,
  "analysis": {
    "report": true,
    "report_format": "codex",
    "output_dir": "analysis",
    "depth": "auto"
  }
}
```

Resolution, lowest to highest: **plugin defaults → `.chapterwise/settings.json` → flags.**
Defaults are codex reports into an `analysis/` folder beside the analyzed file.

`output_dir` resolves the way codex `include` paths do — `analysis` and `./analysis` sit
beside the manuscript, `/reports` is from the project root, `~/…` is a literal path, and
`.chapterwise/…` is the project's `.chapterwise/`. Every section uses this same key and
these same rules; set `.chapterwise/analysis` if you would rather reports were not
visible.

Settings are *intent* and are committed. The `*-recipe` folders beside them are *history*
— what a command last did. Settings-shaped keys left in an older recipe are honoured until
a settings file exists, and folded in when one is written.

---

## Section 0: Preflight — applies to every route

**Sections 1, 2, 5 and 6 all obey this.** Settings are a property of the project, not of
one invocation, so a course run, a batch, a plan and a single-file run must behave the
same way. Anything below that says "every analysis" means every analysis.

### Step 0a: Resolve settings before asking anything

```bash
echo '{"source": "ANY_SOURCE_FILE"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/settings.py resolve
```

For a batch, resolve once against any file in the set — settings belong to the project,
and every file in a project resolves to the same ones.

Returns `report`, `report_format`, `output_dir` (already an absolute path), `depth`,
`found`, and a `sources` map.

### Step 0b: What to ask

| `sources[key]` | Meaning | Do |
|---|---|---|
| `settings` | Written in `.chapterwise/settings.json` | **Never ask.** Use it, mention it in one clause |
| `recipe` | Left by an older version | **Never ask.** Use it |
| `default` | Nothing configured | Ask, with the proposal pre-selected |

A flag beats all three for that run and is never persisted.

### Step 0c: Export reports — every route, not just single-file

Every analysis that writes results also exports a report, unless `report` is `false` or
`--no-report` was passed. **This includes course runs, `--plan` runs, and `--all` /
`--glob` batches** — one report per source file, written after that file's analyses land:

```bash
echo '{"source": "SOURCE_FILE", "module": "MODULE_NAME", "format": "FORMAT"}' \
  | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analysis_report.py
```

The script resolves settings itself, so `format` and the output folder may be omitted
entirely and will still be right. Pass them only to override.

Reports are per module per file. A course run of 3 modules across 28 chapters writes 84
reports — say so before starting, and report the count once at the end rather than per
file. If that is not wanted, `--no-report` or `"report": false` in settings turns it off
for good.

### Step 0d: Offer to save — once per project

If `found` is `false` and the user made a choice this run, offer **once**, after the work
is done:

> "Save these as this project's defaults? Codex reports into `analysis/`."

- **Save** — write `.chapterwise/settings.json`
- **Not now** — ask again next time

```bash
echo '{"path": "SOURCE_FILE", "updates": {"analysis": {"report_format": "FORMAT", "output_dir": "analysis", "depth": "DEPTH", "report": true}}}' \
  | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/settings.py set
```

**Once per project, not once per file.** A batch offers at the end, not 28 times. Never
persist a value that came from a one-off flag.

---

### Resolution

A codex is a tree, and resolution selects which nodes get their own analysis pass. For a
dome script that is one file holding 9 acts and 36 beats:

| `--depth` | Passes | Meaning |
|---|---:|---|
| `root` | 1 | the whole show |
| `1` | 9 | act by act |
| `leaf` | 36 | beat by beat |
| `root,leaf` | 37 | whole-show synthesis **and** every beat |

Results all live in the one `.analysis.json` sibling, tagged by scope, each scope keeping
its own history.

---

## Section 1: Interactive Course Picker (no args)

When invoked without arguments, check for an existing analysis plan first, then present courses.

### Step 1a: Check for existing analysis plan

```bash
echo '{"project_path": ".", "type": "analysis"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py load
```

If a plan is found (returned `"found": true`):

Read the saved recipe to get `modules_run`, `genre`, `chapters_analyzed`, and `course_selections`.

Tell the user:

> "You analyzed this project before — {modules_run_count} modules, {chapters_analyzed} chapters. Run again, or adjust?"

Use AskUserQuestion:
- **Run again** — Re-run the same modules, skip fresh results
- **Re-run everything** — Re-run all modules including fresh results (`--force`)
- **Adjust** — Pick different courses or add/remove modules
- **Single course** — Run just one course

If "Run again" or "Re-run everything": jump to Step 1e using saved course selections.

If "Adjust" or "Single course": continue to Step 1b.

If no plan found: continue to Step 1b.

### Step 1b: Detect genre

Attempt to read project genre from `index.codex.yaml` or any `.codex.yaml` file in the current directory:

```bash
echo '{}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py list | head -20
```

Also check `index.codex.yaml` for a `genre` or `type` field.

If genre is readable, note it (e.g., `literary_fiction`, `thriller`, `fantasy`, `nonfiction`, `poetry`).

If genre is not available, proceed without it — the user will pick courses manually.

### Step 1c: Load course groupings

```bash
echo '{}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/module_loader.py courses
```

This returns the five courses with their module lists.

### Step 1d: Present course picker

Use AskUserQuestion to show the courses. Describe what each covers:

> "Which analysis courses would you like to run?"

Options (allow multi-select by listing them separately):
- **Quick taste** — summary, characters, tags. Fast overview of each chapter.
- **Slow roast** — three-act structure, story beats, pacing, hero's journey. Root-level structural analysis.
- **Spice rack** — writing style, language style, rhythm, clarity. Craft-level analysis per chapter.
- **Simmering** — thematic depth, reader emotions, Jungian analysis, relationships, dream symbolism, immersion. Deep per-chapter analysis.
- **Immersive** — immersive design, immersion, reader emotions, pacing. Experiential design for dome shows and projection work.
- **All courses** — Run everything above.

If genre was detected, note the recommended courses based on genre:

```bash
echo '{"genre": "DETECTED_GENRE"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/module_loader.py recommend
```

For example: "For literary fiction, I'd recommend Quick taste + Slow roast + Spice rack + Simmering."

After the user selects, confirm the full module list before running:

> "Running {N} modules across {M} chapters. This covers {course_names}."

Use AskUserQuestion to confirm:
- **Run** — Proceed
- **Adjust** — Modify selection

### Step 1e: Run selected courses

For each selected course, find all `.codex.yaml` and `.codex.md` files in the project:

Use the Glob tool to find all codex files:
- Pattern: `**/*.codex.yaml` — exclude any paths under `.chapterwise/`
- Pattern: `**/*.codex.md` — exclude any paths under `.chapterwise/`

For "Quick taste" (per-chapter modules on all files):

Progress message:
> "Quick taste... summary, characters, tags on {N} chapters."

Spawn parallel Task agents — one per module — each running that module on all chapters:

```
Task 1: Run summary on all chapters
Task 2: Run characters on all chapters
Task 3: Run tags on all chapters
```

> "Running in parallel... done."

For "Slow roast" (root-level structural modules — run on the index or full manuscript):

Progress message:
> "Slow roasting structure... three-act, story beats, pacing."

Run on index.codex.yaml or a combined manuscript view. These are root-level and do not run per-chapter.

For "Spice rack" (per-chapter craft modules):

Progress message:
> "Spice rack... writing style, language, rhythm on {N} chapters."

Spawn parallel Task agents per module.

For "Simmering" (per-chapter depth modules):

Progress message:
> "Simmering thematic analysis... emotions, Jungian, relationships."

Spawn parallel Task agents per module.

For "Immersive" (per-chapter experiential modules):

Progress message:
> "Mapping immersive design... effects, rhythm, comfort on {N} chapters."

Spawn parallel Task agents per module.

Each parallel task follows the module execution process defined in Section 2.

### Step 1f: Save plan

After all modules complete, save the analysis plan:

```bash
echo '{"project_path": ".", "type": "analysis"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py create
```

Then update the plan with details:

```bash
echo '{"recipe_path": ".chapterwise/analysis-recipe", "updates": {"modules_run": MODULES_LIST, "genre": "GENRE", "chapters_analyzed": N, "course_selections": COURSES_LIST}}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py update
```

Save this silently — no user-facing message about saving.

### Step 1g: Export reports

Per **Step 0c**, a course run exports reports too — one per module per file. Settings
decide the format and folder; the script reads them itself.

Say the shape before starting, since a course run multiplies:

> "3 modules across 28 chapters — 84 reports into `analysis/`."

Batch the exports with the Task tool the same way the analyses were batched. Report the
total once when they land, not per file.

Skip entirely if `report` is `false` or `--no-report` was passed.

### Step 1h: Offer to save the defaults

Per **Step 0d** — once, at the end, only if nothing was configured yet.

### Step 1i: Validate and report

Run validation (Section 8) then report:

> "Done. {modules_run_count} modules across {chapters_analyzed} chapters, {R} reports."

---

## Section 2: Direct Analysis — `analysis <module> [file]`

This is the core single-module execution path. All batch and course execution eventually calls this logic per module per file.

### Step 2a: Resolve the module

Load the module definition:

```bash
echo '{}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/module_loader.py list
```

Find the module named `<module>` in the results. If not found, say:

> "Module '{module}' not found. Run `analysis list` to see available modules."

Read the module's `_filepath` to get the full module prompt.

### Step 2b: Resolve the file

If `[file]` is provided, use it directly.

If not provided:
- Check if there is a single `.codex.yaml` or `.codex.md` file in the current directory — if so, use it.
- Otherwise, use AskUserQuestion to ask which file to analyze.

### Step 2c: Check staleness

Before running analysis, check whether fresh results already exist:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/staleness_checker.py SOURCE_FILE MODULE_NAME
```

If `isStale` is `false` and `--force` is not set:

> "Fresh results exist for {module} on {filename}. Re-run anyway?"

Use AskUserQuestion:
- **Skip** — Use existing results
- **Re-run** — Force re-analysis

If `isStale` is `true`, proceed without asking.

### Step 2d: Read the settings, scan the structure, then propose

**Read the project's settings first — Step 0a.** Anything already configured is not a
question, per the table in Step 0b.

**Scan before asking anything else.** A manuscript's shape determines what a useful
question even is, and this is cheap — structure only, never full content.

```bash
echo '{"path": "SOURCE_FILE"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/codex_scan.py scan
```

Returns per-depth counts and types, how many nodes at each level carry content, root
attributes, and `suggestedDepth` with `suggestedReason`.

If the file is a single node (`totalNodes: 1`), there is nothing to decide — use `root`
and say nothing. Most chapters are this case.

If it has analyzable structure, **state the shape and propose**, with the numbers that
justify the proposal:

> Chrysalis — 9 acts, 36 beats, 36:00, Planetarium Dome Show.
> Suggest whole-show plus beat-by-beat: 37 passes. Report as markdown.

Then **one AskUserQuestion call carrying two questions** — depth and report format —
each with the proposal already selected:

| Question | Header | Options |
|---|---|---|
| How deep? | `Depth` | **Run it** (the proposed depth) · **Whole show only** (1 pass) · **Every leaf** · **Change depth** |
| Report? | `Report` | **Markdown** · **Codex** · **Both** · **No report** |

**One call, not three exchanges.** Per `references/principles.md`, the agent decides and
the user overrides — the proposal is pre-selected, so accepting both is one keystroke.
What is not acceptable is *stating* a format in prose and never offering the other one:
the format is a choice, and the user makes it.

Format guidance, if asked: **Markdown** reads like a document and is what most writers
want. **Codex** is structured — it re-imports, renders in the web app, and can be
analyzed further. **Both** costs nothing extra; the report is a re-render of results
already on disk, not a second analysis.

**Two things suppress a question: a flag, and a setting** — see Step 0b. If every value
is either flagged or configured, ask nothing and run. Say which in one clause: "Report as
codex, per your settings."

### Step 2e: Resolve the nodes to analyze

```bash
echo '{"path": "SOURCE_FILE", "depth": "DEPTH"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/codex_scan.py nodes
```

`depth` accepts `root`, an integer, `leaf`, `auto`, `all`, or a comma list. `root,leaf`
is the common choice for a script — whole-show synthesis plus every scene.

Returns each node in document order with `scope`, `name`, `path`, `depth`, `index`, and
its `content`. Analyze **that content**, not the whole file.

### Step 2f: Load module prompt

Read the module's full prompt content from `_content` field (the body of the module's `.md` file after the frontmatter).

Also read the shared output format partial:

Read the output format spec at `${CLAUDE_PLUGIN_ROOT}/modules/_output-format.md` using the Read tool.

### Step 2g: Run analysis

For each node returned by Step 2e, apply the module's prompt to that node's content and
produce a result matching the module's output format.

**Modules that define more than one output shape select by scope.** `immersive_design`
is the current example: `scope: root` takes its whole-show shape (arc map, motion
budget, breath coverage, the landing); `scope: node:*` takes its scene shape (effects in
play, proposed effects, rhythm and breath, comfort and load). Read the module's own
Scope section and follow it.

At 3 or more nodes, batch with the Task tool — one agent per group of nodes, per the
existing convention in Section 6.

If `--dry-run` is set, show what would be analyzed without writing results:

> "Dry run: {N} nodes, {module}, depth {depth}."

Stop here if dry-run.

### Step 2h: Write results

One writer call per node, carrying that node's scope:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analysis_writer.py SOURCE_FILE MODULE_NAME - \
  --model "YOUR_ACTUAL_MODEL" \
  --scope "node:NODE_ID" --scope-name "NODE_NAME" --scope-path "A › B › C" \
  --scope-depth N --scope-index I < RESULT_JSON
```

For a whole-file analysis, omit every `--scope*` flag.

All results go into the one `{source_basename}.analysis.json` sibling. Each scope keeps
its own history, so analyzing beat 12 never touches beat 11.

**`--model` is required of you.** Report the model you actually are. It is a provenance
record — an unreported model is written as `unknown`, which is honest; a wrong name is
not. Never copy the example.

### Step 2i: Export the report

Skip if the user declined or `--no-report` was passed.

```bash
echo '{"source": "SOURCE_FILE", "module": "MODULE_NAME", "format": "markdown"}' \
  | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analysis_report.py
```

`format` is `markdown`, `codex`, or `both` — whichever the user chose in Step 2d. The
report is assembled from what was just written to `.analysis.json`: it re-reads from
disk and never calls a model, so it costs nothing and cannot drift from the stored
results.

Lands in `{source_dir}/analysis/{slug}-{module}-{YYYY-MM-DD}.{md|codex.yaml}`. With
`both`, the two files share one stem and `paths` lists them in order.

**Codex output goes through `/chapterwise:format`.** The script hands the assembled
document to `CodexAutoFixer` — the same engine behind the format command — before
writing, then validates the result against the Codex V1.3 schema. This is not optional
politeness: a generator that imitates its own format command drifts from it. Nothing to
invoke by hand; it is wired into the codex renderer.

Every write reports `valid` and `issues`. If `valid` is `false`, say so with the first
issue and the file it came from — a report that does not parse as codex is a bug, not a
formatting preference:

> "Report written, but it does not validate: {issue}"

If the script returns `"status": "exists"`, ask before overwriting:

> "Report already exists: {path} — overwrite?"

Re-run with `"force": true` if the user agrees. With `both`, a collision in *either*
format blocks the write, and `paths` names the ones already there.

`--report-only` runs this step alone, with no analysis. Use it to regenerate a report or
switch format without spending anything.

### Step 2j: Offer to save the choice — once

Per **Step 0d**. Skip entirely if `found` was `true` or the answers match what was already
configured — a configured project is never asked again. Confirm in one line:
`"Saved to .chapterwise/settings.json."`

Also record the run in the recipe, as before — that is run history, not configuration:

```bash
echo '{"recipe_path": ".chapterwise/analysis-recipe", "updates": {"modules_run": [...], "chapters_analyzed": N}}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py update
```

Save the recipe silently.

### Step 2k: Confirm

> "Done. {module}, {N} passes — 1 show, 36 beats. Report: {path}"

Or if part of a batch, proceed without per-file output (progress is reported at batch level).

---

## Section 3: Module List — `analysis list`

Show all available modules grouped by course.

### Step 3a: Load courses and modules

```bash
echo '{}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/module_loader.py courses
echo '{}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/module_loader.py list
```

### Step 3b: Display grouped by course

Show modules under their course header. For modules not in any course, show under "Other":

```
Quick taste
  summary            — Chapter summary and key points
  characters         — Character identification and traits
  tags               — Content tags and themes

Slow roast
  three_act_structure — Three-act structural analysis
  story_beats        — Scene-by-scene story beats
  story_pacing       — Pacing and momentum analysis
  heros_journey      — Hero's journey mapping

Spice rack
  writing_style      — Voice and writing style analysis
  language_style     — Language patterns and register
  rhythmic_cadence   — Sentence rhythm and flow
  clarity_accessibility — Readability and clarity

Simmering
  thematic_depth     — Thematic layers and motifs
  reader_emotions    — Emotional arc and impact
  jungian_analysis   — Jungian archetypes and shadow
  character_relationships — Relationship dynamics
  dream_symbolism    — Dream and symbolic content
  immersion          — Immersive quality assessment

Immersive
  immersive_design   — Effects, rhythm, and comfort for dome and projection work
  immersion          — Immersive quality assessment
  reader_emotions    — Emotional arc and impact
  story_pacing       — Pacing and momentum analysis

Other
  [remaining modules not in a course]
```

Include the module's `description` field from its frontmatter.

---

## Section 4: Module Help — `analysis help <module>`

Show detailed information about a specific module.

### Step 4a: Load module

```bash
echo '{}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/module_loader.py list
```

Find the requested module.

### Step 4b: Display details

Show:
- Module name and description
- Category
- What it analyzes (from module content)
- Output format summary
- Example invocation: `analysis {module} path/to/chapter.codex.yaml`

If module not found:
> "Module '{module}' not found. Run `analysis list` to see available modules."

---

## Section 5: Genre-Aware Planning — `analysis --plan`

Build a recommended analysis plan for this project without running anything.

### Step 5a: Detect genre

Read `index.codex.yaml` or any project metadata to find the manuscript type/genre. If not found, use AskUserQuestion:

> "What kind of manuscript is this?"

Options:
- **Literary fiction** — Character-driven prose
- **Thriller / mystery** — Plot-driven, tension-focused
- **Fantasy / sci-fi** — World-building and character
- **Non-fiction** — Essays, memoir, reference
- **Poetry** — Verse and lyric prose
- **Other** — Let me describe it

### Step 5b: Get genre-specific recommendations

```bash
echo '{"genre": "DETECTED_GENRE"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/module_loader.py recommend
```

### Step 5c: Count chapters

Use the Glob tool to count codex files:
- Pattern: `**/*.codex.yaml` — exclude `.chapterwise/` paths
- Pattern: `**/*.codex.md` — exclude `.chapterwise/` paths

### Step 5d: Present the plan

Show the recommended modules grouped by course, skipped modules with reasons, and estimated scope:

```
Scanning manuscript... {genre}, {chapter_count} chapters.
{N} modules selected, {M} skipped.

Quick taste      — summary, characters, tags ({chapter_count} chapters)
Slow roast       — three-act structure, story beats, pacing (root-level)
Spice rack       — writing style, language, rhythm ({chapter_count} chapters)
Simmering        — thematic depth, emotions, Jungian ({chapter_count} chapters)
Immersive        — immersive design, immersion, pacing ({chapter_count} chapters)

Skipped: {skipped_module_1} ({reason}), {skipped_module_2} ({reason})
```

Use AskUserQuestion to confirm or adjust:
- **Run this plan** — Execute immediately
- **Adjust** — Add or remove modules
- **Save without running** — Save the plan for later

### Step 5e: Save the plan

If user confirms, save:

```bash
echo '{"project_path": ".", "type": "analysis"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py create
echo '{"recipe_path": ".chapterwise/analysis-recipe", "updates": {"genre": "GENRE", "modules_recommended": MODULES, "modules_skipped": SKIPPED}}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py update
```

If user chose "Run this plan", proceed to execute each course following Section 1e logic —
which includes report export (Step 0c) and the one-time save offer (Step 0d).

Include the report count in the plan summary before running, so the scope is stated up
front:

> "{N} modules × {M} chapters — {N×M} analyses, {N×M} reports into `analysis/`."

---

## Section 6: Batch Analysis — `--all` and `--glob`

### `analysis <module> --glob "pattern"`

Run a single module on all files matching the glob pattern.

```bash
# Discover matching files
```

Use Glob tool to find files matching the pattern. For each matched file, run the module via
Section 2 logic — settings resolved once up front (Step 0a), a report per file (Step 0c),
and the save offer once at the very end (Step 0d), never per file.

For large batches (10+ files), spawn parallel Task agents:

> "Running {module} on {N} files in parallel..."

```
Task 1: Run {module} on files 1-{batch_size}
Task 2: Run {module} on files {batch_size+1}-{batch_size*2}
...
```

### `analysis --all [--glob "pattern"] [--node node_id]`

Run all available modules on a file or set of files.

If `--glob` is specified, match files from the pattern.
If `--node` is specified, find the file with that node ID in `index.codex.yaml`.
If neither, use the current directory.

Load all modules:

```bash
echo '{}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/module_loader.py list
```

For each module, run it on each file following Section 2 logic. Settings apply here exactly
as they do to a single file: resolve once (Step 0a), export a report per module per file
(Step 0c), offer to save once at the end (Step 0d).

Spawn parallel Task agents per module for efficiency:

> "Running {N} modules on {M} files in parallel..."

State the report volume before starting — `--all` across a folder multiplies fast:

> "33 modules × 28 chapters — 924 analyses. `--no-report` if you don't want a report for
> each."

### `--force` flag

Skip staleness check. Re-run analysis even if fresh results exist.

### `--dry-run` flag

Show what would be run without executing:

> "Dry run: {N} modules on {M} files."
> "Would run: {module_list}"

No analysis is performed, no files written.

---

## Section 7: Re-Analysis Detection

Before running any module batch (courses or `--all`), report staleness across all target files:

For each file and module combination:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/staleness_checker.py FILE_PATH MODULE_NAME
```

Aggregate results:

> "Found existing analysis for {N} of {M} chapters. {K} are stale."

If any are fresh (not stale) and `--force` is not set, use AskUserQuestion:
- **Re-analyze stale only** — Skip fresh results, only run where `isStale: true`
- **Re-analyze everything** — Force all modules regardless of staleness

This check runs once before batch execution begins. Individual staleness checks (Section 2c) are suppressed during batch runs to avoid repeated prompts.

---

## Section 8: Validation and Self-Healing

Run after every analysis run — single module or full course batch. This step is silent on success.

### Step 8a: Validate output files

For each `.analysis.json` written during this run:

1. Parse as JSON — if invalid JSON, regenerate from the in-memory analysis result.
2. Verify required Codex V1.3 structure:
   - Root has `id`, `type: "analysis"`, `attributes` array, `children` array
   - Each module child has `type: "analysis-module"`, `id` matching module name
   - Each entry child has `type: "analysis-entry"`, `sourceHash` in attributes
3. Verify `sourceHash` in the latest entry matches current chapter content hash.

To verify sourceHash:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/staleness_checker.py SOURCE_FILE MODULE_NAME
```

If `currentHash` does not match the `sourceHash` stored in the entry, the result is stale.

### Step 8b: Cross-check with plan

If an analysis plan exists, verify:
- Module counts match what was planned
- No modules are missing from the output that were expected

```bash
echo '{"project_path": ".", "type": "analysis"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py load
```

### Step 8c: Validate plan integrity

```bash
echo '{"recipe_path": ".chapterwise/analysis-recipe"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_validator.py
```

### Step 8d: Auto-heal

Apply fixes automatically when safe:

| Issue | Auto-fix |
|-------|---------|
| Missing `generated` timestamp | Add current UTC time |
| Missing `sourceHash` in entry | Recalculate from source content |
| Stale hash (source changed since analysis) | Mark entry `analysisStatus: stale`, flag for re-analysis |
| Invalid JSON in `.analysis.json` | Regenerate from in-memory result |
| Missing required root attributes | Restore from source file metadata |

### Step 8e: Report

- If all clean: say nothing — validation is invisible.
- If auto-fixed: "Refreshed {N} stale results."
- If issues remain that cannot be auto-fixed: stop and surface exact files:

> "Chapter 5 analysis is incomplete — re-running {module} module."

Then re-run the affected module via Section 2 logic.

---

## Section 9: Error Handling

### Module not found

> "Module '{name}' not found. Run `analysis list` to see available modules."

### Source file not found

> "File not found: {path}"

If `--glob` returned no matches:
> "No files matched pattern: {pattern}"

### Analysis writer failure

> "Could not save results for {filename} — {error}. Retrying..."

If retry also fails, report the file and continue with remaining files.

### Partial batch failure

> "{N} chapters had issues — {list of files}."

Complete all chapters that succeed. Do not silently skip failed chapters.

### Dependency errors

If PyYAML is missing:
> "Missing PyYAML. Install with: `pip3 install pyyaml`"

---

## Section 10: Language Rules

Read and follow `${CLAUDE_PLUGIN_ROOT}/references/principles.md` — especially **LLM Judgment, User Override**.
Follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all shared messaging rules.

**Analysis-specific phases:**

| Phase | Verb | Example |
|-------|------|---------|
| Scan manuscript | Scanning | "Scanning manuscript... literary fiction, character-driven." |
| Quick taste course | Quick taste | "Quick taste... summary, characters, tags on 28 chapters." |
| Slow roast course | Slow roasting | "Slow roasting structure... three-act, story beats, pacing." |
| Spice rack course | Spice rack | "Spice rack... writing style, language, rhythm on 28 chapters." |
| Simmering course | Simmering | "Simmering thematic analysis... emotions, Jungian, relationships." |
| Immersive course | Mapping | "Mapping immersive design... effects, rhythm, comfort on 28 chapters." |
| Parallel execution | Running in parallel | "Running in parallel... done." |
| Scan structure | Scanning | "Scanning structure... 9 acts, 36 beats, 36:00." |
| Per-node analysis | Running | "Running immersive_design... 1 show, 36 beats." |
| Report export | Writing | "Writing report... analysis/chrysalis-immersive-design-2026-08-04.md" |
| Done | Done | "Done. 18 modules across 28 chapters." |

**Course names are the only branded cooking names.** Progress messages within a course use plain technical descriptions.

---

## Tool Usage Reference

**Script calls — always use stdin JSON piped to python3:**

```bash
# Module discovery
echo '{}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/module_loader.py list
echo '{}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/module_loader.py courses
echo '{"genre":"literary_fiction"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/module_loader.py recommend

# Plan management
echo '{"project_path":".","type":"analysis"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py create
echo '{"project_path":".","type":"analysis"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py load
echo '{"recipe_path":".chapterwise/analysis-recipe","updates":{}}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py update

# Staleness checking
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/staleness_checker.py path/to/file.codex.yaml module_name

# Writing results
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analysis_writer.py path/to/file.codex.yaml module_name - \
  --model "your-actual-model" --scope "node:UUID" --scope-name "Beat name" --scope-index 3 < result.json

# Structural scan and node resolution
echo '{"path":"file.codex.yaml"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/codex_scan.py scan
echo '{"path":"file.codex.yaml","depth":"root,leaf"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/codex_scan.py nodes

# Report export
echo '{"source":"file.codex.yaml","module":"immersive_design","format":"markdown"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analysis_report.py

# Settings
echo '{"source":"file.codex.yaml"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/settings.py resolve
echo '{"path":".","updates":{"analysis":{"report_format":"codex"}}}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/settings.py set
echo '{"source":"file.codex.yaml","module":"immersive_design","format":"both","force":true}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analysis_report.py

# Validation
echo '{"recipe_path":".chapterwise/analysis-recipe"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_validator.py
```

**User interaction — always use AskUserQuestion tool**, never inline text prompts. Every decision point requires a question with labeled options.

**Parallel work — use Task tool** for module batches (3+ modules or 10+ files). Each task is independent with no shared state. Collect results after all tasks finish.

**File operations — use Glob and Bash** to discover files. Use Read to load source content. Never modify source files.

---

## .analysis.json Output Schema

Each analysis run produces or updates a `.analysis.json` file using Codex V1.3 format:

```json
{
  "metadata": {
    "formatVersion": "1.3",
    "created": "2026-02-27T15:00:00Z",
    "updated": "2026-02-27T15:00:00Z"
  },
  "id": "chapter-01-analysis",
  "type": "analysis",
  "name": "Analysis Results",
  "attributes": [
    {"key": "sourceFile", "value": "chapter-01.codex.yaml"},
    {"key": "sourceHash", "value": "a1b2c3d4e5f67890"}
  ],
  "children": [
    {
      "id": "summary",
      "type": "analysis-module",
      "name": "Summary",
      "children": [
        {
          "id": "entry-20260227T150000Z",
          "type": "analysis-entry",
          "status": "published",
          "attributes": [
            {"key": "model", "value": "<the model that actually ran>"},
            {"key": "sourceHash", "value": "a1b2c3d4e5f67890"},
            {"key": "analysisStatus", "value": "current"},
            {"key": "timestamp", "value": "2026-02-27T15:00:00Z"}
          ],
          "body": "...",
          "summary": "..."
        }
      ]
    }
  ]
}
```

Key fields:
- `sourceHash` — SHA-256 of source content (first 16 chars). Used for staleness detection.
- `analysisStatus` — `"current"` (fresh) or `"stale"` (source changed since analysis).
- History depth — up to 3 entries per module, newest first. Older entries are demoted to `status: "draft"`.
