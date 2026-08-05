"""
The model recorded on an analysis entry is a provenance claim.

It must reflect the model that actually produced the analysis. Before this
suite existed, `analysis_writer.py` defaulted to 'claude-sonnet-4' and the CLI
never passed anything else, so every analysis the plugin had ever written
carried that stamp regardless of what ran.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).parent.parent / 'plugins' / 'chapterwise'
SCRIPTS = PLUGIN / 'scripts'
WRITER = SCRIPTS / 'analysis_writer.py'

sys.path.insert(0, str(SCRIPTS))
from analysis_writer import UNKNOWN_MODEL, resolve_model  # noqa: E402


PAYLOAD = {'body': '## Test\n\nBody.', 'summary': 'A summary.'}


class TestResolveModel:
    def test_explicit_argument_wins(self):
        assert resolve_model('claude-opus-5', {'model': 'from-payload'}) == 'claude-opus-5'

    def test_payload_model_used_when_no_argument(self):
        assert resolve_model(None, {'model': 'claude-opus-5'}) == 'claude-opus-5'

    def test_env_var_used_when_nothing_else_reports(self, monkeypatch):
        monkeypatch.setenv('CHAPTERWISE_ANALYSIS_MODEL', 'claude-haiku-4-5')
        assert resolve_model(None, PAYLOAD) == 'claude-haiku-4-5'

    def test_argument_beats_env_var(self, monkeypatch):
        monkeypatch.setenv('CHAPTERWISE_ANALYSIS_MODEL', 'from-env')
        assert resolve_model('explicit', PAYLOAD) == 'explicit'

    def test_unreported_model_is_unknown_not_a_guess(self, monkeypatch):
        """An honest blank beats a plausible fabrication."""
        monkeypatch.delenv('CHAPTERWISE_ANALYSIS_MODEL', raising=False)
        assert resolve_model(None, PAYLOAD) == UNKNOWN_MODEL

    def test_blank_and_whitespace_are_treated_as_absent(self, monkeypatch):
        monkeypatch.delenv('CHAPTERWISE_ANALYSIS_MODEL', raising=False)
        assert resolve_model('', {'model': '   '}) == UNKNOWN_MODEL

    def test_value_is_stripped(self):
        assert resolve_model('  claude-opus-5  ', None) == 'claude-opus-5'

    def test_handles_missing_payload(self, monkeypatch):
        monkeypatch.delenv('CHAPTERWISE_ANALYSIS_MODEL', raising=False)
        assert resolve_model(None, None) == UNKNOWN_MODEL


class TestWriterEndToEnd:
    def _run(self, tmp_path, extra_args=(), payload=None, env=None):
        source = tmp_path / 'chapter.codex.yaml'
        source.write_text('id: chapter\ntype: chapter\nbody: Some prose.\n', encoding='utf-8')
        proc = subprocess.run(
            [sys.executable, str(WRITER), str(source), 'summary', '-', *extra_args],
            input=json.dumps(payload or PAYLOAD),
            capture_output=True, text=True, env=env,
        )
        assert proc.returncode == 0, proc.stderr
        written = json.loads((tmp_path / 'chapter.analysis.json').read_text(encoding='utf-8'))
        entry = written['children'][0]['children'][0]
        return {a['key']: a['value'] for a in entry['attributes']}, proc.stderr

    def test_cli_model_flag_is_recorded(self, tmp_path):
        attrs, _ = self._run(tmp_path, ['--model', 'claude-opus-5'])
        assert attrs['model'] == 'claude-opus-5'

    def test_cli_model_equals_form_is_recorded(self, tmp_path):
        attrs, _ = self._run(tmp_path, ['--model=claude-opus-5'])
        assert attrs['model'] == 'claude-opus-5'

    def test_payload_model_is_recorded(self, tmp_path):
        payload = dict(PAYLOAD, model='claude-opus-5')
        attrs, _ = self._run(tmp_path, payload=payload)
        assert attrs['model'] == 'claude-opus-5'

    def test_unreported_model_writes_unknown_and_warns(self, tmp_path):
        import os
        env = {k: v for k, v in os.environ.items() if k != 'CHAPTERWISE_ANALYSIS_MODEL'}
        attrs, stderr = self._run(tmp_path, env=env)
        assert attrs['model'] == UNKNOWN_MODEL
        assert 'no model reported' in stderr.lower()

    def test_writer_never_emits_a_model_nobody_reported(self, tmp_path):
        import os
        env = {k: v for k, v in os.environ.items() if k != 'CHAPTERWISE_ANALYSIS_MODEL'}
        attrs, _ = self._run(tmp_path, env=env)
        assert 'sonnet' not in attrs['model']
        assert 'opus' not in attrs['model']


class TestNoHardcodedModelDefaults:
    """Standing guard. A concrete model name must never be a fallback value."""

    def test_writer_has_no_concrete_model_default(self):
        source = WRITER.read_text(encoding='utf-8')
        offenders = [
            line.strip() for line in source.splitlines()
            if re.search(r"=\s*['\"]claude-[\w.\-]+['\"]", line)
        ]
        assert not offenders, (
            "A concrete model name is being used as a default value. The recorded "
            f"model must come from the caller: {offenders}"
        )

    @pytest.mark.parametrize('path', [
        PLUGIN / 'modules' / '_output-format.md',
        PLUGIN / 'commands' / 'analysis.md',
        PLUGIN / 'commands' / 'atlas.md',
        # Repo-root README — the plugin-level one is now a stub pointing here.
        Path(__file__).parent.parent / 'README.md',
    ], ids=lambda p: p.name)
    def test_docs_do_not_ship_a_copyable_model_name(self, path):
        """
        Example blocks get copied verbatim by agents. Placeholders cannot be
        mistaken for the right answer; 'claude-sonnet-4' can.
        """
        text = path.read_text(encoding='utf-8')
        # Only flags a model name sitting in a value position — the thing an
        # agent copies. Prose naming a model as an illustrative example is fine.
        value_position = re.compile(
            r'("model"\s*:|"value"\s*:|model:|with)\s*"?\{?claude-(sonnet|opus|haiku)-\d',
            re.I,
        )
        offenders = [line.strip() for line in text.splitlines() if value_position.search(line)]
        assert not offenders, f"{path.name} ships a copyable model name: {offenders}"
