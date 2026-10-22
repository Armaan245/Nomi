"""
Nomi for Windows — Main Application Entry Point.
A private, local-first alternative to Wispr Flow.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from app.controller import AppController
from app.ui.tray_icon import create_tray_pixmap


def main():
    # Enable high-DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("Nomi")
    app.setOrganizationName("Nomi")
    app.setWindowIcon(QIcon(create_tray_pixmap(True)))

    # Don't exit when settings window is closed; continue running in system tray
    app.setQuitOnLastWindowClosed(False)

    # Initialize controller and background services
    controller = AppController()

    print("=" * 60, flush=True)
    print(" Nomi Windows — Local AI Dictation Active", flush=True)
    print(" • Hold [Right Alt] (or tap [F8]) to talk into any application.", flush=True)
    print(" • Double-click the system tray icon for Settings & Models.", flush=True)
    print(" • Press [Esc] anytime to cancel active recording.", flush=True)
    print("=" * 60, flush=True)

    # Show notification on launch
    controller.tray.show_notification(
        "Nomi is Ready",
        "Hold Right Alt or tap F8 to dictate into any text field."
    )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
