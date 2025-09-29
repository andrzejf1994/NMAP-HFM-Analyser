"""User interface for the "Nest" tab."""

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


class NestTab(QWidget):
    """Displays nest configuration statistics and filters."""

    def __init__(self, window: ModernMainWindow) -> None:
        super().__init__()
        self._window = window
        self._build_ui()

    def _build_ui(self) -> None:
        window = self._window
        window.nest_tab = self

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        filters.addWidget(QLabel("Maszyna:"))
        window.nest_machine = QComboBox()
        window.nest_machine.currentIndexChanged.connect(window._on_nest_machine_changed)
        filters.addWidget(window.nest_machine)
        filters.addWidget(QLabel("Pin:"))
        window.nest_pin = QComboBox()
        window.nest_pin.currentIndexChanged.connect(window._apply_nest_filters)
        filters.addWidget(window.nest_pin)
        filters.addStretch(1)
        layout.addLayout(filters)

        window.nest_table = QTableWidget(0, 0)
        window.nest_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        window.nest_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        window.nest_table.setSelectionMode(QAbstractItemView.SingleSelection)
        window.nest_table.setAlternatingRowColors(True)
        layout.addWidget(window.nest_table, 1)


__all__ = ["NestTab"]
