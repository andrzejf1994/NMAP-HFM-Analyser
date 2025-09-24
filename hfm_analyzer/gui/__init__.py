"""GUI package exposing the main window and related components."""

from .dialogs import NetworkCheckDialog, SettingsDialog
from .main_window import ModernMainWindow
from .widgets import BarChartWidget, CountBadgeDelegate, PieChartWidget

__all__ = [
    "PieChartWidget",
    "BarChartWidget",
    "CountBadgeDelegate",
    "SettingsDialog",
    "NetworkCheckDialog",
    "ModernMainWindow",
]
