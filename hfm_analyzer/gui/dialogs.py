"""Dialog implementations for the GUI package."""

from __future__ import annotations

from PyQt5.QtCore import QSettings, Qt, QObject, pyqtSignal, QThread, QStandardPaths
import os
import sqlite3
from datetime import date, datetime, timedelta
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from hfm_analyzer.constants import (
    DEFAULT_INTRANET_EXCLUDES,
    DEFAULT_PATH_EVO,
    DEFAULT_PATH_H66_2,
    default_cycle_time_sec,
)
from hfm_analyzer.utils import network_path_available, sqlite_cache_available
from hfm_analyzer.storage.runtime_sqlite_cache import RuntimeSQLiteCache
from hfm_analyzer.gui.utils import _maybe_offer_drive_mapping


class _PathCheckWorker(QObject):
    finished = pyqtSignal(bool)

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path

    def run(self) -> None:
        available = network_path_available(self._path)
        self.finished.emit(available)

class SettingsDialog(QDialog):
    """Application preferences dialog."""

    def __init__(
        self,
        settings: QSettings,
        parent: QWidget | None = None,
        runtime_db_path: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ustawienia")
        self.settings = settings

        initial_path = self.settings.value("base_path", "", type=str)
        self._block_path_signal = True
        self.path_edit = QLineEdit(initial_path)
        self._block_path_signal = False
        self._pending_display_name = self.settings.value(
            "base_path_display_name", "", type=str
        ) or ""
        self._last_checked_path = self.path_edit.text().strip()
        self.path_edit.textChanged.connect(self._on_path_text_changed)

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
        self._cycle_time_by_line_local: dict[int, int] = {}
        self._current_cycle_line_id = int(self.line_id_spin.value())
        self.cycle_time_spin = QSpinBox()
        self.cycle_time_spin.setRange(1, 3600)
        self.cycle_time_spin.setSuffix(" s")
        self.cycle_time_spin.setValue(self._cycle_time_for_line(self._current_cycle_line_id))
        self.line_id_spin.valueChanged.connect(self._on_line_id_changed)

        excl_val = self.settings.value("intranet_exclude_machines", DEFAULT_INTRANET_EXCLUDES, type=str)
        if not excl_val:
            excl_val = DEFAULT_INTRANET_EXCLUDES
        self.intra_excl_edit = QLineEdit(excl_val)

        self.intra_days_back_spin = QSpinBox()
        self.intra_days_back_spin.setRange(0, 30)
        self.intra_days_back_spin.setValue(self.settings.value("intranet_days_back", 1, type=int))

        self.intra_timeout_spin = QSpinBox()
        self.intra_timeout_spin.setRange(1, 3600)
        self.intra_timeout_spin.setSuffix(" s")
        self.intra_timeout_spin.setValue(self.settings.value("intranet_timeout_per_day_sec", 8, type=int))

        db_path = (runtime_db_path or "").strip()
        self.db_path_label = QLabel(db_path or "(brak)")
        self.db_path_label.setWordWrap(True)
        try:
            self.db_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        except Exception:
            pass

        self.persistent_check = QCheckBox("Używaj trwałej bazy danych (nieusuwanej)")
        self.persistent_check.setChecked(self.settings.value("cache_persistent", False, type=bool))
        self.cache_path_edit = QLineEdit(self.settings.value("cache_path", "", type=str))
        self.cache_path_edit.setPlaceholderText("Wybierz lokalizację pliku .sqlite")
        self.cache_browse_btn = QPushButton("Wybierz...")
        self.cache_browse_btn.clicked.connect(self._browse_cache_path)
        self.persistent_check.toggled.connect(self._on_persistent_toggled)
        self.offline_check = QCheckBox("Tryb offline (baza)")
        self.offline_check.setChecked(self.settings.value("offline_cache_mode", False, type=bool))
        self.offline_check.toggled.connect(self._on_offline_toggled)
        self.cache_keep_days_spin = QSpinBox()
        self.cache_keep_days_spin.setRange(0, 3650)
        self.cache_keep_days_spin.setValue(self.settings.value("cache_keep_days", 30, type=int))
        self.cache_clear_btn = QPushButton("Czyść bazę")
        self.cache_clear_btn.clicked.connect(self._clear_cache)

        browse_btn = QPushButton("Przeglądaj")
        browse_btn.clicked.connect(self._browse)

        preset_evo = QPushButton("Ustaw EVO")
        preset_evo.clicked.connect(lambda: self._set_path(DEFAULT_PATH_EVO, 424, "BSG EVO"))
        preset_h66 = QPushButton("Ustaw H66 2")
        preset_h66.clicked.connect(
            lambda: self._set_path(DEFAULT_PATH_H66_2, 436, "BSG H66 2")
        )
        preset_offline = QPushButton("Tryb offline (baza)")
        preset_offline.clicked.connect(self._set_offline_preset)

        form = QFormLayout()
        row = QHBoxLayout()
        row.addWidget(self.path_edit)
        row.addWidget(browse_btn)
        form.addRow("Katalog bazowy:", row)

        form.addRow("Wątki analizy (0=auto):", self.workers_spin)
        form.addRow("Próg dużej zmiany (%):", self.threshold_spin)
        form.addRow("ID linii (intranet):", self.line_id_spin)
        form.addRow("Czas cyklu maszyny (max):", self.cycle_time_spin)
        form.addRow("Dni wstecz (Intranet):", self.intra_days_back_spin)
        form.addRow("Timeout na dzień (Intranet):", self.intra_timeout_spin)
        form.addRow("Wyklucz maszyny (SAP):", self.intra_excl_edit)
        form.addRow("Baza danych (SQLite):", self.db_path_label)
        form.addRow(self.persistent_check)
        form.addRow(self.offline_check)
        cache_row = QHBoxLayout()
        cache_row.addWidget(self.cache_path_edit)
        cache_row.addWidget(self.cache_browse_btn)
        form.addRow("Lokalizacja bazy trwałej:", cache_row)
        clear_row = QHBoxLayout()
        clear_row.addWidget(self.cache_keep_days_spin)
        clear_row.addWidget(self.cache_clear_btn)
        form.addRow("Pozostaw dane (dni):", clear_row)

        presets = QHBoxLayout()
        presets.addWidget(preset_evo)
        presets.addWidget(preset_h66)
        presets.addWidget(preset_offline)
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
        self._on_persistent_toggled(self.persistent_check.isChecked())
        self._on_offline_toggled(self.offline_check.isChecked())

    def _on_path_text_changed(self, _: str) -> None:
        if not getattr(self, "_block_path_signal", False):
            self._pending_display_name = ""
            self._last_checked_path = ""

    def _cycle_time_key(self, line_id: int) -> str:
        return f"cycle_time_sec_line_{int(line_id)}"

    def _cycle_time_for_line(self, line_id: int) -> int:
        key = self._cycle_time_key(line_id)
        return int(self.settings.value(key, default_cycle_time_sec(line_id), type=int))

    def _on_line_id_changed(self, value: int) -> None:
        prev_line_id = int(getattr(self, "_current_cycle_line_id", value))
        self._cycle_time_by_line_local[prev_line_id] = int(self.cycle_time_spin.value())
        self._current_cycle_line_id = int(value)
        next_value = self._cycle_time_by_line_local.get(
            int(value),
            self._cycle_time_for_line(int(value)),
        )
        self.cycle_time_spin.setValue(int(next_value))

    def _apply_path(self, path: str, display_name: str | None = None) -> str:
        mapped = _maybe_offer_drive_mapping(self, path).strip()
        self._pending_display_name = display_name or ""
        self._block_path_signal = True
        self.path_edit.setText(mapped)
        self._block_path_signal = False
        self._last_checked_path = mapped
        return mapped

    def _set_path(
        self, path: str, line_id: int | None = None, display_name: str | None = None
    ) -> None:
        self._apply_path(path, display_name)
        if line_id is not None:
            self.line_id_spin.setValue(line_id)

    def _browse(self) -> None:
        new_path = QFileDialog.getExistingDirectory(self, "Wskaż katalog bazowy z backupami")
        if new_path:
            self._apply_path(new_path)

    def _browse_cache_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Wybierz baze SQLite",
            self.cache_path_edit.text().strip() or self._default_cache_path(),
            "SQLite (*.sqlite *.db *.sqlite3);;Wszystkie pliki (*.*)",
        )
        if path:
            try:
                self.persistent_check.setChecked(True)
            except Exception:
                pass
            self.cache_path_edit.setText(path)

    def _default_cache_path(self) -> str:
        base = ""
        try:
            base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        except Exception:
            base = ""
        if not base:
            try:
                base = os.path.join(os.path.expanduser("~"), "HFM Analyzer")
            except Exception:
                base = ""
        if base:
            try:
                os.makedirs(base, exist_ok=True)
            except Exception:
                pass
            return os.path.join(base, "hfm_analyzer_cache.sqlite")
        return "hfm_analyzer_cache.sqlite"

    def _set_offline_preset(self) -> None:
        self.offline_check.setChecked(True)
        self.persistent_check.setChecked(True)
        self._on_persistent_toggled(True)
        if not self.cache_path_edit.text().strip():
            self.cache_path_edit.setText(self._default_cache_path())
            QMessageBox.information(
                self,
                "Tryb offline",
                "Aby użyć trybu offline, wskaż plik trwałej bazy danych.\n"
                "Domyślna lokalizacja została ustawiona – możesz ją zmienić.",
            )

    def _on_persistent_toggled(self, checked: bool) -> None:
        self.cache_path_edit.setEnabled(checked)
        self.cache_browse_btn.setEnabled(checked)
        self.cache_keep_days_spin.setEnabled(checked)
        self.cache_clear_btn.setEnabled(checked)
        try:
            self.offline_check.setEnabled(checked)
            if not checked:
                self.offline_check.setChecked(False)
        except Exception:
            pass

    def _on_offline_toggled(self, checked: bool) -> None:
        if not checked:
            return
        if not self.persistent_check.isChecked():
            self.persistent_check.setChecked(True)
        if not self.cache_path_edit.text().strip():
            self.cache_path_edit.setText(self._default_cache_path())
            QMessageBox.information(
                self,
                "Tryb offline",
                "Aby użyć trybu offline, wskaż plik trwałej bazy danych.\n"
                "Domyślna lokalizacja została ustawiona – możesz ją zmienić.",
            )

    def _clear_cache(self) -> None:
        if not self.persistent_check.isChecked():
            QMessageBox.information(
                self,
                "Brak trwałej bazy",
                "Włącz trwałą bazę danych, aby móc czyścić zapisane dane.",
            )
            return
        path = self.cache_path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "Brak ścieżki", "Podaj lokalizację bazy SQLite.")
            return
        keep_days = int(self.cache_keep_days_spin.value())
        cutoff_date = date.today() - timedelta(days=keep_days)
        cutoff_dt = datetime.combine(cutoff_date, datetime.min.time())
        msg = (
            "Zostaną usunięte dane starsze niż: "
            f"{cutoff_date.isoformat()} (dziś - {keep_days} dni).\n"
            "Czy na pewno kontynuować?"
        )
        if QMessageBox.question(self, "Potwierdź czyszczenie", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            results = RuntimeSQLiteCache.purge_older_than(path, cutoff_dt)
            summary = ", ".join(
                f"{key}={value}" for key, value in results.items() if value
            )
            if not summary:
                summary = "Brak danych do usunięcia."
            QMessageBox.information(self, "Czyszczenie zakończone", summary)
        except Exception as exc:
            QMessageBox.critical(self, "Błąd czyszczenia", str(exc))

    def _accept(self) -> None:
        current = self.path_edit.text().strip()
        if current and current != self._last_checked_path:
            mapped = _maybe_offer_drive_mapping(self, current).strip()
            if mapped != current:
                self._block_path_signal = True
                self.path_edit.setText(mapped)
                self._block_path_signal = False
            current = mapped
            self._last_checked_path = current

        display_name = self._pending_display_name.strip() if current else ""
        self.settings.setValue("base_path", current)
        self.settings.setValue("base_path_display_name", display_name)
        self.settings.setValue("analysis_workers", int(self.workers_spin.value()))
        self.settings.setValue("large_change_threshold_pct", int(self.threshold_spin.value()))
        self.settings.setValue("intranet_line_id", int(self.line_id_spin.value()))
        self._cycle_time_by_line_local[int(self.line_id_spin.value())] = int(self.cycle_time_spin.value())
        for line_id, cycle_sec in self._cycle_time_by_line_local.items():
            self.settings.setValue(self._cycle_time_key(int(line_id)), int(cycle_sec))
        self.settings.setValue("intranet_exclude_machines", self.intra_excl_edit.text().strip())
        self.settings.setValue("intranet_days_back", int(self.intra_days_back_spin.value()))
        self.settings.setValue("intranet_timeout_per_day_sec", int(self.intra_timeout_spin.value()))
        persistent = bool(self.persistent_check.isChecked())
        cache_path = self.cache_path_edit.text().strip()
        if persistent and not cache_path:
            QMessageBox.warning(
                self,
                "Brak ścieżki",
                "Podaj lokalizację pliku bazy SQLite lub wyłącz tryb trwałej bazy.",
            )
            return
        if persistent and cache_path:
            try:
                cache_dir = os.path.dirname(cache_path)
                if cache_dir:
                    os.makedirs(cache_dir, exist_ok=True)
                if not os.path.exists(cache_path):
                    conn = sqlite3.connect(cache_path)
                    conn.close()
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "Blad bazy",
                    f"Nie mozna utworzyc pliku bazy: {exc}",
                )
                return
        self.settings.setValue("cache_persistent", persistent)
        self.settings.setValue("cache_path", cache_path)
        self.settings.setValue("cache_keep_days", int(self.cache_keep_days_spin.value()))
        offline = bool(self.offline_check.isChecked())
        if offline and (not persistent or not cache_path):
            QMessageBox.warning(
                self,
                "Tryb offline",
                "Aby użyć trybu offline, włącz trwałą bazę i wskaż jej plik.",
            )
            return
        self.settings.setValue("offline_cache_mode", offline)
        self.accept()

class NetworkCheckDialog(QDialog):
    """Dialog displayed when the network path is unavailable."""

    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Brak dostępu do katalogu sieciowego")
        self.settings = settings
        self._current_display_name = (
            self.settings.value("base_path_display_name", "", type=str) or ""
        )

        info = QLabel(
            "Nie udało się uzyskać dostępu do wskazanego katalogu sieciowego.\n"
            "Możesz spróbować ponownie, wybrać inną ścieżkę lub użyć jednego z presetów."
        )
        info.setWordWrap(True)

        self.path_label = QLabel()
        self.path_label.setWordWrap(True)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.retry_btn = QPushButton("Spróbuj ponownie")
        self.retry_btn.clicked.connect(self._on_retry)

        self.quit_btn = QPushButton("Zamknij")
        self.quit_btn.clicked.connect(self.reject)

        self.choose_btn = QPushButton("Wskaż katalog")
        self.choose_btn.clicked.connect(self._choose_path)

        self.offline_btn = QPushButton("Tryb offline (baza)")
        self.offline_btn.clicked.connect(self._use_offline_cache)
        self.offline_btn.setEnabled(self._offline_cache_available())

        self.preset_evo = QPushButton("Ustaw EVO")
        self.preset_evo.clicked.connect(lambda: self._set_path(DEFAULT_PATH_EVO, "BSG EVO"))
        self.preset_h66 = QPushButton("Ustaw H66 2")
        self.preset_h66.clicked.connect(
            lambda: self._set_path(DEFAULT_PATH_H66_2, "BSG H66 2")
        )

        row1 = QHBoxLayout()
        row1.addWidget(self.retry_btn)
        row1.addWidget(self.quit_btn)

        row2 = QHBoxLayout()
        row2.addWidget(self.choose_btn)
        row2.addWidget(self.offline_btn)

        row3 = QHBoxLayout()
        row3.addWidget(self.preset_evo)
        row3.addWidget(self.preset_h66)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addWidget(self.path_label)
        layout.addWidget(self.status_label)
        layout.addLayout(row2)
        layout.addLayout(row3)
        layout.addStretch(1)
        layout.addLayout(row1)
        self.setLayout(layout)

        self._apply_styles()
        self._update_label()
        self._check_thread = None

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QPushButton { padding: 6px 10px; border-radius: 6px; }
            QPushButton:hover { background:#ecf0f1; }
            """
        )

    def _update_label(self) -> None:
        current_path = self.settings.value("base_path", "", type=str)
        self.path_label.setText(f"Aktualna ścieżka: <b>{current_path or '(brak)'}" + "</b>")

    def _choose_path(self) -> None:
        new_path = QFileDialog.getExistingDirectory(self, "Wskaż katalog bazowy z backupami")
        if new_path:
            self._set_path(new_path)

    def _set_path(self, path: str, display_name: str | None = None) -> None:
        mapped = _maybe_offer_drive_mapping(self, path, fast=True).strip()
        try:
            self.settings.setValue("offline_cache_mode", False)
        except Exception:
            pass
        self.settings.setValue("base_path", mapped)
        if mapped:
            self._current_display_name = (display_name or "").strip()
        else:
            self._current_display_name = ""
        self.settings.setValue("base_path_display_name", self._current_display_name)
        self._update_label()
        self._start_path_check()

    def _on_retry(self) -> None:
        self._start_path_check()

    def _set_controls_enabled(self, enabled: bool) -> None:
        for btn in (
            self.retry_btn,
            self.choose_btn,
            self.offline_btn,
            self.preset_evo,
            self.preset_h66,
        ):
            try:
                btn.setEnabled(enabled)
            except Exception:
                pass

    def _start_path_check(self) -> None:
        try:
            if self._check_thread is not None and self._check_thread.isRunning():
                return
        except Exception:
            pass
        base_path = self.settings.value("base_path", "", type=str)
        if not base_path:
            QMessageBox.warning(self, "Brak ścieżki", "Wybierz katalog lub preset.")
            return
        self.status_label.setText("Sprawdzanie dostępu do katalogu...")
        self._set_controls_enabled(False)
        thread = QThread(self)
        worker = _PathCheckWorker(base_path)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_path_check_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._check_thread = thread
        thread.start()

    def _on_path_check_finished(self, available: bool) -> None:
        self._check_thread = None
        self._set_controls_enabled(True)
        self.status_label.setText("")
        if available:
            try:
                self.settings.setValue("offline_cache_mode", False)
            except Exception:
                pass
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Nadal brak dostępu",
                "Ścieżka nadal jest niedostępna. Sprawdź połączenie lub wybierz inną ścieżkę.",
            )

    def _offline_cache_available(self) -> bool:
        try:
            persistent = bool(self.settings.value("cache_persistent", False, type=bool))
        except Exception:
            persistent = False
        if not persistent:
            return False
        path = self.settings.value("cache_path", "", type=str)
        path = (path or "").strip()
        if not path or not os.path.exists(path):
            return False
        try:
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            for table in (
                "param_snapshots",
                "index_snapshots",
                "grip_snapshots",
                "nest_snapshots",
                "hairpin_snapshots",
            ):
                row = cur.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
                if row:
                    conn.close()
                    return True
            conn.close()
        except Exception:
            return False
        return False

    def _use_offline_cache(self) -> None:
        if not self._offline_cache_available():
            QMessageBox.warning(
                self,
                "Brak danych",
                "Trwała baza danych nie jest dostępna lub nie zawiera danych.",
            )
            return
        try:
            self.settings.setValue("offline_cache_mode", True)
        except Exception:
            pass
        self.accept()



class CacheCheckDialog(QDialog):
    """Dialog displayed when the offline cache database is unavailable."""

    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Brak dostepu do bazy offline")
        self.settings = settings

        info = QLabel(
            "Nie udalo sie uzyskac dostepu do wybranej bazy danych trybu offline.\n"
            "Mozesz sprobowac ponownie lub wskazac inna baze SQLite."
        )
        info.setWordWrap(True)

        self.path_label = QLabel()
        self.path_label.setWordWrap(True)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.retry_btn = QPushButton("Sprobuj ponownie")
        self.retry_btn.clicked.connect(self._on_retry)

        self.quit_btn = QPushButton("Zamknij")
        self.quit_btn.clicked.connect(self.reject)

        self.choose_btn = QPushButton("Wybierz baze")
        self.choose_btn.clicked.connect(self._choose_cache)

        self.online_btn = QPushButton("Tryb online")
        self.online_btn.clicked.connect(self._use_online)

        row1 = QHBoxLayout()
        row1.addWidget(self.retry_btn)
        row1.addWidget(self.quit_btn)

        row2 = QHBoxLayout()
        row2.addWidget(self.choose_btn)
        row2.addWidget(self.online_btn)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addWidget(self.path_label)
        layout.addWidget(self.status_label)
        layout.addLayout(row2)
        layout.addStretch(1)
        layout.addLayout(row1)
        self.setLayout(layout)

        self._apply_styles()
        self._update_label()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QPushButton { padding: 6px 10px; border-radius: 6px; }
            QPushButton:hover { background:#ecf0f1; }
            """
        )

    def _update_label(self) -> None:
        current_path = self.settings.value("cache_path", "", type=str)
        self.path_label.setText(
            f"Aktualna baza: <b>{current_path or '(brak)'}" + "</b>"
        )

    def _cache_available(self, path: str | None = None) -> bool:
        try:
            persistent = bool(self.settings.value("cache_persistent", False, type=bool))
        except Exception:
            persistent = False
        if not persistent:
            return False
        cache_path = (path or self.settings.value("cache_path", "", type=str) or "").strip()
        return sqlite_cache_available(cache_path)

    def _on_retry(self) -> None:
        self.status_label.setText("Sprawdzanie dostepu do bazy...")
        if self._cache_available():
            self.accept()
        else:
            self.status_label.setText("Baza nadal jest niedostepna.")

    def _choose_cache(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz baze SQLite",
            self.settings.value("cache_path", "", type=str) or "",
            "SQLite (*.sqlite *.db *.sqlite3);;Wszystkie pliki (*.*)",
        )
        if not path:
            return
        if not self._cache_available(path):
            QMessageBox.warning(
                self,
                "Brak dostepu",
                "Nie udalo sie otworzyc wybranej bazy danych. Wybierz inna lokalizacje.",
            )
            return
        try:
            self.settings.setValue("cache_persistent", True)
            self.settings.setValue("cache_path", path)
            self.settings.setValue("offline_cache_mode", True)
        except Exception:
            pass
        self._update_label()
        self.accept()

    def _use_online(self) -> None:
        try:
            self.settings.setValue("offline_cache_mode", False)
        except Exception:
            pass
        self.accept()


__all__ = ['SettingsDialog', 'NetworkCheckDialog', 'CacheCheckDialog']
