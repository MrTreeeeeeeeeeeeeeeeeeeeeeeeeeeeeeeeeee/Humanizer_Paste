from __future__ import annotations

import ctypes
import platform
from contextlib import contextmanager


CF_UNICODETEXT = 13


def _is_windows() -> bool:
    return platform.system() == "Windows"


if _is_windows():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_bool
    user32.CloseClipboard.restype = ctypes.c_bool
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    user32.GetClipboardData.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
else:
    user32 = None
    kernel32 = None


@contextmanager
def _open_clipboard():
    if user32 is None:
        raise RuntimeError("Windows clipboard API is unavailable")
    if not user32.OpenClipboard(None):
        error = ctypes.get_last_error()
        raise OSError(error, "OpenClipboard failed")
    try:
        yield
    finally:
        user32.CloseClipboard()


def get_clipboard_text() -> str:
    if user32 is None or kernel32 is None:
        return _get_clipboard_text_tk()

    with _open_clipboard():
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            return ""
        try:
            return ctypes.wstring_at(pointer)
        finally:
            kernel32.GlobalUnlock(handle)


def _get_clipboard_text_tk() -> str:
    try:
        import tkinter
    except Exception:
        return ""

    root = tkinter.Tk()
    root.withdraw()
    try:
        return root.clipboard_get()
    except Exception:
        return ""
    finally:
        root.destroy()
