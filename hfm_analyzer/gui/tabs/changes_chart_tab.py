"""User interface for the "Wykres zmian" tab."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from hfm_analyzer.gui.widgets import BarChartWidget

if TYPE_CHECKING:
    from hfm_analyzer.gui.main_window import ModernMainWindow


class ChangesChartTab(QWidget):
    """Displays the native bar chart for change trends."""

    def __init__(self, window: ModernMainWindow) -> None:
        super().__init__()
        self._window = window
        self._build_ui()

    def _build_ui(self) -> None:
        window = self._window
        window.trends_tab = self

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        filters = QHBoxLayout()
        filters.setSpacing(8)

        window.t_f_machine = QComboBox()
        window.t_f_machine.currentIndexChanged.connect(window._apply_trend_filters)
        filters.addWidget(QLabel("Maszyna:"))
        filters.addWidget(window.t_f_machine)

        layout.addLayout(filters)

        window.trend_bar_native = BarChartWidget()
        window.trend_bar_native.setMinimumHeight(260)
        try:
            window.trend_bar_native.set_overlay_min_ymax(10)
        except Exception:
            pass
        layout.addWidget(window.trend_bar_native, 1)

        window._feeder_map_M = {2: "M1", 4: "M2", 6: "M3", 8: "M4", 10: "M5", 12: "M6"}
        window._feeder_map_S = {1: "S1", 3: "S2", 5: "S3", 7: "S4", 9: "S5", 11: "S6"}


__all__ = ["ChangesChartTab"]
