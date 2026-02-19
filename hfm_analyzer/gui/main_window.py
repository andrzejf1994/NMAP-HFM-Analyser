"""Main window implementation for the HFM Analyzer GUI."""

from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import QDateTime, QSettings, QTime, Qt, QSize
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QDateTimeEdit,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTextEdit,
    QToolButton,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QAbstractItemView,
)

from hfm_analyzer.constants import (
    INDEX_PARAM_DISPLAY_ORDER,
    PARAM_DISPLAY_ORDER,
    SUMMARY_PALETTE,
)
from hfm_analyzer.data_labels import (
    GRIP_PARAM_ORDER,
    HAIRPIN_PARAM_ORDER,
    NEST_PARAM_ORDER,
)
from hfm_analyzer.models import (
    FoundFile,
    GripSnapshot,
    HairpinSnapshot,
    IndexSnapshot,
    ParamSnapshot,
)
from hfm_analyzer.gui.handlers import MainWindowHandlers
from hfm_analyzer.gui.tabs import (
    ChangesTab,
    ChangesChartTab,
    ParameterChangesTab,
    ProgramChangesTab,
    StrippingTab,
    GripperTab,
    NestTab,
)
from hfm_analyzer.gui.widgets import LineChartWidget, ParetoChartWidget


def _label(text: str) -> QLabel:
    """Create a consistently styled label used across filter toolbars."""

    widget = QLabel(text)
    widget.setStyleSheet("color:#2c3e50;font-weight:600;")
    return widget


class ModernMainWindow(MainWindowHandlers, QMainWindow):
    def __init__(self, settings: QSettings):
        super().__init__()
        self.settings = settings
        try:
            self.runtime_cache = self._create_runtime_cache()
        except Exception:
            self.runtime_cache = None
        if self.runtime_cache is None:
            self.runtime_cache_path = ""
        app = QApplication.instance()
        if app is not None and not app.windowIcon().isNull():
            self.setWindowIcon(app.windowIcon())
        self.setWindowTitle("HFM Analyzer")
        self.setMinimumSize(1000, 680)
    
        self.found_files: list[FoundFile] = []
        self._all_machines: list[str] = []
    
    
        toolbar = self.addToolBar("Główny")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
    
        title = QLabel("HFM Analyzer")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        toolbar.addWidget(title)
        toolbar.addSeparator()
    
        self.base_path_label = QLabel()
        self.base_path_label.setTextFormat(Qt.RichText)
        toolbar.addWidget(self.base_path_label)
        toolbar.addSeparator()
    
        #choose_base = QAction("Zmień katalog", self)
        #choose_base.triggered.connect(self._browse_base_path)
        #toolbar.addAction(choose_base)
    
        settings_act = QAction("Ustawienia", self)
        settings_act.triggered.connect(self._open_settings)
        toolbar.addAction(settings_act)
    
    
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
    
    
        filters_box = QGroupBox("Filtry i zakres")
        filters_box.setFont(QFont("Segoe UI", 10, QFont.Bold))
    
        filters_box.setMaximumWidth(420)
        filters = QHBoxLayout(filters_box)
        filters.setSpacing(8)
        filters.setContentsMargins(10, 10, 10, 10)
    
    
        machines_col = QVBoxLayout()
        machines_col.addWidget(QLabel("Maszyny"))
        self.machine_list = QListWidget()
        self.machine_list.setSelectionMode(QListWidget.MultiSelection)
        self.machine_list.setAlternatingRowColors(True)
    
        from PyQt5.QtWidgets import QSizePolicy
        self.machine_list.setMinimumWidth(140)
        self.machine_list.setMaximumWidth(160)
        self.machine_list.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        machines_col.addWidget(self.machine_list, 1)
    
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        sel_all = QToolButton()
        sel_all.setToolTip("Zaznacz wszystkie")
        sel_all.setIcon(self._make_action_icon('select'))
        sel_all.clicked.connect(self._select_all)
        desel_all = QToolButton()
        desel_all.setToolTip("Odznacz wszystkie")
        desel_all.setIcon(self._make_action_icon('deselect'))
        desel_all.clicked.connect(self._deselect_all)
        refresh_btn = QToolButton()
        refresh_btn.setToolTip("Odśwież listę")
        refresh_btn.setIcon(self._make_action_icon('refresh'))
        refresh_btn.clicked.connect(self._populate_machines)
        refresh_btn.setToolTip("Odśwież listę")
        for b in (sel_all, desel_all, refresh_btn):
            b.setAutoRaise(False)
            b.setToolButtonStyle(Qt.ToolButtonIconOnly)
            b.setIconSize(QSize(18, 18))
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setMinimumHeight(28)
            b.setProperty("class", "filters")
            btn_row.addWidget(b, 1)
    
        btn_row_widget = QWidget()
        btn_row_widget.setLayout(btn_row)
        btn_row_widget.setMaximumWidth(self.machine_list.maximumWidth())
        machines_col.addWidget(btn_row_widget)
    
    
        range_col = QGridLayout()
    
        range_col.setHorizontalSpacing(0)
        range_col.setVerticalSpacing(8)
        range_col.setContentsMargins(0, 0, 0, 0)
    
        range_col.setColumnStretch(0, 0)
        range_col.setColumnStretch(1, 1)
        range_col.setColumnMinimumWidth(0, 26)
        od_lbl = QLabel("Od:")
        od_lbl.setMargin(0)
        od_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        range_col.addWidget(od_lbl, 0, 0)
        self.start_datetime = QDateTimeEdit(calendarPopup=True)
        self.start_datetime.setDisplayFormat("yyyy-MM-dd HH:mm")
    
        self.start_datetime.setMinimumWidth(180)
        range_col.addWidget(self.start_datetime, 0, 1)
        do_lbl = QLabel("Do:")
        do_lbl.setMargin(0)
        do_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        range_col.addWidget(do_lbl, 1, 0)
        self.end_datetime = QDateTimeEdit(calendarPopup=True)
        self.end_datetime.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.end_datetime.setMinimumWidth(180)
        range_col.addWidget(self.end_datetime, 1, 1)
        self.scan_btn = QPushButton("Rozpocznij analizę")
        self.scan_btn.clicked.connect(self._start_scan)
        range_col.addWidget(self.scan_btn, 2, 0, 1, 2)
    
    
        machines_widget = QWidget()
        machines_widget.setLayout(machines_col)
        machines_widget.setMaximumWidth(self.machine_list.maximumWidth() + 10)
        filters.addWidget(machines_widget, 0)
        filters.addLayout(range_col, 1)
    
    
    
        self.tabs = QTabWidget()
    
    
        self.changes_tab_widget = ChangesTab(self, root, filters_box)
        self.tabs.addTab(self.changes_tab_widget, "Zmiany")
    
        self.changes_chart_tab_widget = ChangesChartTab(self)
        self.tabs.addTab(self.changes_chart_tab_widget, "Wykres zmian")
    
        self.parameter_changes_tab_widget = ParameterChangesTab(self)
        self.tabs.addTab(self.parameter_changes_tab_widget, "Zmiany Parametrów")
    
    
        self.index_tab = QWidget()
        idx_layout = QVBoxLayout(self.index_tab)
        idx_layout.setContentsMargins(12, 12, 12, 12)
        idx_layout.setSpacing(8)
    
        idx_filt = QHBoxLayout()
        idx_filt.setSpacing(8)
        self.idx_f_machine = QComboBox()
        self.idx_f_machine.currentIndexChanged.connect(self._on_index_machine_changed)
        self.idx_f_table = QComboBox()
        self.idx_f_table.currentIndexChanged.connect(self._on_index_table_changed)
        self.idx_f_step = QComboBox()
        self.idx_f_step.currentIndexChanged.connect(self._on_index_step_changed)
        self.idx_f_param = QComboBox()
        self.idx_f_param.currentIndexChanged.connect(self._apply_index_filters)
    
        idx_filt.addWidget(_label("Maszyna:"))
        idx_filt.addWidget(self.idx_f_machine)
        idx_filt.addWidget(_label("Tabela:"))
        idx_filt.addWidget(self.idx_f_table)
        idx_filt.addWidget(_label("Step:"))
        idx_filt.addWidget(self.idx_f_step)
        idx_filt.addWidget(_label("Parametr:"))
        idx_filt.addWidget(self.idx_f_param)
        idx_filt.addStretch(1)
    
        idx_export_btn = QPushButton("Eksport CSV")
        idx_export_btn.clicked.connect(self._export_index_csv)
        idx_filt.addWidget(idx_export_btn)
    
        idx_layout.addLayout(idx_filt)
    
        idx_params = INDEX_PARAM_DISPLAY_ORDER
        idx_fixed_cols = ["Data", "Czas", "Maszyna", "Program", "Tabela", "Step"]
        idx_total_cols = len(idx_fixed_cols) + len(idx_params) + 1
        self.index_table = QTableWidget(0, idx_total_cols)
        self.index_table.setHorizontalHeaderLabels(idx_fixed_cols + idx_params + ["Ścieżka"])
        self.index_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.index_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.index_table.setSelectionMode(QAbstractItemView.SingleSelection)
        for ci in range(self.index_table.columnCount()):
            self.index_table.horizontalHeader().setSectionResizeMode(ci, QHeaderView.ResizeToContents)
        self.index_table.setColumnHidden(idx_total_cols - 1, True)
        idx_layout.addWidget(self.index_table, 1)
    
        self.tabs.addTab(self.index_tab, "Zmiany parametrów stołu")
    
    
        self.param_chart_tab = QWidget()
        pc_layout = QVBoxLayout(self.param_chart_tab)
        pc_layout.setContentsMargins(12, 12, 12, 12)
        pc_layout.setSpacing(8)
    
        pc_filters = QHBoxLayout()
        pc_filters.setSpacing(8)
        self.param_line_machine = QComboBox()
        self.param_line_machine.currentIndexChanged.connect(self._on_param_line_machine_changed)
        self.param_line_pin = QComboBox()
        self.param_line_pin.currentIndexChanged.connect(self._on_param_line_pin_changed)
        self.param_line_step = QComboBox()
        self.param_line_generate = QPushButton("Generuj wykresy")
        self.param_line_generate.clicked.connect(self._apply_param_line_filters)
    
        pc_filters.addWidget(_label("Maszyna:"))
        pc_filters.addWidget(self.param_line_machine)
        pc_filters.addWidget(_label("Pin:"))
        pc_filters.addWidget(self.param_line_pin)
        pc_filters.addWidget(_label("Step:"))
        pc_filters.addWidget(self.param_line_step)
        pc_filters.addWidget(self.param_line_generate)
        pc_filters.addStretch(1)
        pc_layout.addLayout(pc_filters)
    
        self.param_chart_scroll = QScrollArea()
        self.param_chart_scroll.setWidgetResizable(True)
        self.param_chart_scroll.setFrameShape(QScrollArea.NoFrame)
        pc_layout.addWidget(self.param_chart_scroll, 1)
    
        pc_container = QWidget()
        pc_container_layout = QVBoxLayout(pc_container)
        pc_container_layout.setContentsMargins(0, 0, 0, 0)
        pc_container_layout.setSpacing(12)
    
        self.param_line_charts: dict[str, LineChartWidget] = {}
        self._param_line_colors: dict[str, QColor] = {}
        for idx, name in enumerate(PARAM_DISPLAY_ORDER):
            group = QGroupBox(name)
            group_layout = QVBoxLayout(group)
            chart = LineChartWidget()
            chart.setMinimumHeight(220)
            chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            group_layout.addWidget(chart)
            pc_container_layout.addWidget(group)
            self.param_line_charts[name] = chart
            self._param_line_colors[name] = QColor(SUMMARY_PALETTE[idx % len(SUMMARY_PALETTE)])
    
        pc_container_layout.addStretch(1)
        self.param_chart_scroll.setWidget(pc_container)
    
        self.tabs.addTab(self.param_chart_tab, "Wykresy parametrów")
    
    
        self.index_chart_tab = QWidget()
        ic_layout = QVBoxLayout(self.index_chart_tab)
        ic_layout.setContentsMargins(12, 12, 12, 12)
        ic_layout.setSpacing(8)
    
        ic_filters = QHBoxLayout()
        ic_filters.setSpacing(8)
        self.index_line_machine = QComboBox()
        self.index_line_machine.currentIndexChanged.connect(self._on_index_line_machine_changed)
        self.index_line_pin = QComboBox()
        self.index_line_pin.currentIndexChanged.connect(self._on_index_line_pin_changed)
        self.index_line_step = QComboBox()
        self.index_line_generate = QPushButton("Generuj wykresy")
        self.index_line_generate.clicked.connect(self._apply_index_line_filters)
    
        ic_filters.addWidget(_label("Maszyna:"))
        ic_filters.addWidget(self.index_line_machine)
        ic_filters.addWidget(_label("Tablica:"))
        ic_filters.addWidget(self.index_line_pin)
        ic_filters.addWidget(_label("Step:"))
        ic_filters.addWidget(self.index_line_step)
        ic_filters.addWidget(self.index_line_generate)
        ic_filters.addStretch(1)
        ic_layout.addLayout(ic_filters)
    
        self.index_chart_scroll = QScrollArea()
        self.index_chart_scroll.setWidgetResizable(True)
        self.index_chart_scroll.setFrameShape(QScrollArea.NoFrame)
        ic_layout.addWidget(self.index_chart_scroll, 1)
    
        ic_container = QWidget()
        ic_container_layout = QVBoxLayout(ic_container)
        ic_container_layout.setContentsMargins(0, 0, 0, 0)
        ic_container_layout.setSpacing(12)
    
        self.index_line_charts: dict[str, LineChartWidget] = {}
        self._index_line_colors: dict[str, QColor] = {}
        for idx, name in enumerate(INDEX_PARAM_DISPLAY_ORDER):
            group = QGroupBox(name)
            group_layout = QVBoxLayout(group)
            chart = LineChartWidget()
            chart.setMinimumHeight(220)
            chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            group_layout.addWidget(chart)
            ic_container_layout.addWidget(group)
            self.index_line_charts[name] = chart
            self._index_line_colors[name] = QColor(SUMMARY_PALETTE[idx % len(SUMMARY_PALETTE)])
    
        ic_container_layout.addStretch(1)
        self.index_chart_scroll.setWidget(ic_container)
    
        self.tabs.addTab(self.index_chart_tab, "Wykresy parametrów stołu")
    
    
        self.program_changes_tab_widget = ProgramChangesTab(self)
        self.tabs.addTab(self.program_changes_tab_widget, "Zmiany Programów")
    
    
    
        self.param_card_tab = QWidget()
        card_layout = QVBoxLayout(self.param_card_tab)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)
    
        card_filters = QHBoxLayout()
        card_filters.setSpacing(8)
        card_filters.addWidget(QLabel("Maszyna:"))
        self.param_card_machine = QComboBox()
        self.param_card_machine.setEnabled(False)
        self.param_card_machine.currentIndexChanged.connect(self._on_param_card_machine_changed)
        card_filters.addWidget(self.param_card_machine, 1)
        card_filters.addWidget(QLabel("Data i godzina:"))
        self.param_card_datetime = QComboBox()
        self.param_card_datetime.setEnabled(False)
        self.param_card_datetime.currentIndexChanged.connect(self._on_param_card_datetime_changed)
        card_filters.addWidget(self.param_card_datetime, 1)
        card_layout.addLayout(card_filters)
    
        self.param_card_info = QLabel("Brak danych")
        self.param_card_info.setStyleSheet("color:#2c3e50;font-weight:600;")
        self.param_card_info.setWordWrap(True)
        card_layout.addWidget(self.param_card_info)
    
        value_columns = (
            list(PARAM_DISPLAY_ORDER)
            + list(INDEX_PARAM_DISPLAY_ORDER)
            + list(GRIP_PARAM_ORDER)
            + list(NEST_PARAM_ORDER)
            + list(HAIRPIN_PARAM_ORDER)
        )
        self.param_card_value_names = value_columns
        param_headers = ["Program", "Tabela", "Pin", "Step"] + value_columns
        self.param_card_table = QTableWidget(0, len(param_headers))
        self.param_card_table.setHorizontalHeaderLabels(param_headers)
        self.param_card_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.param_card_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.param_card_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.param_card_table.verticalHeader().setVisible(False)
        for ci in range(len(param_headers)):
            self.param_card_table.horizontalHeader().setSectionResizeMode(ci, QHeaderView.ResizeToContents)
        card_layout.addWidget(self.param_card_table, 1)
    
        card_btns = QHBoxLayout()
        card_btns.setSpacing(6)
        card_btns.addStretch(1)
        self.param_card_export_btn = QPushButton("Eksport CSV")
        self.param_card_export_btn.setEnabled(False)
        self.param_card_export_btn.clicked.connect(self._export_param_card_csv)
        card_btns.addWidget(self.param_card_export_btn)
        card_layout.addLayout(card_btns)
    
        self.tabs.addTab(self.param_card_tab, "Karta parametrów")
    
    
        self.gripper_tab_widget = GripperTab(self)
        self.tabs.addTab(self.gripper_tab_widget, "Gripper")

        self.nest_tab_widget = NestTab(self)
        self.tabs.addTab(self.nest_tab_widget, "Nest")
    
    
    
        self.stripping_tab_widget = StrippingTab(self)
        self.tabs.addTab(self.stripping_tab_widget, "Odizolowanie")
    
    
    
        self.intra_tab = QWidget()
        intra_layout = QVBoxLayout(self.intra_tab)
        intra_layout.setContentsMargins(12, 12, 12, 12)
        intra_layout.setSpacing(8)
        from PyQt5.QtWidgets import QComboBox as _QComboBox
        intra_filt_top = QHBoxLayout()
        intra_filt_top.setSpacing(8)
        self.intra_f_machine_code = _QComboBox()
        self.intra_f_machine_code.currentIndexChanged.connect(self._apply_intranet_filters)
        self.intra_f_machine_desc = _QComboBox()
        self.intra_f_machine_desc.currentIndexChanged.connect(self._apply_intranet_filters)
        self.intra_f_source_desc = _QComboBox()
        self.intra_f_source_desc.currentIndexChanged.connect(self._apply_intranet_filters)
        self.intra_f_source_map = _QComboBox()
        self.intra_f_source_map.currentIndexChanged.connect(self._apply_intranet_filters)
        intra_filt_top.addWidget(QLabel("Maszyna SAP:"))
        intra_filt_top.addWidget(self.intra_f_machine_code, 1)
        intra_filt_top.addWidget(QLabel("Maszyna:"))
        intra_filt_top.addWidget(self.intra_f_machine_desc, 1)
        intra_filt_top.addWidget(QLabel("Źródło (opis):"))
        intra_filt_top.addWidget(self.intra_f_source_desc, 1)
        intra_filt_top.addWidget(QLabel("Źródło (mapa):"))
        intra_filt_top.addWidget(self.intra_f_source_map, 1)
        intra_layout.addLayout(intra_filt_top)
    
        intra_filt_bottom = QHBoxLayout()
        intra_filt_bottom.setSpacing(8)
        self.intra_f_date = QLineEdit()
        self.intra_f_date.setPlaceholderText("Filtruj datę...")
        try:
            self.intra_f_date.setClearButtonEnabled(True)
        except Exception:
            pass
        self.intra_f_date.textChanged.connect(self._apply_intranet_filters)
        self.intra_f_serial = QLineEdit()
        self.intra_f_serial.setPlaceholderText("Filtruj serial...")
        try:
            self.intra_f_serial.setClearButtonEnabled(True)
        except Exception:
            pass
        self.intra_f_serial.textChanged.connect(self._apply_intranet_filters)
        self.intra_f_judge = _QComboBox()
        self.intra_f_judge.currentIndexChanged.connect(self._apply_intranet_filters)
        intra_filt_bottom.addWidget(QLabel("Data:"))
        intra_filt_bottom.addWidget(self.intra_f_date, 1)
        intra_filt_bottom.addWidget(QLabel("Serial No:"))
        intra_filt_bottom.addWidget(self.intra_f_serial, 1)
        intra_filt_bottom.addWidget(QLabel("Ocena:"))
        intra_filt_bottom.addWidget(self.intra_f_judge, 1)
        intra_layout.addLayout(intra_filt_bottom)
        try:
            self._populate_intranet_filters()
        except Exception:
            pass
        self.intra_table = QTableWidget(0, 7)
        self.intra_table.setHorizontalHeaderLabels(["Maszyna SAP", "Maszyna", "Źródło (opis)", "Źródło (mapa)", "Data", "Serial No", "Ocena"])
        self.intra_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.intra_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.intra_table.setSelectionMode(QAbstractItemView.SingleSelection)
        for ci in range(7):
            self.intra_table.horizontalHeader().setSectionResizeMode(ci, QHeaderView.ResizeToContents)
        intra_layout.addWidget(self.intra_table, 1)
    
        intra_btns = QHBoxLayout()
        intra_btns.setSpacing(6)
        intra_refresh = QPushButton("Odśwież Intranet")
        intra_refresh.clicked.connect(self._start_intranet_fetch)
        intra_export = QPushButton("Eksport CSV")
        intra_export.clicked.connect(self._export_intranet_csv)
        intra_btns.addStretch(1)
        intra_btns.addWidget(intra_refresh)
        intra_btns.addWidget(intra_export)
        intra_layout.addLayout(intra_btns)
    
        self.tabs.addTab(self.intra_tab, "Intranet")
        self.intranet_rows: list[dict] = []
        self.intranet_filtered_rows: list[dict] = []
        self.intranet_all_rows: list[dict] = []
        self.intranet_nok_rows: list[dict] = []
    
    
        self.pareto_tab = QWidget()
        pareto_layout = QVBoxLayout(self.pareto_tab)
        pareto_layout.setContentsMargins(12, 12, 12, 12)
        pareto_layout.setSpacing(8)
    
        pareto_filters = QHBoxLayout()
        pareto_filters.setSpacing(8)
        pareto_filters.addWidget(QLabel("Maszyna NOK:"))
        self.pareto_machine_combo = QComboBox()
        self.pareto_machine_combo.currentIndexChanged.connect(self._update_pareto_chart)
        pareto_filters.addWidget(self.pareto_machine_combo)
        pareto_filters.addWidget(QLabel("Filtr nazwy:"))
        self.pareto_machine_filter = QLineEdit()
        self.pareto_machine_filter.setPlaceholderText("Wpisz nazwę maszyny...")
        try:
            self.pareto_machine_filter.setClearButtonEnabled(True)
        except Exception:
            pass
        self.pareto_machine_filter.textChanged.connect(self._update_pareto_chart)
        pareto_filters.addWidget(self.pareto_machine_filter, 1)
        pareto_filters.addStretch(1)
        self.pareto_summary_label = QLabel("Brak danych")
        self.pareto_summary_label.setStyleSheet("color:#2c3e50;font-weight:600;")
        pareto_filters.addWidget(self.pareto_summary_label)
        pareto_layout.addLayout(pareto_filters)
    
        self.pareto_chart = ParetoChartWidget()
        pareto_layout.addWidget(self.pareto_chart, 1)
    
        self.tabs.addTab(self.pareto_tab, "Pareto NOK")
    
    
    
    
        self.logs_tab = QTextEdit()
        self.logs_tab.setReadOnly(True)
        self.tabs.addTab(self.logs_tab, "Logi")
    
        self.param_snapshots: list[ParamSnapshot] = []
        self.index_snapshots: list[IndexSnapshot] = []
        self.hp_grip_snapshots: list[GripSnapshot] = []
        self.hp_grip_events: list[dict] = []
        self.hairpin_snapshots: list[HairpinSnapshot] = []
        self.hairpin_events: list[dict] = []
        self.param_card_groups: dict[str, dict[datetime, list[ParamSnapshot]]] = {}
        self.current_param_card_rows: list[ParamSnapshot] = []
        self.param_card_selection: tuple[datetime, str] | None = None
        self._param_line_hierarchy: dict[str, dict[str, set[str]]] = {}
        self._index_line_hierarchy: dict[str, dict[str, set[str]]] = {}
        self._analysis_filter_hierarchy: dict[str, dict[str, dict[str, set[str]]]] = {}
        self._index_filter_hierarchy: dict[str, dict[str, dict[str, set[str]]]] = {}
        self._hp_grip_value_keys: list[str] = []
        self._hairpin_value_keys: list[str] = []
        self._hp_grip_filter_hierarchy: dict[str, set[str]] = {}
        self._hairpin_filter_hierarchy: dict[str, set[str]] = {}
        self._hairpin_display_to_source: dict[str, str] = {}
        self.hp_grip_filtered: list[dict] = []
        self.hairpin_filtered: list[dict] = []
        self._populate_param_line_filters()
        self._populate_index_line_filters()
        self._clear_param_line_charts()
        self._clear_index_line_charts()
        self._populate_param_card_filters()
        self._configure_hp_grip_table()
        self._configure_stripping_table()
        self._populate_hp_grip_filters()
        self._populate_stripping_filters()
        self._populate_pareto_filters()
    
        root.addWidget(self.tabs)
    
        root.setStretch(0, 1)
        root.setStretch(1, 5)
        self.setCentralWidget(central)
    
    
        status = QStatusBar()
        self.setStatusBar(status)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(True)
        self.progress.setFormat("Przetwarzanie...")
        status.addPermanentWidget(self.progress, 1)
        self._active_tasks: set[str] = set()
        self.status_label = QLabel("Gotowy")
        status.addPermanentWidget(self.status_label)
        self.thread_state = QLabel("Wątki: bezczynne")
        status.addPermanentWidget(self.thread_state)
    
    
        now = QDateTime.currentDateTime()
        self.end_datetime.setDateTime(now)
        self.start_datetime.setDateTime(QDateTime(now.date().addDays(-1), QTime(6, 0)))
    
    
        self._refresh_base_path_label()
        self._populate_machines()
        self._apply_styles()

__all__ = ["ModernMainWindow"]
