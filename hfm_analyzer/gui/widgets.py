"""GUI widget implementations used throughout the application."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Iterable, List

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QStyledItemDelegate, QWidget

from ..constants import SUMMARY_PALETTE
from .utils import _natural_sort_key

class PieChartWidget(QWidget):
    """Minimal pie chart widget used when WebEngine is unavailable."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data: dict[str, int] = {}
        self._colors: dict[str, QColor] = {}
        self.setMinimumHeight(220)

    def set_data(self, data: dict[str, int]) -> None:
        self._data = dict(data) if data else {}
        self.update()

    def set_colors(self, color_map: dict[str, QColor]) -> None:
        self._colors = dict(color_map or {})
        self.update()

    def paintEvent(self, event) -> None:  # pragma: no cover - GUI painting
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(8, 8, -8, -8)
        legend_width = 150
        chart_rect = rect.adjusted(0, 0, -legend_width, 0)

        target_diameter = chart_rect.height() * 0.8
        size = min(target_diameter, chart_rect.width() * 0.9)
        radius = size / 2
        center_x = chart_rect.left() + radius
        center_y = chart_rect.center().y()
        bbox = QRectF(center_x - radius, center_y - radius, size, size)

        total = sum(self._data.values()) or 1
        fallback_colors = [QColor(c) for c in SUMMARY_PALETTE]

        start_angle = 0.0
        for index, (label, value) in enumerate(sorted(self._data.items(), key=lambda item: -item[1])):
            angle = 360.0 * (value / total)
            color = self._colors.get(label, fallback_colors[index % len(fallback_colors)])
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawPie(bbox, int(start_angle * 16), int(angle * 16))
            start_angle += angle

        painter.setPen(QColor("#2c3e50"))
        font = painter.font()
        painter.setFont(font)
        text_x = chart_rect.right() + 10
        text_y = rect.top() + 4
        for index, (label, value) in enumerate(sorted(self._data.items(), key=lambda item: -item[1])):
            color = self._colors.get(label, fallback_colors[index % len(fallback_colors)])
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRect(int(text_x), int(text_y + index * 18), 12, 12)
            painter.setPen(QColor("#2c3e50"))
            painter.drawText(int(text_x + 18), int(text_y + 12 + index * 18), f"{label}: {value}")

class BarChartWidget(QWidget):
    """Stacked bar chart used for the activity summary."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._x: list[str] = []
        self._series: dict[str, List[int]] = {}
        self._colors: dict[str, QColor] = {}
        self.setMinimumHeight(220)
        self._overlay_x: list[str] = []
        self._overlay_y: list[int] = []
        self._overlay_min_top = 0

    def set_data(self, x_labels: Iterable[str], series: dict[str, Iterable[int]]) -> None:
        self._x = list(x_labels) if x_labels else []
        self._series = {name: list(values) for name, values in (series or {}).items()}
        self.update()

    def set_colors(self, color_map: dict[str, QColor]) -> None:
        self._colors = dict(color_map or {})
        self.update()

    def set_overlay(self, x_labels: Iterable[str], y_values: Iterable[int]) -> None:
        self._overlay_x = list(x_labels) if x_labels else []
        self._overlay_y = list(y_values) if y_values else []
        self.update()

    def set_overlay_min_ymax(self, value: int) -> None:
        try:
            self._overlay_min_top = int(value)
        except Exception:
            self._overlay_min_top = 0
        self.update()

    def paintEvent(self, event) -> None:  # pragma: no cover - GUI painting
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        outer = self.rect().adjusted(10, 10, -10, -10)
        legend_width = 160
        chart_rect = QRectF(outer.left() + 30, outer.top(), outer.width() - legend_width - 30 - 36, outer.height() - 36)
        painter.fillRect(self.rect(), QColor("white"))

        painter.setPen(QPen(QColor("#95a5a6"), 1))
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.bottomRight())
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.topLeft())

        if not self._x or not self._series:
            painter.setPen(QColor("#7f8c8d"))
            painter.drawText(chart_rect, Qt.AlignCenter, "Brak danych")
            return

        y_max = max((max(values) if values else 0) for values in self._series.values())
        y_max = max(1, y_max)
        y_max_overlay = max(self._overlay_y) if self._overlay_y else 0
        if self._overlay_min_top and y_max_overlay < self._overlay_min_top:
            y_max_overlay = self._overlay_min_top

        painter.setPen(QPen(QColor("#ecf0f1"), 1))
        for i in range(1, 5):
            y = chart_rect.bottom() - i * chart_rect.height() / 5
            painter.drawLine(QPointF(chart_rect.left(), y), QPointF(chart_rect.right(), y))

        painter.setPen(QColor("#7f8c8d"))
        for i in range(0, 6):
            y = chart_rect.bottom() - i * chart_rect.height() / 5
            value = int(round(y_max * i / 5))
            painter.drawText(int(outer.left()), int(y - 8), 28, 16, Qt.AlignRight | Qt.AlignVCenter, str(value))

        painter.setPen(QColor("#2c3e50"))
        painter.drawText(int(outer.left() + 4), int(chart_rect.top() - 6), "Zmiany")
        painter.drawText(int(chart_rect.right() + 24), int(chart_rect.top() - 6), "NOK")

        n_dates = len(self._x)
        names = sorted(self._series.keys())
        n_series = max(1, len(names))
        bar_group_width = chart_rect.width() / max(1, n_dates)
        bar_width = max(2.0, bar_group_width * 0.8 / n_series)

        painter.setPen(QColor("#2c3e50"))
        approx_label_width = 44
        max_labels = max(1, int(chart_rect.width() // approx_label_width))
        stride = max(1, int((len(self._x) + max_labels - 1) // max_labels))
        for index, label in enumerate(self._x):
            if index % stride != 0:
                continue
            cx = chart_rect.left() + (index + 0.5) * bar_group_width
            top_text = str(label)
            bottom_text = ""
            try:
                dt_str = str(label).replace("T", " ")
                fmt = "%Y-%m-%d %H:%M" if len(dt_str) > 10 else "%Y-%m-%d"
                parsed = datetime.strptime(dt_str, fmt)
                top_text = parsed.strftime("%d.%m")
                bottom_text = parsed.strftime("%H:%M") if len(dt_str) > 10 else parsed.strftime("%Y")
            except Exception:
                if len(top_text) > 8:
                    bottom_text = top_text[8:]
                    top_text = top_text[:8]
            painter.drawText(int(cx - 22), int(chart_rect.bottom() + 2), 44, 16, Qt.AlignCenter, top_text)
            painter.drawText(int(cx - 22), int(chart_rect.bottom() + 18), 44, 16, Qt.AlignCenter, bottom_text)

        for series_index, name in enumerate(names):
            color = self._colors.get(name, QColor("#3498db"))
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            values = self._series.get(name, [])
            for date_index, y_value in enumerate(values):
                cx_left = chart_rect.left() + date_index * bar_group_width
                x = cx_left + (bar_group_width - n_series * bar_width) / 2 + series_index * bar_width
                height = 0 if y_value <= 0 else (min(y_value, y_max) / y_max) * chart_rect.height()
                y = chart_rect.bottom() - height
                painter.drawRect(QRectF(x, y, bar_width, height))

        painter.setPen(QColor("#2c3e50"))
        legend_x = outer.right() - legend_width + 10
        legend_y = outer.top() + 4
        for index, name in enumerate(names):
            color = self._colors.get(name, QColor("#3498db"))
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRect(QRectF(legend_x, legend_y + index * 16 - 8, 14, 14))
            painter.setPen(QColor("#2c3e50"))
            painter.drawText(int(legend_x + 20), int(legend_y + 5 + index * 16), name)

        if y_max_overlay > 0:
            painter.setPen(QPen(QColor("#95a5a6"), 1))
            painter.drawLine(chart_rect.topRight(), chart_rect.bottomRight())
            painter.setPen(QColor("#7f8c8d"))
            for i in range(0, 6):
                y = chart_rect.bottom() - i * chart_rect.height() / 5
                value = int(round(y_max_overlay * i / 5))
                painter.drawText(int(chart_rect.right() + 2), int(y - 8), 48, 16, Qt.AlignLeft | Qt.AlignVCenter, str(value))

        if (
            self._overlay_x
            and self._overlay_y
            and len(self._overlay_x) == len(self._overlay_y)
            and y_max_overlay > 0
        ):
            try:
                x_index = {str(lbl): idx for idx, lbl in enumerate(self._x)}
                points = []
                for label, y_value in zip(self._overlay_x, self._overlay_y):
                    text = str(label)
                    position = None
                    if len(text) > 10 and text[10] in (" ", "T"):
                        day = text[:10]
                        day_index = x_index.get(day)
                        if day_index is not None:
                            try:
                                hours = int(text[11:13])
                                minutes = int(text[14:16]) if len(text) >= 16 and text[13] == ":" else 0
                            except Exception:
                                hours = 0
                                minutes = 0
                            fraction = max(0.0, min(0.999, (hours + minutes / 60.0) / 24.0))
                            position = day_index + fraction
                    if position is None:
                        day_index = x_index.get(text)
                        if day_index is None:
                            continue
                        position = day_index + 0.5
                    cx = chart_rect.left() + max(0.0, min(position, len(self._x))) * bar_group_width
                    yy = (0 if y_max_overlay == 0 else (y_value / y_max_overlay) * chart_rect.height())
                    y = chart_rect.bottom() - min(chart_rect.height(), max(0.0, yy))
                    points.append(QPointF(cx, y))
                if len(points) > 1:
                    painter.save()
                    painter.setClipRect(chart_rect)
                    painter.setPen(QPen(QColor("#e74c3c"), 2))
                    for idx in range(1, len(points)):
                        painter.drawLine(points[idx - 1], points[idx])
                    painter.restore()

                painter.setPen(QPen(QColor("#e74c3c"), 2))
                painter.drawLine(legend_x, legend_y + len(names) * 16, legend_x + 14, legend_y + len(names) * 16)
                painter.setPen(QColor("#2c3e50"))
                painter.drawText(int(legend_x + 20), int(legend_y + 5 + len(names) * 16), "NOK")
            except Exception:
                pass

class ParetoChartWidget(QWidget):
    """Simple Pareto chart that highlights dominant NOK sources."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._labels: list[str] = []
        self._values: list[int] = []
        self._cumulative: list[float] = []
        self._series_names: list[str] = []
        self._series_values: dict[str, list[int]] = {}
        self._colors: dict[str, QColor] = {}
        self.setMinimumHeight(260)

    def set_data(self, data: dict[str, int] | None) -> None:
        self._labels = []
        self._values = []
        self._cumulative = []
        self._series_names = []
        self._series_values = {}
        self._colors = {}
        if not data:
            self.update()
            return
        nested: dict[str, dict[str, int]] = {}
        is_nested = any(isinstance(value, dict) for value in data.values())
        if is_nested:
            for label, mapping in data.items():
                if not isinstance(mapping, dict):
                    continue
                cleaned: dict[str, int] = {}
                total_label = 0
                for source, raw in mapping.items():
                    try:
                        count = int(raw)
                    except Exception:
                        continue
                    if count == 0:
                        continue
                    name = str(source or "Nieznane").strip() or "Nieznane"
                    cleaned[name] = cleaned.get(name, 0) + count
                    total_label += count
                if total_label > 0:
                    nested[str(label)] = cleaned
        else:
            for label, raw in data.items():
                try:
                    count = int(raw)
                except Exception:
                    continue
                if count == 0:
                    continue
                nested[str(label)] = {"Łącznie": count}
        items: list[tuple[str, int, dict[str, int]]] = []
        for label, mapping in nested.items():
            total = sum(mapping.values())
            if total <= 0:
                continue
            items.append((label, total, dict(mapping)))
        if not items:
            self.update()
            return
        items.sort(key=lambda pair: -pair[1])
        total_sum = sum(value for _, value, _ in items) or 1
        running = 0
        cumulative: list[float] = []
        for _, value, _ in items:
            running += value
            cumulative.append(min(100.0, (running / total_sum) * 100.0))
        source_totals: dict[str, int] = defaultdict(int)
        for _, _, mapping in items:
            for source, count in mapping.items():
                source_totals[source] += count
        series_names = sorted(
            source_totals.keys(),
            key=lambda name: (-source_totals[name], _natural_sort_key(name)),
        )
        palette = [QColor(color) for color in SUMMARY_PALETTE]
        self._labels = [label for label, _, _ in items]
        self._values = [value for _, value, _ in items]
        self._cumulative = cumulative
        self._series_names = series_names
        self._series_values = {
            name: [mapping.get(name, 0) for _, _, mapping in items]
            for name in series_names
        }
        self._colors = {
            name: palette[idx % len(palette)] if palette else QColor("#3498db")
            for idx, name in enumerate(series_names)
        }
        self.update()

    def paintEvent(self, event) -> None:  # pragma: no cover - GUI painting
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("white"))

        outer = self.rect().adjusted(10, 10, -10, -10)
        legend_width = 150
        chart_rect = QRectF(
            outer.left() + 40,
            outer.top(),
            max(10.0, outer.width() - 40 - legend_width - 20),
            max(10.0, outer.height() - 40),
        )

        painter.setPen(QPen(QColor("#95a5a6"), 1))
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.bottomRight())
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.topLeft())

        if not self._labels:
            painter.setPen(QColor("#7f8c8d"))
            painter.drawText(chart_rect, Qt.AlignCenter, "Brak danych")
            return

        y_max = max(self._values) if self._values else 1
        y_max = max(1, y_max)

        painter.setPen(QPen(QColor("#ecf0f1"), 1))
        for i in range(1, 5):
            y = chart_rect.bottom() - i * chart_rect.height() / 5
            painter.drawLine(QPointF(chart_rect.left(), y), QPointF(chart_rect.right(), y))

        painter.setPen(QColor("#2c3e50"))
        for i in range(0, 6):
            y = chart_rect.bottom() - i * chart_rect.height() / 5
            value = int(round(y_max * i / 5))
            painter.drawText(int(outer.left()), int(y - 8), 28, 16, Qt.AlignRight | Qt.AlignVCenter, str(value))

        painter.drawText(int(outer.left() + 4), int(chart_rect.top() - 6), "Liczba NOK")
        painter.drawText(int(chart_rect.right() + 12), int(chart_rect.top() - 6), "%")

        bar_group_width = chart_rect.width() / max(1, len(self._labels))
        bar_width = max(6.0, bar_group_width * 0.6)
        label_stride = max(1, int(len(self._labels) / max(1, chart_rect.width() // 70)))

        for index, label in enumerate(self._labels):
            x = chart_rect.left() + index * bar_group_width + (bar_group_width - bar_width) / 2
            y_bottom = chart_rect.bottom()
            for series_name in self._series_names:
                values = self._series_values.get(series_name, [])
                if index >= len(values):
                    continue
                value = values[index]
                if value <= 0:
                    continue
                height = (value / y_max) * chart_rect.height() if y_max else 0
                y_top = y_bottom - height
                painter.setPen(Qt.NoPen)
                painter.setBrush(self._colors.get(series_name, QColor("#2980b9")))
                painter.drawRect(QRectF(x, y_top, bar_width, height))
                y_bottom = y_top
            if index % label_stride == 0:
                text = str(label)
                if len(text) > 12:
                    top = text[:12]
                    bottom = text[12:24]
                else:
                    top = text
                    bottom = ""
                painter.setPen(QColor("#2c3e50"))
                painter.drawText(
                    int(x - bar_group_width * 0.1),
                    int(chart_rect.bottom() + 2),
                    int(bar_group_width * 1.2),
                    16,
                    Qt.AlignCenter,
                    top,
                )
                painter.drawText(
                    int(x - bar_group_width * 0.1),
                    int(chart_rect.bottom() + 18),
                    int(bar_group_width * 1.2),
                    16,
                    Qt.AlignCenter,
                    bottom,
                )

        cumulative_points: list[QPointF] = []
        painter.setPen(QPen(QColor("#e74c3c"), 2))
        for index, percentage in enumerate(self._cumulative):
            x = chart_rect.left() + (index + 0.5) * bar_group_width
            y = chart_rect.bottom() - (percentage / 100.0) * chart_rect.height()
            cumulative_points.append(QPointF(x, y))
        if cumulative_points:
            for start, end in zip(cumulative_points, cumulative_points[1:]):
                painter.drawLine(start, end)
            painter.setBrush(QColor("#e74c3c"))
            painter.setPen(Qt.NoPen)
            for point in cumulative_points:
                painter.drawEllipse(point, 4, 4)

        legend_x = chart_rect.right() + 24
        legend_y = outer.top() + 6
        painter.setPen(QColor("#2c3e50"))
        for idx, name in enumerate(self._series_names):
            color = self._colors.get(name, QColor("#2980b9"))
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRect(QRectF(legend_x, legend_y + idx * 16 - 6, 12, 12))
            painter.setPen(QColor("#2c3e50"))
            painter.drawText(int(legend_x + 18), int(legend_y + idx * 16 + 4), name)

        painter.setPen(QColor("#7f8c8d"))
        for i in range(0, 6):
            y = chart_rect.bottom() - i * chart_rect.height() / 5
            percentage = int(round(100 * i / 5))
            painter.drawText(
                int(chart_rect.right() + 16),
                int(y - 8),
                32,
                16,
                Qt.AlignLeft | Qt.AlignVCenter,
                f"{percentage}",
            )

class LineChartWidget(QWidget):
    """Simple line chart widget used for parameter trends when WebEngine is unavailable."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._points: list[tuple[datetime, float]] = []
        self._title: str = ""
        self._color = QColor("#3498db")
        self.setMinimumHeight(220)

    def set_series(
        self,
        title: str,
        points: Iterable[tuple[datetime, float]],
        color: QColor | None = None,
    ) -> None:
        self._title = title
        cleaned: list[tuple[datetime, float]] = []
        for dt, value in points or []:
            if not isinstance(dt, datetime):
                continue
            try:
                val = float(value)
            except Exception:
                continue
            if math.isnan(val) or math.isinf(val):
                continue
            cleaned.append((dt, val))
        cleaned.sort(key=lambda item: item[0])
        self._points = cleaned
        if color is not None:
            self._color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:  # pragma: no cover - GUI painting
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor("white"))
        outer = self.rect().adjusted(8, 8, -8, -8)
        painter.setPen(QPen(QColor("#d0d5db"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(outer, 8, 8)

        title_font = painter.font()
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor("#2c3e50"))
        painter.drawText(
            QRectF(outer.left() + 16, outer.top() + 8, outer.width() - 32, 24),
            Qt.AlignLeft | Qt.AlignVCenter,
            self._title,
        )

        body_font = painter.font()
        body_font.setBold(False)
        painter.setFont(body_font)

        chart_rect = QRectF(
            outer.left() + 16,
            outer.top() + 36,
            max(10.0, outer.width() - 32),
            max(10.0, outer.height() - 72),
        )

        if chart_rect.height() <= 0 or chart_rect.width() <= 0:
            return

        painter.setPen(QPen(QColor("#ecf0f1"), 1))
        for i in range(1, 5):
            y = chart_rect.bottom() - i * chart_rect.height() / 5
            painter.drawLine(QPointF(chart_rect.left(), y), QPointF(chart_rect.right(), y))

        painter.setPen(QPen(QColor("#95a5a6"), 1))
        painter.drawRect(chart_rect)

        if not self._points:
            painter.setPen(QColor("#7f8c8d"))
            painter.drawText(chart_rect, Qt.AlignCenter, "Brak danych")
            return

        base_dt = min(pt[0] for pt in self._points)
        x_values = [(pt[0] - base_dt).total_seconds() for pt in self._points]
        x_span = max(x_values) if x_values else 0.0
        if x_span <= 0:
            x_span = 1.0

        y_values = [pt[1] for pt in self._points]
        y_min = min(y_values)
        y_max = max(y_values)
        if math.isclose(y_min, y_max):
            delta = 1.0 if abs(y_min) < 1.0 else abs(y_min) * 0.1
            y_min -= delta
            y_max += delta
        else:
            margin = (y_max - y_min) * 0.1
            y_min -= margin
            y_max += margin
        if y_max <= y_min:
            y_max = y_min + 1.0

        painter.setPen(QColor("#7f8c8d"))
        for i in range(0, 5):
            frac = i / 4 if 4 else 0
            y = chart_rect.bottom() - frac * chart_rect.height()
            value = y_min + frac * (y_max - y_min)
            painter.drawText(
                QRectF(chart_rect.left() - 64, y - 8, 60, 16),
                Qt.AlignRight | Qt.AlignVCenter,
                f"{value:.3g}",
            )

        points = []
        for offset, value in zip(x_values, y_values):
            x = chart_rect.left() + (offset / x_span) * chart_rect.width()
            y = chart_rect.bottom() - ((value - y_min) / (y_max - y_min)) * chart_rect.height()
            points.append(QPointF(x, y))

        painter.setPen(QPen(self._color, 2))
        painter.setBrush(Qt.NoBrush)
        for idx in range(1, len(points)):
            painter.drawLine(points[idx - 1], points[idx])

        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        for pt in points:
            painter.drawEllipse(pt, 3.5, 3.5)

        tick_count = min(5, max(1, len(self._points)))
        if tick_count == 1:
            offsets = [x_values[0] if x_values else 0.0]
        else:
            offsets = [x_span * i / (tick_count - 1) for i in range(tick_count)]

        painter.setPen(QColor("#2c3e50"))
        for offset in offsets:
            x = chart_rect.left() + (offset / x_span) * chart_rect.width()
            dt = base_dt + timedelta(seconds=offset)
            date_txt = dt.strftime("%Y-%m-%d")
            time_txt = dt.strftime("%H:%M")
            painter.drawText(
                QRectF(x - 45, chart_rect.bottom() + 4, 90, 16),
                Qt.AlignHCenter | Qt.AlignVCenter,
                date_txt,
            )
            painter.drawText(
                QRectF(x - 45, chart_rect.bottom() + 20, 90, 16),
                Qt.AlignHCenter | Qt.AlignVCenter,
                time_txt,
            )

class CountBadgeDelegate(QStyledItemDelegate):
    """Delegate drawing circular badges for numeric values in tree widgets."""

    def paint(self, painter, option, index):  # pragma: no cover - GUI painting
        if index.column() != 1:
            return super().paint(painter, option, index)
        text = index.data()

        bg_brush = index.data(Qt.BackgroundRole)
        if isinstance(bg_brush, QBrush):
            color = bg_brush.color()
        elif isinstance(bg_brush, QColor):
            color = bg_brush
        else:
            color = QColor("#e0f0ff")
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
        painter.setPen(QPen(border, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
        text_color = QColor("#ffffff" if luminance < 150 else "#2c3e50")
        painter.setPen(text_color)
        painter.drawText(rect, Qt.AlignCenter, str(text))
        painter.restore()

    def sizeHint(self, option, index):  # pragma: no cover - GUI painting
        return super().sizeHint(option, index)

__all__ = [
    'PieChartWidget',
    'BarChartWidget',
    'ParetoChartWidget',
    'LineChartWidget',
    'CountBadgeDelegate',
]
