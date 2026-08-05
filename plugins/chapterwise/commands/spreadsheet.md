---
description: "Create spreadsheets in Codex format"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
triggers:
  - spreadsheet
  - create spreadsheet
  - budget spreadsheet
  - data table
  - csv to codex
  - spreadsheet yaml
  - chapterwise:spreadsheet
argument-hint: "[description or file.csv]"
---

# Chapterwise Spreadsheet Content Type

Create interactive spreadsheets within Codex files. Spreadsheets support formulas, column configuration, and multiple data sources.

## When to Apply

Apply this command when the user asks to:
- Create a spreadsheet or data table in Codex format
- Convert CSV data into a Codex spreadsheet
- Build a budget, schedule, or inventory with formulas

## Output Formats

### 1. Inline CSV (Simplest)

For quick data tables embedded in a codex file:

```yaml
content:
  - key: budget
    name: "Production Budget"
    type: spreadsheet
    width: 1/1
    value: |
      Category,Budget,Spent,Remaining
      Talent,50000,12000,=B2-C2
      Equipment,25000,8000,=B3-C3
      Post,15000,0,=B4-C4
```

### 2. External CSV Reference

For existing CSV files:

```yaml
content:
  - key: data
    type: spreadsheet
    width: 1/1
    include: /data/myfile.csv
```

### 3. Full .spreadsheet.yaml (Advanced)

For column types, formatting, and calculated columns:

```yaml
# budget.spreadsheet.yaml
metadata:
  formatVersion: "1.0"
  generator: "claude-opus"
  created: "2025-01-25T12:00:00Z"

columns:
  - key: category
    title: "Category"
    type: text
    width: 150
    readOnly: true

  - key: budget
    title: "Budget"
    type: currency
    width: 120

  - key: spent
    title: "Spent"
    type: currency
    width: 120

  - key: remaining
    title: "Remaining"
    type: currency
    width: 120
    formula: "=B{row}-C{row}"

data:
  - category: "Talent"
    budget: 50000
    spent: 12000

  - category: "Equipment"
    budget: 25000
    spent: 8000

  - category: "Post-Production"
    budget: 15000
    spent: 0
```

Referenced in codex:

```yaml
content:
  - key: budget
    type: spreadsheet
    width: 1/1
    include: /data/budget.spreadsheet.yaml
```

## Width Options

| Width | Description |
|-------|-------------|
| `1/1` | Full width (recommended for spreadsheets) |
| `1/2` | Half width |
| `1/3` | Third width |

## Formula Syntax

Use **Excel-style cell references**:

| Formula | Description |
|---------|-------------|
| `=A1+B1` | Add two cells |
| `=B2-C2` | Subtract |
| `=SUM(B2:B10)` | Sum range |
| `=AVERAGE(C2:C10)` | Average |
| `=IF(A1>0,"Yes","No")` | Conditional |

**Important:** Formulas must use capital letters for cell refs.

## Column Types

| Type | Use For |
|------|---------|
| `text` | Labels, names |
| `numeric` | Plain numbers |
| `currency` | Money (shows $) |
| `percent` | Percentages (shows %) |
| `date` | Date picker |
| `dropdown` | Selection list |
| `checkbox` | Yes/No boolean |

## Workflow

1. **Ask** what data the user wants to organize
2. **Choose format**:
   - Quick/simple → inline CSV
   - External file → CSV with include
   - Full control → .spreadsheet.yaml
3. **Generate** with realistic sample data
4. **Add formulas** for calculated columns
5. **Set width** to `1/1` for most spreadsheets

## Examples

### Budget Spreadsheet
```
User: "Create a film production budget"

→ Generate .spreadsheet.yaml with:
- Categories: Talent, Equipment, Post, Marketing
- Columns: Budget, Spent, Remaining (formula)
- Currency formatting
```

### Schedule Spreadsheet
```
User: "Create a project schedule"

→ Generate inline CSV with:
- Phases: Pre-Production, Production, Post
- Columns: Start Date, End Date, Status
- Status as dropdown if using .spreadsheet.yaml
```

### Inventory Spreadsheet
```
User: "Create equipment inventory"

→ Generate with:
- Items with quantities
- Unit cost and total (formula: =B*C)
- Location, condition columns
```

## Remember

- **Always use `type: spreadsheet`** in content items
- **Prefer `width: 1/1`** for spreadsheets (full width)
- **Use Excel-style formulas** (`=A1+B1`, not `=[@column]`)
- **Capital letters in formulas** for cell references
- **Test formulas** with sample data to verify they work

---

## Error Handling

| Situation | Response |
|-----------|----------|
| CSV parse error | "Cannot parse CSV data — check for unescaped commas or mismatched quotes." |
| Invalid formula syntax | "Formula error in cell {cell}: {detail}." |
| Include file not found | "Spreadsheet file not found: {path}" |
| Write permission denied | "Cannot write to {path} — check file permissions." |

## Language Rules

Follow `${CLAUDE_PLUGIN_ROOT}/references/language-rules.md` for all shared rules.

| Phase | Verb | Example |
|-------|------|---------|
| Start | Scanning | "Scanning data requirements..." |
| Processing | Assembling | "Assembling spreadsheet... {N} rows, {M} columns." |
| Completion | Done | "Done. Spreadsheet added to {file}." |
