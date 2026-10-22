"""
Floating / Docked Top Notch Pill Overlay for FreeFlow Windows.
Matches the minimal, sleek macOS/Wispr Flow top notch design with pure white waveform.
"""

import os
import math
from typing import List, Optional
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRectF, pyqtSlot
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient
from PyQt6.QtWidgets import (
    QWidget,
    QApplication,
    QMenu,
    QGraphicsOpacityEffect,
)
from PyQt6.QtSvg import QSvgRenderer

from app.config import app_config

_ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets")).replace("\\", "/")
ICON_MIC = f"{_ASSETS_DIR}/mic.svg"
ICON_SPARKLE = f"{_ASSETS_DIR}/sparkle.svg"
ICON_CHECK = f"{_ASSETS_DIR}/check.svg"


class MinimalWaveform(QWidget):
    """
    Sleek, centered white waveform matching Wispr Flow's minimal notch visualizer.
    13 capsule bars with smooth envelope tapering from center to dots.
    """

    def __init__(self, num_bars: int = 13, parent=None):
        super().__init__(parent)
        self.num_bars = num_bars
        self.setFixedSize(90, 24)

        # Baseline resting envelope (tapered from center)
        self.base_envelope = [
            2.5, 3.5, 5.0, 7.5, 10.5, 13.5, 15.0, 13.5, 10.5, 7.5, 5.0, 3.5, 2.5
        ]
        self.current_heights = list(self.base_envelope)
        self.target_heights = list(self.base_envelope)

        self.animation_mode = "LISTENING"  # "LISTENING", "PROCESSING", "PASTED", "ERROR"
        self._phase = 0.0

        # Animation loop (60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_step)
        self.timer.start(16)

    def set_mode(self, mode: str):
        self.animation_mode = mode
        if mode == "LISTENING":
            self.target_heights = list(self.base_envelope)

    def update_audio_level(self, rms: float, preview: List[float]):
        """Dynamically scale waveform bars based on microphone input volume."""
        if self.animation_mode != "LISTENING":
            return

        # Boost sensitivity
        boost = min(1.0, rms * 18.0)

        for i in range(self.num_bars):
            base = self.base_envelope[i]
            # Height scales with volume while preserving natural bell curve
            var_sample = preview[i % len(preview)] if preview else 0.0
            h = base * (0.6 + (boost * 1.5)) + (var_sample * 5.0)
            self.target_heights[i] = max(2.5, min(20.0, h))

    def _animate_step(self):
        if self.animation_mode in ("TRANSCRIBING", "POSTPROCESSING"):
            # Rolling breathing shimmer wave during processing
            self._phase += 0.15
            for i in range(self.num_bars):
                wave = math.sin(self._phase + (i * 0.45))
                h = 4.0 + (wave + 1.0) * 5.0
                self.current_heights[i] = h
            self.update()
            return

        # Smooth lerp towards target heights
        changed = False
        for i in range(self.num_bars):
            diff = self.target_heights[i] - self.current_heights[i]
            if abs(diff) > 0.2:
                self.current_heights[i] += diff * 0.35
                changed = True
            else:
                self.current_heights[i] = self.target_heights[i]

        # Decay targets smoothly back to resting state
        if self.animation_mode == "LISTENING":
            for i in range(self.num_bars):
                if self.target_heights[i] > self.base_envelope[i]:
                    self.target_heights[i] -= 0.6

        if changed or self.animation_mode == "LISTENING":
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bar_width = 3.0
        gap = 3.2
        total_w = (self.num_bars * bar_width) + ((self.num_bars - 1) * gap)
        start_x = (self.width() - total_w) / 2.0
        center_y = self.height() / 2.0

        # Bar color
        if self.animation_mode == "PASTED":
            color = QColor(74, 222, 128)   # Bright green
        elif self.animation_mode == "ERROR":
            color = QColor(248, 113, 113)  # Soft red
        elif self.animation_mode == "POSTPROCESSING":
            color = QColor(192, 132, 252)  # Soft purple
        elif self.animation_mode == "TRANSCRIBING":
            color = QColor(253, 224, 71)   # Soft amber/gold
        else:
            color = QColor(255, 255, 255)  # Pure crisp white (like screenshot)

        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(self.num_bars):
            h = self.current_heights[i]
            x = start_x + i * (bar_width + gap)
            y = center_y - (h / 2.0)
            radius = min(bar_width / 2.0, h / 2.0)
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(h), radius, radius)


class PillOverlay(QWidget):
    """
    Sleek top-docked notch visualizer matching the user reference screenshot.
    Can also be freely dragged to any screen position.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Window flags: frameless, stay on top, tool window (no Alt+Tab clutter), don't steal focus
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # Minimal notch size
        self.setFixedSize(156, 38)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        self._drag_start_pos: Optional[QPoint] = None

        # Crisp vector status icons
        self._svg_renderers = {
            "mic": QSvgRenderer(ICON_MIC),
            "sparkle": QSvgRenderer(ICON_SPARKLE),
            "check": QSvgRenderer(ICON_CHECK),
        }

        # Opacity animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(160)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Waveform placed neatly beside the left status icon
        self.waveform = MinimalWaveform(num_bars=13, parent=self)
        self.waveform.move(44, (self.height() - self.waveform.height()) // 2)

        # Auto-hide timer
        self.auto_hide_timer = QTimer(self)
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide_animated)

        self.current_state = "IDLE"

    # ------------------ Mouse Dragging ------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton) and self._drag_start_pos is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_start_pos
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            if self._drag_start_pos is not None:
                app_config.set("custom_pos_x", self.x())
                app_config.set("custom_pos_y", self.y())
                print(f"[Pill] Saved custom notch position: ({self.x()}, {self.y()})")
                self._drag_start_pos = None
            event.accept()

    def _show_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #262626;
                color: #ECECEC;
                border: 1px solid #383838;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #333333;
                color: #FFFFFF;
            }
        """)
        action_reset = menu.addAction("Reset to Top Notch")
        action_reset.triggered.connect(self.reset_position)
        menu.exec(global_pos)

    def reset_position(self):
        """Reset coordinates to top center notch."""
        app_config.set("custom_pos_x", None)
        app_config.set("custom_pos_y", None)
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y()  # Docked right at the top
            self.move(x, y)
            print("[Pill] Reset to top notch.")

    def reposition(self):
        """Position at top center or at saved user drag coordinates."""
        custom_x = app_config.get("custom_pos_x")
        custom_y = app_config.get("custom_pos_y")

        if custom_x is not None and custom_y is not None:
            screen = QApplication.primaryScreen()
            if screen:
                vgeo = screen.virtualGeometry()
                if vgeo.contains(int(custom_x), int(custom_y)):
                    self.move(int(custom_x), int(custom_y))
                    return

        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y()  # Docked flush at top of screen like the screenshot
        self.move(x, y)

    # ------------------ Painting Notch Container ------------------

    def paintEvent(self, event):
        """
        Draw the sleek dark notch matching Wispr Flow / ChatGPT design:
        Smooth rounded bottom corners with true circular arcs and 100% transparent exterior.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_docked_at_top = (self.y() <= 5)
        path = QPainterPath()
        R = 14.0

        if is_docked_at_top:
            # Docked flush at the top: flat top edge, smooth circular arcs at bottom
            rect = QRectF(1.0, 0.0, float(self.width() - 2), float(self.height() - 1))
            path.moveTo(rect.left(), rect.top())
            path.lineTo(rect.right(), rect.top())
            path.lineTo(rect.right(), rect.bottom() - R)
            path.arcTo(QRectF(rect.right() - 2.0 * R, rect.bottom() - 2.0 * R, 2.0 * R, 2.0 * R), 0.0, -90.0)
            path.lineTo(rect.left() + R, rect.bottom())
            path.arcTo(QRectF(rect.left(), rect.bottom() - 2.0 * R, 2.0 * R, 2.0 * R), 270.0, -90.0)
            path.closeSubpath()
        else:
            # Floating pill: fully rounded pill capsule (all 4 corners rounded)
            rect = QRectF(1.0, 1.0, float(self.width() - 2), float(self.height() - 2))
            path.addRoundedRect(rect, R, R)

        # Neutral dark frosted glass gradient (ChatGPT style)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(36, 36, 36, 240))  # Neutral dark charcoal
        grad.setColorAt(1.0, QColor(22, 22, 22, 250))  # Deep neutral dark

        painter.fillPath(path, QBrush(grad))

        # Specular reflection line along top edge
        top_line = QPainterPath()
        top_line.moveTo(rect.left() + 4.0, rect.top() + 1.0)
        top_line.lineTo(rect.right() - 4.0, rect.top() + 1.0)
        painter.strokePath(top_line, QPen(QColor(255, 255, 255, 35), 1.0))

        # Subtle border outline
        if self.current_state == "RECORDING":
            border_color = QColor(255, 255, 255, 120)    # Clean white glow
        elif self.current_state in ("TRANSCRIBING", "POSTPROCESSING"):
            border_color = QColor(250, 204, 21, 180)    # Amber shimmer
        elif self.current_state == "PASTED":
            border_color = QColor(74, 222, 128, 190)    # Soft green
        elif self.current_state == "ERROR":
            border_color = QColor(248, 113, 113, 180)   # Soft red
        else:
            border_color = QColor(255, 255, 255, 30)

        pen = QPen(border_color, 1.0)
        painter.strokePath(path, pen)

        # Draw status icon on the left of the pill
        icon_name = "mic"
        if self.current_state in ("TRANSCRIBING", "POSTPROCESSING"):
            icon_name = "sparkle"
        elif self.current_state == "PASTED":
            icon_name = "check"

        renderer = self._svg_renderers.get(icon_name)
        if renderer and renderer.isValid():
            icon_rect = QRectF(15.0, 11.0, 16.0, 16.0)
            renderer.render(painter, icon_rect)

    # ------------------ Lifecycle & Thread-Safe Slots ------------------

    @pyqtSlot()
    def set_state_listening(self):
        self.auto_hide_timer.stop()
        self.current_state = "RECORDING"
        self.waveform.set_mode("LISTENING")
        self.update()
        self.show_animated()

    @pyqtSlot()
    def set_state_transcribing(self):
        self.current_state = "TRANSCRIBING"
        self.waveform.set_mode("TRANSCRIBING")
        self.update()

    @pyqtSlot()
    def set_state_polishing(self):
        self.current_state = "POSTPROCESSING"
        self.waveform.set_mode("POSTPROCESSING")
        self.update()

    @pyqtSlot(str)
    def set_state_pasted(self, preview_text: str = ""):
        self.current_state = "PASTED"
        self.waveform.set_mode("PASTED")
        self.update()
        self.auto_hide_timer.start(800)

    @pyqtSlot(str)
    def set_state_cancelled(self, message: str = ""):
        self.current_state = "ERROR"
        self.waveform.set_mode("ERROR")
        self.update()
        self.auto_hide_timer.start(600)

    @pyqtSlot(float, list)
    def update_volume(self, rms: float, preview: List[float]):
        if self.current_state == "RECORDING":
            self.waveform.update_audio_level(rms, preview)

    def show_animated(self):
        self.reposition()
        self.show()
        self.raise_()
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.opacity_effect.opacity())
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

    def hide_animated(self):
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.opacity_effect.opacity())
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.finished.connect(self._on_fade_finished)
        self.opacity_anim.start()

    def _on_fade_finished(self):
        try:
            self.opacity_anim.finished.disconnect(self._on_fade_finished)
        except Exception:
            pass
        self.hide()
        self.current_state = "IDLE"
