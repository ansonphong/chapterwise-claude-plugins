#!/usr/bin/env python3
"""Tests for schema_validator module."""
import pytest
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'plugins' / 'chapterwise' / 'scripts'))
from schema_validator import SchemaValidator, validate_codex, validate_analysis


class TestSchemaValidator:
    """Test SchemaValidator class."""

    def test_load_codex_schema(self):
        """Should load codex schema successfully."""
        validator = SchemaValidator()
        schema = validator.load_schema('codex')
        assert schema is not None
        assert schema.get('title') == 'Codex V1.3'

    def test_load_analysis_schema(self):
        """Should load analysis schema successfully."""
        validator = SchemaValidator()
        schema = validator.load_schema('analysis')
        assert schema is not None
        assert schema.get('title') == 'Codex Analysis File V1.3'

    def test_load_invalid_schema_type(self):
        """Should return None for unknown schema type."""
        validator = SchemaValidator()
        schema = validator.load_schema('nonexistent')
        assert schema is None


class TestValidateCodex:
    """Test codex validation."""

    def test_valid_minimal_codex(self):
        """Should validate minimal valid codex."""
        data = {
            'metadata': {'formatVersion': '1.2'}
        }
        is_valid, errors = validate_codex(data)
        assert is_valid is True
        assert errors == []

    def test_valid_full_codex(self):
        """Should validate full codex with all fields."""
        data = {
            'metadata': {
                'formatVersion': '1.2',
                'documentVersion': '1.0.0'
            },
            'id': 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d',
            'type': 'chapter',
            'name': 'Test Chapter',
            'body': 'Some content here',
            'attributes': [
                {'key': 'word_count', 'value': 100}
            ]
        }
        is_valid, errors = validate_codex(data)
        assert is_valid is True
        assert errors == []

    def test_invalid_missing_metadata(self):
        """Should fail when metadata is missing."""
        data = {'id': 'test', 'name': 'Test'}
        is_valid, errors = validate_codex(data)
        assert is_valid is False
        assert len(errors) > 0

    def test_invalid_format_version(self):
        """Should fail with invalid formatVersion."""
        data = {
            'metadata': {'formatVersion': '2.0'}
        }
        is_valid, errors = validate_codex(data)
        assert is_valid is False

    def test_uuid_id_accepted(self):
        """Should accept UUID format for id."""
        data = {
            'metadata': {'formatVersion': '1.2'},
            'id': 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d'
        }
        is_valid, errors = validate_codex(data)
        assert is_valid is True

    def test_simple_id_accepted(self):
        """Should accept simple slug format for id."""
        data = {
            'metadata': {'formatVersion': '1.2'},
            'id': 'my-chapter-1'
        }
        is_valid, errors = validate_codex(data)
        assert is_valid is True


class TestValidateAnalysis:
    """Test analysis validation."""

    def test_valid_analysis(self):
        """Should validate valid analysis file."""
        data = {
            'metadata': {'formatVersion': '1.2'},
            'id': 'test-analysis',
            'type': 'analysis',
            'name': 'Analysis Results',
            'attributes': [
                {'key': 'sourceFile', 'value': 'test.codex.yaml'}
            ],
            'children': []
        }
        is_valid, errors = validate_analysis(data)
        assert is_valid is True

    def test_invalid_analysis_missing_type(self):
        """Should fail when type is not 'analysis'."""
        data = {
            'metadata': {'formatVersion': '1.2'},
            'id': 'test-analysis',
            'type': 'wrong-type',
            'attributes': [{'key': 'sourceFile', 'value': 'test.yaml'}],
            'children': []
        }
        is_valid, errors = validate_analysis(data)
        assert is_valid is False


class TestAutoFixerValidation:
    """Test auto-fixer produces schema-valid output."""

    def test_auto_fixer_output_is_valid(self):
        """Auto-fixer should produce schema-valid codex."""
        from auto_fixer import CodexAutoFixer

        # Minimal input that needs fixing
        input_data = {
            'name': 'Test',
            'type': 'chapter'
        }

        fixer = CodexAutoFixer()
        fixed, fixes = fixer.auto_fix_codex(None, input_data)

        is_valid, errors = validate_codex(fixed)
        assert is_valid, f"Auto-fixer output invalid: {errors}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
