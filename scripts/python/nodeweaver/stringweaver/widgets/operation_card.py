"""Widget for configuring a single operation in the pipeline."""

from typing import Dict, Optional

from .._qt import FrameShadow, FrameShape, QtWidgets, Signal
from ..operations.base import Operation


class OperationCard(QtWidgets.QFrame):
    """A card widget that displays and configures one Operation.

    Auto-generates input fields from the operation's config_fields()
    descriptors. Adding new operation types requires no widget changes.

    Signals:
        config_changed: Emitted when any config field is modified.
        remove_requested: Emitted when the user clicks the remove button.
        move_up_requested: Emitted when the user clicks the move-up button.
        move_down_requested: Emitted when the user clicks the move-down button.
    """

    config_changed = Signal()
    remove_requested = Signal()
    move_up_requested = Signal()
    move_down_requested = Signal()

    def __init__(self, operation: Operation,
                 parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.operation = operation
        self._field_widgets: Dict[str, QtWidgets.QWidget] = {}
        self._field_rows: Dict[str, QtWidgets.QWidget] = {}  # row containers for show/hide
        self._visibility_rules: list = []  # (target_name, field_name, value)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFrameStyle(FrameShape.StyledPanel | FrameShadow.Raised)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Header: operation name + move/remove buttons
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(4)
        title = QtWidgets.QLabel(f"<b>{self.operation.name}</b>")
        header.addWidget(title)
        header.addStretch()

        up_btn = QtWidgets.QToolButton()
        up_btn.setText("\u25B2")
        up_btn.setToolTip("Move up")
        up_btn.setFixedSize(40, 40)
        up_btn.clicked.connect(self.move_up_requested.emit)
        header.addWidget(up_btn)

        down_btn = QtWidgets.QToolButton()
        down_btn.setText("\u25BC")
        down_btn.setToolTip("Move down")
        down_btn.setFixedSize(40, 40)
        down_btn.clicked.connect(self.move_down_requested.emit)
        header.addWidget(down_btn)

        remove_btn = QtWidgets.QToolButton()
        remove_btn.setText("\u2715")
        remove_btn.setToolTip("Remove")
        remove_btn.setFixedSize(40, 40)
        remove_btn.clicked.connect(self.remove_requested.emit)
        header.addWidget(remove_btn)

        layout.addLayout(header)

        # Config fields generated from operation descriptor
        fields_grid = QtWidgets.QGridLayout()
        fields_grid.setSpacing(4)
        fields_grid.setHorizontalSpacing(10)
        fields_grid.setColumnStretch(1, 1)  # input column stretches

        for row_idx, field in enumerate(self.operation.config_fields()):
            widget = self._create_field_widget(field)
            if widget is not None:
                self._field_widgets[field["name"]] = widget
                lbl = QtWidgets.QLabel(field["label"] + ":")
                fields_grid.addWidget(lbl, row_idx, 0)
                fields_grid.addWidget(widget, row_idx, 1)
                # Store both label and widget for show/hide
                self._field_rows[field["name"]] = (lbl, widget)

                # Collect visibility rules
                vis = field.get("visible_when")
                if vis:
                    self._visibility_rules.append(
                        (field["name"], vis["field"], vis["value"])
                    )

        layout.addLayout(fields_grid)

        # Apply initial visibility and wire up drivers
        self._update_field_visibility()
        for target_name, driver_name, _ in self._visibility_rules:
            driver = self._field_widgets.get(driver_name)
            if isinstance(driver, QtWidgets.QComboBox):
                driver.currentIndexChanged.connect(self._update_field_visibility)

    def _create_field_widget(self, field: dict) -> Optional[QtWidgets.QWidget]:
        field_type = field["type"]
        default = field.get("default", "")

        if field_type == "text":
            widget = QtWidgets.QLineEdit()
            widget.setText(str(default))
            widget.textChanged.connect(self._on_field_changed)
            return widget

        if field_type == "int":
            widget = QtWidgets.QSpinBox()
            widget.setRange(
                field.get("min", -999999),
                field.get("max", 999999),
            )
            widget.setValue(int(default))
            widget.valueChanged.connect(self._on_field_changed)
            return widget

        if field_type == "bool":
            widget = QtWidgets.QCheckBox()
            widget.setChecked(bool(default))
            widget.toggled.connect(self._on_field_changed)
            return widget

        if field_type == "choice":
            widget = QtWidgets.QComboBox()
            options = field.get("options", [])
            for value, label in options:
                widget.addItem(label, value)
            idx = widget.findData(default)
            if idx >= 0:
                widget.setCurrentIndex(idx)
            widget.currentIndexChanged.connect(self._on_field_changed)
            return widget

        return None

    def _update_field_visibility(self) -> None:
        """Show/hide fields based on visible_when rules.

        The ``value`` in a rule can be a single value or a list of values.
        """
        for target_name, driver_name, required_value in self._visibility_rules:
            driver = self._field_widgets.get(driver_name)
            row = self._field_rows.get(target_name)
            if driver is None or row is None:
                continue
            if isinstance(driver, QtWidgets.QComboBox):
                current = driver.currentData()
            else:
                continue
            if isinstance(required_value, list):
                visible = current in required_value
            else:
                visible = current == required_value
            lbl, widget = row
            lbl.setVisible(visible)
            widget.setVisible(visible)

    def _on_field_changed(self) -> None:
        """Read all field widgets and update the operation config."""
        config = {}
        for field in self.operation.config_fields():
            name = field["name"]
            widget = self._field_widgets.get(name)
            if widget is None:
                continue
            if isinstance(widget, QtWidgets.QLineEdit):
                config[name] = widget.text()
            elif isinstance(widget, QtWidgets.QSpinBox):
                config[name] = widget.value()
            elif isinstance(widget, QtWidgets.QCheckBox):
                config[name] = widget.isChecked()
            elif isinstance(widget, QtWidgets.QComboBox):
                config[name] = widget.currentData()
        self.operation.set_config(config)
        self._update_field_visibility()
        self.config_changed.emit()
