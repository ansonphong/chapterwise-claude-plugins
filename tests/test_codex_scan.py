"""
Structural scan and node resolution.

The scan is what lets /analysis ask a specific question ("36 beats across 9
acts — beat-by-beat is 36 passes") instead of a generic one. It must stay
structural: shape, counts and content *sizes*, never whole chapters.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (Path(__file__).parent.parent / 'plugins' / 'chapterwise'
          / 'scripts' / 'codex_scan.py')
sys.path.insert(0, str(SCRIPT.parent))

from codex_scan import (  # noqa: E402
    ROOT_SCOPE, node_content, node_content_size, parse_depth, scan, nodes,
)


def write_show(tmp_path, acts=2, beats=3, body_on_beats=False):
    """A script/act/beat tree shaped like a dome show."""
    def beat(a, b):
        node = {'id': f'beat-{a}-{b}', 'type': 'beat', 'name': f'Beat {a}.{b}'}
        if body_on_beats:
            node['body'] = 'Beat prose.'
        else:
            # Chrysalis shape: empty body, everything in content blocks.
            node['content'] = [
                {'key': 'visual', 'name': 'Visual', 'value': f'Visual for {a}.{b}'},
                {'key': 'cues', 'name': 'Cues', 'value': 'A bell.'},
            ]
        return node

    doc = {
        'id': 'show', 'type': 'script', 'name': 'Test Show',
        'body': 'Overview of the show.',
        'attributes': [{'key': 'duration', 'value': '36:00'}],
        'children': [
            {'id': f'act-{a}', 'type': 'act', 'name': f'Act {a}',
             'body': f'Act {a} summary.',
             'children': [beat(a, b) for b in range(beats)]}
            for a in range(acts)
        ],
    }
    path = tmp_path / 'show.codex.yaml'
    import yaml
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding='utf-8')
    return path


class TestContentDetection:
    def test_content_blocks_count_as_content(self, tmp_path):
        """A beat with an empty body but populated content blocks is not empty."""
        node = {'body': '', 'content': [{'key': 'visual', 'value': 'x' * 50}]}
        assert node_content_size(node) == 50

    def test_content_blocks_are_labelled_in_extracted_text(self):
        node = {'content': [{'key': 'visual', 'name': 'Visual', 'value': 'Darkness.'}]}
        assert 'Visual: Darkness.' in node_content(node)

    def test_attributes_are_included_for_analysis(self):
        node = {'body': 'x', 'attributes': [{'key': 'timecode', 'name': 'Timecode',
                                             'value': '00:00'}]}
        assert 'Timecode: 00:00' in node_content(node)


class TestScan:
    def test_reports_tree_shape(self, tmp_path):
        result = scan({'path': str(write_show(tmp_path, acts=2, beats=3))})
        assert result['totalNodes'] == 9   # 1 script + 2 acts + 6 beats
        assert result['maxDepth'] == 2
        assert result['leafCount'] == 6
        assert result['leafDepth'] == 2

    def test_levels_carry_types_and_content_counts(self, tmp_path):
        result = scan({'path': str(write_show(tmp_path))})
        by_depth = {lv['depth']: lv for lv in result['levels']}
        assert by_depth[1]['types'] == ['act']
        assert by_depth[2]['types'] == ['beat']
        assert by_depth[2]['count'] == by_depth[2]['withContent']

    def test_root_attributes_are_surfaced(self, tmp_path):
        result = scan({'path': str(write_show(tmp_path))})
        assert result['attributes']['duration'] == '36:00'

    def test_suggests_deepest_fully_populated_level(self, tmp_path):
        result = scan({'path': str(write_show(tmp_path))})
        assert result['suggestedDepth'] == 2
        assert 'beat' in result['suggestedReason']

    def test_flat_document_suggests_root(self, tmp_path):
        path = tmp_path / 'flat.codex.yaml'
        path.write_text('id: c\ntype: chapter\nname: One\nbody: Prose.\n', encoding='utf-8')
        result = scan({'path': str(path)})
        assert result['suggestedDepth'] == ROOT_SCOPE
        assert result['totalNodes'] == 1

    def test_level_with_an_empty_node_is_not_suggested(self, tmp_path):
        import yaml
        doc = {'id': 's', 'type': 'script', 'name': 'S', 'body': 'x', 'children': [
            {'id': 'a', 'type': 'act', 'name': 'A', 'body': 'has content'},
            {'id': 'b', 'type': 'act', 'name': 'B'},  # empty
        ]}
        path = tmp_path / 's.codex.yaml'
        path.write_text(yaml.safe_dump(doc), encoding='utf-8')
        assert scan({'path': str(path)})['suggestedDepth'] == ROOT_SCOPE


class TestParseDepth:
    LEVELS = [{'depth': 0, 'count': 1}, {'depth': 1, 'count': 9}, {'depth': 2, 'count': 36}]

    def test_root(self):
        assert parse_depth('root', self.LEVELS, 2) == ['root']

    def test_integer(self):
        assert parse_depth('1', self.LEVELS, 2) == [1]

    def test_comma_list(self):
        assert parse_depth('root,leaf', self.LEVELS, 2) == ['root', 'leaf']

    def test_auto_uses_the_suggestion(self):
        assert parse_depth('auto', self.LEVELS, 2) == [2]

    def test_auto_falls_back_to_root(self):
        assert parse_depth('auto', self.LEVELS, 'root') == ['root']

    def test_all_means_root_plus_leaf(self):
        assert parse_depth('all', self.LEVELS, 2) == ['root', 'leaf']

    def test_duplicates_collapse(self):
        assert parse_depth('root,root,leaf', self.LEVELS, 2) == ['root', 'leaf']

    def test_default_is_auto(self):
        assert parse_depth(None, self.LEVELS, 2) == [2]

    def test_unrecognized_selector_is_an_error(self):
        with pytest.raises(ValueError, match='unrecognized depth'):
            parse_depth('sideways', self.LEVELS, 2)


class TestNodes:
    def test_root_and_leaf_returns_both(self, tmp_path):
        result = nodes({'path': str(write_show(tmp_path, acts=2, beats=3)),
                        'depth': 'root,leaf'})
        assert result['count'] == 7          # 1 root + 6 beats
        assert result['nodes'][0]['scope'] == ROOT_SCOPE
        assert all(n['scope'].startswith('node:') for n in result['nodes'][1:])

    def test_document_order_is_preserved(self, tmp_path):
        result = nodes({'path': str(write_show(tmp_path, acts=2, beats=3)),
                        'depth': 'leaf'})
        assert [n['name'] for n in result['nodes']] == [
            'Beat 0.0', 'Beat 0.1', 'Beat 0.2', 'Beat 1.0', 'Beat 1.1', 'Beat 1.2']

    def test_index_is_sequential(self, tmp_path):
        result = nodes({'path': str(write_show(tmp_path)), 'depth': 'root,leaf'})
        assert [n['index'] for n in result['nodes']] == list(range(result['count']))

    def test_path_shows_ancestry(self, tmp_path):
        result = nodes({'path': str(write_show(tmp_path)), 'depth': 'leaf'})
        assert result['nodes'][0]['path'] == 'Test Show › Act 0 › Beat 0.0'

    def test_nodes_carry_their_content(self, tmp_path):
        result = nodes({'path': str(write_show(tmp_path)), 'depth': 'leaf'})
        assert 'Visual for 0.0' in result['nodes'][0]['content']

    def test_overlapping_selectors_do_not_duplicate(self, tmp_path):
        """depth 2 and leaf name the same nodes here."""
        result = nodes({'path': str(write_show(tmp_path, acts=2, beats=3)),
                        'depth': '2,leaf'})
        assert result['count'] == 6
        assert len({n['scope'] for n in result['nodes']}) == 6

    def test_idless_node_gets_structural_address_and_warns(self, tmp_path):
        import yaml
        doc = {'id': 's', 'type': 'script', 'name': 'S', 'body': 'x', 'children': [
            {'type': 'act', 'name': 'Nameless', 'body': 'content'},
        ]}
        path = tmp_path / 's.codex.yaml'
        path.write_text(yaml.safe_dump(doc), encoding='utf-8')
        result = nodes({'path': str(path), 'depth': '1'})
        assert result['nodes'][0]['scope'].startswith('node@')
        assert result['warnings'] and 'has no id' in result['warnings'][0]


class TestCLI:
    def _run(self, action, payload):
        proc = subprocess.run([sys.executable, str(SCRIPT), action],
                              input=json.dumps(payload), capture_output=True, text=True)
        return proc, json.loads(proc.stdout)

    def test_scan_over_stdin(self, tmp_path):
        proc, out = self._run('scan', {'path': str(write_show(tmp_path))})
        assert proc.returncode == 0
        assert out['totalNodes'] == 9

    def test_missing_path_is_an_error(self):
        proc, out = self._run('scan', {})
        assert proc.returncode == 1
        assert 'path' in out['error']

    def test_unknown_action_is_an_error(self, tmp_path):
        proc, out = self._run('sideways', {'path': str(write_show(tmp_path))})
        assert proc.returncode == 1
        assert 'Unknown action' in out['error']

    def test_missing_file_is_an_error(self):
        proc, out = self._run('scan', {'path': '/nonexistent/x.codex.yaml'})
        assert proc.returncode == 1
        assert 'not found' in out['error'].lower()
