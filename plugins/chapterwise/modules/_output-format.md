# Codex V1.3 Analysis Output Format

All analysis modules MUST output results matching this exact format.
For the authoritative schema, see: `schemas/analysis-v1.3.schema.json`

## Required JSON Structure

```json
{
  "body": "## Module Name\n\nMain analysis content in markdown...",
  "summary": "One-line summary of findings",
  "children": [
    {
      "name": "Section Name",
      "summary": "Section summary",
      "content": "## Section\n\nDetailed content...",
      "attributes": [
        {"key": "score", "name": "Score", "value": 8, "dataType": "int"}
      ]
    }
  ],
  "tags": ["analysis", "module-name"],
  "attributes": [
    {"key": "overall_score", "name": "Overall Score", "value": 7, "dataType": "int"}
  ]
}
```

## How Your Output Becomes an Analysis Entry

The `analysis_writer.py` script wraps your output in the full Codex V1.3 structure:

```json
{
  "metadata": {"formatVersion": "1.3", "created": "...", "updated": "..."},
  "id": "{basename}-analysis",
  "type": "analysis",
  "attributes": [
    {"key": "sourceFile", "value": "source.codex.yaml"},
    {"key": "sourceHash", "value": "16-char-sha256-hash"}
  ],
  "children": [
    {
      "id": "module_name",
      "type": "analysis-module",
      "name": "Module Display Name",
      "children": [
        {
          "id": "entry-YYYYMMDDTHHMMSSz",
          "type": "analysis-entry",
          "status": "published",
          "attributes": [
            {"key": "model", "value": "<the model that actually ran>"},
            {"key": "sourceHash", "value": "16-char-hash"},
            {"key": "analysisStatus", "value": "current"},
            {"key": "timestamp", "value": "ISO-8601"}
          ],
          "body": "YOUR body FIELD",
          "summary": "YOUR summary FIELD",
          "children": "YOUR children ARRAY",
          "tags": "YOUR tags ARRAY"
        }
      ]
    }
  ]
}
```

## Rules

1. **body** - Main analysis in markdown with ## headers (REQUIRED)
2. **summary** - 1-2 sentence overview (REQUIRED)
3. **children** - Structured sub-sections (2-5 recommended)
4. **attributes** - Scored metrics with dataType hint
5. **tags** - Relevant keywords for searchability
6. **model** - Report the model you actually are (e.g. `claude-opus-5`). Do NOT
   copy the example value and do NOT guess. The entry is a provenance record —
   an unreported model is written as `unknown`, which is honest; a wrong model
   name is not. Alternatively pass `--model` to `analysis_writer.py`.

## Scope

A codex file can hold many analyzable nodes — a dome script is one file with 9
acts and 36 beats inside. Each node analyzed gets its own entry in the same
`.analysis.json`, distinguished by a `scope` attribute.

| Attribute | Value | Notes |
|---|---|---|
| `scope` | `root` or `node:<id>` | absent means `root` — that is what pre-scope entries are |
| `scopeName` | `Quantum Embryo` | display name |
| `scopePath` | `Chrysalis › In The Void › Quantum Embryo` | disambiguates repeated names |
| `scopeDepth` | `2` | depth in the source tree |
| `scopeIndex` | `1` | document order, used to assemble reports |

The command layer sets these via `--scope*` flags on `analysis_writer.py`. Each
scope keeps its own history, so re-analyzing one beat leaves the others intact.

**If your module defines more than one output shape, select it by scope.**
`immersive_design` is the reference case: `root` produces the whole-show shape
(arc map, motion budget, breath coverage, the landing), `node:*` produces the
scene shape (effects in play, proposed effects, rhythm and breath, comfort and
load). State the rule in your module's own Scope section — the runner follows
whatever the module says.

## Important Notes

- Module IDs MUST use snake_case: `plot_holes`, NOT `plot-holes`
- Attribute keys MUST use snake_case: `word_count`, NOT `wordCount`
- All scores should be integers 1-10
- Use markdown formatting: `## Headers`, `**bold**`, `- lists`, `> quotes`
