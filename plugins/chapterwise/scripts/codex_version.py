#!/usr/bin/env python3
"""
Codex format version constants.

Single source of truth for every script that stamps or checks a
`metadata.formatVersion`. Import from here rather than hardcoding a literal —
that is how the plugin drifted a full spec version behind before.

Spec: https://chapterwise.app/docs/codex/format/codex-format
"""

# Version written into newly generated documents.
CURRENT_FORMAT_VERSION = '1.3'

# Versions that read and validate cleanly. Older documents stay valid — tools
# repair integrity, they never silently migrate a document between versions.
SUPPORTED_FORMAT_VERSIONS = ['1.0', '1.1', '1.2', '1.3']

__all__ = ['CURRENT_FORMAT_VERSION', 'SUPPORTED_FORMAT_VERSIONS']
