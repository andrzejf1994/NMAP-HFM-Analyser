"""Application entrypoint for the HFM Analyzer GUI."""

from __future__ import annotations

import logging
import os
import sys

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication

from .constants import APP_NAME, APP_ORG, DEFAULT_PATH_H66_2
from .gui import ModernMainWindow, NetworkCheckDialog
from .utils import network_path_available


def ensure_base_path(settings: QSettings) -> bool:
    """Ensure that a valid base path is configured in settings."""

    base_path = settings.value("base_path", "", type=str)
    if not base_path:
        settings.setValue("base_path", DEFAULT_PATH_H66_2)
        base_path = DEFAULT_PATH_H66_2

    if network_path_available(base_path):
        return True

    dialog = NetworkCheckDialog(settings)
    result = dialog.exec_()
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


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

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
    apply_fusion_palette(app)

    settings = QSettings()
    if not ensure_base_path(settings):
        sys.exit(0)

    window = ModernMainWindow(settings)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
