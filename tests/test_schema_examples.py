#!/usr/bin/env python3
"""
Tests that validate the examples embedded in schema files.
Ensures schema examples are themselves valid.
"""
import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'plugins' / 'chapterwise' / 'scripts'))
from schema_validator import SchemaValidator


SCHEMA_DIR = Path(__file__).parent.parent / 'schemas'


class TestCodexSchemaExamples:
    """Test examples in codex schema are valid."""

    @pytest.fixture
    def validator(self):
        return SchemaValidator()

    @pytest.fixture
    def codex_schema(self):
        with open(SCHEMA_DIR / 'codex-v1.3.schema.json') as f:
            return json.load(f)

    def test_schema_has_examples(self, codex_schema):
        """Schema should have examples section."""
        assert 'examples' in codex_schema
        assert len(codex_schema['examples']) > 0

    def test_all_examples_are_valid(self, validator, codex_schema):
        """All examples in schema should be valid."""
        for i, example in enumerate(codex_schema.get('examples', [])):
            is_valid, errors = validator.validate(example, 'codex')
            assert is_valid, f"Example {i} invalid: {errors}"


class TestAnalysisSchemaExamples:
    """Test examples in analysis schema are valid."""

    @pytest.fixture
    def validator(self):
        return SchemaValidator()

    @pytest.fixture
    def analysis_schema(self):
        with open(SCHEMA_DIR / 'analysis-v1.3.schema.json') as f:
            return json.load(f)

    def test_schema_has_examples(self, analysis_schema):
        """Schema should have examples section."""
        assert 'examples' in analysis_schema
        assert len(analysis_schema['examples']) > 0

    def test_all_examples_are_valid(self, validator, analysis_schema):
        """All examples in schema should be valid."""
        for i, example in enumerate(analysis_schema.get('examples', [])):
            is_valid, errors = validator.validate(example, 'analysis')
            assert is_valid, f"Example {i} invalid: {errors}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
