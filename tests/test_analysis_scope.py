"""
Scoped analysis entries.

A codex file can hold many analyzable nodes — a dome script is one file with 36
beats inside. Each node gets its own entry in the same .analysis.json, tagged
with a `scope`. Entries written before scopes existed have no `scope` attribute
and count as `root`.

The hazard this suite exists for: add_analysis_result() used to stale every
entry in a module node and trim the list to 3. Pushing 37 scoped entries
through that logic destroyed 34 of them.
"""
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / 'plugins' / 'chapterwise' / 'scripts'
sys.path.insert(0, str(SCRIPTS))

from analysis_writer import (  # noqa: E402
    DEFAULT_HISTORY_DEPTH,
    ROOT_SCOPE,
    add_analysis_result,
    entry_scope,
)


@pytest.fixture
def source(tmp_path):
    path = tmp_path / 'show.codex.yaml'
    path.write_text('id: show\ntype: script\nbody: A show.\n', encoding='utf-8')
    return path


def payload(n):
    return {'body': f'## Analysis {n}', 'summary': f'Summary {n}'}


def entries_for(source_path, module='immersive_design'):
    data = json.loads((source_path.parent / 'show.analysis.json').read_text(encoding='utf-8'))
    for child in data['children']:
        if child['id'] == module:
            return child['children']
    return []


def attrs(entry):
    return {a['key']: a['value'] for a in entry['attributes']}


class TestScopedWritesSurvive:
    def test_thirty_seven_scopes_yield_thirty_seven_entries(self, source):
        """The whole point. 1 root + 36 beats must not collapse to 3."""
        add_analysis_result(source, 'immersive_design', payload('root'),
                            model='m', scope=ROOT_SCOPE)
        for i in range(36):
            add_analysis_result(source, 'immersive_design', payload(i),
                                model='m', scope=f'node:beat-{i:02d}')

        entries = entries_for(source)
        assert len(entries) == 37
        assert len({attrs(e)['scope'] for e in entries}) == 37

    def test_every_scoped_entry_stays_current(self, source):
        for i in range(5):
            add_analysis_result(source, 'immersive_design', payload(i),
                                model='m', scope=f'node:beat-{i}')
        entries = entries_for(source)
        assert all(attrs(e)['analysisStatus'] == 'current' for e in entries)
        assert all(e['status'] == 'published' for e in entries)

    def test_entry_ids_are_unique_within_one_second(self, source):
        """37 writes complete well inside one second; ids must not collide."""
        for i in range(37):
            add_analysis_result(source, 'immersive_design', payload(i),
                                model='m', scope=f'node:beat-{i:02d}')
        ids = [e['id'] for e in entries_for(source)]
        assert len(set(ids)) == len(ids)


class TestPerScopeHistory:
    def test_rewriting_one_scope_trims_only_that_scope(self, source):
        add_antml = add_analysis_result
        for i in range(DEFAULT_HISTORY_DEPTH + 1):
            add_antml(source, 'immersive_design', payload(i), model='m', scope='node:beat-01')
        add_antml(source, 'immersive_design', payload('other'), model='m', scope='node:beat-02')

        entries = entries_for(source)
        beat01 = [e for e in entries if attrs(e)['scope'] == 'node:beat-01']
        beat02 = [e for e in entries if attrs(e)['scope'] == 'node:beat-02']
        assert len(beat01) == DEFAULT_HISTORY_DEPTH
        assert len(beat02) == 1

    def test_rewriting_one_scope_does_not_stale_another(self, source):
        add_analysis_result(source, 'immersive_design', payload(1), model='m', scope='node:a')
        add_analysis_result(source, 'immersive_design', payload(2), model='m', scope='node:b')
        add_analysis_result(source, 'immersive_design', payload(3), model='m', scope='node:b')

        entries = entries_for(source)
        a = [e for e in entries if attrs(e)['scope'] == 'node:a']
        assert attrs(a[0])['analysisStatus'] == 'current', "writing scope b staled scope a"

    def test_newest_entry_for_a_scope_is_first(self, source):
        for i in range(3):
            add_analysis_result(source, 'immersive_design', payload(i), model='m', scope='node:a')
        a = [e for e in entries_for(source) if attrs(e)['scope'] == 'node:a']
        assert a[0]['body'] == '## Analysis 2'
        assert attrs(a[0])['analysisStatus'] == 'current'
        assert all(attrs(e)['analysisStatus'] == 'stale' for e in a[1:])


class TestBackwardCompatibility:
    def test_unscoped_write_behaves_exactly_as_before(self, source):
        for i in range(DEFAULT_HISTORY_DEPTH + 2):
            add_analysis_result(source, 'summary', payload(i), model='m')
        entries = entries_for(source, 'summary')
        assert len(entries) == DEFAULT_HISTORY_DEPTH
        assert attrs(entries[0])['analysisStatus'] == 'current'

    def test_entry_without_scope_attribute_counts_as_root(self):
        assert entry_scope({'attributes': []}) == ROOT_SCOPE
        assert entry_scope({}) == ROOT_SCOPE
        assert entry_scope({'attributes': [{'key': 'scope', 'value': 'node:x'}]}) == 'node:x'

    def test_legacy_file_is_not_destroyed_by_a_scoped_write(self, source, tmp_path):
        """A pre-scope analysis file must survive its first scoped write."""
        add_analysis_result(source, 'immersive_design', payload('legacy'), model='m')
        legacy = entries_for(source)[0]
        for attr in list(legacy['attributes']):
            if attr['key'] == 'scope':
                legacy['attributes'].remove(attr)
        path = tmp_path / 'show.analysis.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        data['children'][0]['children'][0] = legacy
        path.write_text(json.dumps(data), encoding='utf-8')

        add_analysis_result(source, 'immersive_design', payload('beat'),
                            model='m', scope='node:beat-01')

        entries = entries_for(source)
        assert len(entries) == 2, "the scoped write dropped the legacy root entry"
        # The legacy entry keeps no scope attribute — it is read as root, not rewritten.
        assert {entry_scope(e) for e in entries} == {ROOT_SCOPE, 'node:beat-01'}
        legacy_now = [e for e in entries if entry_scope(e) == ROOT_SCOPE][0]
        assert 'scope' not in attrs(legacy_now)


class TestScopeMetadata:
    def test_scope_metadata_is_recorded(self, source):
        add_analysis_result(
            source, 'immersive_design', payload(1), model='m',
            scope='node:6de250b7', scope_name='Quantum Embryo',
            scope_path='Chrysalis › In The Void › Quantum Embryo',
            scope_depth=2, scope_index=1,
        )
        a = attrs(entries_for(source)[0])
        assert a['scope'] == 'node:6de250b7'
        assert a['scopeName'] == 'Quantum Embryo'
        assert a['scopePath'] == 'Chrysalis › In The Void › Quantum Embryo'
        assert a['scopeDepth'] == 2
        assert a['scopeIndex'] == 1

    def test_root_scope_needs_no_node_metadata(self, source):
        add_analysis_result(source, 'immersive_design', payload(1), model='m')
        a = attrs(entries_for(source)[0])
        assert a['scope'] == ROOT_SCOPE
        assert 'scopeName' not in a
