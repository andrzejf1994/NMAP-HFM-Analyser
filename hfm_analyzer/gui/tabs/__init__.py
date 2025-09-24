"""Tab widgets exposed by the GUI package."""

from hfm_analyzer.gui.tabs.changes_tab import ChangesTab
from hfm_analyzer.gui.tabs.changes_chart_tab import ChangesChartTab
from hfm_analyzer.gui.tabs.parameter_changes_tab import ParameterChangesTab
from hfm_analyzer.gui.tabs.program_changes_tab import ProgramChangesTab
from hfm_analyzer.gui.tabs.stripping_tab import StrippingTab
from hfm_analyzer.gui.tabs.insertion_tab import InsertionTab

__all__ = [
    "ChangesTab",
    "ChangesChartTab",
    "ParameterChangesTab",
    "ProgramChangesTab",
    "StrippingTab",
    "InsertionTab",
]
