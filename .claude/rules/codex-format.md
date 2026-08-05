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
