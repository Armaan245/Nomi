"""
Glassmorphic & Gaussian Blur Window Effects for Nomi Windows.
Applies native Windows 11 Acrylic blur / Mica backdrop and Windows 10 SetWindowCompositionAttribute
acrylic blur-behind effects to Qt windows.
"""

import sys
import ctypes
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget


class MARGINS(ctypes.Structure):
    _fields_ = [
        ('cxLeftWidth', ctypes.c_int),
        ('cxRightWidth', ctypes.c_int),
        ('cyTopHeight', ctypes.c_int),
        ('cyBottomHeight', ctypes.c_int),
    ]


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ('AccentState', ctypes.c_int),
        ('AccentFlags', ctypes.c_int),
        ('GradientColor', ctypes.c_uint32),
        ('AnimationId', ctypes.c_int),
    ]


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ('Attribute', ctypes.c_int),
        ('Data', ctypes.c_void_p),
        ('SizeOfData', ctypes.c_size_t),
    ]


# Windows DWM constants
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38

# Backdrop types (Windows 11 22H2+)
DWMSBT_AUTO = 0
DWMSBT_NONE = 1
DWMSBT_MAINWINDOW = 2       # Mica
DWMSBT_TRANSIENTWINDOW = 3   # Acrylic (Gaussian Blur Behind)
DWMSBT_TABBEDWINDOW = 4      # Mica Alt

# Accent states for SetWindowCompositionAttribute
ACCENT_DISABLED = 0
ACCENT_ENABLE_GRADIENT = 1
ACCENT_ENABLE_TRANSPARENTGRADIENT = 2
ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4


def apply_acrylic_blur(
    widget: QWidget,
    dark_mode: bool = True,
    tint_abgr: int = 0xEE1E1E1E,
    enable_acrylic: bool = True
) -> bool:
    """
    Applies Gaussian blur (Acrylic / Mica) behind a Qt QWidget or QMainWindow.
    
    Args:
        widget: The Qt widget (must have a valid winId)
        dark_mode: Whether to force Windows dark mode for titlebar / borders
        tint_abgr: ABGR hexadecimal tint color for Windows Acrylic (e.g. 0xBB18100A is deep navy with ~73% alpha)
        enable_acrylic: Whether to enable Gaussian blur behind window
    """
    if sys.platform != "win32":
        return False

    try:
        # Ensure window has a native handle
        hwnd = int(widget.winId())
        dwmapi = ctypes.windll.dwmapi
        user32 = ctypes.windll.user32

        # 1. Enable immersive dark mode (title bar and borders)
        if dark_mode:
            val = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(val),
                ctypes.sizeof(val)
            )

        if not enable_acrylic:
            return True

        # 2. Extend DWM frame into entire client area
        margins = MARGINS(-1, -1, -1, -1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

        # 3. Modern Windows 11 Acrylic Backdrop (Build 22621+)
        backdrop = ctypes.c_int(DWMSBT_TRANSIENTWINDOW)
        res_dw = dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(backdrop),
            ctypes.sizeof(backdrop)
        )

        # 4. SetWindowCompositionAttribute for universal Acrylic blur support
        policy = ACCENT_POLICY()
        policy.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
        policy.AccentFlags = 2  # Draw all borders
        policy.GradientColor = tint_abgr
        policy.AnimationId = 0

        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19  # WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(policy), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(policy)

        user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))

        return True

    except Exception as e:
        print(f"[Glass] Notice: Could not apply native blur effect ({e})")
        return False
