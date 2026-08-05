#!/usr/bin/env python3
"""
Tests for Codex format version handling.

Guards the V1.3 upgrade against the two ways it previously went wrong:
scripts hardcoding a stale version literal, and the auto-fixer silently
downgrading a document that declared a version it did not recognize.

Spec: https://chapterwise.app/docs/codex/format/codex-format
"""
import re
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / 'plugins' / 'chapterwise' / 'scripts'
SCHEMA_DIR = Path(__file__).parent.parent / 'schemas'
sys.path.insert(0, str(SCRIPTS_DIR))

from codex_version import CURRENT_FORMAT_VERSION, SUPPORTED_FORMAT_VERSIONS
from auto_fixer import CodexAutoFixer
from schema_validator import validate_codex


class TestVersionConstants:
    """The single source of truth for the format version."""

    def test_current_version_is_1_3(self):
        assert CURRENT_FORMAT_VERSION == '1.3'

    def test_current_version_is_supported(self):
        assert CURRENT_FORMAT_VERSION in SUPPORTED_FORMAT_VERSIONS

    def test_older_versions_remain_supported(self):
        """V1.3 is backwards compatible — older documents stay valid."""
        for version in ['1.0', '1.1', '1.2']:
            assert version in SUPPORTED_FORMAT_VERSIONS


class TestSchemaAcceptsV13:
    """The schema must accept the current spec, including its new features."""

    @pytest.mark.parametrize('version', ['1.0', '1.1', '1.2', '1.3'])
    def test_accepts_supported_versions(self, version):
        is_valid, errors = validate_codex({'metadata': {'formatVersion': version}})
        assert is_valid, f"formatVersion {version} rejected: {errors}"

    def test_rejects_unknown_version(self):
        is_valid, _ = validate_codex({'metadata': {'formatVersion': '9.9'}})
        assert not is_valid

    def test_accepts_v13_content_array(self):
        """Content array with width, diagram and spreadsheet types."""
        doc = {
            'metadata': {'formatVersion': '1.3'},
            'id': 'test-doc',
            'type': 'chapter',
            'content': [
                {'key': 'visual', 'name': 'Visual', 'width': '1/2', 'value': 'Wide shot.'},
                {'key': 'audio', 'name': 'Audio', 'width': '1/2', 'value': 'Ambient wind.'},
                {'key': 'flow', 'type': 'diagram', 'width': '1/1',
                 'include': './diagrams/act.mermaid'},
                {'key': 'budget', 'type': 'spreadsheet', 'width': '1/1',
                 'include': '/data/budget.csv'},
            ],
        }
        is_valid, errors = validate_codex(doc)
        assert is_valid, f"V1.3 content array rejected: {errors}"

    @pytest.mark.parametrize('width', ['1/1', '1/2', '1/3'])
    def test_accepts_valid_widths(self, width):
        doc = {'metadata': {'formatVersion': '1.3'},
               'content': [{'key': 'x', 'width': width, 'value': 'y'}]}
        assert validate_codex(doc)[0]

    def test_rejects_invalid_width(self):
        doc = {'metadata': {'formatVersion': '1.3'},
               'content': [{'key': 'x', 'width': '2/3', 'value': 'y'}]}
        assert not validate_codex(doc)[0]

    @pytest.mark.parametrize('path', [
        './diagrams/flow.mermaid',
        './diagrams/flow.mmd',
        '/data/budget.csv',
        '/data/budget.xlsx',
        './chapters/one.codex.yaml',
    ])
    def test_include_resolves_v13_extensions(self, path):
        """V1.3 extends include resolution beyond codex documents."""
        doc = {'metadata': {'formatVersion': '1.3'},
               'content': [{'key': 'x', 'include': path}]}
        is_valid, errors = validate_codex(doc)
        assert is_valid, f"include {path} rejected: {errors}"


class TestAutoFixerDoesNotDowngrade:
    """Regression: the fixer used to rewrite any unrecognized version to 1.2."""

    @pytest.mark.parametrize('version', ['1.0', '1.1', '1.2', '1.3'])
    def test_preserves_supported_version(self, version):
        doc = {'metadata': {'formatVersion': version}, 'id': 'x', 'type': 'note', 'name': 'X'}
        fixed, fixes = CodexAutoFixer().auto_fix_codex(None, doc)
        assert fixed['metadata']['formatVersion'] == version
        assert not [f for f in fixes if 'formatVersion' in f]

    def test_stamps_current_version_when_missing(self):
        doc = {'metadata': {}, 'id': 'x', 'type': 'note', 'name': 'X'}
        fixed, fixes = CodexAutoFixer().auto_fix_codex(None, doc)
        assert fixed['metadata']['formatVersion'] == CURRENT_FORMAT_VERSION
        assert any('formatVersion' in f for f in fixes)

    def test_repairs_unknown_version(self):
        doc = {'metadata': {'formatVersion': '0.9'}, 'id': 'x', 'type': 'note', 'name': 'X'}
        fixed, fixes = CodexAutoFixer().auto_fix_codex(None, doc)
        assert fixed['metadata']['formatVersion'] == CURRENT_FORMAT_VERSION
        assert any('formatVersion' in f for f in fixes)


class TestNoHardcodedVersionStamps:
    """Drift guard — scripts must stamp from the shared constant."""

    # Matches a formatVersion assigned a literal version string.
    STAMP = re.compile(r"""['"]formatVersion['"]\s*:\s*['"][\d.]+['"]""")

    def test_scripts_do_not_hardcode_format_version(self):
        offenders = []
        for script in SCRIPTS_DIR.glob('*.py'):
            if script.name == 'codex_version.py':
                continue
            for i, line in enumerate(script.read_text().splitlines(), 1):
                if self.STAMP.search(line):
                    offenders.append(f"{script.name}:{i}: {line.strip()}")
        assert not offenders, (
            "Scripts must stamp CURRENT_FORMAT_VERSION, not a literal:\n  "
            + "\n  ".join(offenders)
        )

    def test_schema_files_are_current(self):
        """Schema filenames track the spec version they implement."""
        for prefix in ['codex', 'analysis', 'research']:
            expected = SCHEMA_DIR / f'{prefix}-v{CURRENT_FORMAT_VERSION}.schema.json'
            assert expected.exists(), f"missing {expected.name}"
