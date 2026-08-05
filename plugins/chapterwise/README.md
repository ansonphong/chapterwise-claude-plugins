# ChapterWise — the Claude Code plugin

A complete writing toolkit for Claude Code. Import a manuscript from almost any format, run editorial analysis across 33 modules, synthesize a story atlas, and build a static reader — all against plain-text files you own, tracked in Git.

24 slash commands. No account, no lock-in, no server. Your manuscript stays on your disk in open formats.

---

## Table of Contents

- [Install](#install)
- [Quick start](#quick-start)
- [Core concepts](#core-concepts)
  - [The Codex format](#the-codex-format)
  - [Codex Lite](#codex-lite)
  - [Project layout](#project-layout)
  - [Saved configuration and staleness](#saved-configuration-and-staleness)
  - [Preferences](#preferences)
- [Command reference](#command-reference)
  - [The pipeline](#the-pipeline)
    - [`/import`](#import)
    - [`/import-scrivener`](#import-scrivener)
    - [`/analysis`](#analysis)
    - [`/atlas`](#atlas)
    - [`/reader`](#reader)
    - [`/pipeline`](#pipeline)
    - [`/status`](#status)
  - [Research](#research)
    - [`/research`](#research-1)
    - [`/research-deep`](#research-deep)
  - [Authoring](#authoring)
    - [`/format`](#format)
    - [`/markdown`](#markdown)
    - [`/diagram`](#diagram)
    - [`/spreadsheet`](#spreadsheet)
    - [`/index`](#index)
  - [Structure](#structure)
    - [`/explode`](#explode)
    - [`/implode`](#implode)
    - [`/insert`](#insert)
  - [Conversion](#conversion)
    - [`/convert-to-codex`](#convert-to-codex)
    - [`/convert-to-markdown`](#convert-to-markdown)
  - [Maintenance](#maintenance)
    - [`/generate-tags`](#generate-tags)
    - [`/update-word-count`](#update-word-count)
    - [`/format-folder`](#format-folder)
    - [`/format-regen-ids`](#format-regen-ids)
  - [Internal](#internal)
    - [`/feedback-inbox`](#feedback-inbox)
- [Analysis modules](#analysis-modules)
  - [Courses](#courses)
  - [All 33 modules](#all-33-modules)
  - [The `.analysis.json` format](#the-analysisjson-format)
  - [Writing your own module](#writing-your-own-module)
- [Requirements](#requirements)
- [Conventions](#conventions)

---

## Install

```
/plugin marketplace add ansonphong/chapterwise-plugins
/plugin install chapterwise@chapterwise-plugins
```

Restart Claude Code to load the commands.

Every command works in two forms. Use the namespaced form when you have other plugins installed and a bare name might collide:

```
/import              # bare
/chapterwise:import  # namespaced — always unambiguous
```

Most commands also respond to natural language. `"import my novel"`, `"build atlas"`, and `"regenerate ids"` reach `/import`, `/atlas`, and `/format-regen-ids` respectively.

For local development, point `--plugin-dir` at the plugin directory:

```bash
claude --plugin-dir /path/to/chapterwise-plugins/plugins/chapterwise
```

---

## Quick start

From zero to a browsable manuscript in one command:

```
/pipeline my-novel.pdf
```

That runs import → analysis → atlas → reader end to end. Or take it a step at a time:

```
/import my-novel.pdf     # PDF becomes a folder of chapter files
/analysis                # pick which editorial lenses to run
/atlas                   # synthesize characters, timeline, themes
/reader                  # build a static HTML reader
/status                  # see what's fresh and what's stale
```

Everything writes plain files into your project. Commit them, push them, open them in any editor.

---

## Core concepts

### The Codex format

`.codex.yaml` is a recursive, typed document format. One structure describes a chapter, a character, a location, a recipe, a meeting note — anything. Only `metadata.formatVersion` is strictly required; everything else is optional.

```yaml
metadata:
  formatVersion: "1.3"
  documentVersion: "1.0.0"

id: "3f2a9c14-7b8e-4d21-a6f5-0c9e13b8a742"
type: "chapter"              # any type you want — character, location, recipe...
name: "The Long Way Home"
summary: "Elena returns to a city that no longer recognizes her."
status: draft                # published | private | draft

body: |
  Extended prose content in Markdown...

attributes:                  # typed key/value data
  - key: word_count
    name: "Word Count"
    value: 3412
    dataType: int

tags: ["homecoming", "elena"]

children:                    # same structure, recursively
  - id: "..."
    type: "scene"
    name: "Arrival"

relations:
  - targetId: "..."
    kind: "references"
```

**Field selection.** Use `attributes` for key/value data, `body` for prose, `children` for hierarchy, `content` for laid-out sections, and `include` to pull in another file.

**The `content` array (V1.3).** For laid-out documents — side-by-side sections, embedded diagrams, embedded spreadsheets:

```yaml
content:
  - key: system-flow
    name: "System Architecture"
    type: diagram          # text | blockquote | diagram | spreadsheet
    width: 1/1             # 1/1 | 1/2 | 1/3 — defaults to 1/2
    value: |
      flowchart TD
        A[Client] --> B[API]
  - key: budget
    type: spreadsheet
    width: 1/1
    include: /data/budget.spreadsheet.yaml
```

Each item takes either `value` (inline) or `include` (external file). `include` resolves `.codex.yaml`, `.mermaid`, `.mmd`, `.csv`, `.xlsx`, and `.spreadsheet.yaml`. An unknown `type` falls back to text rendering rather than erroring.

**Include paths.** A leading `/` resolves from the Git project root. A leading `./` resolves relative to the current file.

**Version policy.** Formats 1.0 through 1.3 are all valid. Tools repair integrity; they never silently migrate a document between versions. Don't rewrite `formatVersion` on an older document just to modernize it.

### Codex Lite

`.codex.md` (or plain `.md`) is Markdown with YAML frontmatter — the flat, human-friendly alternative when you don't need hierarchy:

```markdown
---
type: chapter
name: "The Long Way Home"
summary: "Elena returns to a city that no longer recognizes her."
tags: homecoming, elena
status: draft
word_count: 3412
---

# The Long Way Home

Elena stepped off the train...
```

Lite is the default output of `/import` because most writers want editable Markdown. Move up to full Codex when you need nested children or entity relations. `/convert-to-codex` and `/convert-to-markdown` move documents between the two.

### Project layout

A ChapterWise project is a Git repository with an `index.codex.yaml` at its root:

```
my-novel/
├── index.codex.yaml          # project entry point — discovery, display, hierarchy
├── chapter-01-arrival.md
├── chapter-02-the-ridge.md
├── atlas/                    # built by /atlas
│   ├── index.codex.yaml
│   ├── characters.codex.yaml
│   ├── timeline.codex.yaml
│   └── themes.codex.yaml
├── reader/                   # built by /reader
│   ├── index.html
│   ├── style.css
│   └── manifest.json
├── chapter-01-arrival.analysis.json    # written by /analysis, sits beside its chapter
└── .chapterwise/             # saved config — see below
```

`index.codex.yaml` holds gitignore-style `patterns.include` / `patterns.exclude` discovery rules, a `display` block (`defaultView`, `sortBy`, `groupBy`), per-type `typeStyles` (emoji and color), and optionally an explicit `children` tree.

Two rules worth internalizing:

- **Never create `.index.codex.yaml`** (leading dot). That's a system-generated cache. You create `index.codex.yaml`.
- **Status does not inherit.** A folder marked `published` does not publish its children. Every item sets its own `status`, defaulting to `private`.

### Saved configuration and staleness

The first time you run `/import`, `/analysis`, `/atlas`, or `/reader`, the plugin saves how you configured it under `.chapterwise/`. Every subsequent run reads that config back, so it never re-interviews you and never redoes finished work.

Freshness is hash-based. Each analysis records a `sourceHash` of the chapter it read. Re-running compares hashes and skips anything unchanged. This is what makes `/atlas --update` cheap: revise two chapters out of thirty, and only those two get re-analyzed and only the affected atlas sections get re-synthesized.

Pass `--force` to any analysis run to ignore freshness and redo everything.

### Preferences

Project-level preferences live in `.claude/chapterwise.local.md` in *your* project (not in the plugin). Currently used by the research commands:

```markdown
---
research:
  format: codex-md          # codex-md | codex-json
  default_depth: standard   # standard | deep
  output_path: .chapterwise/research/
---
```

Resolution order, lowest to highest: plugin defaults → `chapterwise.local.md` → command variant → language in your prompt. Nothing is asked on first run that has a sane default.

---

## Command reference

### The pipeline

#### `/import`

**Turn any manuscript into a ChapterWise project.**

```
/import [path/to/file-or-folder]
```

Detects the source format, scans it for chapter structure, asks only the questions that actually change the outcome, converts, validates, and writes a clean project. Your source file is never modified.

**Supported formats**

| Source | Dependency |
|---|---|
| PDF | `pymupdf` |
| DOCX | `python-docx` |
| Scrivener 3 | `lxml` |
| Ulysses | none |
| Plain text | none |
| Folder of Markdown | none |
| HTML | `beautifulsoup4` |

Anything else falls through to a custom-converter path: Claude reads the existing converters under `patterns/`, writes one tailored to your source, tests it on a sample, and saves it for reuse.

**What it asks you** — and only when it matters:

1. **Organization** (only if multi-level structure is detected) — folders per part, or flat files
2. **Metadata preservation** (Scrivener/Ulysses only) — keep labels and status, keywords as tags, or start clean
3. **Output format** (only if it can't infer) — Markdown/Codex Lite (default) or Codex YAML
4. **Front and back matter** (only if detected) — fold into project metadata, break out as files, or skip

It never asks about file naming (always slugified), IDs (always UUID), word counts (always calculated), tags (always generated), summaries (always extracted from the first paragraph), or the index file (always generated).

**Outputs**

```
output-dir/
├── index.codex.yaml
├── chapter-01-the-awakening.md
├── chapter-02-...
└── .backups/                # created before overwriting on re-import
```

**Examples**

```
/import ~/manuscripts/my-novel.pdf
```
> 342-page PDF → detects chapter boundaries, interviews, converts, validates, writes a Markdown project.

```
/import ./scrivener-project
```
> Triggers the Scrivener metadata question; preserves labels, status, and keywords as frontmatter and tags.

```
/import ./my-novel
```
> Already imported. If the source hash is unchanged, reports it's up to date and does nothing. If changed, re-runs the saved converter and reports only the deltas.

**Notes** — For 20+ chapters, conversion parallelizes across subagents. A chapter that fails conversion is retried with a different heading pattern, split strategy, or encoding; if it still fails it's flagged for manual review and the rest continue. Validation auto-fixes missing fields, bad UUIDs, and orphaned files; anything unfixable stops the run and is reported with the exact file and error.

---

#### `/import-scrivener`

**Import a Scrivener 3 project, skipping format detection.**

```
/import-scrivener [path/to/Project.scriv]
```

A specialization of `/import`, not a competitor. It follows the same workflow with four differences: format detection is skipped, `scrivener_converter.py` is used directly, Scrivener metadata preservation is enabled by default, and the binder maps explicitly to ChapterWise hierarchy.

| Scrivener | ChapterWise |
|---|---|
| Manuscript folder | Project root |
| Sub-folders | Parts / acts |
| Text documents | Chapters / scenes |
| Research folder | Skipped unless you ask for it |

Pick this when you know the source is a `.scriv` bundle. Pick `/import` for anything else or when you're unsure.

**Examples**

```
/import-scrivener ~/Documents/MyNovel.scriv
```
> Full binder import with labels, status, keywords, and synopsis preserved.

**Notes** — Scrivener 3 only. Requires `lxml` and a valid `.scrivx` manifest inside the bundle. If RTF conversion fails on specific documents, export those as plain text from Scrivener first.

---

#### `/analysis`

**Run editorial analysis across your manuscript.**

```
/analysis                              # interactive course picker
/analysis <module> [file]              # one module, one chapter
/analysis list                         # every module, grouped by course
/analysis help <module>                # what a module does
/analysis --plan                       # genre-aware recommendations
/analysis --all [--glob <pattern>]     # every module across matched files
/analysis <module> --glob <pattern>    # one module across matched files
```

| Flag | Effect |
|---|---|
| `--force` | Ignore freshness, re-run even where results exist |
| `--dry-run` | Show what would run, write nothing |
| `--glob <pattern>` | Target files by glob |
| `--node <node_id>` | With `--all`, target the file with that node ID in the index |

**How it works.** Each module is a prompt — a specific editorial lens. Run with no arguments and you get a multi-select course picker. Results are written to `{chapter}.analysis.json` beside each chapter, keeping up to three historical entries per module (newest first; older ones demoted to `draft`). Your manuscript files are never modified.

Structural modules in the Slow roast course (three-act, story beats, pacing, hero's journey) run once against the whole manuscript. Everything else runs per chapter.

Before any batch, freshness is aggregated and reported once — you're asked whether to re-analyze only stale chapters or everything, rather than being prompted per file.

**Examples**

```
/analysis
```
> Detects genre from the index, offers the courses, runs your selection in parallel across every chapter, saves the plan.

```
/analysis characters chapter-03.codex.yaml
```
> One lens, one chapter. Checks freshness first, writes `chapter-03.analysis.json`.

```
/analysis --all --glob "chapters/*.codex.yaml"
```
> Every module across every matched chapter, parallelized per module.

```
/analysis plot_holes --glob "**/*.md" --force
```
> One lens across the whole manuscript, ignoring cached results.

See [Analysis modules](#analysis-modules) for the full catalog.

**Notes** — Validation runs after every analysis and is silent on success. It verifies Codex V1.3 structure, confirms `sourceHash` matches current content, and self-heals missing timestamps, stale hashes, and malformed JSON. Anything it can't fix triggers a targeted re-run of just that module.

---

#### `/atlas`

**Synthesize a cross-referenced story atlas from your manuscript.**

```
/atlas                          # build (interactive)
/atlas --update                 # re-analyze only what changed
/atlas --name "World Atlas"     # named atlas in its own folder
/atlas --add-sections           # extend an existing atlas
/atlas --list                   # show all atlases in the project
/atlas --rebuild                # delete and rebuild from scratch
/atlas --delete                 # remove an atlas
```

An atlas is a standalone reference document synthesized from the whole manuscript: who everyone is, what happened when, which themes run where, how the plot is shaped. It's the thing you reach for in chapter 27 when you can't remember what color you said someone's eyes were in chapter 3.

**Four passes**

| Pass | What happens |
|---|---|
| 0 — Scan | Read the index, sample chapters, detect genre and scale, propose a layout |
| 1 — Extract | Subagents read chapters in batches with overlap, pulling out characters, locations, objects, factions, events; results deduplicated into an entity map |
| 2 — Analyze | Genre-appropriate analysis modules run across chapters (reusing anything already fresh) |
| 3 — Synthesize | One subagent per section condenses everything into the finished atlas |

**Sections** — proposed to fit the manuscript. Fiction gets characters, timeline, themes, plot structure, locations, relationships, and world. Non-fiction gets topic map, key arguments, chapter summaries, and source references. Poetry gets themes, imagery, devices, and emotional arc. Layouts scale: Simple (flat), Standard (one file per section), Detailed (nested subfolders).

**Outputs**

```
atlas/
├── index.codex.yaml
├── characters.codex.yaml
├── timeline.codex.yaml
├── themes.codex.yaml
├── plot-structure.codex.yaml
├── locations.codex.yaml
└── relationships.codex.yaml
```

Multiple atlases can coexist in one project, each with its own name and folder.

**Examples**

```
/atlas
```
> First run: scans, proposes a layout, runs all four passes, writes `atlas/`, asks before committing.

```
/atlas --update
```
> You revised chapters 5 and 12 and added 29–30. Hash-diffs, re-extracts only those four, selectively re-synthesizes the affected sections, patches in place.

```
/atlas --name "World Atlas" --add-sections
```
> Adds sections you skipped on the original build, synthesizing only the new ones.

**Notes** — Needs at least 3 chapters; below that, run individual `/analysis` modules instead. Pass 2 is the heaviest stage — work scales as chapters × modules, so a 28-chapter manuscript with 10 modules is 280 analysis passes on a full build. `--update` typically cuts that by an order of magnitude. Hand-written atlas content (`source: user`) is never overwritten by updates; only generated content is patched. `--rebuild` destroys hand-written content and confirms first. Nothing is ever pushed to a remote automatically.

---

#### `/reader`

**Build a static HTML reader for your project.**

```
/reader [project-path] [--template minimal|academic] [--atlas]
```

Produces a self-contained reading experience — navigation, search, light/dark toggle — that opens straight from the filesystem. No server, no account, no build step. Host it anywhere that serves static files, or just double-click it.

**Templates**

| Template | Character |
|---|---|
| **Minimal** | Clean sans-serif, sidebar navigation, light/dark toggle, search. Novels, short story collections, prose. |
| **Academic** | Serif typography, wider measure, footnote support, annotation margin. Essays, research, textbooks. |
| **Custom** | Describe the look you want — fonts, colors, layout, mood — and it generates the CSS. |

If your project has an atlas, the reader renders it: character cards with role badges and expandable profiles, a chronological timeline with act dividers, and a themes section with per-chapter cross-references.

**Outputs**

```
reader/
├── index.html          # open this
├── style.css
├── reader.js
├── manifest.json
└── atlas-data.json     # atlas projects only
```

Projects under 50 chapters embed content directly in `manifest.json`. Larger projects get per-chapter HTML files under `reader/chapters/`.

**Examples**

```
/reader
```
> Scans the project, asks which style, builds `reader/`.

```
/reader --template academic ~/novels/the-long-way-home
```
> Explicit path and template, no questions.

```
/reader --atlas
```
> Force atlas rendering on a project whose index isn't flagged as an atlas but contains atlas-structured content.

**Notes** — Requires an existing `index.codex.yaml`. Chapters referenced by the index but missing from disk produce a warning and the reader builds with what's there. Iterating on a custom design ("darker background", "bigger fonts") only touches the stylesheet — HTML and JS are left alone.

---

#### `/pipeline`

**Run the whole chain in one command.**

```
/pipeline [source-file] [--skip-reader] [--skip-atlas] [--skip-analysis]
```

Import → Analysis → Atlas → Reader, with sensible defaults chosen automatically at each step and any already-fresh step skipped.

| Flag | Result |
|---|---|
| *(none)* | All 4 steps |
| `--skip-reader` | 3 steps — stops after Atlas |
| `--skip-atlas` | 2 steps — stops after Analysis (this also skips Reader) |
| `--skip-analysis` | 1 step — import only |

In pipeline mode the sub-commands take their defaults rather than interviewing you: flat structure unless parts are detected, Markdown output, front matter excluded, genre-recommended analysis modules, "Story Atlas" or "Reference Atlas" per genre, minimal reader template. You're only asked when something is genuinely ambiguous.

Each step validates before the next begins, and each saves its own config independently — so re-running `/pipeline` resumes rather than restarts. A step that fails doesn't abort the run; you're asked whether to continue.

**Examples**

```
/pipeline my-novel.pdf
```
> Cold start to a browsable reader in one command.

```
/pipeline my-novel.pdf --skip-reader
```
> Import, analyze, and build the atlas; skip the HTML build.

```
/pipeline
```
> Re-run in an existing project. Skips fresh steps, re-runs only what your edits invalidated.

---

#### `/status`

**Show project state and staleness.**

```
/status
```

No arguments, no questions, no writes. A pure dashboard: title, chapter count, word count, per-step state, and what to do next.

| Icon | Meaning |
|---|---|
| `✓` | Fresh |
| `⚠` | Stale — source changed since this ran |
| `✗` | Not started |
| `◌` | Partial / in progress |

Staleness is computed per step: import compares the source file hash; analysis compares each `.analysis.json` `sourceHash` against current chapter content; atlas compares stored chapter hashes against current files; reader compares project structure against the built manifest.

Finds your project by looking for `index.codex.yaml` in the current directory and up to three levels above it.

---

### Research

#### `/research`

**Research a topic and write structured reference files.**

```
/research <topic or instruction>
```

Standalone by default — it researches the topic, not your manuscript, unless you ask it to. Output lands in `.chapterwise/research/`.

No flags. Everything is inferred from how you phrase the request:

| You write | It does |
|---|---|
| "deep dive", "comprehensive" | Deep treatment |
| "brief", "quick overview" | Standard treatment |
| "one file per god", "single document" | Obeys your structure exactly |
| "use web sources" | Forces web search |
| "from memory only", "no web" | Skips the web entirely |
| "relevant to my novel", "compare with chapter 5" | Reads your manuscript and blends it in |
| "save to research/mythology/" | Overrides the output path |

**Sourcing.** Well-known topics draw on model knowledge first, with the web filling gaps. Niche topics search by default. Anything time-sensitive always searches. Every page actually fetched is cited in `credits.webSources` with URL, title, and access timestamp — a fetch that fails is never cited. The model records its own attribution in `credits.models`; updates append rather than replace.

**Outputs** — `.codex.md` by default, or `.research.json` if you've set `research.format: codex-json`. A narrow topic gets one file; a broad one gets a folder with an overview plus subsections.

**Examples**

```
/research Sumerian gods
```
> One reference file, standard depth, model knowledge plus web where thin.

```
/research Sumerian gods relevant to my novel
```
> Reads your index and chapters, blends findings with your story's context.

```
/research use web sources, cyanide poisoning mechanism
```
> Forces web search regardless of topic familiarity, cites every source fetched.

**Notes** — If research on that topic already exists, you're asked whether to update it in place (preserving sections, bumping the timestamp, appending to `credits`) or create a dated new version. Referencing your manuscript when no project exists falls back to standalone with a note rather than erroring.

---

#### `/research-deep`

**Generate a multi-document compendium.**

```
/research-deep <topic or instruction>
```

Also reachable by saying `research:deep`.

Identical to `/research` in every mechanism — preferences, credits, manuscript awareness, format, validation — with three defaults flipped: depth is locked to deep, structure defaults to a folder of documents rather than one file, and web search is strongly favored.

**Outputs**

```
.chapterwise/research/trickster-gods/
├── overview.codex.md       # synthesizes patterns across all of them
├── loki.codex.md
├── anansi.codex.md
├── coyote.codex.md
├── hermes.codex.md
├── maui.codex.md
├── eshu.codex.md
└── sun-wukong.codex.md
```

**Examples**

```
/research-deep all trickster gods across world mythologies
```
> The compendium above — one file per figure, plus a synthesizing overview.

```
/research-deep trickster gods, but just a single file
```
> Deep content, single document. Your phrasing overrides the structural default.

```
/research-deep cyanide poisoning
```
> A topic that doesn't subdivide gets one comprehensive file rather than artificial splitting.

| | `/research` | `/research-deep` |
|---|---|---|
| Depth | Standard, judged per topic | Deep, locked |
| Structure | Single file or small folder | Folder with overview + per-entity files |
| Web search | Judged per topic | Favored by default |

---

### Authoring

#### `/format`

**Format content as Codex — or repair a codex file.**

```
/format [file.codex.yaml]
```

Two jobs in one command: turn arbitrary content into well-formed Codex, and fix existing Codex that has drifted. With a file argument it repairs; without one it creates from whatever you describe.

Applies the universal structure, picks a sensible `type`, generates real UUID v4 IDs and ISO-8601 timestamps (never placeholders), suggests child nodes and tags, and knows the full V1.3 content array — item types, `width` layout, and the include resolver.

Then it always runs the auto-fixer, which repairs missing metadata blocks, invalid or missing UUIDs, duplicate IDs within a file, legacy fields, malformed attribute and relation structures, long-string formatting, and timecode calculations:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py file.codex.yaml
```

| Auto-fixer flag | Effect |
|---|---|
| `-r`, `--recursive` | Fix a whole directory |
| `-d`, `--dry-run` | Preview only |
| `--re-id` | Regenerate every ID |
| `-v`, `--verbose` | Detailed output |

**Examples**

```
/format notes.codex.yaml
```
> Repairs an existing file and reports exactly what changed.

```
/format
```
> Then: "turn my character notes into Codex." Creates a `type: character` document with attributes, relations, and children for arcs.

```
/format
```
> Then: "format this recipe as Codex." Type and attributes (`prep_time`, `ingredients`) are invented to fit — the format isn't limited to manuscripts.

**Notes** — Defaults to `.codex.yaml`; emits `.codex.json` if you ask. Never hand-create `.index.codex.yaml`.

---

#### `/markdown`

**Create or repair Codex Lite files.**

```
/markdown [file.md]
```

Adds and validates ChapterWise frontmatter on plain Markdown — the flat alternative to full Codex.

**Frontmatter fields** — all optional:

| Group | Fields |
|---|---|
| Identity | `type`, `name`, `title`, `summary`, `id` |
| Organization | `tags`, `author`, `last_updated` |
| Publishing | `status`, `featured` |
| Media | `image`, `images` |
| Advanced | `attributes`, `word_count` |

Display title resolves in order: `name` → `title` → first `# H1` → filename.

The helper generates a UUID for a missing or invalid `id`, extracts `name` from the H1 or filename, defaults `type: document`, and recalculates `word_count`.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/lite_helper.py document.md
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/lite_helper.py notes/ --recursive
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/lite_helper.py draft.md --dry-run
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/lite_helper.py bare.md --init
```

**Examples**

```
/markdown character-maya.md
```
> Adds `type: character`, summary, tags, and status to an existing profile.

**Notes** — Lite has no hierarchy and no relations. If your content nests, use full Codex instead.

---

#### `/diagram`

**Create Mermaid diagrams in Codex format.**

```
/diagram [diagram-type] [description]
```

Diagrams render client-side with dark-mode support. Fifteen types are documented:

| Type | Keyword | | Type | Keyword |
|---|---|---|---|---|
| Flowchart | `flowchart TD` | | Pie chart | `pie` |
| Sequence | `sequenceDiagram` | | Architecture | `architecture-beta` |
| Class | `classDiagram` | | Quadrant | `quadrantChart` |
| State | `stateDiagram-v2` | | XY chart | `xychart-beta` |
| ER | `erDiagram` | | Sankey | `sankey-beta` |
| Gantt | `gantt` | | Block | `block-beta` |
| Mindmap | `mindmap` | | Git graph | `gitGraph` |
| Timeline | `timeline` | | | |

**Three ways to embed** — inline in a content array, as an external `.mermaid` file, or as a fenced ` ```mermaid ` block inside `body`:

```yaml
content:
  - key: system-flow
    name: "System Architecture"
    type: diagram
    width: 1/1
    value: |
      flowchart TD
        A[Client] --> B[API Gateway]
        B --> C[(Database)]
```

```yaml
content:
  - key: er-model
    type: diagram
    width: 1/1
    include: /diagrams/schema.mermaid
```

**Examples**

```
/diagram flowchart "the signup process"
```
> A `flowchart TD` content item at `1/2` width.

```
/diagram erDiagram "database schema for characters and locations"
```
> Full-width `erDiagram`, likely as an external include given the complexity.

```
/diagram architecture-beta "backend services"
```
> Architecture diagram with Phosphor icon nodes:
> ```mermaid
> architecture-beta
>     group backend(ph:cloud)[Backend]
>     service api(ph:plugs-connected)[API] in backend
> ```

**Notes** — Always set `type: diagram` on the content item. Use `1/2` or `1/3` for simple flowcharts and pie charts; `1/1` for sequence, ER, gantt, mindmap, and timeline. Common syntax errors: missing spaces around arrows (`A-->B` should be `A --> B`), unquoted special characters in labels, and `graph` where `flowchart` is meant.

---

#### `/spreadsheet`

**Create spreadsheets in Codex format.**

```
/spreadsheet [description or file.csv]
```

Interactive tables with typed columns and Excel-style formulas. Three levels of commitment:

**Inline CSV** — simplest:

```yaml
content:
  - key: budget
    name: "Production Budget"
    type: spreadsheet
    width: 1/1
    value: |
      Category,Budget,Spent,Remaining
      Talent,50000,12000,=B2-C2
```

**External CSV**:

```yaml
content:
  - key: data
    type: spreadsheet
    width: 1/1
    include: /data/myfile.csv
```

**Full `.spreadsheet.yaml`** — column types, formatting, calculated columns:

```yaml
metadata:
  formatVersion: "1.0"

columns:
  - key: category
    title: "Category"
    type: text
    width: 150
    readOnly: true
  - key: remaining
    title: "Remaining"
    type: currency
    width: 120
    formula: "=B{row}-C{row}"

data:
  - category: "Talent"
    budget: 50000
    spent: 12000
```

Column types: `text`, `numeric`, `currency`, `percent`, `date`, `dropdown`, `checkbox`.

Formulas are Excel-style with capital-letter cell references — `=A1+B1`, `=SUM(B2:B10)`, `=AVERAGE(C2:C10)`, `=IF(A1>0,"Yes","No")`.

> **`.spreadsheet.yaml` has its own version namespace.** Its `formatVersion: "1.0"` is unrelated to the Codex spec version. A `1.0` spreadsheet alongside a `1.3` codex is correct, not stale.

**Examples**

```
/spreadsheet "production budget"
```
> Inline CSV content item with a computed Remaining column.

```
/spreadsheet mydata.csv
```
> References your existing CSV via `include` rather than copying it.

```
/spreadsheet "equipment inventory with formulas"
```
> Full `.spreadsheet.yaml` with typed columns and calculated fields.

**Notes** — `width: 1/1` is the right default for spreadsheets. Formula cell references must be capitals; lowercase won't resolve.

---

#### `/index`

**Generate the project index.**

```
/index [project_directory]
```

Creates `index.codex.yaml` at the Git repository root — the entry point that defines how ChapterWise discovers, orders, and displays your content.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/index_generator.py .
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/index_generator.py /path/to/project --dry-run -v
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/index_generator.py . --include-md
```

| Flag | Effect |
|---|---|
| `--name <name>` | Project name (defaults to the folder name) |
| `--title <title>` | Project title (defaults to the name) |
| `--summary <text>` | Project summary |
| `--include-md` | Include Markdown files in discovery |
| `-o`, `--output <path>` | Output path (defaults to `<path>/index.codex.yaml`) |
| `-d`, `--dry-run` | Preview without writing |
| `-v` | Verbose |

**Child node fields** — `name` (required), `title`, `order` (default 999), `emoji`, `status` (default `private`), `featured`, `hidden`, `children` (auto-discovered if omitted).

**Examples**

```
/index
```
> Interviews on project name and structure, generates and auto-fixes the index, offers to commit.

**Notes** — `/import` generates an index for you; reach for `/index` when bootstrapping a project by hand or when your structure changed enough that discovery patterns need rewriting. Never specify `type` on children — it's detected from the file extension. Remember that `status` does not inherit.

---

### Structure

#### `/explode`

**Split a codex file into separate child files.**

```
/explode [file.codex.yaml] [--types type1,type2]
```

Extracts children into standalone files and replaces each in the parent with an `include:` directive. Smaller files, cleaner diffs, parallel editing.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/explode_codex.py story.codex.yaml --types character,location
```

| Flag | Default | Effect |
|---|---|---|
| `--types` | all direct children | Comma-separated types to extract |
| `--output-pattern` | `./{type}s/{name}.codex.yaml` | Placeholders: `{type}`, `{name}`, `{id}`, `{index}` |
| `--format` | `yaml` | `yaml` or `json` |
| `--dry-run` | off | Preview only |
| `--no-backup` | off | Skip backing up the original |
| `--no-auto-fix` | off | Skip auto-fixing extracted files |
| `--force` | off | Overwrite existing output files |
| `-v` | off | Verbose |

**Examples**

```
/explode story.codex.yaml --types character,location
```
> Characters land in `./characters/`, locations in `./locations/`, each an `include:` in the parent.

```
/explode story.codex.yaml --types character --dry-run
```
> Shows exactly what would be extracted, writes nothing.

**Notes** — Existing output files are skipped rather than overwritten unless you pass `--force`. The parent gets a `metadata.exploded` stamp recording timestamp, types, and count.

---

#### `/implode`

**Merge included files back into one document.**

```
/implode [file.codex.yaml]
```

The inverse of `/explode`. Resolves every `include:` and inlines the referenced content.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py story.codex.yaml --dry-run -v
```

| Flag | Effect |
|---|---|
| `--recursive` | Resolve includes inside included files |
| `--delete-sources` | Delete the merged files afterward |
| `--delete-empty-folders` | Clean up folders left empty |
| `--dry-run` | Preview only |
| `--no-backup` | Skip backing up the parent |
| `-v` | Verbose |

**Examples**

```
/implode story.codex.yaml --dry-run -v
```
> Preview the merge before committing to it.

```
/implode project.codex.yaml --recursive --delete-sources --delete-empty-folders
```
> Full consolidation back to a single file.

```bash
cp project.codex.yaml project-dist.codex.yaml
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/implode_codex.py project-dist.codex.yaml --recursive
```
> Build a self-contained distribution copy without touching the working project.

**Round-trip fidelity** — Structural content (id, type, name, body, attributes, children, relations) survives explode → implode faithfully. Two things don't: an included file's own `metadata` block is dropped on merge (it exists for standalone use), and the parent's stamp toggles between `metadata.exploded` and `metadata.imploded` rather than accumulating both. YAML comments and formatting are not guaranteed.

**Notes** — A missing included file is skipped with a warning, not a hard failure. Run the auto-fixer afterward to confirm the merged file validates.

---

#### `/insert`

**Insert notes into a manuscript by describing where they go.**

```
/insert [instruction]
/insert --batch notes.txt
```

You wrote a note on your phone that belongs "after Elena meets Marcus." This finds that place. Two-pass semantic search: the first pass narrows the whole directory to 1–3 promising chapters using each file's title, summary, and child names; the second reads those chapters in full and returns ranked line-level candidates with confidence scores.

**Confidence determines behavior:**

| Confidence | Behavior |
|---|---|
| 95–100% | Inserts automatically, tells you where |
| 50–94% | Shows numbered options, you choose |
| Below 50% | Shows what it found, asks you to specify |

| Flag | Alias | Effect |
|---|---|---|
| `--batch <file>` | `-b` | Multiple notes from a file |
| `--target <dir>` | `-t` | Which directory to search |
| `--interactive` | `-i` | Confirm each note |
| `--clipboard` | `-c` | Read notes from the clipboard |
| `--dry-run` | `-d` | Preview only |
| `--accept [file]` | `-a` | Finalize pending inserts in a file |
| `--accept-all [dir]` | | Finalize across a directory |
| `--undo [file]` | `-u` | Restore from the most recent backup |
| `--delimiter <str>` | | Batch note separator (default `---`) |
| `--confidence <n>` | | Minimum confidence threshold (default `50`) |
| `--no-backup` | | Skip the backup — dangerous |

**Everything lands inside a review marker** — nothing is silently woven into your prose:

```html
<!-- INSERT
time: 2024-01-15T10:30:00Z
source: notepad
instruction: "after the hyperborean incursion"
confidence: 0.87
matched_after: "...the hyperborean forces retreated beyond the ridge."
-->
Elena drew her sword, the blade catching the firelight...
<!-- /INSERT -->
```

Read them, edit them, then `--accept` to strip the markers and keep the text — or `--undo` to roll back. Backups are written to `.backups/` beside the file before any change.

**Examples**

```
/insert after Elena meets Marcus for the first time

She paused, recognizing something familiar in his eyes...
```
> Instruction from the first line, content from the rest.

```
/insert --batch notes.txt --target ./manuscript/ --dry-run
```
> Preview where a whole notebook of `---`-separated notes would land.

```
/insert --accept-all ./manuscript/
```
> Finalize every pending insert across the manuscript.

**Notes** — Works with `.codex.yaml` (writes into `body:`), Codex Lite `.md` (after the frontmatter), and plain `.md` (the whole file). `--undo` only restores the most recent backup.

---

### Conversion

#### `/convert-to-codex`

**Markdown to full Codex.**

```
/convert-to-codex [input.md]
```

Upgrades a Codex Lite file to full Codex when you need children or relations.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py input.md --to-codex
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py input.md --to-codex --format json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py input.md --to-codex --delete-original
```

Frontmatter maps to codex fields; `author`, `last_updated`, `description`, and `license` move into `metadata`; anything unrecognized becomes an `attributes` entry. The first `# H1` becomes the title if frontmatter didn't set one; the rest becomes `body`.

**Examples**

```
/convert-to-codex chapter-01.md
```
> Produces `chapter-01.codex.yaml`, then offers to auto-fix it.

**Notes** — No frontmatter means the whole file is treated as body content. A name collision prompts before overwriting.

---

#### `/convert-to-markdown`

**Full Codex down to Markdown.**

```
/convert-to-markdown [input.codex.yaml]
```

Flattens to Codex Lite for portability outside ChapterWise.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py story.codex.yaml --to-markdown
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/convert_format.py story.codex.yaml --to-markdown -o export/story.md
```

> **This is lossy and one-way.** `children`, `relations`, and `metadata.formatVersion` / `documentVersion` are not carried over. You're warned before conversion if the source has children, but nothing reconstructs them on the way back. Keep the codex file.

**Examples**

```
/convert-to-markdown character.codex.yaml
```
> Exports `character.md` with frontmatter, warning first if hierarchy would be lost.

---

### Maintenance

#### `/generate-tags`

**Extract tags from content.**

```
/generate-tags [file.codex.yaml or file.md]
```

Algorithmic, not a model call — frequency analysis with a 2× weight on words appearing in headings, 200+ stopwords filtered (including manuscript boilerplate like "chapter" and "preface"), plus meaningful bigrams. It won't tag both "Roman" and "Senate" separately if "Roman Senate" already made the list.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tag_generator.py story.codex.yaml
```

| Flag | Default | Effect |
|---|---|---|
| `--count N` | 10 | Maximum tags per entity |
| `--min-count N` | 3 | Minimum occurrences to qualify |
| `--format simple\|detailed` | `simple` | Plain strings, or `{name, count}` objects |
| `--follow-includes` | off | Process included files too |
| `-d`, `--dry-run` | off | Preview only |

**Examples**

```
/generate-tags story.codex.yaml
```
> Top 10 tags written into `tags:`.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tag_generator.py chapter.md --count 5 --min-count 2
```
> Fewer tags, looser threshold — right for short pieces.

**Notes** — Short content produces nothing at the default threshold; drop `--min-count` to 1 or 2. Modular projects need `--follow-includes` or the children aren't scanned.

---

#### `/update-word-count`

**Recalculate word counts.**

```
/update-word-count [file_or_directory]
```

Walks the document tree, counts words in every `body`, and writes a `word_count` attribute (Codex) or frontmatter field (Lite).

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/word_count.py story.codex.yaml
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/word_count.py /path/to/codex -r
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/word_count.py story.codex.yaml --dry-run
```

| Flag | Effect |
|---|---|
| `-r`, `--recursive` | Process subdirectories |
| `--follow-includes` | Process included files (cycle-safe) |
| `--no-markdown` | Skip `.md` files when processing a directory |
| `-d`, `--dry-run` | Preview only |

---

#### `/format-folder`

**Auto-fix every codex file in a folder.**

```
/format-folder [folder_path]
```

Batch form of the auto-fixer.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py /path/to/folder --recursive --include-md
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py /path/to/folder --recursive --dry-run
```

| Flag | Effect |
|---|---|
| `-r`, `--recursive` | Include subdirectories |
| `--include-md` | Also process `.md` as Codex Lite |
| `--re-id` | Regenerate all IDs |
| `-d`, `--dry-run` | Preview only |
| `-v` | Verbose |

Processes `.codex.yaml`, `.codex.yml`, `.codex.json`, and `.codex`. A file that can't be written is skipped individually rather than aborting the batch.

---

#### `/format-regen-ids`

**Regenerate every ID in a file.**

```
/format-regen-ids [file.codex.yaml]
```

Forces new UUIDs for every `id` and `targetId`, including valid ones. For forking a project, duplicating a chapter, or cleaning up after copy-paste left you with collisions.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py file.codex.yaml --re-id
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py /path/to/project --re-id --recursive
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py file.codex.yaml --re-id --dry-run
```

> **Relations pointing outside the regeneration scope break, and nothing repairs them.** IDs within the scope stay internally consistent, so relations inside a single run survive. A `targetId` in another file that wasn't part of the run now points at an ID that no longer exists — you fix those by hand. Run with `--recursive` across the whole project to keep cross-file relations intact.

---

### Internal

#### `/feedback-inbox`

**ChapterWise team only.**

```
/feedback-inbox [triage | work <id> | stats]
```

Triages user feedback from the ChapterWise production database. It requires a `DATABASE_URL` pointing through an SSH tunnel to ChapterWise's own DigitalOcean instance, so it is not usable outside the team — it ships with the plugin but does nothing for external users beyond printing a setup error.

| Mode | Does |
|---|---|
| *(none)* | List new and triaged items, ask what to work on |
| `triage` | Walk new items, assign priority |
| `work <id>` | Claim an item, fix it, resolve it against a commit hash |
| `stats` | Counts by status, category, and area |

---

## Analysis modules

A module is a prompt — one specific editorial lens applied to your prose. 33 ship with the plugin.

### Courses

Courses group modules into coherent passes. Run `/analysis` with no arguments and you pick from these:

| Course | Modules | Use it for |
|---|---|---|
| **Quick taste** | `summary`, `characters`, `tags` | Fast orientation on every chapter |
| **Slow roast** | `three_act_structure`, `story_beats`, `story_pacing`, `heros_journey` | Deep structure — runs against the whole manuscript |
| **Spice rack** | `writing_style`, `language_style`, `rhythmic_cadence`, `clarity_accessibility` | Prose craft |
| **Simmering** | `thematic_depth`, `reader_emotions`, `jungian_analysis`, `character_relationships`, `dream_symbolism`, `immersion` | Depth and psychology |
| **Immersive** | `immersive_design`, `immersion`, `reader_emotions`, `story_pacing` | Dome shows, planetarium pieces, projection work |

A module can belong to more than one course. The remaining 15 modules belong to no course — address them by name, or reach them through `--all` or `--plan`.

### All 33 modules

**Narrative structure**

| Module | Analyzes |
|---|---|
| `summary` | Key events, character interactions, story developments per chapter |
| `story_beats` | Turning points and structural beats |
| `three_act_structure` | Act I/II/III boundaries across the manuscript |
| `eight_stage` | Nigel Watts' Eight-Point Arc, Stasis through Resolution |
| `heros_journey` | Character arcs mapped to Campbell's monomyth |
| `story_pacing` | Event distribution, chronological vs. narrative time |
| `plot_twists` | Twist setup, execution, and impact |
| `misdirection_surprise` | Foreshadowing, red herrings, payoff |
| `reader_emotions` | The reader's emotional journey and its authenticity |

**Characters**

| Module | Analyzes |
|---|---|
| `characters` | Who's present, their roles, motivations, development |
| `character_relationships` | Relationship dynamics, power structures, conflict patterns |
| `win_loss_wave` | Oscillating victory and defeat, escalating stakes, emotional amplitude |

**Writing craft**

| Module | Analyzes |
|---|---|
| `writing_style` | Voice, tone, literary devices, narrative perspective |
| `language_style` | Prose style and sentence construction |
| `rhythmic_cadence` | Rhythm, flow, musicality of the prose |
| `clarity_accessibility` | Readability and comprehension barriers |
| `four_weapons` | Balance of dialogue, action, description, introspection |
| `comedy_analysis` | Humor, comedic timing, structure, effectiveness |
| `tags` | Thematic tags, locations, concepts, motifs |

**Thematic and specialized**

| Module | Analyzes |
|---|---|
| `thematic_depth` | Theme development, layering, resonance |
| `jungian_analysis` | Shadow, anima/animus, persona, individuation |
| `alchemical_symbolism` | Nigredo/albedo/rubedo stages, philosopher's-stone metaphor |
| `dream_symbolism` | Dream sequences and dream-logic symbolism |
| `psychogeography` | How physical space acts on characters psychologically |
| `self_awareness` | Meta-fiction, fourth-wall breaks, authorial intrusion |

**Quality assessment**

| Module | Analyzes |
|---|---|
| `critical_review` | Overall quality — strengths, weaknesses, suggestions |
| `story_strength` | Narrative power, engagement, effectiveness |
| `plot_holes` | Logic inconsistencies, gaps, continuity breaks |
| `cultural_authenticity` | Cultural representation and accuracy |
| `immersion` | Sensory detail, engagement, world-building |
| `status` | Completion state, polish, revision priorities |
| `ai_detector` | Linguistic patterns suggesting AI-generated text |

**Immersive design**

| Module | Analyzes |
|---|---|
| `immersive_design` | Dome show and projection design — proposes effects, maps crescendo and lull, flags vestibular comfort risk |

`immersive_design` is backed by two references: `immersive-effects.md` catalogs 59 named effects across 9 categories, each with its mechanic, target reaction, arc position, comfort risk, and a sourcing-confidence tag; `immersive-comfort.md` collects vestibular thresholds (roughly a 20°/s rotation ceiling, multi-axis rotation as the strongest risk factor, an earth-fixed horizon as the primary mitigation) and fulldome pacing guidance.

Both references rate their own reliability rather than presenting craft as physics, on separate scales. Effects carry a **Confidence** tag — `Documented` (a named source describes the technique), `Observed practice` (demonstrably standard but not formally written up), or `ChapterWise coinage` (we named it; it may still be real and useful, but no external source calls it that). Comfort claims carry a **Tier** — `Measured` (peer-reviewed with published numbers), `Guideline` (published platform or industry standard), or `Consensus` (named practitioners agree, no controlled study).

### The `.analysis.json` format

Results are written beside the source chapter, in Codex V1.3:

```json
{
  "metadata": { "formatVersion": "1.3", "created": "...", "updated": "..." },
  "id": "chapter-03-analysis",
  "type": "analysis",
  "attributes": [
    { "key": "sourceFile", "value": "chapter-03.codex.yaml" },
    { "key": "sourceHash", "value": "a1b2c3d4e5f6a7b8" }
  ],
  "children": [
    {
      "id": "characters",
      "type": "analysis-module",
      "name": "Character Analysis",
      "children": [
        {
          "id": "entry-20260804T142233Z",
          "type": "analysis-entry",
          "status": "published",
          "attributes": [
            { "key": "model", "value": "<the model that actually ran>" },
            { "key": "sourceHash", "value": "a1b2c3d4e5f6a7b8" },
            { "key": "analysisStatus", "value": "current" },
            { "key": "timestamp", "value": "2026-08-04T14:22:33Z" }
          ],
          "summary": "Elena's reticence reads as grief, not coldness.",
          "body": "## Character Analysis\n\n...",
          "children": [],
          "tags": ["analysis", "characters"]
        }
      ]
    }
  ]
}
```

Each module keeps up to three entries, newest first; older ones drop to `status: draft`. The `sourceHash` is what makes staleness detection work. Authoritative schema: `schemas/analysis-v1.3.schema.json`.

### Writing your own module

Modules are discovered from three locations, each overriding the last:

| Location | Scope |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/modules/` | Built-in — the 33 above |
| `~/.claude/analyze/modules/` | Yours, across all projects |
| `./.chapterwise/analysis-modules/` | Yours, this project only |

A module is a Markdown file with frontmatter. Drop it in and `/analysis` finds it:

```markdown
---
name: pacing_density              # required — the key you type
displayName: Pacing Density
description: Measures scene-to-summary ratio per chapter.
category: Narrative Structure
icon: ph ph-gauge
applicableTypes: ["novel", "short_story", "screenplay"]
---

Analyze the ratio of dramatized scene to compressed summary...

[the rest of the file is your analysis prompt]
```

Only `name` is required — without it the module is skipped. A file named the same as a built-in replaces it, so you can override any shipped module by dropping your own version into a higher-priority directory.

Every module must emit the shape defined in `modules/_output-format.md`:

```json
{
  "body": "## Module Name\n\nMain content in markdown...",
  "summary": "One-line summary of findings",
  "children": [
    {
      "name": "Section Name",
      "summary": "Section summary",
      "content": "## Section\n\nDetail...",
      "attributes": [{ "key": "score", "name": "Score", "value": 8, "dataType": "int" }]
    }
  ],
  "tags": ["analysis", "module-name"],
  "attributes": [{ "key": "overall_score", "name": "Overall Score", "value": 7, "dataType": "int" }]
}
```

Module IDs and attribute keys are snake_case. Scores are integers 1–10.

Files beginning with `_` are shared partials, not modules — they're skipped by discovery. Courses are defined in `scripts/module_loader.py`, so a custom module can't join an existing course without editing that file; run it by name, or via `--all` and `--plan`.

---

## Requirements

- **Python 3.8+**
- **PyYAML** — `pip install pyyaml`

Per-format import dependencies, installed only if you need them:

| Format | Package |
|---|---|
| PDF | `pymupdf` |
| DOCX | `python-docx` |
| Scrivener | `lxml` |
| HTML | `beautifulsoup4` |

`/import` checks for what it needs and offers to install it.

---

## Conventions

A few house rules worth knowing, since they shape how the plugin behaves:

**Your files are yours.** Source manuscripts are never modified by import. Analysis writes to sibling `.analysis.json` files, never into your prose. Insert wraps everything in review markers you explicitly accept. Destructive operations back up first, to `.backups/` beside the file.

**Clean defaults, rich options.** First run asks nothing that has a sensible default. Configuration is saved so second runs ask nothing at all. Every inference can be overridden by saying so.

**Data over flare.** Progress messages carry real numbers — chapters processed, modules run, files written. `/status` reports state, not encouragement.

**Nothing is pushed for you.** Commands offer to commit and never push to a remote on their own.

---

## Links

- [ChapterWise](https://chapterwise.app)
- [Repository](https://github.com/ansonphong/chapterwise-plugins)
- [Changelog](../../CHANGELOG.md)
- [License](../../LICENSE) — MIT
