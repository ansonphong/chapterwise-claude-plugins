---
description: "Build a static HTML reader for your project"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, AskUserQuestion, Task
triggers:
  - reader
  - build reader
  - codex reader
  - reading experience
  - chapterwise:reader
argument-hint: "[project-path] [--template name]"
---

# ChapterWise Reader

Build a self-contained reading experience from any Codex project. Output is static HTML, CSS, and JavaScript — open in any browser, host anywhere. No server required, no ChapterWise account needed.

---

## Overview

The reader command scans a Codex project's `index.codex.yaml`, asks one or two questions about style and template, then builds a complete HTML reader with navigation, search, theme toggle, and optional atlas components. The result lives in a `reader/` directory next to your project.

For atlas projects (projects where the index has `type: atlas` or an `atlases` array), the reader generates additional components: character cards, a timeline view, and theme sections — all linked to the chapters where they appear.

---

## Command Routing

### `/reader` (no arguments) — Interactive Builder

1. Find the project root (search for `index.codex.yaml` starting from the current directory)
2. Detect content type:
   - If `type: atlas` in index → activate atlas components
   - If `atlases` array exists in index → offer to include atlas in reader
   - Otherwise → standard manuscript reader
3. Ask which template (Minimal or Academic) or offer Custom
4. Build the reader
5. Save the build configuration silently

### `/reader --template minimal`

Skip template selection. Use the minimal reader template directly. Proceed to Step 1 (Scan).

### `/reader --template academic`

Skip template selection. Use the academic reader template directly. Proceed to Step 1 (Scan).

### `/reader --atlas`

Force atlas rendering even if the project is not flagged as an atlas. Useful when the project contains atlas-structured content but the index does not have `type: atlas`.

### `/reader [project-path]`

Specify a project directory explicitly. Use this when not running from inside a Codex project:

```
/reader ~/novels/the-long-way-home
```

---

## Settings

`.chapterwise/settings.json` holds what this project builds by default. Read it before
asking anything:

```bash
echo '{"path": ".", "section": "reader"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/settings.py resolve
```

```json
{
  "reader": {
    "output_dir": "reader",
    "template": "minimal",
    "theme": "light"
  }
}
```

| Key | Default | Meaning |
|---|---|---|
| `reader.template` | `minimal` | `minimal`, `academic`, or `custom` |
| `reader.theme` | `light` | Which theme the reader opens in — the toggle still works either way |
| `reader.output_dir` | `reader` | Folder, relative to the **project root** |

`sources` marks each value `settings`, `recipe`, or `default`. **Never ask about a value
that came from `settings` or `recipe`** — use it and say so in one clause. Ask only about
`default` values. `--template` beats both for that run and is never written back.

`output_dir` resolves the way codex `include` paths do: `reader` and `/reader` are the
project root, `~/…` is a literal path.

After the first successful build, if nothing was configured yet, offer once:

> "Save these as this project's defaults? Academic template, dark theme."

```bash
echo '{"path": ".", "updates": {"reader": {"template": "academic", "theme": "dark", "output_dir": "reader"}}}' \
  | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/settings.py set
```

Settings are intent, and are committed. `.chapterwise/reader-recipe/` stays what it has
always been — the record of the last build, including any `custom-style.css` being
iterated on.

---

## Step 0: Read settings

Run `settings.py resolve` above. A configured `template` means Step 2 is skipped.

---

## Step 1: Scan Project

Read the project structure to understand what will be built.

**Action:** Locate and read `index.codex.yaml`.

Use the Glob tool with pattern `**/index.codex.yaml` to locate the project index.

If no `index.codex.yaml` is found:

> "I can't find a codex project here. Import your manuscript first with /import."

Stop. Do not proceed.

**Read the index file** and extract:
- Project title (`title` field)
- Top-level children (parts, chapters, sections)
- Total file count
- Any `atlases` array or `type: atlas` flag
- Project summary if present

**Count content files:**

Use the Glob tool to find all content files:
- Pattern: `**/*.md`
- Pattern: `**/*.codex.yaml`
Exclude `index.codex.yaml` itself from the results.

**Report progress:**

> "Scanning project... {N} files, {M} parts."

For atlas projects:

> "Scanning project... atlas with {N} sections, {M} entries."

---

## Step 2: Choose Template

**Skip this step entirely if `reader.template` came from settings or a recipe** — the
project has already chosen. Say so in one clause and continue:

> "Building with the academic template, per your settings."

Otherwise present template options and gather the writer's preference.

**Use AskUserQuestion:**

> "Which reader style?"

Options:
- **Minimal** — Clean, modern sans-serif. Sidebar navigation, light/dark toggle, search. Good for novels, short story collections, any prose.
- **Academic** — Serif typography, wider layout, footnote support, annotation margin. Good for essays, research, academic writing, textbooks.
- **Custom** — Describe what you want. The agent generates CSS and layout from your description.

**If Minimal or Academic is chosen:** Proceed to Step 3 using the chosen template from `${CLAUDE_PLUGIN_ROOT}/templates/`.

**If Custom is chosen:**

Use AskUserQuestion:

> "Describe the look you want — fonts, colors, layout, mood. For example: 'dark background, large serif type, no sidebar, centered text' or 'bold headers, magazine-style two columns, image support'."

The agent:
1. Reads `${CLAUDE_PLUGIN_ROOT}/templates/minimal-reader/` as a reference base
2. Generates custom `style.css` from the description
3. Adapts `index.html` layout if needed (e.g., sidebar right, no sidebar, two-column)
4. Saves the custom CSS in `.chapterwise/reader-recipe/custom-style.css` for iteration
5. Uses the same `reader.js` from minimal unless layout changes require new JS

---

## Step 3: Configure Reader

Determine configuration values from the project before building.

**Extract from index.codex.yaml:**
- `title` → used for `<title>`, sidebar header, and `{{PROJECT_TITLE}}` placeholder
- `summary` → used for meta description
- `attributes.author` → used in HTML meta tags if present
- `children` → the full navigation tree

**Build the manifest data structure:**

```json
{
  "title": "The Long Way Home",
  "author": "Jane Smith",
  "chapters": [
    {
      "id": "chapter-01-the-awakening",
      "title": "The Awakening",
      "path": "part-1-departure/chapter-01-the-awakening.md",
      "wordCount": 3200,
      "tags": ["opening", "protagonist-introduction"],
      "content": "..."
    }
  ],
  "structure": [
    {
      "title": "Part One: Departure",
      "children": ["chapter-01-the-awakening", "chapter-02-the-call"]
    }
  ]
}
```

**For atlas projects, also extract:**
- Character entries (name, role, traits, arc summary, chapter appearances)
- Timeline events (title, chapter reference, characters involved, act)
- Theme entries (name, description, chapter appearances, prominence)
- Location entries if present

**Build navigation:**
- Flat chapter list for sequential prev/next
- Nested tree for sidebar TOC (preserving parts/acts structure)
- Atlas section entries for atlas navigation

**Determine content embedding strategy:**
- Small projects (under 50 chapters): embed all content in `manifest.json`
- Large projects (50+ chapters): write per-chapter HTML files, reference by path in manifest

---

## Step 4: Build Reader

Copy the template and replace all placeholders with project data.

**Action 1:** Create output directory.

```bash
mkdir -p {project-root}/reader/
```

**Action 2:** Copy template files.

```bash
cp ${CLAUDE_PLUGIN_ROOT}/templates/{chosen-template}/*.html {project-root}/reader/
cp ${CLAUDE_PLUGIN_ROOT}/templates/{chosen-template}/*.css {project-root}/reader/
cp ${CLAUDE_PLUGIN_ROOT}/templates/{chosen-template}/*.js {project-root}/reader/
```

**Action 3:** Read all chapter files and render content.

For each chapter referenced in `index.codex.yaml`:

1. Read the file (`.md` or `.codex.yaml`)
2. Parse frontmatter from YAML block
3. Extract body content (Markdown text)
4. Note word count, tags, title from frontmatter

For `.md` files (Codex Lite):
```
Parse: YAML frontmatter between --- markers + Markdown body
```

For `.codex.yaml` files:
```
Parse: YAML document, body field contains Markdown
```

**Action 4:** Write `manifest.json` with all project data.

```bash
Write: {project-root}/reader/manifest.json
```

**Action 5:** Replace placeholders in `index.html`.

The template contains these placeholders:
- `{{PROJECT_TITLE}}` → replace with project title
- `{{MANIFEST}}` → replace with full manifest JSON (for embedded version)

**Report progress:**

> "Building reader shell... HTML, CSS, navigation."

**For atlas projects, also:**
- Generate character card HTML fragments
- Generate timeline entry HTML fragments
- Generate theme section HTML fragments
- Write to `reader/atlas-data.json`

---

## Step 5: Atlas-Specific Rendering

When the project contains atlas data, generate additional components.

### Character Cards

Each character entry becomes a card in the reader's Characters section.

**Card structure:**
- Name (heading)
- Role badge (protagonist, antagonist, supporting, minor)
- Trait tags (from `traits` or `tags` field in character entry)
- Arc summary (1-2 sentence description of character journey)
- Chapter count badge ("appears in 12 chapters")
- Expand button → shows full profile inline

**Linking:**
- Character names in the timeline link to the character's card
- Chapter references in character cards link to that chapter in the reader

### Timeline View

Events in chronological order with act/part dividers.

**Event structure:**
- Event title
- Act/part label (from parent container in atlas structure)
- Chapter reference (links to chapter in reader)
- Characters involved (comma-separated, linked to character cards)

**Display:**
- Vertical list, newest-to-oldest or chronological (writer's preference if atlas has ordering metadata)
- Dividers between acts when act structure is detectable

### Theme Section

List of themes with chapter cross-references.

**Theme entry structure:**
- Theme name (heading)
- Prominence indicator (primary, secondary, minor — from `prominence` field or inferred from chapter count)
- Description paragraph
- Chapter list ("appears in chapters 1, 3, 7, 12, 18")
- Evolution note if present in atlas data

### Cross-Reference Links

All cross-references use anchor IDs:
- Character cards: `id="char-{slug}"` — linked as `#char-{slug}`
- Timeline events: `id="event-{slug}"` — linked as `#event-{slug}`
- Chapter content: `id="chapter-{slug}"` — linked as `#chapter-{slug}`

**Wiring progress:**

> "Wiring interactivity... search, theme toggle."

---

## Step 6: Validate Reader Output

Check the built reader for correctness before reporting success.

**Validation checks (run all):**

1. **Structure check:** `{project-root}/reader/index.html` exists and contains `<!DOCTYPE html>`, a `<head>` block, a `<body>` block.

2. **Asset check:** All CSS and JS files referenced in `index.html` exist on disk.
   - Check `<link href="...">` paths
   - Check `<script src="...">` paths

3. **TOC match:** The chapter count in `manifest.json` matches the number of content files referenced in `index.codex.yaml`. Titles must match exactly.

4. **Atlas completeness:** If atlas rendering was activated, verify that character cards, timeline, and theme sections are present in `index.html` or in the manifest.

5. **Internal links:** No `href="#chapter-X"` that lacks a matching `id="chapter-X"` in the output.

**Run recipe validator:**

```bash
echo '{"recipe_path": ".chapterwise/reader-recipe/"}' | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recipe_validator.py
```

**Auto-fix behavior:**

- Broken relative asset paths → correct based on output directory structure
- Missing alt text on images → add `alt=""` as minimum
- Broken internal anchor links → rebuild from manifest data

**If issues are fixed automatically:**

> "Fixed {N} broken links in the reader."

**If issues cannot be fixed:**

> "The reader references {N} chapters that don't exist in the project — check your index.codex.yaml."

Stop. Report the specific missing files. Do not report success.

**If everything is clean:** Say nothing. Proceed to Step 7.

---

## Step 7: Save Build Configuration and Output

Write the output and save the build configuration for future iterations.

**Action 1:** If content is embedded, the `index.html` already contains everything. Report the final output tree.

**Action 2:** Save the build configuration (internal, no user-facing message).

Write `.chapterwise/reader-recipe/recipe.yaml`:

```yaml
version: "1.0"
created: "{ISO timestamp}"

project: "{project title}"
project_path: "{absolute path to project root}"
reader_type: "single_page"  # single_page, multi_page

design:
  template: "minimal"  # minimal, academic, custom
  theme: "light"       # light, dark

features:
  - tree_navigation
  - prev_next_navigation
  - full_text_search
  - theme_toggle
  - keyboard_navigation

atlas:
  enabled: false  # true if atlas rendering was activated
  sections: []    # ["characters", "timeline", "themes"] if enabled

output:
  directory: "./reader/"
  entry_point: "index.html"
  manifest: "./reader/manifest.json"
  chapter_count: 0
  word_count: 0
```

**Action 3:** Report success.

> "Done. Open reader/index.html to preview."

Show the output file tree:

```
reader/
├── index.html
├── style.css
├── reader.js
└── manifest.json
```

For atlas readers, add atlas files to the tree.

For large projects with per-chapter files:

```
reader/
├── index.html
├── style.css
├── reader.js
├── manifest.json
└── chapters/
    ├── chapter-01-the-awakening.html
    ├── chapter-02-the-call.html
    └── ...
```

**Suggest next steps:**

- Open `reader/index.html` in a browser to preview
- Iterate on the design: "Make the font larger," "Change the accent color," "Add a second theme"
- Host on GitHub Pages, Netlify, or any static host — just point to the `reader/` directory

---

## Custom Reader Design

When the writer chooses Custom in Step 2, the agent builds a bespoke reader.

**Process:**
1. Ask for design description (AskUserQuestion)
2. Read `${CLAUDE_PLUGIN_ROOT}/templates/minimal-reader/style.css` as reference
3. Generate a new `style.css` using `--codex-*` custom properties
4. Adapt `index.html` if layout changes are needed (right sidebar, no sidebar, centered layout)
5. Save custom files in `.chapterwise/reader-recipe/` for iteration

**Custom CSS uses the same `--codex-*` variable system:**

```css
:root {
  --codex-bg: /* writer's choice */;
  --codex-text: /* writer's choice */;
  --codex-accent: /* writer's choice */;
  --codex-font-body: /* writer's choice */;
  --codex-max-width: /* writer's choice */;
}
```

**Iteration:** When the writer says "darker background" or "bigger fonts," the agent edits `.chapterwise/reader-recipe/custom-style.css` and rebuilds only the CSS. The HTML and JS do not need to change for pure style iterations.

---

## Error Handling

**No index.codex.yaml found:**
> "I can't find a codex project here. Import your manuscript first with /import."

**Empty project (no content files):**
> "This project has no content files. Add chapters first."

**Missing chapter files (some referenced files don't exist):**
> "Warning: {N} chapter files referenced in the index are missing. Building reader from available files."

Proceed with the files that do exist. List the missing files.

**Template files missing:**
> "The {template} template files are missing. Check that the plugin is installed correctly."

Stop. Do not attempt to build without template files.

**Atlas data malformed:**
> "The atlas data in {file} didn't parse correctly. Building reader without atlas components."

Continue building the standard reader. Report which atlas file had issues.

---

## Language Rules

Read and follow `${CLAUDE_PLUGIN_ROOT}/references/principles.md` — especially **LLM Judgment, User Override**.
Follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all shared messaging rules.

**Reader-specific:** Minimal cooking language. The reader build is mostly functional.

**Reader-specific phases:**
- "Scanning project... {N} files, {M} parts." -- scan
- "Building reader shell... HTML, CSS, navigation." -- build
- "Wiring interactivity... search, theme toggle." -- wire
- "Done. Open reader/index.html to preview." -- completion
- "Assembling character cards... 14 characters." -- atlas components
- "Building timeline... 47 events." -- atlas components
- "Weaving theme data... 6 themes." -- atlas components

**Iteration responses are brief:** edit the CSS variable, say "Updated. Refresh index.html to see the change."
