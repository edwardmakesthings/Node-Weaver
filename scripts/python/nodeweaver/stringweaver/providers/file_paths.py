"""Provider for file and folder names on disk."""

import os
from typing import List

import hou

from .base import Provider, WorkItem


class FilePathProvider(Provider):
    """Reads filenames from a directory and renames them on disk.

    The user picks a directory via Collect; items are populated from
    the files (and optionally folders) found there.  Operations
    transform the filename and ``apply_value`` performs the rename.

    When *stem_only* mode is active the extension is preserved
    automatically so operations only see the name without it.
    """

    def __init__(self) -> None:
        self._directory: str = ""
        self._include_dirs: bool = True
        self._recursive: bool = False
        self._stem_only: bool = True

    @property
    def name(self) -> str:
        return "File Paths"

    @property
    def needs_node_scope(self) -> bool:
        return False

    @property
    def directory(self) -> str:
        return self._directory

    @directory.setter
    def directory(self, path: str) -> None:
        self._directory = path

    # ── Collection ─────────────────────────────────────────

    def get_items(self, nodes: List[hou.Node]) -> List[WorkItem]:
        """List files in the stored directory.

        *nodes* is ignored — the directory is set externally by the UI
        before this method is called.
        """
        if not self._directory or not os.path.isdir(self._directory):
            return []

        items: List[WorkItem] = []

        if self._recursive:
            for root, dirs, files in os.walk(self._directory):
                for name in files:
                    item = self._make_item(root, name, is_dir=False)
                    if item:
                        items.append(item)
                if self._include_dirs:
                    for name in dirs:
                        item = self._make_item(root, name, is_dir=True)
                        if item:
                            items.append(item)
        else:
            for entry in os.scandir(self._directory):
                if entry.is_file() or (self._include_dirs and entry.is_dir()):
                    item = self._make_item(
                        self._directory, entry.name, is_dir=entry.is_dir()
                    )
                    if item:
                        items.append(item)

        return items

    def _make_item(self, directory: str, name: str, *, is_dir: bool) -> WorkItem:
        full_path = os.path.join(directory, name)
        if self._stem_only and not is_dir:
            stem, _ext = os.path.splitext(name)
            value = stem
        else:
            value = name
        return WorkItem(
            source_path=full_path,
            original_value=value,
        )

    # ── Application ────────────────────────────────────────

    def apply_value(self, item: WorkItem, new_value: str) -> None:
        old_path = item.source_path
        if not os.path.exists(old_path):
            return

        parent = os.path.dirname(old_path)
        old_name = os.path.basename(old_path)

        if self._stem_only and os.path.isfile(old_path):
            _stem, ext = os.path.splitext(old_name)
            new_name = new_value + ext
        else:
            new_name = new_value

        if not new_name or new_name == old_name:
            return

        new_path = os.path.join(parent, new_name)

        # Avoid overwriting existing files
        if os.path.exists(new_path):
            return

        os.rename(old_path, new_path)
