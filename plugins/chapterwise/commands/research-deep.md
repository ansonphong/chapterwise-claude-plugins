---
description: "Deep research — generate a multi-document compendium on any topic"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, AskUserQuestion, Task, WebSearch, WebFetch, Agent
triggers:
  - research-deep
  - chapterwise:research-deep
  - research:deep
  - chapterwise:research:deep
argument-hint: "<topic or instruction>"
---

# ChapterWise Deep Research

## Overview

This is the deep variant of `/research`. It produces a **multi-document compendium** — an overview file plus individual sub-files for each major entity, concept, or subtopic. Use this for broad topics that deserve thorough, structured coverage.

Read and follow `${CLAUDE_PLUGIN_ROOT}/references/principles.md` — especially **LLM Judgment, User Override**.

Read and follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all progress messages.

---

## How This Differs from `/research`

| Aspect | `/research` | `/research:deep` |
|--------|-------------|-------------------|
| Default depth | `standard` — agent judges | `deep` — always comprehensive |
| Default structure | Single file or folder with overview | Folder with overview + individual sub-files |
| Scope | Focused reference | Exhaustive compendium |
| Web search | Agent decides | Strongly favored — comprehensive sourcing |

Everything else — preferences, credits, manuscript-awareness, format — works identically to `/research`.

---

## Execution

Follow the exact same command flow as `${CLAUDE_PLUGIN_ROOT}/commands/research.md`, with these overrides:

1. **Depth is locked to `deep`** — When loading settings in Step 2, ignore `research.depth`. Depth is set by the command variant (Preference Cascade, priority 3) and cannot be overridden by saved preferences. Only prompt language can override (e.g., "just a quick overview").

2. **Structure defaults to multi-file** — create a folder with:
   - `overview.codex.md` (or `.research.json`) — High-level synthesis, table of contents, key themes
   - Individual files per major entity or subtopic — one file per god, per technique, per historical figure, etc.
   - The agent judges how to subdivide based on the topic's natural structure

3. **Web search is strongly favored** — for deep research, default to web-augmented unless the user explicitly says "no web" or the topic is extremely well-known. If web search returns nothing, fall back to LLM knowledge and set `sources: llm-knowledge`.

4. **Progress messages reflect depth:**
   - `"Sourcing deep compendium: {topic}... mapping {N} subtopics."`
   - `"Distilling {subtopic}... {M} of {N}."`
   - `"Done. {N} research files saved to {path}."`

---

## Example Output Structure

`/research:deep all trickster gods across world mythologies`

```
research/trickster-gods/
├── overview.codex.md          # Synthesis: role of tricksters across cultures
├── loki.codex.md              # Norse trickster
├── anansi.codex.md            # West African/Caribbean trickster
├── coyote.codex.md            # Native American trickster
├── hermes.codex.md            # Greek trickster
├── maui.codex.md              # Polynesian trickster
├── eshu.codex.md              # Yoruba trickster
└── sun-wukong.codex.md        # Chinese trickster
```

Each sub-file follows the same Codex format (JSON or Markdown per user preference) with full credits.

The overview file cross-references all sub-files and synthesizes common patterns, cultural differences, and thematic threads.

---

## Natural Language Still Overrides

Even in deep mode, the user's prompt controls everything:

- "deep research trickster gods, but just a single file" → single file, deep content
- "deep research trickster gods, focus only on Norse and Greek" → only Loki and Hermes sub-files
- "deep research trickster gods, organize by cultural region" → region folders instead of per-deity files

The user's word is final. `/research:deep` sets the default depth, not a hard constraint.

---

## Deep Mode Edge Cases

| Situation | Response |
|-----------|----------|
| Topic doesn't naturally subdivide | Produce a single deep file with thorough content. Don't force artificial subdivision. |
| Web search returns nothing | Fall back to LLM knowledge. Set `sources: llm-knowledge`. Proceed with deep content from training data. |
| Very narrow topic (e.g., "deep research cyanide poisoning") | Produce a single comprehensive file with deep detail, not multiple files on sub-aspects unless the content warrants it. |
| User says "just a single file" | Obey. Deep content in one file. Prompt language overrides structure default. |
