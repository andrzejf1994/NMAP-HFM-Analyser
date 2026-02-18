"""Application entrypoint for the HFM Analyzer GUI."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor, QPalette, QIcon
from PyQt5.QtWidgets import QApplication

from hfm_analyzer.constants import APP_NAME, APP_ORG, DEFAULT_PATH_H66_2
from hfm_analyzer.gui import ModernMainWindow, NetworkCheckDialog
from hfm_analyzer.utils import network_path_available


def ensure_base_path(settings: QSettings) -> bool:
    """Ensure that a valid base path is configured in settings."""

    base_path = settings.value("base_path", "", type=str)
    if not base_path:
        settings.setValue("base_path", DEFAULT_PATH_H66_2)
        base_path = DEFAULT_PATH_H66_2

    if network_path_available(base_path):
        try:
            settings.setValue("offline_cache_mode", False)
        except Exception:
            pass
        return True

    try:
        if settings.value("offline_cache_mode", False, type=bool):
            return True
    except Exception:
        pass

    dialog = NetworkCheckDialog(settings)
    result = dialog.exec_()
    try:
        if settings.value("offline_cache_mode", False, type=bool):
            return True
    except Exception:
        pass
    new_path = settings.value("base_path", "", type=str)
    return result == dialog.Accepted and network_path_available(new_path)


def apply_fusion_palette(app: QApplication) -> None:
    """Apply a bright Fusion palette to the Qt application."""

    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QPalette.Window, QColor(246, 247, 251))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(247, 249, 252))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ToolTipText, QColor(33, 37, 41))
    palette.setColor(QPalette.Text, QColor(33, 37, 41))
    palette.setColor(QPalette.Button, QColor(255, 255, 255))
    palette.setColor(QPalette.ButtonText, QColor(33, 37, 41))
    palette.setColor(QPalette.Highlight, QColor(52, 152, 219))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)


def _icon_search_paths() -> list[Path]:
    """Return candidate locations for the application icon."""

    candidates: list[Path] = []

    # When packaged with PyInstaller ``_MEIPASS`` points to the temporary bundle
    # directory that contains our resources.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        base = Path(meipass)
        candidates.append(base / "icon.ico")
        candidates.append(base / "resources" / "icon.ico")

    here = Path(__file__).resolve().parent
    candidates.append(here / "icon.ico")
    candidates.append(here.parent / "icon.ico")

    try:
        executable_dir = Path(sys.argv[0]).resolve().parent
        candidates.append(executable_dir / "icon.ico")
    except Exception:
        pass

    try:
        candidates.append(Path.cwd() / "icon.ico")
    except Exception:
        pass

    ordered_unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except Exception:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered_unique.append(resolved)
    return ordered_unique


def _load_app_icon() -> QIcon | None:
    """Return the application icon if it is available on disk."""

    for path in _icon_search_paths():
        if path.is_file():
            return QIcon(str(path))
    logging.warning("Application icon not found; continuing without a custom icon")
    return None


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    try:
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

    icon = _load_app_icon()
    if icon and not icon.isNull():
        app.setWindowIcon(icon)

    apply_fusion_palette(app)

    settings = QSettings()
    if not ensure_base_path(settings):
        sys.exit(0)

    window = ModernMainWindow(settings)
    if icon and not icon.isNull():
        window.setWindowIcon(icon)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
