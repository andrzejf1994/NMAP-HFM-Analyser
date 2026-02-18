"""User interface for the "Zmiany" (Changes) tab."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

try:  # Web view is optional.
    from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineView  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    QWebEngineView = None  # type: ignore
    QWebEnginePage = None  # type: ignore

from hfm_analyzer.gui.widgets import BarChartWidget, PieChartWidget

if TYPE_CHECKING:
    from hfm_analyzer.gui.main_window import ModernMainWindow


class ChangesTab(QWidget):
    """Encapsulates the "Zmiany" tab content and summary header."""

    def __init__(
        self,
        window: ModernMainWindow,
        root_layout: QVBoxLayout,
        filters_box: QGroupBox,
    ) -> None:
        super().__init__()
        self._window = window
        self._build_ui(root_layout, filters_box)

    def _build_ui(self, root_layout: QVBoxLayout, filters_box: QGroupBox) -> None:
        window = self._window
        window.summary_page = self

        sp_layout = QVBoxLayout(self)
        sp_layout.setContentsMargins(12, 12, 12, 12)
        sp_layout.setSpacing(12)

        header_box = QGroupBox("Podsumowanie")
        header_layout = QHBoxLayout(header_box)
        header_layout.setSpacing(6)
        header_layout.setContentsMargins(0, 0, 0, 0)

        counts_col = QVBoxLayout()
        window.stat_changes = QLabel("Liczba zmian: 0")
        window.stat_changes.setFont(QFont("Segoe UI", 12, QFont.Bold))
        window.stat_machines = QLabel("Liczba maszyn: 0")
        window.stat_machines.setFont(QFont("Segoe UI", 12, QFont.Bold))
        counts_col.addWidget(window.stat_changes)
        counts_col.addWidget(window.stat_machines)
        counts_col.addStretch(1)

        counts_wrapper = QWidget()
        counts_wrapper.setLayout(counts_col)
        counts_wrapper.setFixedWidth(220)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(8)
        charts_row.setContentsMargins(0, 0, 0, 0)

        mode = os.environ.get("HFM_CHARTS", "").lower()
        window._use_static_charts = (QWebEngineView is None) or (mode != "web")
        if QWebEngineView is not None:

            class LoggingWebPage(QWebEnginePage):
                def __init__(self, logger, parent=None):
                    super().__init__(parent)
                    self._logger = logger

                def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
                    try:
                        self._logger(f"[JS] {message} (line {lineNumber})")
                    except Exception:
                        pass

            window.pie_view = QWebEngineView()
            window.pie_view.setPage(LoggingWebPage(window._log, window.pie_view))
            window.pie_view.setMinimumHeight(260)
            window.line_view = QWebEngineView()
            window.line_view.setPage(LoggingWebPage(window._log, window.line_view))
            window.line_view.setMinimumHeight(260)
            charts_row.addWidget(window.pie_view, 1)
            charts_row.addWidget(window.line_view, 1)
        else:
            window.pie_view = None
            window.line_view = None
            charts_row.addWidget(QLabel("Brak wsparcia QWebEngineView zainstaluj PyQtWebEngine"))

        window.pie_label = QLabel()
        window.pie_label.setMinimumHeight(260)
        window.pie_label.setAlignment(Qt.AlignCenter)
        window.line_label = QLabel()
        window.line_label.setMinimumHeight(260)
        window.line_label.setAlignment(Qt.AlignCenter)
        charts_row.addWidget(window.pie_label, 1)
        charts_row.addWidget(window.line_label, 1)

        if window._use_static_charts:
            try:
                if window.pie_view:
                    window.pie_view.hide()
                if window.line_view:
                    window.line_view.hide()
            except Exception:
                pass
            window.pie_label.show()
            window.line_label.show()
        else:
            window.pie_label.hide()
            window.line_label.hide()

        window.pie_native = PieChartWidget()
        window.bar_native = BarChartWidget()
        charts_row.addWidget(window.pie_native, 1)
        charts_row.addWidget(window.bar_native, 3)

        try:
            from PyQt5.QtWidgets import QSizePolicy as _QSizePolicy

            for widget in (
                getattr(window, "pie_view", None),
                getattr(window, "line_view", None),
                getattr(window, "pie_label", None),
                getattr(window, "line_label", None),
            ):
                if widget is not None:
                    widget.hide()
                    widget.setMaximumSize(0, 0)
                    widget.setSizePolicy(_QSizePolicy.Fixed, _QSizePolicy.Fixed)
        except Exception:
            pass
        header_layout.addLayout(charts_row, 1)

        top_row = QHBoxLayout()
        top_row.addWidget(filters_box, 1)
        top_row.addWidget(header_box, 2)
        root_layout.addLayout(top_row)

        hotspots_box = QGroupBox("Najbardziej problematyczne miejsca")
        hotspots_layout = QVBoxLayout(hotspots_box)
        hotspots_layout.setContentsMargins(8, 8, 8, 8)
        hotspots_toolbar = QHBoxLayout()
        hotspots_export = QPushButton("Eksport CSV")
        hotspots_export.clicked.connect(window._export_top_issues_csv)
        hotspots_toolbar.addWidget(hotspots_export)
        hotspots_toolbar.addStretch(1)
        hotspots_layout.addLayout(hotspots_toolbar)

        window.top_issues_tree = QTreeWidget()
        window.top_issues_tree.setColumnCount(5)
        window.top_issues_tree.setHeaderLabels([
            "Maszyna",
            "Pin",
            "Step",
            "Parametr",
            "Zmian",
        ])
        window.top_issues_tree.setAlternatingRowColors(True)
        window.top_issues_tree.setRootIsDecorated(False)
        window.top_issues_tree.setSelectionMode(QTreeWidget.SingleSelection)
        window.top_issues_tree.setStyleSheet(
            """
            QTreeWidget { border: 1px solid #e0e0e0; border-radius: 8px; }
            QHeaderView::section { background: #f5f6f7; padding:8px; border: none; font-weight: 600; }
            QTreeWidget::item { padding: 6px 8px; }
            QTreeView::item:selected {
                background: rgba(52, 152, 219, 80);
                color: #2c3e50;
            }
            QTreeView::item:selected:active {
                background: rgba(52, 152, 219, 110);
            }
            QTreeView::item:selected:!active {
                background: rgba(52, 152, 219, 60);
            }
            """
        )
        window.top_issues_tree.itemClicked.connect(window._on_top_issue_click)
        try:
            for column in range(window.top_issues_tree.columnCount()):
                window.top_issues_tree.header().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        except Exception:
            pass
        hotspots_layout.addWidget(window.top_issues_tree)

        sections_row = QHBoxLayout()
        sections_row.setSpacing(12)

        left_column = QVBoxLayout()
        left_column.setSpacing(12)
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.addWidget(hotspots_box)

        summary_box = QGroupBox("Analiza ilości zmian - Podsumowanie")
        summary_layout = QVBoxLayout(summary_box)

        summary_toolbar = QHBoxLayout()
        summary_expand = QPushButton("Rozwiń wszystko")
        summary_expand.clicked.connect(lambda: window.change_tree.expandAll())
        summary_collapse = QPushButton("Zwiń wszystko")
        summary_collapse.clicked.connect(lambda: window.change_tree.collapseAll())
        summary_export = QPushButton("Eksport CSV")
        summary_export.clicked.connect(window._export_change_tree_csv)
        summary_toolbar.addWidget(summary_expand)
        summary_toolbar.addWidget(summary_collapse)
        summary_toolbar.addWidget(summary_export)
        summary_toolbar.addStretch(1)
        summary_layout.addLayout(summary_toolbar)

        window.change_tree = QTreeWidget()
        window.change_tree.setHeaderLabels(["Maszyna / Pin / Step / Parametr", "Zmian"])
        window.change_tree.setAlternatingRowColors(True)
        window.change_tree.setRootIsDecorated(True)
        window.change_tree.setStyleSheet(
            """
            QTreeWidget { border: 1px solid #e0e0e0; border-radius: 8px; }
            QHeaderView::section { background: #f5f6f7; padding:8px; border: none; font-weight: 600; }
            QTreeWidget::item { padding: 6px 8px; }
            QTreeView::item:selected {
                background: rgba(52, 152, 219, 80);
                color: #2c3e50;
            }
            QTreeView::item:selected:active {
                background: rgba(52, 152, 219, 110);
            }
            QTreeView::item:selected:!active {
                background: rgba(52, 152, 219, 60);
            }
            """
        )
        window.change_tree.itemClicked.connect(window._on_change_tree_click)
        try:
            window.change_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
            window.change_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        except Exception:
            pass
        summary_layout.addWidget(window.change_tree)
        left_column.addWidget(summary_box, 1)
        sections_row.addLayout(left_column, 1)

        details_box = QGroupBox("Drzewo danych")
        details_layout = QVBoxLayout(details_box)

        tree_toolbar = QHBoxLayout()
        expand_btn = QPushButton("Rozwiń wszystko")
        expand_btn.clicked.connect(lambda: window.tree.expandAll())
        collapse_btn = QPushButton("Zwiń wszystko")
        collapse_btn.clicked.connect(lambda: window.tree.collapseAll())
        export_btn = QPushButton("Eksport CSV")
        export_btn.clicked.connect(window._export_tree_csv)
        tree_toolbar.addWidget(expand_btn)
        tree_toolbar.addWidget(collapse_btn)
        tree_toolbar.addWidget(export_btn)
        tree_toolbar.addStretch(1)
        details_layout.addLayout(tree_toolbar)

        window.tree = QTreeWidget()
        window.tree.setHeaderLabels(["Maszyna / Data", "Zmian", "OK", "NOK", "Szczegóły"])
        window.tree.setAlternatingRowColors(True)
        window.tree.setColumnWidth(0, 260)
        window.tree.setColumnWidth(1, 90)
        window.tree.setColumnWidth(2, 75)
        window.tree.setColumnWidth(3, 75)
        window.tree.setStyleSheet(
            """
            QTreeWidget { border: 1px solid #e0e0e0; border-radius: 8px; }
            QHeaderView::section { background: #f5f6f7; padding:8px; border: none; font-weight: 600; }
            QTreeWidget::item { padding: 6px 8px; }
            QTreeView::item:selected {
                background: rgba(52, 152, 219, 80);
                color: #2c3e50;
            }
            QTreeView::item:selected:active {
                background: rgba(52, 152, 219, 110);
            }
            QTreeView::item:selected:!active {
                background: rgba(52, 152, 219, 60);
            }
            """
        )
        details_layout.addWidget(window.tree)
        sections_row.addWidget(details_box, 1)

        sp_layout.addLayout(sections_row, 1)


__all__ = ["ChangesTab"]
