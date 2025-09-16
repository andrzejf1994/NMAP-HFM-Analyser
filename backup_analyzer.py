import os
import sys
import glob
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

import plotly.graph_objects as go
import pandas as pd
import csv
import re
import xml.etree.ElementTree as ET
try:
    import lxml.etree as LET
except ImportError:
    LET = None
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback
import logging

from PyQt5.QtCore import (
    QDateTime,
    QTime,
    Qt,
    QSettings,
    QThread,
    pyqtSignal,
    QUrl,
    QPointF,
    QRectF,
)
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QPixmap, QImage, QPainter, QBrush
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QListWidget,
    QListWidgetItem,
    QDateTimeEdit,
    QMessageBox,
    QAction,
    QFileDialog,
    QDialog,
    QLineEdit,
    QFormLayout,
    QDialogButtonBox,
    QSpinBox,
    QComboBox,
    QTabWidget,
    QTextEdit,
    QGroupBox,
    QGridLayout,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHeaderView,
    QStatusBar,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QStyle,
    QStyledItemDelegate,
)
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
except ImportError:
    QWebEngineView = None
    QWebEnginePage = None


class PieChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {}
        self._colors = {}
        self.setMinimumHeight(220)

    def set_data(self, data: dict):
        self._data = dict(data) if data else {}
        self.update()

    def set_colors(self, cmap: dict):
        self._colors = dict(cmap or {})
        self.update()

    def paintEvent(self, e):
        from PyQt5.QtGui import QPainter, QPen
        from PyQt5.QtCore import QRectF, QPointF
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)


        rect = self.rect().adjusted(8, 8, -8, -8)

        legend_w = 150
        chart_rect = QRectF(rect.left(), rect.top(), rect.width() - legend_w, rect.height())

        target_d = chart_rect.height() * 0.8
        size = min(target_d, chart_rect.width() * 0.9)
        r = size / 2
        cx = chart_rect.left() + r
        cy = chart_rect.center().y()
        bbox = QRectF(cx - r, cy - r, size, size)

        total = sum(self._data.values()) or 1
        fallback_colors = [
            QColor('#3498db'), QColor('#2ecc71'), QColor('#e74c3c'),
            QColor('#f1c40f'), QColor('#9b59b6'), QColor('#1abc9c'),
            QColor('#34495e'), QColor('#e67e22'), QColor('#7f8c8d'),
        ]

        start_angle = 0.0
        for idx, (label, val) in enumerate(sorted(self._data.items(), key=lambda x: -x[1])):
            angle = 360.0 * (val / total)
            col = self._colors.get(label)
            if col is None:
                col = fallback_colors[idx % len(fallback_colors)]
            p.setBrush(col)
            p.setPen(Qt.NoPen)
            p.drawPie(bbox, int(start_angle * 16), int(angle * 16))
            start_angle += angle




        p.setPen(QColor('#2c3e50'))
        font = p.font(); font.setPointSize(font.pointSize())
        p.setFont(font)
        x, y = chart_rect.right() + 10, rect.top() + 4
        for idx, (label, val) in enumerate(sorted(self._data.items(), key=lambda x: -x[1])):
            col = self._colors.get(label)
            if col is None:
                col = fallback_colors[idx % len(fallback_colors)]
            p.setBrush(col)
            p.setPen(Qt.NoPen)
            p.drawRect(int(x), int(y + idx*18), 12, 12)
            p.setPen(QColor('#2c3e50'))
            p.drawText(int(x + 18), int(y + 12 + idx*18), f"{label}: {val}")


class BarChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._x = []
        self._series = {}
        self._colors = {}
        self.setMinimumHeight(220)
        self._overlay_x = []
        self._overlay_y = []
        self._overlay_min_top = 0  # minimal top range for overlay axis

    def set_data(self, x_labels, series: dict):
        self._x = list(x_labels) if x_labels else []
        self._series = {k: list(v) for k, v in (series or {}).items()}
        self.update()

    def set_colors(self, cmap: dict):
        self._colors = dict(cmap or {})
        self.update()

    def set_overlay(self, x_labels, y_values):
        self._overlay_x = list(x_labels) if x_labels else []
        self._overlay_y = list(y_values) if y_values else []
        self.update()

    def set_overlay_min_ymax(self, v: int):
        try:
            self._overlay_min_top = int(v)
        except Exception:
            self._overlay_min_top = 0
        self.update()

    def paintEvent(self, e):
        from PyQt5.QtGui import QPainter, QPen
        from PyQt5.QtCore import QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        outer = self.rect().adjusted(10, 10, -10, -10)

        legend_w = 160

        rect = QRectF(outer.left()+30, outer.top(), outer.width()-legend_w-30-36, outer.height()-36)
        p.fillRect(self.rect(), QColor('white'))


        p.setPen(QPen(QColor('#95a5a6'), 1))
        p.drawLine(rect.bottomLeft(), rect.bottomRight())
        p.drawLine(rect.bottomLeft(), rect.topLeft())

        if not self._x or not self._series:
            p.setPen(QColor('#7f8c8d'))
            p.drawText(rect, Qt.AlignCenter, 'Brak danych')
            return


        y_max = 1
        for vals in self._series.values():
            if vals:
                y_max = max(y_max, max(vals))
        y_max_overlay = 0
        try:
            if self._overlay_y:
                y_max_overlay = max(0, max(self._overlay_y))
        except Exception:
            y_max_overlay = 0
        # Ensure minimal top for overlay if requested
        try:
            if self._overlay_min_top and y_max_overlay < self._overlay_min_top:
                y_max_overlay = self._overlay_min_top
        except Exception:
            pass


        p.setPen(QPen(QColor('#ecf0f1'), 1))
        for i in range(1, 5):
            y = rect.bottom() - i * rect.height() / 5
            p.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

        try:
            p.setPen(QColor('#7f8c8d'))
            for i in range(0,6):
                y = rect.bottom() - i * rect.height() / 5
                val = int(round(y_max * i / 5))
                p.drawText(int(outer.left()), int(y-8), 28, 16, Qt.AlignRight | Qt.AlignVCenter, str(val))
        except Exception:
            pass

        # Axis titles
        try:
            p.setPen(QColor('#2c3e50'))
            p.drawText(int(outer.left()+4), int(rect.top()-6), 'Zmiany')
            p.drawText(int(rect.right()+24), int(rect.top()-6), 'NOK')
        except Exception:
            pass
        n_dates = len(self._x)
        names = sorted(self._series.keys())
        n_series = max(1, len(names))
        bar_group_width = rect.width() / max(1, n_dates)
        bar_width = max(2.0, bar_group_width * 0.8 / n_series)


        p.setPen(QColor('#2c3e50'))
        approx_label_w = 44
        max_labels = max(1, int(rect.width() // approx_label_w))
        stride = max(1, int((len(self._x) + max_labels - 1) // max_labels))
        for i, lab in enumerate(self._x):
            if i % stride != 0:
                continue
            cx = rect.left() + (i + 0.5) * bar_group_width
            top_txt = str(lab)
            bottom_txt = ''
            try:
                from datetime import datetime as _dt
                s = str(lab).replace('T', ' ')
                fmt = '%Y-%m-%d %H:%M' if len(s) > 10 else '%Y-%m-%d'
                d = _dt.strptime(s, fmt)
                top_txt = d.strftime('%d.%m')
                bottom_txt = d.strftime('%H:%M') if len(s) > 10 else d.strftime('%Y')
            except Exception:
                if len(top_txt) > 8:
                    bottom_txt = top_txt[8:]
                    top_txt = top_txt[:8]
            p.drawText(int(cx-22), int(rect.bottom()+2), 44, 16, Qt.AlignCenter, top_txt)
            p.drawText(int(cx-22), int(rect.bottom()+18), 44, 16, Qt.AlignCenter, bottom_txt)


        for j, name in enumerate(names):
            color = self._colors.get(name, QColor('#3498db'))
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            vals = self._series.get(name, [])
            for i, yv in enumerate(vals):
                cx_left = rect.left() + i * bar_group_width

                x = cx_left + (bar_group_width - n_series * bar_width) / 2 + j * bar_width
                h = 0 if yv <= 0 else (min(yv, y_max) / y_max) * rect.height()
                y = rect.bottom() - h
                p.drawRect(QRectF(x, y, bar_width, h))


        p.setPen(QColor('#2c3e50'))
        x0 = outer.right() - legend_w + 10
        y0 = outer.top() + 4
        for idx, name in enumerate(names):
            color = self._colors.get(name, QColor('#3498db'))
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRect(QRectF(x0, y0 + idx*16 - 8, 14, 14))
            p.setPen(QColor('#2c3e50'))
            p.drawText(int(x0+20), int(y0 + 5 + idx*16), name)

        if y_max_overlay > 0:
            try:
                p.setPen(QPen(QColor('#95a5a6'), 1))
                p.drawLine(rect.topRight(), rect.bottomRight())
                p.setPen(QColor('#7f8c8d'))
                for i in range(0,6):
                    y = rect.bottom() - i * rect.height() / 5
                    val = int(round(y_max_overlay * i / 5))
                    p.drawText(int(rect.right()+2), int(y-8), 48, 16, Qt.AlignLeft | Qt.AlignVCenter, str(val))
            except Exception:
                pass


        if self._overlay_x and self._overlay_y and len(self._overlay_x) == len(self._overlay_y):
            try:

                x_index = {str(lbl): i for i, lbl in enumerate(self._x)}
                pts = []
                for lbl, yv in zip(self._overlay_x, self._overlay_y):
                    s = str(lbl)

                    pos = None
                    if len(s) > 10 and s[10] in (' ', 'T'):
                        day = s[:10]
                        i_day = x_index.get(day)
                        if i_day is not None:

                            try:
                                hh = int(s[11:13])
                                mm = int(s[14:16]) if len(s) >= 16 and s[13] == ':' else 0
                            except Exception:
                                hh = 0; mm = 0
                            frac = max(0.0, min(0.999, (hh + mm/60.0) / 24.0))
                            pos = i_day + frac
                    if pos is None:
                        i_day = x_index.get(s)
                        if i_day is None:
                            continue
                        pos = i_day + 0.5
                    cx = rect.left() + max(0.0, min(pos, len(self._x))) * bar_group_width
                    yy = (0 if y_max_overlay == 0 else (yv / y_max_overlay) * rect.height())
                    y = rect.bottom() - min(rect.height(), max(0.0, yy))
                    pts.append(QPointF(cx, y))
                if len(pts) > 1:
                    from PyQt5.QtGui import QPen
                    p.save()
                    p.setClipRect(rect)
                    p.setPen(QPen(QColor('#e74c3c'), 2))
                    for i in range(1, len(pts)):
                        p.drawLine(pts[i-1], pts[i])
                    p.restore()

                leg_row = len(names)
                from PyQt5.QtGui import QPen as _QPen
                p.setPen(_QPen(QColor('#e74c3c'), 2))
                p.drawLine(x0, y0 + leg_row*16, x0+14, y0 + leg_row*16)
                p.setPen(QColor('#2c3e50'))
                p.drawText(int(x0+20), int(y0 + 5 + leg_row*16), 'NOK')
            except Exception:
                pass


class CountBadgeDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):

        if index.column() != 1:
            return super().paint(painter, option, index)
        text = index.data()

        bg_brush = index.data(Qt.BackgroundRole)
        if isinstance(bg_brush, QBrush):
            color = bg_brush.color()
        elif isinstance(bg_brush, QColor):
            color = bg_brush
        else:
            color = QColor('#e0f0ff')
        rect = option.rect.adjusted(6, 3, -6, -3)


        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        radius = rect.height() / 2.0
        painter.drawRoundedRect(rect, radius, radius)


        border = QColor(color)
        border = border.darker(115)
        border.setAlpha(160)
        from PyQt5.QtGui import QPen as _QPen
        painter.setPen(_QPen(border, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)


        lum = (0.299*color.red() + 0.587*color.green() + 0.114*color.blue())
        txt_col = QColor('#ffffff' if lum < 150 else '#2c3e50')
        painter.setPen(txt_col)
        painter.drawText(rect, Qt.AlignCenter, str(text))
        painter.restore()

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)

        return s
APP_ORG = "Nidec"
APP_NAME = "HFM Analyzer"

DEFAULT_PATH_EVO = r"\\\\nmap-production-backup.nidec.eu\\backup-from-lines\\ZI01-0010-0890\\ZI01-0010-0890-0305-0010"
DEFAULT_PATH_H66_2 = r"\\\\nmap-production-backup.nidec.eu\\backup-from-lines\\ZI01-0010-0920\\ZI01-0010-0920-0370-0010"


def _list_mapped_network_drives() -> list[tuple[str, str]]:
    """Return list of (unc_prefix, drive_letter) for mapped network drives.

    unc_prefix example: \\server\share
    drive_letter example: X:
    """
    mappings: list[tuple[str, str]] = []

    try:
        import wmi
        c = wmi.WMI()
        for d in c.Win32_LogicalDisk(DriveType=4):
            unc = (d.ProviderName or "").rstrip("\\/")
            drv = (d.DeviceID or "").strip()
            if unc and drv:
                mappings.append((unc, drv))
    except Exception:
        pass

    if not mappings:
        try:
            import subprocess, re
            out = subprocess.check_output("net use", shell=True, text=True, encoding="utf-8", errors="ignore")
            for line in out.splitlines():
                m = re.search(r"([A-Z]:)\\s+\\\\[^\s]+", line)
                if m:
                    drv = m.group(1)
                    unc_match = re.search(r"(\\\\[^\s]+)", line)
                    if unc_match:
                        unc = unc_match.group(1).rstrip("\\/")
                        mappings.append((unc, drv))
        except Exception:
            pass

    def _core_unc(s: str) -> str:
        if not s:
            return s
        s = s.replace('/', '\\').strip()

        while s.startswith('\\'):
            s = s[1:]

        parts = s.split('\\')
        if len(parts) >= 2:
            return (parts[0] + '\\' + parts[1]).lower()
        return s.lower()

    norm = []
    for unc, drv in mappings:
        norm.append((_core_unc(unc), drv.upper()))
    norm.sort(key=lambda x: len(x[0]), reverse=True)
    return norm


def _map_unc_to_drive_if_possible(path: str) -> str:
    """If `path` starts with a mapped UNC, replace that prefix with drive letter."""
    if not path:
        return path
    try:
        def _core_unc(s: str) -> tuple[str, str]:
            s2 = s.replace('/', '\\')
            while s2.startswith('\\'):
                s2 = s2[1:]
            parts = s2.split('\\', 2)
            if len(parts) >= 2:
                core = (parts[0] + '\\' + parts[1]).lower()
                rest = parts[2] if len(parts) > 2 else ''
                return core, rest
            return s2.lower(), ''

        core, rest = _core_unc(path)
        for unc_core, drv in _list_mapped_network_drives():
            if core == unc_core:
                remainder = rest.lstrip('\\/')
                return drv + ('\\' + remainder if remainder else '')
    except Exception:
        pass
    return path


@dataclass
class FoundFile:
    machine: str
    dt: datetime
    path: str



PARAM_NAMES = [
    "X",
    "Y",
    "Angle",
    "Rotation",
    "Nose Translation",
    "Nose Locking",
    "Wire Feeding",
]


PARAM_DISPLAY_ORDER = [
    "Angle",
    "Nose Locking",
    "Nose Translation",
    "Rotation",
    "Step Speed",
    "Wire Feeding",
    "X",
    "Y",
]


# Domyślna lista wykluczonych maszyn (SAP) dla danych z intranetu
DEFAULT_INTRANET_EXCLUDES_LIST = [
    "ZI01-0010-0890-0001",
    "ZI01-0010-0890-0002",
    "ZI01-0010-0890-0003",
    "ZI01-0010-0890-0010",
    "ZI01-0010-0890-0020",
    "ZI01-0010-0890-0020-0010",
    "ZI01-0010-0890-0020-0020",
    "ZI01-0010-0890-0030",
    "ZI01-0010-0890-0030-0010",
    "ZI01-0010-0890-0040",
    "ZI01-0010-0890-0040-0010",
    "ZI01-0010-0890-0050",
    "ZI01-0010-0890-0060",
    "ZI01-0010-0890-0305",
    "ZI01-0010-0890-0310",
    "ZI01-0010-0890-0320",
    "ZI01-0010-0890-0320-0010",
    "ZI01-0010-0890-0320-0020",
    "ZI01-0010-0890-0330",
    "ZI01-0010-0890-0340",
    "ZI01-0010-0890-0340-0010",
    "ZI01-0010-0890-0340-0020",
    "ZI01-0010-0890-0350",
    "ZI01-0010-0890-0360",
    "ZI01-0010-0890-0370",
    "ZI01-0010-0890-0380",
    "ZI01-0010-0890-0380-0010",
    "ZI01-0010-0890-0380-0020",
    "ZI01-0010-0890-0390",
    "ZI01-0010-0890-0400",
    "ZI01-0010-0890-0400-0010",
    "ZI01-0010-0890-0400-0020",
    "ZI01-0010-0890-0410",
    "ZI01-0010-0890-0420",
    "ZI01-0010-0890-0430",
    "ZI01-0010-0890-0440",
    "ZI01-0010-0890-0450",
    "ZI01-0010-0890-0460",
    "ZI01-0010-0890-0470",
    "ZI01-0010-0890-0480",
    "ZI01-0010-0890-0480-0010",
    "ZI01-0010-0890-0480-0020",
    "ZI01-0010-0890-0490",
    "ZI01-0010-0890-0490-0010",
    "ZI01-0010-0890-0490-0020",
    "ZI01-0010-0890-0500",
    "ZI01-0010-0890-0510",
    "ZI01-0010-0890-0510-0010",
    "ZI01-0010-0890-0510-0020",
    "ZI01-0010-0890-0520",
    "ZI01-0010-0890-0530",
    "ZI01-0010-0890-0530-0010",
    "ZI01-0010-0890-0540",
    "ZI01-0010-0890-0540-0010",
    "ZI01-0010-0890-0540-0020",
    "ZI01-0010-0890-0550",
    "ZI01-0010-0890-0550-0010",
    "ZI01-0010-0890-0550-0020",
    "ZI01-0010-0890-0560",
    "ZI01-0010-0890-0570",
    "ZI01-0010-0890-0570-0010",
    "ZI01-0010-0890-0570-0020",
    "ZI01-0010-0890-0580",
    "ZI01-0010-0890-0580-0010",
    "ZI01-0010-0890-0580-0020",
    "ZI01-0010-0890-0580-0030",
    "ZI01-0010-0890-0590",
    "ZI01-0010-0890-0600",
    "ZI01-0010-0890-0610",
    "ZI01-0010-0890-0610-0010",
    "ZI01-0010-0890-0620",
    "ZI01-0010-0890-0620-0010",
    "ZI01-0010-0890-0630",
    "ZI01-0010-0890-0630-0010",
    "ZI01-0010-0890-0640",
    "ZI01-0010-0890-0650",
    "ZI01-0010-0890-0660",
    "ZI01-0010-0890-0670",
    "ZI01-0010-0890-0680",
    "ZI01-0010-0920-0001",
    "ZI01-0010-0920-0002",
    "ZI01-0010-0920-0003",
    "ZI01-0010-0920-0010",
    "ZI01-0010-0920-0020",
    "ZI01-0010-0920-0020-0010",
    "ZI01-0010-0920-0020-0020",
    "ZI01-0010-0920-0030",
    "ZI01-0010-0920-0030-0010",
    "ZI01-0010-0920-0040",
    "ZI01-0010-0920-0040-0010",
    "ZI01-0010-0920-0050",
    "ZI01-0010-0920-0050-0010",
    "ZI01-0010-0920-0050-0020",
    "ZI01-0010-0920-0050-0030",
]

DEFAULT_INTRANET_EXCLUDES = ",".join(DEFAULT_INTRANET_EXCLUDES_LIST)

@dataclass
class ParamSnapshot:
    dt: datetime
    machine: str
    program: str
    table: str
    pin: str
    step: int
    values: dict
    path: str


def network_path_available(path: str) -> bool:
    if not path:
        return False
    try:
        return os.path.exists(path)
    except Exception:
        return False


class SettingsDialog(QDialog):
    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ustawienia")
        self.settings = settings

        self.path_edit = QLineEdit(self.settings.value("base_path", "", type=str))

        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(0, 32)
        self.workers_spin.setValue(self.settings.value("analysis_workers", 0, type=int))

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 100)
        self.threshold_spin.setSuffix(" %")
        self.threshold_spin.setValue(self.settings.value("large_change_threshold_pct", 10, type=int))

        self.line_id_spin = QSpinBox()
        self.line_id_spin.setRange(1, 10000)
        self.line_id_spin.setValue(self.settings.value("intranet_line_id", 436, type=int))

        excl_val = self.settings.value("intranet_exclude_machines", DEFAULT_INTRANET_EXCLUDES, type=str)
        if not excl_val:
            excl_val = DEFAULT_INTRANET_EXCLUDES
        self.intra_excl_edit = QLineEdit(excl_val)

        # Ile dni wstecz pobierać dane z intranetu (dla mapowania źródeł)
        self.intra_days_back_spin = QSpinBox()
        self.intra_days_back_spin.setRange(0, 30)
        self.intra_days_back_spin.setValue(self.settings.value("intranet_days_back", 1, type=int))

        browse_btn = QPushButton("Przeglądaj")
        browse_btn.clicked.connect(self._browse)

        preset_evo = QPushButton("Ustaw EVO")
        def _set_evo():
            mapped = _map_unc_to_drive_if_possible(DEFAULT_PATH_EVO)
            self.path_edit.setText(mapped)
            self.line_id_spin.setValue(424)
        preset_evo.clicked.connect(_set_evo)
        preset_h66 = QPushButton("Ustaw H66 2")
        def _set_h66():
            mapped = _map_unc_to_drive_if_possible(DEFAULT_PATH_H66_2)
            self.path_edit.setText(mapped)
            self.line_id_spin.setValue(436)
        preset_h66.clicked.connect(_set_h66)

        form = QFormLayout()
        row = QHBoxLayout()
        row.addWidget(self.path_edit)
        row.addWidget(browse_btn)
        form.addRow("Katalog bazowy:", row)

        form.addRow("Wątki analizy (0=auto):", self.workers_spin)
        form.addRow("Próg dużej zmiany (%):", self.threshold_spin)
        form.addRow("ID linii (intranet):", self.line_id_spin)
        form.addRow("Dni wstecz (Intranet):", self.intra_days_back_spin)
        form.addRow("Wyklucz maszyny (SAP):", self.intra_excl_edit)

        presets = QHBoxLayout()
        presets.addWidget(preset_evo)
        presets.addWidget(preset_h66)
        form.addRow("Presety:", presets)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QLineEdit { padding:6px 10px; border:1px solid #bdc3c7; border-radius:6px; }
            QPushButton { padding:6px 10px; }
            """
        )

    def _browse(self):
        new_path = QFileDialog.getExistingDirectory(self, "Wskaż katalog bazowy z backupami")
        if new_path:
            self.path_edit.setText(new_path)

    def _accept(self):
        self.settings.setValue("base_path", self.path_edit.text().strip())
        try:
            self.settings.setValue("analysis_workers", int(self.workers_spin.value()))
        except Exception:
            pass
        try:
            self.settings.setValue("large_change_threshold_pct", int(self.threshold_spin.value()))
        except Exception:
            pass
        try:
            self.settings.setValue("intranet_line_id", int(self.line_id_spin.value()))
        except Exception:
            pass
        try:
            self.settings.setValue("intranet_exclude_machines", self.intra_excl_edit.text().strip())
        except Exception:
            pass
        try:
            self.settings.setValue("intranet_days_back", int(self.intra_days_back_spin.value()))
        except Exception:
            pass
        self.accept()


class NetworkCheckDialog(QDialog):
    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Brak dostępu do katalogu sieciowego")
        self.settings = settings

        info = QLabel(
            "Nie udało się uzyskać dostępu do wskazanego katalogu sieciowego.\n"
            "Upewnij się, że masz połączenie z siecią/VPN oraz, że dysk/udział jest dostępny."
        )
        info.setWordWrap(True)

        current_path = self.settings.value("base_path", "", type=str)
        self.path_label = QLabel(f"Aktualna ścieżka: <b>{current_path or '(brak)'}" + "</b>")
        self.path_label.setTextFormat(Qt.RichText)

        retry_btn = QPushButton("Ponów sprawdzenie")
        retry_btn.clicked.connect(self._on_retry)
        quit_btn = QPushButton("Zamknij")
        quit_btn.clicked.connect(self.reject)
        choose_btn = QPushButton("Wybierz inną ścieżkę")
        choose_btn.clicked.connect(self._choose_path)

        preset_evo = QPushButton("Ustaw domyślną ścieżkę EVO")
        preset_evo.clicked.connect(lambda: self._set_path(DEFAULT_PATH_EVO))
        preset_h66 = QPushButton("Ustaw domyślną ścieżkę H66 2")
        preset_h66.clicked.connect(lambda: self._set_path(DEFAULT_PATH_H66_2))

        btn_row1 = QHBoxLayout()
        btn_row1.addWidget(retry_btn)
        btn_row1.addWidget(quit_btn)

        btn_row2 = QHBoxLayout()
        btn_row2.addWidget(choose_btn)

        btn_row3 = QHBoxLayout()
        btn_row3.addWidget(preset_evo)
        btn_row3.addWidget(preset_h66)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addWidget(self.path_label)
        layout.addLayout(btn_row2)
        layout.addLayout(btn_row3)
        layout.addStretch(1)
        layout.addLayout(btn_row1)
        self.setLayout(layout)
        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QPushButton { padding: 6px 10px; border-radius: 6px; }
            QPushButton:hover { background:#ecf0f1; }
            """
        )

    def _update_label(self):
        current_path = self.settings.value("base_path", "", type=str)
        self.path_label.setText(f"Aktualna ścieżka: <b>{current_path or '(brak)'}" + "</b>")

    def _choose_path(self):
        new_path = QFileDialog.getExistingDirectory(self, "Wskaż katalog bazowy z backupami")
        if new_path:
            self._set_path(new_path)

    def _set_path(self, path: str):
        self.settings.setValue("base_path", path)
        self._update_label()

    def _on_retry(self):
        base_path = self.settings.value("base_path", "", type=str)
        if network_path_available(base_path):
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Nadal brak dostępu",
                "Ścieżka nadal jest niedostępna. Sprawdź połączenie lub wybierz inną ścieżkę.",
            )


class ScanWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, base_path: str, machines: list, start_dt: datetime, end_dt: datetime):
        super().__init__()
        self.base_path = base_path
        self.machines = machines
        self.start_dt = start_dt.replace(second=0)
        self.end_dt = end_dt.replace(second=0)

    def run(self):
        try:
            found: list[FoundFile] = []
            d = self.start_dt.date()
            total_days = (self.end_dt.date() - d).days + 1
            day_idx = 0
            while d <= self.end_dt.date():
                day_idx += 1
                self.progress.emit(f"Skanuję dzień {day_idx}/{total_days}: {d.isoformat()}")
                yyyy = f"{d.year:04d}"
                mm = f"{d.month:02d}"
                yyyy_mm_dd = d.strftime("%Y-%m-%d")
                for machine in self.machines:
                    day_dir = os.path.join(self.base_path, machine, yyyy, mm, yyyy_mm_dd)
                    pattern = os.path.join(day_dir, f"{machine}_{yyyy_mm_dd}_*.xml")
                    for fp in glob.glob(pattern):
                        try:
                            if not os.path.isfile(fp):
                                continue
                            fname = os.path.basename(fp)
                            parts = fname.split("_")
                            if len(parts) < 3:
                                continue
                            dt_str = parts[1] + "_" + parts[2].replace(".xml", "")
                            file_dt = datetime.strptime(dt_str, "%Y-%m-%d_%H-%M-%S").replace(second=0)
                            if self.start_dt <= file_dt <= self.end_dt:
                                found.append(FoundFile(machine=machine, dt=file_dt, path=fp))
                        except Exception:
                            continue
                d += timedelta(days=1)
            self.finished.emit(found)
        except Exception as e:
            self.error.emit(str(e))


class AnalyzeWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, files: list, max_workers: int | None = None):
        super().__init__()
        self.files: list[FoundFile] = list(files)
        if max_workers is None:
            try:
                cw = os.cpu_count() or 4
            except Exception:
                cw = 4

            max_workers = min(8, max(2, cw))

        try:
            env_workers = os.environ.get('HFM_ANALYSIS_WORKERS')
            if env_workers:
                val = int(env_workers)
                if val > 0:
                    max_workers = min(32, val)
        except Exception:
            pass
        self.max_workers = max_workers
        try:
            logging.getLogger("backup_analyzer").info(
                f"[AnalyzeWorker] init: files={len(self.files)} max_workers={self.max_workers}"
            )
        except Exception:
            pass
    def run(self):
        try:
            results: list[ParamSnapshot] = []
            total = len(self.files)

            if not hasattr(self, "_analyze_file"):
                try:
                    logging.getLogger("backup_analyzer").error("[AnalyzeWorker] _analyze_file missing")
                except Exception:
                    pass
                self.error.emit("internal: _analyze_file missing")
                return

            with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                try:
                    logging.getLogger("backup_analyzer").info("[AnalyzeWorker] submitting tasks")
                except Exception:
                    pass
                futs = {ex.submit(self._analyze_file, ff): ff for ff in self.files}
                done = 0
                for fut in as_completed(futs):
                    done += 1
                    ff = futs[fut]
                    self.progress.emit(f"Analizuję plik {done}/{total}: {os.path.basename(ff.path)}")
                    try:
                        recs = fut.result()
                        if recs:
                            results.extend(recs)
                    except Exception:

                        continue
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

    def _analyze_file(self, ff: FoundFile) -> list:
        recs: list[ParamSnapshot] = []

        if LET is not None:
            parser = LET.XMLParser(huge_tree=True, recover=True)
            root = LET.parse(ff.path, parser=parser).getroot()
            iter_items = root.iter
        else:
            root = ET.parse(ff.path).getroot()
            iter_items = root.iter

        program = ''
        for it in iter_items('Item'):
            if it.get('name') == 'sgFileName':
                program = it.get('value') or ''
                break

        pin_map = {}
        aHair = None
        aKin = None
        for arr in iter_items('Array'):
            nm = arr.get('name')
            if nm == 'aHairPinType' and aHair is None:
                aHair = arr
            elif nm == 'aKinTable' and aKin is None:
                aKin = arr
            if aHair is not None and aKin is not None:
                break

        if aHair is not None:
            for s in aHair.iter('Struct'):
                idx = s.get('idx') or ''
                pin = ''
                for it in s.iter('Item'):
                    if it.get('name') == 'sgDescrizione':
                        pin = it.get('value') or ''
                        break
                pin_map[idx] = pin

        if aKin is None:
            return recs

        for st in aKin.iter('Struct'):
            struct_idx = st.get('idx') or ''
            pin_name = pin_map.get(struct_idx, '')

            steps_arr = None
            for arr in st.iter('Array'):
                if arr.get('name') == 'Step':
                    steps_arr = arr
                    break
            if steps_arr is None:
                continue
            steps = list(steps_arr.iter('Struct'))
            for step_i, step_el in enumerate(steps, start=1):
                rPos = None
                boAx = None
                for arr in step_el.iter('Array'):
                    nm = arr.get('name')
                    if nm == 'rPos':
                        rPos = arr
                    elif nm == 'boAxIncluded':
                        boAx = arr
                    if rPos is not None and boAx is not None:
                        break
                if rPos is None or boAx is None:
                    continue
                pos_items = list(rPos.iter('Item'))
                inc_items = list(boAx.iter('Item'))
                values = [0.0] * 7
                any_non_zero = False
                for i in range(7):
                    include = 0
                    if i < len(inc_items):
                        try:
                            include = int((inc_items[i].get('value') or '0'))
                        except Exception:
                            include = 0
                    if include == 1 and i < len(pos_items):
                        try:
                            v = float(pos_items[i].get('value') or '0')
                        except Exception:
                            v = 0.0
                        values[i] = v
                        if abs(v) > 1e-12:
                            any_non_zero = True
                if not any_non_zero:
                    continue

                # Read step speed (iOverride) if present on this step
                step_speed = None
                try:
                    for it in step_el.iter('Item'):
                        if it.get('name') == 'iOverride':
                            step_speed = float((it.get('value') or '0').strip())
                            break
                except Exception:
                    step_speed = None

                vals = {
                    "X": values[0],
                    "Y": values[1],
                    "Angle": values[2],
                    "Rotation": values[3],
                    "Nose Translation": values[4],
                    "Nose Locking": values[5],
                    "Step Speed": (step_speed if step_speed is not None else 0.0),
                    "Wire Feeding": values[6],
                }
                recs.append(ParamSnapshot(
                    dt=ff.dt,
                    machine=ff.machine,
                    program=program,
                    table=struct_idx,
                    pin=pin_name,
                    step=step_i,
                    values=vals,
                    path=ff.path,
                ))
        return recs


class IntranetWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url: str, start_dt: datetime, end_dt: datetime, line_id: int, excludes: list[str] | None = None):
        super().__init__()
        self.url = url
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.line_id = line_id
        self.excludes = set(excludes or [])

    def run(self):
        try:
            data = self._fetch()
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

    def _fetch(self) -> dict:
        import urllib.parse, urllib.request
        start_date = self.start_dt.strftime('%Y-%m-%d')
        end_date = self.end_dt.strftime('%Y-%m-%d')

        payload = {
            'linia[]': str(self.line_id),
            'data_od': start_date,
            'data_do': end_date,
            'dokument': 'view',
        }
        enc = urllib.parse.urlencode(payload).encode('utf-8')
        req = urllib.request.Request(self.url, data=enc, method='POST')
        self.progress.emit(f"[Intranet] POST {self.url} payload={payload}")

        html = None
        try:
            import requests
            with requests.Session() as s:
                r = s.post(self.url, data=payload, timeout=8)
                if r.status_code == 200:
                    html = r.text
                self.progress.emit(f"[Intranet] HTTP status via requests: {getattr(r, 'status_code', '?')}")
        except Exception:
            pass
        if html is None:
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            self.progress.emit(f"[Intranet] HTTP status via urllib: {getattr(resp, 'status', '200 or unknown')}")
        self.progress.emit(f"[Intranet] HTML length: {len(html) if html else 0}")


        rows = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            table = soup.find('table')
            for tr in table.find_all('tr'):
                tds = [td.get_text(strip=True) for td in tr.find_all(['td','th'])]
                if len(tds) < 5:
                    continue
                rows.append(tds)
        except Exception:

            for line in html.splitlines():
                if '<tr' in line and '</tr>' in line:
                    cells = []
                    for m in re.finditer(r'<t[dh][^>]*>(.*?)</t[dh]>', line, re.I):
                        txt = re.sub('<[^<]+?>', '', m.group(1))
                        cells.append(txt.strip())
                    if len(cells) >= 5:
                        rows.append(cells)


        header = None
        data_rows = []
        for r in rows:
            if header is None:
                lc = [c.lower() for c in r]

                if any('serial_no' in c for c in lc) or any('judge' in c for c in lc) or any('data' in c for c in lc):
                    header = r
                    self.progress.emit(f"[Intranet] Header: {header}")
                    continue
            else:
                data_rows.append(r)
        if data_rows:
            self.progress.emit(f"[Intranet] First row: {data_rows[0]}")
        self.progress.emit(f"[Intranet] Parsed rows: {len(data_rows)}")

        if not header:
            return {'per_day': {}, 'rows': []}

        def idx(name):
            for i, c in enumerate(header):
                if name.lower() in c.lower():
                    return i
            return -1
        i_masz_sap = idx('maszyna_sap')
        i_masz_opis = idx('maszyna_opis')
        i_data = idx('data')
        i_serial = idx('serial_no')
        i_judge = idx('judge')
        self.progress.emit(f"[Intranet] Col idx: data={i_data}, serial_no={i_serial}, judge={i_judge}, masz_sap={i_masz_sap}, opis={i_masz_opis}")

        entries_all = []
        entries_nok = []
        for r in data_rows:
            try:
                dtxt = r[i_data]

                dt = None
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M'):
                    try:
                        dt = datetime.strptime(dtxt, fmt)
                        break
                    except Exception:
                        continue
                if dt is None:
                    continue
                if not (self.start_dt <= dt <= self.end_dt):
                    continue
                serial = r[i_serial].strip()
                masz_sap = r[i_masz_sap].strip() if i_masz_sap >= 0 else ''
                if masz_sap in self.excludes:
                    continue
                masz_opis = r[i_masz_opis].strip() if i_masz_opis >= 0 else ''
                judge = r[i_judge].strip()
                rec = {'data': dt, 'serial_no': serial, 'maszyna_sap': masz_sap, 'maszyna_opis': masz_opis, 'judge': judge}
                entries_all.append(rec)
                if str(judge).strip().upper() == 'NOK':
                    entries_nok.append(rec)
            except Exception:
                continue

        entries_all.sort(key=lambda x: x['data'])
        entries_nok.sort(key=lambda x: x['data'])
        kept = list(entries_nok)
        self.progress.emit(f"[Intranet] Filtered entries (NOK, in-range): {len(kept)} | all_in_range={len(entries_all)}")


        fine_grain = (self.end_dt - self.start_dt).total_seconds() <= 48*3600
        series = defaultdict(int)
        rows_out = []
        for rec in kept:
            dt = rec['data']; ser = rec['serial_no']; sap = rec['maszyna_sap']; opis = rec['maszyna_opis']; judge = rec['judge']
            key = dt.strftime('%Y-%m-%d %H:00') if fine_grain else dt.date().isoformat()
            series[key] += 1
            rows_out.append(rec)
        self.progress.emit(f"[Intranet] Buckets: {len(series)} (fine_grain={fine_grain})")
        return {'series': dict(series), 'rows': rows_out, 'rows_all': entries_all}

    def _analyze_file(self, ff: FoundFile) -> list:
        recs: list[ParamSnapshot] = []

        if LET is not None:
            parser = LET.XMLParser(huge_tree=True, recover=True)
            root = LET.parse(ff.path, parser=parser).getroot()
            iter_items = root.iter
        else:
            root = ET.parse(ff.path).getroot()
            iter_items = root.iter


        program = ''
        for it in iter_items('Item'):
            if it.get('name') == 'sgFileName':
                program = it.get('value') or ''
                break


        pin_map = {}
        aHair = None
        aKin = None
        for arr in iter_items('Array'):
            nm = arr.get('name')
            if nm == 'aHairPinType' and aHair is None:
                aHair = arr
            elif nm == 'aKinTable' and aKin is None:
                aKin = arr
            if aHair is not None and aKin is not None:
                break

        if aHair is not None:
            for s in aHair.iter('Struct'):
                idx = s.get('idx') or ''
                pin = ''
                for it in s.iter('Item'):
                    if it.get('name') == 'sgDescrizione':
                        pin = it.get('value') or ''
                        break
                pin_map[idx] = pin

        if aKin is None:
            return recs

        for st in aKin.iter('Struct'):
            struct_idx = st.get('idx') or ''
            pin_name = pin_map.get(struct_idx, '')

            steps_arr = None
            for arr in st.iter('Array'):
                if arr.get('name') == 'Step':
                    steps_arr = arr
                    break
            if steps_arr is None:
                continue
            steps = list(steps_arr.iter('Struct'))
            for step_i, step_el in enumerate(steps, start=1):
                rPos = None
                boAx = None
                for arr in step_el.iter('Array'):
                    nm = arr.get('name')
                    if nm == 'rPos':
                        rPos = arr
                    elif nm == 'boAxIncluded':
                        boAx = arr
                    if rPos is not None and boAx is not None:
                        break
                if rPos is None or boAx is None:
                    continue
                pos_items = list(rPos.iter('Item'))
                inc_items = list(boAx.iter('Item'))
                values = [0.0] * 7
                any_non_zero = False
                for i in range(7):
                    include = 0
                    if i < len(inc_items):
                        try:
                            include = int((inc_items[i].get('value') or '0'))
                        except Exception:
                            include = 0
                    if include == 1 and i < len(pos_items):
                        try:
                            v = float(pos_items[i].get('value') or '0')
                        except Exception:
                            v = 0.0
                        values[i] = v
                        if abs(v) > 1e-12:
                            any_non_zero = True
                if not any_non_zero:
                    continue

                step_speed = None
                try:
                    for it in step_el.iter('Item'):
                        if it.get('name') == 'iOverride':
                            step_speed = float((it.get('value') or '0').strip())
                            break
                except Exception:
                    step_speed = None

                vals = {
                    "X": values[0],
                    "Y": values[1],
                    "Angle": values[2],
                    "Rotation": values[3],
                    "Nose Translation": values[4],
                    "Nose Locking": values[5],
                    "Step Speed": (step_speed if step_speed is not None else 0.0),
                    "Wire Feeding": values[6],
                }
                recs.append(ParamSnapshot(
                    dt=ff.dt,
                    machine=ff.machine,
                    program=program,
                    table=struct_idx,
                    pin=pin_name,
                    step=step_i,
                    values=vals,
                    path=ff.path,
                ))
        return recs
class ModernMainWindow(QMainWindow):
    def __init__(self, settings: QSettings):
        super().__init__()
        self.settings = settings
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


        self.summary_page = QWidget()
        sp_layout = QVBoxLayout(self.summary_page)
        sp_layout.setContentsMargins(12, 12, 12, 12)
        sp_layout.setSpacing(12)


        header_box = QGroupBox("Podsumowanie")
        header_layout = QHBoxLayout(header_box)
        header_layout.setSpacing(6)
        header_layout.setContentsMargins(0, 0, 0, 0)


        counts_col = QVBoxLayout()
        self.stat_changes = QLabel("Liczba zmian: 0")
        self.stat_changes.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.stat_machines = QLabel("Liczba maszyn: 0")
        self.stat_machines.setFont(QFont("Segoe UI", 12, QFont.Bold))
        counts_col.addWidget(self.stat_changes)
        counts_col.addWidget(self.stat_machines)
        counts_col.addStretch(1)

        counts_wrapper = QWidget()
        counts_wrapper.setLayout(counts_col)
        counts_wrapper.setFixedWidth(220)


        charts_row = QHBoxLayout()
        charts_row.setSpacing(8)
        charts_row.setContentsMargins(0, 0, 0, 0)

        mode = os.environ.get('HFM_CHARTS', '').lower()
        self._use_static_charts = (QWebEngineView is None) or (mode != 'web')
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

            self.pie_view = QWebEngineView()
            self.pie_view.setPage(LoggingWebPage(self._log, self.pie_view))
            self.pie_view.setMinimumHeight(260)
            self.line_view = QWebEngineView()
            self.line_view.setPage(LoggingWebPage(self._log, self.line_view))
            self.line_view.setMinimumHeight(260)
            charts_row.addWidget(self.pie_view, 1)
            charts_row.addWidget(self.line_view, 1)
        else:
            self.pie_view = None
            self.line_view = None
            charts_row.addWidget(QLabel("Brak wsparcia QWebEngineView zainstaluj PyQtWebEngine"))


        self.pie_label = QLabel()
        self.pie_label.setMinimumHeight(260)
        self.pie_label.setAlignment(Qt.AlignCenter)
        self.line_label = QLabel()
        self.line_label.setMinimumHeight(260)
        self.line_label.setAlignment(Qt.AlignCenter)
        charts_row.addWidget(self.pie_label, 1)
        charts_row.addWidget(self.line_label, 1)


        if self._use_static_charts:
            try:
                if self.pie_view: self.pie_view.hide()
                if self.line_view: self.line_view.hide()
            except Exception:
                pass
            self.pie_label.show()
            self.line_label.show()
        else:
            self.pie_label.hide()
            self.line_label.hide()


        self.pie_native = PieChartWidget()
        self.bar_native = BarChartWidget()
        charts_row.addWidget(self.pie_native, 1)
        charts_row.addWidget(self.bar_native, 3)


        try:
            from PyQt5.QtWidgets import QSizePolicy as _QSizePolicy
            for w in (getattr(self, 'pie_view', None), getattr(self, 'line_view', None),
                      getattr(self, 'pie_label', None), getattr(self, 'line_label', None)):
                if w is not None:
                    w.hide()
                    w.setMaximumSize(0, 0)
                    w.setSizePolicy(_QSizePolicy.Fixed, _QSizePolicy.Fixed)
        except Exception:
            pass
        header_layout.addLayout(charts_row, 1)

        top_row = QHBoxLayout()
        top_row.addWidget(filters_box, 1)
        top_row.addWidget(header_box, 2)
        root.addLayout(top_row)


        details_box = QGroupBox("Drzewo danych")
        details_layout = QVBoxLayout(details_box)

        tree_toolbar = QHBoxLayout()
        expand_btn = QPushButton("Rozwiń wszystko")
        expand_btn.clicked.connect(lambda: self.tree.expandAll())
        collapse_btn = QPushButton("Zwiń wszystko")
        collapse_btn.clicked.connect(lambda: self.tree.collapseAll())
        tree_toolbar.addWidget(expand_btn)
        tree_toolbar.addWidget(collapse_btn)
        tree_toolbar.addStretch(1)
        details_layout.addLayout(tree_toolbar)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Maszyna / Data", "Zmian", "Szczegóły"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 320)
        self.tree.setColumnWidth(1, 90)
        self.tree.setStyleSheet(
            """
            QTreeWidget { border: 1px solid #e0e0e0; border-radius: 8px; }
            QHeaderView::section { background: #f5f6f7; padding:8px; border: none; font-weight: 600; }
            QTreeWidget::item { padding: 6px 8px; }
            QTreeView::item:selected { background: transparent; outline: 1px solid #3498db; }
            """
        )
        details_layout.addWidget(self.tree)
        sp_layout.addWidget(details_box, 1)

        self.tabs.addTab(self.summary_page, "Zmiany")


        self.analysis_tab = QWidget()
        an_layout = QVBoxLayout(self.analysis_tab)
        an_layout.setContentsMargins(12, 12, 12, 12)
        an_layout.setSpacing(8)

        from PyQt5.QtWidgets import QComboBox
        filt_row = QHBoxLayout()
        filt_row.setSpacing(8)
        self.f_machine = QComboBox()
        self.f_machine.setEditable(False)
        self.f_machine.currentIndexChanged.connect(self._apply_analysis_filters)
        self.f_pin = QComboBox()
        self.f_pin.currentIndexChanged.connect(self._apply_analysis_filters)
        self.f_step = QComboBox()
        self.f_step.currentIndexChanged.connect(self._apply_analysis_filters)
        self.f_param = QComboBox()
        self.f_param.currentIndexChanged.connect(self._apply_analysis_filters)

        def _label(text):
            w = QLabel(text)
            w.setStyleSheet("color:#2c3e50;font-weight:600;")
            return w

        filt_row.addWidget(_label("Maszyna:"))
        filt_row.addWidget(self.f_machine)
        filt_row.addWidget(_label("Pin:"))
        filt_row.addWidget(self.f_pin)
        filt_row.addWidget(_label("Step:"))
        filt_row.addWidget(self.f_step)
        filt_row.addWidget(_label("Parametr:"))
        filt_row.addWidget(self.f_param)
        filt_row.addStretch(1)

        run_btn = QPushButton("Analizuj zmiany")
        run_btn.clicked.connect(self._start_analysis)
        self.analysis_run_btn = run_btn
        filt_row.addWidget(run_btn)
        stop_btn = QPushButton("Zatrzymaj analizę")
        stop_btn.clicked.connect(self._stop_analysis)
        self.analysis_stop_btn = stop_btn
        filt_row.addWidget(stop_btn)
        export_btn = QPushButton("Eksport CSV")
        export_btn.clicked.connect(self._export_analysis_csv)
        filt_row.addWidget(export_btn)

        an_layout.addLayout(filt_row)


        #from PyQt5.QtWidgets import QSplitter
        #split = QSplitter()
        #split.setOrientation(Qt.Horizontal)
        #self.top_issues_tree = QTreeWidget()
        #self.top_issues_tree.setHeaderLabels(["Podsumowanie", "Ilość"])
        #self.top_issues_tree.setAlternatingRowColors(True)
        #self.top_issues_tree.itemClicked.connect(self._on_top_issue_click)
        #self.change_tree = QTreeWidget()
        #self.change_tree.setHeaderLabels(["Zmiany (drzewo)", "Ilość"])
        #self.change_tree.setAlternatingRowColors(True)
        #self.change_tree.itemClicked.connect(self._on_change_tree_click)
        #split.addWidget(self.top_issues_tree)
        #split.addWidget(self.change_tree)
        #split.setSizes([320, 520])
        #an_layout.addWidget(split, 2)

        self.analysis_table = QTableWidget(0, 15)
        self.analysis_table.setHorizontalHeaderLabels([
            "Data", "Czas", "Maszyna", "Program", "Tabela", "Pin", "Step",
            "Angle", "Nose Locking", "Nose Translation", "Rotation", "Wire Feeding", "X", "Y", "Ă„Ä…ÄąË‡cieĂ„Ä…Ă„Ëťka",
        ])
        try:
            params = PARAM_DISPLAY_ORDER
            fixed_cols = ["Data", "Czas", "Maszyna", "Program", "Tabela", "Pin", "Step"]
            path_col = "Ścieżka"
            total_cols = len(fixed_cols) + len(params) + 1
            self.analysis_table.setColumnCount(total_cols)
            self.analysis_table.setHorizontalHeaderLabels(fixed_cols + params + [path_col])
        except Exception:
            pass
        self.analysis_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.analysis_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.analysis_table.setSelectionMode(QAbstractItemView.SingleSelection)
        for ci in range(self.analysis_table.columnCount()):
            self.analysis_table.horizontalHeader().setSectionResizeMode(ci, QHeaderView.ResizeToContents)

        try:
            params = PARAM_DISPLAY_ORDER
            fixed_cols = 7
            total_cols = fixed_cols + len(params) + 1
            self.analysis_table.setColumnHidden(total_cols - 1, True)
        except Exception:
            self.analysis_table.setColumnHidden(14, True)
        an_layout.addWidget(self.analysis_table, 1)

        self.trends_tab = QWidget()
        tr_layout = QVBoxLayout(self.trends_tab)
        tr_layout.setContentsMargins(12, 12, 12, 12)
        tr_layout.setSpacing(8)
        from PyQt5.QtWidgets import QComboBox
        tr_filt = QHBoxLayout()
        tr_filt.setSpacing(8)
        self.t_f_machine = QComboBox(); self.t_f_machine.currentIndexChanged.connect(self._apply_trend_filters)
        tr_filt.addWidget(QLabel("Maszyna:")); tr_filt.addWidget(self.t_f_machine)
        tr_layout.addLayout(tr_filt)

        self.trend_bar_native = BarChartWidget()
        self.trend_bar_native.setMinimumHeight(260)
        try:
            self.trend_bar_native.set_overlay_min_ymax(10)
        except Exception:
            pass
        tr_layout.addWidget(self.trend_bar_native, 1)

        # Mapping for feeder descriptions -> machine code per line prefix
        # Extend as needed; selected machine prefix ('M' or 'S') chooses which mapping to use
        self._feeder_map_M = {2: 'M1', 4: 'M2', 6: 'M3', 8: 'M4', 10: 'M5', 12: 'M6'}
        self._feeder_map_S = {1: 'S1', 3: 'S2', 5: 'S3', 7: 'S4', 9: 'S5', 11: 'S6'}
        self.tabs.addTab(self.trends_tab, "Wykres zmian")

        self.tabs.addTab(self.analysis_tab, "Zmiany Parametrów")


        self.programs_tab = QWidget()
        pg_layout = QVBoxLayout(self.programs_tab)
        pg_layout.setContentsMargins(12, 12, 12, 12)
        pg_layout.setSpacing(8)


        from PyQt5.QtWidgets import QComboBox
        pg_filt = QHBoxLayout()
        pg_filt.setSpacing(8)
        self.pg_f_machine = QComboBox()
        self.pg_f_machine.currentIndexChanged.connect(self._apply_program_filters)
        self.pg_f_old = QComboBox()
        self.pg_f_old.currentIndexChanged.connect(self._apply_program_filters)
        self.pg_f_new = QComboBox()
        self.pg_f_new.currentIndexChanged.connect(self._apply_program_filters)

        def _pl(text):
            w = QLabel(text)
            w.setStyleSheet("color:#2c3e50;font-weight:600;")
            return w

        pg_filt.addWidget(_pl("Maszyna:"))
        pg_filt.addWidget(self.pg_f_machine)
        pg_filt.addWidget(_pl("Stary program:"))
        pg_filt.addWidget(self.pg_f_old)
        pg_filt.addWidget(_pl("Nowy program:"))
        pg_filt.addWidget(self.pg_f_new)
        pg_filt.addStretch(1)
        pg_layout.addLayout(pg_filt)

        self.program_table = QTableWidget(0, 4)
        self.program_table.setHorizontalHeaderLabels(["Data", "Czas", "Maszyna", "Program (stary -> nowy)"])
        self.program_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.program_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.program_table.setSelectionMode(QAbstractItemView.SingleSelection)
        for ci in range(4):
            self.program_table.horizontalHeader().setSectionResizeMode(ci, QHeaderView.ResizeToContents)
        pg_layout.addWidget(self.program_table, 1)
        pg_export_btn = QPushButton("Eksport CSV")
        pg_export_btn.clicked.connect(self._export_programs_csv)
        pg_layout.addWidget(pg_export_btn)

        self.tabs.addTab(self.programs_tab, "Zmiany Programów")


        self.intra_tab = QWidget()
        intra_layout = QVBoxLayout(self.intra_tab)
        intra_layout.setContentsMargins(12, 12, 12, 12)
        intra_layout.setSpacing(8)
        from PyQt5.QtWidgets import QComboBox as _QComboBox
        intra_filt = QHBoxLayout()
        intra_filt.setSpacing(8)
        self.intra_f_machine = _QComboBox()
        self.intra_f_machine.currentIndexChanged.connect(self._apply_intranet_filters)
        intra_filt.addWidget(QLabel("Źródło (mapa):"))
        intra_filt.addWidget(self.intra_f_machine, 1)
        intra_layout.addLayout(intra_filt)
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
        intra_export = QPushButton("Eksport CSV")
        intra_export.clicked.connect(self._export_intranet_csv)
        intra_btns.addStretch(1)
        intra_btns.addWidget(intra_export)
        intra_layout.addLayout(intra_btns)

        self.tabs.addTab(self.intra_tab, "NOK (Intranet)")




        self.logs_tab = QTextEdit()
        self.logs_tab.setReadOnly(True)
        self.tabs.addTab(self.logs_tab, "Logi")

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


    def closeEvent(self, e):
        # Gracefully stop any running workers to avoid QThread warnings on exit
        for name in ('worker', 'a_worker', 'intra_worker'):
            try:
                w = getattr(self, name, None)
                if w is not None and hasattr(w, 'isRunning') and w.isRunning():
                    try:
                        if hasattr(w, 'requestInterruption'):
                            w.requestInterruption()
                    except Exception:
                        pass
                    try:
                        w.quit()
                    except Exception:
                        pass
                    try:
                        w.wait(3000)
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            super().closeEvent(e)
        except Exception:
            pass

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f6f7fb;
            }
            QToolBar {
                spacing: 10px;
                padding: 6px;
                background: #ffffff;
                border-bottom: 1px solid #e6e6e6;
            }
            QGroupBox {
                border: 1px solid #e6e6e6;
                border-radius: 12px;
                background: #ffffff;
                margin-top: 1ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #2f3640;
                background: #ffffff;
            }
            QPushButton {
                padding: 8px 14px;
                border-radius: 6px;
                border: none;
                font-weight: 600;
                background: #3498db;
                color: white;
            }
            QPushButton:hover { background: #2d89c5; }
            QPushButton:disabled { background: #9fb9cf; }
            QLineEdit, QDateTimeEdit {
                padding: 8px 10px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background: #ffffff;
            }
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: white;
            }
            QListWidget::item { padding: 4px 6px; }
            QListWidget::item:selected { background: #3498db; color: white; }
            QTabBar::tab { padding: 10px 14px; }
            QTableWidget { background: #ffffff; }
            QStatusBar { background: #ffffff; border-top: 1px solid #e6e6e6; }
            QProgressBar { border: none; background: #ecf0f1; border-radius: 8px; min-height: 22px; text-align: center; }
            QProgressBar::chunk { background: #3498db; border-radius: 8px; }
            QToolButton[class="filters"] {
                border: 1px solid #d0d5db;
                border-radius: 6px;
                background: #ffffff;
                padding: 4px 8px;
                font-size: 16px;
            }
            QToolButton[class="filters"]:hover {
                border-color: #3498db;
                background: #f5f9ff;
            }
            """
        )


    def _set_plot_png(self, label: QLabel, fig, width=520, height=320, scale=2):
        if label is None or fig is None:
            return
        try:
            png_bytes = fig.to_image(format='png', width=width, height=height, scale=scale)
        except Exception:
            self._log("[Charts] PNG export failed (is 'kaleido' installed?)\n" + traceback.format_exc())
            label.setText("BĂ„Ä…Ă˘â‚¬ĹˇÄ‚â€žĂ˘â‚¬Â¦d renderowania PNG (kaleido)")
            return
        try:
            qimg = QImage.fromData(png_bytes)
            if qimg.isNull():
                raise RuntimeError("QImage is null")
            pix = QPixmap.fromImage(qimg)
            label.setPixmap(pix)
            self._log(f"[Charts] PNG set in label: {len(png_bytes)} bytes")
        except Exception:
            self._log("[Charts] Failed to set PNG in label\n" + traceback.format_exc())
            label.setText("BĂ„Ä…Ă˘â‚¬ĹˇÄ‚â€žĂ˘â‚¬Â¦d wyĂ„Ä…Ă˘â‚¬Ĺźwietlania PNG")
    def _log(self, msg: str):
        try:
            if hasattr(self, 'logs_tab') and self.logs_tab is not None:
                self.logs_tab.append(msg)
        except Exception:
            pass
        try:
            logging.getLogger("backup_analyzer").info(msg)
        except Exception:
            pass
    def _set_plot_html(self, view, fig):
        if view is None or fig is None:
            return
        try:
            frag = fig.to_html(include_plotlyjs='inline', full_html=False)
            html = (
                "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                "<style>html,body{margin:0;padding:0;background:#fff;}</style>"
                "</head><body>" + frag + "</body></html>"
            )
            self._log(f"[Charts] HTML size: {len(html)} bytes")
            view.setHtml(html, QUrl("about:blank"))
            self._log("[Charts] HTML set in view")
        except Exception:
            err = traceback.format_exc()
            self._log("[Charts] Error while rendering plot:\n" + err)
            view.setHtml("<html><body>Błąd renderowania wykresu</body></html>")
    def _refresh_base_path_label(self):
        base_path = self.settings.value("base_path", "", type=str)
        disp = "(nie ustawiono)"
        if base_path:
            parts = base_path.rstrip('\\').split('\\')
            disp = parts[-1] if parts else base_path

        self.base_path_label.setText(f"Linia: <b>{disp}</b>")

    def _get_base_path(self) -> str:
        return self.settings.value("base_path", "", type=str)

    def _select_all(self):
        for i in range(self.machine_list.count()):
            self.machine_list.item(i).setSelected(True)

    def _deselect_all(self):
        for i in range(self.machine_list.count()):
            self.machine_list.item(i).setSelected(False)

    def _populate_machines(self):
        base_path = self._get_base_path()
        self.machine_list.clear()
        self._all_machines.clear()
        if not base_path or not network_path_available(base_path):
            self.machine_list.addItem("(brak dostępnych katalogów)")
            self.scan_btn.setEnabled(False)
            return
        try:
            entries = [n for n in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, n))]
        except Exception:
            entries = []
        if not entries:
            self.machine_list.addItem("(brak podfolderów)")
            self.scan_btn.setEnabled(False)
        else:
            entries.sort()
            for name in entries:
                self.machine_list.addItem(QListWidgetItem(name))
            self.scan_btn.setEnabled(True)
            try:
                # Domyślnie zaznacz wszystkie maszyny po odświeżeniu listy
                self._select_all()
            except Exception:
                pass

    def _browse_base_path(self):
        new_path = QFileDialog.getExistingDirectory(self, "Wskaż katalog bazowy z backupami")
        if new_path:
            self.settings.setValue("base_path", new_path)
            self._refresh_base_path_label()
            self._populate_machines()

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec_() == QDialog.Accepted:
            self._refresh_base_path_label()
            self._populate_machines()


    def _start_scan(self):
        base_path = self._get_base_path()
        if not network_path_available(base_path):
            QMessageBox.critical(self, "Błąd", "Katalog bazowy jest niedostępny.")
            return
        selected = [it.text() for it in self.machine_list.selectedItems() if not it.text().startswith("(")]
        if not selected:
            QMessageBox.warning(self, "Wybór maszyn", "Zaznacz co najmniej jedną maszynę.")
            return
        start_dt = self.start_datetime.dateTime().toPyDateTime()
        end_dt = self.end_datetime.dateTime().toPyDateTime()
        if start_dt > end_dt:
            QMessageBox.warning(self, "Zakres dat", "Data początkowa jest późniejsza niż data końcowa.")
            return


        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.status_label.setText("Trwa skanowanie...")
        self.scan_btn.setEnabled(False)

        try:
            if hasattr(self, 'stat_changes') and self.stat_changes is not None:
                self.stat_changes.setText("Liczba zmian: 0")
            if hasattr(self, 'stat_machines') and self.stat_machines is not None:
                self.stat_machines.setText("Liczba maszyn: 0")
        except Exception:
            pass
        if self.pie_view:
            self.pie_view.setHtml("<html><head><meta charset='utf-8'></head><body style='font-family:Segoe UI;color:#7f8c8d;margin:12px;'>Brak danych</body></html>")
        if self.line_view:
            self.line_view.setHtml("<html><head><meta charset='utf-8'></head><body style='font-family:Segoe UI;color:#7f8c8d;margin:12px;'>Brak danych</body></html>")
        if hasattr(self, 'pie_label') and self.pie_label is not None:
            self.pie_label.setText("Brak danych")
            self.pie_label.setPixmap(QPixmap())
        if hasattr(self, 'line_label') and self.line_label is not None:
            self.line_label.setText("Brak danych")
            self.line_label.setPixmap(QPixmap())
        if hasattr(self, 'pie_native') and self.pie_native is not None:
            self.pie_native.set_data({})
        if hasattr(self, 'line_native') and self.line_native is not None:
            self.line_native.set_data([], {})
        if hasattr(self, 'tree') and self.tree is not None:
            self.tree.clear()
        self.logs_tab.clear()
        try:
            if hasattr(self, 'table') and self.table is not None:
                self.table.setRowCount(0)
        except Exception:
            pass
        try:
            self._log(f"[Scan] Start: {start_dt} -> {end_dt}; Wybrane maszyny: {len(selected)}")
        except Exception:
            pass
        self.worker = ScanWorker(base_path, selected, start_dt, end_dt)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, msg: str):

        try:
            self.progress.setFormat(msg)
        except Exception:
            pass
        try:
            if msg.startswith("Analiza ") or msg.startswith("Analizuj"):
                m = re.search(r"(\d+)/(\d+)", msg)
                if m:
                    done = int(m.group(1))
                    total = int(m.group(2))
                    start = getattr(self, 'analysis_started_at', None)
                    if start and done > 0 and total > 0:
                        elapsed = datetime.now() - start
                        rate_per_file = max(0.001, elapsed.total_seconds() / done)
                        remain = max(0, total - done)
                        eta_secs = int(rate_per_file * remain)
                        eta_txt = str(timedelta(seconds=eta_secs)).split('.', 1)[0]
                        self.status_label.setText(f"Analiza {done}/{total} | ETA {eta_txt}")
        except Exception:
            pass
        try:
            self.logs_tab.append(msg)
        except Exception:
            pass
    def _on_error(self, err: str):
        self.progress.setVisible(False)
        self.status_label.setText("Błąd")
        self.scan_btn.setEnabled(True)
        QMessageBox.critical(self, "Błąd", err)
        self.logs_tab.append(f"Błąd: {err}")

    def _on_finished(self, found: list):
        self.progress.setVisible(False)
        self.status_label.setText("Zakończono")
        self.scan_btn.setEnabled(True)

        self.found_files = list(found)
        self._render_summary()
        try:
            self._log(f"[Trends] Populate after scan: files={len(self.found_files)}")
            self._populate_trend_filters()
            self._apply_trend_filters()
        except Exception:
            pass
        try:
            self.analysis_run_btn.setEnabled(bool(self.found_files))
        except Exception:
            pass
        try:
            machines = sorted({f.machine for f in self.found_files})
            self._log(f"[Scan] Zakończono. Zmian: {len(self.found_files)}, Maszyn: {len(machines)}")
        except Exception:
            pass
        try:
            self._start_intranet_fetch()
        except Exception:
            pass
    def _render_summary(self):

        total_changes = len(self.found_files)

        try:
            if hasattr(self, 'stat_changes') and self.stat_changes is not None:
                self.stat_changes.setText(f"Liczba zmian: {total_changes}")
        except Exception:
            pass
        if not self.found_files:
            try:
                if hasattr(self, 'stat_machines') and self.stat_machines is not None:
                    self.stat_machines.setText("Liczba maszyn: 0")
            except Exception:
                pass
            if self.pie_view:
                self.pie_view.setHtml("<html><body style='font-family:Segoe UI;color:#7f8c8d;margin:12px;'>Brak danych</body></html>")
            if self.line_view:
                self.line_view.setHtml("<html><body style='font-family:Segoe UI;color:#7f8c8d;margin:12px;'>Brak danych</body></html>")
            if hasattr(self, 'detail_html') and self.detail_html is not None:
                self.detail_html.setHtml("<div style='margin:12px;color:#7f8c8d;'>Brak danych do wyświetlenia</div>")
            return


        per_machine_counts = defaultdict(int)
        per_machine_day_counts = defaultdict(lambda: defaultdict(int))
        machines = set()
        for f in self.found_files:
            machines.add(f.machine)
            per_machine_counts[f.machine] += 1
            day = f.dt.date()
            per_machine_day_counts[f.machine][day] += 1

        try:
            if hasattr(self, 'stat_machines') and self.stat_machines is not None:
                self.stat_machines.setText(f"Liczba maszyn: {len(machines)}")
        except Exception:
            pass
        try:
            self._log(f"[Summary] Maszyny: {len(machines)}; Zmian: {total_changes}")
            top = sorted(per_machine_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            self._log("[Summary] Top maszyny: " + ", ".join(f"{m}:{c}" for m,c in top))
        except Exception:
            pass
        palette = ['#3498db', '#2ecc71', '#e74c3c', '#f1c40f', '#9b59b6', '#1abc9c', '#34495e', '#e67e22', '#7f8c8d']
        sorted_names = sorted(machines)
        color_map = {name: QColor(palette[i % len(palette)]) for i, name in enumerate(sorted_names)}


        try:
            self.pie_native.set_colors(color_map)
            self.pie_native.set_data(per_machine_counts)
            self._log(f"[Charts] Pie(native): etykiet={len(per_machine_counts)}")
        except Exception:
            self._log("[Charts] Pie(native) exception:\n" + traceback.format_exc())


        try:

            try:
                start_dt = self.start_datetime.dateTime().toPyDateTime()
                end_dt = self.end_datetime.dateTime().toPyDateTime()
                rng_secs = abs((end_dt - start_dt).total_seconds())
            except Exception:
                start_dt = None
                end_dt = None
                rng_secs = 0

            if (rng_secs <= 0 or start_dt is None or end_dt is None) and self.found_files:
                dts = [f.dt for f in self.found_files]
                start_dt = min(dts)
                end_dt = max(dts)
                rng_secs = (end_dt - start_dt).total_seconds()

            total_hours = max(1, int((rng_secs + 3599) // 3600)) if rng_secs else 1
            bin_hours = 1
            if total_hours > 240:
                bin_hours = 2
            if total_hours > 480:
                bin_hours = 3

            def norm_key(dt):
                base = dt.replace(minute=0, second=0, microsecond=0)
                h = (base.hour // bin_hours) * bin_hours
                base = base.replace(hour=h)
                return base.strftime('%Y-%m-%d %H:00')

            # Build contiguous time buckets (no gaps)
            from datetime import timedelta as _td
            start_norm = start_dt.replace(minute=0, second=0, microsecond=0)
            start_norm = start_norm.replace(hour=(start_norm.hour // bin_hours) * bin_hours)
            end_floor = end_dt.replace(minute=0, second=0, microsecond=0)
            end_floor = end_floor.replace(hour=(end_floor.hour // bin_hours) * bin_hours)
            end_norm = end_floor if end_floor >= end_dt else end_floor + _td(hours=bin_hours)
            bucket_keys = []
            cur = start_norm
            while cur <= end_norm:
                bucket_keys.append(cur.strftime('%Y-%m-%d %H:00'))
                cur += _td(hours=bin_hours)
            per_machine = defaultdict(lambda: defaultdict(int))
            for f in self.found_files:
                key = norm_key(f.dt)
                per_machine[f.machine][key] += 1
            x_keys = bucket_keys
            series = {}
            for machine in sorted(per_machine.keys()):
                series[machine] = [per_machine[machine].get(k, 0) for k in x_keys]
            self.bar_native.set_colors(color_map)
            self.bar_native.set_data(x_keys, series)
            # Attempt to overlay NOK aligned to x_keys if intranet_rows present
            try:
                nok_rows = getattr(self, 'intranet_rows', [])
                if nok_rows:
                    def _norm_label(dt):
                        base = dt.replace(minute=0, second=0, microsecond=0)
                        h = (base.hour // bin_hours) * bin_hours
                        base = base.replace(hour=h)
                        return base.strftime('%Y-%m-%d %H:00')
                    counts = {k: 0 for k in x_keys}
                    seen_sn = set()
                    for r in nok_rows:
                        dt = r.get('data')
                        sn = str(r.get('serial_no',''))
                        if not dt or not sn or sn in seen_sn:
                            continue
                        seen_sn.add(sn)
                        lab = _norm_label(dt)
                        if lab in counts:
                            counts[lab] += 1
                    self.bar_native.set_overlay(x_keys, [counts.get(k, 0) for k in x_keys])
            except Exception:
                pass
            self._log(f"[Charts] Bar(native): bin_hours={bin_hours}, x={len(x_keys)}, series={len(series)}")
        except Exception:
            self._log("[Charts] Bar(native) exception:\n" + traceback.format_exc())


        grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for f in self.found_files:
            hour = f.dt.replace(minute=0, second=0, microsecond=0)
            grouped[f.machine][f.dt.date()][hour].append(f.dt)

        if hasattr(self, 'tree') and self.tree is not None:

            def color_for(val, vmin, vmax):
                if vmax == vmin:

                    return QColor('#e0f7e9')
                t = (val - vmin) / float(vmax - vmin)

                g = (0x2e, 0xcc, 0x71)
                r = (0xe7, 0x4c, 0x3c)
                rr = int(g[0] + (r[0]-g[0])*t)
                gg = int(g[1] + (r[1]-g[1])*t)
                bb = int(g[2] + (r[2]-g[2])*t)
                return QColor(rr, gg, bb)

            self.tree.clear()

            machine_totals = {
                m: sum(len(ch) for hours in grouped[m].values() for ch in hours.values())
                for m in grouped.keys()
            }
            if machine_totals:
                mmin = min(machine_totals.values())
                mmax = max(machine_totals.values())
            else:
                mmin = mmax = 0


            try:
                self.tree.setItemDelegateForColumn(1, CountBadgeDelegate(self.tree))
            except Exception:
                pass


            def translucent(c: QColor, alpha: int = 70) -> QColor:
                cc = QColor(c)
                cc.setAlpha(alpha)
                return cc

            for machine in sorted(grouped.keys()):
                total_machine = machine_totals[machine]
                m_item = QTreeWidgetItem([f"{machine}", str(total_machine), ""])
                self.tree.addTopLevelItem(m_item)
                m_item.setExpanded(True)
                m_item.setTextAlignment(1, Qt.AlignCenter)
                m_col = color_for(total_machine, mmin, mmax)

                m_item.setBackground(0, translucent(m_col, 70))
                m_item.setBackground(1, m_col)

                mc = color_map.get(machine, QColor('#3498db'))
                ico = self._make_color_icon(mc)
                m_item.setIcon(0, ico)

                try:
                    f = m_item.font(0)
                    f.setBold(True)
                    m_item.setFont(0, f)
                except Exception:
                    pass


                day_totals = {day: sum(len(ch) for ch in hours.values()) for day, hours in grouped[machine].items()}
                if day_totals:
                    dmin = min(day_totals.values())
                    dmax = max(day_totals.values())
                else:
                    dmin = dmax = 0
                for day, hours_dict in sorted(grouped[machine].items()):
                    total_day = day_totals[day]
                    d_item = QTreeWidgetItem([f"{day.strftime('%Y-%m-%d')}", str(total_day), ""])
                    m_item.addChild(d_item)
                    d_item.setTextAlignment(1, Qt.AlignCenter)
                    d_col = color_for(total_day, dmin, dmax)
                    d_item.setBackground(0, translucent(d_col, 60))
                    d_item.setBackground(1, d_col)


                    hour_totals = {hour: len(changes) for hour, changes in hours_dict.items()}
                    if hour_totals:
                        hmin = min(hour_totals.values())
                        hmax = max(hour_totals.values())
                    else:
                        hmin = hmax = 0
                    for hour, changes in sorted(hours_dict.items()):
                        hour_str = hour.strftime('%H:00')
                        minutes = sorted({dt.strftime('%H:%M') for dt in changes})
                        cnt = len(changes)
                        h_item = QTreeWidgetItem([f"{hour_str}", str(cnt), ", ".join(minutes)])
                        d_item.addChild(h_item)
                        h_item.setTextAlignment(1, Qt.AlignCenter)
                        h_col = color_for(cnt, hmin, hmax)
                        h_item.setBackground(0, translucent(h_col, 50))
                        h_item.setBackground(1, h_col)

            try:
                self.tree.collapseAll()
            except Exception:
                pass

    def _start_intranet_fetch(self):

        try:
            start_dt = self.start_datetime.dateTime().toPyDateTime()
            end_dt = self.end_datetime.dateTime().toPyDateTime()
            line_id = self.settings.value("intranet_line_id", 436, type=int)
            url = "http://intranet/raporty/Generuj/raport/dane_procesowe_trace"

            url = "http://intranet/raporty/Generuj/raport/raport_sn"
            try:
                days_back = int(self.settings.value("intranet_days_back", 1, type=int))
            except Exception:
                days_back = 1
            if days_back < 0:
                days_back = 0
            fetch_start = start_dt - timedelta(days=days_back)
            self._log(f"[Intranet] Fetch start: {fetch_start} -> {end_dt} (requested {start_dt}->{end_dt}, days_back={days_back}), line={line_id}")

            try:
                self.progress.setRange(0,0)
                self.progress.setVisible(True)
                self.status_label.setText("Pobieranie danych z intranetu...")
            except Exception:
                pass
            excl_str = self.settings.value("intranet_exclude_machines", DEFAULT_INTRANET_EXCLUDES, type=str)
            if not excl_str:
                excl_str = DEFAULT_INTRANET_EXCLUDES
            excludes = [s.strip() for s in excl_str.split(',') if s.strip()]
            self.intra_worker = IntranetWorker(url, fetch_start, end_dt, int(line_id), excludes=excludes)
            self.intra_worker.progress.connect(self._on_progress)
            self.intra_worker.finished.connect(self._on_intranet_ready)
            self.intra_worker.error.connect(self._on_intranet_error)
            self.intra_worker.start()
        except Exception as ex:
            self._log(f"[Intranet] Skipping overlay: {ex}")

    def _on_intranet_ready(self, data: dict):
        try:
            series = data.get('series', {}) if isinstance(data, dict) else {}
            rows = data.get('rows', []) if isinstance(data, dict) else []


            keys = sorted(series.keys())
            self.bar_native.set_overlay(keys, [int(series[k]) for k in keys])
            # Keep rows for trend overlays per machine
            self.intranet_rows = rows
            self._log(f"[Intranet] Overlay points: {sum(series.values())} events on {len(keys)} buckets")

            # Build source machine (feeder) per serial and store rows
            def _codes_from_opis(opis: str) -> list:
                import re as _re
                s = str(opis or '')
                toks = s.strip().split()
                if toks:
                    cand = toks[-1].upper()
                    if len(cand) >= 2 and cand[0] in ('M','S') and cand[1:].isdigit():
                        return [cand]
                mobj = _re.search(r"podajnik\s*drutu\s*(\d+)", s, _re.I)
                out = []
                if mobj:
                    try:
                        num = int(mobj.group(1))
                        if num in self._feeder_map_M:
                            out.append(self._feeder_map_M[num])
                        if num in self._feeder_map_S:
                            out.append(self._feeder_map_S[num])
                    except Exception:
                        pass
                return out

            all_rows = data.get('rows_all', []) if isinstance(data, dict) else []
            try:
                self._log(f"[Intranet] rows_all={len(all_rows)} NOK={len(rows)}")
            except Exception:
                pass
            by_sn = {}
            for r in all_rows:
                by_sn.setdefault(r.get('serial_no',''), []).append(r)

            def _find_source(sn_rows: list):
                feed_rows = [rr for rr in sn_rows if 'podajnik drutu' in str(rr.get('maszyna_opis','')).lower()]
                if feed_rows:
                    feed_rows.sort(key=lambda z: z.get('data'))
                    fr = feed_rows[0]
                    codes = _codes_from_opis(fr.get('maszyna_opis',''))
                    return fr.get('maszyna_opis',''), (codes[0] if codes else '')
                # fallback: any explicit M/S token across rows
                for rr in sn_rows:
                    codes = _codes_from_opis(rr.get('maszyna_opis',''))
                    if codes:
                        return rr.get('maszyna_opis',''), codes[0]
                return '', ''

            enriched = []
            for r in rows:
                rr = dict(r)
                src_opis, src_code = _find_source(by_sn.get(r.get('serial_no',''), []))
                rr['source_opis'] = src_opis
                rr['source_mapped'] = src_code
                enriched.append(rr)
            # Deduplicate by serial_no, keep oldest (by 'data')
            enriched.sort(key=lambda r: r.get('data'))
            seen = set()
            dedup = []
            for rr in enriched:
                sn = rr.get('serial_no','')
                if sn in seen:
                    continue
                seen.add(sn)
                dedup.append(rr)
            try:
                mapped_cnt = sum(1 for rr in dedup if rr.get('source_mapped'))
                feeder_cnt = sum(1 for r0 in (all_rows or []) if 'podajnik drutu' in str(r0.get('maszyna_opis','')).lower())
                missing = [rr.get('serial_no','') for rr in dedup if not rr.get('source_mapped')][:5]
                self._log(f"[Intranet] Mapped sources: {mapped_cnt}/{len(dedup)} | feeders_in_rows_all={feeder_cnt} | missing_sample={missing}")
            except Exception:
                pass
            self.intranet_rows = dedup

            # Populate filters and fill table
            try:
                self._populate_intranet_filters()
                self._apply_intranet_filters()
            except Exception:
                pass
        except Exception as ex:
            self._log(f"[Intranet] Overlay error: {ex}")

        try:
            self.progress.setVisible(False)
            self.status_label.setText("Gotowy")
        except Exception:
            pass
    def _populate_intranet_filters(self):
        rows = getattr(self, 'intranet_rows', [])
        codes = sorted({r.get('source_mapped','') for r in rows if r.get('source_mapped')})
        prev = self.intra_f_machine.currentText() if self.intra_f_machine.count() else ""
        self.intra_f_machine.blockSignals(True)
        self.intra_f_machine.clear()
        self.intra_f_machine.addItem("(Wszystkie)")
        for c in codes:
            self.intra_f_machine.addItem(c)
        ix = self.intra_f_machine.findText(prev)
        if ix >= 0:
            self.intra_f_machine.setCurrentIndex(ix)
        self.intra_f_machine.blockSignals(False)

    def _apply_intranet_filters(self):
        rows = getattr(self, 'intranet_rows', [])
        if not isinstance(rows, list):
            rows = []
        sel = self.intra_f_machine.currentText() if self.intra_f_machine.count() else "(Wszystkie)"
        flt = []
        for r in rows:
            mapped = str(r.get('source_mapped','') or '')
            if sel and sel != "(Wszystkie)":
                if not mapped or sel != mapped:
                    continue
            flt.append(r)
        self.intranet_filtered_rows = flt
        # Fill intranet table
        self.intra_table.setRowCount(len(flt))
        for i, r in enumerate(flt):
            self.intra_table.setItem(i, 0, QTableWidgetItem(r.get('maszyna_sap','')))
            self.intra_table.setItem(i, 1, QTableWidgetItem(r.get('maszyna_opis','')))
            self.intra_table.setItem(i, 2, QTableWidgetItem(r.get('source_opis','')))
            self.intra_table.setItem(i, 3, QTableWidgetItem(r.get('source_mapped','')))
            dt = r.get('data')
            self.intra_table.setItem(i, 4, QTableWidgetItem(dt.strftime('%Y-%m-%d %H:%M:%S') if dt else ''))
            self.intra_table.setItem(i, 5, QTableWidgetItem(r.get('serial_no','')))
            self.intra_table.setItem(i, 6, QTableWidgetItem(r.get('judge','')))
        try:
            self.intra_table.resizeColumnsToContents()
        except Exception:
            pass
    def _on_intranet_error(self, err: str):
        self._log(f"[Intranet] Błąd pobierania: {err}. Pomijam overlay.")
        try:
            self.progress.setVisible(False)
            self.status_label.setText("Gotowy")
        except Exception:
            pass
    def _fill_table(self):

        if not hasattr(self, 'table') or self.table is None:
            return
        self.table.setRowCount(0)
        if not self.found_files:
            return
        self.found_files.sort(key=lambda f: (f.machine, f.dt))
        self.table.setRowCount(len(self.found_files))
        for row, f in enumerate(self.found_files):
            self.table.setItem(row, 0, QTableWidgetItem(f.machine))
            self.table.setItem(row, 1, QTableWidgetItem(f.dt.strftime('%Y-%m-%d')))
            self.table.setItem(row, 2, QTableWidgetItem(f.dt.strftime('%H:%M:%S')))
            self.table.setItem(row, 3, QTableWidgetItem(f.path))


    def _table_menu(self, pos):

        return


    def _filter_tree(self, text: str):
        if not hasattr(self, 'tree') or self.tree is None:
            return
        query = (text or '').strip().lower()

        def show_all(item):
            item.setHidden(False)
            for i in range(item.childCount()):
                show_all(item.child(i))

        def matches(item) -> bool:
            cols = [item.text(c).lower() for c in range(self.tree.columnCount())]
            here = any(query in c for c in cols)
            any_child = False
            for i in range(item.childCount()):
                if matches(item.child(i)):
                    any_child = True
            visible = here or any_child
            item.setHidden(not visible)

            if visible and query:
                p = item.parent()
                while p is not None:
                    p.setHidden(False)
                    p.setExpanded(True)
                    p = p.parent()
            return visible

        self.tree.setUpdatesEnabled(False)
        if not query:
            for i in range(self.tree.topLevelItemCount()):
                show_all(self.tree.topLevelItem(i))

            self.tree.expandToDepth(1)
        else:
            for i in range(self.tree.topLevelItemCount()):
                matches(self.tree.topLevelItem(i))
            self.tree.expandAll()
        self.tree.setUpdatesEnabled(True)

    def _make_color_icon(self, color: QColor, size: int = 14) -> QIcon:
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        from PyQt5.QtGui import QPainter, QPen
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        r = size/2

        p.setPen(QPen(QColor('#ffffff'), 2))
        p.setBrush(QColor('#ffffff'))
        p.drawRoundedRect(0, 0, size, size, r, r)

        inset = 2
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(inset, inset, size-2*inset, size-2*inset, r-2, r-2)
        p.end()
        return QIcon(pm)


    def _make_action_icon(self, kind: str, size: int = 18) -> QIcon:
        from PyQt5.QtGui import QPainter, QPen
        from PyQt5.QtCore import QPointF, QRectF
        import math
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        pen_w = max(2, int(size * 0.10))
        if kind == 'select':
            color = QColor('#27ae60')  # green
        elif kind == 'deselect':
            color = QColor('#e74c3c')  # red
        else:
            color = QColor('#3498db')  # blue for refresh and default
        pen = QPen(color, pen_w)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)

        if kind == 'select':
            x0, y0 = size * 0.20, size * 0.55
            x1, y1 = size * 0.42, size * 0.78
            x2, y2 = size * 0.82, size * 0.28
            p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        elif kind == 'deselect':
            m = size * 0.18
            rect = QRectF(m, m, size - 2 * m, size - 2 * m)
            p.drawEllipse(rect)
            p.drawLine(QPointF(rect.left() + 1, rect.bottom() - 1), QPointF(rect.right() - 1, rect.top() + 1))
        elif kind == 'refresh':
            m = size * 0.18
            rect = QRectF(m, m, size - 2 * m, size - 2 * m)
            p.drawArc(rect, int(45 * 16), int(270 * 16))
            cx, cy = rect.center().x(), rect.center().y()
            r = rect.width() / 2
            ang = math.radians(45)
            tip = QPointF(cx + r * math.cos(ang), cy - r * math.sin(ang))
            p.drawLine(tip, QPointF(tip.x() - size * 0.12, tip.y()))
            p.drawLine(tip, QPointF(tip.x(), tip.y() + size * 0.12))
        p.end()
        return QIcon(pm)

    def _update_thread_state(self, text: str):
        try:
            if hasattr(self, 'thread_state') and self.thread_state is not None:
                self.thread_state.setText(text)
        except Exception:
            pass

    def _stop_analysis(self):
        try:
            # Stop running workers gracefully
            for name in ('a_worker', 'worker', 'intra_worker'):
                w = getattr(self, name, None)
                if w is not None:
                    try:
                        if hasattr(w, 'requestInterruption'):
                            w.requestInterruption()
                    except Exception:
                        pass
                    try:
                        w.quit()
                    except Exception:
                        pass
                    try:
                        w.wait(3000)
                    except Exception:
                        pass
            self.progress.setVisible(False)
            self.status_label.setText('Zatrzymano')
            self._update_thread_state('Wątki: bezczynne')
            try:
                self.analysis_run_btn.setEnabled(True)
            except Exception:
                pass
        except Exception:
            pass

    def _start_analysis(self):
        if not getattr(self, 'found_files', None):
            QMessageBox.information(self, "Brak danych", "Najpierw uruchom skanowanie, aby znaleźć pliki.")
            return
        try:
            if getattr(self, 'a_worker', None) is not None and self.a_worker.isRunning():
                return
        except Exception:
            pass
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.status_label.setText("Analiza zmian...")
        self.analysis_run_btn.setEnabled(False)
        self.analysis_table.setRowCount(0)
        self.analysis_records = []
        try:
            self._update_thread_state('Wątki: analiza')
        except Exception:
            pass


        try:
            self.analysis_started_at = datetime.now()
            total_files = len(self.found_files)
            self._log(
                f"[Analysis] START {self.analysis_started_at.strftime('%Y-%m-%d %H:%M:%S')} | files={total_files}"
            )
            if LET is None:
                self._log("[Analysis] XML parser: stdlib ElementTree (lxml not available)")
            else:
                self._log("[Analysis] XML parser: lxml.etree")
        except Exception:
            pass
        try:
            pref_workers = self.settings.value("analysis_workers", 0, type=int)
        except Exception:
            pref_workers = 0
        self.a_worker = AnalyzeWorker(self.found_files, max_workers=(pref_workers if pref_workers and pref_workers > 0 else None))
        self.a_worker.progress.connect(self._on_progress)
        self.a_worker.finished.connect(self._on_analysis_finished)
        self.a_worker.error.connect(self._on_analysis_error)
        try:
            self._log(f"[Analysis] workers={self.a_worker.max_workers}")
        except Exception:
            pass
        self.a_worker.start()

    def _on_analysis_error(self, err: str):
        self.progress.setVisible(False)
        self.status_label.setText("Błąd analizy")
        self.analysis_run_btn.setEnabled(True)
        QMessageBox.critical(self, "Błąd analizy", err)
        try:
            end = datetime.now()
            start = getattr(self, 'analysis_started_at', None)
            dur = (end - start) if start else None
            dur_txt = str(dur).split('.', 1)[0] if dur else 'n/a'
            self._log(
                f"[Analysis] END {end.strftime('%Y-%m-%d %H:%M:%S')} | duration={dur_txt} (ERROR)"
            )
        except Exception:
            pass
    def _on_analysis_finished(self, records: list):
        self.progress.setVisible(False)
        self.status_label.setText("Analiza zakończona")
        self.analysis_run_btn.setEnabled(True)
        try:
            end = datetime.now()
            start = getattr(self, 'analysis_started_at', None)
            dur = (end - start) if start else None
            dur_txt = str(dur).split('.', 1)[0] if dur else 'n/a'
            self._log(
                f"[Analysis] END {end.strftime('%Y-%m-%d %H:%M:%S')} | duration={dur_txt}"
            )
        except Exception:
            pass
        snaps: list[ParamSnapshot] = sorted(records, key=lambda r: r.dt)
        events = []
        prog_events = []
        seen_prog = set()
        last_state = {}
        last_prog = {}
        baseline_done = set()
        try:
            threshold_pct = float(self.settings.value("large_change_threshold_pct", 10, type=int))
        except Exception:
            threshold_pct = 10.0
        for s in snaps:
            key = (s.machine, s.table, s.pin, s.step)
            if key not in baseline_done:

                baseline_done.add(key)
                last_state[key] = dict(s.values)
                last_prog[key] = s.program
                continue

            if last_prog.get(key) != s.program:
                pe_key = (s.machine, last_prog.get(key, ''), s.program, s.dt)
                if pe_key not in seen_prog:
                    seen_prog.add(pe_key)
                    prog_events.append({
                        'dt': s.dt,
                        'machine': s.machine,
                        'old_program': last_prog.get(key, ''),
                        'new_program': s.program,
                    })
                last_state[key] = dict(s.values)
                last_prog[key] = s.program
                continue

            prev = last_state.get(key, {})
            changed_cols = {}
            large_cols = {}
            for name in PARAM_DISPLAY_ORDER:
                nv = s.values.get(name, 0)
                pv = prev.get(name, 0)
                if abs((nv or 0) - (pv or 0)) > 1e-12:
                    changed_cols[name] = f"{pv:g} -> {nv:g}"
                    if abs(pv) > 1e-12:
                        pct = abs((nv - pv) / pv) * 100.0
                    else:
                        pct = 100.0 if abs(nv) > 1e-12 else 0.0
                    large_cols[name] = (pct >= threshold_pct)
                else:
                    changed_cols[name] = ""
                    large_cols[name] = False
            if any(changed_cols.values()):
                row = {
                    'dt': s.dt,
                    'machine': s.machine,
                    'program': s.program,
                    'table': s.table,
                    'pin': s.pin,
                    'step': s.step,
                    'cols': changed_cols,
                    'large': large_cols,
                    'path': s.path,
                    'type': 'change',
                }
                events.append(row)
                last_state[key] = dict(s.values)
                last_prog[key] = s.program

        events.sort(key=lambda x: (x['dt'], x['machine'], x.get('pin', ''), x['step']))
        prog_events.sort(key=lambda x: (x['dt'], x['machine']))
        self.analysis_events = events
        self.program_events = prog_events
        self._populate_analysis_filters()
        self._apply_analysis_filters()
        self._populate_program_filters()
        self._apply_program_filters()
        try:
            self._fill_change_trees()
        except Exception:
            pass
        try:
            self._populate_trend_filters()
            self._apply_trend_filters()
        except Exception:
            pass
        try:
            self._populate_trend_filters()
            self._apply_trend_filters()
        except Exception:
            pass
    def _populate_analysis_filters(self):

        machines = sorted({e['machine'] for e in getattr(self, 'analysis_events', [])})
        pins = sorted({e['pin'] for e in getattr(self, 'analysis_events', []) if e['pin']})
        steps = sorted({e['step'] for e in getattr(self, 'analysis_events', [])})
        params = PARAM_DISPLAY_ORDER

        def fill(cb, items):
            prev = cb.currentText() if cb.count() else ""
            cb.blockSignals(True)
            cb.clear()
            cb.addItem("(Wszystkie)")
            for it in items:
                cb.addItem(str(it))

            ix = cb.findText(prev)
            if ix >= 0:
                cb.setCurrentIndex(ix)
            cb.blockSignals(False)

        fill(self.f_machine, machines)
        fill(self.f_pin, pins)
        fill(self.f_step, steps)
        fill(self.f_param, params)

    def _apply_analysis_filters(self):
        if not hasattr(self, 'analysis_events'):
            return
        m = self.f_machine.currentText() if self.f_machine.count() else "(Wszystkie)"
        pin = self.f_pin.currentText() if self.f_pin.count() else "(Wszystkie)"
        st = self.f_step.currentText() if self.f_step.count() else "(Wszystkie)"
        par = self.f_param.currentText() if self.f_param.count() else "(Wszystkie)"

        rows = []
        for e in getattr(self, 'analysis_events', []):

            if e.get('type') != 'change':
                continue
            if m and m != "(Wszystkie)" and e['machine'] != m:
                continue
            if pin and pin != "(Wszystkie)" and e['pin'] != pin:
                continue
            if st and st != "(Wszystkie)" and str(e['step']) != st:
                continue
            if par and par != "(Wszystkie)":

                if not e['cols'].get(par):
                    continue
            rows.append(e)


        rows.sort(key=lambda x: (x['dt'], x['machine'], x.get('pin',''), x['step']))

        self.analysis_table.setRowCount(len(rows))
        highlight = QBrush(QColor('#fff6bf'))
        big_change = QBrush(QColor('#ffd6d6'))
        for i, e in enumerate(rows):
            self.analysis_table.setItem(i, 0, QTableWidgetItem(e['dt'].strftime('%Y-%m-%d')))
            self.analysis_table.setItem(i, 1, QTableWidgetItem(e['dt'].strftime('%H:%M:%S')))
            self.analysis_table.setItem(i, 2, QTableWidgetItem(e['machine']))
            self.analysis_table.setItem(i, 3, QTableWidgetItem(e['program']))
            self.analysis_table.setItem(i, 4, QTableWidgetItem(e['table']))
            self.analysis_table.setItem(i, 5, QTableWidgetItem(e['pin']))
            self.analysis_table.setItem(i, 6, QTableWidgetItem(str(e['step'])))

            base = 7
            params = PARAM_DISPLAY_ORDER
            for j, name in enumerate(params):
                val = e['cols'].get(name, "")
                item = QTableWidgetItem(val)
                if val:
                    if e.get('large', {}).get(name):
                        item.setBackground(big_change)
                    else:
                        item.setBackground(highlight)
                self.analysis_table.setItem(i, base + j, item)

            path_col_idx = base + len(params)
            self.analysis_table.setItem(i, path_col_idx, QTableWidgetItem(e.get('path','')))
        self.analysis_table.resizeColumnsToContents()
        self.analysis_filtered_rows = rows

    def _fill_change_trees(self):
        try:
            from PyQt5.QtWidgets import QTreeWidgetItem
            events = getattr(self, 'analysis_events', [])
            if not hasattr(self, 'top_issues_tree') or not hasattr(self, 'change_tree'):
                return
            per_mach = {}
            for e in events:
                if e.get('type') != 'change':
                    continue
                m = e.get('machine', '')
                grp = per_mach.setdefault(m, {'pin': {}, 'step': {}, 'param': {}})
                pin = e.get('pin', '')
                if pin:
                    grp['pin'][pin] = grp['pin'].get(pin, 0) + 1
                st = e.get('step')
                if st is not None:
                    s = str(st)
                    grp['step'][s] = grp['step'].get(s, 0) + 1
                for name, ch in (e.get('cols') or {}).items():
                    if ch:
                        grp['param'][name] = grp['param'].get(name, 0) + 1

            self.top_issues_tree.clear()
            for mach, groups in sorted(per_mach.items(), key=lambda kv: -(sum(groups['pin'].values()) + sum(groups['step'].values()) + sum(groups['param'].values()))):
                tot = sum(groups['pin'].values()) + sum(groups['step'].values()) + sum(groups['param'].values())
                m_item = QTreeWidgetItem([mach, str(tot)])
                m_item.setData(0, Qt.UserRole, ('machine', mach))
                self.top_issues_tree.addTopLevelItem(m_item)
                for label, key in (("Piny", 'pin'), ("Kroki", 'step'), ("Parametry", 'param')):
                    grp_item = QTreeWidgetItem([label, str(sum(groups[key].values()))])
                    m_item.addChild(grp_item)
                    for name, cnt in sorted(groups[key].items(), key=lambda kv: -kv[1])[:20]:
                        it = QTreeWidgetItem([name, str(cnt)])
                        it.setData(0, Qt.UserRole, (key, mach, name))
                        grp_item.addChild(it)
                m_item.setExpanded(True)

            self.change_tree.clear()
            idx = {}
            for e in events:
                if e.get('type') != 'change':
                    continue
                m = e.get('machine', '')
                pin = e.get('pin', '')
                st = str(e.get('step'))
                idx_m = idx.setdefault(m, {})
                idx_p = idx_m.setdefault(pin, {})
                idx_p[st] = idx_p.get(st, 0) + 1
            for mach, pins in sorted(idx.items()):
                m_cnt = sum(sum(steps.values()) for steps in pins.values())
                m_item = QTreeWidgetItem([mach, str(m_cnt)])
                m_item.setData(0, Qt.UserRole, ('machine', mach))
                self.change_tree.addTopLevelItem(m_item)
                for pin, steps in sorted(pins.items(), key=lambda kv: -sum(kv[1].values())):
                    p_cnt = sum(steps.values())
                    p_it = QTreeWidgetItem([pin or '(brak)', str(p_cnt)])
                    p_it.setData(0, Qt.UserRole, ('pin', mach, pin))
                    m_item.addChild(p_it)
                    for st, cnt in sorted(steps.items(), key=lambda kv: -kv[1]):
                        s_it = QTreeWidgetItem([f"Step {st}", str(cnt)])
                        s_it.setData(0, Qt.UserRole, ('step', mach, st))
                        p_it.addChild(s_it)
                m_item.setExpanded(True)
        except Exception:
            pass

    def _on_top_issue_click(self, item, col):
        try:
            data = item.data(0, Qt.UserRole)
            if not data:
                return
            kind = data[0]
            if kind == 'machine':
                self._set_combo(self.f_machine, data[1])
            elif kind == 'pin':
                _, mach, pin = data
                self._set_combo(self.f_machine, mach)
                self._set_combo(self.f_pin, pin)
            elif kind == 'step':
                _, mach, st = data
                self._set_combo(self.f_machine, mach)
                self._set_combo(self.f_step, str(st))
            elif kind == 'param':
                _, mach, par = data
                self._set_combo(self.f_machine, mach)
                self._set_combo(self.f_param, par)
            self._apply_analysis_filters()
        except Exception:
            pass

    def _on_change_tree_click(self, item, col):
        try:
            data = item.data(0, Qt.UserRole)
            if not data:
                return
            kind = data[0]
            if kind == 'machine':
                self._set_combo(self.f_machine, data[1])
            elif kind == 'pin':
                _, mach, pin = data
                self._set_combo(self.f_machine, mach)
                self._set_combo(self.f_pin, pin)
            elif kind == 'step':
                _, mach, st = data
                self._set_combo(self.f_machine, mach)
                self._set_combo(self.f_step, str(st))
            self._apply_analysis_filters()
        except Exception:
            pass

    def _set_combo(self, combo, value):
        try:
            if not combo or combo.count() == 0:
                return
            ix = combo.findText(str(value))
            if ix >= 0:
                combo.setCurrentIndex(ix)
        except Exception:
            pass

    def _fill_program_changes_table(self):
        rows = getattr(self, 'program_events', [])
        self.program_table.setRowCount(len(rows))
        for i, e in enumerate(rows):
            self.program_table.setItem(i, 0, QTableWidgetItem(e['dt'].strftime('%Y-%m-%d')))
            self.program_table.setItem(i, 1, QTableWidgetItem(e['dt'].strftime('%H:%M:%S')))
            self.program_table.setItem(i, 2, QTableWidgetItem(e['machine']))
            self.program_table.setItem(i, 3, QTableWidgetItem(f"{e.get('old_program','')} -> {e.get('new_program','')}"))
        self.program_table.resizeColumnsToContents()
        self.program_filtered_rows = rows

    def _populate_program_filters(self):
        rows = getattr(self, 'program_events', [])
        machines = sorted({e['machine'] for e in rows})
        olds = sorted({e['old_program'] for e in rows})
        news = sorted({e['new_program'] for e in rows})

        def fill(cb, items):
            prev = cb.currentText() if cb.count() else ""
            cb.blockSignals(True)
            cb.clear()
            cb.addItem("(Wszystkie)")
            for it in items:
                cb.addItem(str(it))
            ix = cb.findText(prev)
            if ix >= 0:
                cb.setCurrentIndex(ix)
            cb.blockSignals(False)

        fill(self.pg_f_machine, machines)
        fill(self.pg_f_old, olds)
        fill(self.pg_f_new, news)

    def _populate_trend_filters(self):
        rows = getattr(self, 'found_files', [])
        machines = sorted({f.machine for f in rows})
        try:
            self._log(f"[Trends] _populate_trend_filters: machines={len(machines)}")
        except Exception:
            pass
        def fill(cb, items):
            prev = cb.currentText() if cb.count() else ""
            cb.blockSignals(True)
            cb.clear()
            cb.addItem("(Wszystkie)")
            for it in items:
                cb.addItem(str(it))
            ix = cb.findText(prev)
            if ix >= 0:
                cb.setCurrentIndex(ix)
            cb.blockSignals(False)

        fill(self.t_f_machine, machines)

    def _apply_trend_filters(self):
        rows = getattr(self, 'found_files', [])
        if not rows:
            return
        m = self.t_f_machine.currentText() if self.t_f_machine.count() else "(Wszystkie)"

        flt = [f for f in rows if (m == "(Wszystkie)" or f.machine == m)]

        try:
            start_dt = self.start_datetime.dateTime().toPyDateTime()
            end_dt = self.end_datetime.dateTime().toPyDateTime()
        except Exception:
            if flt:
                start_dt = min(e['dt'] for e in flt)
                end_dt = max(e['dt'] for e in flt)
            else:
                start_dt = datetime.now()
                end_dt = start_dt
        total_minutes = max(1, int((end_dt - start_dt).total_seconds() // 60))
        target_bins = 96
        approx_bin = max(1, total_minutes // max(1, target_bins))
        def snap_15(n):
            return int(max(15, min(180, ((n + 14)//15)*15)))
        bin_min = snap_15(approx_bin)

        # Build same series as in summary, but filtered by machine
        try:
            self._log(f"[Trends] _apply_trend_filters: sel='{m}', rows={len(flt)}")
            try:
                start_dt = self.start_datetime.dateTime().toPyDateTime()
                end_dt = self.end_datetime.dateTime().toPyDateTime()
                rng_secs = abs((end_dt - start_dt).total_seconds())
            except Exception:
                start_dt = None
                end_dt = None
                rng_secs = 0
            if (rng_secs <= 0 or start_dt is None or end_dt is None) and flt:
                dts = [f.dt for f in flt]
                start_dt = min(dts)
                end_dt = max(dts)
                rng_secs = (end_dt - start_dt).total_seconds()

            total_hours = max(1, int((rng_secs + 3599) // 3600)) if rng_secs else 1
            bin_hours = 1
            if total_hours > 240:
                bin_hours = 2
            if total_hours > 480:
                bin_hours = 3

            def norm_key(dt):
                base = dt.replace(minute=0, second=0, microsecond=0)
                h = (base.hour // bin_hours) * bin_hours
                base = base.replace(hour=h)
                return base.strftime('%Y-%m-%d %H:00')

            # contiguous buckets (no gaps)
            from datetime import timedelta as _td
            start_norm = start_dt.replace(minute=0, second=0, microsecond=0)
            start_norm = start_norm.replace(hour=(start_norm.hour // bin_hours) * bin_hours)
            end_floor = end_dt.replace(minute=0, second=0, microsecond=0)
            end_floor = end_floor.replace(hour=(end_floor.hour // bin_hours) * bin_hours)
            end_norm = end_floor if end_floor >= end_dt else end_floor + _td(hours=bin_hours)
            bucket_keys = []
            cur = start_norm
            while cur <= end_norm:
                bucket_keys.append(cur.strftime('%Y-%m-%d %H:00'))
                cur += _td(hours=bin_hours)
            per_machine = defaultdict(lambda: defaultdict(int))
            machines = set()
            for f in flt:
                machines.add(f.machine)
                key = norm_key(f.dt)
                per_machine[f.machine][key] += 1
            x_keys = bucket_keys
            series = {}
            for machine in sorted(per_machine.keys()):
                series[machine] = [per_machine[machine].get(k, 0) for k in x_keys]

            palette = ['#3498db', '#2ecc71', '#e74c3c', '#f1c40f', '#9b59b6', '#1abc9c', '#34495e', '#e67e22', '#7f8c8d']
            sorted_names = sorted(machines)
            color_map = {name: QColor(palette[i % len(palette)]) for i, name in enumerate(sorted_names)}
            self.trend_bar_native.set_colors(color_map)
            self.trend_bar_native.set_data(x_keys, series)
            self._log(f"[Trends] Render: bin_hours={bin_hours}, x={len(x_keys)} series={len(series)}")

            # Overlay NOK counts aligned to x_keys for selected machine
            try:
                nok_rows = getattr(self, 'intranet_rows', [])
                if nok_rows:
                    sel_machine = m if m and m != '(Wszystkie)' else ''
                    sel_prefix = sel_machine[:1].upper() if sel_machine else ''

                    import re as _re
                    def _feeder_map(num: int, pref: str) -> str:
                        if pref == 'S':
                            return self._feeder_map_S.get(num, '')
                        if pref == 'M':
                            return self._feeder_map_M.get(num, '')
                        # fallback: any known
                        return self._feeder_map_M.get(num, self._feeder_map_S.get(num, ''))

                    def _map_row_machine(r) -> str:
                        opis = str(r.get('maszyna_opis','') or '')
                        toks = opis.strip().split()
                        if toks:
                            cand = toks[-1].upper()
                            if len(cand) >= 2 and cand[0] in ('M','S') and cand[1:].isdigit():
                                return cand
                        mobj = _re.search(r"podajnik\s*drutu\s*(\d+)", opis, _re.I)
                        if mobj:
                            try:
                                return _feeder_map(int(mobj.group(1)), sel_prefix)
                            except Exception:
                                return ''
                        return ''

                    def _norm_label(dt):
                        base = dt.replace(minute=0, second=0, microsecond=0)
                        h = (base.hour // bin_hours) * bin_hours
                        base = base.replace(hour=h)
                        return base.strftime('%Y-%m-%d %H:00')

                    counts = {k: 0 for k in x_keys}
                    seen_sn = set()
                    for r in nok_rows:
                        try:
                            dt = r.get('data')
                            sn = str(r.get('serial_no',''))
                            if not dt or not sn:
                                continue
                            lab = _norm_label(dt)
                            if lab not in counts:
                                continue
                            rm = r.get('source_mapped') or _map_row_machine(r)
                            if sel_machine:
                                if not rm or rm.upper() != sel_machine.upper():
                                    continue
                            if sn in seen_sn:
                                continue
                            seen_sn.add(sn)
                            counts[lab] += 1
                        except Exception:
                            continue

                    self.trend_bar_native.set_overlay(x_keys, [counts.get(k, 0) for k in x_keys])
                else:
                    self.trend_bar_native.set_overlay([], [])
            except Exception:
                self.trend_bar_native.set_overlay([], [])
        except Exception:
            pass
    def _apply_program_filters(self):
        rows = getattr(self, 'program_events', [])
        m = self.pg_f_machine.currentText() if self.pg_f_machine.count() else "(Wszystkie)"
        o = self.pg_f_old.currentText() if self.pg_f_old.count() else "(Wszystkie)"
        n = self.pg_f_new.currentText() if self.pg_f_new.count() else "(Wszystkie)"
        flt = []
        for e in rows:
            if m != "(Wszystkie)" and e['machine'] != m:
                continue
            if o != "(Wszystkie)" and e['old_program'] != o:
                continue
            if n != "(Wszystkie)" and e['new_program'] != n:
                continue
            flt.append(e)

        flt.sort(key=lambda x: (x['dt'], x['machine']))
        self.program_table.setRowCount(len(flt))
        for i, e in enumerate(flt):
            self.program_table.setItem(i, 0, QTableWidgetItem(e['dt'].strftime('%Y-%m-%d')))
            self.program_table.setItem(i, 1, QTableWidgetItem(e['dt'].strftime('%H:%M:%S')))
            self.program_table.setItem(i, 2, QTableWidgetItem(e['machine']))
            self.program_table.setItem(i, 3, QTableWidgetItem(f"{e.get('old_program','')} -> {e.get('new_program','')}"))
        self.program_table.resizeColumnsToContents()
        self.program_filtered_rows = flt

    def _export_analysis_csv(self):
        rows = getattr(self, 'analysis_filtered_rows', getattr(self, 'analysis_events', []))
        if not rows:
            QMessageBox.information(self, "Brak danych", "Brak wierszy do eksportu.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz CSV", "zmiany_parametrow.csv", "CSV Files (*.csv)")
        if not path:
            return
        headers = ["Data","Czas","Maszyna","Program","Tabela","Pin","Step"] + PARAM_DISPLAY_ORDER
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f, delimiter=';')
                w.writerow(headers)
                for e in rows:
                    if e.get('type') != 'change':
                        continue
                    row = [
                        e['dt'].strftime('%Y-%m-%d'),
                        e['dt'].strftime('%H:%M:%S'),
                        e['machine'], e['program'], e['table'], e['pin'], e['step'],
                    ]
                    row += [e['cols'].get(name, "") for name in PARAM_DISPLAY_ORDER]
                    w.writerow(row)
            self._log(f"[Export] Zapisano CSV: {path}")
        except Exception as ex:
            QMessageBox.critical(self, "BĂ„Ä…Ă˘â‚¬ĹˇÄ‚â€žĂ˘â‚¬Â¦d eksportu", str(ex))

    def _export_programs_csv(self):
        rows = getattr(self, 'program_filtered_rows', getattr(self, 'program_events', []))
        if not rows:
            QMessageBox.information(self, "Brak danych", "Brak wierszy do eksportu.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz CSV", "zmiany_programow.csv", "CSV Files (*.csv)")
        if not path:
            return
        headers = ["Data","Czas","Maszyna","Stary program","Nowy program"]
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f, delimiter=';')
                w.writerow(headers)
                for e in rows:
                    w.writerow([
                        e['dt'].strftime('%Y-%m-%d'), e['dt'].strftime('%H:%M:%S'), e['machine'],
                        e.get('old_program',''), e.get('new_program','')
                    ])
            self._log(f"[Export] Zapisano CSV: {path}")
        except Exception as ex:
            QMessageBox.critical(self, "Błąd eksportu", str(ex))

    def _export_intranet_csv(self):
        # Prefer filtered rows if available; fallback to reading table
        rows = getattr(self, 'intranet_filtered_rows', getattr(self, 'intranet_rows', []))
        if not rows:
            try:
                rows = []
                for i in range(self.intra_table.rowCount()):
                    rows.append({
                        'maszyna_sap': self.intra_table.item(i,0).text() if self.intra_table.item(i,0) else '',
                        'maszyna_opis': self.intra_table.item(i,1).text() if self.intra_table.item(i,1) else '',
                        'source_opis': self.intra_table.item(i,2).text() if self.intra_table.item(i,2) else '',
                        'source_mapped': self.intra_table.item(i,3).text() if self.intra_table.item(i,3) else '',
                        'data': self.intra_table.item(i,4).text() if self.intra_table.item(i,4) else '',
                        'serial_no': self.intra_table.item(i,5).text() if self.intra_table.item(i,5) else '',
                        'judge': self.intra_table.item(i,6).text() if self.intra_table.item(i,6) else '',
                    })
            except Exception:
                rows = []
        if not rows:
            QMessageBox.information(self, "Brak danych", "Brak wierszy do eksportu.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz CSV", "intranet_nok.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f, delimiter=';')
                w.writerow(["Maszyna SAP","Maszyna","Źródło (opis)","Źródło (mapa)","Data","Serial No","Ocena"])
                for r in rows:
                    w.writerow([
                        r.get('maszyna_sap',''),
                        r.get('maszyna_opis',''),
                        r.get('source_opis',''),
                        r.get('source_mapped',''),
                        r.get('data',''),
                        r.get('serial_no',''),
                        r.get('judge','')
                    ])
            self._log(f"[Export] Zapisano CSV: {path}")
        except Exception as ex:
            QMessageBox.critical(self, "Błąd eksportu", str(ex))


def ensure_base_path(settings: QSettings) -> bool:
    base_path = settings.value("base_path", "", type=str)
    if not base_path:
        settings.setValue("base_path", DEFAULT_PATH_H66_2)
        base_path = DEFAULT_PATH_H66_2

    if network_path_available(base_path):
        return True

    dlg = NetworkCheckDialog(settings)
    res = dlg.exec_()
    return res == QDialog.Accepted and network_path_available(settings.value("base_path", "", type=str))


def _apply_fusion_palette(app: QApplication):

    app.setStyle("Fusion")
    pal = app.palette()
    pal.setColor(QPalette.Window, QColor(246, 247, 251))
    pal.setColor(QPalette.Base, QColor(255, 255, 255))
    pal.setColor(QPalette.AlternateBase, QColor(247, 249, 252))
    pal.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
    pal.setColor(QPalette.ToolTipText, QColor(33, 37, 41))
    pal.setColor(QPalette.Text, QColor(33, 37, 41))
    pal.setColor(QPalette.Button, QColor(255, 255, 255))
    pal.setColor(QPalette.ButtonText, QColor(33, 37, 41))
    pal.setColor(QPalette.Highlight, QColor(52, 152, 219))
    pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(pal)


def main():
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    try:
        # Force software OpenGL/ANGLE to avoid GPU/driver issues
        from PyQt5.QtWidgets import QApplication as _QApp  # noqa
        QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
        os.environ.setdefault("QT_OPENGL", "software")
        os.environ.setdefault("QT_ANGLE_PLATFORM", "warp")
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setOrganizationName(APP_ORG)
    app.setApplicationName(APP_NAME)
    _apply_fusion_palette(app)

    settings = QSettings()
    if not ensure_base_path(settings):
        sys.exit(0)

    w = ModernMainWindow(settings)
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

















