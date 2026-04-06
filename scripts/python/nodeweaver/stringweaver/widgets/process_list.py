"""Widget for displaying work items in a grouped tree with before/after preview."""

import os
from typing import Dict, List, Optional, Tuple

from .._qt import QBrush, QColor, Qt, QtWidgets, Signal
from ..providers.base import WorkItem

# Highlight brush for changed preview values
_CHANGED_BRUSH = QBrush(QColor(150, 230, 150))
_DEFAULT_BRUSH = QBrush()


class _ElideLeftDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate that elides text from the left on top-level (group) rows."""

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if not index.parent().isValid():
            option.textElideMode = Qt.ElideLeft


class ProcessListWidget(QtWidgets.QWidget):
    """Tree view displaying work items grouped by their parent path.

    Top-level rows show the source path (node path or directory) in
    bold and are not selectable.  Child rows show individual item
    names with their original and preview values.

    Columns:
        Item: Tree hierarchy — group paths and child display names.
        Original: Value before operations (leaf rows only).
        Preview: Value after all operations (leaf rows only).

    Signals:
        apply_to_selection_requested: Emitted with a list of flat indices
            when the user requests applying operations to selected items.
        items_removed: Emitted after items are removed via context menu,
            so the parent can update pipeline state and preview.
    """

    apply_to_selection_requested = Signal(list)
    items_removed = Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._items: List[WorkItem] = []
        self._setup_ui()

    # ── UI setup ───────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._info_label = QtWidgets.QLabel("No items collected")
        layout.addWidget(self._info_label)

        # Filter bar
        self._filter_edit = QtWidgets.QLineEdit()
        self._filter_edit.setPlaceholderText("Filter items\u2026")
        self._filter_edit.setClearButtonEnabled(True)
        self._filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self._filter_edit)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderLabels(["Item", "Original", "Preview"])
        self._tree.setColumnCount(3)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)

        # Sortable columns
        self._tree.setSortingEnabled(True)
        self._tree.sortByColumn(0, Qt.AscendingOrder)

        # Elide group paths from the left so the tail is always visible
        self._tree.setItemDelegateForColumn(0, _ElideLeftDelegate(self._tree))

        header = self._tree.header()
        header.setStretchLastSection(True)
        self._tree.setColumnWidth(0, 220)
        self._tree.setColumnWidth(1, 180)

        layout.addWidget(self._tree)

    # ── Helpers ────────────────────────────────────────────

    @staticmethod
    def _split_source(item: WorkItem) -> Tuple[str, str]:
        """Return (parent_path, display_name) for a work item."""
        parent, name = os.path.split(item.source_path)
        if not name:
            return item.source_path, item.original_value
        return parent, name

    def _iter_leaves(self):
        """Yield every leaf QTreeWidgetItem."""
        for i in range(self._tree.topLevelItemCount()):
            group = self._tree.topLevelItem(i)
            for j in range(group.childCount()):
                yield group.child(j)

    # ── Public API ─────────────────────────────────────────

    def set_column_headers(self, headers: List[str]) -> None:
        """Update column header labels (3 strings)."""
        for i, label in enumerate(headers[:3]):
            self._tree.headerItem().setText(i, label)

    def set_items(self, items: List[WorkItem]) -> None:
        """Populate the tree with work items, grouped by parent path."""
        self._items = list(items)
        self._tree.setSortingEnabled(False)
        self._tree.clear()

        # Group by parent path, preserving insertion order
        groups: Dict[str, List[Tuple[int, WorkItem]]] = {}
        for i, item in enumerate(self._items):
            key, _ = self._split_source(item)
            groups.setdefault(key, []).append((i, item))

        for parent_path, entries in groups.items():
            group_tw = QtWidgets.QTreeWidgetItem([parent_path, "", ""])
            group_tw.setFlags(group_tw.flags() & ~Qt.ItemIsSelectable)
            font = group_tw.font(0)
            font.setBold(True)
            group_tw.setFont(0, font)
            group_tw.setToolTip(0, parent_path)

            for flat_idx, item in entries:
                _, display_name = self._split_source(item)
                child = QtWidgets.QTreeWidgetItem([
                    display_name,
                    item.original_value,
                    item.original_value,
                ])
                child.setData(0, Qt.UserRole, flat_idx)
                child.setToolTip(0, item.source_path)
                group_tw.addChild(child)

            self._tree.addTopLevelItem(group_tw)

        self._tree.expandAll()
        self._tree.setSortingEnabled(True)
        self._update_info()

    def update_previews(self, previews: List[Tuple[WorkItem, str]]) -> None:
        """Update the Preview column from pipeline results."""
        preview_map: Dict[int, Tuple[WorkItem, str]] = {
            i: (item, pv) for i, (item, pv) in enumerate(previews)
        }
        for child in self._iter_leaves():
            flat_idx = child.data(0, Qt.UserRole)
            entry = preview_map.get(flat_idx)
            if entry is None:
                continue
            item, preview = entry
            child.setText(2, preview)
            changed = preview != item.original_value
            child.setForeground(2, _CHANGED_BRUSH if changed else _DEFAULT_BRUSH)

    def clear(self) -> None:
        self._items.clear()
        self._tree.clear()
        self._update_info()

    def get_selected_indices(self) -> List[int]:
        """Return flat indices of selected leaf items."""
        indices = []
        for tree_item in self._tree.selectedItems():
            flat_idx = tree_item.data(0, Qt.UserRole)
            if flat_idx is not None:
                indices.append(flat_idx)
        return sorted(indices)

    def remove_indices(self, indices: List[int]) -> None:
        """Remove items at the given flat indices and rebuild the tree."""
        for idx in sorted(indices, reverse=True):
            if 0 <= idx < len(self._items):
                self._items.pop(idx)
        # Preserve current sort state across rebuild
        header = self._tree.header()
        sort_col = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()
        self.set_items(self._items)
        self._tree.sortByColumn(sort_col, sort_order)

    @property
    def items(self) -> List[WorkItem]:
        return list(self._items)

    # ── Internal ───────────────────────────────────────────

    def _update_info(self) -> None:
        count = len(self._items)
        if count == 0:
            self._info_label.setText("No items collected")
        else:
            groups = self._tree.topLevelItemCount()
            self._info_label.setText(
                f"{count} item{'s' if count != 1 else ''} "
                f"in {groups} group{'s' if groups != 1 else ''}"
            )

    def _apply_filter(self, text: str) -> None:
        """Show/hide items based on filter text matching any column or group path."""
        needle = text.lower()
        for i in range(self._tree.topLevelItemCount()):
            group = self._tree.topLevelItem(i)
            group_match = needle in group.text(0).lower() if needle else False
            any_visible = False
            for j in range(group.childCount()):
                child = group.child(j)
                if not needle:
                    child.setHidden(False)
                    any_visible = True
                    continue
                visible = group_match or any(
                    needle in child.text(col).lower()
                    for col in range(self._tree.columnCount())
                )
                child.setHidden(not visible)
                if visible:
                    any_visible = True
            group.setHidden(not any_visible if needle else False)

    def _show_context_menu(self, pos) -> None:
        """Show right-click context menu on leaf items."""
        item = self._tree.itemAt(pos)
        if item is None or item.data(0, Qt.UserRole) is None:
            return

        selected = self.get_selected_indices()
        if not selected:
            return

        menu = QtWidgets.QMenu(self)
        count = len(selected)
        label = f"{count} item{'s' if count > 1 else ''}"

        run_sel = menu.addAction(f"Apply Operations to {label}")
        menu.addSeparator()
        remove_sel = menu.addAction(f"Remove {label} from List")

        action = menu.exec_(self._tree.viewport().mapToGlobal(pos))

        if action == run_sel:
            self.apply_to_selection_requested.emit(selected)
        elif action == remove_sel:
            self.remove_indices(selected)
            self.items_removed.emit()
