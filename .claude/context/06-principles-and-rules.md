# Principles and Rules

## Three Core Principles

1. **LLM Judgment, User Override** -- The agent makes intelligent decisions about structure, depth, and format, but always yields to explicit user preferences. Preference cascade (later wins): plugin defaults, `.claude/chapterwise.local.md`, command variant, prompt language.

2. **Clean Defaults, Rich Options** -- Commands work with zero configuration. First run produces useful output. Power users customize via preferences, flags, and natural language.

3. **Data Over Flare** -- Every progress message includes real data (chapter counts, word counts, file counts, entity names). No theatrical language, no emojis.

## Language Rules

- **Never say "recipe" to the user.** The recipe system is internal only.
- **No theatrical cooking language.** Forbidden: "order up", "bon appetit", "chef's kiss", "ready to serve", "plating", "garnish".
- **Cooking verbs as action verbs** -- scan, slice, season, simmer, fold, reduce, distill, gather, assemble. Paired with technical nouns and real data, not used as metaphors.
- **Progress formula:** `[cooking verb] [technical noun]... [real data]` -- e.g., "Scanning structure... PDF, 342 pages, three-act novel."
- **Completion:** Say "Done." -- plain, no flare.
- **Tool rules:** Use Glob (not find), Read (not cat), Grep (not grep/rg in Bash).

## Recipe System (Internal)

Recipes are state-tracking folders at `.chapterwise/<type>-recipe/` in the user's project. Types: import, analysis, atlas, reader. Managed by `recipe_manager.py` (create/load/list/validate/update). Validated by `recipe_validator.py` after every save. The recipe concept is never exposed to users.

## User Preferences

Stored in `.claude/chapterwise.local.md` in the user's project (not the plugin repo):
- YAML frontmatter for structured config (per-command sections)
- Markdown body for freeform project notes
- Created on first use if absent
- Only sections for used commands are added
- Override vs mutate: prompt overrides apply once; explicit "always use X" updates the file

## Modular Rules (`.claude/rules/`)

Contextual rules that load when working on matching files:
- `commands.md` -- Command file structure, frontmatter format, conventions
- `scripts.md` -- Script I/O patterns (stdin JSON preferred), conventions
- `testing.md` -- pytest conventions, TDD approach
- `codex-format.md` -- Codex V1.3 structure, Codex Lite structure, validation workflow

## Validation After Output

- Run `codex_validator.py` after generating codex files (silent on success)
- Run `recipe_validator.py` after saving recipes (silent on success)
- Auto-fix what is safe; report only unfixable issues
