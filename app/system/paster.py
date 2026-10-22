"""
Text injection module for Nomi Windows.
Supports direct Unicode typing via SendInput at the active cursor position ("with bliss")
as well as clipboard-based pasting with reliable focus restoration.
"""

import time
import ctypes
from ctypes import wintypes
from typing import Optional
import pyperclip
import win32api
import win32con
import win32gui
import win32process


# Win32 SendInput Structures
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulong),
    ]


class INPUT_I(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ii", INPUT_I),
    ]


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_RETURN = 0x0D
VK_TAB = 0x09


class TextPaster:
    """Injects text directly into the focused cursor position in any Windows application."""

    @staticmethod
    def restore_target_focus(target_hwnd: int) -> bool:
        """
        Safely restores foreground focus to the target window using thread attachment,
        overcoming Windows restrictions on SetForegroundWindow.
        """
        if not target_hwnd or not win32gui.IsWindow(target_hwnd):
            return False

        current_fg = win32gui.GetForegroundWindow()
        if current_fg == target_hwnd:
            return True

        our_tid = win32api.GetCurrentThreadId()
        fg_tid, _ = win32process.GetWindowThreadProcessId(current_fg)

        attached = False
        try:
            if fg_tid != our_tid:
                win32process.AttachThreadInput(our_tid, fg_tid, True)
                attached = True
        except Exception:
            pass

        try:
            win32gui.SetForegroundWindow(target_hwnd)
            win32gui.BringWindowToTop(target_hwnd)
        except Exception:
            pass
        finally:
            if attached:
                try:
                    win32process.AttachThreadInput(our_tid, fg_tid, False)
                except Exception:
                    pass

        time.sleep(0.04)
        return win32gui.GetForegroundWindow() == target_hwnd

    @classmethod
    def type_unicode_text(
        cls,
        text: str,
        target_hwnd: int = 0,
        speed_ms: int = 0
    ) -> bool:
        """
        Types text directly at the cursor location character-by-character or batch
        using Windows SendInput with KEYEVENTF_UNICODE.
        Bypasses clipboard completely, preserving user clipboard contents and history.
        """
        if not text:
            return False

        if target_hwnd:
            cls.restore_target_focus(target_hwnd)

        # Build list of input events
        inputs_list = []
        for char in text:
            if char == "\r":
                continue
            elif char == "\n":
                # Send Enter key
                down = INPUT(type=INPUT_KEYBOARD, ii=INPUT_I(ki=KEYBDINPUT(wVk=VK_RETURN, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)))
                up = INPUT(type=INPUT_KEYBOARD, ii=INPUT_I(ki=KEYBDINPUT(wVk=VK_RETURN, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)))
                inputs_list.append((down, up))
            elif char == "\t":
                # Send Tab key
                down = INPUT(type=INPUT_KEYBOARD, ii=INPUT_I(ki=KEYBDINPUT(wVk=VK_TAB, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)))
                up = INPUT(type=INPUT_KEYBOARD, ii=INPUT_I(ki=KEYBDINPUT(wVk=VK_TAB, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)))
                inputs_list.append((down, up))
            else:
                # Encode character to UTF-16 code units (handles standard + emoji surrogate pairs)
                utf16_bytes = char.encode("utf-16le")
                for i in range(0, len(utf16_bytes), 2):
                    code_unit = utf16_bytes[i] | (utf16_bytes[i + 1] << 8)
                    down = INPUT(type=INPUT_KEYBOARD, ii=INPUT_I(ki=KEYBDINPUT(wVk=0, wScan=code_unit, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0)))
                    up = INPUT(type=INPUT_KEYBOARD, ii=INPUT_I(ki=KEYBDINPUT(wVk=0, wScan=code_unit, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)))
                    inputs_list.append((down, up))

        if not inputs_list:
            return False

        try:
            if speed_ms <= 0:
                # Instant batch typing: send all inputs at once
                flat_inputs = []
                for down, up in inputs_list:
                    flat_inputs.append(down)
                    flat_inputs.append(up)

                n = len(flat_inputs)
                arr = (INPUT * n)(*flat_inputs)
                sent = ctypes.windll.user32.SendInput(n, arr, ctypes.sizeof(INPUT))
                return sent == n
            else:
                # Smooth typewriter typing at the cursor with blissful pace
                delay_sec = max(0.002, speed_ms / 1000.0)
                for down, up in inputs_list:
                    arr = (INPUT * 2)(down, up)
                    ctypes.windll.user32.SendInput(2, arr, ctypes.sizeof(INPUT))
                    time.sleep(delay_sec)
                return True

        except Exception as e:
            print(f"[Paster] Failed direct unicode typing: {e}")
            return False

    @classmethod
    def paste_text(
        cls,
        text: str,
        restore_clipboard: bool = True,
        delay_ms: int = 70,
        target_hwnd: int = 0
    ) -> bool:
        """
        Injects text using simulated Ctrl+V via Windows clipboard.
        Used as fallback or for massive documents.
        """
        if not text:
            return False

        if target_hwnd:
            cls.restore_target_focus(target_hwnd)

        original_clipboard: Optional[str] = None
        if restore_clipboard:
            try:
                original_clipboard = pyperclip.paste()
            except Exception:
                original_clipboard = None

        try:
            pyperclip.copy(text)
            time.sleep(0.05)

            # Send Ctrl+V
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord("V"), 0, 0, 0)
            time.sleep(0.04)
            win32api.keybd_event(ord("V"), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

            time.sleep(max(0.1, delay_ms / 1000.0))

            # Restore original clipboard safely
            if restore_clipboard and original_clipboard is not None:
                time.sleep(0.2)
                try:
                    pyperclip.copy(original_clipboard)
                except Exception:
                    pass

            return True

        except Exception as e:
            print(f"[Paster] Failed to paste via clipboard: {e}")
            return False

    @classmethod
    def inject_text(
        cls,
        text: str,
        target_hwnd: int = 0,
        mode: str = "direct",
        speed_ms: int = 0,
        restore_clipboard: bool = True,
        delay_ms: int = 70
    ) -> bool:
        """
        Smart injection router.
        mode can be 'direct' (instant cursor typing), 'smooth' (typewriter flow), or 'clipboard'.
        """
        if mode in ("direct", "typewriter", "smooth"):
            eff_speed = speed_ms if mode != "direct" else 0
            success = cls.type_unicode_text(text, target_hwnd=target_hwnd, speed_ms=eff_speed)
            if success:
                return True
            # Fallback to clipboard if SendInput had any issues
            print("[Paster] Falling back to clipboard paste...")
            return cls.paste_text(text, restore_clipboard=restore_clipboard, delay_ms=delay_ms, target_hwnd=target_hwnd)
        else:
            return cls.paste_text(text, restore_clipboard=restore_clipboard, delay_ms=delay_ms, target_hwnd=target_hwnd)
