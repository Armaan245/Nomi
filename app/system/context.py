"""
Windows Context Extractor.
Inspects foreground window title, process name, and active selected text.
"""

import time
import psutil
import pyperclip
import win32gui
import win32process
import win32api
import win32con
from typing import Tuple, Optional


class SystemContextService:
    """Provides details about the currently active window and text selection."""

    @staticmethod
    def get_active_window_info() -> Tuple[str, str, int]:
        """
        Returns (window_title, process_name, hwnd).
        Handles permission errors or missing processes gracefully.
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return ("", "", 0)

            title = win32gui.GetWindowText(hwnd) or ""
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc_name = ""

            if pid and psutil.pid_exists(pid):
                try:
                    proc_name = psutil.Process(pid).name()
                except Exception:
                    proc_name = ""

            return (title.strip(), proc_name.strip(), hwnd)

        except Exception as e:
            print(f"[Context] Error getting window info: {e}")
            return ("", "", 0)

    @staticmethod
    def get_selected_text() -> Optional[str]:
        """
        Attempts to read highlighted/selected text in the active application
        by simulating Ctrl+C and restoring clipboard contents afterward.
        Returns selected text if any was highlighted, else None.
        """
        original_clipboard = ""
        try:
            original_clipboard = pyperclip.paste()
        except Exception:
            pass

        # Clear clipboard temporarily to test if copy succeeds
        try:
            pyperclip.copy("")
        except Exception:
            pass

        # Simulate Ctrl+C
        try:
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('C'), 0, 0, 0)
            time.sleep(0.04)
            win32api.keybd_event(ord('C'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.06)

            selected = pyperclip.paste()

            # Restore original clipboard
            if original_clipboard:
                pyperclip.copy(original_clipboard)

            if selected and selected.strip():
                return selected.strip()
        except Exception as e:
            print(f"[Context] Error reading selection: {e}")
            if original_clipboard:
                try:
                    pyperclip.copy(original_clipboard)
                except Exception:
                    pass

        return None
