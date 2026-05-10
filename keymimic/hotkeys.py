from __future__ import annotations

import ctypes
import platform
import queue
import threading
from dataclasses import dataclass
from typing import Callable


class HotkeyError(RuntimeError):
    pass


class HotkeyParseError(ValueError):
    pass


MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
PM_NOREMOVE = 0x0000

MODIFIER_ALIASES = {
    "CTRL": "Ctrl",
    "CONTROL": "Ctrl",
    "SHIFT": "Shift",
    "ALT": "Alt",
    "OPTION": "Alt",
    "WIN": "Win",
    "WINDOWS": "Win",
    "META": "Win",
    "CMD": "Win",
    "COMMAND": "Win",
}

MODIFIER_FLAGS = {
    "Ctrl": MOD_CONTROL,
    "Shift": MOD_SHIFT,
    "Alt": MOD_ALT,
    "Win": MOD_WIN,
}

KEY_CODES = {
    "Backspace": 0x08,
    "Tab": 0x09,
    "Enter": 0x0D,
    "Esc": 0x1B,
    "Escape": 0x1B,
    "Space": 0x20,
    "PageUp": 0x21,
    "PageDown": 0x22,
    "End": 0x23,
    "Home": 0x24,
    "Left": 0x25,
    "Up": 0x26,
    "Right": 0x27,
    "Down": 0x28,
    "Insert": 0x2D,
    "Delete": 0x2E,
}

for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    KEY_CODES[char] = ord(char)
for char in "0123456789":
    KEY_CODES[char] = ord(char)
for i in range(1, 25):
    KEY_CODES[f"F{i}"] = 0x70 + i - 1

DISPLAY_KEYS = {
    "ESCAPE": "Esc",
    "ESC": "Esc",
    "RETURN": "Enter",
    "ENTER": "Enter",
    "SPACE": "Space",
    "PGUP": "PageUp",
    "PAGEUP": "PageUp",
    "PGDN": "PageDown",
    "PAGEDOWN": "PageDown",
    "BKSP": "Backspace",
    "BACKSPACE": "Backspace",
    "DEL": "Delete",
    "DELETE": "Delete",
    "INS": "Insert",
    "INSERT": "Insert",
    "UP": "Up",
    "DOWN": "Down",
    "LEFT": "Left",
    "RIGHT": "Right",
    "HOME": "Home",
    "END": "End",
    "TAB": "Tab",
}

PUNCTUATION_KEYS = {
    ";": 0xBA,
    "=": 0xBB,
    ",": 0xBC,
    "-": 0xBD,
    ".": 0xBE,
    "/": 0xBF,
    "`": 0xC0,
    "[": 0xDB,
    "\\": 0xDC,
    "]": 0xDD,
    "'": 0xDE,
}
KEY_CODES.update(PUNCTUATION_KEYS)


@dataclass(frozen=True)
class ParsedHotkey:
    display: str
    modifiers: int
    vk: int


def _display_key(token: str) -> str:
    stripped = token.strip()
    upper = stripped.upper()
    if len(stripped) == 1 and stripped.isalpha():
        return stripped.upper()
    if len(stripped) == 1 and stripped.isdigit():
        return stripped
    if upper in DISPLAY_KEYS:
        return DISPLAY_KEYS[upper]
    if upper.startswith("F") and upper[1:].isdigit():
        number = int(upper[1:])
        if 1 <= number <= 24:
            return f"F{number}"
    if stripped in PUNCTUATION_KEYS:
        return stripped
    raise HotkeyParseError(f"Unsupported hotkey key: {token}")


def parse_hotkey(value: str, *, required: bool = True) -> ParsedHotkey | None:
    if not value.strip():
        if required:
            raise HotkeyParseError("Hotkey is required")
        return None

    parts = [part.strip() for part in value.replace(" ", "").split("+") if part]
    if not parts:
        if required:
            raise HotkeyParseError("Hotkey is required")
        return None

    modifiers: list[str] = []
    key: str | None = None
    for part in parts:
        upper = part.upper()
        if upper in MODIFIER_ALIASES:
            modifier = MODIFIER_ALIASES[upper]
            if modifier not in modifiers:
                modifiers.append(modifier)
            continue
        if key is not None:
            raise HotkeyParseError("Only one non-modifier key is allowed")
        key = _display_key(part)

    if key is None:
        raise HotkeyParseError("A non-modifier key is required")

    modifier_flags = 0
    for modifier in modifiers:
        modifier_flags |= MODIFIER_FLAGS[modifier]
    display_order = [name for name in ("Ctrl", "Shift", "Alt", "Win") if name in modifiers]
    display = "+".join(display_order + [key])
    vk = KEY_CODES[key]
    return ParsedHotkey(display=display, modifiers=modifier_flags, vk=vk)


def normalize_hotkey(value: str, *, required: bool = False) -> str:
    parsed = parse_hotkey(value, required=required)
    return "" if parsed is None else parsed.display


def validate_hotkey_settings(settings: object) -> None:
    fields = {
        "start_pause_typing": False,
        "stop_typing": True,
        "show_hide_window": False,
    }
    seen: dict[str, str] = {}
    for field_name, required in fields.items():
        value = getattr(settings, field_name)
        normalized = normalize_hotkey(value, required=required)
        if not normalized:
            continue
        duplicate = seen.get(normalized.casefold())
        if duplicate:
            raise HotkeyParseError(
                f"{field_name} conflicts with {duplicate}: {normalized}"
            )
        seen[normalized.casefold()] = field_name


def hotkey_to_windows(value: str) -> tuple[int, int]:
    parsed = parse_hotkey(value, required=True)
    assert parsed is not None
    return parsed.modifiers | MOD_NOREPEAT, parsed.vk


def _is_windows() -> bool:
    return platform.system() == "Windows"


if _is_windows():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
else:
    user32 = None


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_size_t),
        ("time", ctypes.c_uint32),
        ("pt_x", ctypes.c_long),
        ("pt_y", ctypes.c_long),
    ]


if user32 is not None:
    user32.RegisterHotKey.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_uint,
    ]
    user32.RegisterHotKey.restype = ctypes.c_bool
    user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.UnregisterHotKey.restype = ctypes.c_bool
    user32.GetMessageW.argtypes = [
        ctypes.POINTER(MSG),
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_uint,
    ]
    user32.GetMessageW.restype = ctypes.c_int
    user32.PeekMessageW.argtypes = [
        ctypes.POINTER(MSG),
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
    ]
    user32.PeekMessageW.restype = ctypes.c_bool
    user32.PostThreadMessageW.argtypes = [
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_size_t,
        ctypes.c_size_t,
    ]
    user32.PostThreadMessageW.restype = ctypes.c_bool


HotkeyCallback = Callable[[str], None]


class GlobalHotkeyManager:
    """Thread-owned RegisterHotKey manager.

    RegisterHotKey delivers WM_HOTKEY messages to the registering thread when
    hwnd is null, so registrations and the message loop live in one worker
    thread. Reconfiguration restarts that thread atomically enough for a
    desktop utility and restores the previous bindings if new registration
    fails.
    """

    def __init__(self, callback: HotkeyCallback | None = None) -> None:
        self._callback = callback
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._bindings: dict[str, str] = {}
        self._lock = threading.RLock()

    @property
    def bindings(self) -> dict[str, str]:
        with self._lock:
            return dict(self._bindings)

    def apply_bindings(
        self,
        bindings: dict[str, str],
        callback: HotkeyCallback | None = None,
    ) -> dict[str, str]:
        if callback is not None:
            self._callback = callback
        if not _is_windows():
            with self._lock:
                self._bindings = {
                    action: normalize_hotkey(hotkey)
                    for action, hotkey in bindings.items()
                    if normalize_hotkey(hotkey)
                }
            return {
                action: "Unavailable on this platform"
                for action in self._bindings
            }

        normalized = {
            action: normalize_hotkey(hotkey)
            for action, hotkey in bindings.items()
            if normalize_hotkey(hotkey)
        }
        old_bindings = self.bindings
        self.stop()
        if not normalized:
            with self._lock:
                self._bindings = {}
            return {}
        try:
            statuses = self._start_thread(normalized)
        except Exception:
            if old_bindings:
                self._start_thread(old_bindings)
            raise
        with self._lock:
            self._bindings = dict(normalized)
        return statuses

    def stop(self) -> None:
        with self._lock:
            thread = self._thread
            thread_id = self._thread_id
            self._thread = None
            self._thread_id = None
        if thread and thread.is_alive() and thread_id and user32 is not None:
            user32.PostThreadMessageW(thread_id, WM_QUIT, 0, 0)
            thread.join(timeout=2.0)

    def _start_thread(self, bindings: dict[str, str]) -> dict[str, str]:
        ready: queue.Queue[tuple[bool, dict[str, str], int | None]] = queue.Queue()
        callback = self._callback
        thread = threading.Thread(
            target=self._thread_main,
            args=(bindings, callback, ready),
            name="KeyMimicHotkeys",
            daemon=True,
        )
        thread.start()
        try:
            ok, statuses, thread_id = ready.get(timeout=2.0)
        except queue.Empty as exc:
            raise HotkeyError("Timed out while registering hotkeys") from exc
        if not ok:
            thread.join(timeout=1.0)
            detail = "; ".join(f"{k}: {v}" for k, v in statuses.items())
            raise HotkeyError(f"Could not register hotkeys: {detail}")
        with self._lock:
            self._thread = thread
            self._thread_id = thread_id
        return statuses

    def _thread_main(
        self,
        bindings: dict[str, str],
        callback: HotkeyCallback | None,
        ready: queue.Queue[tuple[bool, dict[str, str], int | None]],
    ) -> None:
        if user32 is None:
            ready.put((False, {"platform": "Windows is required"}, None))
            return

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        thread_id = kernel32.GetCurrentThreadId()
        id_to_action: dict[int, str] = {}
        statuses: dict[str, str] = {}
        ok = True
        msg = MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_NOREMOVE)

        for index, (action, hotkey) in enumerate(bindings.items(), start=1):
            modifiers, vk = hotkey_to_windows(hotkey)
            registered = user32.RegisterHotKey(None, index, modifiers, vk)
            if not registered:
                error = ctypes.get_last_error()
                statuses[action] = f"registration failed ({error})"
                ok = False
                break
            id_to_action[index] = action
            statuses[action] = "registered"

        if not ok:
            for hotkey_id in id_to_action:
                user32.UnregisterHotKey(None, hotkey_id)
            ready.put((False, statuses, thread_id))
            return

        ready.put((True, statuses, thread_id))
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                action = id_to_action.get(int(msg.wParam))
                if action and callback:
                    callback(action)

        for hotkey_id in id_to_action:
            user32.UnregisterHotKey(None, hotkey_id)
