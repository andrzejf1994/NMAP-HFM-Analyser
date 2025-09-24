"""User interface for the "Zmiany Programów" tab."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

if TYPE_CHECKING:
    from hfm_analyzer.gui.main_window import ModernMainWindow


class ProgramChangesTab(QWidget):
    """Displays program change history with filtering options."""

    def __init__(self, window: ModernMainWindow) -> None:
        super().__init__()
        self._window = window
        self._build_ui()

    def _build_ui(self) -> None:
        window = self._window
        window.programs_tab = self

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        filters = QHBoxLayout()
        filters.setSpacing(8)

        window.pg_f_machine = QComboBox()
        window.pg_f_machine.currentIndexChanged.connect(window._apply_program_filters)
        window.pg_f_old = QComboBox()
        window.pg_f_old.currentIndexChanged.connect(window._apply_program_filters)
        window.pg_f_new = QComboBox()
        window.pg_f_new.currentIndexChanged.connect(window._apply_program_filters)

        def _label(text: str) -> QLabel:
            widget = QLabel(text)
            widget.setStyleSheet("color:#2c3e50;font-weight:600;")
            return widget

        filters.addWidget(_label("Maszyna:"))
        filters.addWidget(window.pg_f_machine)
        filters.addWidget(_label("Stary program:"))
        filters.addWidget(window.pg_f_old)
        filters.addWidget(_label("Nowy program:"))
        filters.addWidget(window.pg_f_new)
        filters.addStretch(1)
        layout.addLayout(filters)

        window.program_table = QTableWidget(0, 4)
        window.program_table.setHorizontalHeaderLabels([
            "Data",
            "Czas",
            "Maszyna",
            "Program (stary -> nowy)",
        ])
        window.program_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        window.program_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        window.program_table.setSelectionMode(QAbstractItemView.SingleSelection)
        for column in range(4):
            window.program_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        layout.addWidget(window.program_table, 1)

        export_btn = QPushButton("Eksport CSV")
        export_btn.clicked.connect(window._export_programs_csv)
        layout.addWidget(export_btn)


__all__ = ["ProgramChangesTab"]
