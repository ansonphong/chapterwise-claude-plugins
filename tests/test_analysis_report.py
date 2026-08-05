"""
Report assembly.

The report is a deterministic re-render of stored results. It must never call a
model, must come out in document order rather than write order, and must be
byte-identical when regenerated from unchanged input.
"""
import json
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
        build({'source': str(show), 'module': MODULE, 'generated': '2026-08-04'})
        text = (show.parent / 'analysis' /
                'show-immersive-design-2026-08-04.md').read_text(encoding='utf-8')
        assert text.index('Opening') < text.index('Rising') < text.index('Climax')


class TestOutputLocation:
    def test_lands_in_analysis_folder_beside_the_source(self, show):
        result = build({'source': str(show), 'module': MODULE, 'generated': '2026-08-04'})
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
        args = {'source': str(show), 'module': MODULE,
                'generated': '2026-08-04', 'generatedISO': '2026-08-04T00:00:00Z',
                'force': True}
        a = Path(build(args)['path']).read_bytes()
        b = Path(build(args)['path']).read_bytes()
        assert a == b

    def test_codex_regeneration_differs_only_in_uuids(self, show):
        """UUIDs are fresh per render; nothing else may move."""
        args = {'source': str(show), 'module': MODULE, 'format': 'codex',
                'generated': '2026-08-04', 'generatedISO': '2026-08-04T00:00:00Z',
                'force': True}
        first = yaml.safe_load(Path(build(args)['path']).read_text(encoding='utf-8'))
        second = yaml.safe_load(Path(build(args)['path']).read_text(encoding='utf-8'))
        assert [c['name'] for c in first['children']] == [c['name'] for c in second['children']]
        assert first['metadata'] == second['metadata']


class TestMarkdown:
    def test_includes_summary_body_children_and_metrics(self, show):
        build({'source': str(show), 'module': MODULE, 'generated': '2026-08-04'})
        text = (show.parent / 'analysis' /
                'show-immersive-design-2026-08-04.md').read_text(encoding='utf-8')
        assert 'Opening summary.' in text
        assert 'Read of Opening.' in text
        assert 'Effects in Play' in text
        assert '| intensity | 7 |' in text

    def test_records_the_model_that_ran(self, show):
        build({'source': str(show), 'module': MODULE, 'generated': '2026-08-04'})
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
        build({'source': str(show), 'module': MODULE, 'generated': '2026-08-04',
               'force': True})
        text = (show.parent / 'analysis' /
                'show-immersive-design-2026-08-04.md').read_text(encoding='utf-8')
        assert 'newer' in text
        assert 'Read of Opening.' not in text

    def test_orphaned_entry_is_kept_and_flagged(self, show):
        """A node removed from the source must not silently vanish from the report."""
        doc = yaml.safe_load(show.read_text(encoding='utf-8'))
        doc['children'][0]['children'] = [doc['children'][0]['children'][0]]
        show.write_text(yaml.safe_dump(doc, sort_keys=False), encoding='utf-8')

        result = build({'source': str(show), 'module': MODULE,
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
