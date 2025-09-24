"""Tab widgets exposed by the GUI package."""

from .changes_tab import ChangesTab
from .changes_chart_tab import ChangesChartTab
from .parameter_changes_tab import ParameterChangesTab
from .program_changes_tab import ProgramChangesTab
from .stripping_tab import StrippingTab
from .insertion_tab import InsertionTab

__all__ = [
    "ChangesTab",
    "ChangesChartTab",
    "ParameterChangesTab",
    "ProgramChangesTab",
    "StrippingTab",
    "InsertionTab",
]
