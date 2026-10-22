"""
Global hotkey manager using pynput.
Supports Hold-to-Talk (Right Alt / F8), Press-to-Toggle (F8 / F9), and Cancel across all Windows apps.
"""

from typing import Optional, Set
from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal


class GlobalHotkeyManager(QObject):
    """
    Listens to system-wide keyboard events without taking focus away from active apps.
    Allows both Hold-to-Talk and Press-to-Toggle simultaneously.
    """
    hold_start_signal = pyqtSignal()
    hold_stop_signal = pyqtSignal()
    toggle_signal = pyqtSignal()
    cancel_signal = pyqtSignal()

    def __init__(
        self,
        mode: str = "hold",
        hold_key_name: str = "alt_r",
        toggle_key_name: str = "f8",
        cancel_key_name: str = "esc"
    ):
        super().__init__()
        self.mode = mode                     # "hold", "toggle", or "both"
        self.hold_key_name = hold_key_name.lower()
        self.toggle_key_name = toggle_key_name.lower()
        self.cancel_key_name = cancel_key_name.lower()

        self._listener: Optional[keyboard.Listener] = None
        self._is_holding = False
        self._enabled = True

        # Recognized aliases for keys
        self._alt_r_aliases: Set[str] = {"alt_r", "alt_gr", "altgr", "right alt", "165"}
        self._f8_aliases: Set[str] = {"f8", "119"}
        self._f9_aliases: Set[str] = {"f9", "120"}
        self._esc_aliases: Set[str] = {"esc", "escape", "27"}

    def set_config(self, mode: str, hold_key: str, toggle_key: str):
        self.mode = mode.lower()
        self.hold_key_name = hold_key.lower()
        self.toggle_key_name = toggle_key.lower()
        print(f"[Hotkey] Config updated: Hold='{self.hold_key_name}', Toggle='{self.toggle_key_name}'")

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        print(f"[Hotkey] Enabled state: {enabled}")

    def start(self):
        """Start global keyboard listener."""
        if self._listener is not None:
            return

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.daemon = True
        self._listener.start()
        print(f"[Hotkey] Global listener active.")
        print(f"         • Hold to talk:  [Right Alt] or [{self.hold_key_name.upper()}]")
        print(f"         • Tap to toggle: [{self.toggle_key_name.upper()}] (or [F8])")
        print(f"         • Cancel:        [Esc]")

    def stop(self):
        """Stop global keyboard listener."""
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
            self._is_holding = False

    def _normalize_key(self, key) -> str:
        """Convert pynput Key / KeyCode to normalized string."""
        try:
            if isinstance(key, keyboard.Key):
                name = key.name.lower()
                if name in ("alt_r", "alt_gr"):
                    return "alt_r"
                if name in ("esc", "escape"):
                    return "esc"
                return name

            if hasattr(key, "vk") and key.vk is not None:
                vk = key.vk
                if vk == 165 or vk == 164:  # VK_RMENU / VK_LMENU
                    return "alt_r" if vk == 165 else "alt_l"
                if 112 <= vk <= 123:
                    return f"f{vk - 111}"
                if vk == 27:
                    return "esc"

            if hasattr(key, "char") and key.char:
                return key.char.lower()

        except Exception as e:
            print(f"[Hotkey] Normalization error: {e}")

        return str(key).lower()

    def _is_hold_key(self, key_name: str) -> bool:
        if self.hold_key_name in self._alt_r_aliases and key_name in self._alt_r_aliases:
            return True
        if key_name == self.hold_key_name:
            return True
        return False

    def _is_toggle_key(self, key_name: str) -> bool:
        if self.toggle_key_name in self._f8_aliases and key_name in self._f8_aliases:
            return True
        if key_name == self.toggle_key_name:
            return True
        return False

    def _on_press(self, key):
        if not self._enabled:
            return

        key_name = self._normalize_key(key)

        # Cancel on Escape
        if key_name in self._esc_aliases or key_name == self.cancel_key_name:
            if self._is_holding:
                print("[Hotkey] Escape pressed -> Cancelling recording.")
                self._is_holding = False
                self.cancel_signal.emit()
            return

        # Hold-to-Talk Key
        if self._is_hold_key(key_name):
            if not self._is_holding:
                self._is_holding = True
                print(f"[Hotkey] Hold key down ({key_name}) -> Starting recording...")
                self.hold_start_signal.emit()

    def _on_release(self, key):
        if not self._enabled:
            return

        key_name = self._normalize_key(key)

        # Hold-to-Talk Key released
        if self._is_hold_key(key_name):
            if self._is_holding:
                self._is_holding = False
                print(f"[Hotkey] Hold key released ({key_name}) -> Processing audio...")
                self.hold_stop_signal.emit()
                return

        # Toggle Key tapped
        if self._is_toggle_key(key_name):
            print(f"[Hotkey] Toggle key pressed ({key_name}) -> Toggling recording...")
            self.toggle_signal.emit()
