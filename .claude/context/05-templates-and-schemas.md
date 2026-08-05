# Templates and Schemas

## Reader Templates

Two HTML reader templates in `plugins/chapterwise/templates/`, each containing `index.html`, `style.css`, and `reader.js`:

| Template | Path | Description |
|----------|------|-------------|
| **minimal-reader** | `templates/minimal-reader/` | Clean, minimal reading experience. Default template. |
| **academic-reader** | `templates/academic-reader/` | Academic-style with citations and annotation support. |

The `/reader` command copies a template, injects codex content, and produces a self-contained static HTML reader. Template selection via `--template` flag or user preference.

## JSON Schemas (repo root `schemas/`)

Three JSON Schema files (Draft 2020-12) defining the Codex V1.3 ecosystem:

| Schema | File | Validates |
|--------|------|-----------|
| **Codex V1.3** | `schemas/codex-v1.3.schema.json` | `.codex.yaml` files. Recursive structure: metadata, id, type, name, summary, body, attributes, tags, children, relations. |
| **Analysis V1.2** | `schemas/analysis-v1.3.schema.json` | `.analysis.json` files. Wraps analysis-module children containing analysis-entry children with sourceHash, model, timestamp. |
| **Research V1.2** | `schemas/research-v1.3.schema.json` | `.research.json` files. Research output format for `/research` and `/research:deep` commands. |

Schema resolution in `schema_validator.py`: `Path(__file__).parent.parent.parent.parent / 'schemas'` (from `scripts/` up to repo root).

## Recipe Schema (plugin-level)

| Schema | File | Validates |
|--------|------|-----------|
| **Recipe** | `plugins/chapterwise/schemas/recipe.schema.yaml` | `.chapterwise/<type>-recipe/recipe.yaml` files. |

Recipe schema properties: type (import/analysis/atlas/reader), version, created, source (project_path, chapter_count, word_count, chapter_hashes), manuscript (title, author, type, structure), strategy, preferences, passes, modules, atlas, structure, output, updates.

## Reference Documents (`plugins/chapterwise/references/`)

| File | Content |
|------|---------|
| `principles.md` | Three core principles (LLM Judgment/User Override, Clean Defaults/Rich Options, Data Over Flare) + preference cascade + preference storage format |
| `language-rules.md` | Progress message formula, cooking verb rules, tool usage rules, validation rules |
| `insert-marker-format.md` | INSERT marker syntax for review workflow |
| `insert-edge-cases.md` | Edge cases for the insert command |
| `insert-workflows.md` | Insert command workflow documentation |
| `atlas-section-schemas.md` | Atlas section structure definitions |
