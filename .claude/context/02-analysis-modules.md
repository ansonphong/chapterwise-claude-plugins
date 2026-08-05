# Analysis Modules (33 modules)

All modules are `.md` files in `modules/` with YAML frontmatter (name, displayName, description, category, icon, applicableTypes). Discovered by `module_loader.py` from three search paths (built-in, user global, project-local).

Two modules are backed by shipped reference files rather than carrying their domain knowledge inline: `immersive_design` loads `references/immersive-effects.md` (the effects catalog) and `references/immersive-comfort.md` (vestibular thresholds and pacing rules). Extending the catalog does not require touching the module prompt.

## Course Groupings

Modules are organized into five courses (defined in `module_loader.py` COURSES dict):

### Quick Taste -- fast per-chapter overview
- `summary` -- Chapter Summary (key events, character interactions, developments)
- `characters` -- Character Analysis (roles, motivations, development)
- `tags` -- Content Tags & Keywords (themes, locations, concepts, motifs)

### Slow Roast -- root-level structural analysis (runs on index/full manuscript, not per-chapter)
- `three_act_structure` -- Three-Act Structure (Setup, Confrontation, Resolution)
- `story_beats` -- Story Beats (key narrative moments, turning points)
- `story_pacing` -- Story Pacing (timing, dramatic tension, event distribution)
- `heros_journey` -- Hero's Journey (Campbell's archetypal stages)

### Spice Rack -- per-chapter writing craft
- `writing_style` -- Writing Style (voice, tone, literary devices, perspective)
- `language_style` -- Language & Style (prose style, sentence construction)
- `rhythmic_cadence` -- Rhythmic Cadence (prose rhythm, sentence flow, musicality)
- `clarity_accessibility` -- Clarity & Accessibility (readability, comprehension barriers)

### Simmering -- per-chapter depth & psychology
- `thematic_depth` -- Thematic Depth (theme development, layering, resonance)
- `reader_emotions` -- Reader Emotions (emotional journey, emotional truth)
- `jungian_analysis` -- Jungian Analysis (archetypes, shadow, anima/animus, individuation)
- `character_relationships` -- Character Relationships (dynamics, power, bonds, conflict)
- `dream_symbolism` -- Dream Symbolism (dream logic, symbolic imagery, subconscious)
- `immersion` -- Immersion (sensory detail, engagement, suspension of disbelief)

### Immersive -- experiential design for dome shows and installations
- `immersive_design` -- Immersive Design (effects catalog, crescendo/lull rhythm, vestibular comfort)
- `immersion` -- Immersion (also in Simmering; prose-side counterpart)
- `reader_emotions` -- Reader Emotions (emotional journey)
- `story_pacing` -- Story Pacing (timing, tension distribution)

Note the division of labour: `immersion` asks whether a text transports a reader; `immersive_design` asks whether a sequence would land on a 360° surface. They are complementary, not alternatives.

### Uncategorized (15 modules -- not in a course, available for direct or genre-based use)
`ai_detector`, `alchemical_symbolism`, `comedy_analysis`, `critical_review`, `cultural_authenticity`, `eight_stage` (Nigel Watts), `four_weapons` (dialogue/action/description/introspection), `misdirection_surprise`, `plot_holes`, `plot_twists`, `psychogeography`, `self_awareness` (meta-fiction), `status` (manuscript readiness), `story_strength`, `win_loss_wave`

## How Modules Work

1. `codex_scan.py scan` reads the source's structure and proposes a resolution
2. `codex_scan.py nodes` resolves `--depth` to the concrete nodes to analyze
3. Module prompt is read from its `.md` file body (after frontmatter)
4. Each node's content is fed alongside the module prompt
5. LLM produces structured JSON matching `_output-format.md` schema
6. `analysis_writer.py` wraps output in Codex V1.3 structure and saves to `.analysis.json`
7. `analysis_report.py` optionally renders a report into `<source_dir>/analysis/`
8. `staleness_checker.py` uses SHA-256 hash (first 16 chars) to detect when source changes

## Resolution and Scope

Analysis granularity is **depth in the codex tree**, not one pass per file. A dome script
is one file holding 9 acts and 36 beats; `--depth root,leaf` produces 37 analyses of it.

Every result lives in the one `.analysis.json` sibling, tagged with a `scope` attribute —
`root` for the whole file, `node:<id>` for a node inside it, plus `scopeName`,
`scopePath`, `scopeDepth` and `scopeIndex`. An entry with **no** `scope` attribute is read
as `root`, which is what every pre-scope entry is.

History is kept **per scope**. `add_analysis_result()` partitions staling and trimming by
scope, because the flat version deleted 34 of 37 entries: it treated other nodes'
analyses as older versions of the one being written.

Modules that define more than one output shape select by scope. `immersive_design` is the
reference case — `root` gives the whole-show shape, `node:*` gives the scene shape.

## Reports

`analysis_report.py` renders stored results into `<source_dir>/analysis/` as markdown,
Codex V1.3, or `both`. It is a formatter and never calls a model, so regenerating is free
and the report cannot drift from the stored results. It walks the source tree to emit in
document order, since entries are stored newest-first and flat. Ids are derived from what
a node *is*, so a regenerated report is byte-identical.

**The format is chosen at runtime, then remembered.** `/analysis` asks depth and report
format in one AskUserQuestion call, both pre-answered by the scan's proposal, and offers
afterwards to save them to `.chapterwise/settings.json`. Stating a format in prose and
never offering the alternative is not asking — that was the v2.4.0 defect.

`settings.py` owns the config layer: `plugin defaults → .chapterwise/settings.json →
flags`. Defaults are **codex** into an `analysis/` folder beside the analyzed file.
`analysis_report.build()` reads settings itself, so a direct script call gets the same
answer the command does. A `sources` map marks each value `default`, `recipe`, or
`settings` — a command asks only about `default` values, which is what stops it asking
twice. Settings are intent and are committed; the `*-recipe` folders are run history.
`commands/analysis.md` Section 0 is the shared contract every route defers to — resolve
before asking, export a report on every route, offer to save once per project. Wiring it
into the single-file route alone was the v2.6.0 gap.
`report_dir` resolves like a codex `include`: bare or `./` is beside the file, a leading
`/` is the project root, `~` is literal.

**Codex output goes through `/chapterwise:format`.** `render_codex()` hands the assembled
document to `CodexAutoFixer`, then `validate_output()` checks it against the V1.3 schema
and the result carries `valid` / `issues`. Two consequences worth knowing:

- Attribute keys must match `^[a-z][a-z0-9_-]*$` — `source_file`, not `sourceFile`. The
  `.analysis.json` file is a different document under a different schema and keeps its
  camelCase keys.
- Node ids must be **v4-shaped** or the fixer replaces them. `stable_id()` stamps a sha1
  digest with the v4 version and variant bits to be deterministic and survive the fixer.

`analysis/` sits beside `atlas/` and `reader/` — the convention for deliverables derived
from the manuscript. `.chapterwise/` holds machine state and reference inputs.

## Output Format

Each module produces: `body` (markdown), `summary` (1-2 sentences), `children` (2-5 sub-sections), `attributes` (scored metrics, integers 1-10), `tags`. Module IDs and attribute keys use snake_case. Results stored per-module with up to 3 historical entries.

## Genre-Aware Recommendations

`module_loader.py recommend` maps genres to module sets. Supported genres: literary_fiction, thriller, fantasy, nonfiction, poetry. Unknown genres get all course modules as default.
