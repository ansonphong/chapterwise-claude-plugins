---
description: "Build a story atlas from your manuscript"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, AskUserQuestion, Task
triggers:
  - atlas
  - build atlas
  - generate atlas
  - story atlas
  - character atlas
  - update atlas
  - chapterwise:atlas
argument-hint: "[--update] [--name 'name'] [--rebuild] [--delete] [--list] [--add-sections]"
---

# ChapterWise Atlas

## Overview

Build a comprehensive reference atlas from your manuscript — characters, timeline, themes, plot structure, locations, and relationships — synthesized across all chapters into a navigable Codex project. The atlas is a living document: after the initial build, run `/atlas --update` to incorporate manuscript changes incrementally without rebuilding from scratch.

The atlas is a four-pass pipeline:

- **Pass 0:** Scan manuscript, propose atlas folder structure tailored to content complexity
- **Pass 1:** Extract entities chapter-by-chapter — characters, locations, objects, factions, key events (one read per chapter)
- **Pass 2:** Per-chapter deep analysis using existing analysis modules, reusing fresh results where available (one pass per chapter per module — the heaviest stage)
- **Pass 3:** Cross-chapter synthesis into cohesive atlas sections, written as `.codex.yaml` files (one pass per atlas section)

Output is committed to the project git repo as native Codex files — browsable on ChapterWise.app, in VS Code, or as a standalone reader via the /reader command.

---

## Command Routing

Parse flags from the argument and route accordingly:

- `/atlas` — Build new atlas (interactive), or extend existing atlas if one is found
- `/atlas --update` — Incremental update: re-analyze changed chapters only
- `/atlas --name "X"` — Build a named atlas at folder `x/` (slugified)
- `/atlas --rebuild` — Delete existing atlas and rebuild from scratch
- `/atlas --delete` — Delete an atlas and remove it from the project index
- `/atlas --list` — Show all atlases registered in this project
- `/atlas --add-sections` — Add new sections to an existing atlas

If no flags are present, proceed to **Step 1** of the Build New Atlas pipeline. If `--update` is present, jump to the **Update Pipeline**. All other flags jump to **Management Commands**.

---

## BUILD NEW ATLAS

### Step 1: Check for Existing Atlas Recipe

Load any saved atlas configuration for this project.

```bash
echo '{"project_path": ".", "type": "atlas"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py load
```

**If an existing atlas configuration is found:**

Report to the user:

> "You already have an atlas for this project — {atlas name}, {N} sections, built {date ago}. Update it with changes, rebuild from scratch, or add new sections?"

Use AskUserQuestion to present options:
- **Update** — Incremental update (jump to Update Pipeline)
- **Add sections** — Extend with new sections (jump to `--add-sections`)
- **Rebuild** — Delete and rebuild from scratch (confirm, then continue from Step 2)
- **Manage** — List atlases, delete, or rename

If multiple atlases exist, present the list and ask which one the user means.

**If no existing atlas is found:** Continue to Step 2.

---

### Step 2: Scan Project (Pass 0)

Read the project structure and sample chapters to propose an atlas tailored to the content.

**Action:** Read the project index.

```bash
echo '{"project_path": "."}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py scan
```

Then read the project `index.codex.yaml` directly to gather chapter count, title, and existing metadata:

Read the project's `index.codex.yaml` using the Read tool to understand the manuscript structure.

Sample 3–5 chapters from different positions in the manuscript (beginning, middle, end) to detect genre, POV style, cast complexity, and world complexity.

**Progress:** `"Scanning manuscript... {genre}, {N} chapters, {word count} words."`

**Atlas structure decision tree:**

Based on cast size and complexity, propose one of three layouts:

**Simple** (fewer than 5 named characters, single setting):
```
atlas/
  index.codex.yaml
  characters.codex.yaml
  timeline.codex.yaml
  themes.codex.yaml
  plot-structure.codex.yaml
```

**Standard** (5–15 characters, multi-setting fiction):
```
atlas/
  index.codex.yaml
  characters.codex.yaml
  timeline.codex.yaml
  themes.codex.yaml
  plot-structure.codex.yaml
  locations.codex.yaml
  relationships.codex.yaml
```

**Detailed** (15+ characters, multiple factions, or fantasy/sci-fi world complexity):
```
atlas/
  index.codex.yaml
  characters/
    protagonists.codex.yaml
    antagonists.codex.yaml
    supporting-cast.codex.yaml
    relationship-map.codex.yaml
  world/
    locations.codex.yaml
    factions.codex.yaml
    magic-system.codex.yaml    (fantasy/sci-fi only)
    artifacts.codex.yaml
  plot/
    three-act-structure.codex.yaml
    timeline.codex.yaml
    story-beats.codex.yaml
    subplots.codex.yaml
  themes/
    thematic-depth.codex.yaml
    symbolism.codex.yaml
    motifs.codex.yaml
```

For non-fiction manuscripts, propose: `topic-map.codex.yaml`, `key-arguments.codex.yaml`, `chapter-summaries.codex.yaml`, `source-references.codex.yaml`.

For poetry collections, propose: `themes.codex.yaml`, `imagery.codex.yaml`, `devices.codex.yaml`, `emotional-arc.codex.yaml`.

**Ask the user ONE question** (using AskUserQuestion) presenting the proposed structure:

> "Here's the atlas structure I'd recommend for your {genre} with {N} characters:"
> ```
> atlas/
>   characters.codex.yaml
>   timeline.codex.yaml
>   themes.codex.yaml
>   plot-structure.codex.yaml
>   locations.codex.yaml
> ```
> "Build all sections, or pick specific ones?"

Options:
- **Build all** (Recommended) — Full atlas, all proposed sections
- **Select sections** — Show checkboxes for each proposed section
- **Characters only** — Quick shortcut, single section

After confirming structure, ask for the atlas name if no `--name` flag was provided:

> "What should I call this atlas? Default is 'atlas'."

Options: `[atlas]` `[story-atlas]` `[Custom name]`

**Show the scale of work before starting the deep passes:**

> "Ready to build. {M} chapters x {K} modules = ~{N} analysis passes, plus synthesis.
> Start with entity extraction, or build the full atlas?"

Options:
- **Build full atlas** — Run all four passes
- **Entity preview only** — Run Pass 0 and Pass 1 only, show what was found

---

### Step 3: Extract Entities (Pass 1)

Extract characters, locations, objects, factions, and key events from every chapter. This pass reads chapter content directly with the agent — no analysis modules involved.

**Context window strategy:** Process chapters individually in batches, not all at once. Use parallel Task subagents.

**Action:** Dispatch entity extraction using Task subagents, 7 chapters per batch:

```
Task 1: Extract entities from chapters 1–7
Task 2: Extract entities from chapters 8–14
Task 3: Extract entities from chapters 15–21
Task 4: Extract entities from chapters 22–28
```

Each subagent task:
1. Reads the chapter file(s) assigned to it
2. Includes the last 500 tokens of the previous chapter as overlap (to catch cross-boundary references)
3. Extracts: character names, descriptions, roles, key traits; location names and descriptions; significant objects; faction names and members; key events with chapter reference and involved characters
4. Returns structured entity data

**After all extraction tasks complete:**

1. Deduplicate entities by name similarity across all batch results — merge nicknames, full names, and aliases (e.g., "Dr. Vasquez", "Elena", "Elena Vasquez" → one entity)
2. Merge `chapters_present` arrays for each entity
3. Resolve description conflicts: keep the most detailed description; note trait evolution if the same entity is described differently across chapters
4. Identify the protagonist(s) and their primary relationships

**Entity map output format:**
```yaml
entities:
  characters:
    - name: "Elena Vasquez"
      description: "Former marine biologist turned environmental activist"
      chapters_present: [1, 3, 4, 5, 7, 9, 12, 15, 18, 21, 24, 27, 28]
      key_traits: [determined, haunted, brilliant]
      story_role: protagonist
  locations:
    - name: "Coral Bay Research Station"
      description: "Isolated marine research facility on the Pacific coast"
      chapters_present: [1, 3, 7, 15, 27]
  objects:
    - name: "The Blackwood Report"
      description: "Suppressed environmental impact study"
      chapters_present: [5, 11, 17, 24]
  factions:
    - name: "Pacific Conservation Alliance"
      members: ["Elena Vasquez", "Dr. Yuki Tanaka", "Sam Reyes"]
  key_events:
    - event: "Report leaked to press"
      chapter: 17
      characters_involved: ["Elena Vasquez", "Marcus Chen"]
stats:
  total_chapters: 28
  unique_characters: 14
  unique_locations: 8
  manuscript_length: 87234
  estimated_reading_hours: 6
```

**Progress:** `"Extracting entities... {N} characters, {M} locations, {K} key events found across {P} chapters."`

If building an entity preview only, stop here and present the entity summary:

> "Here's what I found across {N} chapters:
> - {N} characters (protagonists, supporting cast, antagonists)
> - {M} locations
> - {K} key events
> Ready to build the full atlas?"

---

### Step 4: Analyze Cross-Chapter (Pass 2)

Run deep per-chapter analysis using existing analysis modules. Reuse fresh `.analysis.json` files where available — never re-run analysis that is still current.

**Action:** Check for existing analysis data first.

```bash
echo '{"project_path": ".", "chapter": "ALL"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/staleness_checker.py
```

This returns which chapters have fresh `.analysis.json` files and which are stale or missing.

**Report reuse to the user:**

> "Found existing analysis for {N} of {M} chapters. Re-analyzing {K} changed chapters."
> "{X} module runs needed ({Y} reused from previous analysis)."

**Module selection by atlas type:**

| Atlas Type | Modules | Skip |
|------------|---------|------|
| Literary Fiction | characters, character_relationships, three_act_structure, story_beats, story_pacing, writing_style, thematic_depth, reader_emotions, immersion, jungian_analysis, summary, tags | comedy_analysis, win_loss_wave, four_weapons |
| Thriller / Mystery | characters, story_pacing, plot_twists, misdirection_surprise, win_loss_wave, story_beats, heros_journey, reader_emotions, summary, tags | jungian_analysis, dream_symbolism, rhythmic_cadence |
| Fantasy / Sci-Fi | characters, character_relationships, psychogeography, story_beats, thematic_depth, tags, summary, writing_style | comedy_analysis |
| Non-Fiction | summary, tags, clarity_accessibility, writing_style, language_style, thematic_depth | All narrative modules |
| Poetry | writing_style, language_style, rhythmic_cadence, literary_devices, emotional_dynamics, tags | All plot and structure modules |

**Action:** Dispatch analysis for chapters that need it, using parallel Task subagents in batches of 5–7 chapters:

```
Task 1: Analyze chapters 1–7  (all selected modules)
Task 2: Analyze chapters 8–14 (all selected modules)
Task 3: Analyze chapters 15–21 (all selected modules)
Task 4: Analyze chapters 22–28 (all selected modules)
```

Each task runs the assigned modules on its chapters and writes `.analysis.json` files using:

```bash
echo '{"chapter_path": "CHAPTER_FILE", "modules": ["characters", "story_beats", "..."], "output_path": "CHAPTER_DIR"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analysis_writer.py
```

**Progress:**
- `"Analyzing {N} chapters with {M} modules... running in parallel."`
- `"Chapters 1–14 done. 15–28 still running..."`
- `"All {N} chapters analyzed. {T} module results collected."`

---

### Step 5: Synthesize Atlas (Pass 3)

Cross-reference all entity data and per-chapter analysis to produce cohesive atlas sections. This is where isolated per-chapter data becomes a complete cross-chapter reference.

**Two-stage synthesis for context window management:**

**Stage 1: Condense per-chapter data into entity-centric summaries**

For each entity type, merge all per-chapter analysis references into compact per-entity profiles:

- Per character: merge all character analysis data across chapters → 200–500 tokens per character (includes chapters present, key actions per chapter, trait evolution, relationships per chapter)
- Per theme: merge thematic depth results across all chapters → 100–300 tokens per theme (chapters present, intensity, key quotes)
- Per location: merge psychogeography and setting data → 100–200 tokens per location
- Per plot element: merge story beats and structure data → summary of arc position

This condensation step is critical for large manuscripts. It reduces 2,000+ tokens of raw per-chapter JSON per entity down to 200–500 tokens, making synthesis feasible without exceeding context limits.

**Stage 2: Run synthesizers in parallel**

Dispatch each synthesizer as a Task subagent. Each synthesizer receives:
- The condensed entity data from Stage 1
- The entity map from Pass 1
- The project metadata (title, genre, chapter count, word count)
- The output format specification (Codex YAML node structure)

Synthesizer assignments (only run synthesizers for selected sections):

| Synthesizer | Input | Output Section |
|-------------|-------|----------------|
| CharacterSynthesizer | Condensed character profiles + entity map | `characters.codex.yaml` |
| TimelineSynthesizer | Condensed event data + story beats summaries | `timeline.codex.yaml` |
| ThemeSynthesizer | Condensed theme threads + emotional data | `themes.codex.yaml` |
| StructureSynthesizer | Condensed structure data + three-act analysis | `plot-structure.codex.yaml` |
| LocationSynthesizer | Condensed location data + psychogeography | `locations.codex.yaml` |
| RelationshipSynthesizer | Condensed relationship data + emotional arcs | `relationships.codex.yaml` |
| WorldSynthesizer | Faction data + world rules + artifacts | `world/` (fantasy/sci-fi only) |
| TopicMapSynthesizer | Summaries + tags + key arguments | `topic-map.codex.yaml` (nonfiction only) |
| ImageryDevicesSynthesizer | Literary devices + rhythmic data + imagery | `imagery.codex.yaml` (poetry only) |

For manuscripts with 50+ chapters or 30+ characters, add a meta-synthesizer after Stage 2 that checks cross-section consistency: timeline events match character arc turning points, relationship evolution is reflected in both the characters section and the relationships section, chapter references are accurate across all sections.

**Progress:**
- `"Synthesizing character arcs... {N} characters across {M} chapters."`
- `"Building timeline... {N} events mapped."`
- `"Weaving theme threads... {N} major themes."`
- `"Assembling atlas files... {N} sections."`

---

### Step 6: Write Atlas Files

Create the atlas directory and write all section files as Codex YAML, then register the atlas in the project index.

**Atlas directory structure:** Create as determined in Pass 0. Write each synthesizer's output to the appropriate file.

**Atlas index file** (`atlas/index.codex.yaml` or `{name}/index.codex.yaml`):

```yaml
type: atlas
name: "{atlas name}"
description: "{N} sections covering {N} characters, {N} events across {M} chapters"
atlas_type: story    # story | script | nonfiction | research | poetry
source_project: "{project name}"
generated: "{ISO 8601 timestamp}"
generator: "chapterwise-atlas"

style:
  preset: atlas-default    # atlas-default | atlas-dark | atlas-academic | atlas-fantasy

children:
  - type: section
    name: Characters
    src: characters.codex.yaml
  - type: section
    name: Timeline
    src: timeline.codex.yaml
  - type: section
    name: Themes
    src: themes.codex.yaml
  - type: section
    name: Plot Structure
    src: plot-structure.codex.yaml
  - type: section
    name: Locations
    src: locations.codex.yaml
  - type: section
    name: Relationships
    src: relationships.codex.yaml
```

**Section file format** (see Atlas Section Types below for full per-section schema).

**Project root index update:** Add or update the `atlases` array in the project's root `index.codex.yaml`:

```yaml
# In project root index.codex.yaml — add or append to atlases array
atlases:
  - name: "{atlas name}"
    path: {atlas-folder}/
    atlas_type: story
    generated: "{ISO 8601 timestamp}"
    generator: chapterwise-atlas
    sections: [characters, timeline, themes, plot-structure, locations, relationships]
```

The `atlases` array is separate from `children`. Atlases are not mixed into the manuscript content tree.

**Ask before committing:**

> "Atlas complete — {N} files ready. Commit to the project repo?"

Options: `[Commit]` `[Save without committing]` `[Review first]`

If committing, use this commit message format:
```
Add atlas: {name} ({N} sections, {N} characters, {N} events)

Sections: characters, timeline, themes, plot-structure, locations, relationships
Generated by chapterwise-atlas with {the model that actually ran}
```

Never auto-push to remote.

---

### Step 7: Save Recipe

Persist the atlas recipe for incremental updates.

```bash
echo '{
  "project_path": ".",
  "type": "atlas",
  "atlas": {
    "name": "{atlas name}",
    "slug": "{slug}",
    "output_path": "{atlas-folder}/"
  },
  "chapter_hashes": {CHAPTER_HASH_MAP},
  "entity_map": {ENTITY_MAP},
  "passes": {
    "pass0": {"status": "complete"},
    "pass1": {"status": "complete", "entities_found": {COUNTS}},
    "pass2": {"status": "complete", "modules_used": [...], "chapters_analyzed": N},
    "pass3": {"status": "complete", "sections_synthesized": [...]}
  },
  "structure": {
    "layout": "{simple|standard|detailed}",
    "sections_selected": [...],
    "sections_available": [...]
  }
}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py save
```

The recipe is saved at `.chapterwise/atlas-recipe/recipe.yaml` (or `.chapterwise/atlas-recipe-{slug}/recipe.yaml` for named atlases).

The chapter hashes are critical for the Update Pipeline — they enable diffing on the next `/atlas --update` run.

---

### Step 8: Validate and Heal Atlas Output

Run validators on the completed atlas. This step is mandatory — run it before presenting the final completion message.

**Validate atlas content:**

```bash
echo '{"path": "./atlas/", "fix": true}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/codex_validator.py
```

For named atlases, replace `./atlas/` with the actual atlas folder path.

The validator checks:
- Atlas `index.codex.yaml` has `type: atlas` and all required fields
- All section files listed in the index actually exist on disk
- UUIDs are present and unique across all nodes
- Entity names are consistent across sections (character "Elena" not "Elena Vasquez" in one section and "Elena V." in another)
- Chapter references point to real chapters in the manuscript
- `source` field is set on all generated nodes

With `fix: true`, it auto-repairs: missing UUIDs, missing frontmatter fields, orphan section files not registered in the index, word count fields.

**Validate recipe:**

```bash
echo '{"recipe_path": ".chapterwise/atlas-recipe/"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_validator.py
```

**Handling validator output:**
- If issues were auto-fixed: `"Cleaned up {N} formatting issues in atlas files."`
- If unfixable issues remain: `"The timeline section references chapter 29 which doesn't exist — review manually."` Flag these clearly.
- If everything is clean: say nothing, proceed silently.

Release criteria: both validators return `valid: true` before the completion message is shown.

**Completion message:**

> "Done. {atlas name} — {N} files, {N} characters, {N} events mapped."

Then show the file tree and next steps:

```
atlas/
├── index.codex.yaml
├── characters.codex.yaml    ({N} profiles with arcs)
├── timeline.codex.yaml      ({N} events, chronological)
├── themes.codex.yaml        ({N} themes with chapter mapping)
├── plot-structure.codex.yaml (three-act breakdown)
├── locations.codex.yaml     ({N} locations with significance)
└── relationships.codex.yaml ({N} relationships mapped)

Next steps:
  View on ChapterWise.app or open in VS Code
  Run /atlas --update after revisions
  Run /reader on atlas/ for a custom styled version
```

---

## Update Pipeline (--update flag)

Incremental update after manuscript changes. Re-analyzes only what changed — never rebuilds from scratch unless the scale of changes demands it.

### Update Step 1: Load Existing Recipe

```bash
echo '{"project_path": ".", "type": "atlas"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py load
```

If no recipe is found: `"No atlas found for this project. Run /atlas to build one first."`

Identify which atlas to update if multiple exist. If `--name` flag was provided, use that atlas. If multiple atlases exist and no name was given, ask:

> "You have {N} atlases: {list}. Which one to update?"

### Update Step 2: Diff Chapter Hashes

Compare current chapter content against the hashes stored in the recipe.

Hash each chapter file and compare against `recipe.source.chapter_hashes`.

Categorize each chapter:
- `unchanged` — hash matches
- `modified` — hash differs
- `added` — chapter not in recipe
- `removed` — chapter in recipe but not in project
- `moved` — same content hash, different file position

**Diff result format:**
```yaml
diff:
  unchanged: [1, 2, 3, 4, 6, ...]
  modified: [5, 12]
  added: [29, 30]
  removed: []
  moved: []
  summary:
    total_chapters_now: 30
    total_chapters_before: 28
    chapters_changed: 4
    chapters_unchanged: 26
```

**If no changes detected:** `"Your manuscript hasn't changed since the last atlas build. Nothing to update."`

**Progress:** `"Scanning for changes... {N} chapters changed ({M} modified, {K} new). {P} unchanged."`

**Edge cases:**

If more than 80% of chapters changed:
> "Almost your entire manuscript changed — it'll be faster to rebuild from scratch. Rebuild, or patch what I can?"

Options: `[Rebuild]` `[Patch anyway]`

If a character rename is detected across modified chapters:
> "It looks like '{old name}' is now '{new name}' in the revised chapters. Update the name across the entire atlas?"

Options: `[Yes, update everywhere]` `[No, keep both]`

If manuscript part structure changed:
> "Your manuscript structure changed — {N} parts now instead of {M}. The plot structure section needs rebuilding."

Automatically re-run the StructureSynthesizer.

### Update Step 3: Re-Extract Entities (changed chapters only)

Run entity extraction on modified and added chapters only.

Same extraction approach as Pass 1, but scoped to the changed chapter set. Include the last chapter before the change range as overlap context.

For removed chapters: mark entities that appeared exclusively in removed chapters as candidates for removal from the entity map.

**Merge with existing entity map:**

| Entity situation | Action |
|-----------------|--------|
| Existed before, still present | Update description and chapter list |
| New entity in added chapter | Add to entity map |
| Entity only in removed chapters | Remove from entity map |
| Entity in both removed and kept chapters | Keep, update chapter list |

**Progress:** `"Re-extracting entities from {N} changed chapters..."`

Report changes: `"Found {N} new characters, {M} new locations. {K} existing entities updated."`

### Update Step 4: Re-Analyze Changed Chapters (changed chapters only)

Same as Pass 2 scoped to modified and added chapters. Use the same module set from the original recipe.

```
Full atlas:    28 chapters x 10 modules = 280 analyses
After update:   4 chapters x 10 modules =  40 analyses (86% saved)
```

**Progress:** `"Analyzing {N} changed chapters with {M} modules..."`

### Update Step 5: Determine Re-Synthesis Strategy

Choose between selective re-synthesis and full re-synthesis:

- If fewer than 50% of chapters changed: **selective** — re-run only affected synthesizers
- If 50% or more chapters changed: **full** — rebuild all sections from fresh analysis

**Affected section mapping for selective re-synthesis:**

| What changed | Sections to re-synthesize |
|-------------|--------------------------|
| Character added, removed, or modified | Characters, Relationships |
| New chapters added | Timeline, Plot Structure, Characters (if new character appearances) |
| Chapter rewritten (same characters) | Timeline, Themes |
| Chapter removed | Timeline, Plot Structure, Characters (remove chapter references) |
| Location added or changed | Locations |
| Theme shift detected | Themes |

**Progress (selective):** `"Re-synthesizing {N} of {M} atlas sections..."`

**Progress (full):** `"Too many changes for selective patching — rebuilding atlas from fresh analysis."`

### Update Step 6: Re-Synthesize Affected Sections

Run only the affected synthesizers using the same approach as Pass 3.

**Preserve user edits.** Atlas nodes have a `source` field:
```yaml
source: generated   # Agent wrote this — safe to update
source: user        # Writer added this — never overwrite
```

When patching sections, update `source: generated` nodes with new synthesized content. Never touch `source: user` nodes. If a synthesizer would overwrite a user node, skip that node and leave a note.

### Update Step 7: Patch Atlas Files

Update changed sections in place, preserving unchanged sections and all user edits.

1. Open each affected section file
2. Replace `source: generated` nodes that changed with updated synthesis output
3. Preserve `source: user` nodes exactly as-is
4. Write new files for any new sections
5. Remove sections for removed content
6. Update `atlas/index.codex.yaml` if sections were added or removed
7. Update the `generated` timestamp in the project root `index.codex.yaml` for this atlas entry

**Commit message format:**
```
Update atlas: {N} characters updated, {M} chapters added, timeline patched

Changed chapters: {list} (modified), {list} (added)
Sections updated: characters, timeline, plot-structure
Sections unchanged: themes, locations, relationships
```

**Progress:** `"Patching atlas files... {N} sections updated, {M} preserved."`

### Update Step 8: Validate Updated Atlas

```bash
echo '{"path": "./atlas/", "fix": true}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/codex_validator.py
```

Cross-validate updated sections against preserved sections:
- Updated timeline events reference real chapters
- Character arc turning points in the character section match relationship evolution in the relationships section
- User-edited nodes (`source: user`) were not modified

```bash
echo '{"recipe_path": ".chapterwise/atlas-recipe/"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_validator.py
```

### Update Step 9: Update Recipe

Patch the recipe — append to the `updates` array, update `chapter_hashes`, and update the `updated` timestamp.

```bash
echo '{
  "project_path": ".",
  "type": "atlas",
  "patch": {
    "chapter_hashes": {UPDATED_HASH_MAP},
    "update_entry": {
      "date": "{ISO 8601}",
      "trigger": "manual",
      "chapters_changed": {"modified": [...], "added": [...], "removed": []},
      "entities_changed": {"added": [...], "updated": [...], "removed": []},
      "sections_resynthesized": [...],
      "sections_preserved": [...],
      "strategy": "selective"
    }
  }
}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_manager.py patch
```

**Completion:** `"Done. Atlas updated in {N} seconds."`

Show a change summary:
```
Changes:
  +{N} characters ({names})
  +{M} timeline events
  +{K} chapters mapped ({list})
  {P} sections unchanged ({list})
```

---

## Management Commands

### --list

Read the `atlases` array from the project root `index.codex.yaml` and display a formatted summary.

For each atlas entry, show: name, path, atlas type, sections built, total section count, and when it was last generated or updated.

Example output:
```
2 atlases in this project:

  Story Atlas        atlas/         story     6 sections    built 3 days ago
  World Atlas        world-atlas/   story     4 sections    built 1 week ago
```

If no atlases exist: `"No atlases found. Run /atlas to build one."`

### --name "X"

Build a named atlas instead of the default `atlas/` folder. Slugify the name (lowercase, hyphens, no spaces) to use as the folder name and recipe folder name.

Example:
- `--name "World Atlas"` → folder `world-atlas/`, recipe at `.chapterwise/atlas-recipe-world-atlas/`
- `--name "Character Deep Dive"` → folder `character-deep-dive/`, recipe at `.chapterwise/atlas-recipe-character-deep-dive/`

Set `atlas.name` and `atlas.slug` in the recipe accordingly. Continue with the full Build New Atlas pipeline from Step 2.

### --rebuild

Clean rebuild: delete the existing atlas and start from scratch.

1. Identify which atlas to rebuild (ask if multiple exist)
2. Confirm with the user:
   > "This will delete {atlas name} and rebuild from scratch. Any notes you added (`source: user`) will be lost. Continue?"
3. Delete the atlas output folder
4. Delete `.chapterwise/atlas-recipe/` (or named recipe folder)
5. Remove the atlas entry from the project root `index.codex.yaml` `atlases` array
6. Run the full Build New Atlas pipeline from Step 2

### --delete

Delete an atlas entirely — folder, recipe, and index registration.

1. If multiple atlases exist, ask which one to delete:
   > "You have {N} atlases: {list}. Which one to delete?"
2. Confirm:
   > "Delete {atlas name}? This removes {N} files and can't be undone."
3. Delete the atlas output folder
4. Delete the recipe folder at `.chapterwise/atlas-recipe[-{slug}]/`
5. Remove the entry from the project root `index.codex.yaml` `atlases` array
6. Commit: `"Delete atlas: {name}"`

### --add-sections

Extend an existing atlas with additional sections that were not built in the original run.

1. Load the existing atlas recipe
2. Identify which sections exist (`structure.sections_selected` in recipe)
3. Identify which sections are available but not yet built (`structure.sections_available` minus already built)
4. Present available sections to the user:
   > "Your {atlas name} has: {existing sections}.
   > Available to add: {available sections}.
   > Which sections to add?"
5. Run only the necessary synthesizers for the selected new sections (Stage 2 from Pass 3)
6. Write new section files
7. Update the atlas `index.codex.yaml` to include new sections
8. Update the project root `index.codex.yaml` `atlases` entry `sections` list
9. Update the recipe `structure.sections_selected` and the `updated` timestamp
10. Run validators on the new section files

**Progress:** `"Adding {section names}..."`
`"Synthesizing {section}... {data}."`

**Completion:** `"Done. {atlas name} updated — now {N} sections."`

---

## Atlas Section Types

Full schemas for each section type are documented in the reference file.

Read `${CLAUDE_PLUGIN_ROOT}/references/atlas-section-schemas.md` for the complete YAML format for each section type: Characters, Timeline, Themes, Plot Structure, Locations, Relationships, World (fantasy), Topic Map (nonfiction), Imagery (poetry).

Each section follows the standard Codex node schema with section-specific `attributes` and `children` structures.

---

## Context Window Strategy

**Pass 1 (Entity Extraction):**

Process chapters individually with overlapping context. Never load the full manuscript at once.

- Process each chapter with a sliding 500-token overlap from the previous chapter
- Batch chapters into groups of 7 for parallel Task subagents
- Merge entity results after all batches complete, resolving duplicates by name similarity

**Pass 3 (Synthesis):**

Two-stage synthesis prevents context overflow even for large manuscripts.

- Stage 1: Condense per-chapter analysis JSON into entity-centric summaries (200–500 tokens per entity)
- Stage 2: Each synthesizer receives only the condensed summaries, not raw per-chapter dumps
- CharacterSynthesizer: ~500 tokens × 14 characters = ~7,000 tokens (fits comfortably)
- TimelineSynthesizer: entity map events + story beats summaries = ~5,000 tokens
- ThemeSynthesizer: condensed theme threads = ~3,000 tokens
- Each synthesizer runs as an independent Task subagent with its own context window

For extremely large manuscripts (50+ chapters, 30+ characters), run a meta-synthesizer after all section synthesizers complete. The meta-synthesizer reads all section outputs and checks cross-section consistency without needing all raw data in context.

---

## Multi-Atlas Support

A project can have multiple atlases — each with a different name, focus, and folder.

**Common patterns:**
- "Story Atlas" — characters, timeline, themes, plot structure (default)
- "World Atlas" — locations, factions, magic system, artifacts (fantasy/sci-fi)
- "Character Deep Dive" — characters section only, maximum synthesis depth using Opus
- "Revision Atlas" — generated after a full rewrite, for comparison with the original

Each atlas has its own:
- Output folder (e.g., `atlas/`, `world-atlas/`, `character-deep-dive/`)
- Recipe folder (e.g., `.chapterwise/atlas-recipe/`, `.chapterwise/atlas-recipe-world-atlas/`)
- Entry in the project root `index.codex.yaml` `atlases` array

The `atlases` array in the project root index is how ChapterWise.app, the VS Code extension, and the /reader command discover and render atlases. Each atlas displays in a dedicated section separate from the manuscript content tree.

When multiple atlases exist, always clarify which atlas a command applies to. If the `--name` flag is not provided and multiple atlases exist, ask:
> "You have {N} atlases: {list}. Which one?"

---

## Error Handling

| Situation | Response |
|-----------|----------|
| Manuscript too short (under 3 chapters) | "Your manuscript is {N} chapters — an atlas needs more material to synthesize across. Try running individual analysis modules instead." |
| Pass 2 partial failure | "Analyzed {N} of {M} chapters. {K} had issues — building atlas from available data, flagging gaps." |
| Synthesis timeout on large manuscript | "Synthesis is taking longer than expected for {N} chapters. Continuing..." |
| Atlas already exists, no flag provided | "Found an existing atlas. Update it with your latest changes, or build a new one?" |
| Unknown manuscript type | "I can't determine the genre from the content. What type of work is this?" |
| Missing `index.codex.yaml` | "No Codex project found here. Run /import first to convert your manuscript into a Codex project." |
| Atlas file manually deleted | "The {section name} section file is missing from the atlas folder. Regenerate it, or skip?" |
| Character renamed across modified chapters | "'{old name}' appears to be '{new name}' in the revised chapters. Update the name across the entire atlas?" |
| No changes in update run | "Your manuscript hasn't changed since the last atlas build. Nothing to update." |
| Massive rewrite (>80% chapters changed) | "Almost your entire manuscript changed — rebuilding from scratch will be faster than patching. Rebuild, or patch anyway?" |

---

## Language Rules

Read and follow `${CLAUDE_PLUGIN_ROOT}/references/principles.md` — especially **LLM Judgment, User Override**.
Follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all shared messaging rules.

**Atlas-specific phases:**

| Phase | Cooking verb | Example |
|-------|-------------|---------|
| Pass 0: Scan manuscript | Scanning | "Scanning manuscript... literary fiction, 28 chapters, 87,000 words." |
| Section selection | Building / Selecting | "Building characters, timeline, themes. 3 of 6 sections selected." |
| Pass 1: Extract entities | Extracting | "Extracting entities... 14 characters, 8 locations, 47 events." |
| Existing analysis check | (silent or descriptive) | "Found existing analysis for 20 of 28 chapters. Re-analyzing 8 changed." |
| Pass 2: Per-chapter analysis | Analyzing | "Analyzing 8 chapters with 10 modules... running in parallel." |
| Pass 3: Synthesize characters | Synthesizing | "Synthesizing character arcs... 14 characters across 28 chapters." |
| Pass 3: Synthesize timeline | Building | "Building timeline... 47 events mapped." |
| Pass 3: Synthesize themes | Weaving | "Weaving theme threads... 6 major themes." |
| Pass 3: Write files | Assembling | "Assembling atlas files... 6 sections." |
| Update: compare hashes | Scanning | "Scanning for changes... 4 chapters changed, 26 unchanged." |
| Update: re-extract | Re-extracting | "Re-extracting entities from 4 changed chapters..." |
| Update: merge entity data | Merging | "Merging entity changes... 2 added, 3 updated, 0 removed." |
| Update: re-synthesize | Re-synthesizing | "Re-synthesizing 3 of 6 atlas sections..." |
| Update: patch files | Patching | "Patching atlas files... 3 sections updated, 3 preserved." |
| Completion | Done | "Done. Story Atlas — 6 files, 14 characters, 47 events mapped." |
