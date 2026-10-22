"""
System tray icon and context menu for Nomi Windows.
Features a clean vector soundwave emblem and ChatGPT dark menu styling.
"""

import os
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QRectF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu

_ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets")).replace("\\", "/")
ICON_GEAR = f"{_ASSETS_DIR}/gear.svg"
ICON_CLOCK = f"{_ASSETS_DIR}/clock.svg"
ICON_BOOK = f"{_ASSETS_DIR}/book.svg"
ICON_CHECKLIST = f"{_ASSETS_DIR}/checklist.svg"


def create_tray_pixmap(is_active: bool = True) -> QPixmap:
    """Generate a crisp minimalist vector soundwave app icon programmatically."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Dark rounded container badge
    bg_color = QColor(28, 28, 28)
    border_color = QColor(56, 56, 56) if is_active else QColor(40, 40, 40)
    painter.setBrush(QBrush(bg_color))
    painter.setPen(QPen(border_color, 2))
    painter.drawRoundedRect(4, 4, 56, 56, 16, 16)

    # Minimalist vector soundwave bars
    bar_color = QColor(255, 255, 255) if is_active else QColor(110, 110, 110)
    painter.setBrush(QBrush(bar_color))
    painter.setPen(Qt.PenStyle.NoPen)

    bars = [
        (15.0, 27.0, 4.5, 10.0),
        (23.0, 20.0, 4.5, 24.0),
        (31.0, 14.0, 4.5, 36.0),
        (39.0, 20.0, 4.5, 24.0),
        (47.0, 27.0, 4.5, 10.0),
    ]
    for x, y, w, h in bars:
        r = w / 2.0
        painter.drawRoundedRect(QRectF(x, y, w, h), r, r)

    painter.end()
    return pixmap


class SystemTrayManager(QObject):
    """Manages the Windows taskbar system tray integration."""

    open_settings_requested = pyqtSignal()
    open_notes_requested = pyqtSignal()
    open_tasks_requested = pyqtSignal()
    open_history_requested = pyqtSignal()
    toggle_hotkeys_requested = pyqtSignal(bool)
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(parent)
        self.is_active = True
        self.init_ui()

    def init_ui(self):
        icon = QIcon(create_tray_pixmap(self.is_active))
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Nomi — Personal Context Assistant")

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #212121;
                color: #ECECEC;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: #2F2F2F;
                color: #FFFFFF;
            }
            QMenu::item:disabled {
                color: #6E6E6E;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2E2E2E;
                margin: 4px 6px;
            }
        """)

        title_action = menu.addAction("Nomi Context Assistant")
        title_action.setEnabled(False)
        menu.addSeparator()

        self.action_notes = menu.addAction(QIcon(ICON_BOOK), "Smart Lecture Notes...")
        self.action_notes.triggered.connect(self.open_notes_requested.emit)

        self.action_tasks = menu.addAction(QIcon(ICON_CHECKLIST), "Tasks & Calendar...")
        self.action_tasks.triggered.connect(self.open_tasks_requested.emit)

        self.action_history = menu.addAction(QIcon(ICON_CLOCK), "Dictation History...")
        self.action_history.triggered.connect(self.open_history_requested.emit)

        menu.addSeparator()

        self.action_settings = menu.addAction(QIcon(ICON_GEAR), "Settings & AI Models...")
        self.action_settings.triggered.connect(self.open_settings_requested.emit)

        menu.addSeparator()

        self.action_pause = menu.addAction("Pause Hotkeys")
        self.action_pause.setCheckable(True)
        self.action_pause.toggled.connect(self._on_pause_toggled)

        menu.addSeparator()

        self.action_quit = menu.addAction("Quit Nomi")
        self.action_quit.triggered.connect(self.quit_requested.emit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_pause_toggled(self, checked: bool):
        self.is_active = not checked
        self.tray_icon.setIcon(QIcon(create_tray_pixmap(self.is_active)))
        self.toggle_hotkeys_requested.emit(self.is_active)
        status_text = "Nomi (Active)" if self.is_active else "Nomi (Paused)"
        self.tray_icon.setToolTip(status_text)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_settings_requested.emit()

    def show_notification(self, title: str, message: str):
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 2000)
