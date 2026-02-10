"""Dialog implementations for the GUI package."""

from __future__ import annotations

from PyQt5.QtCore import QSettings, Qt, QObject, pyqtSignal, QThread
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
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from hfm_analyzer.constants import (
    DEFAULT_INTRANET_EXCLUDES,
    DEFAULT_PATH_EVO,
    DEFAULT_PATH_H66_2,
)
from hfm_analyzer.utils import network_path_available
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

        excl_val = self.settings.value("intranet_exclude_machines", DEFAULT_INTRANET_EXCLUDES, type=str)
        if not excl_val:
            excl_val = DEFAULT_INTRANET_EXCLUDES
        self.intra_excl_edit = QLineEdit(excl_val)

        self.intra_days_back_spin = QSpinBox()
        self.intra_days_back_spin.setRange(0, 30)
        self.intra_days_back_spin.setValue(self.settings.value("intranet_days_back", 1, type=int))

        db_path = (runtime_db_path or "").strip()
        self.db_path_label = QLabel(db_path or "(brak)")
        self.db_path_label.setWordWrap(True)
        try:
            self.db_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        except Exception:
            pass

        browse_btn = QPushButton("Przeglądaj")
        browse_btn.clicked.connect(self._browse)

        preset_evo = QPushButton("Ustaw EVO")
        preset_evo.clicked.connect(lambda: self._set_path(DEFAULT_PATH_EVO, 424, "BSG EVO"))
        preset_h66 = QPushButton("Ustaw H66 2")
        preset_h66.clicked.connect(
            lambda: self._set_path(DEFAULT_PATH_H66_2, 436, "BSG H66 2")
        )

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
        form.addRow("Baza danych (SQLite):", self.db_path_label)

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

    def _on_path_text_changed(self, _: str) -> None:
        if not getattr(self, "_block_path_signal", False):
            self._pending_display_name = ""
            self._last_checked_path = ""

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
        self.settings.setValue("intranet_exclude_machines", self.intra_excl_edit.text().strip())
        self.settings.setValue("intranet_days_back", int(self.intra_days_back_spin.value()))
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
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Nadal brak dostępu",
                "Ścieżka nadal jest niedostępna. Sprawdź połączenie lub wybierz inną ścieżkę.",
            )

__all__ = ['SettingsDialog', 'NetworkCheckDialog']
