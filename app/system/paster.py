"""
Automatic text injection module.
Pastes text into the active Windows application via simulated Ctrl+V.
"""

import time
import pyperclip
import win32api
import win32con
import win32gui
from typing import Optional


class TextPaster:
    """Safely pastes text into any active text field on Windows."""

    @staticmethod
    def paste_text(
        text: str,
        restore_clipboard: bool = True,
        delay_ms: int = 70,
        target_hwnd: int = 0
    ) -> bool:
        if not text:
            return False

        # If a target window was provided and is not currently foreground, restore focus
        if target_hwnd and win32gui.IsWindow(target_hwnd):
            current_fg = win32gui.GetForegroundWindow()
            if current_fg != target_hwnd:
                try:
                    win32gui.SetForegroundWindow(target_hwnd)
                    time.sleep(0.04)
                except Exception:
                    pass

        # Save previous clipboard
        original_clipboard: Optional[str] = None
        if restore_clipboard:
            try:
                original_clipboard = pyperclip.paste()
            except Exception:
                original_clipboard = None

        try:
            # Set target text to clipboard
            pyperclip.copy(text)
            time.sleep(0.05)

            # Send Ctrl+V key combination
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('V'), 0, 0, 0)
            time.sleep(0.04)
            win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

            # Wait for target application to process the paste message
            time.sleep(max(0.08, delay_ms / 1000.0))

            # Optionally restore original clipboard
            if restore_clipboard and original_clipboard is not None:
                time.sleep(0.08)
                try:
                    pyperclip.copy(original_clipboard)
                except Exception:
                    pass

            return True

        except Exception as e:
            print(f"[Paster] Failed to paste: {e}")
            return False
