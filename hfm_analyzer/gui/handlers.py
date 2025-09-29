"""Event handler mixins for the GUI main window."""

from __future__ import annotations

import csv
import glob
import logging
import math
import os
import re
import string
import traceback
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Iterable, List

from PyQt5.QtCore import QDateTime, QTime, Qt, QPointF, QRectF, QSize
from PyQt5.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDateTimeEdit,
    QFileDialog,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from hfm_analyzer.constants import (
    APP_NAME,
    APP_ORG,
    DEFAULT_INTRANET_EXCLUDES,
    DEFAULT_PATH_EVO,
    DEFAULT_PATH_H66_2,
    INDEX_OVERRIDE_LABEL,
    INDEX_PARAM_DISPLAY_ORDER,
    PARAM_NAMES,
    PARAM_DISPLAY_ORDER,
    SUMMARY_PALETTE,
)
from hfm_analyzer.models import (
    FoundFile,
    GripSnapshot,
    HairpinSnapshot,
    IndexSnapshot,
    NestSnapshot,
    ParamSnapshot,
)
from hfm_analyzer.utils import (
    extract_unc_share,
    list_mapped_network_drives,
    map_network_drive,
    map_unc_to_drive_if_possible,
    network_path_available,
)
from hfm_analyzer.workers import (
    AnalyzeWorker,
    IntranetWorker,
    ScanWorker,
    STEP_SPEED_LABEL,
)
from hfm_analyzer.gui.dialogs import NetworkCheckDialog, SettingsDialog
from hfm_analyzer.gui.utils import (
    GRIP_PARAM_ORDER,
    HAIRPIN_PARAM_EXCLUDE,
    HAIRPIN_PARAM_LABELS,
    HAIRPIN_PARAM_ORDER,
    NEST_PARAM_ORDER,
    TRACKED_MACHINE_CODES,
    _natural_sort_key,
    _maybe_offer_drive_mapping,
)
from hfm_analyzer.gui.widgets import CountBadgeDelegate

class MainWindowHandlers:
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

    def _refresh_base_path_label(self):
            base_path = self.settings.value("base_path", "", type=str)
            display_name = self.settings.value("base_path_display_name", "", type=str)
            display_name = display_name.strip()
            if display_name:
                disp = display_name
            elif base_path:
                disp = base_path
            else:
                disp = "(nie ustawiono)"

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
            old_path = self.settings.value("base_path", "", type=str)
            new_path = QFileDialog.getExistingDirectory(self, "Wskaż katalog bazowy z backupami")
            if new_path:
                self.settings.setValue("base_path", new_path)
                if new_path != old_path:
                    self._reset_results_state(clear_found_files=True)
                self._refresh_base_path_label()
                self._populate_machines()

    def _open_settings(self):
            old_path = self.settings.value("base_path", "", type=str)
            old_line_id = self.settings.value("intranet_line_id", 436, type=int)
            dlg = SettingsDialog(self.settings, self)
            if dlg.exec_() == QDialog.Accepted:
                new_path = self.settings.value("base_path", "", type=str)
                new_line_id = self.settings.value("intranet_line_id", 436, type=int)
                if new_path != old_path or new_line_id != old_line_id:
                    self._reset_results_state(clear_found_files=True)
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


            self._reset_results_state(clear_found_files=True)
            self.progress.setRange(0, 0)
            self.progress.setVisible(True)
            self.status_label.setText("Trwa skanowanie...")
            self.scan_btn.setEnabled(False)
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
                if self.found_files:
                    self._start_analysis()
            except Exception:
                pass

    def _prepare_analysis_files(self) -> list[FoundFile]:
            files = list(getattr(self, 'found_files', []))
            if not files:
                return files

            base_path = self._get_base_path()
            if not base_path or not network_path_available(base_path):
                return files

            try:
                earliest: dict[str, FoundFile] = {}
                for entry in files:
                    current = earliest.get(entry.machine)
                    if current is None or entry.dt < current.dt:
                        earliest[entry.machine] = entry

                extras: list[FoundFile] = []
                baseline_details: list[tuple[str, str]] = []
                seen_paths = {entry.path for entry in files}
                for machine, ref in earliest.items():
                    prev = self._find_previous_backup_file(base_path, machine, ref.dt)
                    if prev is not None and prev.path not in seen_paths:
                        extras.append(prev)
                        seen_paths.add(prev.path)
                        try:
                            filename = os.path.basename(prev.path) if prev.path else "(brak)"
                        except Exception:
                            filename = prev.path or "(brak)"
                        baseline_details.append((machine, filename))

                if not extras:
                    return files

                combined = files + extras
                combined.sort(key=lambda item: (item.dt, item.machine, item.path))
                try:
                    details_txt = "; ".join(
                        f"{machine}: {name}" for machine, name in baseline_details
                    )
                    msg = (
                        f"[Analysis] Dodano {len(extras)} plik(ów) migawki spoza wybranego zakresu"
                    )
                    if details_txt:
                        msg += f": {details_txt}"
                    self._log(msg)
                except Exception:
                    pass
                return combined
            except Exception:
                return files

    def _find_previous_backup_file(
            self, base_path: str, machine: str, reference_dt: datetime
        ) -> FoundFile | None:
            try:
                machine_dir = os.path.join(base_path, machine)
                if not os.path.isdir(machine_dir):
                    return None

                try:
                    years = sorted(
                        (entry for entry in os.listdir(machine_dir) if entry.isdigit()),
                        reverse=True,
                    )
                except Exception:
                    years = []

                for year in years:
                    year_path = os.path.join(machine_dir, year)
                    if not os.path.isdir(year_path):
                        continue
                    try:
                        year_val = int(year)
                    except Exception:
                        continue
                    if year_val > reference_dt.year:
                        continue

                    try:
                        months = sorted(
                            (entry for entry in os.listdir(year_path) if entry.isdigit()),
                            reverse=True,
                        )
                    except Exception:
                        months = []

                    for month in months:
                        month_path = os.path.join(year_path, month)
                        if not os.path.isdir(month_path):
                            continue
                        try:
                            month_val = int(month)
                        except Exception:
                            continue
                        if year_val == reference_dt.year and month_val > reference_dt.month:
                            continue

                        try:
                            days = sorted(os.listdir(month_path), reverse=True)
                        except Exception:
                            days = []

                        for day_name in days:
                            day_path = os.path.join(month_path, day_name)
                            if not os.path.isdir(day_path):
                                continue
                            try:
                                day_date = datetime.strptime(day_name, "%Y-%m-%d").date()
                            except Exception:
                                continue
                            if day_date > reference_dt.date():
                                continue

                            pattern = os.path.join(day_path, f"{machine}_{day_name}_*.xml")
                            try:
                                candidates = sorted(glob.glob(pattern), reverse=True)
                            except Exception:
                                candidates = []

                            for path in candidates:
                                parts = os.path.basename(path).split("_")
                                if len(parts) < 3:
                                    continue
                                dt_str = parts[1] + "_" + parts[2].replace(".xml", "")
                                try:
                                    file_dt = datetime.strptime(
                                        dt_str, "%Y-%m-%d_%H-%M-%S"
                                    ).replace(second=0)
                                except Exception:
                                    continue
                                if file_dt >= reference_dt:
                                    continue
                                return FoundFile(machine=machine, dt=file_dt, path=path)
                return None
            except Exception:
                return None

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
                    nok_rows = getattr(self, 'intranet_nok_rows', getattr(self, 'intranet_rows', []))
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

            quality_rollup = self._quality_rollup_by_machine()

            if quality_rollup:
                for machine, machine_entry in quality_rollup.items():
                    days_map = machine_entry.get('days', {}) if isinstance(machine_entry, dict) else {}
                    machine_days = grouped[machine]
                    for day_key, day_entry in days_map.items():
                        hours_map = day_entry.get('hours', {}) if isinstance(day_entry, dict) else {}
                        day_hours = machine_days[day_key]
                        for hour_key in hours_map.keys():
                            _ = day_hours[hour_key]

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

                def _machine_code(name: object) -> str:
                    text = str(name or '').strip()
                    if not text:
                        return ''
                    match = re.search(r'([MS])\s*-?\s*(\d{1,2})', text.upper())
                    if not match:
                        return ''
                    prefix = match.group(1)
                    try:
                        num = int(match.group(2))
                    except Exception:
                        return ''
                    code = f"{prefix}{num}"
                    return code if code in TRACKED_MACHINE_CODES else ''

                ordered_codes = [f"M{i}" for i in range(1, 7)] + [f"S{i}" for i in range(1, 7)]
                code_order = {code: idx for idx, code in enumerate(ordered_codes)}

                machines_available = set(grouped.keys())
                if quality_rollup:
                    machines_available.update(quality_rollup.keys())

                machines_to_show = [
                    name for name in machines_available if _machine_code(name) in TRACKED_MACHINE_CODES
                ]
                machines_to_show.sort(
                    key=lambda nm: (
                        code_order.get(_machine_code(nm), len(code_order)),
                        str(nm),
                    )
                )

                machine_totals = {}
                for machine in machines_to_show:
                    machine_changes = grouped.get(machine, {})
                    total = sum(len(ch) for hours in machine_changes.values() for ch in hours.values())
                    machine_totals[machine] = total
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

                for machine in machines_to_show:
                    total_machine = machine_totals.get(machine, 0)
                    machine_quality = quality_rollup.get(machine, {}) if quality_rollup else {}
                    ok_machine = len(machine_quality.get('ok', ()))
                    nok_machine = len(machine_quality.get('nok', ()))
                    m_item = QTreeWidgetItem([
                        f"{machine}",
                        str(total_machine),
                        str(ok_machine),
                        str(nok_machine),
                        "",
                    ])
                    self.tree.addTopLevelItem(m_item)
                    m_item.setExpanded(True)
                    m_item.setTextAlignment(1, Qt.AlignCenter)
                    m_item.setTextAlignment(2, Qt.AlignCenter)
                    m_item.setTextAlignment(3, Qt.AlignCenter)
                    m_col = color_for(total_machine, mmin, mmax)

                    m_item.setBackground(0, translucent(m_col, 70))
                    m_item.setBackground(1, m_col)
                    m_item.setBackground(2, translucent(m_col, 50))
                    m_item.setBackground(3, translucent(m_col, 50))

                    mc = color_map.get(machine, QColor('#3498db'))
                    ico = self._make_color_icon(mc)
                    m_item.setIcon(0, ico)

                    try:
                        f = m_item.font(0)
                        f.setBold(True)
                        m_item.setFont(0, f)
                    except Exception:
                        pass


                    machine_changes = grouped.get(machine, {})
                    day_totals = {
                        day: sum(len(ch) for ch in hours.values())
                        for day, hours in machine_changes.items()
                    }
                    if day_totals:
                        dmin = min(day_totals.values())
                        dmax = max(day_totals.values())
                    else:
                        dmin = dmax = 0
                    for day, hours_dict in sorted(machine_changes.items()):
                        total_day = day_totals[day]
                        day_quality = {}
                        if machine_quality:
                            day_quality = machine_quality.get('days', {}).get(day, {})
                        ok_day = len(day_quality.get('ok', ())) if day_quality else 0
                        nok_day = len(day_quality.get('nok', ())) if day_quality else 0
                        d_item = QTreeWidgetItem([
                            f"{day.strftime('%Y-%m-%d')}",
                            str(total_day),
                            str(ok_day),
                            str(nok_day),
                            "",
                        ])
                        m_item.addChild(d_item)
                        d_item.setTextAlignment(1, Qt.AlignCenter)
                        d_item.setTextAlignment(2, Qt.AlignCenter)
                        d_item.setTextAlignment(3, Qt.AlignCenter)
                        d_col = color_for(total_day, dmin, dmax)
                        d_item.setBackground(0, translucent(d_col, 60))
                        d_item.setBackground(1, d_col)
                        d_item.setBackground(2, translucent(d_col, 45))
                        d_item.setBackground(3, translucent(d_col, 45))


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
                            hour_quality = {}
                            if day_quality:
                                hour_quality = day_quality.get('hours', {}).get(hour, {})
                            ok_hour = len(hour_quality.get('ok', ())) if hour_quality else 0
                            nok_hour = len(hour_quality.get('nok', ())) if hour_quality else 0
                            h_item = QTreeWidgetItem([
                                f"{hour_str}",
                                str(cnt),
                                str(ok_hour),
                                str(nok_hour),
                                ", ".join(minutes),
                            ])
                            d_item.addChild(h_item)
                            h_item.setTextAlignment(1, Qt.AlignCenter)
                            h_item.setTextAlignment(2, Qt.AlignCenter)
                            h_item.setTextAlignment(3, Qt.AlignCenter)
                            h_col = color_for(cnt, hmin, hmax)
                            h_item.setBackground(0, translucent(h_col, 50))
                            h_item.setBackground(1, h_col)
                            h_item.setBackground(2, translucent(h_col, 40))
                            h_item.setBackground(3, translucent(h_col, 40))

                try:
                    self.tree.collapseAll()
                except Exception:
                    pass

    def _quality_rollup_by_machine(self) -> dict[str, dict]:
            rows = getattr(self, 'intranet_all_rows', []) or getattr(self, 'intranet_rows', [])
            if not rows:
                return {}

            try:
                start_dt = self.start_datetime.dateTime().toPyDateTime()
                end_dt = self.end_datetime.dateTime().toPyDateTime()
            except Exception:
                start_dt = None
                end_dt = None
            if start_dt and end_dt and end_dt < start_dt:
                start_dt, end_dt = end_dt, start_dt

            known_machines: set[str] = set()
            try:
                known_machines.update(
                    f.machine
                    for f in getattr(self, 'found_files', [])
                    if getattr(f, 'machine', '')
                )
            except Exception:
                pass
            try:
                machine_list = getattr(self, 'machine_list', None)
                if machine_list is not None:
                    known_machines.update(
                        item.text().strip()
                        for item in machine_list.selectedItems()
                        if item
                        and item.text()
                        and not item.text().startswith('(')
                    )
            except Exception:
                pass

            import re as _re

            def _normalize_code(value: object) -> str:
                txt = str(value or '').strip()
                if not txt:
                    return ''
                match = _re.search(r'([MS])\s*-?\s*(\d{1,2})', txt.upper())
                if not match:
                    return ''
                prefix = match.group(1)
                try:
                    num = int(match.group(2))
                except Exception:
                    return ''
                code = f"{prefix}{num}"
                return code if code in TRACKED_MACHINE_CODES else ''

            display_lookup: dict[str, str] = {code: code for code in TRACKED_MACHINE_CODES}
            for machine in known_machines:
                code = _normalize_code(machine)
                if code:
                    display_lookup.setdefault(code, machine)

            feeder_map: dict[int, str] = {}
            try:
                feeder_map.update(getattr(self, '_feeder_map_M', {}))
            except Exception:
                pass
            try:
                feeder_map.update(getattr(self, '_feeder_map_S', {}))
            except Exception:
                pass

            def _display_for_code(code: str) -> str:
                if not code:
                    return ''
                return display_lookup.get(code, code)

            def _podajnik_code(desc: object) -> str:
                text = str(desc or '')
                match = _re.search(r'podajnik\s*drutu\s*(\d+)', text, _re.I)
                if not match:
                    return ''
                try:
                    num = int(match.group(1))
                except Exception:
                    return ''
                mapped = feeder_map.get(num, '')
                return _normalize_code(mapped)

            entries: list[dict] = []
            for rec in rows:
                if not isinstance(rec, dict):
                    continue
                dt = rec.get('data')
                serial = rec.get('serial_no')
                judge = str(rec.get('judge', '') or '').strip().upper()
                if judge not in {'OK', 'NOK'}:
                    continue
                if not dt or not serial:
                    continue
                if start_dt and dt < start_dt:
                    continue
                if end_dt and dt > end_dt:
                    continue
                entries.append(rec)
            if not entries:
                return {}
            try:
                entries.sort(key=lambda r: r.get('data'))
            except Exception:
                pass

            rollup: dict[str, dict] = {}
            for rec in entries:
                dt = rec.get('data')
                if dt is None:
                    continue
                judge = str(rec.get('judge', '') or '').strip().upper()
                serial = str(rec.get('serial_no', '') or '').strip()
                if not serial:
                    continue

                machine_name = ''
                if judge == 'OK':
                    opis = str(rec.get('maszyna_opis', '') or '')
                    if not opis.lower().strip().startswith('podajnik drutu'):
                        continue
                    code = _podajnik_code(opis)
                    if not code:
                        code = _normalize_code(rec.get('machine_actual'))
                    if not code:
                        code = _normalize_code(rec.get('sap_mapped'))
                    if not code:
                        code = _normalize_code(rec.get('maszyna_sap'))
                    if not code:
                        continue
                    machine_name = _display_for_code(code)
                else:
                    code = _normalize_code(rec.get('machine_source'))
                    if not code:
                        code = _normalize_code(rec.get('source_mapped'))
                    if not code:
                        code = _normalize_code(rec.get('source_opis'))
                    if not code:
                        code = _normalize_code(rec.get('machine_actual'))
                    if not code:
                        code = _normalize_code(rec.get('sap_mapped'))
                    if not code:
                        code = _normalize_code(rec.get('maszyna_sap'))
                    if not code:
                        continue
                    machine_name = _display_for_code(code)

                if not machine_name:
                    continue

                day_key = dt.date()
                hour_key = dt.replace(minute=0, second=0, microsecond=0)
                machine_entry = rollup.setdefault(
                    machine_name,
                    {'ok': set(), 'nok': set(), 'days': {}},
                )
                day_entry = machine_entry['days'].setdefault(
                    day_key,
                    {'ok': set(), 'nok': set(), 'hours': {}},
                )
                hour_entry = day_entry['hours'].setdefault(
                    hour_key,
                    {'ok': set(), 'nok': set()},
                )

                if judge == 'NOK':
                    machine_entry['nok'].add(serial)
                    machine_entry['ok'].discard(serial)
                    day_entry['nok'].add(serial)
                    day_entry['ok'].discard(serial)
                    hour_entry['nok'].add(serial)
                    hour_entry['ok'].discard(serial)
                else:
                    if serial not in machine_entry['nok']:
                        machine_entry['ok'].add(serial)
                    if serial not in day_entry['nok']:
                        day_entry['ok'].add(serial)
                    if serial not in hour_entry['nok']:
                        hour_entry['ok'].add(serial)

            return rollup

    def _start_intranet_fetch(self, show_progress: bool = True):

            try:
                prev_worker = getattr(self, 'intra_worker', None)
                if prev_worker is not None and hasattr(prev_worker, 'isRunning') and prev_worker.isRunning():
                    try:
                        if hasattr(prev_worker, 'requestInterruption'):
                            prev_worker.requestInterruption()
                    except Exception:
                        pass
                    try:
                        prev_worker.quit()
                    except Exception:
                        pass
                    try:
                        prev_worker.wait(1000)
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                self.intra_worker = None
            except Exception:
                pass
            try:
                self._set_task_active('intranet', False)
            except Exception:
                pass

            try:
                self.intranet_rows = []
                self.intranet_filtered_rows = []
                self.intranet_all_rows = []
                self.intranet_nok_rows = []
                if hasattr(self, 'intra_table') and self.intra_table is not None:
                    self.intra_table.setRowCount(0)
                if hasattr(self, 'bar_native') and self.bar_native is not None:
                    self.bar_native.set_overlay([], [])
            except Exception:
                pass

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

                if show_progress:
                    try:
                        self.progress.setRange(0, 0)
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
                self._set_task_active('intranet', True)
                try:
                    if self._is_worker_running('a_worker'):
                        self._update_thread_state('Wątki: analiza + intranet')
                    else:
                        self._update_thread_state('Wątki: intranet')
                except Exception:
                    pass
            except Exception as ex:
                self._log(f"[Intranet] Skipping overlay: {ex}")
                try:
                    self._set_task_active('intranet', False)
                except Exception:
                    pass

    def _on_intranet_ready(self, data: dict):
            try:
                series = data.get('series', {}) if isinstance(data, dict) else {}
                rows = data.get('rows', []) if isinstance(data, dict) else []


                keys = sorted(series.keys())
                self.bar_native.set_overlay(keys, [int(series[k]) for k in keys])
                # Keep rows for trend overlays per machine
                self.intranet_nok_rows = rows
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

                by_sn = {}
                for r in all_rows:
                    by_sn.setdefault(r.get('serial_no',''), []).append(r)

                source_cache: dict[str, tuple[str, str]] = {}
                for sn, sn_rows in by_sn.items():
                    source_cache[sn] = _find_source(sn_rows)

                known_machines: set[str] = set()
                try:
                    known_machines.update(
                        f.machine
                        for f in getattr(self, 'found_files', [])
                        if getattr(f, 'machine', '')
                    )
                except Exception:
                    pass
                try:
                    machine_list = getattr(self, 'machine_list', None)
                    if machine_list is not None:
                        known_machines.update(
                            item.text().strip()
                            for item in machine_list.selectedItems()
                            if item
                            and item.text()
                            and not item.text().startswith('(')
                        )
                except Exception:
                    pass

                def _extract_machine_tokens(text: object) -> list[str]:
                    import re as _re

                    tokens: list[str] = []
                    s = str(text or '')
                    if not s:
                        return tokens
                    for match in _re.finditer(r'([MS]\s*-?\s*\d{1,2})', s, _re.I):
                        raw = match.group(1).upper()
                        cleaned = raw.replace(' ', '').replace('-', '')
                        if len(cleaned) >= 2 and cleaned[0] in ('M', 'S') and cleaned[1:].isdigit():
                            try:
                                cleaned = cleaned[0] + str(int(cleaned[1:]))
                            except Exception:
                                pass
                            tokens.append(cleaned)
                    return tokens

                def _normalize_machine_code(value: object) -> str:
                    txt = str(value or '').strip()
                    if not txt:
                        return ''
                    up = txt.upper().replace(' ', '').replace('-', '').replace('_', '')
                    if len(up) >= 2 and up[0] in ('M', 'S') and up[1:].isdigit():
                        try:
                            return up[0] + str(int(up[1:]))
                        except Exception:
                            return up
                    tokens = _extract_machine_tokens(txt)
                    return tokens[0] if tokens else ''

                known_lookup: dict[str, str] = {}
                for name in sorted(known_machines):
                    if not name:
                        continue
                    norm = _normalize_machine_code(name)
                    if norm and norm not in known_lookup:
                        known_lookup[norm] = name
                    upper = name.upper()
                    if upper and upper not in known_lookup:
                        known_lookup[upper] = name

                def _canonical_machine(value: object, allow_unknown: bool = False) -> str:
                    txt = str(value or '').strip()
                    if not txt:
                        return ''
                    norm = _normalize_machine_code(txt)
                    if norm and norm in known_lookup:
                        return known_lookup[norm]
                    upper = txt.upper()
                    if upper in known_lookup:
                        return known_lookup[upper]
                    if allow_unknown or not known_lookup:
                        return norm or (txt if allow_unknown else '')
                    return ''

                sap_to_machine: dict[str, str] = {}
                for rec in all_rows:
                    sap = str(rec.get('maszyna_sap', '') or '').strip()
                    if not sap or sap in sap_to_machine:
                        continue
                    resolved = ''
                    for cand in _extract_machine_tokens(rec.get('maszyna_opis', '')):
                        resolved = _canonical_machine(cand)
                        if resolved:
                            break
                    if not resolved:
                        src_code = source_cache.get(rec.get('serial_no', ''), ('', ''))[1]
                        resolved = _canonical_machine(src_code)
                    if resolved:
                        sap_to_machine[sap] = resolved

                enriched_all: list[dict] = []
                actual_hits = 0
                source_hits = 0
                for r in all_rows:
                    rr = dict(r)
                    src_opis, raw_src_code = source_cache.get(r.get('serial_no', ''), ('', ''))
                    canonical_src = _canonical_machine(raw_src_code)
                    rr['source_opis'] = src_opis
                    rr['source_mapped'] = canonical_src or _canonical_machine(raw_src_code, allow_unknown=True)
                    rr['sap_mapped'] = sap_to_machine.get(str(r.get('maszyna_sap', '') or '').strip(), '')

                    actual_candidates = _extract_machine_tokens(rr.get('maszyna_opis', ''))
                    sap = str(rr.get('maszyna_sap', '') or '').strip()
                    mapped_from_sap = sap_to_machine.get(sap, '')
                    if mapped_from_sap:
                        actual_candidates.append(mapped_from_sap)
                    actual = ''
                    for cand in actual_candidates:
                        resolved = _canonical_machine(cand)
                        if resolved:
                            actual = resolved
                            break
                    if not actual and mapped_from_sap:
                        actual = _canonical_machine(mapped_from_sap, allow_unknown=True)
                    if not actual:
                        desc_upper = str(rr.get('maszyna_opis', '') or '').upper()
                        for machine in known_machines:
                            if machine and machine.upper() in desc_upper:
                                actual = machine
                                break
                    if actual:
                        actual_hits += 1
                    rr['machine_actual'] = actual

                    source_candidates = []
                    if canonical_src:
                        source_candidates.append(canonical_src)
                    if raw_src_code:
                        source_candidates.append(raw_src_code)
                    source_candidates.extend(_extract_machine_tokens(src_opis))
                    if not source_candidates:
                        source_candidates.extend(_extract_machine_tokens(rr.get('maszyna_opis', '')))
                    source = ''
                    for cand in source_candidates:
                        resolved = _canonical_machine(cand)
                        if resolved:
                            source = resolved
                            break
                    if not source and canonical_src:
                        source = _canonical_machine(canonical_src, allow_unknown=True)
                    if not source and raw_src_code:
                        source = _canonical_machine(raw_src_code, allow_unknown=True)
                    if not source:
                        desc_upper = str(src_opis or '').upper()
                        for machine in known_machines:
                            if machine and machine.upper() in desc_upper:
                                source = machine
                                break
                    if source:
                        source_hits += 1
                    rr['machine_source'] = source
                    enriched_all.append(rr)
                self.intranet_all_rows = enriched_all

                enriched: list[dict] = []
                for r in rows:
                    rr = dict(r)
                    src_opis, raw_src_code = source_cache.get(r.get('serial_no', ''), ('', ''))
                    canonical_src = _canonical_machine(raw_src_code)
                    rr['source_opis'] = src_opis
                    rr['source_mapped'] = canonical_src or _canonical_machine(raw_src_code, allow_unknown=True)
                    sap = str(rr.get('maszyna_sap', '') or '').strip()
                    rr['sap_mapped'] = sap_to_machine.get(sap, '')
                    rr['machine_actual'] = _canonical_machine(
                        rr.get('machine_actual') or sap_to_machine.get(sap, ''),
                        allow_unknown=True,
                    )
                    rr['machine_source'] = _canonical_machine(canonical_src or raw_src_code, allow_unknown=True)
                    enriched.append(rr)

                try:
                    self._log(
                        f"[Intranet] Known machines for mapping: {sorted(known_machines) or 'brak'}"
                    )
                    self._log(
                        f"[Intranet] SAP->machine mappings: {len(sap_to_machine)} entries"
                    )
                    self._log(
                        f"[Intranet] machine_actual mapped {actual_hits}/{len(enriched_all)} | machine_source mapped {source_hits}/{len(enriched_all)}"
                    )
                    unresolved = [
                        rec.get('maszyna_sap', '')
                        for rec in enriched_all
                        if rec.get('maszyna_sap') and not rec.get('machine_actual')
                    ][:5]
                    if unresolved:
                        self._log(
                            f"[Intranet] Unresolved machine_actual SAP sample: {unresolved}"
                        )
                except Exception:
                    pass
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
                    nok_machine_hits = sum(1 for rr in dedup if rr.get('machine_source'))
                    nok_missing = [rr.get('serial_no','') for rr in dedup if not rr.get('machine_source')][:5]
                    self._log(
                        f"[Intranet] NOK machine_source mapped {nok_machine_hits}/{len(dedup)} | missing_sample={nok_missing}"
                    )
                except Exception:
                    pass
                self.intranet_nok_rows = dedup
                self.intranet_rows = enriched_all

                # Populate filters and fill table
                try:
                    self._rebuild_intranet_table(self.intranet_rows)
                    self._populate_intranet_filters()
                    self._apply_intranet_filters()
                except Exception:
                    pass
                try:
                    self._populate_pareto_filters()
                except Exception:
                    pass
                try:
                    self._render_summary()
                except Exception:
                    pass
            except Exception as ex:
                self._log(f"[Intranet] Overlay error: {ex}")

            analysis_running = self._is_worker_running('a_worker')
            worker_running = self._is_worker_running('worker')
            self._set_task_active('intranet', False)
            if not analysis_running and not worker_running:
                self.status_label.setText("Gotowy")
                try:
                    self._update_thread_state('Wątki: bezczynne')
                except Exception:
                    pass
                try:
                    self.analysis_run_btn.setEnabled(True)
                except Exception:
                    pass
            else:
                if analysis_running:
                    try:
                        self._update_thread_state('Wątki: analiza')
                    except Exception:
                        pass
            try:
                self.intra_worker = None
            except Exception:
                pass

    def _format_intranet_datetime(self, value) -> str:
            if not value:
                return ""
            try:
                if isinstance(value, datetime):
                    return value.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
            return str(value)

    def _rebuild_intranet_table(self, rows: list[dict]) -> None:
            table = getattr(self, 'intra_table', None)
            if table is None:
                return
            table.setUpdatesEnabled(False)
            table.setRowCount(len(rows))
            for idx, record in enumerate(rows):
                sap = record.get('maszyna_sap', '')
                machine = record.get('maszyna_opis', '')
                source_desc = record.get('source_opis', '')
                source_map = record.get('source_mapped', '')
                dt_txt = record.get('_display_date')
                if not dt_txt:
                    dt_txt = self._format_intranet_datetime(record.get('data'))
                    record['_display_date'] = dt_txt
                if dt_txt:
                    record['_date_lower'] = dt_txt.lower()
                serial = record.get('serial_no', '')
                record['_serial_lower'] = str(serial or '').lower()
                judge = record.get('judge', '')
                table.setItem(idx, 0, QTableWidgetItem(str(sap)))
                table.setItem(idx, 1, QTableWidgetItem(str(machine)))
                table.setItem(idx, 2, QTableWidgetItem(str(source_desc)))
                table.setItem(idx, 3, QTableWidgetItem(str(source_map)))
                table.setItem(idx, 4, QTableWidgetItem(dt_txt))
                table.setItem(idx, 5, QTableWidgetItem(str(serial)))
                table.setItem(idx, 6, QTableWidgetItem(str(judge)))
                try:
                    table.setRowHidden(idx, False)
                except Exception:
                    pass
            table.setUpdatesEnabled(True)
            try:
                table.resizeColumnsToContents()
            except Exception:
                pass

    def _populate_intranet_filters(self):
            rows = getattr(self, 'intranet_rows', [])
            if not isinstance(rows, list):
                rows = []
            machines_sap = [r.get('maszyna_sap', '') for r in rows if r.get('maszyna_sap')]
            machines_desc = [r.get('maszyna_opis', '') for r in rows if r.get('maszyna_opis')]
            sources_desc = [r.get('source_opis', '') for r in rows if r.get('source_opis')]
            sources_map = [r.get('source_mapped', '') for r in rows if r.get('source_mapped')]
            judges = [r.get('judge', '') for r in rows if r.get('judge')]

            if hasattr(self, 'intra_f_machine_code'):
                self._set_combo_items(self.intra_f_machine_code, machines_sap)
            if hasattr(self, 'intra_f_machine_desc'):
                self._set_combo_items(self.intra_f_machine_desc, machines_desc)
            if hasattr(self, 'intra_f_source_desc'):
                self._set_combo_items(self.intra_f_source_desc, sources_desc)
            if hasattr(self, 'intra_f_source_map'):
                self._set_combo_items(self.intra_f_source_map, sources_map)
            if hasattr(self, 'intra_f_judge'):
                self._set_combo_items(self.intra_f_judge, judges)

    def _apply_intranet_filters(self):
            rows = getattr(self, 'intranet_rows', [])
            if not isinstance(rows, list):
                rows = []
            table = getattr(self, 'intra_table', None)
            if table is None:
                self.intranet_filtered_rows = list(rows)
                return
            if table.rowCount() != len(rows):
                self._rebuild_intranet_table(rows)
            machine_code_combo = getattr(self, 'intra_f_machine_code', None)
            machine_desc_combo = getattr(self, 'intra_f_machine_desc', None)
            source_desc_combo = getattr(self, 'intra_f_source_desc', None)
            source_map_combo = getattr(self, 'intra_f_source_map', None)
            judge_combo = getattr(self, 'intra_f_judge', None)
            machine_code = machine_code_combo.currentText() if machine_code_combo is not None and machine_code_combo.count() else "(Wszystkie)"
            machine_desc = machine_desc_combo.currentText() if machine_desc_combo is not None and machine_desc_combo.count() else "(Wszystkie)"
            source_desc = source_desc_combo.currentText() if source_desc_combo is not None and source_desc_combo.count() else "(Wszystkie)"
            source_map = source_map_combo.currentText() if source_map_combo is not None and source_map_combo.count() else "(Wszystkie)"
            judge_val = judge_combo.currentText() if judge_combo is not None and judge_combo.count() else "(Wszystkie)"
            date_edit = getattr(self, 'intra_f_date', None)
            serial_edit = getattr(self, 'intra_f_serial', None)
            date_filter = date_edit.text().strip().lower() if date_edit is not None else ""
            serial_filter = serial_edit.text().strip().lower() if serial_edit is not None else ""
            filtered: list[dict] = []
            table.setUpdatesEnabled(False)
            for idx, record in enumerate(rows):
                mapped = str(record.get('source_mapped', '') or '')
                machine_val = str(record.get('maszyna_sap', '') or '')
                machine_desc_val = str(record.get('maszyna_opis', '') or '')
                source_desc_val = str(record.get('source_opis', '') or '')
                judge = str(record.get('judge', '') or '')
                match = True
                if machine_code and machine_code != "(Wszystkie)" and machine_val != machine_code:
                    match = False
                if match and machine_desc and machine_desc != "(Wszystkie)" and machine_desc_val != machine_desc:
                    match = False
                if match and source_desc and source_desc != "(Wszystkie)" and source_desc_val != source_desc:
                    match = False
                if match and source_map and source_map != "(Wszystkie)" and mapped != source_map:
                    match = False
                if match and judge_val and judge_val != "(Wszystkie)" and judge != judge_val:
                    match = False
                if match and date_filter:
                    date_lower = record.get('_date_lower')
                    if date_lower is None:
                        dt_txt = record.get('_display_date') or self._format_intranet_datetime(record.get('data'))
                        record['_display_date'] = dt_txt
                        date_lower = (dt_txt or '').lower()
                        record['_date_lower'] = date_lower
                    if date_filter not in (date_lower or ''):
                        match = False
                if match and serial_filter:
                    serial_lower = record.get('_serial_lower')
                    if serial_lower is None:
                        serial_lower = str(record.get('serial_no', '') or '').lower()
                        record['_serial_lower'] = serial_lower
                    if serial_filter not in serial_lower:
                        match = False
                if idx < table.rowCount():
                    try:
                        table.setRowHidden(idx, not match)
                    except Exception:
                        pass
                if match:
                    filtered.append(record)
            table.setUpdatesEnabled(True)
            self.intranet_filtered_rows = filtered

    def _on_intranet_error(self, err: str):
            self._log(f"[Intranet] Błąd pobierania: {err}. Pomijam overlay.")
            analysis_running = self._is_worker_running('a_worker')
            worker_running = self._is_worker_running('worker')
            self._set_task_active('intranet', False)
            if not analysis_running and not worker_running:
                self.status_label.setText("Gotowy")
                try:
                    self._update_thread_state('Wątki: bezczynne')
                except Exception:
                    pass
                try:
                    self.analysis_run_btn.setEnabled(True)
                except Exception:
                    pass
            elif analysis_running:
                try:
                    self._update_thread_state('Wątki: analiza')
                except Exception:
                    pass
            try:
                self.intra_worker = None
            except Exception:
                pass

    def _make_color_icon(self, color: QColor, size: int = 14) -> QIcon:
            pm = QPixmap(size, size)
            pm.fill(Qt.transparent)
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

    def _is_worker_running(self, attr: str) -> bool:
            try:
                worker = getattr(self, attr, None)
                return bool(worker is not None and hasattr(worker, 'isRunning') and worker.isRunning())
            except Exception:
                return False

    def _set_task_active(self, task: str, active: bool) -> None:
            try:
                tasks = getattr(self, '_active_tasks', set())
            except Exception:
                tasks = set()
            if active:
                if task not in tasks:
                    tasks.add(task)
            else:
                tasks.discard(task)
            self._active_tasks = tasks
            progress = getattr(self, 'progress', None)
            if progress is None:
                return
            if tasks:
                try:
                    progress.setRange(0, 0)
                except Exception:
                    pass
                try:
                    progress.setVisible(True)
                except Exception:
                    pass
            else:
                try:
                    progress.setRange(0, 1)
                    progress.setValue(0)
                except Exception:
                    pass
                try:
                    progress.setVisible(False)
                    progress.setFormat("Przetwarzanie...")
                except Exception:
                    pass

    def _reset_results_state(self, *, clear_found_files: bool = False) -> None:
            progress = getattr(self, 'progress', None)
            if progress is not None:
                try:
                    progress.setRange(0, 1)
                    progress.setValue(0)
                    progress.setVisible(False)
                    progress.setFormat("Przetwarzanie...")
                except Exception:
                    pass
            status = getattr(self, 'status_label', None)
            if status is not None:
                try:
                    status.setText("Gotowe")
                except Exception:
                    pass
            try:
                self._active_tasks = set()
            except Exception:
                pass
            try:
                if hasattr(self, 'thread_state') and self.thread_state is not None:
                    self.thread_state.setText('Wątki: bezczynne')
            except Exception:
                pass
            if clear_found_files:
                try:
                    self.found_files = []
                except Exception:
                    pass
                try:
                    if hasattr(self, 'analysis_run_btn') and self.analysis_run_btn is not None:
                        self.analysis_run_btn.setEnabled(False)
                except Exception:
                    pass
            try:
                self.analysis_records = []
            except Exception:
                pass
            try:
                self.analysis_filtered_rows = []
            except Exception:
                pass
            analysis_table = getattr(self, 'analysis_table', None)
            if analysis_table is not None:
                try:
                    analysis_table.setRowCount(0)
                except Exception:
                    pass
            try:
                self.hp_grip_snapshots = []
                self.hp_grip_events = []
                self.hp_grip_filtered = []
                self._hp_grip_value_keys = []
                self._hp_grip_filter_hierarchy = {}
                self.nest_snapshots = []
                self.nest_events = []
                self.nest_filtered = []
                self._nest_value_keys = []
                self._nest_filter_hierarchy = {}
                self.hairpin_snapshots = []
                self.hairpin_events = []
                self.hairpin_filtered = []
                self._hairpin_value_keys = []
                self._hairpin_filter_hierarchy = {}
                self._hairpin_display_to_source = {}
                self._configure_hp_grip_table()
                self._configure_nest_table()
                self._configure_stripping_table()
                self._populate_hp_grip_filters()
                self._populate_nest_filters()
                self._populate_stripping_filters()
                self._param_card_index_lookup = {}
                self._param_card_grip_lookup = {}
                self._param_card_nest_lookup = {}
                self._param_card_hairpin_lookup = {}
            except Exception:
                pass
            try:
                self.pareto_chart.set_data({})
                if hasattr(self, 'pareto_summary_label'):
                    self.pareto_summary_label.setText("Brak danych")
                self._populate_pareto_filters()
            except Exception:
                pass
            try:
                self.param_snapshots = []
            except Exception:
                pass
            try:
                self.index_snapshots = []
            except Exception:
                pass
            try:
                self.index_events = []
                self.index_filtered_rows = []
            except Exception:
                pass
            index_table = getattr(self, 'index_table', None)
            if index_table is not None:
                try:
                    index_table.setRowCount(0)
                except Exception:
                    pass
            try:
                self.program_events = []
                self.program_filtered_rows = []
            except Exception:
                pass
            program_table = getattr(self, 'program_table', None)
            if program_table is not None:
                try:
                    program_table.setRowCount(0)
                except Exception:
                    pass
            top_tree = getattr(self, 'top_issues_tree', None)
            if top_tree is not None:
                try:
                    top_tree.clear()
                except Exception:
                    pass
            change_tree = getattr(self, 'change_tree', None)
            if change_tree is not None:
                try:
                    change_tree.clear()
                except Exception:
                    pass
            try:
                if hasattr(self, 'stat_changes') and self.stat_changes is not None:
                    self.stat_changes.setText('Liczba zmian: 0')
            except Exception:
                pass
            try:
                if hasattr(self, 'stat_machines') and self.stat_machines is not None:
                    self.stat_machines.setText('Liczba maszyn: 0')
            except Exception:
                pass
            pie_view = getattr(self, 'pie_view', None)
            if pie_view and clear_found_files:
                try:
                    pie_view.setHtml("<html><head><meta charset='utf-8'></head><body style='font-family:Segoe UI;color:#7f8c8d;margin:12px;'>Brak danych</body></html>")
                except Exception:
                    pass
            line_view = getattr(self, 'line_view', None)
            if line_view and clear_found_files:
                try:
                    line_view.setHtml("<html><head><meta charset='utf-8'></head><body style='font-family:Segoe UI;color:#7f8c8d;margin:12px;'>Brak danych</body></html>")
                except Exception:
                    pass
            pie_label = getattr(self, 'pie_label', None)
            if pie_label is not None and clear_found_files:
                try:
                    pie_label.setText('Brak danych')
                    pie_label.setPixmap(QPixmap())
                except Exception:
                    pass
            line_label = getattr(self, 'line_label', None)
            if line_label is not None and clear_found_files:
                try:
                    line_label.setText('Brak danych')
                    line_label.setPixmap(QPixmap())
                except Exception:
                    pass
            pie_native = getattr(self, 'pie_native', None)
            if pie_native is not None and clear_found_files:
                try:
                    pie_native.set_data({})
                except Exception:
                    pass
            line_native = getattr(self, 'line_native', None)
            if line_native is not None and clear_found_files:
                try:
                    line_native.set_data([], {})
                except Exception:
                    pass
            tree = getattr(self, 'tree', None)
            if tree is not None and clear_found_files:
                try:
                    tree.clear()
                except Exception:
                    pass
            summary_table = getattr(self, 'table', None)
            if summary_table is not None:
                try:
                    summary_table.setRowCount(0)
                except Exception:
                    pass
            try:
                self.intranet_rows = []
                self.intranet_filtered_rows = []
                self.intranet_all_rows = []
                self.intranet_nok_rows = []
                self._populate_pareto_filters()
            except Exception:
                pass
            intra_table = getattr(self, 'intra_table', None)
            if intra_table is not None:
                try:
                    intra_table.setRowCount(0)
                except Exception:
                    pass
            bar_native = getattr(self, 'bar_native', None)
            if bar_native is not None:
                try:
                    bar_native.set_overlay([], [])
                except Exception:
                    pass
            try:
                if hasattr(self, 'logs_tab') and self.logs_tab is not None:
                    self.logs_tab.clear()
            except Exception:
                pass
            for line_edit_name in ('intra_f_date', 'intra_f_serial'):
                line_edit = getattr(self, line_edit_name, None)
                if line_edit is not None:
                    try:
                        line_edit.blockSignals(True)
                        line_edit.clear()
                        line_edit.blockSignals(False)
                    except Exception:
                        pass
            for combo_name in (
                'intra_f_machine_code',
                'intra_f_machine_desc',
                'intra_f_source_desc',
                'intra_f_source_map',
                'intra_f_judge',
                'f_machine',
                'f_pin',
                'f_step',
                'f_param',
                'param_line_machine',
                'param_line_pin',
                'param_line_step',
                'index_line_machine',
                'index_line_pin',
                'index_line_step',
                'pg_f_machine',
                'pg_f_old',
                'pg_f_new',
                't_f_machine',
                'idx_f_machine',
                'idx_f_table',
                'idx_f_step',
                'idx_f_param',
            ):
                combo = getattr(self, combo_name, None)
                if combo is not None:
                    try:
                        combo.blockSignals(True)
                        combo.clear()
                        combo.blockSignals(False)
                    except Exception:
                        pass
            self._param_line_hierarchy = {}
            self._index_line_hierarchy = {}
            try:
                self._clear_param_line_charts()
            except Exception:
                pass
            try:
                self._clear_index_line_charts()
            except Exception:
                pass
            self.param_card_groups = {}
            self.param_card_selection = None
            self.current_param_card_rows = []
            card_info = getattr(self, 'param_card_info', None)
            if card_info is not None:
                try:
                    card_info.setText('Brak danych')
                except Exception:
                    pass
            card_table = getattr(self, 'param_card_table', None)
            if card_table is not None:
                try:
                    card_table.setRowCount(0)
                except Exception:
                    pass
            export_btn = getattr(self, 'param_card_export_btn', None)
            if export_btn is not None:
                try:
                    export_btn.setEnabled(False)
                except Exception:
                    pass
            dt_combo = getattr(self, 'param_card_datetime', None)
            machine_combo = getattr(self, 'param_card_machine', None)
            if dt_combo is not None:
                try:
                    dt_combo.blockSignals(True)
                    dt_combo.clear()
                    dt_combo.addItem('(Brak danych)')
                    dt_combo.setEnabled(False)
                    dt_combo.blockSignals(False)
                except Exception:
                    pass
            if machine_combo is not None:
                try:
                    machine_combo.blockSignals(True)
                    machine_combo.clear()
                    machine_combo.addItem('(Brak danych)')
                    machine_combo.setEnabled(False)
                    machine_combo.blockSignals(False)
                except Exception:
                    pass

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
                self._set_task_active('analysis', False)
                self._set_task_active('intranet', False)
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
            analysis_files = self._prepare_analysis_files()
            if not analysis_files:
                QMessageBox.information(self, "Brak danych", "Brak plików do analizy.")
                return
            self._reset_results_state(clear_found_files=False)
            self.progress.setRange(0, 0)
            self.progress.setVisible(True)
            self.status_label.setText("Analiza zmian...")
            self.analysis_run_btn.setEnabled(False)
            self._set_task_active('analysis', True)
            self.analysis_table.setRowCount(0)
            self.analysis_records = []
            try:
                if hasattr(self, 'index_table') and self.index_table is not None:
                    self.index_table.setRowCount(0)
            except Exception:
                pass
            self.index_events = []
            self.index_filtered_rows = []
            try:
                self._update_thread_state('Wątki: analiza')
            except Exception:
                pass

            try:
                self.param_snapshots = []
                self.index_snapshots = []
                self.hp_grip_snapshots = []
                self.nest_snapshots = []
                self.hairpin_snapshots = []
                self.param_card_groups = {}
                self.current_param_card_rows = []
                self.param_card_selection = None
                self._populate_param_line_filters()
                self._populate_index_line_filters()
                self._clear_param_line_charts()
                self._clear_index_line_charts()
                self._populate_param_card_filters()
                self._hp_grip_value_keys = []
                self._nest_value_keys = []
                self._hairpin_value_keys = []
                self._hp_grip_filter_hierarchy = {}
                self._nest_filter_hierarchy = {}
                self._hairpin_filter_hierarchy = {}
                self._hairpin_display_to_source = {}
                self.hp_grip_filtered = []
                self.nest_filtered = []
                self.hairpin_filtered = []
                self._configure_hp_grip_table()
                self._configure_nest_table()
                self._configure_stripping_table()
                self._populate_hp_grip_filters()
                self._populate_nest_filters()
                self._populate_stripping_filters()
            except Exception:
                pass


            try:
                self.analysis_started_at = datetime.now()
                total_files = len(analysis_files)
                self._log(
                    f"[Analysis] START {self.analysis_started_at.strftime('%Y-%m-%d %H:%M:%S')} | files={total_files}"
                )
            except Exception:
                pass
            try:
                pref_workers = self.settings.value("analysis_workers", 0, type=int)
            except Exception:
                pref_workers = 0
            self.a_worker = AnalyzeWorker(
                analysis_files,
                max_workers=(pref_workers if pref_workers and pref_workers > 0 else None),
            )
            self.a_worker.progress.connect(self._on_progress)
            self.a_worker.finished.connect(self._on_analysis_finished)
            self.a_worker.error.connect(self._on_analysis_error)
            try:
                self._log(f"[Analysis] workers={self.a_worker.max_workers}")
            except Exception:
                pass
            self.a_worker.start()
            try:
                self._start_intranet_fetch(show_progress=False)
            except Exception:
                pass

    def _on_analysis_error(self, err: str):
            self._set_task_active('analysis', False)
            intra_running = self._is_worker_running('intra_worker')
            if intra_running:
                self.status_label.setText("Błąd analizy (trwa pobieranie Intranetu)")
                try:
                    self._update_thread_state('Wątki: intranet')
                except Exception:
                    pass
            else:
                self.status_label.setText("Błąd analizy")
                try:
                    self._update_thread_state('Wątki: bezczynne')
                except Exception:
                    pass
            try:
                self.analysis_run_btn.setEnabled(not intra_running)
            except Exception:
                pass
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
            try:
                self.a_worker = None
            except Exception:
                pass

    def _on_analysis_finished(self, records):
            self._set_task_active('analysis', False)
            intra_running = self._is_worker_running('intra_worker')
            if intra_running:
                self.status_label.setText("Analiza zakończona (trwa pobieranie Intranetu)")
                try:
                    self._update_thread_state('Wątki: intranet')
                except Exception:
                    pass
            else:
                self.status_label.setText("Analiza zakończona")
                try:
                    self._update_thread_state('Wątki: bezczynne')
                except Exception:
                    pass
            try:
                self.analysis_run_btn.setEnabled(not intra_running)
            except Exception:
                pass
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
            if isinstance(records, dict):
                param_records = list(records.get('params') or [])
                index_records = list(records.get('index') or [])
                hp_grip_records = list(records.get('hp_grip') or [])
                nest_records = list(records.get('nest') or [])
                hairpin_records = list(records.get('hairpin') or [])
            else:
                param_records = list(records or [])
                index_records = []
                hp_grip_records = []
                nest_records = []
                hairpin_records = []

            snaps: list[ParamSnapshot] = sorted(param_records, key=lambda r: r.dt)
            self.param_snapshots = snaps
            self.param_card_selection = None
            self.current_param_card_rows = []
            try:
                self._populate_param_card_filters()
            except Exception:
                pass
            try:
                grip_snaps = sorted(hp_grip_records, key=lambda r: r.dt)
                self.hp_grip_snapshots = grip_snaps
                self.hp_grip_events = self._build_struct_change_events(grip_snaps)
                self._refresh_hp_grip_columns()
                self._populate_hp_grip_filters()
            except Exception:
                pass
            try:
                nest_snaps = sorted(nest_records, key=lambda r: r.dt)
                self.nest_snapshots = nest_snaps
                self.nest_events = self._build_struct_change_events(nest_snaps)
                self._refresh_nest_columns()
                self._populate_nest_filters()
            except Exception:
                pass
            try:
                hairpin_snaps = sorted(hairpin_records, key=lambda r: r.dt)
                self.hairpin_snapshots = hairpin_snaps
                self.hairpin_events = self._build_struct_change_events(hairpin_snaps)
                self._refresh_stripping_columns()
                self._populate_stripping_filters()
            except Exception:
                pass
            events = []
            prog_events = []
            seen_prog = set()
            last_state: dict[tuple[str, str, str, int], ParamSnapshot] = {}
            last_prog: dict[tuple[str, str, str, int], str] = {}
            baseline_done: set[tuple[str, str, str, int]] = set()
            try:
                threshold_pct = float(self.settings.value("large_change_threshold_pct", 10, type=int))
            except Exception:
                threshold_pct = 10.0
            for s in snaps:
                key = (s.machine, s.table, s.pin, s.step)
                if key not in baseline_done:

                    baseline_done.add(key)
                    last_state[key] = s
                    last_prog[key] = s.program
                    continue

                prev = last_state.get(key)
                if prev is None:
                    last_state[key] = s
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
                    last_state[key] = s
                    last_prog[key] = s.program
                    continue

                changed_cols = {}
                large_cols = {}
                for name in PARAM_DISPLAY_ORDER:
                    if name == 'Step Speed':
                        prev_speed = prev.values.get('Step Speed')
                        curr_speed = s.values.get('Step Speed')
                        if prev_speed is None and curr_speed is None:
                            changed = False
                        elif prev_speed is None or curr_speed is None:
                            changed = True
                        else:
                            try:
                                changed = abs(curr_speed - prev_speed) > 1e-12
                            except Exception:
                                changed = curr_speed != prev_speed

                        changed_cols[name] = ""
                        large_cols[name] = False
                        if not changed:
                            continue

                        prev_txt = self._format_override_value(prev_speed)
                        curr_txt = self._format_override_value(curr_speed)
                        if prev_txt == curr_txt:
                            continue

                        changed_cols[name] = f"{prev_txt} -> {curr_txt}"
                        if (
                            prev_speed is not None
                            and curr_speed is not None
                            and abs(prev_speed) > 1e-12
                        ):
                            pct = abs((curr_speed - prev_speed) / prev_speed) * 100.0
                            large_cols[name] = (pct >= threshold_pct)
                        continue

                    if name not in PARAM_NAMES:
                        changed_cols[name] = ""
                        large_cols[name] = False
                        continue

                    prev_include = bool(prev.included.get(name, False))
                    curr_include = bool(s.included.get(name, False))
                    if not prev_include and not curr_include:
                        changed_cols[name] = ""
                        large_cols[name] = False
                        continue

                    prev_mode = prev.modes.get(name, 'ABS')
                    curr_mode = s.modes.get(name, 'ABS')
                    prev_value = float(prev.values.get(name, 0.0) or 0.0)
                    curr_value = float(s.values.get(name, 0.0) or 0.0)

                    value_changed = abs(curr_value - prev_value) > 1e-12
                    mode_changed = (curr_mode or '').upper() != (prev_mode or '').upper()
                    include_changed = curr_include != prev_include

                    changed_cols[name] = ""
                    large_cols[name] = False
                    if not (value_changed or mode_changed or include_changed):
                        continue

                    prev_txt = self._format_index_value(prev_include, prev_value, prev_mode)
                    curr_txt = self._format_index_value(curr_include, curr_value, curr_mode)
                    if prev_txt == curr_txt:
                        continue

                    changed_cols[name] = f"{prev_txt} -> {curr_txt}"
                    if prev_include and curr_include and abs(prev_value) > 1e-12:
                        pct = abs((curr_value - prev_value) / prev_value) * 100.0
                        large_cols[name] = (pct >= threshold_pct)
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

                last_state[key] = s
                last_prog[key] = s.program

            events.sort(key=lambda x: (x['dt'], x['machine'], x.get('pin', ''), x['step']))
            events = self._deduplicate_param_events(events)
            prog_events.sort(key=lambda x: (x['dt'], x['machine']))
            self.analysis_events = events
            self.program_events = prog_events
            self._populate_analysis_filters()
            self._apply_analysis_filters()
            self._populate_program_filters()
            self._apply_program_filters()

            index_snaps: list[IndexSnapshot] = sorted(index_records, key=lambda r: r.dt)
            self.index_snapshots = index_snaps
            index_events = self._build_index_events(index_snaps, threshold_pct)
            self.index_events = index_events
            self._populate_index_filters()
            self._apply_index_filters()
            try:
                self._populate_param_line_filters()
                self._clear_param_line_charts()
            except Exception:
                pass
            try:
                self.a_worker = None
            except Exception:
                pass
            try:
                self._populate_index_line_filters()
                self._clear_index_line_charts()
            except Exception:
                pass
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

            events = getattr(self, 'analysis_events', [])
            hierarchy: dict[str, dict[str, dict[str, set[str]]]] = {}
            for event in events:
                if event.get('type') != 'change':
                    continue
                machine = str(event.get('machine', '') or '').strip()
                pin = str(event.get('pin', '') or '').strip()
                step_val = event.get('step')
                step = str(step_val) if step_val is not None else ''
                cols = event.get('cols') or {}
                params = {name for name, text in cols.items() if text}
                machine_entry = hierarchy.setdefault(machine, {})
                pin_entry = machine_entry.setdefault(pin, {})
                step_entry = pin_entry.setdefault(step, set())
                if params:
                    step_entry.update(params)
            self._analysis_filter_hierarchy = hierarchy

            machines = [key for key in hierarchy.keys() if key]
            self._set_combo_items(self.f_machine, machines)
            self._update_analysis_pin_options()

    def _update_analysis_pin_options(self) -> None:
            hierarchy = getattr(self, '_analysis_filter_hierarchy', {}) or {}
            machine = self.f_machine.currentText().strip() if self.f_machine.count() else ""
            pins: set[str] = set()
            if machine and machine != "(Wszystkie)":
                pins.update(key for key in hierarchy.get(machine, {}).keys() if key)
            else:
                for machine_pins in hierarchy.values():
                    pins.update(key for key in machine_pins.keys() if key)
            self._set_combo_items(self.f_pin, pins)
            self._update_analysis_step_options()

    def _update_analysis_step_options(self) -> None:
            hierarchy = getattr(self, '_analysis_filter_hierarchy', {}) or {}
            machine = self.f_machine.currentText().strip() if self.f_machine.count() else ""
            pin = self.f_pin.currentText().strip() if self.f_pin.count() else ""
            steps: set[str] = set()
            if machine and machine != "(Wszystkie)":
                machine_pins = hierarchy.get(machine, {})
                if pin and pin != "(Wszystkie)":
                    steps.update(step for step in machine_pins.get(pin, {}).keys() if step)
                else:
                    for pin_steps in machine_pins.values():
                        steps.update(step for step in pin_steps.keys() if step)
            else:
                if pin and pin != "(Wszystkie)":
                    for machine_pins in hierarchy.values():
                        steps.update(step for step in machine_pins.get(pin, {}).keys() if step)
                else:
                    for machine_pins in hierarchy.values():
                        for pin_steps in machine_pins.values():
                            steps.update(step for step in pin_steps.keys() if step)
            self._set_combo_items(self.f_step, steps)
            self._update_analysis_param_options()

    def _update_analysis_param_options(self) -> None:
            hierarchy = getattr(self, '_analysis_filter_hierarchy', {}) or {}
            machine = self.f_machine.currentText().strip() if self.f_machine.count() else ""
            pin = self.f_pin.currentText().strip() if self.f_pin.count() else ""
            step = self.f_step.currentText().strip() if self.f_step.count() else ""
            params: set[str] = set()

            def collect(machine_key: str, machine_pins: dict[str, dict[str, set[str]]]) -> None:
                for pin_key, pin_steps in machine_pins.items():
                    if pin and pin != "(Wszystkie)" and pin_key != pin:
                        continue
                    for step_key, param_set in pin_steps.items():
                        if step and step != "(Wszystkie)" and step_key != step:
                            continue
                        params.update(param_set)

            if machine and machine != "(Wszystkie)":
                collect(machine, hierarchy.get(machine, {}))
            else:
                for machine_key, machine_pins in hierarchy.items():
                    collect(machine_key, machine_pins)

            ordered = [name for name in PARAM_DISPLAY_ORDER if name in params]
            self._set_combo_items(self.f_param, ordered, sort_items=False)

    def _on_analysis_machine_changed(self, index: int) -> None:  # noqa: ARG002
            self._update_analysis_pin_options()
            self._apply_analysis_filters()

    def _on_analysis_pin_changed(self, index: int) -> None:  # noqa: ARG002
            self._update_analysis_step_options()
            self._apply_analysis_filters()

    def _on_analysis_step_changed(self, index: int) -> None:  # noqa: ARG002
            self._update_analysis_param_options()
            self._apply_analysis_filters()

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
                path_text = e.get('path', '') or ''
                path_item = QTableWidgetItem(path_text)
                if path_text:
                    path_item.setToolTip(path_text)
                self.analysis_table.setItem(i, path_col_idx, path_item)
            self.analysis_table.resizeColumnsToContents()
            self.analysis_filtered_rows = rows

    def _set_combo_items(self, combo: QComboBox, items: Iterable[str], *, sort_items: bool = True) -> None:
            texts: list[str] = []
            seen: set[str] = set()
            for item in items:
                text = str(item)
                if not text:
                    continue
                if text in seen:
                    continue
                texts.append(text)
                seen.add(text)
            if sort_items:
                texts.sort(key=_natural_sort_key)
            current = combo.currentText() if combo.count() else ""
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("(Wszystkie)")
            for text in texts:
                combo.addItem(text)
            if current and combo.findText(current) >= 0:
                combo.setCurrentIndex(combo.findText(current))
            else:
                combo.setCurrentIndex(0)
            combo.blockSignals(False)

    def _populate_param_line_filters(self):
            if not hasattr(self, 'param_line_machine'):
                return
            snaps = getattr(self, 'param_snapshots', [])
            hierarchy: dict[str, dict[str, set[str]]] = {}
            for snap in snaps:
                machine = (snap.machine or '').strip()
                if not machine:
                    continue
                machine_entry = hierarchy.setdefault(machine, {})
                pin = (snap.pin or '').strip()
                if pin:
                    step_set = machine_entry.setdefault(pin, set())
                else:
                    step_set = machine_entry.setdefault('', set())
                if snap.step is not None:
                    step_set.add(str(snap.step))
            self._param_line_hierarchy = hierarchy
            self._set_combo_items(self.param_line_machine, hierarchy.keys())
            self._update_param_line_pin_options()

    def _update_param_line_pin_options(self) -> None:
            if not hasattr(self, 'param_line_machine'):
                return
            hierarchy = getattr(self, '_param_line_hierarchy', {}) or {}
            machine = self.param_line_machine.currentText().strip() if self.param_line_machine.count() else ""
            pins: set[str] = set()
            if machine and machine != "(Wszystkie)":
                pins.update(key for key in hierarchy.get(machine, {}).keys() if key)
            else:
                for machine_pins in hierarchy.values():
                    pins.update(key for key in machine_pins.keys() if key)
            self._set_combo_items(self.param_line_pin, pins)
            self._update_param_line_step_options()

    def _update_param_line_step_options(self) -> None:
            if not hasattr(self, 'param_line_step'):
                return
            hierarchy = getattr(self, '_param_line_hierarchy', {}) or {}
            machine = self.param_line_machine.currentText().strip() if self.param_line_machine.count() else ""
            pin = self.param_line_pin.currentText().strip() if self.param_line_pin.count() else ""
            steps: set[str] = set()
            if machine and machine != "(Wszystkie)":
                machine_pins = hierarchy.get(machine, {})
                if pin and pin != "(Wszystkie)":
                    steps.update(machine_pins.get(pin, set()))
                else:
                    for values in machine_pins.values():
                        steps.update(values)
            else:
                if pin and pin != "(Wszystkie)":
                    for machine_pins in hierarchy.values():
                        steps.update(machine_pins.get(pin, set()))
                else:
                    for machine_pins in hierarchy.values():
                        for values in machine_pins.values():
                            steps.update(values)
            self._set_combo_items(self.param_line_step, steps)

    def _on_param_line_machine_changed(self, index: int) -> None:  # noqa: ARG002
            self._update_param_line_pin_options()

    def _on_param_line_pin_changed(self, index: int) -> None:  # noqa: ARG002
            self._update_param_line_step_options()

    def _apply_param_line_filters(self):
            charts = getattr(self, 'param_line_charts', {})
            if not charts:
                return
            snaps = getattr(self, 'param_snapshots', [])
            machine = self.param_line_machine.currentText().strip() if self.param_line_machine.count() else "(Wszystkie)"
            pin = self.param_line_pin.currentText().strip() if self.param_line_pin.count() else "(Wszystkie)"
            step = self.param_line_step.currentText().strip() if self.param_line_step.count() else "(Wszystkie)"

            for name, chart in charts.items():
                points: list[tuple[datetime, float]] = []
                for snap in snaps:
                    if machine and machine != "(Wszystkie)" and snap.machine != machine:
                        continue
                    if pin and pin != "(Wszystkie)" and str(snap.pin or "") != pin:
                        continue
                    if step and step != "(Wszystkie)" and str(snap.step) != step:
                        continue
                    if name != STEP_SPEED_LABEL and not snap.included.get(name, False):
                        continue
                    value = snap.values.get(name)
                    if value is None:
                        continue
                    try:
                        val = float(value)
                    except Exception:
                        continue
                    if math.isnan(val) or math.isinf(val):
                        continue
                    points.append((snap.dt, val))
                chart.set_series(name, points, self._param_line_colors.get(name))

    def _clear_param_line_charts(self) -> None:
            charts = getattr(self, 'param_line_charts', {})
            if not charts:
                return
            for name, chart in charts.items():
                chart.set_series(name, [], self._param_line_colors.get(name))

    def _refresh_hp_grip_columns(self) -> None:
            keys: set[str] = set()
            events = getattr(self, 'hp_grip_events', [])
            if events:
                for event in events:
                    for key in event.get('values', {}).keys():
                        text = str(key or '').strip()
                        if text:
                            keys.add(text)
            else:
                for snap in getattr(self, 'hp_grip_snapshots', []):
                    if not isinstance(snap, GripSnapshot):
                        continue
                    for key in getattr(snap, 'values', {}).keys():
                        text = str(key or '').strip()
                        if text:
                            keys.add(text)
            ordered: list[str] = []
            for key in GRIP_PARAM_ORDER:
                if key in keys:
                    ordered.append(key)
            remaining = sorted(keys.difference(ordered), key=_natural_sort_key)
            ordered.extend(remaining)
            self._hp_grip_value_keys = ordered
            self._configure_hp_grip_table()

    def _refresh_nest_columns(self) -> None:
            keys: set[str] = set()
            events = getattr(self, 'nest_events', [])
            if events:
                for event in events:
                    for key in event.get('values', {}).keys():
                        text = str(key or '').strip()
                        if text:
                            keys.add(text)
            else:
                for snap in getattr(self, 'nest_snapshots', []):
                    if not isinstance(snap, NestSnapshot):
                        continue
                    for key in getattr(snap, 'values', {}).keys():
                        text = str(key or '').strip()
                        if text:
                            keys.add(text)
            ordered: list[str] = []
            for key in NEST_PARAM_ORDER:
                if key in keys:
                    ordered.append(key)
            remaining = sorted(keys.difference(ordered), key=_natural_sort_key)
            ordered.extend(remaining)
            self._nest_value_keys = ordered
            self._configure_nest_table()

    def _refresh_stripping_columns(self) -> None:
            keys: set[str] = set()
            events = getattr(self, 'hairpin_events', [])
            if events:
                for event in events:
                    for key in event.get('values', {}).keys():
                        text = str(key or '').strip()
                        if text:
                            keys.add(text)
            else:
                for snap in getattr(self, 'hairpin_snapshots', []):
                    if not isinstance(snap, HairpinSnapshot):
                        continue
                    for key in getattr(snap, 'values', {}).keys():
                        text = str(key or '').strip()
                        if text:
                            keys.add(text)
            normalized: dict[str, str] = {}
            for source in keys:
                if source in HAIRPIN_PARAM_EXCLUDE:
                    continue
                display = HAIRPIN_PARAM_LABELS.get(source, source)
                normalized.setdefault(display, source)
            display_map: dict[str, str] = {}
            ordered_display: list[str] = []
            for display in HAIRPIN_PARAM_ORDER:
                if display in normalized:
                    display_map[display] = normalized.pop(display)
                    ordered_display.append(display)
            for display in sorted(normalized.keys(), key=_natural_sort_key):
                source = normalized[display]
                unique = display
                suffix = 2
                while unique in display_map:
                    unique = f"{display} ({suffix})"
                    suffix += 1
                display_map[unique] = source
                ordered_display.append(unique)
            self._hairpin_value_keys = ordered_display
            self._hairpin_display_to_source = display_map
            self._configure_stripping_table()

    def _configure_hp_grip_table(self) -> None:
            table = getattr(self, 'hp_grip_table', None)
            if table is None:
                return
            base_headers = ["Data", "Czas", "Maszyna", "Program", "Pin"]
            columns = base_headers + list(getattr(self, '_hp_grip_value_keys', [])) + ["Ścieżka"]
            table.setColumnCount(len(columns))
            table.setHorizontalHeaderLabels(columns)
            try:
                table.setColumnHidden(len(columns) - 1, True)
            except Exception:
                pass
            try:
                header = table.horizontalHeader()
                for idx in range(len(columns)):
                    header.setSectionResizeMode(idx, QHeaderView.ResizeToContents)
            except Exception:
                pass

    def _configure_nest_table(self) -> None:
            table = getattr(self, 'nest_table', None)
            if table is None:
                return
            base_headers = ["Data", "Czas", "Maszyna", "Program", "Pin"]
            columns = base_headers + list(getattr(self, '_nest_value_keys', [])) + ["Ścieżka"]
            table.setColumnCount(len(columns))
            table.setHorizontalHeaderLabels(columns)
            try:
                table.setColumnHidden(len(columns) - 1, True)
            except Exception:
                pass
            try:
                header = table.horizontalHeader()
                for idx in range(len(columns)):
                    header.setSectionResizeMode(idx, QHeaderView.ResizeToContents)
            except Exception:
                pass

    def _configure_stripping_table(self) -> None:
            table = getattr(self, 'stripping_table', None)
            if table is None:
                return
            base_headers = ["Data", "Czas", "Maszyna", "Program", "Pin"]
            columns = base_headers + list(getattr(self, '_hairpin_value_keys', [])) + ["Ścieżka"]
            table.setColumnCount(len(columns))
            table.setHorizontalHeaderLabels(columns)
            try:
                table.setColumnHidden(len(columns) - 1, True)
            except Exception:
                pass
            try:
                header = table.horizontalHeader()
                for idx in range(len(columns)):
                    header.setSectionResizeMode(idx, QHeaderView.ResizeToContents)
            except Exception:
                pass

    def _populate_hp_grip_filters(self) -> None:
            if not hasattr(self, 'hp_grip_machine'):
                return
            events = getattr(self, 'hp_grip_events', [])
            hierarchy: dict[str, set[str]] = {}
            for event in events:
                machine = str(event.get('machine', '') or '').strip()
                pin = str(event.get('pin', '') or '').strip()
                if not machine:
                    continue
                machine_set = hierarchy.setdefault(machine, set())
                if pin:
                    machine_set.add(pin)
            self._hp_grip_filter_hierarchy = hierarchy
            machines = [key for key in hierarchy.keys() if key]
            self._set_combo_items(self.hp_grip_machine, machines)
            self._update_hp_grip_pin_options()
            self._apply_hp_grip_filters()

    def _update_hp_grip_pin_options(self) -> None:
            hierarchy = getattr(self, '_hp_grip_filter_hierarchy', {}) or {}
            machine = self.hp_grip_machine.currentText().strip() if self.hp_grip_machine.count() else ""
            pins: set[str] = set()
            if machine and machine != "(Wszystkie)":
                pins.update(hierarchy.get(machine, set()))
            else:
                for values in hierarchy.values():
                    pins.update(values)
            self._set_combo_items(self.hp_grip_pin, pins)

    def _on_hp_grip_machine_changed(self, index: int) -> None:  # noqa: ARG002
            self._update_hp_grip_pin_options()
            self._apply_hp_grip_filters()

    def _apply_hp_grip_filters(self) -> None:
            table = getattr(self, 'hp_grip_table', None)
            if table is None:
                return
            events = getattr(self, 'hp_grip_events', [])
            machine = self.hp_grip_machine.currentText() if self.hp_grip_machine.count() else "(Wszystkie)"
            pin = self.hp_grip_pin.currentText() if self.hp_grip_pin.count() else "(Wszystkie)"
            rows: list[dict] = []
            for event in events:
                if machine and machine != "(Wszystkie)" and event.get('machine') != machine:
                    continue
                if pin and pin != "(Wszystkie)" and event.get('pin') != pin:
                    continue
                rows.append(event)
            rows.sort(key=lambda r: (r.get('dt'), r.get('machine'), r.get('pin')))
            table.setRowCount(len(rows))
            value_keys = list(getattr(self, '_hp_grip_value_keys', []))
            highlight = QBrush(QColor('#dbeafe'))
            for row_idx, event in enumerate(rows):
                dt = event.get('dt')
                table.setItem(row_idx, 0, QTableWidgetItem(dt.strftime('%Y-%m-%d') if isinstance(dt, datetime) else ''))
                table.setItem(row_idx, 1, QTableWidgetItem(dt.strftime('%H:%M:%S') if isinstance(dt, datetime) else ''))
                table.setItem(row_idx, 2, QTableWidgetItem(event.get('machine', '')))
                table.setItem(row_idx, 3, QTableWidgetItem(event.get('program', '')))
                table.setItem(row_idx, 4, QTableWidgetItem(event.get('pin', '')))
                base = 5
                for offset, key in enumerate(value_keys):
                    text = str(event.get('values', {}).get(key, ''))
                    item = QTableWidgetItem(text)
                    if text:
                        item.setToolTip(text)
                        item.setBackground(highlight)
                    table.setItem(row_idx, base + offset, item)
                path_idx = base + len(value_keys)
                path_txt = event.get('path', '') or ''
                path_item = QTableWidgetItem(path_txt)
                if path_txt:
                    path_item.setToolTip(path_txt)
                table.setItem(row_idx, path_idx, path_item)
            try:
                table.resizeColumnsToContents()
            except Exception:
                pass
            self.hp_grip_filtered = rows

    def _populate_nest_filters(self) -> None:
            if not hasattr(self, 'nest_machine'):
                return
            events = getattr(self, 'nest_events', [])
            hierarchy: dict[str, set[str]] = {}
            for event in events:
                machine = str(event.get('machine', '') or '').strip()
                pin = str(event.get('pin', '') or '').strip()
                if not machine:
                    continue
                machine_set = hierarchy.setdefault(machine, set())
                if pin:
                    machine_set.add(pin)
            self._nest_filter_hierarchy = hierarchy
            machines = [key for key in hierarchy.keys() if key]
            self._set_combo_items(self.nest_machine, machines)
            self._update_nest_pin_options()
            self._apply_nest_filters()

    def _update_nest_pin_options(self) -> None:
            hierarchy = getattr(self, '_nest_filter_hierarchy', {}) or {}
            machine = self.nest_machine.currentText().strip() if self.nest_machine.count() else ""
            pins: set[str] = set()
            if machine and machine != "(Wszystkie)":
                pins.update(hierarchy.get(machine, set()))
            else:
                for values in hierarchy.values():
                    pins.update(values)
            self._set_combo_items(self.nest_pin, pins)

    def _on_nest_machine_changed(self, index: int) -> None:  # noqa: ARG002
            self._update_nest_pin_options()
            self._apply_nest_filters()

    def _apply_nest_filters(self) -> None:
            table = getattr(self, 'nest_table', None)
            if table is None:
                return
            events = getattr(self, 'nest_events', [])
            machine = self.nest_machine.currentText() if self.nest_machine.count() else "(Wszystkie)"
            pin = self.nest_pin.currentText() if self.nest_pin.count() else "(Wszystkie)"
            rows: list[dict] = []
            for event in events:
                if machine and machine != "(Wszystkie)" and event.get('machine') != machine:
                    continue
                if pin and pin != "(Wszystkie)" and event.get('pin') != pin:
                    continue
                rows.append(event)
            rows.sort(key=lambda r: (r.get('dt'), r.get('machine'), r.get('pin')))
            table.setRowCount(len(rows))
            value_keys = list(getattr(self, '_nest_value_keys', []))
            highlight = QBrush(QColor('#dbeafe'))
            for row_idx, event in enumerate(rows):
                dt = event.get('dt')
                table.setItem(row_idx, 0, QTableWidgetItem(dt.strftime('%Y-%m-%d') if isinstance(dt, datetime) else ''))
                table.setItem(row_idx, 1, QTableWidgetItem(dt.strftime('%H:%M:%S') if isinstance(dt, datetime) else ''))
                table.setItem(row_idx, 2, QTableWidgetItem(event.get('machine', '')))
                table.setItem(row_idx, 3, QTableWidgetItem(event.get('program', '')))
                table.setItem(row_idx, 4, QTableWidgetItem(event.get('pin', '')))
                base = 5
                for offset, key in enumerate(value_keys):
                    text = str(event.get('values', {}).get(key, ''))
                    item = QTableWidgetItem(text)
                    if text:
                        item.setToolTip(text)
                        item.setBackground(highlight)
                    table.setItem(row_idx, base + offset, item)
                path_idx = base + len(value_keys)
                path_txt = event.get('path', '') or ''
                path_item = QTableWidgetItem(path_txt)
                if path_txt:
                    path_item.setToolTip(path_txt)
                table.setItem(row_idx, path_idx, path_item)
            try:
                table.resizeColumnsToContents()
            except Exception:
                pass
            self.nest_filtered = rows

    def _populate_stripping_filters(self) -> None:
            if not hasattr(self, 'stripping_machine'):
                return
            events = getattr(self, 'hairpin_events', [])
            hierarchy: dict[str, set[str]] = {}
            for event in events:
                machine = str(event.get('machine', '') or '').strip()
                pin = str(event.get('pin', '') or '').strip()
                if not machine:
                    continue
                machine_set = hierarchy.setdefault(machine, set())
                if pin:
                    machine_set.add(pin)
            self._hairpin_filter_hierarchy = hierarchy
            machines = [key for key in hierarchy.keys() if key]
            self._set_combo_items(self.stripping_machine, machines)
            self._update_stripping_pin_options()
            self._apply_stripping_filters()

    def _update_stripping_pin_options(self) -> None:
            hierarchy = getattr(self, '_hairpin_filter_hierarchy', {}) or {}
            machine = self.stripping_machine.currentText().strip() if self.stripping_machine.count() else ""
            pins: set[str] = set()
            if machine and machine != "(Wszystkie)":
                pins.update(hierarchy.get(machine, set()))
            else:
                for values in hierarchy.values():
                    pins.update(values)
            self._set_combo_items(self.stripping_pin, pins)

    def _on_stripping_machine_changed(self, index: int) -> None:  # noqa: ARG002
            self._update_stripping_pin_options()
            self._apply_stripping_filters()

    def _apply_stripping_filters(self) -> None:
            table = getattr(self, 'stripping_table', None)
            if table is None:
                return
            events = getattr(self, 'hairpin_events', [])
            machine = self.stripping_machine.currentText() if self.stripping_machine.count() else "(Wszystkie)"
            pin = self.stripping_pin.currentText() if self.stripping_pin.count() else "(Wszystkie)"
            rows: list[dict] = []
            for event in events:
                if machine and machine != "(Wszystkie)" and event.get('machine') != machine:
                    continue
                if pin and pin != "(Wszystkie)" and event.get('pin') != pin:
                    continue
                rows.append(event)
            rows.sort(key=lambda r: (r.get('dt'), r.get('machine'), r.get('pin')))
            table.setRowCount(len(rows))
            value_keys = list(getattr(self, '_hairpin_value_keys', []))
            display_map = getattr(self, '_hairpin_display_to_source', {}) or {}
            highlight = QBrush(QColor('#dbeafe'))
            for row_idx, event in enumerate(rows):
                dt = event.get('dt')
                table.setItem(row_idx, 0, QTableWidgetItem(dt.strftime('%Y-%m-%d') if isinstance(dt, datetime) else ''))
                table.setItem(row_idx, 1, QTableWidgetItem(dt.strftime('%H:%M:%S') if isinstance(dt, datetime) else ''))
                table.setItem(row_idx, 2, QTableWidgetItem(event.get('machine', '')))
                table.setItem(row_idx, 3, QTableWidgetItem(event.get('program', '')))
                table.setItem(row_idx, 4, QTableWidgetItem(event.get('pin', '')))
                base = 5
                for offset, key in enumerate(value_keys):
                    source_key = display_map.get(key, key)
                    raw_value = event.get('values', {}).get(source_key, '')
                    text = '' if raw_value is None else str(raw_value)
                    item = QTableWidgetItem(text)
                    if text:
                        item.setToolTip(text)
                        item.setBackground(highlight)
                    table.setItem(row_idx, base + offset, item)
                path_idx = base + len(value_keys)
                path_txt = event.get('path', '') or ''
                path_item = QTableWidgetItem(path_txt)
                if path_txt:
                    path_item.setToolTip(path_txt)
                table.setItem(row_idx, path_idx, path_item)
            try:
                table.resizeColumnsToContents()
            except Exception:
                pass
            self.hairpin_filtered = rows

    def _pareto_target_label(self, row: dict) -> str:
            if not isinstance(row, dict):
                return ""
            for key in ("maszyna_opis", "machine_actual", "sap_mapped", "maszyna_sap"):
                text = str(row.get(key, '') or '').strip()
                if text:
                    return text
            return ""

    def _pareto_source_label(self, row: dict) -> str:
            if not isinstance(row, dict):
                return ""
            for key in ("source_opis", "machine_source", "source_mapped"):
                text = str(row.get(key, '') or '').strip()
                if text:
                    return text
            return ""

    def _populate_pareto_filters(self) -> None:
            if not hasattr(self, 'pareto_machine_combo'):
                return
            rows = getattr(self, 'intranet_nok_rows', [])
            machines = {self._pareto_target_label(r) for r in rows}
            machines = {m for m in machines if m}
            self._set_combo_items(self.pareto_machine_combo, machines)
            self._update_pareto_chart()

    def _update_pareto_chart(self) -> None:
            chart = getattr(self, 'pareto_chart', None)
            if chart is None:
                return
            rows = getattr(self, 'intranet_nok_rows', [])
            if not rows:
                chart.set_data({})
                if hasattr(self, 'pareto_summary_label'):
                    self.pareto_summary_label.setText("Brak danych")
                return
            machine = self.pareto_machine_combo.currentText() if self.pareto_machine_combo.count() else "(Wszystkie)"
            filter_edit = getattr(self, 'pareto_machine_filter', None)
            name_filter = filter_edit.text().strip().lower() if filter_edit is not None else ""
            nested: dict[str, dict[str, int]] = {}
            for row in rows:
                target = self._pareto_target_label(row) or "Nieznana maszyna"
                if machine and machine != "(Wszystkie)" and target != machine:
                    continue
                source = self._pareto_source_label(row) or "Nieznane źródło"
                if name_filter and name_filter not in target.lower() and name_filter not in source.lower():
                    continue
                source_map = nested.setdefault(source, {})
                source_map[target] = source_map.get(target, 0) + 1
            effective = {label: mapping for label, mapping in nested.items() if sum(mapping.values()) > 0}
            if not effective:
                chart.set_data({})
                if hasattr(self, 'pareto_summary_label'):
                    self.pareto_summary_label.setText("Brak danych")
                return
            chart.set_data(effective)
            if hasattr(self, 'pareto_summary_label'):
                total = sum(sum(mapping.values()) for mapping in effective.values())
                source_count = len(effective)
                target_count = len({name for mapping in effective.values() for name in mapping.keys()})
                self.pareto_summary_label.setText(
                    f"Łącznie NOK: {total} | Źródła: {source_count} | Maszyny NOK: {target_count}"
                )

    def _populate_param_card_filters(self) -> None:
            dt_combo = getattr(self, 'param_card_datetime', None)
            machine_combo = getattr(self, 'param_card_machine', None)
            if dt_combo is None or machine_combo is None:
                return
            snaps = getattr(self, 'param_snapshots', [])
            groups: dict[str, dict[datetime, list[ParamSnapshot]]] = {}
            for snap in snaps:
                if not isinstance(snap, ParamSnapshot):
                    continue
                dt = getattr(snap, 'dt', None)
                if not isinstance(dt, datetime):
                    continue
                machine_key = snap.machine or ''
                machine_map = groups.setdefault(machine_key, {})
                machine_map.setdefault(dt, []).append(snap)
            self.param_card_groups = groups
            self.param_card_selection = None
            self.current_param_card_rows = []
            dt_combo.blockSignals(True)
            machine_combo.blockSignals(True)
            dt_combo.clear()
            machine_combo.clear()
            dt_combo.setEnabled(False)
            machine_combo.setEnabled(False)
            if not groups:
                machine_combo.addItem("(Brak danych)")
                dt_combo.addItem("(Brak danych)")
                dt_combo.blockSignals(False)
                machine_combo.blockSignals(False)
                self._set_param_card_group(None, None)
                return
            try:
                machine_keys = sorted(groups.keys(), key=_natural_sort_key)
            except Exception:
                machine_keys = list(groups.keys())
            for machine in machine_keys:
                display = machine if machine else '-'
                machine_combo.addItem(display, machine)
            machine_combo.setEnabled(True)
            machine_combo.blockSignals(False)
            dt_combo.blockSignals(False)
            if machine_combo.count():
                machine_combo.setCurrentIndex(0)
            else:
                self._set_param_card_group(None, None)

    def _on_param_card_datetime_changed(self, index: int) -> None:
            dt_combo = getattr(self, 'param_card_datetime', None)
            machine_combo = getattr(self, 'param_card_machine', None)
            if dt_combo is None or machine_combo is None:
                return
            if index < 0:
                self._set_param_card_group(None, None)
                return
            dt = dt_combo.itemData(index, Qt.UserRole)
            if not isinstance(dt, datetime):
                dt = dt_combo.itemData(index)
            if not isinstance(dt, datetime):
                self._set_param_card_group(None, None)
                return
            machine = machine_combo.currentData(Qt.UserRole)
            if machine is None:
                text = machine_combo.currentText()
                machine = '' if text == '-' else text
            machine_str = machine if isinstance(machine, str) else str(machine or '')
            self._set_param_card_group(dt, machine_str)

    def _update_param_card_datetime_options(self, machine_key: str) -> None:
            dt_combo = getattr(self, 'param_card_datetime', None)
            if dt_combo is None:
                return
            dt_combo.blockSignals(True)
            dt_combo.clear()
            groups = getattr(self, 'param_card_groups', {})
            machine_map = groups.get(machine_key or '', {})
            if not machine_map:
                dt_combo.addItem("(Brak danych)")
                dt_combo.setEnabled(False)
                dt_combo.blockSignals(False)
                self._set_param_card_group(None, None)
                return
            try:
                sorted_datetimes = sorted(machine_map.keys(), reverse=True)
            except Exception:
                sorted_datetimes = list(machine_map.keys())
            for dt in sorted_datetimes:
                try:
                    label = dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    label = str(dt)
                dt_combo.addItem(label, dt)
            dt_combo.setEnabled(True)
            dt_combo.blockSignals(False)
            if dt_combo.count():
                dt_combo.setCurrentIndex(0)
            else:
                self._set_param_card_group(None, None)

    def _on_param_card_machine_changed(self, index: int) -> None:
            dt_combo = getattr(self, 'param_card_datetime', None)
            machine_combo = getattr(self, 'param_card_machine', None)
            if dt_combo is None or machine_combo is None:
                return
            if index < 0:
                dt_combo.blockSignals(True)
                dt_combo.clear()
                dt_combo.addItem("(Brak danych)")
                dt_combo.setEnabled(False)
                dt_combo.blockSignals(False)
                self._set_param_card_group(None, None)
                return
            machine = machine_combo.itemData(index, Qt.UserRole)
            if machine is None:
                text = machine_combo.itemText(index)
                machine = '' if text == '-' else text
            machine_key = machine if isinstance(machine, str) else str(machine or '')
            self._update_param_card_datetime_options(machine_key)

    def _set_param_card_group(self, dt: datetime | None, machine: str | None) -> None:
            groups = getattr(self, 'param_card_groups', {})
            snaps: list[ParamSnapshot] = []
            if dt is not None and machine is not None:
                try:
                    machine_key = machine or ''
                    snaps = list(groups.get(machine_key, {}).get(dt, []))
                except Exception:
                    snaps = []
            self._param_card_index_lookup = {}
            self._param_card_grip_lookup = {}
            self._param_card_nest_lookup = {}
            self._param_card_hairpin_lookup = {}
            self.current_param_card_rows = snaps
            self.param_card_selection = (dt, machine) if snaps else None
            export_btn = getattr(self, 'param_card_export_btn', None)
            if export_btn is not None:
                export_btn.setEnabled(bool(snaps))
            if snaps and dt is not None and machine is not None:
                machine_norm = (machine or '').strip()
                try:
                    index_lookup: dict[tuple[str, str, int], IndexSnapshot] = {}
                    for idx_snap in getattr(self, 'index_snapshots', []):
                        if not isinstance(idx_snap, IndexSnapshot):
                            continue
                        snap_machine = (idx_snap.machine or '').strip()
                        if snap_machine != machine_norm:
                            continue
                        if getattr(idx_snap, 'dt', None) != dt:
                            continue
                        step_key = idx_snap.step if idx_snap.step is not None else -1
                        key = (
                            (idx_snap.program or '').strip(),
                            (idx_snap.table or '').strip(),
                            step_key,
                        )
                        index_lookup[key] = idx_snap
                    self._param_card_index_lookup = index_lookup
                except Exception:
                    self._param_card_index_lookup = {}
                try:
                    grip_lookup: dict[tuple[str, str], GripSnapshot] = {}
                    for grip_snap in getattr(self, 'hp_grip_snapshots', []):
                        if not isinstance(grip_snap, GripSnapshot):
                            continue
                        snap_machine = (grip_snap.machine or '').strip()
                        if snap_machine != machine_norm:
                            continue
                        if getattr(grip_snap, 'dt', None) != dt:
                            continue
                        key = (
                            (grip_snap.program or '').strip(),
                            (grip_snap.pin or '').strip(),
                        )
                        grip_lookup[key] = grip_snap
                    self._param_card_grip_lookup = grip_lookup
                except Exception:
                    self._param_card_grip_lookup = {}
                try:
                    nest_lookup: dict[tuple[str, str], NestSnapshot] = {}
                    for nest_snap in getattr(self, 'nest_snapshots', []):
                        if not isinstance(nest_snap, NestSnapshot):
                            continue
                        snap_machine = (nest_snap.machine or '').strip()
                        if snap_machine != machine_norm:
                            continue
                        if getattr(nest_snap, 'dt', None) != dt:
                            continue
                        key = (
                            (nest_snap.program or '').strip(),
                            (nest_snap.pin or '').strip(),
                        )
                        nest_lookup[key] = nest_snap
                    self._param_card_nest_lookup = nest_lookup
                except Exception:
                    self._param_card_nest_lookup = {}
                try:
                    hairpin_lookup: dict[tuple[str, str], HairpinSnapshot] = {}
                    for hair_snap in getattr(self, 'hairpin_snapshots', []):
                        if not isinstance(hair_snap, HairpinSnapshot):
                            continue
                        snap_machine = (hair_snap.machine or '').strip()
                        if snap_machine != machine_norm:
                            continue
                        if getattr(hair_snap, 'dt', None) != dt:
                            continue
                        key = (
                            (hair_snap.program or '').strip(),
                            (hair_snap.pin or '').strip(),
                        )
                        hairpin_lookup[key] = hair_snap
                    self._param_card_hairpin_lookup = hairpin_lookup
                except Exception:
                    self._param_card_hairpin_lookup = {}
            self._update_param_card_table(snaps)

    def _update_param_card_table(self, snaps: list[ParamSnapshot] | None) -> None:
            table = getattr(self, 'param_card_table', None)
            info = getattr(self, 'param_card_info', None)
            if table is None:
                return
            if not snaps:
                table.setRowCount(0)
                if info is not None:
                    info.setText("Brak danych")
                return
            try:
                first = snaps[0]
            except Exception:
                table.setRowCount(0)
                if info is not None:
                    info.setText("Brak danych")
                return
            try:
                date_txt = first.dt.strftime('%Y-%m-%d')
                time_txt = first.dt.strftime('%H:%M:%S')
            except Exception:
                date_txt = str(getattr(first, 'dt', ''))
                time_txt = ''
            machine = first.machine or '-'
            programs = sorted({snap.program for snap in snaps if getattr(snap, 'program', '')})
            tables = sorted({snap.table for snap in snaps if getattr(snap, 'table', '')})
            pins = sorted({snap.pin for snap in snaps if getattr(snap, 'pin', '')})
            steps = sorted({snap.step for snap in snaps if getattr(snap, 'step', None) is not None})
            paths = sorted({snap.path for snap in snaps if getattr(snap, 'path', '')})
            info_lines = [
                f"Data: {date_txt}    Czas: {time_txt}".strip(),
                f"Maszyna: {machine}    Migawek: {len(snaps)}",
            ]
            if programs:
                info_lines.append(f"Programy: {', '.join(programs)}")
            if tables:
                info_lines.append(f"Tabele: {', '.join(tables)}")
            info_lines.append(f"Piny: {len(pins)}    Stepy: {len(steps)}")
            if paths:
                if len(paths) == 1:
                    info_lines.append(f"Plik: {paths[0]}")
                else:
                    info_lines.append(f"Pliki: {len(paths)} (np. {paths[0]})")
            if info is not None:
                info.setText("\n".join(info_lines))
            try:
                sorted_snaps = sorted(
                    snaps,
                    key=lambda s: (
                        getattr(s, 'program', '') or '',
                        getattr(s, 'table', '') or '',
                        getattr(s, 'pin', '') or '',
                        getattr(s, 'step', -1) if getattr(s, 'step', None) is not None else -1,
                    ),
                )
            except Exception:
                sorted_snaps = list(snaps)
            value_names = list(getattr(self, 'param_card_value_names', list(PARAM_DISPLAY_ORDER)))
            rows: list[list[str]] = []
            for snap in sorted_snaps:
                program = snap.program or '-'
                table_name = snap.table or '-'
                pin = snap.pin or '-'
                step_val = snap.step if snap.step is not None else '-'
                step_txt = str(step_val)
                row_values: list[str] = [program, table_name, pin, step_txt]
                for name in value_names:
                    row_values.append(self._param_card_cell_text(snap, name))
                rows.append(row_values)
            table.setUpdatesEnabled(False)
            table.setRowCount(len(rows))
            for row_idx, row_values in enumerate(rows):
                for col_idx, value in enumerate(row_values):
                    table.setItem(row_idx, col_idx, QTableWidgetItem(value))
            table.setUpdatesEnabled(True)
            try:
                table.resizeColumnsToContents()
            except Exception:
                pass

    def _param_card_struct_text(self, value: object) -> str:
            text = self._format_struct_value(value)
            return "" if text == "(brak)" else text

    def _param_card_cell_text(self, snap: ParamSnapshot, name: str) -> str:
            if name in PARAM_DISPLAY_ORDER:
                if name == STEP_SPEED_LABEL:
                    value = snap.values.get(name)
                    if value is None:
                        return ""
                    try:
                        return f"{value:g}"
                    except Exception:
                        return str(value)
                include = bool(snap.included.get(name, False))
                if not include:
                    return "wył."
                value = snap.values.get(name)
                if value is None:
                    value_txt = ""
                else:
                    try:
                        value_txt = f"{value:g}"
                    except Exception:
                        value_txt = str(value)
                mode = str(snap.modes.get(name, '') or '').upper()
                if mode:
                    if value_txt:
                        return f"{value_txt} ({mode})"
                    return f"({mode})"
                return value_txt

            if name in INDEX_PARAM_DISPLAY_ORDER:
                lookup = getattr(self, '_param_card_index_lookup', {}) or {}
                program_key = (snap.program or '').strip()
                table_key = (snap.table or '').strip()
                step_key = snap.step if snap.step is not None else -1
                idx_snap = lookup.get((program_key, table_key, step_key))
                if idx_snap is None:
                    if name == INDEX_OVERRIDE_LABEL:
                        return ""
                    return ""
                if name == INDEX_OVERRIDE_LABEL:
                    return self._format_override_value(getattr(idx_snap, 'override', None))
                include = bool(idx_snap.included.get(name, False))
                if not include:
                    return "wył."
                value = idx_snap.values.get(name)
                if value is None:
                    value_txt = ""
                else:
                    try:
                        value_txt = f"{value:g}"
                    except Exception:
                        value_txt = str(value)
                mode = str(idx_snap.modes.get(name, '') or '').upper()
                if mode:
                    if value_txt:
                        return f"{value_txt} ({mode})"
                    return f"({mode})"
                return value_txt

            program_key = (snap.program or '').strip()
            pin_key = (snap.pin or '').strip()

            if name in GRIP_PARAM_ORDER:
                lookup = getattr(self, '_param_card_grip_lookup', {}) or {}
                struct_snap = lookup.get((program_key, pin_key))
                if not struct_snap:
                    return ""
                return self._param_card_struct_text(struct_snap.values.get(name, ''))

            if name in NEST_PARAM_ORDER:
                lookup = getattr(self, '_param_card_nest_lookup', {}) or {}
                struct_snap = lookup.get((program_key, pin_key))
                if not struct_snap:
                    return ""
                return self._param_card_struct_text(struct_snap.values.get(name, ''))

            if name in HAIRPIN_PARAM_ORDER:
                lookup = getattr(self, '_param_card_hairpin_lookup', {}) or {}
                struct_snap = lookup.get((program_key, pin_key))
                if not struct_snap:
                    return ""
                value = struct_snap.values.get(name)
                if value is None:
                    for raw_key, display in HAIRPIN_PARAM_LABELS.items():
                        if display == name:
                            value = struct_snap.values.get(raw_key)
                            if value is not None:
                                break
                return self._param_card_struct_text(value)

            return ""

    def _populate_index_line_filters(self):
            if not hasattr(self, 'index_line_machine'):
                return
            snaps = getattr(self, 'index_snapshots', [])
            hierarchy: dict[str, dict[str, set[str]]] = {}
            for snap in snaps:
                machine = (snap.machine or '').strip()
                if not machine:
                    continue
                machine_entry = hierarchy.setdefault(machine, {})
                table = (snap.table or '').strip()
                if table:
                    step_set = machine_entry.setdefault(table, set())
                else:
                    step_set = machine_entry.setdefault('', set())
                if snap.step is not None:
                    step_set.add(str(snap.step))
            self._index_line_hierarchy = hierarchy
            self._set_combo_items(self.index_line_machine, hierarchy.keys())
            self._update_index_line_table_options()

    def _update_index_line_table_options(self) -> None:
            if not hasattr(self, 'index_line_machine'):
                return
            hierarchy = getattr(self, '_index_line_hierarchy', {}) or {}
            machine = self.index_line_machine.currentText().strip() if self.index_line_machine.count() else ""
            tables: set[str] = set()
            if machine and machine != "(Wszystkie)":
                tables.update(key for key in hierarchy.get(machine, {}).keys() if key)
            else:
                for machine_tables in hierarchy.values():
                    tables.update(key for key in machine_tables.keys() if key)
            self._set_combo_items(self.index_line_pin, tables)
            self._update_index_line_step_options()

    def _update_index_line_step_options(self) -> None:
            if not hasattr(self, 'index_line_step'):
                return
            hierarchy = getattr(self, '_index_line_hierarchy', {}) or {}
            machine = self.index_line_machine.currentText().strip() if self.index_line_machine.count() else ""
            table = self.index_line_pin.currentText().strip() if self.index_line_pin.count() else ""
            steps: set[str] = set()
            if machine and machine != "(Wszystkie)":
                machine_tables = hierarchy.get(machine, {})
                if table and table != "(Wszystkie)":
                    steps.update(machine_tables.get(table, set()))
                else:
                    for values in machine_tables.values():
                        steps.update(values)
            else:
                if table and table != "(Wszystkie)":
                    for machine_tables in hierarchy.values():
                        steps.update(machine_tables.get(table, set()))
                else:
                    for machine_tables in hierarchy.values():
                        for values in machine_tables.values():
                            steps.update(values)
            self._set_combo_items(self.index_line_step, steps)

    def _on_index_line_machine_changed(self, index: int) -> None:  # noqa: ARG002
            self._update_index_line_table_options()

    def _on_index_line_pin_changed(self, index: int) -> None:  # noqa: ARG002
            self._update_index_line_step_options()

    def _apply_index_line_filters(self):
            charts = getattr(self, 'index_line_charts', {})
            if not charts:
                return
            snaps = getattr(self, 'index_snapshots', [])
            machine = self.index_line_machine.currentText().strip() if self.index_line_machine.count() else "(Wszystkie)"
            table = self.index_line_pin.currentText().strip() if self.index_line_pin.count() else "(Wszystkie)"
            step = self.index_line_step.currentText().strip() if self.index_line_step.count() else "(Wszystkie)"

            for name, chart in charts.items():
                points: list[tuple[datetime, float]] = []
                for snap in snaps:
                    if machine and machine != "(Wszystkie)" and snap.machine != machine:
                        continue
                    if table and table != "(Wszystkie)" and str(snap.table or "") != table:
                        continue
                    if step and step != "(Wszystkie)" and str(snap.step) != step:
                        continue
                    if name == INDEX_OVERRIDE_LABEL:
                        value = snap.override
                    else:
                        if not snap.included.get(name, False):
                            continue
                        value = snap.values.get(name)
                    if value is None:
                        continue
                    try:
                        val = float(value)
                    except Exception:
                        continue
                    if math.isnan(val) or math.isinf(val):
                        continue
                    points.append((snap.dt, val))
                chart.set_series(name, points, self._index_line_colors.get(name))

    def _clear_index_line_charts(self) -> None:
            charts = getattr(self, 'index_line_charts', {})
            if not charts:
                return
            for name, chart in charts.items():
                chart.set_series(name, [], self._index_line_colors.get(name))

    def _populate_index_filters(self):
            events = getattr(self, 'index_events', [])
            hierarchy: dict[str, dict[str, dict[str, set[str]]]] = {}
            for event in events:
                if event.get('type') != 'index_change':
                    continue
                machine = str(event.get('machine', '') or '').strip()
                table = str(event.get('table', '') or '').strip()
                step_val = event.get('step')
                step = str(step_val) if step_val is not None else ''
                cols = event.get('cols') or {}
                params = {name for name, text in cols.items() if text}
                machine_entry = hierarchy.setdefault(machine, {})
                table_entry = machine_entry.setdefault(table, {})
                step_entry = table_entry.setdefault(step, set())
                if params:
                    step_entry.update(params)
            self._index_filter_hierarchy = hierarchy

            machines = [key for key in hierarchy.keys() if key]
            self._set_combo_items(self.idx_f_machine, machines)
            self._update_index_table_options()

    def _update_index_table_options(self) -> None:
            hierarchy = getattr(self, '_index_filter_hierarchy', {}) or {}
            machine = self.idx_f_machine.currentText().strip() if self.idx_f_machine.count() else ""
            tables: set[str] = set()
            if machine and machine != "(Wszystkie)":
                tables.update(key for key in hierarchy.get(machine, {}).keys() if key)
            else:
                for machine_tables in hierarchy.values():
                    tables.update(key for key in machine_tables.keys() if key)
            self._set_combo_items(self.idx_f_table, tables)
            self._update_index_step_options()

    def _update_index_step_options(self) -> None:
            hierarchy = getattr(self, '_index_filter_hierarchy', {}) or {}
            machine = self.idx_f_machine.currentText().strip() if self.idx_f_machine.count() else ""
            table = self.idx_f_table.currentText().strip() if self.idx_f_table.count() else ""
            steps: set[str] = set()
            if machine and machine != "(Wszystkie)":
                machine_tables = hierarchy.get(machine, {})
                if table and table != "(Wszystkie)":
                    steps.update(step for step in machine_tables.get(table, {}).keys() if step)
                else:
                    for table_steps in machine_tables.values():
                        steps.update(step for step in table_steps.keys() if step)
            else:
                if table and table != "(Wszystkie)":
                    for machine_tables in hierarchy.values():
                        steps.update(step for step in machine_tables.get(table, {}).keys() if step)
                else:
                    for machine_tables in hierarchy.values():
                        for table_steps in machine_tables.values():
                            steps.update(step for step in table_steps.keys() if step)
            self._set_combo_items(self.idx_f_step, steps)
            self._update_index_param_options()

    def _update_index_param_options(self) -> None:
            hierarchy = getattr(self, '_index_filter_hierarchy', {}) or {}
            machine = self.idx_f_machine.currentText().strip() if self.idx_f_machine.count() else ""
            table = self.idx_f_table.currentText().strip() if self.idx_f_table.count() else ""
            step = self.idx_f_step.currentText().strip() if self.idx_f_step.count() else ""
            params: set[str] = set()

            def collect(table_map: dict[str, set[str]]) -> None:
                for step_key, values in table_map.items():
                    if step and step != "(Wszystkie)" and step_key != step:
                        continue
                    params.update(values)

            if machine and machine != "(Wszystkie)":
                machine_tables = hierarchy.get(machine, {})
                if table and table != "(Wszystkie)":
                    collect(machine_tables.get(table, {}))
                else:
                    for table_steps in machine_tables.values():
                        collect(table_steps)
            else:
                if table and table != "(Wszystkie)":
                    for machine_tables in hierarchy.values():
                        collect(machine_tables.get(table, {}))
                else:
                    for machine_tables in hierarchy.values():
                        for table_steps in machine_tables.values():
                            collect(table_steps)

            ordered = [name for name in INDEX_PARAM_DISPLAY_ORDER if name in params]
            self._set_combo_items(self.idx_f_param, ordered, sort_items=False)

    def _on_index_machine_changed(self, index: int) -> None:  # noqa: ARG002
            self._update_index_table_options()
            self._apply_index_filters()

    def _on_index_table_changed(self, index: int) -> None:  # noqa: ARG002
            self._update_index_step_options()
            self._apply_index_filters()

    def _on_index_step_changed(self, index: int) -> None:  # noqa: ARG002
            self._update_index_param_options()
            self._apply_index_filters()

    def _apply_index_filters(self):
            if not hasattr(self, 'index_events'):
                return
            m = self.idx_f_machine.currentText() if self.idx_f_machine.count() else "(Wszystkie)"
            table = self.idx_f_table.currentText() if self.idx_f_table.count() else "(Wszystkie)"
            st = self.idx_f_step.currentText() if self.idx_f_step.count() else "(Wszystkie)"
            par = self.idx_f_param.currentText() if self.idx_f_param.count() else "(Wszystkie)"

            rows = []
            for e in getattr(self, 'index_events', []):
                if e.get('type') != 'index_change':
                    continue
                if m and m != "(Wszystkie)" and e['machine'] != m:
                    continue
                if table and table != "(Wszystkie)" and e['table'] != table:
                    continue
                if st and st != "(Wszystkie)" and str(e['step']) != st:
                    continue
                if par and par != "(Wszystkie)":
                    if not e['cols'].get(par):
                        continue
                rows.append(e)

            rows.sort(key=lambda x: (x['dt'], x['machine'], x['table'], x['step']))

            self.index_table.setRowCount(len(rows))
            highlight = QBrush(QColor('#fff6bf'))
            big_change = QBrush(QColor('#ffd6d6'))
            for i, e in enumerate(rows):
                self.index_table.setItem(i, 0, QTableWidgetItem(e['dt'].strftime('%Y-%m-%d')))
                self.index_table.setItem(i, 1, QTableWidgetItem(e['dt'].strftime('%H:%M:%S')))
                self.index_table.setItem(i, 2, QTableWidgetItem(e['machine']))
                self.index_table.setItem(i, 3, QTableWidgetItem(e['program']))
                self.index_table.setItem(i, 4, QTableWidgetItem(e['table']))
                self.index_table.setItem(i, 5, QTableWidgetItem(str(e['step'])))

                base = 6
                params = INDEX_PARAM_DISPLAY_ORDER
                for j, name in enumerate(params):
                    val = e['cols'].get(name, "")
                    item = QTableWidgetItem(val)
                    if val:
                        if e.get('large', {}).get(name):
                            item.setBackground(big_change)
                        else:
                            item.setBackground(highlight)
                    self.index_table.setItem(i, base + j, item)

                path_col_idx = base + len(params)
                path_text = e.get('path', '') or ''
                path_item = QTableWidgetItem(path_text)
                if path_text:
                    path_item.setToolTip(path_text)
                self.index_table.setItem(i, path_col_idx, path_item)
            self.index_table.resizeColumnsToContents()
            self.index_filtered_rows = rows

    def _format_index_value(self, include: bool, value: float, mode: str) -> str:
            if not include:
                return "wył."
            try:
                val_txt = f"{value:g}"
            except Exception:
                val_txt = str(value)
            mode_txt = (mode or '').upper()
            if mode_txt:
                if val_txt:
                    return f"{val_txt} ({mode_txt})"
                return f"({mode_txt})"
            return val_txt

    def _format_override_value(self, value: float | None) -> str:
            if value is None:
                return "(brak)"
            try:
                return f"{value:g}"
            except Exception:
                return str(value)

    def _normalize_struct_scalar(value: object) -> str:
            text = str(value or "").strip()
            if not text:
                return ""
            candidate = text.replace(",", ".")
            try:
                dec = Decimal(candidate)
            except (InvalidOperation, ValueError):
                return text.lower()
            normalized = dec.normalize()
            formatted = format(normalized, "f")
            if "." in formatted:
                formatted = formatted.rstrip("0").rstrip(".")
            return formatted or "0"

    def _format_struct_value(value: object) -> str:
            text = str(value or "").strip()
            if not text:
                return "(brak)"
            candidate = text.replace(",", ".")
            try:
                dec = Decimal(candidate)
            except (InvalidOperation, ValueError):
                return text
            normalized = dec.normalize()
            formatted = format(normalized, "f")
            if "." in formatted:
                formatted = formatted.rstrip("0").rstrip(".")
            return formatted or "0"

    def _build_struct_change_events(self, snaps: list[GripSnapshot | HairpinSnapshot]) -> list[dict]:
            events: list[dict] = []
            last_state: dict[tuple[str, str], GripSnapshot | HairpinSnapshot] = {}
            baseline_done: set[tuple[str, str]] = set()
            for snap in snaps:
                if not isinstance(snap, (GripSnapshot, HairpinSnapshot)):
                    continue
                key = (snap.machine, snap.pin)
                if key not in baseline_done:
                    baseline_done.add(key)
                    last_state[key] = snap
                    continue
                prev = last_state.get(key)
                if prev is None:
                    last_state[key] = snap
                    continue
                prev_program = getattr(prev, "program", "") or ""
                curr_program = getattr(snap, "program", "") or ""
                if prev_program != curr_program:
                    last_state[key] = snap
                    continue
                prev_values = getattr(prev, "values", {}) or {}
                curr_values = getattr(snap, "values", {}) or {}
                changed: dict[str, str] = {}
                for name in sorted(set(prev_values.keys()) | set(curr_values.keys()), key=_natural_sort_key):
                    prev_raw = prev_values.get(name, "")
                    curr_raw = curr_values.get(name, "")
                    prev_norm = self._normalize_struct_scalar(prev_raw)
                    curr_norm = self._normalize_struct_scalar(curr_raw)
                    if prev_norm == curr_norm:
                        continue
                    prev_txt = self._format_struct_value(prev_raw)
                    curr_txt = self._format_struct_value(curr_raw)
                    if prev_txt == curr_txt:
                        continue
                    changed[name] = f"{prev_txt} -> {curr_txt}"
                if changed:
                    events.append(
                        {
                            'dt': snap.dt,
                            'machine': snap.machine,
                            'program': snap.program,
                            'pin': snap.pin,
                            'values': changed,
                            'path': snap.path,
                        }
                    )
                last_state[key] = snap
            events.sort(key=lambda e: (e.get('dt'), e.get('machine'), e.get('pin')))
            return events

    def _build_index_events(self, snaps: list[IndexSnapshot], threshold_pct: float) -> list[dict]:
            events: list[dict] = []
            last_state: dict[tuple[str, str, int], IndexSnapshot] = {}
            last_prog: dict[tuple[str, str, int], str] = {}
            baseline_done: set[tuple[str, str, int]] = set()
            for s in snaps:
                key = (s.machine, s.table, s.step)
                if key not in baseline_done:
                    baseline_done.add(key)
                    last_state[key] = s
                    last_prog[key] = s.program
                    continue

                prev = last_state.get(key)
                if prev is None:
                    last_state[key] = s
                    last_prog[key] = s.program
                    continue

                if last_prog.get(key) != s.program:
                    last_state[key] = s
                    last_prog[key] = s.program
                    continue

                changed_cols: dict[str, str] = {}
                large_cols: dict[str, bool] = {}
                for name in INDEX_PARAM_DISPLAY_ORDER:
                    if name == INDEX_OVERRIDE_LABEL:
                        prev_val = prev.override
                        curr_val = s.override
                        if prev_val is None and curr_val is None:
                            changed = False
                        elif prev_val is None or curr_val is None:
                            changed = True
                        else:
                            changed = abs(curr_val - prev_val) > 1e-12

                        changed_cols[name] = ""
                        large_cols[name] = False
                        if not changed:
                            continue

                        prev_txt = self._format_override_value(prev_val)
                        curr_txt = self._format_override_value(curr_val)
                        if prev_txt == curr_txt:
                            continue

                        changed_cols[name] = f"{prev_txt} -> {curr_txt}"
                        continue

                    prev_include = bool(prev.included.get(name, False))
                    curr_include = bool(s.included.get(name, False))
                    if not prev_include and not curr_include:
                        changed_cols[name] = ""
                        large_cols[name] = False
                        continue

                    prev_mode = prev.modes.get(name, 'ABS')
                    curr_mode = s.modes.get(name, 'ABS')
                    prev_value = float(prev.values.get(name, 0.0) or 0.0)
                    curr_value = float(s.values.get(name, 0.0) or 0.0)

                    value_changed = abs(curr_value - prev_value) > 1e-12
                    mode_changed = (curr_mode or '').upper() != (prev_mode or '').upper()
                    include_changed = curr_include != prev_include

                    changed_cols[name] = ""
                    large_cols[name] = False
                    if not (value_changed or mode_changed or include_changed):
                        continue

                    prev_txt = self._format_index_value(prev_include, prev_value, prev_mode)
                    curr_txt = self._format_index_value(curr_include, curr_value, curr_mode)
                    if prev_txt == curr_txt:
                        continue

                    changed_cols[name] = f"{prev_txt} -> {curr_txt}"
                    if prev_include and curr_include and abs(prev_value) > 1e-12:
                        pct = abs((curr_value - prev_value) / prev_value) * 100.0
                        large_cols[name] = (pct >= threshold_pct)

                if any(changed_cols.values()):
                    events.append({
                        'dt': s.dt,
                        'machine': s.machine,
                        'program': s.program,
                        'table': s.table,
                        'step': s.step,
                        'pin': '',
                        'cols': changed_cols,
                        'large': large_cols,
                        'path': s.path,
                        'type': 'index_change',
                    })

                last_state[key] = s
                last_prog[key] = s.program

            events.sort(key=lambda x: (x['dt'], x['machine'], x['table'], x['step']))
            deduped = self._deduplicate_index_events(events)
            return self._collapse_repeated_index_events(deduped)

    @staticmethod
    def _normalize_event_text(value: object) -> str:
            if value is None:
                return ""
            if isinstance(value, str):
                text = value.strip()
            else:
                text = str(value).strip()
            if not text:
                return ""
            candidate = text.replace(",", ".")
            try:
                dec = Decimal(candidate)
            except (InvalidOperation, ValueError):
                return text.lower()
            normalized = dec.normalize()
            formatted = format(normalized, "f")
            if "." in formatted:
                formatted = formatted.rstrip("0").rstrip(".")
            return formatted or "0"

    @staticmethod
    def _event_dt_key(value: object):
            if isinstance(value, datetime):
                return value.replace(microsecond=0)
            return value

    def _merge_event_paths(self, existing: dict, duplicate: dict) -> None:
            current = self._normalize_event_text(existing.get('path', ''))
            new_path = self._normalize_event_text(duplicate.get('path', ''))
            if not new_path:
                return
            if not current:
                existing['path'] = new_path
                return
            paths = [p for p in (line.strip() for line in current.splitlines()) if p]
            if new_path in paths:
                return
            paths.append(new_path)
            existing['path'] = "\n".join(paths)

    def _deduplicate_param_events(self, events: list[dict]) -> list[dict]:
            seen: dict[tuple, dict] = {}
            deduped: list[dict] = []
            order = tuple(PARAM_DISPLAY_ORDER)
            for event in events:
                if event.get('type') != 'change':
                    deduped.append(event)
                    continue
                cols = event.get('cols') or {}
                key = (
                    self._event_dt_key(event.get('dt')),
                    self._normalize_event_text(event.get('machine')),
                    self._normalize_event_text(event.get('program')),
                    self._normalize_event_text(event.get('table')),
                    self._normalize_event_text(event.get('pin')),
                    self._normalize_event_text(event.get('step')),
                    tuple((name, self._normalize_event_text(cols.get(name, ""))) for name in order),
                )
                existing = seen.get(key)
                if existing is not None:
                    self._merge_event_paths(existing, event)
                    continue
                seen[key] = event
                deduped.append(event)
            return deduped

    def _deduplicate_index_events(self, events: list[dict]) -> list[dict]:
            seen: dict[tuple, dict] = {}
            deduped: list[dict] = []
            order = tuple(INDEX_PARAM_DISPLAY_ORDER)
            merged = 0
            logger = logging.getLogger(__name__)
            for event in events:
                if event.get('type') != 'index_change':
                    deduped.append(event)
                    continue
                cols = event.get('cols') or {}
                key = (
                    self._event_dt_key(event.get('dt')),
                    self._normalize_event_text(event.get('machine')),
                    self._normalize_event_text(event.get('program')),
                    self._normalize_event_text(event.get('table')),
                    self._normalize_event_text(event.get('step')),
                    tuple((name, self._normalize_event_text(cols.get(name, ""))) for name in order),
                )
                existing = seen.get(key)
                if existing is not None:
                    merged += 1
                    logger.debug(
                        "[IndexEvents] merged duplicate (dt=%s machine=%s table=%s step=%s) paths: %s | %s",
                        event.get('dt'),
                        event.get('machine'),
                        event.get('table'),
                        event.get('step'),
                        existing.get('path'),
                        event.get('path'),
                    )
                    self._merge_event_paths(existing, event)
                    continue
                seen[key] = event
                deduped.append(event)
            if merged:
                logger.info("[IndexEvents] merged %s strict duplicate entries", merged)
            return deduped

    def _collapse_repeated_index_events(self, events: list[dict]) -> list[dict]:
            order = tuple(INDEX_PARAM_DISPLAY_ORDER)
            collapsed: list[dict] = []
            last_signature: dict[tuple[str, str, str, str], tuple[tuple, object, dict]] = {}
            logger = logging.getLogger(__name__)
            repeats = 0
            for event in events:
                if event.get('type') != 'index_change':
                    collapsed.append(event)
                    continue

                cols = event.get('cols') or {}
                machine = self._normalize_event_text(event.get('machine'))
                program = self._normalize_event_text(event.get('program'))
                table = self._normalize_event_text(event.get('table'))
                step = self._normalize_event_text(event.get('step'))
                signature = tuple((name, self._normalize_event_text(cols.get(name, ""))) for name in order)
                key = (machine, program, table, step)

                previous = last_signature.get(key)
                if previous and previous[0] == signature:
                    repeats += 1
                    prev_dt = previous[1]
                    prev_event = previous[2]
                    logger.info(
                        "[IndexEvents] dropping repeated change for %s/%s table=%s step=%s (%s -> %s)",
                        event.get('machine'),
                        event.get('program'),
                        event.get('table'),
                        event.get('step'),
                        prev_dt,
                        event.get('dt'),
                    )
                    logger.debug(
                        "[IndexEvents] repeat details: prev_path=%s new_path=%s diffs=%s",
                        prev_event.get('path'),
                        event.get('path'),
                        {name: cols.get(name, "") for name in order if cols.get(name, "")},
                    )
                    self._merge_event_paths(prev_event, event)
                    continue

                last_signature[key] = (signature, event.get('dt'), event)
                collapsed.append(event)

            if repeats:
                logger.info("[IndexEvents] collapsed %s repeated index events", repeats)
            return collapsed

    def _fill_change_trees(self):
            try:
                from PyQt5.QtWidgets import QTreeWidgetItem
                events = getattr(self, 'analysis_events', [])
                change_tree = getattr(self, 'change_tree', None)
                top_tree = getattr(self, 'top_issues_tree', None)
                if change_tree is None or top_tree is None:
                    return

                combo_counts: dict[tuple[str, str, str, str], int] = {}
                nested: dict[str, dict[str, dict[str, dict[str, int]]]] = {}
                for e in events:
                    if e.get('type') != 'change':
                        continue
                    machine = e.get('machine', '')
                    pin = e.get('pin') or ''
                    step_val = e.get('step')
                    step_key = str(step_val) if step_val is not None else ''
                    cols = e.get('cols') or {}
                    for name, change in cols.items():
                        if not change:
                            continue
                        key = (machine, pin, step_key, name)
                        combo_counts[key] = combo_counts.get(key, 0) + 1
                        machine_entry = nested.setdefault(machine, {})
                        pin_entry = machine_entry.setdefault(pin, {})
                        step_entry = pin_entry.setdefault(step_key, {})
                        step_entry[name] = step_entry.get(name, 0) + 1

                def step_total(params_dict: dict[str, int]) -> int:
                    return sum(params_dict.values())

                def pin_total(steps_dict: dict[str, dict[str, int]]) -> int:
                    return sum(step_total(params_dict) for params_dict in steps_dict.values())

                def machine_total(pins_dict: dict[str, dict[str, dict[str, int]]]) -> int:
                    return sum(pin_total(steps_dict) for steps_dict in pins_dict.values())

                def color_for(val: int, vmin: int, vmax: int) -> QColor:
                    if vmax <= vmin:
                        return QColor('#e0f7e9')
                    ratio = max(0.0, min(1.0, (val - vmin) / float(vmax - vmin)))
                    start = QColor(0x2e, 0xcc, 0x71)
                    end = QColor(0xe7, 0x4c, 0x3c)
                    rr = int(start.red() + (end.red() - start.red()) * ratio)
                    gg = int(start.green() + (end.green() - start.green()) * ratio)
                    bb = int(start.blue() + (end.blue() - start.blue()) * ratio)
                    return QColor(rr, gg, bb)

                def translucent(color: QColor, alpha: int) -> QColor:
                    tmp = QColor(color)
                    tmp.setAlpha(alpha)
                    return tmp

                try:
                    top_tree.blockSignals(True)
                except Exception:
                    pass
                top_tree.clear()
                try:
                    top_tree.setItemDelegateForColumn(4, CountBadgeDelegate(top_tree))
                except Exception:
                    pass
                if combo_counts:
                    combo_min = min(combo_counts.values())
                    combo_max = max(combo_counts.values())
                else:
                    combo_min = combo_max = 0
                limit = 25
                for (machine, pin, step_key, name), cnt in sorted(
                    combo_counts.items(),
                    key=lambda kv: (-kv[1], kv[0][0], kv[0][1], kv[0][2], kv[0][3]),
                ):
                    item = QTreeWidgetItem([
                        machine or '(brak)',
                        pin or '(brak)',
                        step_key or '(brak)',
                        name,
                        str(cnt),
                    ])
                    item.setData(0, Qt.UserRole, ('combo', machine, pin, step_key, name))
                    item.setTextAlignment(4, Qt.AlignCenter)
                    color = color_for(cnt, combo_min, combo_max)
                    item.setBackground(4, color)
                    for idx in range(4):
                        item.setBackground(idx, translucent(color, 40))
                    top_tree.addTopLevelItem(item)
                    limit -= 1
                    if limit <= 0:
                        break
                try:
                    top_tree.blockSignals(False)
                except Exception:
                    pass

                try:
                    change_tree.blockSignals(True)
                except Exception:
                    pass
                change_tree.clear()
                try:
                    change_tree.setItemDelegateForColumn(1, CountBadgeDelegate(change_tree))
                except Exception:
                    pass

                def label_sort_key(value: str) -> tuple[int, str]:
                    text = (value or "").strip()
                    if not text:
                        return (1, "")
                    return (0, text.lower())

                def step_sort_key(value: str) -> tuple[int, str]:
                    text = (value or "").strip()
                    if not text:
                        return (1, "")
                    try:
                        number = int(text)
                    except ValueError:
                        return (0, text.lower())
                    return (0, f"{number:010d}")

                machine_totals = {
                    machine_key: machine_total(pins_dict)
                    for machine_key, pins_dict in nested.items()
                }
                if machine_totals:
                    m_min = min(machine_totals.values())
                    m_max = max(machine_totals.values())
                else:
                    m_min = m_max = 0

                for machine, pins in sorted(nested.items(), key=lambda kv: label_sort_key(kv[0])):
                    m_cnt = machine_total(pins)
                    m_item = QTreeWidgetItem([machine or '(brak)', str(m_cnt)])
                    m_item.setData(0, Qt.UserRole, ('machine', machine))
                    m_item.setTextAlignment(1, Qt.AlignCenter)
                    m_color = color_for(m_cnt, m_min, m_max)
                    m_item.setBackground(0, translucent(m_color, 70))
                    m_item.setBackground(1, m_color)
                    change_tree.addTopLevelItem(m_item)
                    pin_totals = {pin_key: pin_total(step_dict) for pin_key, step_dict in pins.items()}
                    if pin_totals:
                        p_min = min(pin_totals.values())
                        p_max = max(pin_totals.values())
                    else:
                        p_min = p_max = 0
                    for pin, steps in sorted(pins.items(), key=lambda kv: label_sort_key(kv[0])):
                        p_cnt = pin_total(steps)
                        p_label = pin or '(brak)'
                        p_it = QTreeWidgetItem([p_label, str(p_cnt)])
                        p_it.setData(0, Qt.UserRole, ('pin', machine, pin))
                        p_it.setTextAlignment(1, Qt.AlignCenter)
                        p_color = color_for(p_cnt, p_min, p_max)
                        p_it.setBackground(0, translucent(p_color, 60))
                        p_it.setBackground(1, p_color)
                        m_item.addChild(p_it)
                        step_totals = {
                            step_key: step_total(param_dict) for step_key, param_dict in steps.items()
                        }
                        if step_totals:
                            s_min = min(step_totals.values())
                            s_max = max(step_totals.values())
                        else:
                            s_min = s_max = 0
                        for step_key, params_dict in sorted(
                            steps.items(), key=lambda kv: step_sort_key(kv[0])
                        ):
                            s_cnt = step_total(params_dict)
                            s_label = f"Step {step_key}" if step_key else '(brak)'
                            s_it = QTreeWidgetItem([s_label, str(s_cnt)])
                            s_it.setData(0, Qt.UserRole, ('step', machine, step_key))
                            s_it.setTextAlignment(1, Qt.AlignCenter)
                            s_color = color_for(s_cnt, s_min, s_max)
                            s_it.setBackground(0, translucent(s_color, 50))
                            s_it.setBackground(1, s_color)
                            p_it.addChild(s_it)
                            param_values = list(params_dict.values())
                            if param_values:
                                prm_min = min(param_values)
                                prm_max = max(param_values)
                            else:
                                prm_min = prm_max = 0
                            for name, cnt in sorted(
                                params_dict.items(), key=lambda kv: label_sort_key(kv[0])
                            ):
                                n_it = QTreeWidgetItem([name, str(cnt)])
                                n_it.setData(
                                    0,
                                    Qt.UserRole,
                                    ('param', machine, pin, step_key, name),
                                )
                                n_it.setTextAlignment(1, Qt.AlignCenter)
                                n_color = color_for(cnt, prm_min, prm_max)
                                n_it.setBackground(0, translucent(n_color, 40))
                                n_it.setBackground(1, n_color)
                                s_it.addChild(n_it)
                try:
                    change_tree.blockSignals(False)
                except Exception:
                    pass
                try:
                    change_tree.collapseAll()
                except Exception:
                    pass
            except Exception:
                pass

    def _on_top_issue_click(self, item, col):
            try:
                data = item.data(0, Qt.UserRole)
                if not data:
                    return
                kind = data[0]
                if kind == 'combo':
                    _, mach, pin, step, par = data
                    if mach:
                        self._set_combo(self.f_machine, mach)
                    if pin:
                        self._set_combo(self.f_pin, pin)
                    if step:
                        self._set_combo(self.f_step, str(step))
                    if par:
                        self._set_combo(self.f_param, par)
                elif kind == 'machine':
                    self._set_combo(self.f_machine, data[1])
                elif kind == 'pin':
                    _, mach, pin = data
                    self._set_combo(self.f_machine, mach)
                    if pin:
                        self._set_combo(self.f_pin, pin)
                elif kind == 'step':
                    _, mach, st = data
                    self._set_combo(self.f_machine, mach)
                    if st:
                        self._set_combo(self.f_step, str(st))
                elif kind == 'param':
                    _, mach, pin, st, par = data
                    if mach:
                        self._set_combo(self.f_machine, mach)
                    if pin:
                        self._set_combo(self.f_pin, pin)
                    if st:
                        self._set_combo(self.f_step, str(st))
                    if par:
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
                    if pin:
                        self._set_combo(self.f_pin, pin)
                elif kind == 'step':
                    _, mach, st = data
                    self._set_combo(self.f_machine, mach)
                    if st:
                        self._set_combo(self.f_step, str(st))
                elif kind == 'param':
                    _, mach, pin, st, par = data
                    if mach:
                        self._set_combo(self.f_machine, mach)
                    if pin:
                        self._set_combo(self.f_pin, pin)
                    if st:
                        self._set_combo(self.f_step, str(st))
                    if par:
                        self._set_combo(self.f_param, par)
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
            machines = {e.get('machine', '') for e in rows if e.get('machine')}
            olds = {e.get('old_program', '') for e in rows if e.get('old_program')}
            news = {e.get('new_program', '') for e in rows if e.get('new_program')}

            self._set_combo_items(self.pg_f_machine, machines)
            self._set_combo_items(self.pg_f_old, olds)
            self._set_combo_items(self.pg_f_new, news)

    def _populate_trend_filters(self):
            rows = getattr(self, 'found_files', [])
            machines = {f.machine for f in rows if f.machine}
            try:
                self._log(f"[Trends] _populate_trend_filters: machines={len(machines)}")
            except Exception:
                pass
            self._set_combo_items(self.t_f_machine, machines)

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
                    nok_rows = getattr(self, 'intranet_nok_rows', getattr(self, 'intranet_rows', []))
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

    def _export_index_csv(self):
            rows = getattr(self, 'index_filtered_rows', getattr(self, 'index_events', []))
            if not rows:
                QMessageBox.information(self, "Brak danych", "Brak wierszy do eksportu.")
                return
            path, _ = QFileDialog.getSaveFileName(self, "Zapisz CSV", "zmiany_parametrow_stolu.csv", "CSV Files (*.csv)")
            if not path:
                return
            headers = ["Data", "Czas", "Maszyna", "Program", "Tabela", "Step"] + INDEX_PARAM_DISPLAY_ORDER
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    w = csv.writer(f, delimiter=';')
                    w.writerow(headers)
                    for e in rows:
                        if e.get('type') != 'index_change':
                            continue
                        row = [
                            e['dt'].strftime('%Y-%m-%d'),
                            e['dt'].strftime('%H:%M:%S'),
                            e['machine'],
                            e['program'],
                            e['table'],
                            e['step'],
                        ]
                        row += [e['cols'].get(name, "") for name in INDEX_PARAM_DISPLAY_ORDER]
                        w.writerow(row)
                self._log(f"[Export] Zapisano CSV: {path}")
            except Exception as ex:
                QMessageBox.critical(self, "Błąd eksportu", str(ex))

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

    def _export_param_card_csv(self):
            snaps = list(getattr(self, 'current_param_card_rows', []))
            if not snaps:
                QMessageBox.information(
                    self,
                    "Brak danych",
                    "Wybierz datę, godzinę i maszynę karty parametrów.",
                )
                return
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Zapisz CSV",
                "karta_parametrow.csv",
                "CSV Files (*.csv)",
            )
            if not path:
                return
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    w = csv.writer(f, delimiter=';')
                    first = snaps[0]
                    try:
                        date_txt = first.dt.strftime('%Y-%m-%d')
                        time_txt = first.dt.strftime('%H:%M:%S')
                    except Exception:
                        date_txt = str(getattr(first, 'dt', ''))
                        time_txt = ''
                    machine = first.machine or ''
                    programs = sorted({snap.program for snap in snaps if getattr(snap, 'program', '')})
                    tables = sorted({snap.table for snap in snaps if getattr(snap, 'table', '')})
                    pins = sorted({snap.pin for snap in snaps if getattr(snap, 'pin', '')})
                    steps = sorted({snap.step for snap in snaps if getattr(snap, 'step', None) is not None})
                    paths = sorted({snap.path for snap in snaps if getattr(snap, 'path', '')})
                    w.writerow(["Data", date_txt, "Czas", time_txt])
                    w.writerow(["Maszyna", machine, "Migawek", len(snaps)])
                    w.writerow([
                        "Programy",
                        ", ".join(programs) if programs else '-',
                    ])
                    w.writerow([
                        "Tabele",
                        ", ".join(tables) if tables else '-',
                    ])
                    w.writerow(["Piny", len(pins), "Stepy", len(steps)])
                    if paths:
                        if len(paths) == 1:
                            w.writerow(["Plik", paths[0]])
                        else:
                            w.writerow(["Pliki", len(paths), "Przykład", paths[0]])
                    w.writerow([])
                    value_names = list(getattr(self, 'param_card_value_names', list(PARAM_DISPLAY_ORDER)))
                    csv_headers = ["Program", "Tabela", "Pin", "Step"] + value_names
                    w.writerow(csv_headers)
                    try:
                        sorted_snaps = sorted(
                            snaps,
                            key=lambda s: (
                                getattr(s, 'program', '') or '',
                                getattr(s, 'table', '') or '',
                                getattr(s, 'pin', '') or '',
                                getattr(s, 'step', -1) if getattr(s, 'step', None) is not None else -1,
                            ),
                        )
                    except Exception:
                        sorted_snaps = snaps
                    for snap in sorted_snaps:
                        program = snap.program or '-'
                        table_name = snap.table or '-'
                        pin = snap.pin or '-'
                        step_val = snap.step if snap.step is not None else '-'
                        step_txt = str(step_val)
                        row = [program, table_name, pin, step_txt]
                        for name in value_names:
                            row.append(self._param_card_cell_text(snap, name))
                        w.writerow(row)
                self._log(f"[Export] Zapisano kartę parametrów CSV: {path}")
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

__all__ = ['MainWindowHandlers']
