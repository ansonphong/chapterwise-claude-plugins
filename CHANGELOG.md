# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
