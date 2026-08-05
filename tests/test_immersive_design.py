#!/usr/bin/env python3
"""Tests for the immersive_design module, its references, and the comedy_analysis rename."""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'plugins' / 'chapterwise' / 'scripts'))
from module_loader import COURSES, discover_modules, get_courses, list_modules  # noqa: E402

PLUGIN_ROOT = Path(__file__).parent.parent / 'plugins' / 'chapterwise'
MODULES_DIR = PLUGIN_ROOT / 'modules'
REFERENCES_DIR = PLUGIN_ROOT / 'references'
EFFECTS_REF = REFERENCES_DIR / 'immersive-effects.md'
COMFORT_REF = REFERENCES_DIR / 'immersive-comfort.md'

# The 19 effect names that existed before this catalog was expanded. None may be
# silently dropped — writers may already be using them.
LEGACY_EFFECTS = [
    "Drop & Burst", "Cosmic Zoom", "Encroaching Giant", "Surround Reveal",
    "Simulated Motion", "Infinite Tunnel", "Starfield Drift", "Breaking the Dome",
    "Drop-In", "Full-Spectrum Fade", "Liquid Flow", "Surprise Sync",
    "Mirror Effect", "Collapse & Rebuild", "Time-Lapse", "Sensory Layering",
    "Hidden Geometry", "Inside the Body", "Portal",
]

ARC_POSITIONS = {"opening", "build", "climax", "lull", "close", "all"}
COMFORT_LEVELS = {"none", "low", "moderate", "high"}


def parse_frontmatter(path):
    """Minimal frontmatter parser matching module_loader's expectations."""
    text = path.read_text()
    match = re.match(r'^---\n(.*?)\n---', text, re.S)
    if not match:
        return {}
    out = {}
    for line in match.group(1).splitlines():
        if ':' in line and not line.startswith(' '):
            key, value = line.split(':', 1)
            out[key.strip()] = value.strip()
    return out


def parse_effects():
    """Return [{name, fields{}}] for every ### entry in the effects catalog."""
    text = EFFECTS_REF.read_text()
    # Effect entries are ### headings inside numbered ## category sections.
    body = text.split('## 1. Sensory Overwhelm', 1)[1]
    body = body.split('## Effects by arc position', 1)[0]
    effects = []
    for block in re.split(r'\n### ', body)[1:]:
        lines = block.splitlines()
        name = lines[0].strip()
        fields = {}
        for line in lines[1:]:
            m = re.match(r'\*\*(.+?):\*\*\s*(.*)', line.strip())
            if m:
                # Strip emphasis markers — high-risk entries bold their level.
                fields[m.group(1)] = m.group(2).replace('**', '').strip()
        effects.append({'name': name, 'fields': fields})
    return effects


def head(value):
    """Leading token of a field, before any ' — reason' suffix."""
    return value.split('—')[0].strip()


class TestModuleDiscovery:

    def test_immersive_design_is_discovered(self):
        modules = discover_modules(str(PLUGIN_ROOT))
        assert 'immersive_design' in modules

    def test_comedy_analysis_is_discovered(self):
        modules = discover_modules(str(PLUGIN_ROOT))
        assert 'comedy_analysis' in modules

    def test_gag_analysis_is_gone(self):
        modules = discover_modules(str(PLUGIN_ROOT))
        assert 'gag_analysis' not in modules

    def test_immersion_still_present_and_unchanged(self):
        """immersive_design must not have displaced the prose immersion module."""
        modules = discover_modules(str(PLUGIN_ROOT))
        assert 'immersion' in modules
        assert modules['immersion']['category'] == 'Quality Assessment'

    def test_all_modules_still_parse(self):
        """A malformed frontmatter would silently drop a module from discovery."""
        on_disk = {p.stem for p in MODULES_DIR.glob('*.md') if not p.stem.startswith('_')}
        discovered = set(discover_modules(str(PLUGIN_ROOT)).keys())
        assert on_disk == discovered


class TestFrontmatter:

    def test_immersive_design_frontmatter_complete(self):
        fm = parse_frontmatter(MODULES_DIR / 'immersive_design.md')
        for field in ('name', 'displayName', 'description', 'category', 'icon', 'applicableTypes'):
            assert field in fm, f"missing {field}"
        assert fm['name'] == 'immersive_design'

    def test_immersive_design_category_matches_core(self):
        """Must match chapterwise-core's category string exactly."""
        fm = parse_frontmatter(MODULES_DIR / 'immersive_design.md')
        assert fm['category'] == 'Immersive Design'

    def test_comedy_analysis_frontmatter_renamed(self):
        fm = parse_frontmatter(MODULES_DIR / 'comedy_analysis.md')
        assert fm['name'] == 'comedy_analysis'
        assert fm['displayName'] == 'Comedy Analysis'
        assert fm['category'] == 'Writing Craft'

    def test_immersive_design_declares_immersive_experience_type(self):
        """29 of 32 modules already declare this type; the module about immersive
        experiences is the last one that should omit it."""
        fm = parse_frontmatter(MODULES_DIR / 'immersive_design.md')
        assert 'immersive_experience' in fm['applicableTypes']

    def test_rename_preserved_comedy_applicable_types(self):
        """The rename should change identity, not reach."""
        fm = parse_frontmatter(MODULES_DIR / 'comedy_analysis.md')
        for expected in ('novel', 'short_story', 'screenplay',
                         'theatrical_play', 'immersive_experience'):
            assert expected in fm['applicableTypes'], f"lost type: {expected}"

    def test_module_names_are_snake_case(self):
        for path in MODULES_DIR.glob('*.md'):
            if path.stem.startswith('_'):
                continue
            name = parse_frontmatter(path).get('name', '')
            assert re.fullmatch(r'[a-z0-9_]+', name), f"{path.name}: {name!r}"


class TestCourses:

    def test_immersive_course_exists(self):
        assert 'immersive' in get_courses()['courses']

    def test_every_course_module_exists(self):
        """A course naming a missing module silently under-delivers."""
        available = set(discover_modules(str(PLUGIN_ROOT)).keys())
        for course_id, course in COURSES.items():
            missing = set(course['modules']) - available
            assert not missing, f"course {course_id!r} names missing modules: {missing}"

    def test_immersive_course_leads_with_immersive_design(self):
        assert get_courses()['courses']['immersive']['modules'][0] == 'immersive_design'


class TestEffectsCatalog:

    def test_catalog_exists(self):
        assert EFFECTS_REF.is_file()

    def test_catalog_has_substantial_entries(self):
        assert len(parse_effects()) >= 55

    def test_every_effect_has_all_seven_fields(self):
        required = {'Category', 'Mechanic', 'Targets', 'Arc position', 'Comfort risk',
                    'Caveats', 'Confidence'}
        for effect in parse_effects():
            missing = required - set(effect['fields'])
            assert not missing, f"{effect['name']}: missing {missing}"

    def test_arc_positions_use_closed_vocabulary(self):
        for effect in parse_effects():
            for token in effect['fields']['Arc position'].split('·'):
                assert token.strip() in ARC_POSITIONS, \
                    f"{effect['name']}: bad arc position {token.strip()!r}"

    def test_comfort_risk_uses_closed_vocabulary(self):
        for effect in parse_effects():
            level = head(effect['fields']['Comfort risk'])
            assert level in COMFORT_LEVELS, \
                f"{effect['name']}: bad comfort risk {level!r}"

    def test_confidence_uses_closed_vocabulary(self):
        """Three permitted forms, each optionally followed by ' — <source>'."""
        permitted = {'Documented', 'Observed practice', 'ChapterWise coinage'}
        for effect in parse_effects():
            value = effect['fields']['Confidence']
            assert head(value) in permitted, \
                f"{effect['name']}: bad confidence {value!r}"

    def test_documented_effects_cite_a_source(self):
        """'Documented' without a source is an unsupported claim."""
        for effect in parse_effects():
            value = effect['fields']['Confidence']
            if head(value) == 'Documented':
                assert '—' in value and len(value.split('—', 1)[1].strip()) > 5, \
                    f"{effect['name']}: Documented but no source given"

    def test_no_legacy_effect_was_dropped(self):
        catalog = EFFECTS_REF.read_text()
        missing = [name for name in LEGACY_EFFECTS if name not in catalog]
        assert not missing, f"legacy effect names lost: {missing}"

    def test_high_risk_effects_are_flagged(self):
        """The two most dangerous legacy effects had no comfort annotation before."""
        by_name = {e['name']: e['fields'] for e in parse_effects()}
        for name in ('Simulated Motion', 'Infinite Tunnel'):
            assert head(by_name[name]['Comfort risk']) == 'high', \
                f"{name} must be flagged high risk"

    def test_high_risk_effects_explain_why(self):
        """A bare 'high' with no reason is not actionable for an author."""
        for effect in parse_effects():
            risk = effect['fields']['Comfort risk']
            if head(risk) == 'high':
                assert '—' in risk, f"{effect['name']}: high risk with no reason given"


class TestComfortReference:

    def test_comfort_reference_exists(self):
        assert COMFORT_REF.is_file()

    def test_documents_key_thresholds(self):
        text = COMFORT_REF.read_text()
        for marker in ('20°/s', 'multi-axis', 'horizon', '1.2', 'ages 9'):
            assert marker in text, f"comfort reference missing {marker!r}"

    def test_marks_evidence_status(self):
        """Consensus must not be presented as measured fact."""
        text = COMFORT_REF.read_text()
        assert 'Measured' in text and 'Consensus' in text

    def test_warns_against_astm(self):
        assert 'ASTM' in COMFORT_REF.read_text()


class TestModuleReferences:

    def test_module_points_at_both_references(self):
        text = (MODULES_DIR / 'immersive_design.md').read_text()
        assert 'references/immersive-effects.md' in text
        assert 'references/immersive-comfort.md' in text

    def test_plugin_root_paths_resolve(self):
        """Every ${CLAUDE_PLUGIN_ROOT}/... path in the module must exist on disk."""
        text = (MODULES_DIR / 'immersive_design.md').read_text()
        for rel in re.findall(r'\$\{CLAUDE_PLUGIN_ROOT\}/([\w\-./]+)', text):
            assert (PLUGIN_ROOT / rel).exists(), f"unresolved reference: {rel}"


class TestVocabularyGuards:
    """Standing guards against reintroduction, not one-time checks."""

    PLUGIN_FILES = [p for p in PLUGIN_ROOT.rglob('*')
                    if p.is_file() and p.suffix in {'.md', '.py', '.json', '.yaml'}]

    def test_no_gag_vocabulary_anywhere(self):
        """Word-boundary matched — 'engagement' contains 'gag' and is fine."""
        offenders = []
        for path in self.PLUGIN_FILES:
            for i, line in enumerate(path.read_text(errors='ignore').splitlines(), 1):
                if re.search(r'\bgag', line, re.I):
                    offenders.append(f"{path.name}:{i}")
        assert not offenders, f"'gag' vocabulary found: {offenders}"

    def test_no_billing_vocabulary(self):
        """Plugin users bring their own compute. Credits are a web concept."""
        allow = [
            r'credits\.', r'`credits`', r'"credits"', r'credits:', r'credits section',
            r'Credits Rules', r'model credits', r'new credits', r'existing credits',
            r'preferences, credits', r'append new credits', r'full credits',
            r'credit-card', r"'paid'", r'paid off', r'Free-form', r'Freeform',
            r'Free text', r'freely', r'free-form', r'Unit cost',
        ]
        pattern = re.compile(
            r'\bcredits?\b|\bpaid\b|\(free\)|\bfree\b|cost estimate'
            r'|\bbilling\b|\bpricing\b|\bsubscription\b', re.I)
        offenders = []
        for path in self.PLUGIN_FILES:
            for i, line in enumerate(path.read_text(errors='ignore').splitlines(), 1):
                if pattern.search(line) and not any(re.search(a, line, re.I) for a in allow):
                    offenders.append(f"{path.name}:{i}: {line.strip()[:80]}")
        assert not offenders, "billing vocabulary found:\n" + "\n".join(offenders)


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
