#!/usr/bin/env python3
"""
Auto-Fix Service for Codex Integrity Issues
Automatically repairs common integrity problems in codex files.

This service can be used:
1. As a library service (imported by the app)
2. As a command-line tool (run standalone)

Command-line usage:
    python auto_fixer.py <file_or_directory> [--recursive] [--dry-run] [--verbose]

Examples:
    # Fix a single file
    python auto_fixer.py /path/to/file.codex.yaml

    # Fix all files in a directory recursively
    python auto_fixer.py /path/to/directory --recursive

    # Dry run (show what would be fixed without making changes)
    python auto_fixer.py /path/to/file.codex.yaml --dry-run
"""

import uuid
import re
import os
import sys
import logging
import argparse
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from pathlib import Path

# Schema validation (optional, for --validate flag)
try:
    from schema_validator import validate_codex
    HAS_SCHEMA_VALIDATOR = True
except ImportError:
    HAS_SCHEMA_VALIDATOR = False
    validate_codex = None

logger = logging.getLogger(__name__)

# Codex format version constants (single source of truth).
try:
    from codex_version import CURRENT_FORMAT_VERSION, SUPPORTED_FORMAT_VERSIONS
except ImportError:  # standalone execution outside the scripts directory
    CURRENT_FORMAT_VERSION = '1.3'
    SUPPORTED_FORMAT_VERSIONS = ['1.0', '1.1', '1.2', '1.3']


class CodexAutoFixer:
    """
    Service to automatically fix common integrity issues in Codex files.
    Spec: https://chapterwise.app/docs/codex/format/codex-format
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.fixes_applied = []
        self.used_ids = set()
        self.regenerate_all_ids = False

    def auto_fix_codex(self, codex, parsed_content: Dict[Any, Any] = None, regenerate_all_ids: bool = False) -> Tuple[Dict[Any, Any], List[str]]:
        """
        Automatically fix common integrity issues in Codex content.

        Args:
            codex: Codex model instance (or None for standalone mode)
            parsed_content: Parsed codex content (optional - will read from file if None)
            regenerate_all_ids: If True, regenerate ALL IDs even if they're valid

        Returns:
            Tuple of (fixed_content, list_of_fixes_applied)
        """
        self.fixes_applied = []
        self.used_ids = set()
        self.regenerate_all_ids = regenerate_all_ids

        try:
            # If no parsed content provided, try to read and fix the file
            if parsed_content is None:
                parsed_content = self._attempt_file_recovery(codex)
                if parsed_content is None:
                    return None, self.fixes_applied

            # Make a deep copy to avoid modifying the original
            import copy
            fixed_content = copy.deepcopy(parsed_content)

            # Collect existing valid IDs first (unless regenerating all)
            if not regenerate_all_ids:
                self._collect_valid_ids(fixed_content)

            # Apply format fixes
            fixed_content = self._ensure_v1_metadata(fixed_content)
            fixed_content = self._remove_legacy_fields(fixed_content)
            fixed_content = self._fix_missing_node_fields(fixed_content)

            # Regenerate all IDs if requested, otherwise just fix invalid ones
            if regenerate_all_ids:
                fixed_content = self._regenerate_all_ids(fixed_content)
            else:
                fixed_content = self._fix_invalid_uuids(fixed_content)
                fixed_content = self._fix_duplicate_ids(fixed_content)

            fixed_content = self._fix_invalid_attribute_structure(fixed_content)
            fixed_content = self._fix_invalid_relation_structure(fixed_content)
            fixed_content = self._clean_empty_names(fixed_content)
            fixed_content = self._convert_long_strings_to_pipe(fixed_content)
            fixed_content = self._auto_calculate_timecodes(fixed_content)
            fixed_content = self._quote_time_patterns(fixed_content)

            codex_id = getattr(codex, 'id', 'standalone') if codex else 'standalone'
            self.logger.info(f"Applied {len(self.fixes_applied)} auto-fixes to codex {codex_id}")

            return fixed_content, self.fixes_applied

        except Exception as e:
            self.logger.error(f"Error during auto-fix: {e}", exc_info=True)
            return parsed_content if parsed_content else None, []

    def _collect_valid_ids(self, data: Any, path: str = "") -> None:
        """Collect all valid UUIDs to avoid duplicates when generating new ones."""
        if isinstance(data, dict):
            if 'id' in data:
                node_id = data['id']
                if self._is_valid_uuid(str(node_id)):
                    self.used_ids.add(node_id)

            for key, value in data.items():
                self._collect_valid_ids(value, f"{path}.{key}" if path else key)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._collect_valid_ids(item, f"{path}[{i}]")

    def _ensure_v1_metadata(self, content: Dict[Any, Any]) -> Dict[Any, Any]:
        """
        Ensure the metadata section exists and is properly formatted.

        Format Requirements:
        - Must have 'metadata' object at root
        - metadata.formatVersion must be a known version; missing or unknown
          values are set to CURRENT_FORMAT_VERSION. A document already
          declaring a known version is never rewritten — the auto-fixer
          repairs integrity, it does not migrate documents between versions.
        - metadata.documentVersion recommended (defaults to "1.0.0")

        Args:
            content: Parsed codex content

        Returns:
            Content with proper metadata
        """
        # Ensure metadata object exists
        if 'metadata' not in content:
            content['metadata'] = {}
            self.fixes_applied.append("Added missing 'metadata' section")

        if not isinstance(content['metadata'], dict):
            content['metadata'] = {}
            self.fixes_applied.append("Fixed invalid metadata structure")

        # Stamp the current spec version when absent. Documents that already
        # declare a supported version are left alone — including older ones,
        # which stay valid (see chapterwise.app/docs/codex/format).
        if 'formatVersion' not in content['metadata']:
            content['metadata']['formatVersion'] = CURRENT_FORMAT_VERSION
            self.fixes_applied.append(f"Added metadata.formatVersion = '{CURRENT_FORMAT_VERSION}'")
        elif content['metadata']['formatVersion'] not in SUPPORTED_FORMAT_VERSIONS:
            old_version = content['metadata']['formatVersion']
            content['metadata']['formatVersion'] = CURRENT_FORMAT_VERSION
            self.fixes_applied.append(
                f"Updated metadata.formatVersion from '{old_version}' to '{CURRENT_FORMAT_VERSION}'"
            )

        # Ensure documentVersion exists (if not present, initialize to 1.0.0)
        # NOTE: Never overwrite existing documentVersion - that's managed by versioning system
        if 'documentVersion' not in content['metadata']:
            content['metadata']['documentVersion'] = '1.0.0'
            self.fixes_applied.append("Added metadata.documentVersion = '1.0.0'")
            self.logger.info("Initialized documentVersion to 1.0.0 (field was missing)")
        else:
            self.logger.debug(f"Preserving existing documentVersion: {content['metadata'].get('documentVersion')}")

        return content

    def _remove_legacy_fields(self, content: Dict[Any, Any]) -> Dict[Any, Any]:
        """
        Remove legacy fields that don't belong in the current format.

        Legacy fields to remove:
        - packetType (V0.9 field)
        - version (V0.9 field, now in metadata.formatVersion)
        - codexId (V0.9 field, use node-level 'id' instead)
        - codexVersion (V0.9 field, now metadata.documentVersion)
        - data (V0.9 wrapper, should already be unwrapped by migration)

        Args:
            content: Parsed codex content

        Returns:
            Content with legacy fields removed
        """
        legacy_fields_removed = []

        # Remove top-level legacy fields
        if 'packetType' in content:
            del content['packetType']
            legacy_fields_removed.append('packetType')

        if 'version' in content and 'metadata' in content:
            # Only remove if metadata exists (meaning we're in a versioned document)
            del content['version']
            legacy_fields_removed.append('version')

        if 'codexId' in content:
            # We use node-level 'id' not root-level 'codexId'
            # If there's no 'id', migrate codexId to id
            if 'id' not in content and content['codexId']:
                content['id'] = content['codexId']
                legacy_fields_removed.append('codexId (migrated to id)')
            else:
                legacy_fields_removed.append('codexId')
            del content['codexId']

        if 'codexVersion' in content:
            # If metadata.documentVersion doesn't exist, migrate it
            if 'metadata' in content and 'documentVersion' not in content['metadata']:
                content['metadata']['documentVersion'] = content['codexVersion']
                legacy_fields_removed.append('codexVersion (migrated to metadata.documentVersion)')
            else:
                legacy_fields_removed.append('codexVersion')
            del content['codexVersion']

        if 'data' in content:
            # This shouldn't happen if migration was run, but handle it
            self.logger.warning("Found 'data' wrapper in content - this should have been migrated!")
            legacy_fields_removed.append('data (WARNING: should have been migrated first!)')

        if legacy_fields_removed:
            self.fixes_applied.append(f"Removed legacy fields: {', '.join(legacy_fields_removed)}")
            self.logger.info(f"Removed legacy fields: {', '.join(legacy_fields_removed)}")

        return content

    def _fix_missing_node_fields(self, content: Dict[Any, Any]) -> Dict[Any, Any]:
        """
        Fix missing required node fields.

        Nodes should have:
        - id: unique identifier (UUID recommended)
        - type: node classification
        - name or title: human-readable identifier

        Args:
            content: Parsed codex content

        Returns:
            Content with fixed node fields
        """

        def fix_entity_fields_recursive(data: Any, path: str = "") -> Any:
            if isinstance(data, dict):
                # Check if this looks like a node (has some node-like fields)
                if any(key in data for key in ['id', 'type', 'name', 'title', 'attributes', 'children']):
                    # Fix missing id
                    if 'id' not in data:
                        data['id'] = self._generate_new_uuid()
                        self.fixes_applied.append(f"Added missing 'id' field at {path}")

                    # Fix missing type (optional, but good practice)
                    if 'type' not in data and path:  # Don't add type to root
                        data['type'] = 'node'
                        self.fixes_applied.append(f"Added missing 'type' field at {path}")

                    # Fix missing name/title
                    if 'name' not in data and 'title' not in data and path:  # Don't require at root
                        data['name'] = 'Untitled'
                        self.fixes_applied.append(f"Added missing 'name' field at {path}")

                # Recursively process nested structures
                for key, value in data.items():
                    data[key] = fix_entity_fields_recursive(value, f"{path}.{key}" if path else key)

            elif isinstance(data, list):
                for i, item in enumerate(data):
                    data[i] = fix_entity_fields_recursive(item, f"{path}[{i}]")

            return data

        return fix_entity_fields_recursive(content)

    def _fix_invalid_uuids(self, content: Dict[Any, Any]) -> Dict[Any, Any]:
        """Fix invalid UUID formats throughout the codex."""

        def fix_uuids_recursive(data: Any, path: str = "") -> Any:
            if isinstance(data, dict):
                # Fix node IDs
                if 'id' in data:
                    old_id = data['id']
                    if not self._is_valid_uuid(str(old_id)):
                        new_id = self._fix_uuid_format(str(old_id))
                        data['id'] = new_id
                        self.fixes_applied.append(f"Fixed invalid UUID at {path}.id: '{old_id}' → '{new_id}'")

                # Fix relation targetIds
                if 'relations' in data and isinstance(data['relations'], list):
                    for i, relation in enumerate(data['relations']):
                        if isinstance(relation, dict) and 'targetId' in relation:
                            old_target_id = relation['targetId']
                            if not self._is_valid_uuid(str(old_target_id)):
                                new_target_id = self._fix_uuid_format(str(old_target_id))
                                relation['targetId'] = new_target_id
                                self.fixes_applied.append(f"Fixed invalid targetId at {path}.relations[{i}].targetId: '{old_target_id}' → '{new_target_id}'")

                # Recursively process nested structures
                for key, value in data.items():
                    data[key] = fix_uuids_recursive(value, f"{path}.{key}" if path else key)

            elif isinstance(data, list):
                for i, item in enumerate(data):
                    data[i] = fix_uuids_recursive(item, f"{path}[{i}]")

            return data

        return fix_uuids_recursive(content)

    def _fix_uuid_format(self, invalid_uuid: str) -> str:
        """
        Fix common UUID format issues.

        Args:
            invalid_uuid: The invalid UUID string

        Returns:
            A valid UUID v4 string
        """
        # Remove common suffixes like "-1", "-2", etc.
        cleaned_uuid = re.sub(r'-\d+$', '', invalid_uuid)

        # Check if the cleaned version is a valid UUID
        if self._is_valid_uuid(cleaned_uuid):
            # Make sure it's unique
            if cleaned_uuid not in self.used_ids:
                self.used_ids.add(cleaned_uuid)
                return cleaned_uuid

        # If we can't salvage the UUID, generate a new one
        return self._generate_new_uuid()

    def _fix_duplicate_ids(self, content: Dict[Any, Any]) -> Dict[Any, Any]:
        """Fix duplicate node IDs."""
        seen_ids = set()

        def fix_duplicates_recursive(data: Any, path: str = "") -> Any:
            if isinstance(data, dict):
                if 'id' in data:
                    entity_id = data['id']
                    if entity_id in seen_ids:
                        new_id = self._generate_new_uuid()
                        data['id'] = new_id
                        self.fixes_applied.append(f"Fixed duplicate ID at {path}.id: '{entity_id}' → '{new_id}'")
                    else:
                        seen_ids.add(entity_id)

                for key, value in data.items():
                    data[key] = fix_duplicates_recursive(value, f"{path}.{key}" if path else key)

            elif isinstance(data, list):
                for i, item in enumerate(data):
                    data[i] = fix_duplicates_recursive(item, f"{path}[{i}]")

            return data

        return fix_duplicates_recursive(content)

    def _regenerate_all_ids(self, content: Dict[Any, Any]) -> Dict[Any, Any]:
        """
        Regenerate ALL IDs in the document, even if they're valid.
        Useful for ensuring completely fresh IDs when importing or duplicating content.
        """
        id_count = 0

        def regenerate_ids_recursive(data: Any, path: str = "") -> Any:
            nonlocal id_count

            if isinstance(data, dict):
                # Regenerate node ID if present
                if 'id' in data:
                    old_id = data['id']
                    new_id = self._generate_new_uuid()
                    data['id'] = new_id
                    id_count += 1
                    self.fixes_applied.append(f"Regenerated ID at {path}.id: '{old_id}' → '{new_id}'")

                # Regenerate relation targetIds
                if 'relations' in data and isinstance(data['relations'], list):
                    for i, relation in enumerate(data['relations']):
                        if isinstance(relation, dict) and 'targetId' in relation:
                            old_target_id = relation['targetId']
                            new_target_id = self._generate_new_uuid()
                            relation['targetId'] = new_target_id
                            id_count += 1
                            self.fixes_applied.append(f"Regenerated targetId at {path}.relations[{i}].targetId: '{old_target_id}' → '{new_target_id}'")

                # Recursively process nested structures
                for key, value in data.items():
                    data[key] = regenerate_ids_recursive(value, f"{path}.{key}" if path else key)

            elif isinstance(data, list):
                for i, item in enumerate(data):
                    data[i] = regenerate_ids_recursive(item, f"{path}[{i}]")

            return data

        result = regenerate_ids_recursive(content)
        self.logger.info(f"Regenerated {id_count} IDs throughout the document")
        return result

    def _fix_invalid_attribute_structure(self, content: Dict[Any, Any]) -> Dict[Any, Any]:
        """Fix invalid attribute structures."""

        def fix_attributes_recursive(data: Any, path: str = "") -> Any:
            if isinstance(data, dict):
                if 'attributes' in data and isinstance(data['attributes'], list):
                    fixed_attributes = []
                    for i, attr in enumerate(data['attributes']):
                        if isinstance(attr, dict):
                            # Fix missing key
                            if 'key' not in attr:
                                attr['key'] = f'attribute_{i}'
                                self.fixes_applied.append(f"Added missing 'key' field to attribute at {path}.attributes[{i}]")

                            # Fix missing value
                            if 'value' not in attr:
                                attr['value'] = ''
                                self.fixes_applied.append(f"Added missing 'value' field to attribute at {path}.attributes[{i}]")

                            # Fix invalid key format
                            if 'key' in attr and not re.match(r'^[a-z][a-z0-9_-]*$', str(attr['key'])):
                                old_key = attr['key']
                                new_key = self._sanitize_attribute_key(str(old_key))
                                attr['key'] = new_key
                                self.fixes_applied.append(f"Fixed invalid attribute key at {path}.attributes[{i}]: '{old_key}' → '{new_key}'")

                            fixed_attributes.append(attr)
                        else:
                            # Skip invalid attribute structures
                            self.fixes_applied.append(f"Removed invalid attribute structure at {path}.attributes[{i}]")

                    data['attributes'] = fixed_attributes

                # Recursively process nested structures
                for key, value in data.items():
                    data[key] = fix_attributes_recursive(value, f"{path}.{key}" if path else key)

            elif isinstance(data, list):
                for i, item in enumerate(data):
                    data[i] = fix_attributes_recursive(item, f"{path}[{i}]")

            return data

        return fix_attributes_recursive(content)

    def _fix_invalid_relation_structure(self, content: Dict[Any, Any]) -> Dict[Any, Any]:
        """Fix invalid relation structures."""

        def fix_relations_recursive(data: Any, path: str = "") -> Any:
            if isinstance(data, dict):
                if 'relations' in data and isinstance(data['relations'], list):
                    fixed_relations = []
                    for i, relation in enumerate(data['relations']):
                        if isinstance(relation, dict):
                            # Fix missing targetId
                            if 'targetId' not in relation:
                                relation['targetId'] = self._generate_new_uuid()
                                self.fixes_applied.append(f"Added missing 'targetId' field to relation at {path}.relations[{i}]")

                            # Fix missing kind (spec uses 'type', but 'kind' is legacy compatibility)
                            if 'kind' not in relation and 'type' not in relation:
                                relation['type'] = 'related-to'
                                self.fixes_applied.append(f"Added missing 'type' field to relation at {path}.relations[{i}]")

                            fixed_relations.append(relation)
                        else:
                            # Skip invalid relation structures
                            self.fixes_applied.append(f"Removed invalid relation structure at {path}.relations[{i}]")

                    data['relations'] = fixed_relations

                # Recursively process nested structures
                for key, value in data.items():
                    data[key] = fix_relations_recursive(value, f"{path}.{key}" if path else key)

            elif isinstance(data, list):
                for i, item in enumerate(data):
                    data[i] = fix_relations_recursive(item, f"{path}[{i}]")

            return data

        return fix_relations_recursive(content)

    def _clean_empty_names(self, content: Dict[Any, Any]) -> Dict[Any, Any]:
        """Fix empty or whitespace-only names."""

        def fix_names_recursive(data: Any, path: str = "") -> Any:
            if isinstance(data, dict):
                if 'name' in data:
                    name = data['name']
                    if not name or not str(name).strip():
                        data['name'] = 'Untitled'
                        self.fixes_applied.append(f"Fixed empty name at {path}.name")

                # Recursively process nested structures
                for key, value in data.items():
                    data[key] = fix_names_recursive(value, f"{path}.{key}" if path else key)

            elif isinstance(data, list):
                for i, item in enumerate(data):
                    data[i] = fix_names_recursive(item, f"{path}[{i}]")

            return data

        return fix_names_recursive(content)

    def _convert_long_strings_to_pipe(self, content: Dict[Any, Any]) -> Dict[Any, Any]:
        """
        Convert long strings to use YAML pipe syntax (|) for better readability.
        Also strips leading/trailing whitespace and normalizes line endings.

        This applies to fields like:
        - body
        - description
        - summary (if multiline)
        - value (in content and attributes)

        Strings are converted if they:
        - Contain newlines OR
        - Are longer than 80 characters
        """
        string_fields_converted = 0

        def should_use_pipe_syntax(value: Any) -> bool:
            """Check if a string should use pipe syntax."""
            if not isinstance(value, str):
                return False

            # Already has newlines - definitely use pipe
            if '\n' in value:
                return True

            # Long single-line strings - use pipe if over 80 chars
            if len(value) > 80:
                return True

            return False

        def clean_string(value: str) -> str:
            """
            Clean string by:
            - Stripping leading/trailing whitespace
            - Removing extra blank lines at start/end
            - Normalizing line endings to \n
            - Removing trailing spaces on each line
            """
            # Normalize line endings (handle \r\n and \r)
            value = value.replace('\r\n', '\n').replace('\r', '\n')

            # Strip leading/trailing whitespace from entire string
            value = value.strip()

            # For multiline strings, clean each line
            if '\n' in value:
                lines = value.split('\n')
                # Strip trailing whitespace from each line but preserve leading indent
                cleaned_lines = [line.rstrip() for line in lines]
                value = '\n'.join(cleaned_lines)

                # Remove excessive blank lines at start/end
                value = value.strip('\n')

            return value

        def convert_strings_recursive(data: Any, path: str = "") -> Any:
            nonlocal string_fields_converted

            if isinstance(data, dict):
                # Fields that commonly contain long text
                text_fields = ['body', 'description', 'summary', 'value', 'text', 'content_text']

                for field in text_fields:
                    if field in data and should_use_pipe_syntax(data[field]):
                        old_value = data[field]
                        # Clean the string thoroughly
                        data[field] = clean_string(str(old_value))
                        string_fields_converted += 1

                        # Truncate long values in log
                        preview = data[field][:50] + "..." if len(data[field]) > 50 else data[field]
                        preview = preview.replace('\n', ' ')  # Single line for log
                        self.fixes_applied.append(f"Cleaned and converted {field} at {path} to pipe syntax: '{preview}'")

                # Recursively process nested structures
                for key, value in data.items():
                    data[key] = convert_strings_recursive(value, f"{path}.{key}" if path else key)

            elif isinstance(data, list):
                for i, item in enumerate(data):
                    data[i] = convert_strings_recursive(item, f"{path}[{i}]")

            return data

        result = convert_strings_recursive(content)

        if string_fields_converted > 0:
            self.logger.info(f"Cleaned and converted {string_fields_converted} string fields to use pipe syntax")

        return result

    def _generate_new_uuid(self) -> str:
        """Generate a new unique UUID v4."""
        while True:
            new_uuid = str(uuid.uuid4())
            if new_uuid not in self.used_ids:
                self.used_ids.add(new_uuid)
                return new_uuid

    def _is_valid_uuid(self, uuid_str: str) -> bool:
        """Check if string is a valid UUID v4."""
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, uuid_str.lower()))

    def _sanitize_attribute_key(self, key: str) -> str:
        """Sanitize attribute key to follow naming convention."""
        # Convert to lowercase and replace invalid characters
        sanitized = re.sub(r'[^a-z0-9_-]', '_', key.lower())

        # Ensure it starts with a letter
        if not sanitized or not sanitized[0].isalpha():
            sanitized = 'attr_' + sanitized

        # Remove consecutive underscores/hyphens
        sanitized = re.sub(r'[_-]+', '_', sanitized)

        # Trim to reasonable length
        if len(sanitized) > 50:
            sanitized = sanitized[:50].rstrip('_-')

        return sanitized or 'attribute'

    def _parse_duration_to_seconds(self, duration_str: str) -> int:
        """
        Parse duration string in format "HH:MM:SS", "MM:SS", or "SS" to total seconds.

        Examples:
            "01:00" -> 60 seconds
            "19:00" -> 1140 seconds
            "1:30:00" -> 5400 seconds

        Args:
            duration_str: Duration string to parse

        Returns:
            Total seconds as integer
        """
        try:
            if not isinstance(duration_str, str):
                return 0

            parts = duration_str.strip().split(':')

            if len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:  # MM:SS
                minutes, seconds = int(parts[0]), int(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 1:  # SS
                return int(parts[0])
            else:
                return 0
        except (ValueError, AttributeError):
            self.logger.warning(f"Could not parse duration: {duration_str}")
            return 0

    def _format_seconds_to_duration(self, total_seconds: int) -> str:
        """
        Convert total seconds to "HH:MM:SS" or "MM:SS" format.

        Examples:
            60 -> "01:00"
            1140 -> "19:00"
            3661 -> "01:01:01"

        Args:
            total_seconds: Total seconds as integer

        Returns:
            Formatted duration string
        """
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def _auto_calculate_timecodes(self, data: Dict[Any, Any]) -> Dict[Any, Any]:
        """
        Automatically calculate timecodes based on cumulative duration at each level.
        Timecodes accumulate continuously across the ENTIRE document at each depth level.

        For example:
        - Act 1 → Beat 0 (00:00), Beat 1 (01:00), Beat 2 (02:00), Beat 3 (03:00)
        - Act 2 → Beat 4 (04:00), Beat 5 (05:00), Beat 6 (06:00), Beat 7 (07:00)
        - Act 3 → Beat 8 (08:00), Beat 9 (09:00), etc.

        Args:
            data: Codex content dictionary

        Returns:
            Modified codex content with calculated timecodes
        """
        self.logger.info("Auto-calculating continuous timecodes across document at each depth level")

        # Track cumulative time at each depth level across the entire document
        depth_cumulatives = {}

        def traverse_and_calculate(node, depth=0):
            """
            Recursively traverse nodes and calculate timecodes.

            Args:
                node: Current node to process
                depth: Current depth level in the tree

            Returns:
                Duration of this node (in seconds)
            """
            if not isinstance(node, dict):
                return 0

            # Initialize cumulative for this depth if not exists
            if depth not in depth_cumulatives:
                depth_cumulatives[depth] = 0

            current_duration = 0

            # Check if this node has attributes
            if 'attributes' in node and isinstance(node['attributes'], list):
                attributes = node['attributes']

                # Look for duration and timecode attributes
                has_timecode = False
                timecode_index = None

                for i, attr in enumerate(attributes):
                    if isinstance(attr, dict):
                        if attr.get('key') == 'duration':
                            duration_value = attr.get('value', '00:00')
                            current_duration = self._parse_duration_to_seconds(duration_value)

                        if attr.get('key') == 'timecode':
                            has_timecode = True
                            timecode_index = i

                # Set timecode based on cumulative at THIS DEPTH across entire document
                if has_timecode and timecode_index is not None:
                    # Use the current cumulative for this depth BEFORE adding this node's duration
                    timecode_str = self._format_seconds_to_duration(depth_cumulatives[depth])
                    old_value = attributes[timecode_index].get('value', '')

                    # Only log if we're actually changing the value
                    # NOTE: Timecode values MUST be quoted strings in YAML to avoid sexagesimal parsing
                    # (e.g., '23:00' not 23:00, which YAML interprets as 1380 seconds)
                    if str(old_value) != timecode_str:
                        attributes[timecode_index]['value'] = timecode_str
                        self.fixes_applied.append(f"Auto-calculated timecode at depth {depth}: {timecode_str}")
                        self.logger.debug(f"Updated timecode from {old_value} to {timecode_str} (depth {depth})")
                    else:
                        # Ensure it's always a string (will be quoted by YAML dumper)
                        attributes[timecode_index]['value'] = timecode_str

                    # Add this node's duration to the cumulative for this depth
                    depth_cumulatives[depth] += current_duration

            # Process children at the next depth level
            if 'children' in node and isinstance(node['children'], list):
                for child in node['children']:
                    traverse_and_calculate(child, depth + 1)

            return current_duration

        # Start traversal from root level
        # Process the document itself (depth 0)
        traverse_and_calculate(data, depth=0)

        return data

    def _quote_time_patterns(self, content: Dict[Any, Any]) -> Dict[Any, Any]:
        """
        Detect time-pattern strings in attributes and ensure they're quoted.
        This prevents YAML sexagesimal parsing (e.g., 36:00 → 2160).

        Also converts integer values that look like parsed time values back to time format.

        Args:
            content: Codex content dictionary

        Returns:
            Modified codex content with time patterns quoted
        """
        import re
        time_pattern = re.compile(r'^\d{1,2}:\d{2}(:\d{2})?(\.\d+)?$')

        def check_time_patterns(data: Any, path: str = "") -> Any:
            if isinstance(data, dict):
                # Check attributes for time patterns
                if 'attributes' in data and isinstance(data['attributes'], list):
                    for i, attr in enumerate(data['attributes']):
                        if isinstance(attr, dict):
                            key = attr.get('key', '')
                            value = attr.get('value')

                            # Check for time pattern in value
                            if isinstance(value, str) and time_pattern.match(value):
                                # Already a string, will be quoted by dumper
                                # Log only if it's a common time attribute
                                if key in ['timecode', 'duration', 'time', 'timestamp']:
                                    self.fixes_applied.append(
                                        f"Detected time pattern in {key}: '{value}' (will be quoted)"
                                    )

                            # Check if value is an integer that might have been parsed from time
                            elif isinstance(value, int) and value >= 60 and value % 60 == 0:
                                if key in ['timecode', 'duration']:
                                    # Convert back to time format
                                    minutes = value // 60
                                    seconds = value % 60
                                    new_value = f"{minutes:02d}:{seconds:02d}"
                                    attr['value'] = new_value
                                    self.fixes_applied.append(
                                        f"Converted {key} from {value} back to time: {new_value}"
                                    )

                # Recurse
                if 'children' in data and isinstance(data['children'], list):
                    for child in data['children']:
                        check_time_patterns(child, f"{path}.children")

            return data

        return check_time_patterns(content)

    def write_fixed_codex(self, codex, fixed_content: Dict[Any, Any], file_path: str = None) -> None:
        """
        Write the fixed codex content back to the file.

        Works in both web app and CLI contexts:
        - Web app: Uses versioning system and database commits
        - CLI: Falls back to direct file writing

        Args:
            codex: Codex model instance (can be None in CLI mode)
            fixed_content: Fixed codex content
            file_path: Optional file path for CLI mode (required if codex is None)
        """
        try:
            # Try web app imports first
            from app.services.version_service import CodexVersionService
            from app.services.codex_file_manager import CodexFileManager
            from app import db

            # Web app mode - use versioning system
            self.logger.info("Using web app mode with versioning")

            # Create a version backup before applying auto-fix
            version_service = CodexVersionService()

            # Create description of fixes applied
            fix_description = f"Auto-fix applied: {len(self.fixes_applied)} issues resolved"
            if self.fixes_applied:
                # Include first few fix descriptions
                fix_summary = "; ".join(self.fixes_applied[:3])
                if len(self.fixes_applied) > 3:
                    fix_summary += f" (and {len(self.fixes_applied) - 3} more)"
                fix_description = f"Auto-fix: {fix_summary}"

            # Save current version as backup before auto-fix
            backup_result = version_service.save_current_version(
                codex,
                fix_description,
                version_type='patch'
            )

            if backup_result['success']:
                self.logger.info(f"Created version backup {backup_result['version_number']} before auto-fix for codex {codex.id}")
            else:
                self.logger.warning(f"Failed to create version backup before auto-fix: {backup_result.get('error', 'Unknown error')}")

            # Write the fixed content
            file_manager = CodexFileManager()
            file_manager.write_codex_content(codex, fixed_content)

            # Update file metadata to reflect the fix
            if codex.file_metadata:
                codex.file_metadata['last_auto_fix'] = datetime.utcnow().isoformat()
                codex.file_metadata['fixes_applied'] = len(self.fixes_applied)
                if backup_result['success']:
                    codex.file_metadata['auto_fix_backup_version'] = backup_result['version_number']

            db.session.commit()

            self.logger.info(f"Successfully wrote auto-fixed codex data for {codex.id}")

        except ImportError:
            # CLI mode - fall back to direct file writing
            import yaml

            self.logger.info("Web app not available, using CLI mode for file writing")

            # Determine file path
            output_path = file_path
            if not output_path and codex:
                # Try to get file path from codex object
                output_path = getattr(codex, 'file_path', None) or (
                    codex.get_file_path() if hasattr(codex, 'get_file_path') else None
                )

            if not output_path:
                raise ValueError("No file path available for writing. Provide file_path parameter in CLI mode.")

            # Custom YAML representer for multiline strings
            def str_representer(dumper, data):
                """Custom representer that uses pipe syntax for multiline strings."""
                if '\n' in data or len(data) > 80:
                    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
                return dumper.represent_scalar('tag:yaml.org,2002:str', data)

            yaml.add_representer(str, str_representer)

            # Write fixed content directly to file
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(fixed_content, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)

            self.logger.info(f"Successfully wrote auto-fixed codex data to {output_path} (CLI mode)")

        except Exception as e:
            self.logger.error(f"Error writing auto-fixed codex data: {e}", exc_info=True)
            raise

    def _attempt_file_recovery(self, codex) -> Optional[Dict[Any, Any]]:
        """
        Attempt to recover and fix malformed JSON/YAML files.

        Args:
            codex: Codex model instance

        Returns:
            Parsed content if recovery successful, None otherwise
        """
        try:
            file_path = codex.get_file_path() if codex else None

            if not file_path or not os.path.exists(file_path):
                self.fixes_applied.append("File not found - cannot recover")
                return None

            # Read raw content
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()

            if not raw_content.strip():
                self.fixes_applied.append("File is empty - cannot recover")
                return None

            # Determine file type
            file_type = getattr(codex, 'file_type', 'yaml') if codex else 'yaml'

            # Try normal parsing first
            try:
                if file_type == 'yaml':
                    import yaml
                    return yaml.safe_load(raw_content)
                else:
                    import json
                    return json.loads(raw_content)
            except Exception:
                # Normal parsing failed, try recovery
                pass

            # Attempt recovery based on file type
            if file_type == 'yaml':
                return self._recover_yaml_syntax(raw_content)
            else:
                return self._recover_json_syntax(raw_content)

        except Exception as e:
            self.logger.error(f"Error during file recovery: {e}")
            self.fixes_applied.append(f"File recovery failed: {str(e)}")
            return None

    def _recover_json_syntax(self, raw_content: str) -> Optional[Dict[Any, Any]]:
        """
        Attempt to recover malformed JSON.

        Args:
            raw_content: Raw file content

        Returns:
            Parsed JSON if recovery successful
        """
        import json
        import re

        try:
            # Common JSON fixes
            fixed_content = raw_content

            # Fix missing quotes around property names
            fixed_content = re.sub(r'(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', fixed_content)
            self.fixes_applied.append("Fixed unquoted JSON property names")

            # Fix trailing commas
            fixed_content = re.sub(r',(\s*[}\]])', r'\1', fixed_content)
            self.fixes_applied.append("Removed trailing commas in JSON")

            # Fix single quotes to double quotes
            if "'" in fixed_content and '"' not in fixed_content:
                fixed_content = fixed_content.replace("'", '"')
                self.fixes_applied.append("Converted single quotes to double quotes")

            # Try to fix missing closing brackets/braces
            open_braces = fixed_content.count('{')
            close_braces = fixed_content.count('}')
            open_brackets = fixed_content.count('[')
            close_brackets = fixed_content.count(']')

            if open_braces > close_braces:
                fixed_content += '}' * (open_braces - close_braces)
                self.fixes_applied.append(f"Added {open_braces - close_braces} missing closing braces")

            if open_brackets > close_brackets:
                fixed_content += ']' * (open_brackets - close_brackets)
                self.fixes_applied.append(f"Added {open_brackets - close_brackets} missing closing brackets")

            # Try parsing the fixed content
            try:
                return json.loads(fixed_content)
            except json.JSONDecodeError as e:
                # If still failing, try more aggressive fixes
                return self._aggressive_json_recovery(fixed_content)

        except Exception as e:
            self.logger.error(f"JSON recovery failed: {e}")
            return None

    def _aggressive_json_recovery(self, content: str) -> Optional[Dict[Any, Any]]:
        """
        Aggressive JSON recovery for severely malformed files.
        """
        import json

        try:
            # Create a minimal valid codex structure
            recovered_data = {
                "metadata": {
                    "formatVersion": CURRENT_FORMAT_VERSION,
                    "documentVersion": "1.0.0"
                },
                "id": self._generate_new_uuid(),
                "type": "node",
                "name": "Recovered Node",
                "attributes": []
            }

            self.fixes_applied.append("Created minimal valid codex structure from corrupted file")
            return recovered_data

        except Exception:
            return None

    def _recover_yaml_syntax(self, raw_content: str) -> Optional[Dict[Any, Any]]:
        """
        Attempt to recover malformed YAML.

        Args:
            raw_content: Raw file content

        Returns:
            Parsed YAML if recovery successful
        """
        import yaml
        import re

        try:
            fixed_content = raw_content

            # Fix common YAML indentation issues
            lines = fixed_content.split('\n')
            fixed_lines = []

            for line in lines:
                # Fix tabs to spaces
                if '\t' in line:
                    line = line.replace('\t', '  ')
                    if line not in fixed_lines:  # Avoid duplicate messages
                        self.fixes_applied.append("Converted tabs to spaces in YAML")

                # Fix inconsistent indentation (basic attempt)
                if line.strip() and not line.startswith(' ') and ':' in line and not line.startswith('#'):
                    # This might be a root-level key, ensure it's not indented
                    line = line.lstrip()

                fixed_lines.append(line)

            fixed_content = '\n'.join(fixed_lines)

            # Fix missing colons after keys
            fixed_content = re.sub(r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*$', r'\1\2:', fixed_content, flags=re.MULTILINE)

            # Try parsing the fixed content
            try:
                return yaml.safe_load(fixed_content)
            except yaml.YAMLError as e:
                # If still failing, try more aggressive fixes
                return self._aggressive_yaml_recovery(fixed_content)

        except Exception as e:
            self.logger.error(f"YAML recovery failed: {e}")
            return None

    def _aggressive_yaml_recovery(self, content: str) -> Optional[Dict[Any, Any]]:
        """
        Aggressive YAML recovery for severely malformed files.
        """
        try:
            # Create a minimal valid codex structure
            recovered_data = {
                "metadata": {
                    "formatVersion": CURRENT_FORMAT_VERSION,
                    "documentVersion": "1.0.0"
                },
                "id": self._generate_new_uuid(),
                "type": "node",
                "name": "Recovered Node",
                "attributes": []
            }

            self.fixes_applied.append("Created minimal valid codex structure from corrupted YAML file")
            return recovered_data

        except Exception:
            return None


# ============================================================================
# Codex Lite (Markdown) Auto-Fixer
# ============================================================================

class CodexLiteFixer:
    """
    Auto-fixer for Codex Lite (Markdown) files with YAML frontmatter.
    Spec: https://chapterwise.app/docs/codex/format/codex-format
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.fixes_applied = []

    def auto_fix_codex_lite(self, text: str, file_name: str = None) -> Tuple[str, List[str]]:
        """
        Auto-fix a Codex Lite (Markdown) document.

        Args:
            text: Raw markdown text with YAML frontmatter
            file_name: Optional filename for extracting name fallback

        Returns:
            Tuple of (fixed_text, list_of_fixes_applied)
        """
        self.fixes_applied = []

        try:
            frontmatter, body = self._extract_frontmatter(text)

            # Fix missing name
            if 'name' not in frontmatter and 'title' not in frontmatter:
                h1 = self._extract_h1_from_markdown(body)
                if h1:
                    frontmatter['name'] = h1
                    self.fixes_applied.append(f"Added missing 'name' from H1: '{h1}'")
                elif file_name:
                    name_from_file = Path(file_name).stem
                    if name_from_file.endswith('.codex'):
                        name_from_file = name_from_file[:-6]
                    frontmatter['name'] = name_from_file
                    self.fixes_applied.append(f"Added missing 'name' from filename: '{name_from_file}'")
                else:
                    frontmatter['name'] = 'Untitled'
                    self.fixes_applied.append("Added missing 'name' with default: 'Untitled'")

            # Fix missing or invalid ID
            if 'id' not in frontmatter or not isinstance(frontmatter.get('id'), str):
                frontmatter['id'] = str(uuid.uuid4())
                self.fixes_applied.append(f"Added missing 'id': '{frontmatter['id']}'")
            elif not self._is_valid_uuid(frontmatter['id']):
                old_id = frontmatter['id']
                frontmatter['id'] = str(uuid.uuid4())
                self.fixes_applied.append(f"Fixed invalid UUID format: '{old_id}' → '{frontmatter['id']}'")

            # Ensure type field exists
            if 'type' not in frontmatter or not isinstance(frontmatter.get('type'), str):
                frontmatter['type'] = 'document'
                self.fixes_applied.append("Added missing 'type' field: 'document'")

            # Update word count
            word_count = self._count_words(body)
            old_word_count = frontmatter.get('word_count')
            if old_word_count != word_count:
                frontmatter['word_count'] = word_count
                if old_word_count is None:
                    self.fixes_applied.append(f"Added 'word_count': {word_count}")
                else:
                    self.fixes_applied.append(f"Updated 'word_count': {old_word_count} → {word_count}")

            # Serialize back to markdown
            fixed_text = self._serialize_markdown(frontmatter, body)

            return fixed_text, self.fixes_applied

        except Exception as e:
            self.logger.error(f"Error during Codex Lite auto-fix: {e}", exc_info=True)
            return text, self.fixes_applied

    def _extract_frontmatter(self, text: str) -> Tuple[Dict[str, Any], str]:
        """Extract YAML frontmatter from markdown text."""
        import yaml

        trimmed = text.lstrip()

        # Check for frontmatter delimiter
        if not trimmed.startswith('---'):
            return {}, text

        # Find the closing delimiter
        after_first = trimmed[3:]
        end_index = after_first.find('\n---')

        if end_index == -1:
            return {}, text

        frontmatter_text = after_first[:end_index]
        body_start = 3 + end_index + 4  # "---" + content + "\n---"
        body = trimmed[body_start:].strip()

        try:
            frontmatter = yaml.safe_load(frontmatter_text) or {}
            return frontmatter, body
        except yaml.YAMLError:
            return {}, text

    def _extract_h1_from_markdown(self, text: str) -> Optional[str]:
        """Extract first H1 heading from markdown text."""
        match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        return match.group(1).strip() if match else None

    def _count_words(self, text: str) -> int:
        """Count words in text."""
        if not text or not isinstance(text, str):
            return 0
        return len([w for w in text.split() if w])

    def _is_valid_uuid(self, uuid_str: str) -> bool:
        """Check if string is a valid UUID v4."""
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, uuid_str.lower()))

    def _serialize_markdown(self, frontmatter: Dict[str, Any], body: str) -> str:
        """Serialize frontmatter and body back to markdown format."""
        import yaml

        if not frontmatter:
            return body

        # Custom representer for clean YAML output
        def str_representer(dumper, data):
            if '\n' in data or len(data) > 80:
                return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
            return dumper.represent_scalar('tag:yaml.org,2002:str', data)

        yaml.add_representer(str, str_representer)

        fm_yaml = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False).strip()
        return f"---\n{fm_yaml}\n---\n\n{body}"


# ============================================================================
# Command-Line Interface Functions
# ============================================================================

def is_markdown_file(file_path: str) -> bool:
    """Check if file is a markdown file."""
    return file_path.lower().endswith('.md')


def is_codex_file(file_path: str) -> bool:
    """Check if file is a codex file."""
    lower = file_path.lower()
    return any(lower.endswith(ext) for ext in ['.codex.yaml', '.codex.yml', '.codex.json', '.codex'])


def fix_single_file(file_path: str, dry_run: bool = False, verbose: bool = False,
                    regenerate_all_ids: bool = False, validate: bool = False) -> bool:
    """
    Fix a single codex or markdown file.

    Args:
        file_path: Path to the codex or markdown file
        dry_run: If True, only show what would be fixed without making changes
        verbose: If True, show detailed logging
        regenerate_all_ids: If True, regenerate ALL IDs even if they're valid
        validate: If True, validate output against JSON schema after fixing

    Returns:
        True if successful, False otherwise
    """
    try:
        import yaml

        # Setup logging
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        is_md = is_markdown_file(file_path)
        file_type = "Codex Lite (Markdown)" if is_md else "Codex"

        print(f"{'[DRY RUN] ' if dry_run else ''}{'[RE-ID MODE] ' if regenerate_all_ids and not is_md else ''}Processing [{file_type}]: {file_path}")

        # Check if file exists
        if not os.path.exists(file_path):
            print(f"❌ Error: File not found: {file_path}")
            return False

        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()

        # Handle Markdown (Codex Lite) files
        if is_md:
            fixer = CodexLiteFixer()
            fixed_text, fixes = fixer.auto_fix_codex_lite(raw_text, file_path)

            if not fixes:
                print("✅ No fixes needed")
                return True

            # Show fixes
            print(f"\n📝 Fixes applied ({len(fixes)}):")
            for i, fix in enumerate(fixes, 1):
                print(f"  {i}. {fix}")

            # Write fixed content (unless dry run)
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_text)
                print(f"✅ Fixed file written: {file_path}")
            else:
                print("\n🔍 Dry run - no changes made")

            return True

        # Handle YAML/JSON Codex files
        content = yaml.safe_load(raw_text)

        # Create auto-fixer and fix content
        fixer = CodexAutoFixer()
        fixed_content, fixes = fixer.auto_fix_codex(None, content, regenerate_all_ids=regenerate_all_ids)

        if not fixes:
            print("✅ No fixes needed")
            return True

        # Show fixes
        print(f"\n📝 Fixes applied ({len(fixes)}):")
        for i, fix in enumerate(fixes, 1):
            print(f"  {i}. {fix}")

        # Validate against schema if requested
        if validate and HAS_SCHEMA_VALIDATOR:
            is_valid, val_errors = validate_codex(fixed_content)
            if not is_valid:
                print(f"\n⚠️ Schema validation warnings ({len(val_errors)}):")
                for error in val_errors[:5]:
                    print(f"  - {error}")
            else:
                print("✅ Schema validation passed")

        # Write fixed content (unless dry run)
        if not dry_run:
            # Custom YAML representer for multiline strings
            def str_representer(dumper, data):
                """Custom representer that uses pipe syntax for multiline strings."""
                if '\n' in data or len(data) > 80:
                    # Use literal block scalar (|) for multiline or long strings
                    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
                return dumper.represent_scalar('tag:yaml.org,2002:str', data)

            yaml.add_representer(str, str_representer)

            # Write fixed content with custom formatting
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(fixed_content, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)

            print(f"✅ Fixed file written: {file_path}")
        else:
            print("\n🔍 Dry run - no changes made")

        return True

    except Exception as e:
        print(f"❌ Error processing file: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def fix_directory(directory_path: str, recursive: bool = False, dry_run: bool = False,
                  verbose: bool = False, regenerate_all_ids: bool = False,
                  include_markdown: bool = False, validate: bool = False) -> Tuple[int, int]:
    """
    Fix all codex files in a directory.

    Args:
        directory_path: Path to directory
        recursive: If True, process subdirectories recursively
        dry_run: If True, only show what would be fixed without making changes
        verbose: If True, show detailed logging
        regenerate_all_ids: If True, regenerate ALL IDs even if they're valid
        include_markdown: If True, also process .md files as Codex Lite
        validate: If True, validate output against JSON schema after fixing

    Returns:
        Tuple of (successful_count, failed_count)
    """
    print(f"{'[DRY RUN] ' if dry_run else ''}{'[RE-ID MODE] ' if regenerate_all_ids else ''}Processing directory: {directory_path}")
    print(f"{'Recursive mode enabled' if recursive else 'Non-recursive mode'}")
    if include_markdown:
        print("Including Markdown files (Codex Lite)")
    print()

    # Find all codex files
    codex_extensions = ['.codex.yaml', '.codex.yml', '.codex.json', '.codex']
    if include_markdown:
        codex_extensions.append('.md')

    codex_files = []

    if recursive:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if any(file.endswith(ext) for ext in codex_extensions):
                    codex_files.append(os.path.join(root, file))
    else:
        for file in os.listdir(directory_path):
            file_path = os.path.join(directory_path, file)
            if os.path.isfile(file_path) and any(file.endswith(ext) for ext in codex_extensions):
                codex_files.append(file_path)

    if not codex_files:
        print("⚠️ No codex files found")
        return 0, 0

    print(f"Found {len(codex_files)} codex file(s)\n")

    # Process each file
    successful = 0
    failed = 0

    for i, file_path in enumerate(codex_files, 1):
        print(f"\n[{i}/{len(codex_files)}] ", end="")
        if fix_single_file(file_path, dry_run, verbose, regenerate_all_ids, validate):
            successful += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📁 Total: {len(codex_files)}")
    print(f"{'='*60}")

    return successful, failed


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Auto-fix Codex files (YAML, JSON, and Markdown)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix a single file
  python auto_fixer.py /path/to/file.codex.yaml

  # Fix a Codex Lite (Markdown) file
  python auto_fixer.py /path/to/file.md

  # Fix all files in a directory recursively
  python auto_fixer.py /path/to/directory --recursive

  # Include markdown files when processing directories
  python auto_fixer.py /path/to/directory -r --include-md

  # Dry run (show what would be fixed without making changes)
  python auto_fixer.py /path/to/file.codex.yaml --dry-run

  # Regenerate ALL IDs (even valid ones)
  python auto_fixer.py /path/to/file.codex.yaml --re-id

  # Verbose output
  python auto_fixer.py /path/to/file.codex.yaml --verbose
        """
    )

    parser.add_argument('path', help='Path to codex file or directory')
    parser.add_argument('-r', '--recursive', action='store_true', help='Process directories recursively')
    parser.add_argument('-d', '--dry-run', action='store_true', help='Show what would be fixed without making changes')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed logging')
    parser.add_argument('--re-id', action='store_true', help='Regenerate ALL IDs (even valid ones)')
    parser.add_argument('--include-md', action='store_true', help='Include .md files as Codex Lite when processing directories')
    parser.add_argument('--validate', action='store_true',
                        help='Validate output against JSON schema after fixing')

    args = parser.parse_args()

    # Check if path exists
    if not os.path.exists(args.path):
        print(f"❌ Error: Path not found: {args.path}")
        sys.exit(1)

    # Process file or directory
    if os.path.isfile(args.path):
        success = fix_single_file(args.path, args.dry_run, args.verbose, args.re_id, args.validate)
        sys.exit(0 if success else 1)
    elif os.path.isdir(args.path):
        successful, failed = fix_directory(
            args.path,
            args.recursive,
            args.dry_run,
            args.verbose,
            args.re_id,
            args.include_md,
            args.validate
        )
        sys.exit(0 if failed == 0 else 1)
    else:
        print(f"❌ Error: Invalid path: {args.path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
