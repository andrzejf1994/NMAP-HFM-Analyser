"""User interface for the "Zmiany Parametrów" tab."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ..constants import PARAM_DISPLAY_ORDER

if TYPE_CHECKING:
    from ..main_window import ModernMainWindow


class ParameterChangesTab(QWidget):
    """Encapsulates the parameter changes table and filters."""

    def __init__(self, window: ModernMainWindow) -> None:
        super().__init__()
        self._window = window
        self._build_ui()

    def _build_ui(self) -> None:
        window = self._window
        window.analysis_tab = self

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        filt_row = QHBoxLayout()
        filt_row.setSpacing(8)

        window.f_machine = QComboBox()
        window.f_machine.setEditable(False)
        window.f_machine.currentIndexChanged.connect(window._on_analysis_machine_changed)
        window.f_pin = QComboBox()
        window.f_pin.currentIndexChanged.connect(window._on_analysis_pin_changed)
        window.f_step = QComboBox()
        window.f_step.currentIndexChanged.connect(window._on_analysis_step_changed)
        window.f_param = QComboBox()
        window.f_param.currentIndexChanged.connect(window._apply_analysis_filters)

        def _label(text: str) -> QLabel:
            widget = QLabel(text)
            widget.setStyleSheet("color:#2c3e50;font-weight:600;")
            return widget

        filt_row.addWidget(_label("Maszyna:"))
        filt_row.addWidget(window.f_machine)
        filt_row.addWidget(_label("Pin:"))
        filt_row.addWidget(window.f_pin)
        filt_row.addWidget(_label("Step:"))
        filt_row.addWidget(window.f_step)
        filt_row.addWidget(_label("Parametr:"))
        filt_row.addWidget(window.f_param)
        filt_row.addStretch(1)

        run_btn = QPushButton("Analizuj zmiany")
        run_btn.clicked.connect(window._start_analysis)
        window.analysis_run_btn = run_btn
        filt_row.addWidget(run_btn)

        stop_btn = QPushButton("Zatrzymaj analizę")
        stop_btn.clicked.connect(window._stop_analysis)
        window.analysis_stop_btn = stop_btn
        filt_row.addWidget(stop_btn)

        export_btn = QPushButton("Eksport CSV")
        export_btn.clicked.connect(window._export_analysis_csv)
        filt_row.addWidget(export_btn)

        layout.addLayout(filt_row)

        window.analysis_table = QTableWidget(0, 15)
        window.analysis_table.setHorizontalHeaderLabels([
            "Data",
            "Czas",
            "Maszyna",
            "Program",
            "Tabela",
            "Pin",
            "Step",
            "Angle",
            "Nose Locking",
            "Nose Translation",
            "Rotation",
            "Wire Feeding",
            "X",
            "Y",
            "Ă„Ä…ÄąË‡cieĂ„Ä…Ă„Ëťka",
        ])
        try:
            params = PARAM_DISPLAY_ORDER
            fixed_cols = ["Data", "Czas", "Maszyna", "Program", "Tabela", "Pin", "Step"]
            path_col = "Ścieżka"
            total_cols = len(fixed_cols) + len(params) + 1
            window.analysis_table.setColumnCount(total_cols)
            window.analysis_table.setHorizontalHeaderLabels(fixed_cols + list(params) + [path_col])
        except Exception:
            pass
        window.analysis_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        window.analysis_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        window.analysis_table.setSelectionMode(QAbstractItemView.SingleSelection)
        for column in range(window.analysis_table.columnCount()):
            window.analysis_table.horizontalHeader().setSectionResizeMode(column, window.analysis_table.horizontalHeader().ResizeToContents)

        try:
            params = PARAM_DISPLAY_ORDER
            fixed_cols = 7
            total_cols = fixed_cols + len(params) + 1
            window.analysis_table.setColumnHidden(total_cols - 1, True)
        except Exception:
            window.analysis_table.setColumnHidden(14, True)
        layout.addWidget(window.analysis_table, 1)


__all__ = ["ParameterChangesTab"]
