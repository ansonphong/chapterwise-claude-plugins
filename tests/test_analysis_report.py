"""
Report assembly.

The report is a deterministic re-render of stored results. It must never call a
model, must come out in document order rather than write order, and must be
byte-identical when regenerated from unchanged input.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).parent.parent / 'plugins' / 'chapterwise' / 'scripts'
SCRIPT = SCRIPTS / 'analysis_report.py'
sys.path.insert(0, str(SCRIPTS))

from analysis_report import ROOT_SCOPE, build  # noqa: E402
from analysis_writer import add_analysis_result  # noqa: E402

MODULE = 'immersive_design'


@pytest.fixture
def show(tmp_path):
    """Three beats in two acts, then analyses written out of document order."""
    doc = {
        'id': 'show', 'type': 'script', 'name': 'Test Show', 'body': 'Overview.',
        'children': [
            {'id': 'act-1', 'type': 'act', 'name': 'Act One', 'children': [
                {'id': 'beat-a', 'type': 'beat', 'name': 'Opening'},
                {'id': 'beat-b', 'type': 'beat', 'name': 'Rising'},
            ]},
            {'id': 'act-2', 'type': 'act', 'name': 'Act Two', 'children': [
                {'id': 'beat-c', 'type': 'beat', 'name': 'Climax'},
            ]},
        ],
    }
    path = tmp_path / 'show.codex.yaml'
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding='utf-8')

    # Deliberately reversed, to prove the report re-sorts from the source.
    for scope, name in [('node:beat-c', 'Climax'), ('node:beat-b', 'Rising'),
                        ('node:beat-a', 'Opening')]:
        add_analysis_result(
            path, MODULE,
            {'body': f'## Immersive Design\n\nRead of {name}.',
             'summary': f'{name} summary.',
             'children': [{'name': 'Effects in Play', 'content': f'Effects for {name}.'}],
             'tags': ['dome'], 'attributes': [{'key': 'intensity', 'value': 7}]},
            model='claude-opus-5', scope=scope, scope_name=name, scope_depth=2)

    add_analysis_result(
        path, MODULE,
        {'body': '## Immersive Design\n\nWhole-show read.', 'summary': 'The show.'},
        model='claude-opus-5', scope=ROOT_SCOPE)
    return path


class TestOrdering:
    def test_report_follows_document_order_not_write_order(self, show):
        result = build({'source': str(show), 'module': MODULE, 'generated': '2026-08-04'})
        assert result['scopes'] == [
            ROOT_SCOPE, 'node:beat-a', 'node:beat-b', 'node:beat-c']

    def test_markdown_headings_appear_in_show_order(self, show):
        build({'source': str(show), 'module': MODULE, 'format': 'markdown',
               'generated': '2026-08-04'})
        text = (show.parent / 'analysis' /
                'show-immersive-design-2026-08-04.md').read_text(encoding='utf-8')
        assert text.index('Opening') < text.index('Rising') < text.index('Climax')


class TestOutputLocation:
    def test_lands_in_analysis_folder_beside_the_source(self, show):
        result = build({'source': str(show), 'module': MODULE, 'format': 'markdown',
                        'generated': '2026-08-04'})
        out = Path(result['path'])
        assert out.parent == show.parent / 'analysis'
        assert out.name == 'show-immersive-design-2026-08-04.md'

    def test_codex_extension(self, show):
        result = build({'source': str(show), 'module': MODULE,
                        'format': 'codex', 'generated': '2026-08-04'})
        assert Path(result['path']).name.endswith('.codex.yaml')

    def test_existing_file_is_reported_not_overwritten(self, show):
        args = {'source': str(show), 'module': MODULE, 'generated': '2026-08-04'}
        first = build(args)
        Path(first['path']).write_text('sentinel', encoding='utf-8')
        second = build(args)
        assert second['status'] == 'exists'
        assert Path(first['path']).read_text(encoding='utf-8') == 'sentinel'

    def test_force_overwrites(self, show):
        args = {'source': str(show), 'module': MODULE, 'generated': '2026-08-04'}
        first = build(args)
        Path(first['path']).write_text('sentinel', encoding='utf-8')
        assert build({**args, 'force': True})['status'] == 'written'


class TestDeterminism:
    def test_regenerating_is_byte_identical(self, show):
        args = {'source': str(show), 'module': MODULE, 'format': 'markdown',
                'generated': '2026-08-04', 'generatedISO': '2026-08-04T00:00:00Z',
                'force': True}
        a = Path(build(args)['path']).read_bytes()
        b = Path(build(args)['path']).read_bytes()
        assert a == b

    def test_codex_regeneration_is_byte_identical(self, show):
        """Ids are derived, not minted, so nothing at all moves between renders."""
        args = {'source': str(show), 'module': MODULE, 'format': 'codex',
                'generated': '2026-08-04', 'generatedISO': '2026-08-04T00:00:00Z',
                'force': True}
        assert (Path(build(args)['path']).read_bytes()
                == Path(build(args)['path']).read_bytes())


class TestMarkdown:
    def test_includes_summary_body_children_and_metrics(self, show):
        build({'source': str(show), 'module': MODULE, 'format': 'markdown',
               'generated': '2026-08-04'})
        text = (show.parent / 'analysis' /
                'show-immersive-design-2026-08-04.md').read_text(encoding='utf-8')
        assert 'Opening summary.' in text
        assert 'Read of Opening.' in text
        assert 'Effects in Play' in text
        assert '| intensity | 7 |' in text

    def test_records_the_model_that_ran(self, show):
        build({'source': str(show), 'module': MODULE, 'format': 'markdown',
               'generated': '2026-08-04'})
        text = (show.parent / 'analysis' /
                'show-immersive-design-2026-08-04.md').read_text(encoding='utf-8')
        assert 'claude-opus-5' in text


class TestCodex:
    def test_is_valid_codex_v13(self, show):
        result = build({'source': str(show), 'module': MODULE, 'format': 'codex',
                        'generated': '2026-08-04'})
        doc = yaml.safe_load(Path(result['path']).read_text(encoding='utf-8'))
        assert doc['metadata']['formatVersion'] == '1.3'
        assert doc['type'] == 'analysis-report'
        assert doc['id'] and all(c['id'] for c in doc['children'])

    def test_mirrors_the_source_tree(self, show):
        result = build({'source': str(show), 'module': MODULE, 'format': 'codex',
                        'generated': '2026-08-04'})
        doc = yaml.safe_load(Path(result['path']).read_text(encoding='utf-8'))
        assert [c['name'] for c in doc['children']] == [
            'Overview', 'Opening', 'Rising', 'Climax']


class TestStaleAndOrphan:
    def test_stale_entries_are_excluded(self, show):
        add_analysis_result(show, MODULE, {'body': 'newer', 'summary': 'newer'},
                            model='claude-opus-5', scope='node:beat-a',
                            scope_name='Opening', scope_depth=2)
        build({'source': str(show), 'module': MODULE, 'format': 'markdown',
               'generated': '2026-08-04', 'force': True})
        text = (show.parent / 'analysis' /
                'show-immersive-design-2026-08-04.md').read_text(encoding='utf-8')
        assert 'newer' in text
        assert 'Read of Opening.' not in text

    def test_orphaned_entry_is_kept_and_flagged(self, show):
        """A node removed from the source must not silently vanish from the report."""
        doc = yaml.safe_load(show.read_text(encoding='utf-8'))
        doc['children'][0]['children'] = [doc['children'][0]['children'][0]]
        show.write_text(yaml.safe_dump(doc, sort_keys=False), encoding='utf-8')

        result = build({'source': str(show), 'module': MODULE, 'format': 'markdown',
                        'generated': '2026-08-04', 'force': True})
        assert 'node:beat-b' in result['scopes']
        text = Path(result['path']).read_text(encoding='utf-8')
        assert 'no longer in source' in text


class TestErrors:
    def _run(self, payload):
        proc = subprocess.run([sys.executable, str(SCRIPT)],
                              input=json.dumps(payload), capture_output=True, text=True)
        return proc, json.loads(proc.stdout)

    def test_missing_module_field(self, show):
        proc, out = self._run({'source': str(show)})
        assert proc.returncode == 1 and 'module' in out['error']

    def test_no_analysis_file(self, tmp_path):
        src = tmp_path / 'bare.codex.yaml'
        src.write_text('id: b\ntype: chapter\nbody: x\n', encoding='utf-8')
        proc, out = self._run({'source': str(src), 'module': MODULE})
        assert proc.returncode == 1 and 'No analysis found' in out['error']

    def test_module_absent_from_analysis(self, show):
        proc, out = self._run({'source': str(show), 'module': 'summary'})
        assert proc.returncode == 1 and 'No current summary results' in out['error']

    def test_unknown_format(self, show):
        proc, out = self._run({'source': str(show), 'module': MODULE, 'format': 'pdf'})
        assert proc.returncode == 1 and 'Unknown format' in out['error']

    def test_never_invokes_a_model(self):
        """Structural guard: the formatter must stay deterministic."""
        source = SCRIPT.read_text(encoding='utf-8')
        for forbidden in ('anthropic', 'openai', 'requests.post', 'urllib.request'):
            assert forbidden not in source, f"report generator reaches for {forbidden}"


class TestHeadingDeduplication:
    """Modules routinely open a child with its own heading."""

    def test_child_heading_not_printed_twice(self, show, tmp_path):
        from analysis_writer import add_analysis_result
        add_analysis_result(
            show, 'dupe',
            {'body': 'Body.', 'summary': 'S.',
             'children': [{'name': 'Motion Budget',
                           'content': '## Motion Budget\n\nThe budget.'}]},
            model='claude-opus-5')
        result = build({'source': str(show), 'module': 'dupe', 'format': 'markdown',
                        'generated': '2026-08-04', 'force': True})
        text = Path(result['path']).read_text(encoding='utf-8')
        assert text.count('Motion Budget') == 1

    def test_child_heading_kept_when_content_has_none(self, show):
        from analysis_writer import add_analysis_result
        add_analysis_result(
            show, 'plain',
            {'body': 'Body.', 'summary': 'S.',
             'children': [{'name': 'Effects in Play', 'content': 'Just prose.'}]},
            model='claude-opus-5')
        result = build({'source': str(show), 'module': 'plain', 'format': 'markdown',
                        'generated': '2026-08-04', 'force': True})
        text = Path(result['path']).read_text(encoding='utf-8')
        assert 'Effects in Play' in text and 'Just prose.' in text

    def test_different_heading_is_not_treated_as_duplicate(self, show):
        from analysis_writer import add_analysis_result
        add_analysis_result(
            show, 'diff',
            {'body': 'Body.', 'summary': 'S.',
             'children': [{'name': 'Comfort & Load',
                           'content': '## Something Else\n\nText.'}]},
            model='claude-opus-5')
        result = build({'source': str(show), 'module': 'diff', 'format': 'markdown',
                        'generated': '2026-08-04', 'force': True})
        text = Path(result['path']).read_text(encoding='utf-8')
        assert 'Comfort & Load' in text and 'Something Else' in text


class TestBothFormats:
    """The report format is a runtime choice, and "both" is one of the answers."""

    def test_writes_markdown_and_codex(self, show):
        result = build({'source': str(show), 'module': MODULE,
                        'format': 'both', 'generated': '2026-08-04'})
        assert [Path(p).suffix for p in result['paths']] == ['.md', '.yaml']
        assert all(Path(p).exists() for p in result['paths'])

    def test_both_share_one_stem(self, show):
        result = build({'source': str(show), 'module': MODULE,
                        'format': 'both', 'generated': '2026-08-04'})
        md, codex = (Path(p) for p in result['paths'])
        assert md.stem == codex.name.split('.codex')[0]

    def test_an_existing_file_in_either_format_blocks_both(self, show):
        args = {'source': str(show), 'module': MODULE, 'generated': '2026-08-04'}
        existing = Path(build({**args, 'format': 'codex'})['path'])
        result = build({**args, 'format': 'both'})
        assert result['status'] == 'exists'
        assert str(existing) in result['paths']

    def test_force_writes_over_both(self, show):
        args = {'source': str(show), 'module': MODULE, 'generated': '2026-08-04'}
        build({**args, 'format': 'codex'})
        result = build({**args, 'format': 'both', 'force': True})
        assert result['status'] == 'written' and len(result['paths']) == 2

    def test_single_format_still_reports_one_path(self, show):
        result = build({'source': str(show), 'module': MODULE, 'format': 'markdown',
                        'generated': '2026-08-04'})
        assert result['paths'] == [result['path']]


class TestFormatAuthority:
    """
    The codex report is produced through the plugin's own format machinery.

    A generator that imitates `/chapterwise:format` instead of using it is how
    the two drift apart — and drift is exactly what shipped: attribute keys the
    V1.3 schema forbids, unnoticed because nothing validated the output.
    """

    def _doc(self, show):
        result = build({'source': str(show), 'module': MODULE, 'format': 'codex',
                        'generated': '2026-08-04', 'force': True})
        return result, yaml.safe_load(Path(result['path']).read_text(encoding='utf-8'))

    def test_codex_report_passes_schema_validation(self, show):
        result, _ = self._doc(show)
        assert result['valid'] is True, result['issues']

    def test_the_auto_fixer_actually_ran(self, show):
        """documentVersion is the fixer's fingerprint — nothing else adds it."""
        _, doc = self._doc(show)
        assert doc['metadata']['documentVersion'] == '1.0.0'

    def test_attribute_keys_are_schema_legal(self, show):
        _, doc = self._doc(show)
        keys = [a['key'] for a in doc['attributes']]
        keys += [a['key'] for c in doc['children'] for a in c.get('attributes', [])]
        assert keys, 'expected attributes to check'
        assert all(re.fullmatch(r'[a-z][a-z0-9_-]*', k) for k in keys), keys

    def test_ids_survive_the_fixer(self, show):
        """
        The fixer replaces any id that is not v4-shaped. Deterministic ids that
        it rewrites are not deterministic.
        """
        _, first = self._doc(show)
        _, second = self._doc(show)
        assert first['id'] == second['id']
        assert [c['id'] for c in first['children']] == [c['id'] for c in second['children']]

    def test_ids_are_v4_shaped(self, show):
        _, doc = self._doc(show)
        v4 = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
        assert v4.match(doc['id'])
        assert all(v4.match(c['id']) for c in doc['children'])

    def test_markdown_report_is_validated_too(self, show):
        result = build({'source': str(show), 'module': MODULE, 'format': 'markdown',
                        'generated': '2026-08-04', 'force': True})
        assert result['valid'] is True and result['issues'] == []

    def test_invalid_codex_is_reported_not_silently_written(self):
        from analysis_report import validate_output
        valid, issues = validate_output('codex', 'metadata: {}\nattributes:\n- key: badKey\n')
        assert not valid and any('badKey' in i for i in issues)

    def test_missing_frontmatter_is_caught(self):
        from analysis_report import validate_output
        valid, issues = validate_output('markdown', '# Just a heading\n')
        assert not valid and 'frontmatter' in issues[0].lower()


class TestCodexLiteFrontmatter:
    """The markdown report is a Codex Lite document, not loose markdown."""

    def _text(self, show):
        build({'source': str(show), 'module': MODULE, 'format': 'markdown',
               'generated': '2026-08-04', 'force': True})
        return (show.parent / 'analysis' /
                'show-immersive-design-2026-08-04.md').read_text(encoding='utf-8')

    def test_has_frontmatter(self, show):
        text = self._text(show)
        assert text.startswith('---\n')
        fm = yaml.safe_load(text.split('---')[1])
        assert fm['type'] == 'analysis-report'
        assert fm['module'] == MODULE
        assert fm['entry_count'] == 4

    def test_frontmatter_records_the_model(self, show):
        fm = yaml.safe_load(self._text(show).split('---')[1])
        assert fm['model'] == 'claude-opus-5'

    def test_title_follows_frontmatter(self, show):
        assert '\n# Immersive Design — show\n' in self._text(show)
