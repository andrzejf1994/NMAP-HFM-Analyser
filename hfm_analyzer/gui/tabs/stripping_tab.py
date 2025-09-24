"""User interface for the "Odizolowanie" tab."""

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


class StrippingTab(QWidget):
    """Displays stripping statistics and filters."""

    def __init__(self, window: ModernMainWindow) -> None:
        super().__init__()
        self._window = window
        self._build_ui()

    def _build_ui(self) -> None:
        window = self._window
        window.stripping_tab = self

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        filters.addWidget(QLabel("Maszyna:"))
        window.stripping_machine = QComboBox()
        window.stripping_machine.currentIndexChanged.connect(window._on_stripping_machine_changed)
        filters.addWidget(window.stripping_machine)
        filters.addWidget(QLabel("Pin:"))
        window.stripping_pin = QComboBox()
        window.stripping_pin.currentIndexChanged.connect(window._apply_stripping_filters)
        filters.addWidget(window.stripping_pin)
        filters.addStretch(1)
        layout.addLayout(filters)

        window.stripping_table = QTableWidget(0, 0)
        window.stripping_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        window.stripping_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        window.stripping_table.setSelectionMode(QAbstractItemView.SingleSelection)
        window.stripping_table.setAlternatingRowColors(True)
        layout.addWidget(window.stripping_table, 1)


__all__ = ["StrippingTab"]
