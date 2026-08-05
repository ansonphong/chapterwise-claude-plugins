#!/usr/bin/env python3
"""
Scrivener File Writer - Output File Generation

Writes Scrivener content to disk in chosen format:
- Codex Lite (Markdown with YAML frontmatter)
- Codex YAML (.codex.yaml)
- Codex JSON (.codex.json)
"""

import argparse
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

# Codex format version (single source of truth).
try:
    from codex_version import CURRENT_FORMAT_VERSION
except ImportError:  # standalone execution outside the scripts directory
    CURRENT_FORMAT_VERSION = '1.3'

try:
    import yaml
except ImportError:
    yaml = None

if TYPE_CHECKING:
    from scrivener_parser import ScrivenerProject, BinderItem

logger = logging.getLogger(__name__)


@dataclass
class WriteResult:
    """Result of write operation."""
    files_written: int
    directories_created: int
    errors: List[str]


class ScrivenerFileWriter:
    """Write Scrivener content to disk."""

    def __init__(
        self,
        output_dir: Path,
        format: str = "markdown",
        dry_run: bool = False,
        index_depth: int = 1,
        containers: Optional[List[str]] = None,
        content_types: Optional[List[str]] = None
    ):
        """
        Initialize file writer.

        Args:
            output_dir: Directory to write files to
            format: Output format - "markdown", "yaml", or "json"
            dry_run: If True, don't actually write files
            index_depth: How many levels get their own index.codex.yaml (0=single, 1=per-book, 2=per-act)
            containers: Types that become inline in index (default: ["act", "part", "book", "folder"])
            content_types: Types that become .md files (default: ["chapter", "scene", "document"])
        """
        self.output_dir = Path(output_dir)
        self.format = format
        self.dry_run = dry_run
        self.index_depth = index_depth
        self.containers = containers or ["act", "part", "book", "folder"]
        self.content_types = content_types or ["chapter", "scene", "document"]
        self.files_written = 0
        self.dirs_created = 0
        self.errors: List[str] = []
        self._index_files_created: List[Path] = []

    def preview_files(self, project: "ScrivenerProject") -> List[str]:
        """Preview what files would be created."""
        files = []
        self._collect_files(project.binder_items, "", files)
        return files

    def _collect_files(self, items: List["BinderItem"], parent_path: str, files: List[str]):
        """Collect file paths recursively."""
        for item in items:
            if item.item_type in ("Trash", "Root"):
                continue

            slug = self._slugify(item.title)

            if item.item_type in ("Folder", "DraftFolder"):
                folder_path = f"{parent_path}/{slug}" if parent_path else slug
                if item.children:
                    self._collect_files(item.children, folder_path, files)

            elif item.item_type == "Text":
                ext = self._get_extension()
                file_path = f"{parent_path}/{slug}{ext}" if parent_path else f"{slug}{ext}"
                files.append(file_path)

                # Text items can have children too
                if item.children:
                    self._collect_files(item.children, parent_path, files)

    def write_project(self, project: "ScrivenerProject") -> WriteResult:
        """Write all project files to disk."""
        if not self.dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.dirs_created += 1

        self._write_items(project.binder_items, self.output_dir)

        return WriteResult(
            files_written=self.files_written,
            directories_created=self.dirs_created,
            errors=self.errors
        )

    def _write_items(self, items: List["BinderItem"], current_dir: Path):
        """Write items recursively."""
        for item in items:
            if item.item_type in ("Trash", "Root"):
                continue

            slug = self._slugify(item.title)

            if item.item_type in ("Folder", "DraftFolder"):
                folder_path = current_dir / slug
                if not self.dry_run:
                    folder_path.mkdir(parents=True, exist_ok=True)
                    self.dirs_created += 1

                if item.children:
                    self._write_items(item.children, folder_path)

            elif item.item_type == "Text":
                self._write_document(item, current_dir)

                # Text items can have children
                if item.children:
                    self._write_items(item.children, current_dir)

    def _write_document(self, item: "BinderItem", directory: Path):
        """Write a single document."""
        slug = self._slugify(item.title)
        ext = self._get_extension()
        file_path = directory / f"{slug}{ext}"

        try:
            if self.format == "markdown":
                content = self._build_markdown(item)
            elif self.format == "yaml":
                content = self._build_yaml(item)
            else:  # json
                content = self._build_json(item)

            if not self.dry_run:
                file_path.write_text(content, encoding="utf-8")

            self.files_written += 1
            logger.debug(f"Wrote: {file_path}")

        except Exception as e:
            self.errors.append(f"{file_path}: {e}")
            logger.error(f"Failed to write {file_path}: {e}")

    def _build_markdown(self, item: "BinderItem") -> str:
        """Build Codex Lite (Markdown with frontmatter)."""
        frontmatter = {
            "type": self._map_type(item),
            "name": item.title
        }

        # Add Scrivener metadata
        if item.label:
            frontmatter["scrivener_label"] = item.label
        if item.status:
            frontmatter["scrivener_status"] = item.status
        if item.keywords:
            frontmatter["tags"] = ", ".join(item.keywords)
        if item.synopsis:
            frontmatter["summary"] = item.synopsis
        if not item.include_in_compile:
            frontmatter["scrivener_include_in_compile"] = False

        # Build YAML frontmatter
        if yaml:
            yaml_fm = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True).strip()
        else:
            # Fallback to simple format if yaml not installed
            yaml_fm = "\n".join(f"{k}: {repr(v)}" for k, v in frontmatter.items())

        body = item.converted_content or ""

        return f"---\n{yaml_fm}\n---\n\n# {item.title}\n\n{body}\n"

    def _build_yaml(self, item: "BinderItem") -> str:
        """Build full Codex YAML."""
        if not yaml:
            raise ImportError("PyYAML is required for YAML output. Install with: pip3 install pyyaml")

        data = self._build_codex_data(item)
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)

    def _build_json(self, item: "BinderItem") -> str:
        """Build Codex JSON."""
        data = self._build_codex_data(item)
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _build_codex_data(self, item: "BinderItem") -> dict:
        """Build Codex data structure."""
        data = {
            "metadata": {
                "formatVersion": CURRENT_FORMAT_VERSION,
                "created": datetime.now().isoformat()
            },
            "id": item.uuid,
            "type": self._map_type(item),
            "name": item.title
        }

        # Add attributes
        attributes = []
        if item.label:
            attributes.append({"key": "scrivener_label", "value": item.label})
        if item.status:
            attributes.append({"key": "scrivener_status", "value": item.status})
        if item.keywords:
            attributes.append({"key": "keywords", "value": ", ".join(item.keywords)})
        if not item.include_in_compile:
            attributes.append({"key": "scrivener_include_in_compile", "value": "false"})

        if attributes:
            data["attributes"] = attributes

        if item.synopsis:
            data["summary"] = item.synopsis

        if item.converted_content:
            data["body"] = item.converted_content

        return data

    def generate_index(self, project: "ScrivenerProject"):
        """Generate index.codex.yaml files."""
        if self.dry_run:
            return

        if not yaml:
            logger.warning("PyYAML not installed, skipping index generation")
            return

        # Create boilerplate index.codex.yaml
        index_path = self.output_dir / "index.codex.yaml"
        index_data = {
            "metadata": {
                "formatVersion": CURRENT_FORMAT_VERSION,
                "created": datetime.now().isoformat(),
                "source": "scrivener-import"
            },
            "id": "index-root",
            "type": "project",
            "name": project.title,
            "summary": f"Imported from Scrivener: {project.title}",
            "attributes": [
                {"key": "scrivener_identifier", "value": project.identifier},
                {"key": "scrivener_version", "value": project.version},
                {"key": "scrivener_creator", "value": project.creator}
            ]
        }

        index_path.write_text(
            yaml.dump(index_data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8"
        )
        logger.info(f"Created: {index_path}")

        # Create .index.codex.yaml (auto-generated cache)
        cache_index = self._build_cache_index(project)
        cache_path = self.output_dir / ".index.codex.yaml"
        cache_path.write_text(
            yaml.dump(cache_index, default_flow_style=False, allow_unicode=True),
            encoding="utf-8"
        )
        logger.info(f"Created: {cache_path}")

    def _build_cache_index(self, project: "ScrivenerProject") -> dict:
        """Build .index.codex.yaml structure."""
        return {
            "metadata": {
                "formatVersion": CURRENT_FORMAT_VERSION,
                "generated": True,
                "generatedAt": datetime.now().isoformat(),
                "source": "scrivener-import"
            },
            "id": "index-root",
            "type": "index",
            "name": project.title,
            "children": self._build_index_children(project.binder_items)
        }

    def _build_index_children(self, items: List["BinderItem"]) -> List[dict]:
        """Build index children recursively."""
        children = []

        for item in items:
            if item.item_type in ("Trash", "Root"):
                continue

            slug = self._slugify(item.title)

            if item.item_type in ("Folder", "DraftFolder"):
                child = {
                    "id": f"folder-{slug}",
                    "type": "folder",
                    "name": item.title
                }
                if item.children:
                    child["children"] = self._build_index_children(item.children)
                children.append(child)

            elif item.item_type == "Text":
                ext = self._get_extension()
                child = {
                    "id": f"file-{slug}",
                    "type": self._map_type(item),
                    "name": item.title,
                    "_filename": f"{slug}{ext}"
                }
                children.append(child)

                # Handle Text items with children
                if item.children:
                    for sub in self._build_index_children(item.children):
                        children.append(sub)

        return children

    # ========== NESTED INDEX METHODS (V2) ==========

    def write_project_nested(self, project: "ScrivenerProject") -> WriteResult:
        """Write project with nested index structure (V2)."""
        if not self.dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.dirs_created += 1

        # Filter to manuscript items only (skip Research, Trash, etc.)
        manuscript_items = [
            item for item in project.binder_items
            if item.item_type not in ("Trash", "TrashFolder", "ResearchFolder", "Root")
            and not item.title.lower().startswith("template")
        ]

        # Write nested structure
        self._write_nested_items(manuscript_items, self.output_dir, depth=0)

        # Generate master index
        self._write_master_index(project, manuscript_items)

        return WriteResult(
            files_written=self.files_written,
            directories_created=self.dirs_created,
            errors=self.errors
        )

    def _write_nested_items(self, items: List["BinderItem"], current_dir: Path, depth: int):
        """Write items with nested index structure."""
        for item in items:
            if item.item_type in ("Trash", "TrashFolder", "Root"):
                continue

            slug = self._slugify(item.title)

            if self._is_container(item):
                # Create folder for container
                folder_path = current_dir / slug
                if not self.dry_run:
                    folder_path.mkdir(parents=True, exist_ok=True)
                    self.dirs_created += 1

                # Decide whether this container gets its own index
                if depth < self.index_depth:
                    # Write sub-index for this container
                    self._write_nested_index(item, folder_path, depth + 1)
                    self._index_files_created.append(folder_path / "index.codex.yaml")

                # Recurse into children
                if item.children:
                    self._write_nested_items(item.children, folder_path, depth + 1)

            elif self._is_content(item):
                # Write content file
                self._write_document(item, current_dir)

                # Text items can have children - write them in same directory
                if item.children:
                    self._write_nested_items(item.children, current_dir, depth)

    def _write_nested_index(self, container_item: "BinderItem", directory: Path, depth: int):
        """Write index.codex.yaml for a container (book, act, etc.)."""
        if not yaml:
            logger.warning("PyYAML not installed, skipping nested index generation")
            return

        index_data = {
            "metadata": {
                "formatVersion": CURRENT_FORMAT_VERSION,
                "generator": "scrivener-import"
            },
            "id": container_item.uuid,
            "type": self._map_type(container_item),
            "name": container_item.title,
            "patterns": {
                "include": ["**/*.md"],
                "exclude": ["_drafts/**"]
            },
            "children": self._build_children_with_includes(container_item.children, directory, depth)
        }

        # Add optional metadata
        if container_item.synopsis:
            index_data["summary"] = container_item.synopsis
        if container_item.label:
            index_data["scrivener_label"] = container_item.label
        if container_item.status:
            index_data["scrivener_status"] = container_item.status

        index_path = directory / "index.codex.yaml"
        if not self.dry_run:
            index_path.write_text(
                yaml.dump(index_data, default_flow_style=False, allow_unicode=True, sort_keys=False),
                encoding="utf-8"
            )
            self.files_written += 1
        logger.info(f"Created nested index: {index_path}")

    def _build_children_with_includes(self, items: List["BinderItem"], parent_dir: Path, depth: int) -> List[dict]:
        """Build children array with include directives for content files."""
        children = []

        for item in items:
            if item.item_type in ("Trash", "TrashFolder", "Root"):
                continue

            slug = self._slugify(item.title)

            if self._is_container(item):
                # Check if this container gets its own index
                if depth < self.index_depth:
                    # Reference sub-index
                    children.append({
                        "include": f"./{slug}/index.codex.yaml"
                    })
                else:
                    # Inline container with nested children
                    child_data = {
                        "id": item.uuid,
                        "type": self._map_type(item),
                        "name": item.title
                    }
                    if item.synopsis:
                        child_data["summary"] = item.synopsis
                    if item.label:
                        child_data["scrivener_label"] = item.label

                    # Add children with includes
                    if item.children:
                        child_data["children"] = self._build_children_with_includes(
                            item.children, parent_dir / slug, depth + 1
                        )
                    children.append(child_data)

            elif self._is_content(item):
                # Include directive for content file
                ext = self._get_extension()
                # Calculate relative path from parent_dir
                children.append({
                    "include": f"./{slug}{ext}"
                })

                # Text items with children - add their children too
                if item.children:
                    for sub_child in self._build_children_with_includes(item.children, parent_dir, depth):
                        children.append(sub_child)

        return children

    def _write_master_index(self, project: "ScrivenerProject", manuscript_items: List["BinderItem"]):
        """Write the master index.codex.yaml at root."""
        if not yaml:
            return

        # Build children - either includes to sub-indexes or inline
        children = []
        for item in manuscript_items:
            if item.item_type in ("Trash", "TrashFolder", "Root"):
                continue

            slug = self._slugify(item.title)

            if self._is_container(item) and self.index_depth > 0:
                # Reference sub-index
                children.append({
                    "include": f"./{slug}/index.codex.yaml"
                })
            elif self._is_container(item):
                # Inline container (index_depth=0)
                child_data = {
                    "id": item.uuid,
                    "type": self._map_type(item),
                    "name": item.title
                }
                if item.children:
                    child_data["children"] = self._build_children_with_includes(item.children, self.output_dir / slug, 1)
                children.append(child_data)
            elif self._is_content(item):
                # Content file at root level
                ext = self._get_extension()
                children.append({
                    "include": f"./{slug}{ext}"
                })

        index_data = {
            "metadata": {
                "formatVersion": CURRENT_FORMAT_VERSION,
                "generator": "scrivener-import",
                "source": f"{project.title}.scriv"
            },
            "id": project.identifier or "project-root",
            "type": "index",
            "name": project.title,
            "patterns": {
                "include": ["**/*.md"],
                "exclude": ["_drafts/**"]
            },
            "children": children
        }

        if project.author:
            index_data["author"] = project.author

        index_path = self.output_dir / "index.codex.yaml"
        if not self.dry_run:
            index_path.write_text(
                yaml.dump(index_data, default_flow_style=False, allow_unicode=True, sort_keys=False),
                encoding="utf-8"
            )
            self.files_written += 1
        logger.info(f"Created master index: {index_path}")

    def _map_type(self, item: "BinderItem") -> str:
        """Map Scrivener item to Codex type."""
        # Check label first
        if item.label:
            label_lower = item.label.lower()
            if "chapter" in label_lower:
                return "chapter"
            if "scene" in label_lower:
                return "scene"
            if "character" in label_lower:
                return "character"
            if "location" in label_lower:
                return "location"
            if "act" in label_lower:
                return "act"
            if "part" in label_lower:
                return "part"
            if "book" in label_lower:
                return "book"

        # Check title patterns
        title_lower = item.title.lower()
        if title_lower.startswith("chapter"):
            return "chapter"
        if title_lower.startswith("scene"):
            return "scene"
        if title_lower.startswith("act"):
            return "act"
        if title_lower.startswith("book"):
            return "book"
        if title_lower.startswith("part"):
            return "part"

        # Check item type for containers
        if item.item_type in ("Folder", "DraftFolder"):
            return "folder"

        return "document"

    def _is_container(self, item: "BinderItem") -> bool:
        """Check if item should be treated as a container (inline in index)."""
        mapped_type = self._map_type(item)
        return mapped_type in self.containers or item.item_type in ("Folder", "DraftFolder")

    def _is_content(self, item: "BinderItem") -> bool:
        """Check if item should be written as a content file (.md)."""
        mapped_type = self._map_type(item)
        return mapped_type in self.content_types or item.item_type == "Text"

    def _get_extension(self) -> str:
        """Get file extension for format."""
        if self.format == "markdown":
            return ".md"
        elif self.format == "yaml":
            return ".codex.yaml"
        else:
            return ".codex.json"

    def _slugify(self, text: str) -> str:
        """Convert text to slug for filenames."""
        # Lowercase
        slug = text.lower()
        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        # Remove multiple hyphens
        slug = re.sub(r'-+', '-', slug)
        # Trim hyphens
        slug = slug.strip('-')

        return slug or "untitled"


def main():
    parser = argparse.ArgumentParser(
        description="Write Scrivener content to Codex format files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Formats:
  markdown  - Codex Lite (.md with YAML frontmatter) - default
  yaml      - Full Codex format (.codex.yaml)
  json      - Full Codex format (.codex.json)

This module is typically used by scrivener_import.py, not directly.
        """
    )

    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "yaml", "json"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Just show help - this module is meant to be imported
    print("ScrivenerFileWriter module loaded successfully.")
    print(f"YAML available: {yaml is not None}")
    print(f"\nUse: from scrivener_file_writer import ScrivenerFileWriter")


if __name__ == "__main__":
    main()
