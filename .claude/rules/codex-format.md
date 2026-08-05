# Rules: Codex Format

Applies when creating or modifying codex output files (`.codex.yaml`, `.codex.md`, `.analysis.json`, `.research.json`).

## Codex V1.3 JSON Structure

```json
{
  "metadata": { "formatVersion": "1.3", "created": "ISO-8601", "updated": "ISO-8601" },
  "id": "unique-slug",
  "type": "chapter|analysis|research|atlas|...",
  "name": "Display Name",
  "summary": "One-line description",
  "body": "Markdown content",
  "attributes": [{ "key": "name", "value": "val", "dataType": "string" }],
  "tags": ["keyword"],
  "children": [],
  "relations": [{ "targetId": "other-id", "kind": "references" }]
}
```

## Codex Lite (Markdown) Structure

```markdown
---
type: document
summary: "Brief description"
tags: tag1, tag2
status: draft
---

# Title

Content in standard Markdown...
```

## Validation

- Always run `codex_validator.py` after generating codex output
- Schema files live in `schemas/` (codex-v1.3.schema.json, analysis-v1.3.schema.json, research-v1.3.schema.json)
- Silent on success — only report auto-fixes and unfixable issues

**A generator that emits codex must go through the format machinery, not imitate it.**
Import `CodexAutoFixer` from `auto_fixer.py` — the engine behind `/chapterwise:format` —
hand it the assembled document, and validate the result with
`schema_validator.validate_codex`. `analysis_report.py:render_codex` is the reference
implementation. Two rules the fixer enforces that hand-written emitters get wrong:

- **Attribute keys are lowercase**, `^[a-z][a-z0-9_-]*$`. `source_file`, never `sourceFile`.
- **Node ids must be v4-shaped.** Anything else is treated as broken and replaced, which
  silently breaks deterministic output. See `analysis_report.stable_id`.

## Schema Resolution

Schema files are at the **repository root** in `schemas/`:

```
schemas/
├── codex-v1.3.schema.json
├── analysis-v1.3.schema.json
└── research-v1.3.schema.json
```

The `schema_validator.py` script resolves schemas relative to itself:
`Path(__file__).parent.parent.parent.parent / 'schemas'`
(from `plugins/chapterwise/scripts/` → repo root → `schemas/`)

When invoking validation from commands, use:
```bash
echo '{"path": "./output/", "fix": true}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/codex_validator.py
```

The validator finds schemas automatically — no path argument needed.
