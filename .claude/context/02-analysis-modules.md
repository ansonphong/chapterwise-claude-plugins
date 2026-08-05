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

1. Module prompt is read from its `.md` file body (after frontmatter)
2. Source codex file content is fed alongside the module prompt
3. LLM produces structured JSON matching `_output-format.md` schema
4. `analysis_writer.py` wraps output in Codex V1.3 structure and saves to `.analysis.json`
5. `staleness_checker.py` uses SHA-256 hash (first 16 chars) to detect when source changes

## Output Format

Each module produces: `body` (markdown), `summary` (1-2 sentences), `children` (2-5 sub-sections), `attributes` (scored metrics, integers 1-10), `tags`. Module IDs and attribute keys use snake_case. Results stored per-module with up to 3 historical entries.

## Genre-Aware Recommendations

`module_loader.py recommend` maps genres to module sets. Supported genres: literary_fiction, thriller, fantasy, nonfiction, poetry. Unknown genres get all course modules as default.
