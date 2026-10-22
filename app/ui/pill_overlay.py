"""
Floating / Docked Top Notch Pill Overlay for Nomi Windows.
Features dynamic width expansion, live speech-to-text preview,
minimal white waveform visualizer, and crisp vector status icons.
"""

import os
import math
from typing import List, Optional
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect, QRectF, pyqtSlot
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget,
    QApplication,
    QMenu,
    QLabel,
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
    Sleek, compact white waveform matching Wispr Flow's minimal notch visualizer.
    7 capsule bars with dynamic volume scaling and subtle resting envelope.
    """

    def __init__(self, num_bars: int = 7, parent=None):
        super().__init__(parent)
        self.num_bars = num_bars
        self.setFixedSize(38, 20)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # Baseline resting envelope
        self.base_envelope = [2.5, 4.5, 8.0, 12.0, 8.0, 4.5, 2.5]
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

        boost = min(1.0, rms * 18.0)
        for i in range(self.num_bars):
            base = self.base_envelope[i]
            var_sample = preview[i % len(preview)] if preview else 0.0
            h = base * (0.6 + (boost * 1.5)) + (var_sample * 4.0)
            self.target_heights[i] = max(2.5, min(16.0, h))

    def _animate_step(self):
        if self.animation_mode in ("TRANSCRIBING", "POSTPROCESSING"):
            # Rolling breathing shimmer wave during processing
            self._phase += 0.18
            for i in range(self.num_bars):
                wave = math.sin(self._phase + (i * 0.6))
                h = 3.5 + (wave + 1.0) * 4.0
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

        bar_width = 2.4
        gap = 2.4
        total_w = (self.num_bars * bar_width) + ((self.num_bars - 1) * gap)
        start_x = (self.width() - total_w) / 2.0
        center_y = self.height() / 2.0

        if self.animation_mode == "PASTED":
            color = QColor(74, 222, 128)   # Bright green
        elif self.animation_mode == "ERROR":
            color = QColor(248, 113, 113)  # Soft red
        elif self.animation_mode == "POSTPROCESSING":
            color = QColor(192, 132, 252)  # Soft purple
        elif self.animation_mode == "TRANSCRIBING":
            color = QColor(253, 224, 71)   # Soft amber
        else:
            color = QColor(255, 255, 255)  # Crisp white

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
    Sleek top-docked notch visualizer with live speech preview.
    Matches ChatGPT neutral dark aesthetic with smooth dynamic expansion.
    """

    BASE_WIDTH = 170
    MAX_WIDTH = 480
    HEIGHT = 38

    def __init__(self, parent=None):
        super().__init__(parent)

        # Window flags: frameless, stay on top, tool window, don't steal focus
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.resize(self.BASE_WIDTH, self.HEIGHT)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        self._drag_start_pos: Optional[QPoint] = None
        self._raw_spoken_text = ""

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

        # Geometry expansion animation (for dynamic island/notch resizing)
        self.geom_anim = QPropertyAnimation(self, b"geometry")
        self.geom_anim.setDuration(180)
        self.geom_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Compact Waveform
        self.waveform = MinimalWaveform(num_bars=7, parent=self)
        self.waveform.move(34, (self.HEIGHT - self.waveform.height()) // 2)

        # Live Text Preview Label
        self.lbl_text = QLabel(self)
        self.lbl_text.setGeometry(78, 0, self.width() - 86, self.HEIGHT)
        self.lbl_text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.lbl_text.setStyleSheet("""
            QLabel {
                color: #A0A0A0;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
                font-size: 12px;
                font-weight: 400;
                background: transparent;
            }
        """)
        self.lbl_text.setText("Listening...")

        # Auto-hide timer
        self.auto_hide_timer = QTimer(self)
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide_animated)

        self.current_state = "IDLE"

    # ------------------ Dynamic Sizing & Layout ------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep text label bounded inside the expanded notch
        self.lbl_text.setGeometry(78, 0, max(10, self.width() - 86), self.HEIGHT)
        if self._raw_spoken_text and self.current_state == "RECORDING":
            fm = QFontMetrics(self.lbl_text.font())
            avail_w = max(20, self.width() - 92)
            self.lbl_text.setText(fm.elidedText(self._raw_spoken_text, Qt.TextElideMode.ElideLeft, avail_w))

    def animate_to_width(self, target_w: int):
        """Smoothly resize pill width, anchoring to center when docked."""
        target_w = max(self.BASE_WIDTH, min(self.MAX_WIDTH, target_w))
        if self.width() == target_w:
            return

        screen = QApplication.primaryScreen()
        is_docked = (self.y() <= 5) and (app_config.get("custom_pos_x") is None)

        if is_docked and screen:
            geo = screen.availableGeometry()
            new_x = geo.x() + (geo.width() - target_w) // 2
            new_y = geo.y()
        else:
            diff = (target_w - self.width()) // 2
            new_x = max(10, self.x() - diff)
            new_y = self.y()

        self.geom_anim.stop()
        self.geom_anim.setStartValue(self.geometry())
        self.geom_anim.setEndValue(QRect(int(new_x), int(new_y), int(target_w), self.HEIGHT))
        self.geom_anim.start()

    # ------------------ Mouse Dragging & Context Menu ------------------

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
        self.resize(self.BASE_WIDTH, self.HEIGHT)
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y()
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
        y = geo.y()
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
            # Docked flush at the top
            rect = QRectF(1.0, 0.0, float(self.width() - 2), float(self.height() - 1))
            path.moveTo(rect.left(), rect.top())
            path.lineTo(rect.right(), rect.top())
            path.lineTo(rect.right(), rect.bottom() - R)
            path.arcTo(QRectF(rect.right() - 2.0 * R, rect.bottom() - 2.0 * R, 2.0 * R, 2.0 * R), 0.0, -90.0)
            path.lineTo(rect.left() + R, rect.bottom())
            path.arcTo(QRectF(rect.left(), rect.bottom() - 2.0 * R, 2.0 * R, 2.0 * R), 270.0, -90.0)
            path.closeSubpath()
        else:
            # Floating pill
            rect = QRectF(1.0, 1.0, float(self.width() - 2), float(self.height() - 2))
            path.addRoundedRect(rect, R, R)

        # Neutral dark frosted glass gradient (ChatGPT style)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(36, 36, 36, 245))  # Neutral dark charcoal
        grad.setColorAt(1.0, QColor(22, 22, 22, 252))  # Deep neutral dark
        painter.fillPath(path, QBrush(grad))

        # Specular reflection line along top edge
        top_line = QPainterPath()
        top_line.moveTo(rect.left() + 4.0, rect.top() + 1.0)
        top_line.lineTo(rect.right() - 4.0, rect.top() + 1.0)
        painter.strokePath(top_line, QPen(QColor(255, 255, 255, 35), 1.0))

        # Subtle border outline
        if self.current_state == "RECORDING":
            border_color = QColor(255, 255, 255, 120)   # Clean white glow
        elif self.current_state in ("TRANSCRIBING", "POSTPROCESSING"):
            border_color = QColor(250, 204, 21, 180)   # Amber shimmer
        elif self.current_state == "PASTED":
            border_color = QColor(74, 222, 128, 190)   # Soft green
        elif self.current_state == "ERROR":
            border_color = QColor(248, 113, 113, 180)  # Soft red
        else:
            border_color = QColor(255, 255, 255, 30)

        pen = QPen(border_color, 1.0)
        painter.strokePath(path, pen)

        # Draw status icon on the left
        icon_name = "mic"
        if self.current_state in ("TRANSCRIBING", "POSTPROCESSING"):
            icon_name = "sparkle"
        elif self.current_state == "PASTED":
            icon_name = "check"

        renderer = self._svg_renderers.get(icon_name)
        if renderer and renderer.isValid():
            icon_rect = QRectF(12.0, 11.0, 16.0, 16.0)
            renderer.render(painter, icon_rect)

    # ------------------ Lifecycle & Thread-Safe Slots ------------------

    @pyqtSlot()
    def set_state_listening(self):
        self.auto_hide_timer.stop()
        self.current_state = "RECORDING"
        self._raw_spoken_text = ""
        self.waveform.set_mode("LISTENING")
        self.lbl_text.setStyleSheet("""
            QLabel {
                color: #8E8E93;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
                font-size: 12px;
                font-style: italic;
                background: transparent;
            }
        """)
        self.lbl_text.setText("Listening...")
        self.animate_to_width(self.BASE_WIDTH)
        self.update()
        self.show_animated()

    @pyqtSlot(str)
    def update_live_text(self, text: str):
        """Update live speech preview dynamically as the user speaks."""
        if self.current_state != "RECORDING":
            return

        text = text.strip()
        if not text:
            return

        self._raw_spoken_text = text
        self.lbl_text.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }
        """)

        # Calculate needed width for the spoken text
        font = self.lbl_text.font()
        fm = QFontMetrics(font)
        text_width = fm.horizontalAdvance(text)
        ideal_width = min(self.MAX_WIDTH, max(self.BASE_WIDTH, 86 + text_width + 24))
        self.animate_to_width(ideal_width)

        avail_width = max(20, ideal_width - 92)
        display_text = fm.elidedText(text, Qt.TextElideMode.ElideLeft, avail_width)
        self.lbl_text.setText(display_text)

    @pyqtSlot()
    def set_state_transcribing(self):
        self.current_state = "TRANSCRIBING"
        self.waveform.set_mode("TRANSCRIBING")
        self.lbl_text.setStyleSheet("""
            QLabel {
                color: #FDE047;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }
        """)
        self.lbl_text.setText("Transcribing...")
        self.update()

    @pyqtSlot()
    def set_state_polishing(self):
        self.current_state = "POSTPROCESSING"
        self.waveform.set_mode("POSTPROCESSING")
        self.lbl_text.setStyleSheet("""
            QLabel {
                color: #C084FC;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }
        """)
        self.lbl_text.setText("Polishing with AI...")
        self.update()

    @pyqtSlot(str)
    def set_state_pasted(self, preview_text: str = ""):
        self.current_state = "PASTED"
        self.waveform.set_mode("PASTED")
        self.lbl_text.setStyleSheet("""
            QLabel {
                color: #4ADE80;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }
        """)
        msg = "Typed with bliss!" if not preview_text or preview_text.startswith("[") else "Inserted!"
        self.lbl_text.setText(msg)
        self.update()
        self.auto_hide_timer.start(800)

    @pyqtSlot(str)
    def set_state_cancelled(self, message: str = ""):
        self.current_state = "ERROR"
        self.waveform.set_mode("ERROR")
        self.lbl_text.setStyleSheet("""
            QLabel {
                color: #F87171;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }
        """)
        self.lbl_text.setText(message if message else "Cancelled")
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
        self.resize(self.BASE_WIDTH, self.HEIGHT)
        self.lbl_text.setText("Listening...")
