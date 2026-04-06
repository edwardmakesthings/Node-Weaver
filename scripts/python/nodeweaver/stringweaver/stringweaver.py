"""StringWeaver - Batch string transformation tool for Houdini.

Provides a GUI for applying sequential string operations to node names,
parameter values, and expressions across multiple nodes at once.

Example:
    >>> from nodeweaver.stringweaver import StringWeaver
    >>> weaver = StringWeaver()
    >>> weaver.show()
"""

from typing import List, Optional

import hou

from ._qt import Qt, QtCore, QtWidgets
from .pipeline import Pipeline
from .providers import PROVIDER_REGISTRY, Provider
from .providers.base import WorkItem
from .providers.file_paths import FilePathProvider
from .providers.parameters import ExpressionProvider, StringParameterProvider
from .widgets.operation_panel import OperationPanel
from .widgets.process_list import ProcessListWidget

# Scope options for node collection
SCOPES = [
    ("selected", "Selected Nodes"),
    ("siblings", "Selected + Siblings"),
    ("selected_children", "Selected + Direct Children"),
    ("selected_all_sub", "Selected + All Subchildren"),
    ("children_only", "Direct Children Only"),
    ("all_sub_only", "All Subchildren Only"),
    ("all_scene", "All Nodes in Hip File"),
]


class StringWeaver(QtWidgets.QWidget):
    """Main StringWeaver interface.

    A batch string transformation tool that collects items from Houdini
    (node names, parameter values, expressions), lets the user build
    a pipeline of string operations, previews the results live, and
    applies them all at once with a single undo step.
    """

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        *,
        parm_start: bool = False,
        start_value: str = "",
        nodes: Optional[List[hou.Node]] = None,
        parms: Optional[List[hou.Parm]] = None,
    ) -> None:
        super().__init__(
            parent or hou.qt.mainWindow(),
            Qt.WindowStaysOnTopHint,
        )
        self.pipeline = Pipeline()
        self._active_provider: Optional[Provider] = None
        self._start_value = start_value

        self._setup_window()
        self._setup_ui()
        self._connect_signals()

        # Pre-select provider based on launch context
        if parm_start:
            idx = self._provider_combo.findData("string_parameters")
        else:
            idx = self._provider_combo.findData("node_names")
        if idx >= 0:
            self._provider_combo.setCurrentIndex(idx)
        self._on_provider_changed(self._provider_combo.currentIndex())

        # Auto-populate items when launched with specific targets
        if parms:
            self._load_parm_items(parms)
        elif nodes:
            self._load_node_items(nodes)

    # ── Window setup ───────────────────────────────────────

    def _setup_window(self) -> None:
        self.setWindowTitle("String Weaver")
        self.setGeometry(450, 300, 900, 600)
        self.setMinimumSize(600, 400)
        self._center()

    def _center(self) -> None:
        screen = self.screen().geometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2,
        )

    def showWindow(self) -> None:
        """Show the window parented to Houdini's main window."""
        self.setParent(hou.qt.mainWindow(), Qt.Window)
        self.show()

    def closeEvent(self, event: QtCore.QEvent) -> None:
        self.setParent(None)

    # ── UI construction ────────────────────────────────────

    def _setup_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Top row: source config
        main_layout.addLayout(self._build_source_section())

        # Resizable splitter between process list and operations
        splitter = QtWidgets.QSplitter()

        # Left panel: process list + actions
        left_widget = QtWidgets.QWidget()
        left = QtWidgets.QVBoxLayout(left_widget)
        left.setContentsMargins(0, 0, 0, 0)
        left.addWidget(self._build_process_section(), stretch=1)
        left.addLayout(self._build_action_section())
        splitter.addWidget(left_widget)

        # Right panel: operations
        self._operation_panel = OperationPanel()
        self._operation_panel.setMinimumWidth(250)
        splitter.addWidget(self._operation_panel)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def _build_source_section(self) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()

        # Provider selector
        self._provider_combo = QtWidgets.QComboBox()
        for key, cls in PROVIDER_REGISTRY.items():
            self._provider_combo.addItem(cls().name, key)
        row.addWidget(QtWidgets.QLabel("Source:"))
        row.addWidget(self._provider_combo)

        # Scope selector (hidden for non-node providers)
        self._scope_label = QtWidgets.QLabel("Scope:")
        self._scope_combo = QtWidgets.QComboBox()
        for key, label in SCOPES:
            self._scope_combo.addItem(label, key)
        row.addWidget(self._scope_label)
        row.addWidget(self._scope_combo)

        # Directory display (shown for file-based providers)
        self._dir_label = QtWidgets.QLabel("Dir:")
        self._dir_display = QtWidgets.QLineEdit()
        self._dir_display.setReadOnly(True)
        self._dir_display.setPlaceholderText("Click Collect to choose\u2026")
        self._dir_label.setVisible(False)
        self._dir_display.setVisible(False)
        row.addWidget(self._dir_label)
        row.addWidget(self._dir_display)

        # Use Labels checkbox (shown for parameter providers)
        self._use_labels_cb = QtWidgets.QCheckBox("Use Labels")
        self._use_labels_cb.setChecked(True)
        self._use_labels_cb.setToolTip(
            "Show parameter labels instead of internal names"
        )
        self._use_labels_cb.setVisible(False)
        row.addWidget(self._use_labels_cb)

        row.addStretch()

        # Collect mode selector
        row.addWidget(QtWidgets.QLabel("Mode:"))
        self._collect_mode_combo = QtWidgets.QComboBox()
        self._collect_mode_combo.addItem("Add", "add")
        self._collect_mode_combo.addItem("Replace", "replace")
        row.addWidget(self._collect_mode_combo)

        # Collect button
        self._collect_btn = QtWidgets.QPushButton("Collect Items")
        row.addWidget(self._collect_btn)

        return row

    def _build_process_section(self) -> QtWidgets.QWidget:
        self._process_list = ProcessListWidget()
        return self._process_list

    def _build_action_section(self) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()

        self._remove_selected_btn = QtWidgets.QPushButton("Remove Selected")
        self._clear_btn = QtWidgets.QPushButton("Clear All")

        row.addWidget(self._remove_selected_btn)
        row.addWidget(self._clear_btn)
        row.addStretch()

        self._remove_after_run_cb = QtWidgets.QCheckBox("Remove after run")
        self._remove_after_run_cb.setToolTip(
            "Remove successfully changed items from the list after running"
        )
        row.addWidget(self._remove_after_run_cb)

        self._run_selected_btn = QtWidgets.QPushButton("Run on Selected")
        self._run_selected_btn.setEnabled(False)
        row.addWidget(self._run_selected_btn)

        self._run_btn = QtWidgets.QPushButton("Run Operations on All")
        self._run_btn.setEnabled(False)
        row.addWidget(self._run_btn)

        return row

    # ── Signal connections ─────────────────────────────────

    def _connect_signals(self) -> None:
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self._collect_btn.clicked.connect(self._on_collect_clicked)
        self._remove_selected_btn.clicked.connect(self._remove_selected)
        self._clear_btn.clicked.connect(self._clear_items)
        self._run_btn.clicked.connect(self._run_operations)
        self._run_selected_btn.clicked.connect(self._run_on_selection_btn)
        self._operation_panel.operations_changed.connect(self._update_preview)
        self._process_list.apply_to_selection_requested.connect(self._run_on_selection)
        self._process_list.items_removed.connect(self._on_items_removed)
        self._use_labels_cb.toggled.connect(self._on_use_labels_toggled)

    # ── Slots ──────────────────────────────────────────────

    # Column headers per provider key
    _PROVIDER_HEADERS = {
        "node_names": ["Node", "Original Name", "Preview"],
        "node_comments": ["Node", "Original Comment", "Preview"],
        "string_parameters": ["Parameter", "Original Value", "Preview"],
        "expressions": ["Parameter", "Original Expr", "Preview"],
        "file_paths": ["File", "Original Name", "Preview"],
    }
    _DEFAULT_HEADERS = ["Item", "Original", "Preview"]

    def _on_provider_changed(self, index: int) -> None:
        key = self._provider_combo.currentData()
        provider_cls = PROVIDER_REGISTRY.get(key)
        if provider_cls:
            self._active_provider = provider_cls()

        # Sync label preference for parameter providers
        if isinstance(self._active_provider, (StringParameterProvider, ExpressionProvider)):
            self._active_provider.use_labels = self._use_labels_cb.isChecked()

        # Clear stale items from the previous provider
        self._clear_items()

        # Toggle scope vs directory controls
        needs_scope = self._active_provider is None or self._active_provider.needs_node_scope
        self._scope_label.setVisible(needs_scope)
        self._scope_combo.setVisible(needs_scope)
        self._dir_label.setVisible(not needs_scope)
        self._dir_display.setVisible(not needs_scope)

        # Toggle labels checkbox for parameter providers
        is_parm_provider = isinstance(
            self._active_provider, (StringParameterProvider, ExpressionProvider)
        )
        self._use_labels_cb.setVisible(is_parm_provider)

        # Update column headers
        headers = self._PROVIDER_HEADERS.get(key, self._DEFAULT_HEADERS)
        self._process_list.set_column_headers(headers)

    def _load_parm_items(self, parms: List[hou.Parm]) -> None:
        """Create WorkItems directly from explicit parameter references."""
        use_labels = self._use_labels_cb.isChecked()
        items = []
        for p in parms:
            val = p.eval()
            if not val:
                continue
            if use_labels:
                display = p.parmTemplate().label()
                source = f"{p.node().path()}/{display}"
            else:
                source = p.path()
            items.append(WorkItem(
                node=p.node(),
                source_path=source,
                original_value=str(val),
                parm=p,
            ))
        if items:
            self._populate_items(items)

    def _load_node_items(self, nodes: List[hou.Node]) -> None:
        """Collect items from an explicit node list using the active provider."""
        if self._active_provider is None:
            return
        if isinstance(self._active_provider, (StringParameterProvider, ExpressionProvider)):
            self._active_provider.use_labels = self._use_labels_cb.isChecked()
        items = self._active_provider.get_items(nodes)
        if items:
            self._populate_items(items)

    def _populate_items(self, items: List[WorkItem]) -> None:
        """Load a list of WorkItems into the pipeline and process list."""
        self.pipeline.set_items(items)
        self._process_list.set_items(items)
        self._update_run_state()

    def _append_items(self, new_items: List[WorkItem]) -> None:
        """Add items to the existing list, skipping duplicates."""
        existing = {
            (item.source_path, item.original_value) for item in self.pipeline.items
        }
        unique = [
            item for item in new_items
            if (item.source_path, item.original_value) not in existing
        ]
        if not unique:
            return
        combined = list(self.pipeline.items) + unique
        self._populate_items(combined)

    def _on_collect_clicked(self) -> None:
        """Dispatch to add or replace based on the mode combo."""
        if self._collect_mode_combo.currentData() == "add":
            self._collect_items_add()
        else:
            self._collect_items()

    def _collect_items(self) -> None:
        if self._active_provider is None:
            return

        # Sync label preference before collecting
        if isinstance(self._active_provider, (StringParameterProvider, ExpressionProvider)):
            self._active_provider.use_labels = self._use_labels_cb.isChecked()

        # File-based providers: prompt for a directory instead of using scope
        if not self._active_provider.needs_node_scope:
            self._collect_file_items()
            return

        nodes = self._get_target_nodes()
        if not nodes:
            hou.ui.displayMessage(
                "No nodes found for the selected scope.\n"
                "Make sure nodes are selected in the network editor.",
                severity=hou.severityType.Warning,
            )
            return

        items = self._active_provider.get_items(nodes)
        if not items:
            hou.ui.displayMessage(
                "No matching items found in the selected nodes.",
                severity=hou.severityType.ImportantMessage,
            )
            return

        self._populate_items(items)
        self._update_preview()

    def _collect_file_items(self) -> None:
        """Prompt for a directory and collect file items."""
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Collect Files From",
            self._dir_display.text() or "",
        )
        if not directory:
            return

        provider = self._active_provider
        if not isinstance(provider, FilePathProvider):
            return

        provider.directory = directory
        self._dir_display.setText(directory)

        items = provider.get_items([])
        if not items:
            hou.ui.displayMessage(
                "No files found in the selected directory.",
                severity=hou.severityType.ImportantMessage,
            )
            return

        self._populate_items(items)
        self._update_preview()

    def _collect_items_add(self) -> None:
        """Collect new items and add them to the existing list."""
        if self._active_provider is None:
            return

        # Sync label preference before collecting
        if isinstance(self._active_provider, (StringParameterProvider, ExpressionProvider)):
            self._active_provider.use_labels = self._use_labels_cb.isChecked()

        # File-based providers
        if not self._active_provider.needs_node_scope:
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "Select Directory to Add Files From",
                self._dir_display.text() or "",
            )
            if not directory:
                return
            provider = self._active_provider
            if not isinstance(provider, FilePathProvider):
                return
            provider.directory = directory
            self._dir_display.setText(directory)
            new_items = provider.get_items([])
        else:
            nodes = self._get_target_nodes()
            if not nodes:
                hou.ui.displayMessage(
                    "No nodes found for the selected scope.\n"
                    "Make sure nodes are selected in the network editor.",
                    severity=hou.severityType.Warning,
                )
                return
            new_items = self._active_provider.get_items(nodes)

        if not new_items:
            hou.ui.displayMessage(
                "No new items found.",
                severity=hou.severityType.ImportantMessage,
            )
            return

        self._append_items(new_items)
        self._update_preview()

    def _remove_selected(self) -> None:
        indices = self._process_list.get_selected_indices()
        if not indices:
            return
        self._process_list.remove_indices(indices)
        self.pipeline.set_items(self._process_list.items)
        self._update_run_state()
        self._update_preview()

    def _clear_items(self) -> None:
        self._process_list.clear()
        self.pipeline.clear_items()
        self._update_run_state()

    def _update_preview(self) -> None:
        self.pipeline.set_operations(self._operation_panel.get_operations())
        if self.pipeline.items:
            previews = self.pipeline.preview()
            self._process_list.update_previews(previews)
        self._update_run_state()

    def _update_run_state(self) -> None:
        has_items = bool(self.pipeline.items)
        has_ops = bool(self._operation_panel.get_operations())
        self._run_btn.setEnabled(has_items and has_ops)
        self._run_selected_btn.setEnabled(has_items and has_ops)

    def _run_operations(self) -> None:
        if self._active_provider is None:
            return

        # File renames are outside Houdini undo — confirm first
        if isinstance(self._active_provider, FilePathProvider):
            result = QtWidgets.QMessageBox.warning(
                self,
                "Rename Files on Disk",
                "This will rename files on disk.\n"
                "File renames cannot be undone with Ctrl+Z.\n\n"
                "Continue?",
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Cancel,
            )
            if result != QtWidgets.QMessageBox.Ok:
                return

        self.pipeline.set_operations(self._operation_panel.get_operations())
        previews = self.pipeline.preview()
        changed_indices = [i for i, (item, pv) in enumerate(previews) if pv != item.original_value]
        changed = self.pipeline.execute(self._active_provider)

        hou.ui.displayMessage(
            f"StringWeaver applied {changed} change{'s' if changed != 1 else ''}.",
            severity=hou.severityType.Message,
        )

        self._post_run_refresh(changed_indices)

    def _run_on_selection_btn(self) -> None:
        """Handler for the Run on Selected button."""
        indices = self._process_list.get_selected_indices()
        if indices:
            self._run_on_selection(indices)

    def _run_on_selection(self, indices: List[int]) -> None:
        """Apply operations only to the selected items in the process list."""
        if self._active_provider is None:
            return

        all_items = self._process_list.items
        selected_items = [all_items[i] for i in indices if 0 <= i < len(all_items)]
        if not selected_items:
            return

        # File renames are outside Houdini undo — confirm first
        if isinstance(self._active_provider, FilePathProvider):
            result = QtWidgets.QMessageBox.warning(
                self,
                "Rename Files on Disk",
                f"This will rename {len(selected_items)} file(s) on disk.\n"
                "File renames cannot be undone with Ctrl+Z.\n\n"
                "Continue?",
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Cancel,
            )
            if result != QtWidgets.QMessageBox.Ok:
                return

        sub_pipeline = Pipeline()
        sub_pipeline.set_items(selected_items)
        sub_pipeline.set_operations(self._operation_panel.get_operations())
        previews = sub_pipeline.preview()
        changed_sub = [
            indices[j] for j, (item, pv) in enumerate(previews) if pv != item.original_value
        ]
        changed = sub_pipeline.execute(self._active_provider)

        hou.ui.displayMessage(
            f"StringWeaver applied {changed} change{'s' if changed != 1 else ''} "
            f"to {len(selected_items)} selected item{'s' if len(selected_items) != 1 else ''}.",
            severity=hou.severityType.Message,
        )

        self._post_run_refresh(changed_sub)

    def _post_run_refresh(self, changed_indices: List[int]) -> None:
        """Refresh after a run, optionally removing changed items."""
        if self._remove_after_run_cb.isChecked() and changed_indices:
            self._process_list.remove_indices(changed_indices)
            self.pipeline.set_items(self._process_list.items)
            self._update_run_state()
            self._update_preview()
            return

        # Full re-collect
        if isinstance(self._active_provider, FilePathProvider):
            items = self._active_provider.get_items([])
            if items:
                self._populate_items(items)
                self._update_preview()
            else:
                self._clear_items()
        else:
            self._collect_items()

    def _on_use_labels_toggled(self, use_labels: bool) -> None:
        """Rewrite source_path on existing items to reflect label vs name."""
        items = self.pipeline.items
        if not items:
            return
        for item in items:
            if item.parm is None:
                continue
            if use_labels:
                display = item.parm.parmTemplate().label()
                item.source_path = f"{item.parm.node().path()}/{display}"
            else:
                item.source_path = item.parm.path()
        self._process_list.set_items(items)
        self._update_preview()

    def _on_items_removed(self) -> None:
        """Sync pipeline after items are removed via context menu."""
        self.pipeline.set_items(self._process_list.items)
        self._update_run_state()
        self._update_preview()

    # ── Node scope expansion ───────────────────────────────

    def _get_target_nodes(self) -> List[hou.Node]:
        scope = self._scope_combo.currentData()
        selected = list(hou.selectedNodes())

        if scope == "selected":
            return selected

        if scope == "siblings":
            seen = set()
            nodes: List[hou.Node] = []
            for node in selected:
                parent = node.parent()
                if parent is None or parent.path() in seen:
                    continue
                seen.add(parent.path())
                nodes.extend(parent.children())
            return nodes

        if scope == "selected_children":
            nodes = list(selected)
            for node in selected:
                nodes.extend(node.children())
            return nodes

        if scope == "selected_all_sub":
            nodes = list(selected)
            for node in selected:
                nodes.extend(node.allSubChildren())
            return nodes

        if scope == "children_only":
            nodes = []
            for node in selected:
                nodes.extend(node.children())
            return nodes

        if scope == "all_sub_only":
            nodes = []
            for node in selected:
                nodes.extend(node.allSubChildren())
            return nodes

        if scope == "all_scene":
            root = hou.node("/")
            if root is None:
                return []
            return list(root.allSubChildren())

        return selected
