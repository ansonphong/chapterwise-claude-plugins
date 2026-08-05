# ChapterWise Core Principles

These principles apply to ALL ChapterWise commands. Read and follow them alongside `language-rules.md`.

---

## Principle 1: LLM Judgment, User Override

The agent makes intelligent, organic decisions about structure, depth, organization, and format — but always yields to explicit user preferences.

### Preference Cascade

Priority (later overrides earlier):

1. **Plugin defaults** — Sane out-of-the-box behavior hardcoded in the command definition
2. **`.chapterwise/settings.json`** — Persistent per-project settings, one section per command
3. **Command variant** — e.g., `/research` vs `/research:deep`
4. **Prompt language** — Always wins. Natural language in the user's prompt overrides everything.

### What This Means in Practice

- **File organization:** The agent chooses folder names, file structure, and nesting depth based on content scope — but if the user says "put it in my worldbuilding folder" or "one file per character", obey.
- **Output format:** The agent uses the saved preference or default — but if the user says "output this one as JSON", obey for this invocation without changing the saved preference.
- **Depth and scope:** The agent judges how deep to go based on topic breadth — but if the user says "make it massive" or "keep it brief", obey.
- **Web search:** The agent decides whether to search the web based on topic type — but if the user says "use web sources" or "no web", obey.
- **Structure:** The agent decides single-file vs multi-file based on topic — but if the user specifies structure ("one section per god", "flat list"), obey.

### When Settings Don't Exist Yet

If a command needs a value that isn't in `.chapterwise/settings.json`:

1. Apply a sensible default silently (Principle 2 — Clean Defaults)
2. **Offer once**, after the command completes, to save what was used
3. Never ask again — a value whose `sources` entry is `settings` is settled

### Override vs Mutate

- **Prompt override:** User says "output this one as JSON" → obey for this invocation, do NOT change the setting
- **Explicit change:** User says "always use JSON from now on" → write it with `settings.py set`

---

## Principle 2: Clean Defaults, Rich Options

Commands work with zero configuration. The first run should produce useful output without requiring the user to set preferences, choose options, or read documentation. But power users can customize deeply through preferences, flags, and natural language instructions.

---

## Principle 3: Data Over Flare

Every progress message, completion report, and status update includes real data — chapter counts, word counts, file counts, entity names. Never replace substance with decoration. See `language-rules.md` for the full messaging rules.

---

## Settings Storage: `.chapterwise/settings.json`

The single per-project configuration file for every ChapterWise command. One file, one
section per command, so a project has one place to look rather than one per command.

**Location:** `.chapterwise/settings.json` (in the user's project, not the plugin)

```json
{
  "version": 1,
  "analysis": { "report": true, "report_format": "codex", "report_dir": "analysis", "depth": "auto" },
  "atlas":    { "output_dir": "atlas", "sections": ["characters", "timeline", "themes",
                                                   "plot-structure", "locations", "relationships"] },
  "reader":   { "output_dir": "reader", "template": "minimal", "theme": "light" },
  "research": { "output_dir": ".chapterwise/research", "format": "codex-md", "depth": "standard" }
}
```

**Read and write it through `scripts/settings.py`,** never by hand-parsing:

```bash
echo '{"path": ".", "section": "reader"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/settings.py resolve
echo '{"path": ".", "updates": {"reader": {"theme": "dark"}}}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/settings.py set
```

`resolve` returns the section's values with paths already resolved, plus `found` and a
`sources` map marking each value `settings`, `recipe`, or `default`.

**Path values resolve the way codex `include` paths do** — bare and `./` are relative,
a leading `/` is the **project root**, `~` is a literal path. What "relative" means depends
on what the artifact belongs to: an analysis report sits beside the manuscript it
describes, while an atlas, a reader and research are per-project.

**Rules:**
- Read settings before asking anything
- A value from `settings` or `recipe` is never a question
- Write only what the user chose — never persist a one-off flag
- Offer to save once per project, not once per run
- Create the file only when the user says to save; reading never writes

**Settings are intent. `*-recipe` folders are history** — what a command last did, so work
is not redone. Keep them separate.
