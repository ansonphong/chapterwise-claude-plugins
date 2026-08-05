#!/usr/bin/env python3
"""
Schema Validator for Codex and Analysis files.
Provides centralized JSON Schema validation for all scripts.

Usage:
    from schema_validator import validate_codex, validate_analysis

    is_valid, errors = validate_codex(data)
    if not is_valid:
        print(f"Validation errors: {errors}")
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Codex format version (single source of truth).
try:
    from codex_version import CURRENT_FORMAT_VERSION
except ImportError:  # standalone execution outside the scripts directory
    CURRENT_FORMAT_VERSION = '1.3'

try:
    import jsonschema
    from jsonschema import Draft202012Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    Draft202012Validator = None

logger = logging.getLogger(__name__)

# Schema directory relative to this file
SCHEMA_DIR = Path(__file__).parent.parent.parent.parent / 'schemas'

# Schema file mapping
SCHEMA_FILES = {
    'codex': 'codex-v1.3.schema.json',
    'analysis': 'analysis-v1.3.schema.json',
}


class SchemaValidator:
    """
    Centralized schema validator for the Codex format.

    Caches loaded schemas for performance.
    """

    def __init__(self, schema_dir: Path = None):
        """
        Initialize validator with optional custom schema directory.

        Args:
            schema_dir: Path to directory containing schema files.
                       Defaults to ../../../schemas relative to this file.
        """
        self.schema_dir = schema_dir or SCHEMA_DIR
        self._schema_cache: Dict[str, dict] = {}
        self._validator_cache: Dict[str, Any] = {}

    def load_schema(self, schema_type: str) -> Optional[dict]:
        """
        Load a schema by type name.

        Args:
            schema_type: One of 'codex' or 'analysis'

        Returns:
            Schema dict or None if not found
        """
        if schema_type in self._schema_cache:
            return self._schema_cache[schema_type]

        filename = SCHEMA_FILES.get(schema_type)
        if not filename:
            logger.warning(f"Unknown schema type: {schema_type}")
            return None

        schema_path = self.schema_dir / filename
        if not schema_path.exists():
            logger.warning(f"Schema file not found: {schema_path}")
            return None

        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            self._schema_cache[schema_type] = schema
            return schema
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in schema {schema_path}: {e}")
            return None

    def get_validator(self, schema_type: str) -> Optional[Any]:
        """
        Get a jsonschema validator for the given schema type.

        Args:
            schema_type: One of 'codex' or 'analysis'

        Returns:
            Draft202012Validator instance or None
        """
        if not HAS_JSONSCHEMA:
            logger.warning("jsonschema not installed, validation disabled")
            return None

        if schema_type in self._validator_cache:
            return self._validator_cache[schema_type]

        schema = self.load_schema(schema_type)
        if schema is None:
            return None

        validator = Draft202012Validator(schema)
        self._validator_cache[schema_type] = validator
        return validator

    def validate(self, data: dict, schema_type: str) -> Tuple[bool, List[str]]:
        """
        Validate data against a schema.

        Args:
            data: Data to validate
            schema_type: One of 'codex' or 'analysis'

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        if not HAS_JSONSCHEMA:
            # No validation library, assume valid
            return True, []

        validator = self.get_validator(schema_type)
        if validator is None:
            # Schema not found, skip validation
            return True, []

        errors = list(validator.iter_errors(data))

        if not errors:
            return True, []

        # Format error messages with path
        error_msgs = []
        for err in errors[:10]:  # Limit to 10 errors
            path = '.'.join(str(p) for p in err.absolute_path) or 'root'
            error_msgs.append(f"{path}: {err.message}")

        return False, error_msgs


# Module-level singleton for convenience
_default_validator = None


def _get_validator() -> SchemaValidator:
    """Get or create default validator instance."""
    global _default_validator
    if _default_validator is None:
        _default_validator = SchemaValidator()
    return _default_validator


def validate_codex(data: dict) -> Tuple[bool, List[str]]:
    """
    Validate codex data against the Codex V1.3 schema.

    Args:
        data: Parsed codex content (dict)

    Returns:
        Tuple of (is_valid, list_of_error_messages)

    Example:
        is_valid, errors = validate_codex(yaml.safe_load(content))
        if not is_valid:
            for error in errors:
                print(f"  - {error}")
    """
    return _get_validator().validate(data, 'codex')


def validate_analysis(data: dict) -> Tuple[bool, List[str]]:
    """
    Validate analysis data against the Analysis V1.3 schema.

    Args:
        data: Parsed analysis content (dict)

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    return _get_validator().validate(data, 'analysis')


def validate_codex_file(file_path: Path) -> Tuple[bool, List[str]]:
    """
    Load and validate a codex file.

    Args:
        file_path: Path to .codex.yaml or .codex.json file

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    import yaml

    file_path = Path(file_path)

    if not file_path.exists():
        return False, [f"File not found: {file_path}"]

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix == '.json':
                data = json.load(f)
            else:
                data = yaml.safe_load(f)
    except Exception as e:
        return False, [f"Parse error: {e}"]

    return validate_codex(data)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: schema_validator.py <file.codex.yaml>")
        print("       schema_validator.py --test")
        sys.exit(1)

    if sys.argv[1] == '--test':
        # Quick self-test
        print("Testing schema validator...")

        # Test codex validation
        valid_codex = {'metadata': {'formatVersion': CURRENT_FORMAT_VERSION}}
        is_valid, errors = validate_codex(valid_codex)
        print(f"Valid codex: {is_valid} (expected: True)")

        invalid_codex = {'id': 'test'}  # Missing metadata
        is_valid, errors = validate_codex(invalid_codex)
        print(f"Invalid codex: {is_valid} (expected: False)")
        print(f"  Errors: {errors}")

        print("Self-test complete!")
    else:
        # Validate a file
        file_path = Path(sys.argv[1])
        is_valid, errors = validate_codex_file(file_path)

        if is_valid:
            print(f"✅ {file_path} is valid")
        else:
            print(f"❌ {file_path} has validation errors:")
            for error in errors:
                print(f"  - {error}")

        sys.exit(0 if is_valid else 1)
