"""User interface for the "Gripper" tab."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from hfm_analyzer.gui.main_window import ModernMainWindow


class GripperTab(QWidget):
    """Displays gripper statistics and filters."""

    def __init__(self, window: ModernMainWindow) -> None:
        super().__init__()
        self._window = window
        self._build_ui()

    def _build_ui(self) -> None:
        window = self._window
        window.hp_grip_tab = self

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        filters.addWidget(QLabel("Maszyna:"))
        window.hp_grip_machine = QComboBox()
        window.hp_grip_machine.currentIndexChanged.connect(window._on_hp_grip_machine_changed)
        filters.addWidget(window.hp_grip_machine)
        filters.addWidget(QLabel("Pin:"))
        window.hp_grip_pin = QComboBox()
        window.hp_grip_pin.currentIndexChanged.connect(window._apply_hp_grip_filters)
        filters.addWidget(window.hp_grip_pin)
        filters.addStretch(1)
        layout.addLayout(filters)

        window.hp_grip_table = QTableWidget(0, 0)
        window.hp_grip_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        window.hp_grip_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        window.hp_grip_table.setSelectionMode(QAbstractItemView.SingleSelection)
        window.hp_grip_table.setAlternatingRowColors(True)
        layout.addWidget(window.hp_grip_table, 1)


__all__ = ["GripperTab"]
