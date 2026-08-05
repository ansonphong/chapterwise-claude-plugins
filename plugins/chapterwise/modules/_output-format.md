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
            {"key": "model", "value": "claude-sonnet-4"},
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

## Important Notes

- Module IDs MUST use snake_case: `plot_holes`, NOT `plot-holes`
- Attribute keys MUST use snake_case: `word_count`, NOT `wordCount`
- All scores should be integers 1-10
- Use markdown formatting: `## Headers`, `**bold**`, `- lists`, `> quotes`
