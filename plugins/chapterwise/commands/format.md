---
description: "Format content as Chapterwise Codex"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
triggers:
  - codex format
  - chapterwise codex
  - codex yaml
  - write in codex
  - fix codex
  - auto-fix
argument-hint: "[file.codex.yaml]"
---

# Chapterwise Codex Format V1.3

Convert content to the Chapterwise Codex format - a perfectly recursive specification for **ANY structured content**. The format is infinitely flexible: invent any `type` you need. Common patterns are provided as templates, but you can create recipes, workouts, API docs, meeting notes, research papers, playlists, or literally anything else.

## When to Apply

Apply this command when the user asks to:
- Create or convert content to Chapterwise Codex format
- Fix formatting issues in a `.codex.yaml` or `.codex.json` file
- Structure content that benefits from hierarchy and metadata

## Output Format

**Default:** YAML with `.codex.yaml` extension
**Alternative:** JSON with `.codex.json` extension (if user requests)

## Required Structure

Every codex file MUST have:

```yaml
metadata:
  formatVersion: "1.3"
```

---

## CREATING ANY CONTENT TYPE

The Codex format is **infinitely flexible**. The templates below are common patterns, but you can create ANY type of content. The format adapts to whatever you need.

### Universal Structure (Works for Anything)

```yaml
metadata:
  formatVersion: "1.3"
  documentVersion: "1.0.0"
  author: "[Author]"
  created: "[ISO-8601]"

id: "[unique-id]"
type: "[your-custom-type]"  # ANY string: recipe, workout, meeting, research, playlist, etc.
title: "[Display Title]"
summary: "[One-line description]"
status: draft

body: |
  [Main content - supports full markdown]

attributes:
  - key: [any_key]
    name: "[Display Name]"
    value: [any value - string, number, boolean, array, object]
    dataType: [string|int|float|boolean|stringArray|date|url|markdown|object]

tags:
  - [relevant-tags]

children:
  - id: "[child-id]"
    type: "[child-type]"  # Can be different from parent
    name: "[Child Name]"
    # ...same structure recursively
```

### Custom Type Examples

**Not in templates? Just invent the type:**

```yaml
# A recipe
type: recipe
attributes:
  - key: prep_time
    value: 30
    dataType: int
  - key: ingredients
    value: ["flour", "sugar", "eggs"]
    dataType: stringArray

# A meeting note
type: meeting
attributes:
  - key: attendees
    value: ["Alice", "Bob"]
    dataType: stringArray
  - key: action_items
    value: 3
    dataType: int

# A research paper
type: research
attributes:
  - key: doi
    value: "10.1234/example"
    dataType: string
  - key: peer_reviewed
    value: true
    dataType: boolean

# A playlist
type: playlist
children:
  - type: track
    name: "Song Title"
    attributes:
      - key: artist
        value: "Artist Name"
      - key: duration_seconds
        value: 245
        dataType: int

# A workout routine
type: workout
children:
  - type: exercise
    name: "Squats"
    attributes:
      - key: sets
        value: 3
        dataType: int
      - key: reps
        value: 12
        dataType: int

# An API endpoint
type: endpoint
attributes:
  - key: method
    value: "POST"
  - key: path
    value: "/api/v1/users"
  - key: auth_required
    value: true
    dataType: boolean
```

### Guidelines for Custom Types

1. **Type names:** Use lowercase with hyphens (`meeting-notes`, `api-endpoint`, `character-sheet`)
2. **Be semantic:** Name types by what they ARE, not what they contain
3. **Attributes for structured data:** Anything with a specific value goes in attributes
4. **Body for prose:** Free-form text, descriptions, notes
5. **Children for hierarchy:** Sub-items, sections, steps, components
6. **Tags for discovery:** Cross-cutting categories, searchable labels

### When to Use What

| Content Style | Use |
|--------------|-----|
| Key-value data | `attributes` array |
| Long-form text | `body` field (markdown) |
| Structured sections | `children` array with `type: section` |
| Sub-items of same kind | `children` with same type as parent |
| Mixed sub-items | `children` with different types |
| Side-by-side sections | `content` array with `width` |
| Diagrams and data tables | `content` array with `type: diagram` / `type: spreadsheet` |
| Links to other files | `include: "./path/file.codex.yaml"` |
| External references | `external_url` or `relations` array |

---

## THE CONTENT ARRAY (V1.3)

Where `body` is one continuous block of prose, `content` is a list of laid-out
sections. Use it when a node has several distinct parts that should sit next to
each other — a logline beside its themes, a scene's visuals beside its audio, a
chapter's summary beside the diagram of its structure.

```yaml
content:
  - key: visual
    name: "Visual"
    width: 1/2
    value: |
      Wide shot. The valley at first light.

  - key: audio
    name: "Audio"
    width: 1/2
    value: |
      Ambient wind, no score until the reveal.

  - key: structure
    name: "Act Structure"
    type: diagram
    width: 1/1
    include: ./diagrams/three-act.mermaid

  - key: budget
    name: "Word Budget"
    type: spreadsheet
    width: 1/1
    include: ./data/chapter-budget.csv
```

### Content Item Fields

| Field | Required | Purpose |
|-------|:--------:|---------|
| `key` | yes | Machine-readable identifier, lowercase-with-hyphens |
| `value` | yes* | The content itself. Use `\|` for multiline. |
| `name` | no | Display label shown above the section |
| `type` | no | Content category (default `text`) |
| `width` | no | Layout width (default `1/2`) |
| `id` | no | Unique identifier |
| `include` | no | Path to an external file supplying the content |

\* Either `value` or `include` — `include` replaces `value` when the content
lives in its own file.

### Content Types

| Type | Renders as |
|------|-----------|
| `text` | Markdown prose (default) |
| `blockquote` | Quoted / pulled-out material |
| `diagram` | Mermaid diagram — see `/chapterwise:diagram` |
| `spreadsheet` | Interactive data table — see `/chapterwise:spreadsheet` |

Custom types are permitted; unknown types fall back to text rendering.

### Width

Items flow left-to-right and wrap to a new row when the current one fills.
YAML order is preserved.

| Value | Behavior |
|-------|----------|
| `1/1` | Full width, gets its own row |
| `1/2` | Half width (default) |
| `1/3` | Third width |

Set `width: 1/1` for diagrams, spreadsheets, and anything with wide content.
Two `1/2` items sit side by side; three `1/3` items make a row of three.

### Include Resolution (V1.3)

`include:` is no longer limited to codex documents. Inside a content array it
also resolves:

| Extension | Becomes |
|-----------|---------|
| `.mermaid`, `.mmd` | A `diagram` section |
| `.csv` | A `spreadsheet` section |
| `.xlsx` | A `spreadsheet` section (converted to CSV) |
| `.spreadsheet.yaml` | A `spreadsheet` section with column config and formulas |

Path rules are unchanged: paths starting with `/` resolve from the Git project
root, `./` from the current file's directory.

---

## COMMON TEMPLATES (Reference Examples)

### 1. Venue / Location Database Entry

For planetariums, theaters, studios, or any venue with technical specs:

```yaml
metadata:
  formatVersion: "1.3"
  documentVersion: "1.0.0"
  author: "Studio Phong"
  created: "[ISO-8601]"
  updated: "[ISO-8601]"

id: "[venue-slug]"
type: venue
title: "[Display Name with Emoji]"
summary: "[One-line venue description]"
status: private

body: |
  [Extended description, history, unique features, and context.]

image: "/[Category]/[venue-slug]/[main-image].jpg"

images:
  - url: "/[Category]/[venue-slug]/exterior.jpg"
    caption: "Exterior view"
  - url: "/[Category]/[venue-slug]/dome.jpg"
    caption: "Interior dome"

attributes:
  - key: venue_type
    name: "Venue Type"
    value: "university_campus"  # or: science_center, private, municipal, corporate
    dataType: string
  - key: dome_diameter_m
    name: "Dome Diameter"
    value: 19.8
    dataType: float
  - key: seating_capacity
    name: "Seating Capacity"
    value: 206
    dataType: int
  - key: projection_system
    name: "Projection System"
    value: "Sky-Skan Definiti 8K"
    dataType: string
  - key: audio_system
    name: "Audio System"
    value: "7.1 Surround"
    dataType: string
  - key: rental_available
    name: "Available for Rental"
    value: true
    dataType: boolean
  - key: gps_coordinates
    name: "GPS"
    value: "40.0076, -105.2622"
    dataType: string

tags:
  - planetarium
  - north-america
  - 8k-projection
  - rental-available

external_url: "https://venue-website.com"
```

### 2. Character (Narrative)

```yaml
metadata:
  formatVersion: "1.3"
  documentVersion: "1.0.0"
  author: "[Author]"
  created: "[ISO-8601]"

id: "[uuid-v4]"
type: character
summary: "[One-line character description]"
status: draft
featured: true

body: |
  [Extended description, backstory, personality, arc overview]

image: "/Characters/[character-slug].jpg"

attributes:
  - key: age
    name: "Age"
    value: 25
    dataType: int
  - key: role
    name: "Role"
    value: "Protagonist"
    dataType: string
  - key: abilities
    name: "Abilities"
    value:
      - "Telepathy"
      - "Precognition"
    dataType: stringArray

relations:
  - targetId: "[related-character-uuid]"
    kind: "ally"
    strength: 0.8
    reciprocal: true

children:
  - id: "[arc-uuid]"
    type: arc
    name: "[Character Arc Name]"

tags:
  - character
  - protagonist
  - [story-tag]
```

---

## Node Types Reference

| Domain | Types |
|--------|-------|
| **Business** | `budget`, `budget_item`, `presentation`, `slide`, `organization`, `partner`, `asset_registry`, `asset`, `asset_category` |
| **Technical** | `technical-architecture`, `component`, `implementation_phase`, `pipeline`, `phase`, `step` |
| **Production** | `script`, `act`, `beat`, `scene`, `process`, `shot_category`, `shot` |
| **Content** | `book`, `chapter`, `article`, `section` |
| **Venues** | `venue`, `location`, `region` |
| **Narrative** | `universe`, `world`, `character`, `arc`, `faction`, `item` |
| **Organization** | `index`, `collection`, `case_study` |

## Common Attribute Data Types

`int`, `float`, `boolean`, `string`, `stringArray`, `date`, `url`, `markdown`, `object`

## Relation Kinds

- `parent` / `child`
- `partner` / `collaborator`
- `features` / `featured-in`
- `set-in` / `contains`
- `precedes` / `follows`
- `ally` / `enemy`
- `mentors` / `student-of`

## Key Rules

1. **Only `metadata.formatVersion` is required** - everything else optional
2. **Use pipe `|` for multiline strings** - preserves markdown formatting
3. **Perfect recursion** - any node can have children with same structure
4. **Include directives** - reference files with `include: "./path/file.codex.yaml"`, or in a content array a `.mermaid`, `.csv`, `.xlsx`, or `.spreadsheet.yaml` source
5. **Status doesn't inherit** - each node sets its own
6. **Paths starting with `/`** - relative to Git repository root
7. **Relative paths `./`** - resolved from current file's directory
8. **NEVER create `.index.codex.yaml` files** - they are system-generated by Chapterwise
9. **Older documents stay valid** - `1.0` through `1.3` all parse; never rewrite a document's `formatVersion` just to modernize it

## Workflow

1. **Ask** what type of content the user wants to create/convert
2. **Match or invent** - use a template if it fits, otherwise create a custom type
3. **Generate** properly formatted YAML with real UUIDs and timestamps
4. **Structure appropriately:**
   - Attributes for structured/typed data
   - Body for prose and markdown content
   - Content array for laid-out sections, diagrams, and data tables
   - Children for hierarchy and sub-items
5. **Apply tags** - for discoverability and organization
6. **Suggest children** - recommend logical sub-nodes if applicable
7. **Run auto-fixer** after substantial work (see below)

---

## Auto-Fixer (ALWAYS RUN AFTER ADDING ENTITIES)

**After adding ANY new entity/node to a codex file, ALWAYS run the auto-fixer:**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py <file.codex.yaml>
```

### When to Run Auto-Fixer

Run it after:
- Creating a new codex file
- Adding ANY new node/child (even one)
- Converting content to codex format
- Restructuring or moving nodes
- Any edit that creates new entities

### What It Fixes

| Issue | Fix Applied |
|-------|-------------|
| Missing `metadata` section | Adds `metadata.formatVersion: "1.3"` |
| Missing `documentVersion` | Adds `"1.0.0"` |
| Legacy fields (`packetType`, `codexId`, `version`) | Removes or migrates them |
| Missing node `id` | Generates UUID v4 |
| Invalid UUID format | Regenerates valid UUID |
| Duplicate IDs | Generates new unique IDs |
| Missing `type` on nodes | Adds `type: "node"` |
| Missing `name` on nodes | Adds `name: "Untitled"` |
| Invalid attribute structure | Fixes `key`/`value` format |
| Invalid relation structure | Fixes `targetId`/`type` format |
| Empty names | Replaces with "Untitled" |
| Long strings | Converts to YAML pipe (`|`) syntax |
| Timecode calculation | Auto-calculates from durations |
| Time pattern quoting | Ensures `"01:30"` not parsed as 90 |
| Malformed YAML/JSON | Attempts syntax recovery |

### Command-Line Options

```bash
# Fix a single file
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py /path/to/file.codex.yaml

# Fix all files in directory recursively
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py /path/to/directory --recursive

# Dry run (preview fixes without changing files)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py /path/to/file.codex.yaml --dry-run

# Regenerate ALL IDs (useful for duplicating content)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py /path/to/file.codex.yaml --re-id

# Verbose output
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py /path/to/file.codex.yaml --verbose

# Combine flags
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py /path/to/directory -r -d -v
```

### Quick Pattern

```
1. Write/edit codex content (add any new entity)
2. Save file
3. Run: python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_fixer.py <file>
4. Report fixes to user
```

**This is not optional.** Every new entity needs valid UUIDs and proper formatting.

## Remember

- **Templates are examples, not limits** - create any type you need
- **The format is recursive** - any node can contain any other node
- **Invent types freely** - `type: grocery-list` is just as valid as `type: character`
- **Mix and match** - a `project` can have children of type `task`, `note`, `reference`, `milestone`
- **Always run auto-fixer** - it catches issues you won't notice

---

## Error Handling

| Situation | Response |
|-----------|----------|
| File not found | "File not found: {path}" |
| Invalid YAML/JSON syntax | "Cannot parse {path} — check for syntax errors near line {N}." |
| Missing `metadata.formatVersion` | "No formatVersion found. Adding `metadata.formatVersion: 1.3`." |
| Write permission denied | "Cannot write to {path} — check file permissions." |
| Missing PyYAML dependency | "Missing PyYAML. Install with: `pip3 install pyyaml`" |

## Language Rules

Follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all shared rules.

| Phase | Verb | Example |
|-------|------|---------|
| Start | Scanning | "Scanning {file}..." |
| Processing | Seasoning | "Seasoning metadata... IDs, types, attributes." |
| Completion | Done | "Done. {file} formatted." |
