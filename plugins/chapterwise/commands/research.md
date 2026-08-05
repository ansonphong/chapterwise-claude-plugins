---
description: "Research any topic and generate structured codex reference files"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, AskUserQuestion, Task, WebSearch, WebFetch, Agent
triggers:
  - research
  - chapterwise:research
argument-hint: "<topic or instruction>"
---

# ChapterWise Research

## Overview

Research any topic and produce structured reference files in Codex format, stored in `.chapterwise/research/`. Research is clean and standalone by default — no manuscript scanning unless explicitly requested. The agent decides depth, structure, and web search usage based on topic scope, but the user's natural language always overrides.

Read and follow `${CLAUDE_PLUGIN_ROOT}/references/principles.md` — especially **LLM Judgment, User Override**.

Read and follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all progress messages.

---

## Command Flow

### Step 1: Parse the Prompt

Extract from the user's input:

| Signal | What to detect |
|--------|---------------|
| **Topic** | The subject to research |
| **Depth hints** | "deep dive", "comprehensive", "massive compendium", "quick overview", "brief" |
| **Structure hints** | "one file per god", "flat list", "single document", "organize by region" |
| **Format override** | "output as JSON", "use markdown", "codex format" |
| **Web hints** | "use web sources", "search the web", "no web", "from memory only" |
| **Manuscript references** | "relate to my character", "compare with chapter 5", "relevant to my novel" |
| **Output path override** | "put it in my worldbuilding folder", "save to research/mythology/" |

If the user references their manuscript or specific chapters, set context to `manuscript-informed`. Otherwise, default to `standalone`.

---

### Step 2: Load Settings

```bash
echo '{"path": ".", "section": "research"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/settings.py resolve
```

Returns `format`, `depth`, and `output_dir` (already an absolute path), plus `found` and a
`sources` map.

| Key | Default | Meaning |
|---|---|---|
| `research.format` | `codex-md` | `codex-md` or `codex-json` |
| `research.depth` | `standard` | `standard` or `deep` |
| `research.output_dir` | `.chapterwise/research` | Relative to the **project root** |

Research output stays under `.chapterwise/` on purpose: it is reference material consulted
*while* writing, not a deliverable derived *from* the manuscript. Atlases, readers and
analysis reports are the latter, which is why those sit in visible folders.

`sources` marks each value `settings` or `default`. Prompt language still overrides
everything, for this invocation only.

---

### Step 3: Apply Defaults (First Run)

If nothing is configured, use the defaults **silently**. Do NOT ask — this follows
Principle 2 (Clean Defaults); the first run should produce useful output without an
interview.

After the research completes (Step 9), if `found` was `false`, offer once to save:

> "Save these as this project's defaults? Codex Markdown, standard depth."

```bash
echo '{"path": ".", "updates": {"research": {"format": "codex-md", "depth": "standard"}}}' \
  | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/settings.py set
```

A one-off override — "output this one as JSON" — is obeyed for that run and **never**
written back. "Always use JSON from now on" is the sentence that changes the setting.

---

### Step 4: Determine Scope

Apply the preference cascade (Principle 1) to resolve:

**Depth:**
- Default: `standard`
- Saved preference: `research.default_depth`
- Prompt override: detect "deep", "comprehensive", "massive" → `deep`; detect "brief", "quick", "overview" → `standard`

**Structure (LLM judgment):**

| Topic scope | Agent decision |
|-------------|---------------|
| Narrow, focused topic | Single file |
| Broad topic, standard depth | Folder with overview file, sub-sections as children within it |
| Broad topic, deep mode | Folder with overview + individual sub-files |
| User specifies structure | Obey exactly |

**Format:**
- Saved preference or first-run choice
- Prompt override for this invocation (don't mutate saved preference)

---

### Step 5: Determine Sources

The agent decides whether to use web search based on topic type:

| Scenario | Decision |
|----------|----------|
| Well-known topic (major history, famous figures, established science) | LLM knowledge first. Web if gaps detected. |
| Niche topic (obscure mythology, specific technical details, regional history) | Web search by default |
| Recent events, current data, statistics | Web search required |
| User says "use web sources" or "search for this" | Always search |
| User says "no web" or "from memory" | LLM knowledge only |

When using web search:
1. Use WebSearch to find relevant sources
2. Use WebFetch to read promising results
3. Cite every web source in the `credits.webSources` array
4. Include URL, page title, and access timestamp for each source

---

### Step 6: Determine Context

**Default: Standalone.** Do NOT scan the manuscript unless the user explicitly asks.

| User says | Context |
|-----------|---------|
| "research Sumerian Gods" | `standalone` — pure research, no manuscript |
| "research Sumerian Gods relevant to my novel" | `manuscript-informed` — scan project for context |
| "relate Enlil to my character Archon" | `manuscript-informed` — read specific chapters |
| "how does my character diverge from trickster gods" | `manuscript-informed` — deep manuscript scan + research |

When manuscript-informed:
1. Read `index.codex.yaml` to understand the project
2. Read relevant chapter files as needed
3. Blend research with manuscript context in the output
4. Set `context: manuscript-informed` in the output attributes

---

### Step 7: Research

Execute the research based on resolved scope, sources, and context.

**Progress message:** `"Sourcing {topic}..."`

If web-augmented: `"Sourcing {topic}... gathering web references."`

If manuscript-informed: `"Sourcing {topic}... cross-referencing with manuscript."`

Generate thorough, well-structured content. For deep mode, aim for comprehensive coverage. For standard mode, aim for a solid, useful reference document.

---

### Step 8: Write Output

**Output root:** `.chapterwise/research/` (or user-specified path)

**Folder and file naming:** Use LLM judgment to create clean, descriptive slugs from the topic.

Examples:
- Topic "Sumerian Gods" → `sumerian-gods/`
- Topic "How cyanide poisoning works" → `cyanide-poisoning.codex.md` (single file)
- Topic "All trickster gods across mythology" (deep) → `trickster-gods/overview.codex.md` + sub-files

**If updating existing research:** Detect by matching the slugified topic against existing filenames or folder names in `.chapterwise/research/`. If a match is found:

1. Use AskUserQuestion: "Research on '{topic}' already exists at {path}. Update it or create a new version?"
   - **Update** — Merge new content into existing file. Preserve existing sections, add new ones, update the `updated` timestamp. Append new model credits.
   - **New version** — Create a new file with a date suffix (e.g., `sumerian-gods-2026-03-09/`)
2. When updating: preserve `depth`, `sources`, `context` from the new run. Keep all existing credits and append new ones.

#### Codex Markdown Format (.codex.md)

```markdown
---
type: research
topic: "{topic}"
depth: standard
sources: llm-knowledge
context: standalone
tags: [tag1, tag2, tag3]
credits:
  models:
    - "{your-model-name} ({your-provider})" — primary-researcher
  web_sources:
    - "[Page Title](https://example.com)" (2026-03-09)
---

# {Topic Title}

{Structured research content with sections and subsections...}
```

#### Codex V1.3 JSON Format (.research.json)

```json
{
  "metadata": {
    "formatVersion": "1.3",
    "created": "{ISO 8601}",
    "updated": "{ISO 8601}"
  },
  "id": "{topic-slug}",
  "type": "research",
  "name": "{Topic Title}",
  "summary": "{One-line summary of the research}",
  "body": "{Main markdown content}",
  "tags": ["tag1", "tag2"],
  "attributes": [
    {"key": "topic", "value": "{topic}", "dataType": "string"},
    {"key": "depth", "value": "standard", "dataType": "string"},
    {"key": "sources", "value": "llm-knowledge", "dataType": "string"},
    {"key": "context", "value": "standalone", "dataType": "string"}
  ],
  "credits": {
    "models": [
      {
        "name": "{your-model-name}",
        "provider": "{your-provider}",
        "role": "primary-researcher"
      }
    ],
    "webSources": [
      {
        "url": "https://example.com",
        "title": "Page Title",
        "accessedAt": "{ISO 8601}"
      }
    ]
  },
  "children": []
}
```

#### Credits Rules

- **`credits.models`** — Add yourself to this array. Use your actual model name (e.g., `claude-sonnet-4-6`, `claude-opus-4-6`) and provider. Do NOT hardcode a specific model — report whatever model you actually are. If this research is later augmented by a different model or provider, that model appends itself.
- **`credits.webSources`** — Every WebFetch call produces a citation. Include URL, page title, and access date (ISO 8601). Never omit a source that was actually used. In Codex Markdown format, use: `"[Title](url)" (YYYY-MM-DD)`.
- When updating existing research, append new credits — never replace the existing list.

#### Children Structure

For multi-section research, use the `children` array (JSON) or subsections (Markdown):

**JSON children types:**
- `research-section` — A major section grouping
- `research-entry` — An individual entity or topic entry

**Example (deep mode, one entry per deity):**

```json
"children": [
  {
    "id": "major-deities",
    "type": "research-section",
    "name": "Major Deities",
    "body": "Overview of the primary gods...",
    "children": [
      {
        "id": "anu",
        "type": "research-entry",
        "name": "Anu — Sky Father",
        "summary": "Supreme god of the heavens",
        "body": "Anu (also known as An) was..."
      }
    ]
  }
]
```

---

### Step 9: Validate Output

Run validation on all written files. This step is mandatory — run it before the completion message.

For Codex JSON (`.research.json`) files:
1. Parse as JSON — verify valid structure
2. Verify required Codex V1.3 fields: `metadata`, `id`, `type: "research"`, `attributes`, `credits`
3. Verify `credits.models` is non-empty (agent must have added itself)

For Codex Markdown (`.codex.md`) files:
1. Verify YAML frontmatter parses correctly
2. Verify `type: research` is present
3. Verify credits section exists in frontmatter

If available, run the codex validator:
```bash
echo '{"path": ".chapterwise/research/{topic-slug}/", "fix": true}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/codex_validator.py
```

- If all clean: say nothing — validation is invisible.
- If auto-fixed: note fixes silently and proceed.
- If unfixable issues: report them to the user before the brief.

---

### Step 10: Brief the User

Report what was created:

**Single file:**
> "Done. Research saved to `.chapterwise/research/cyanide-poisoning.codex.md`."

**Multi-file:**
> "Done. {N} research files saved to `.chapterwise/research/sumerian-gods/`."

Then show the file tree:

```
.chapterwise/research/sumerian-gods/
├── overview.codex.md
├── anu.codex.md
├── enlil.codex.md
├── enki.codex.md
└── inanna.codex.md
```

If web sources were used, note the count:
> "{N} web sources cited."

---

## Key Attributes Reference

| Attribute | Values | Purpose |
|-----------|--------|---------|
| `topic` | Free text | The research subject |
| `depth` | `standard` \| `deep` | How extensive the research is |
| `sources` | `llm-knowledge` \| `web-augmented` | Whether web sources were used |
| `context` | `standalone` \| `manuscript-informed` | Whether the manuscript was referenced |

---

## Research-Specific Language Rules

Follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all shared rules.

| Phase | Verb | Example |
|-------|------|---------|
| Start research | Sourcing | "Sourcing Sumerian mythology..." |
| Web search | Gathering | "Gathering web references... 5 relevant pages found." |
| Manuscript scan | Cross-referencing | "Cross-referencing with manuscript... 3 chapters mention Enlil." |
| Structuring output | Distilling | "Distilling research... 5 entries across 3 sections." |
| Writing files | Assembling | "Assembling research files... 5 entries." |
| Completion | Done | "Done. 5 research files saved to .chapterwise/research/sumerian-gods/." |

---

## Error Handling

| Situation | Response |
|-----------|----------|
| No topic provided | "What would you like to research?" (use AskUserQuestion) |
| Web search returns no results | Fall back to LLM knowledge. Note `sources: llm-knowledge` in output. |
| Web fetch fails on a URL | Skip that source, continue with others. Do not cite failed fetches. |
| Output directory not writable | Report the error and suggest an alternative path. |
| Manuscript referenced but no codex files found | "No Codex project found here. Running standalone research instead." Set context to `standalone`. |
| Existing research file found for same topic | Ask user: update existing or create new version. See Step 8 update flow. |
