"""
Reusable Modern ChatGPT Desktop Style Components for Nomi Windows.
Clean monochrome vector styling without emojis.
"""

from typing import Optional, List
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QIcon
from PyQt6.QtWidgets import (
    QWidget,
    QCheckBox,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)


class SwitchToggle(QCheckBox):
    """
    Sleek, modern ChatGPT / iOS style toggle switch with smooth animation.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(42, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._thumb_pos = 3.0

        self._anim = QPropertyAnimation(self, b"thumb_pos", self)
        self._anim.setDuration(140)
        self.toggled.connect(self._handle_toggled)

    @pyqtProperty(float)
    def thumb_pos(self) -> float:
        return self._thumb_pos

    @thumb_pos.setter
    def thumb_pos(self, pos: float):
        self._thumb_pos = pos
        self.update()

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._thumb_pos = 21.0 if checked else 3.0
        self.update()

    def _handle_toggled(self, checked: bool):
        self._anim.stop()
        self._anim.setEndValue(21.0 if checked else 3.0)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        # Background track: Blue when checked, neutral dark gray when unchecked
        track_color = QColor(37, 99, 235) if self.isChecked() else QColor(56, 56, 56)

        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)

        # Inner pure white knob
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(int(self._thumb_pos), 3, 18, 18)


class SettingsRow(QFrame):
    """
    A single row within a SettingsCard:
    [ Title + Description on Left ] --------- [ Interactive Control on Right ]
    """

    def __init__(
        self,
        title: str,
        description: str = "",
        control: Optional[QWidget] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("settingsRow")
        self.setStyleSheet("""
            QFrame#settingsRow {
                background: transparent;
                border: none;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        # Left Column: Title + Description
        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 13.5px; font-weight: 500; color: #FFFFFF;")
        text_col.addWidget(self.title_label)

        if description:
            self.desc_label = QLabel(description)
            self.desc_label.setStyleSheet("font-size: 12px; color: #9B9B9B; line-height: 1.4;")
            self.desc_label.setWordWrap(True)
            text_col.addWidget(self.desc_label)

        layout.addLayout(text_col, stretch=1)

        # Right Column: Control Widget
        self._control = control
        if control:
            layout.addWidget(control, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if isinstance(control, SwitchToggle):
                self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if isinstance(self._control, SwitchToggle) and event.button() == Qt.MouseButton.LeftButton:
            self._control.toggle()


class SettingsCard(QFrame):
    """
    Modern ChatGPT Desktop rounded settings card with thin 1px row dividers.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsCard")
        self.setStyleSheet("""
            QFrame#settingsCard {
                background-color: #282828;
                border: 1px solid #333333;
                border-radius: 10px;
            }
        """)

        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(0)
        self._rows: List[QWidget] = []

    def add_row(self, row: QWidget):
        if self._rows:
            divider = QFrame()
            divider.setFixedHeight(1)
            divider.setStyleSheet("background-color: #333333; border: none;")
            self.card_layout.addWidget(divider)

        self._rows.append(row)
        self.card_layout.addWidget(row)


class NavItemButton(QPushButton):
    """
    Sidebar Navigation Item with clean monochrome vector icon and rounded pill selection.
    """

    def __init__(self, text: str, icon_path: Optional[str] = None, parent=None):
        super().__init__(text.replace("&", "&&"), parent)
        if icon_path:
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(16, 16))
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 10px;
                padding-right: 12px;
                background-color: transparent;
                color: #B4B4B4;
                border: none;
                border-radius: 8px;
                font-size: 13.5px;
                font-weight: 500;
            }
            QPushButton:hover:!checked {
                background-color: #212121;
                color: #ECECEC;
            }
            QPushButton:checked {
                background-color: #2F2F2F;
                color: #FFFFFF;
                font-weight: 500;
            }
        """)
