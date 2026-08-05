#!/usr/bin/env python3
"""
Discovers and loads analysis modules from:
1. Built-in: ${CLAUDE_PLUGIN_ROOT}/modules/
2. User global: ~/.claude/analyze/modules/
3. Project: ./.chapterwise/analysis-modules/

Commands:
  list              List all available modules (sorted by category)
  get <name>        Get a specific module by name
  courses           Return course groupings (quick_taste, slow_roast, spice_rack, simmering)
  recommend         Genre-aware module selection (input: {"genre": "literary_fiction"})
"""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional


# Course groupings — hardcoded for simplicity
COURSES = {
    "quick_taste": {
        "name": "Quick taste",
        "description": "Fast overview — summary, characters, tags",
        "modules": ["summary", "characters", "tags"]
    },
    "slow_roast": {
        "name": "Slow roast",
        "description": "Deep structural analysis",
        "modules": ["three_act_structure", "story_beats", "story_pacing", "heros_journey"]
    },
    "spice_rack": {
        "name": "Spice rack",
        "description": "Writing craft modules",
        "modules": ["writing_style", "language_style", "rhythmic_cadence", "clarity_accessibility"]
    },
    "simmering": {
        "name": "Simmering",
        "description": "Depth and psychology",
        "modules": ["thematic_depth", "reader_emotions", "jungian_analysis", "character_relationships", "dream_symbolism", "immersion"]
    },
    "immersive": {
        "name": "Immersive",
        "description": "Experiential design — effects, rhythm, comfort",
        "modules": ["immersive_design", "immersion", "reader_emotions", "story_pacing"]
    }
}

# Genre-to-module mapping for genre-aware recommendations
GENRE_MODULE_MAP = {
    "literary_fiction": {
        "include": [
            "summary", "characters", "character_relationships", "three_act_structure",
            "story_beats", "story_pacing", "writing_style", "language_style",
            "thematic_depth", "reader_emotions", "immersion", "jungian_analysis",
            "dream_symbolism", "tags"
        ],
        "skip": ["comedy_analysis", "win_loss_wave", "four_weapons", "ai_detector"],
        "reason": "Literary fiction emphasizes character depth, thematic analysis, and writing craft."
    },
    "thriller": {
        "include": [
            "summary", "characters", "story_pacing", "plot_twists",
            "misdirection_surprise", "win_loss_wave", "story_beats",
            "heros_journey", "reader_emotions", "tags"
        ],
        "skip": ["jungian_analysis", "dream_symbolism", "rhythmic_cadence", "alchemical_symbolism"],
        "reason": "Thrillers prioritize pacing, tension, and plot momentum over psychological depth."
    },
    "fantasy": {
        "include": [
            "summary", "characters", "character_relationships", "psychogeography",
            "story_beats", "thematic_depth", "tags", "writing_style",
            "three_act_structure", "heros_journey"
        ],
        "skip": ["comedy_analysis"],
        "reason": "Fantasy benefits from world-building, character depth, and structural analysis."
    },
    "nonfiction": {
        "include": [
            "summary", "tags", "clarity_accessibility", "writing_style",
            "language_style", "thematic_depth", "critical_review"
        ],
        "skip": [
            "characters", "character_relationships", "three_act_structure",
            "story_beats", "heros_journey", "story_pacing", "plot_twists",
            "misdirection_surprise", "comedy_analysis", "four_weapons", "eight_stage"
        ],
        "reason": "Non-fiction prioritizes clarity, style, and accessibility over narrative structure."
    },
    "poetry": {
        "include": [
            "writing_style", "language_style", "rhythmic_cadence",
            "thematic_depth", "reader_emotions", "tags", "dream_symbolism"
        ],
        "skip": [
            "story_beats", "three_act_structure", "plot_holes", "story_pacing",
            "characters", "character_relationships", "comedy_analysis"
        ],
        "reason": "Poetry centers on rhythm, style, and thematic depth rather than plot structure."
    }
}


def parse_module_frontmatter(filepath: Path) -> Optional[Dict]:
    """Parse YAML frontmatter from a module markdown file."""
    content = filepath.read_text()
    if not content.startswith('---'):
        return None

    parts = content.split('---', 2)
    if len(parts) < 3:
        return None

    try:
        metadata = yaml.safe_load(parts[1])
        metadata['_filepath'] = str(filepath)
        metadata['_content'] = parts[2].strip()
        return metadata
    except yaml.YAMLError:
        return None


def discover_modules(plugin_root: str = None) -> Dict[str, Dict]:
    """
    Discover all available modules from all paths.
    Later paths override earlier (project > user > built-in).
    """
    modules = {}

    search_paths = []

    # 1. Built-in modules
    if plugin_root:
        search_paths.append(Path(plugin_root) / 'modules')

    # 2. User global modules
    user_modules = Path.home() / '.claude' / 'analyze' / 'modules'
    if user_modules.exists():
        search_paths.append(user_modules)

    # 3. Project modules
    project_modules = Path.cwd() / '.chapterwise' / 'analysis-modules'
    if project_modules.exists():
        search_paths.append(project_modules)

    for search_path in search_paths:
        if not search_path.exists():
            continue
        for md_file in search_path.glob('*.md'):
            if md_file.name.startswith('_'):
                continue  # Skip partials like _output-format.md

            metadata = parse_module_frontmatter(md_file)
            if metadata and 'name' in metadata:
                modules[metadata['name']] = metadata

    return modules


def list_modules(plugin_root: str = None) -> List[Dict]:
    """Return list of modules sorted by category then name."""
    modules = discover_modules(plugin_root)
    module_list = list(modules.values())

    return sorted(module_list, key=lambda m: (
        m.get('category', 'Other'),
        m.get('name', '')
    ))


def get_module(name: str, plugin_root: str = None) -> Optional[Dict]:
    """Get a specific module by name."""
    modules = discover_modules(plugin_root)
    return modules.get(name)


def get_courses() -> Dict:
    """Return all course groupings."""
    return {"courses": COURSES}


def recommend_modules(genre: str) -> Dict:
    """
    Return genre-aware module recommendations.
    Input: genre string (e.g. 'literary_fiction', 'thriller', 'fantasy', 'nonfiction', 'poetry')
    Output: {"recommended": [...], "skipped": [...], "reason": "..."}
    """
    mapping = GENRE_MODULE_MAP.get(genre)
    if not mapping:
        # Unknown genre — return all course modules as a safe default
        all_modules = []
        for course in COURSES.values():
            all_modules.extend(course["modules"])
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for m in all_modules:
            if m not in seen:
                seen.add(m)
                deduped.append(m)
        return {
            "recommended": deduped,
            "skipped": [],
            "reason": f"Unknown genre '{genre}' — returning standard module set."
        }

    return {
        "recommended": mapping["include"],
        "skipped": mapping["skip"],
        "reason": mapping["reason"]
    }


if __name__ == '__main__':
    import sys
    import json

    plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '.')

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'list':
            modules = list_modules(plugin_root)
            print(json.dumps(modules, indent=2))
        elif cmd == 'get' and len(sys.argv) > 2:
            module = get_module(sys.argv[2], plugin_root)
            if module:
                print(json.dumps(module, indent=2))
            else:
                print(f"Module '{sys.argv[2]}' not found", file=sys.stderr)
                sys.exit(1)
        elif cmd == 'courses':
            # Input via stdin (ignored — no input needed, but consume it)
            try:
                sys.stdin.read()
            except Exception:
                pass
            print(json.dumps(get_courses(), indent=2))
        elif cmd == 'recommend':
            # Input: {"genre": "literary_fiction"}
            try:
                data = json.load(sys.stdin)
            except (json.JSONDecodeError, EOFError):
                data = {}
            genre = data.get('genre', '')
            print(json.dumps(recommend_modules(genre), indent=2))
        else:
            print("Usage: module_loader.py list | get <name> | courses | recommend")
    else:
        print("Usage: module_loader.py list | get <name> | courses | recommend")
