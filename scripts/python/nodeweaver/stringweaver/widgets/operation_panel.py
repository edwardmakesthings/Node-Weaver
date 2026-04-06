"""Panel widget for managing the operation pipeline."""

import json
import os
from typing import List, Optional

from .._qt import FrameShape, QtWidgets, Signal, ToolButtonPopupMode
from ..operations import REGISTRY, Operation, create_operation
from .operation_card import OperationCard

# Default preset directory under Houdini user prefs
_PRESET_DIR = os.path.join(
    os.environ.get("HOUDINI_USER_PREF_DIR", os.path.expanduser("~/houdini21.0")),
    "stringweaver_presets",
)


class OperationPanel(QtWidgets.QWidget):
    """Vertical panel displaying stacked operation cards.

    Provides add/remove/reorder controls for the operation pipeline.

    Signals:
        operations_changed: Emitted when operations are added, removed,
            reordered, or their configuration changes.
    """

    operations_changed = Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._cards: List[OperationCard] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # Header with add-operation menu
        header = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("<b>Operations</b>")
        header.addWidget(label)
        header.addStretch()

        self._add_btn = QtWidgets.QToolButton()
        self._add_btn.setText("+")
        self._add_btn.setToolTip("Add operation")
        self._add_btn.setFixedSize(40, 40)
        font = self._add_btn.font()
        font.setPointSize(16)
        self._add_btn.setFont(font)
        self._add_btn.setPopupMode(ToolButtonPopupMode.InstantPopup)
        add_menu = QtWidgets.QMenu(self._add_btn)
        for key, cls in REGISTRY.items():
            instance = cls()
            action = add_menu.addAction(instance.name)
            action.setData(key)
            action.triggered.connect(lambda checked=False, k=key: self._add_operation(k))
        self._add_btn.setMenu(add_menu)
        header.addWidget(self._add_btn)

        # Preset buttons — use basic symbols that render in all Qt fonts
        self._save_preset_btn = QtWidgets.QToolButton()
        self._save_preset_btn.setText("\u2B07")  # downwards arrow (save)
        self._save_preset_btn.setToolTip("Save preset")
        self._save_preset_btn.setFixedSize(40, 40)
        font = self._save_preset_btn.font()
        font.setPointSize(14)
        self._save_preset_btn.setFont(font)
        self._save_preset_btn.clicked.connect(self._save_preset)
        header.addWidget(self._save_preset_btn)

        self._load_preset_btn = QtWidgets.QToolButton()
        self._load_preset_btn.setText("\u2B06")  # upwards arrow (load)
        self._load_preset_btn.setToolTip("Load preset")
        self._load_preset_btn.setFixedSize(40, 40)
        font = self._load_preset_btn.font()
        font.setPointSize(14)
        self._load_preset_btn.setFont(font)
        self._load_preset_btn.setPopupMode(ToolButtonPopupMode.InstantPopup)
        self._load_preset_menu = QtWidgets.QMenu(self._load_preset_btn)
        self._load_preset_btn.setMenu(self._load_preset_menu)
        self._load_preset_menu.aboutToShow.connect(self._populate_preset_menu)
        header.addWidget(self._load_preset_btn)

        outer_layout.addLayout(header)

        # Scrollable area for operation cards
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(FrameShape.NoFrame)
        self._cards_container = QtWidgets.QWidget()
        self._cards_layout = QtWidgets.QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(4)
        self._cards_layout.addStretch()
        scroll.setWidget(self._cards_container)
        outer_layout.addWidget(scroll)

    def _add_operation(self, type_key: str) -> None:
        operation = create_operation(type_key)
        self.add_card(operation)

    def add_card(self, operation: Operation) -> OperationCard:
        """Add an operation card to the panel.

        Args:
            operation: The operation instance to display.

        Returns:
            The created OperationCard widget.
        """
        card = OperationCard(operation, parent=self._cards_container)
        card.config_changed.connect(self.operations_changed.emit)
        card.remove_requested.connect(lambda c=card: self._remove_card(c))
        card.move_up_requested.connect(lambda c=card: self._move_card(c, -1))
        card.move_down_requested.connect(lambda c=card: self._move_card(c, 1))

        # Insert before the trailing stretch
        self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
        self._cards.append(card)
        self.operations_changed.emit()
        return card

    def _remove_card(self, card: OperationCard) -> None:
        if card in self._cards:
            self._cards.remove(card)
            self._cards_layout.removeWidget(card)
            card.deleteLater()
            self.operations_changed.emit()

    def _move_card(self, card: OperationCard, direction: int) -> None:
        if card not in self._cards:
            return
        idx = self._cards.index(card)
        new_idx = idx + direction
        if not (0 <= new_idx < len(self._cards)):
            return

        # Swap in list
        self._cards[idx], self._cards[new_idx] = self._cards[new_idx], self._cards[idx]

        # Rebuild layout order (remove all, re-insert in order)
        for c in self._cards:
            self._cards_layout.removeWidget(c)
        for i, c in enumerate(self._cards):
            self._cards_layout.insertWidget(i, c)

        self.operations_changed.emit()

    def get_operations(self) -> List[Operation]:
        """Return the ordered list of operations from all cards."""
        return [card.operation for card in self._cards]

    def clear(self) -> None:
        """Remove all operation cards."""
        for card in self._cards[:]:
            self._remove_card(card)

    # ── Preset serialization ───────────────────────────────

    def get_preset_data(self) -> list:
        """Serialize current operations to a list of dicts."""
        data = []
        for card in self._cards:
            op = card.operation
            type_key = next(
                (k for k, cls in REGISTRY.items() if isinstance(op, cls)), None
            )
            if type_key is not None:
                data.append({"type": type_key, "config": op.get_config()})
        return data

    def load_preset_data(self, data: list) -> None:
        """Restore operations from a serialized preset list."""
        self.clear()
        for entry in data:
            type_key = entry.get("type", "")
            config = entry.get("config", {})
            if type_key not in REGISTRY:
                continue
            op = create_operation(type_key)
            op.set_config(config)
            card = self.add_card(op)
            # Sync card widgets with loaded config
            for field in op.config_fields():
                name = field["name"]
                widget = card._field_widgets.get(name)
                if widget is None:
                    continue
                value = config.get(name, field.get("default", ""))
                if isinstance(widget, QtWidgets.QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QtWidgets.QSpinBox):
                    widget.setValue(int(value))
                elif isinstance(widget, QtWidgets.QCheckBox):
                    widget.setChecked(bool(value))
                elif isinstance(widget, QtWidgets.QComboBox):
                    idx = widget.findData(value)
                    if idx >= 0:
                        widget.setCurrentIndex(idx)

    def _save_preset(self) -> None:
        """Prompt for a name and save current operations as a JSON preset."""
        if not self._cards:
            return

        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save Preset", "Preset name:"
        )
        if not ok or not name.strip():
            return

        os.makedirs(_PRESET_DIR, exist_ok=True)
        # Sanitize filename
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name.strip())
        filepath = os.path.join(_PRESET_DIR, f"{safe_name}.json")

        if os.path.exists(filepath):
            result = QtWidgets.QMessageBox.question(
                self,
                "Overwrite Preset",
                f'A preset named "{safe_name}" already exists. Overwrite?',
            )
            if result != QtWidgets.QMessageBox.Yes:
                return

        data = self.get_preset_data()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _populate_preset_menu(self) -> None:
        """Rebuild the load-preset menu from files on disk."""
        self._load_preset_menu.clear()

        if not os.path.isdir(_PRESET_DIR):
            action = self._load_preset_menu.addAction("(no presets)")
            action.setEnabled(False)
            return

        files = sorted(
            f for f in os.listdir(_PRESET_DIR) if f.endswith(".json")
        )
        if not files:
            action = self._load_preset_menu.addAction("(no presets)")
            action.setEnabled(False)
            return

        for filename in files:
            preset_name = filename[:-5]  # strip .json
            action = self._load_preset_menu.addAction(preset_name)
            filepath = os.path.join(_PRESET_DIR, filename)
            action.triggered.connect(
                lambda checked=False, fp=filepath: self._load_preset(fp)
            )

        self._load_preset_menu.addSeparator()
        open_dir = self._load_preset_menu.addAction("Open Preset Folder")
        open_dir.triggered.connect(
            lambda: os.startfile(_PRESET_DIR) if os.path.isdir(_PRESET_DIR) else None
        )

    def _load_preset(self, filepath: str) -> None:
        """Load a preset from a JSON file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        if not isinstance(data, list):
            return

        self.load_preset_data(data)
