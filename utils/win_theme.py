import sys
import ctypes


def apply_dark_titlebar(window, bg_hex="#0F0F12", fg_hex="#FAFAFA"):
    if sys.platform != "win32":
        return

    try:
        hwnd = int(window.winId())
        dwm = ctypes.windll.dwmapi

        for attr in (20, 19):
            val = ctypes.c_int(1)
            dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))

        def _colorref(hex_str):
            h = hex_str.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return (b << 16) | (g << 8) | r
        cap = ctypes.c_int(_colorref(bg_hex))
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(cap), ctypes.sizeof(cap))
        txt = ctypes.c_int(_colorref(fg_hex))
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(txt), ctypes.sizeof(txt))
    except Exception:
        pass