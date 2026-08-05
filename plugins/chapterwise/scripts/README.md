# Scripts Interface Guide

This directory contains utility scripts for the ChapterWise plugin ecosystem. Each script follows one of three interface patterns: stdin/stdout JSON, command-line arguments (argparse), or library-only (imported by other scripts).

## stdin → stdout JSON

These scripts accept JSON on stdin and return JSON on stdout. All output uses 2-space indentation for readability. These are ideal for integration with Claude agents and web services.

### Data Processing Scripts

**`recipe_manager.py`** — Create, load, and manage recipe folders
```bash
echo '{"project_path": "./my-novel", "type": "import"}' | python3 recipe_manager.py create
echo '{"project_path": "./my-novel"}' | python3 recipe_manager.py list
echo '{"recipe_path": ".chapterwise/import-recipe"}' | python3 recipe_manager.py validate
echo '{"recipe_path": ".chapterwise/import-recipe", "updates": {"manuscript": {"title": "New"}}}' | python3 recipe_manager.py update
echo '{"project_path": "./my-novel", "type": "import"}' | python3 recipe_manager.py load
```
Commands: `create`, `load`, `list`, `validate`, `update`

**`recipe_validator.py`** — Validate recipe.yaml files and cross-recipe consistency
```bash
echo '{"recipe_path": ".chapterwise/import-recipe/"}' | python3 recipe_validator.py
```
Output: `{"valid": true, "issues": [], "cross_recipe_issues": []}`

**`codex_validator.py`** — Validate and auto-fix .codex.yaml and .md files
```bash
echo '{"path": "./my-novel/", "fix": true}' | python3 codex_validator.py
```
Output: `{"valid": true, "issues": [], "fixes_applied": []}`

Validation includes:
- All .md files have valid YAML frontmatter
- All .codex.yaml files parse correctly
- UUIDs are present and unique
- index.codex.yaml references exist
- No orphan files

**`format_detector.py`** — Detect manuscript source format from file
```bash
echo '{"path": "/path/to/file.pdf"}' | python3 format_detector.py
```
Output: `{"format": "pdf", "confidence": 0.99, "details": {...}}`

Supported formats: pdf, docx, doc, scrivener, ulysses, markdown, plaintext, html, rtf, epub, final_draft, fountain

**`run_recipe.py`** — Execute a saved ChapterWise import recipe
```bash
echo '{"recipe_path": ".chapterwise/import-recipe", "source_path": "new-draft.pdf"}' | python3 run_recipe.py
```
Output: `{"success": true, "output_dir": "./my-novel/", "message": "..."}`

### Codex Format Tools

**`convert_format.py`** — Convert between Codex formats (JSON ↔ YAML ↔ Markdown)
```bash
echo '{"input_file": "story.codex.yaml", "format": "markdown"}' | python3 convert_format.py
```

**`implode_codex.py`** — Merge included files back into parent Codex
```bash
echo '{"input_file": "story.codex.yaml", "delete_sources": false}' | python3 implode_codex.py
```

**`explode_codex.py`** — Extract Codex children into separate files
```bash
echo '{"input_file": "story.codex.yaml", "types": ["character", "location"]}' | python3 explode_codex.py
```

### Analysis & Metadata

**`analysis_writer.py`** — Write analysis results to .analysis.json files
```bash
echo '{"source_path": "chapter.codex.yaml", "analysis": {...}, "modules": ["summary"]}' | python3 analysis_writer.py
```
Output: `{"analysis_file": "chapter.analysis.json", "created": true}`

Uses Codex V1.3 format with children arrays and attributes.

**`staleness_checker.py`** — Compute sourceHash and detect staleness
```bash
echo '{"source_path": "chapter.codex.yaml"}' | python3 staleness_checker.py
```
Output: `{"source_hash": "abc123...", "analysis_file": "chapter.analysis.json", "is_stale": false}`

**`tag_generator.py`** — Auto-generate tags from Codex body fields
```bash
echo '{"file": "story.codex.yaml", "count": 20}' | python3 tag_generator.py
```
Output: `{"tags": ["character", "mystery", ...], "method": "tfidf"}`

**`word_count.py`** — Update word_count attributes in Codex files
```bash
echo '{"file": "story.codex.yaml", "recursive": true}' | python3 word_count.py
```
Output: `{"word_counts": {"root": 50000, "chapter-1": 8000, ...}}`

### Integration Scripts

**`module_loader.py`** — Discover and load analysis modules
```bash
python3 module_loader.py list
echo '{}' | python3 module_loader.py courses
echo '{"genre": "literary_fiction"}' | python3 module_loader.py recommend
```
Commands: `list`, `get <name>`, `courses`, `recommend`

**`location_finder.py`** — Index Codex files and extract location hints
```bash
echo '{"path": "./manuscript/", "action": "scan"}' | python3 location_finder.py
echo '{"file": "chapter.codex.yaml", "action": "index"}' | python3 location_finder.py
```

**`note_parser.py`** — Parse notes and separate instructions from content
```bash
echo '{"text": "This goes after the hyperborean incursion.\n\nNew content.", "batch": false}' | python3 note_parser.py
```
Output: `{"instruction": "after the hyperborean incursion", "content": "New content"}`

**`auto_fixer.py`** — Auto-fix Codex V1.3 integrity issues
```bash
echo '{"file": "story.codex.yaml", "dry_run": false}' | python3 auto_fixer.py
```
Output: `{"fixed": true, "fixes": [...]}`

---

## CLI (argparse)

These scripts use standard command-line arguments and are designed for batch operations, scripting, and local file processing.

### Codex & Format Tools

**`explode_codex.py`** — Extract Codex children into separate files
```bash
python3 explode_codex.py story.codex.yaml --types character,location
python3 explode_codex.py story.codex.yaml --types character --dry-run
python3 explode_codex.py story.codex.yaml --types character --output-pattern "./nodes/{type}/{name}.codex.yaml"
```
Options: `--types`, `--output-pattern`, `--dry-run`, `--no-auto-fix`

**`implode_codex.py`** — Merge included files back into parent Codex
```bash
python3 implode_codex.py story.codex.yaml
python3 implode_codex.py story.codex.yaml --delete-sources
python3 implode_codex.py story.codex.yaml --dry-run --recursive
```
Options: `--delete-sources`, `--dry-run`, `--recursive`, `--delete-empty-folders`

**`index_generator.py`** — Generate index.codex.yaml files by scanning directory
```bash
python3 index_generator.py .
python3 index_generator.py /path/to/project --dry-run
```
Options: `--dry-run`, `--include-md`, `-v`

### Integrity & Metadata

**`auto_fixer.py`** — Auto-fix Codex V1.3 integrity issues
```bash
python3 auto_fixer.py /path/to/file.codex.yaml
python3 auto_fixer.py /path/to/directory --recursive
python3 auto_fixer.py /path/to/file.codex.yaml --dry-run
```
Options: `--recursive`, `--dry-run`, `--verbose`

**`lite_helper.py`** — Validate and fix Markdown YAML frontmatter (Codex Lite)
```bash
python3 lite_helper.py document.md
python3 lite_helper.py /path/to/docs --recursive
python3 lite_helper.py document.md --init  # Add frontmatter to bare markdown
```
Options: `--recursive`, `--dry-run`, `--init`

**`tag_generator.py`** — Auto-generate tags from content
```bash
python3 tag_generator.py story.codex.yaml
python3 tag_generator.py story.codex.yaml --count 15
python3 tag_generator.py story.codex.yaml --min-count 5 --dry-run
```
Options: `--count`, `--min-count`, `--dry-run`

**`word_count.py`** — Update word_count attributes
```bash
python3 word_count.py story.codex.yaml
python3 word_count.py /path/to/codex --recursive
python3 word_count.py story.codex.yaml --follow-includes
```
Options: `--recursive`, `--follow-includes`

### Scrivener Import Tools

**`scrivener_import.py`** — Convert Scrivener projects to Codex formats (main orchestrator)
```bash
python3 scrivener_import.py /path/to/Project.scriv
python3 scrivener_import.py /path/to/Project.scriv --format markdown --output ./output
python3 scrivener_import.py /path/to/Project.scriv --dry-run --verbose
```
Options: `--format` (markdown, yaml, json), `--output`, `--dry-run`, `--verbose`, `--quiet`

**`scrivener_parser.py`** — Parse Scrivener .scrivx XML structure
```bash
python3 scrivener_parser.py /path/to/Project.scriv
```

**`rtf_converter.py`** — Convert RTF to Markdown/HTML
```bash
python3 rtf_converter.py input.rtf --output output.md
python3 rtf_converter.py input.rtf --method pandoc
```
Methods: `striprtf` (default), `pandoc`, `raw`

**`scrivener_file_writer.py`** — Write Scrivener content to disk
```bash
python3 scrivener_file_writer.py --format markdown --output ./output
```
Formats: markdown (Codex Lite), yaml (.codex.yaml), json (.codex.json)

### Utility Scripts

**`location_finder.py`** — Index Codex files and extract location hints
```bash
python3 location_finder.py scan . --no-recursive
python3 location_finder.py scan /path/to/project
python3 location_finder.py index chapter1.codex.yaml
python3 location_finder.py index story.codex.yaml --no-follow-includes
python3 location_finder.py deep ./manuscript/  # Follow all includes
python3 location_finder.py hints "after the hyperborean incursion"
```
Subcommands: `scan`, `index`, `deep`, `hints`

**`insert_engine.py`** — File insertion with format detection and backup
```bash
python3 insert_engine.py insert /path/to/file.txt --line 42
python3 insert_engine.py find-location /path/to/file.txt --hint "after chapter 5"
```

**`convert_format.py`** — Convert between Codex formats
```bash
python3 convert_format.py document.md --to-codex
python3 convert_format.py story.codex.yaml --to-markdown
python3 convert_format.py document.md --to-codex -o output.codex.yaml
```
Options: `--to-codex`, `--to-markdown`, `-o/--output`

---

## Library-Only (Imported)

These scripts provide utility functions and are imported by other scripts. They have no CLI entry point but can be used as Python modules.

**`schema_validator.py`** — JSON Schema validation for Codex V1.3 and analysis files
```python
from schema_validator import validate_codex, validate_analysis
is_valid, errors = validate_codex(data)
```

**`note_parser.py`** — Parse notes and separate instructions from content
```python
from note_parser import NoteParser
parser = NoteParser()
notes = parser.parse_batch(text)
```

**`insert_engine.py`** — Core insertion engine with format detection
```python
from insert_engine import InsertEngine
engine = InsertEngine(project_path)
result = engine.insert(file_path, content, line_number)
```

---

## Common Patterns

### Error Handling
JSON output scripts include error details:
```json
{"success": false, "error": "File not found", "details": "..."}
```

CLI scripts exit with code 1 on error and log to stderr.

### Dry Run Mode
Scripts supporting `--dry-run` or `dry_run` show what would be changed without making modifications.

### Recursive Processing
Scripts supporting `--recursive` traverse directories and process all matching files.

### Follow Includes
Scripts supporting `--follow-includes` resolve `include:` directives and process referenced files.

### Validation Levels
Most validators support multiple checks:
- **Basic**: File parsing and structure
- **Strict**: UUIDs, references, word counts
- **Auto-fix**: Attempt to repair issues

---

## Integration Examples

### With Claude Agents
```python
import subprocess
import json

data = {"path": "./my-novel/", "fix": True}
result = subprocess.run(
    ["python3", "codex_validator.py"],
    input=json.dumps(data),
    capture_output=True,
    text=True
)
output = json.loads(result.stdout)
```

### Chained Operations
```bash
# Extract characters, generate tags, count words
python3 explode_codex.py story.codex.yaml --types character
python3 tag_generator.py story/characters/*.codex.yaml
python3 word_count.py story --recursive
```

### Batch Processing
```bash
# Fix and validate all codex files
for file in **/*.codex.yaml; do
  echo "{\"file\": \"$file\", \"dry_run\": false}" | python3 auto_fixer.py
done
```
