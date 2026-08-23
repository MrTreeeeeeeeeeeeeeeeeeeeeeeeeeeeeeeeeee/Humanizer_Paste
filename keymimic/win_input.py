from __future__ import annotations

import ctypes
import platform
import random
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008
INPUT_KEYBOARD = 1

SC_LSHIFT = 0x2A
SC_LCTRL = 0x1D
SC_LALT = 0x38
SC_ENTER = 0x1C
SC_BACKSPACE = 0x0E
SC_SPACE = 0x39
SC_TAB = 0x0F


def is_windows() -> bool:
    return platform.system() == "Windows"


user32: Any
winmm: Any
if is_windows():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    winmm = ctypes.WinDLL("winmm", use_last_error=True)
else:
    user32 = None
    winmm = None


ULONG_PTR = (
    ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_uint),
        ("time", ctypes.c_uint),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_uint),
        ("dwFlags", ctypes.c_uint),
        ("time", ctypes.c_uint),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_uint),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint),
        ("union", INPUT_UNION),
    ]


if user32 is not None:
    user32.SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = ctypes.c_uint
    user32.VkKeyScanW.argtypes = [ctypes.c_wchar]
    user32.VkKeyScanW.restype = ctypes.c_short
    user32.MapVirtualKeyW.argtypes = [ctypes.c_uint, ctypes.c_uint]
    user32.MapVirtualKeyW.restype = ctypes.c_uint
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
if winmm is not None:
    winmm.timeBeginPeriod.argtypes = [ctypes.c_uint]
    winmm.timeBeginPeriod.restype = ctypes.c_uint
    winmm.timeEndPeriod.argtypes = [ctypes.c_uint]
    winmm.timeEndPeriod.restype = ctypes.c_uint


@dataclass(frozen=True)
class ScanInfo:
    vk: int
    scan: int
    need_shift: bool
    need_ctrl_alt: bool


class WindowsInput:
    def __init__(
        self,
        hold_jitter_ms: int = 10,
        rng: random.Random | None = None,
    ) -> None:
        self.hold_jitter_ms = hold_jitter_ms
        self._rng = rng or random.Random()

    @property
    def available(self) -> bool:
        return user32 is not None

    def send_scan_input(self, scan_code: int, flags: int = 0) -> None:
        if user32 is None:
            raise RuntimeError("Windows input injection is unavailable")
        input_struct = INPUT(
            type=INPUT_KEYBOARD,
            union=INPUT_UNION(
                ki=KEYBDINPUT(
                    wVk=0,
                    wScan=scan_code,
                    dwFlags=KEYEVENTF_SCANCODE | flags,
                    time=0,
                    dwExtraInfo=0,
                )
            ),
        )
        sent = user32.SendInput(
            1,
            ctypes.byref(input_struct),
            ctypes.sizeof(INPUT),
        )
        if sent != 1:
            error = ctypes.get_last_error()
            raise OSError(error, "SendInput failed")

    def press_key_scan(
        self,
        scan_code: int,
        hold_time_ms: int,
        *,
        is_extended: bool = False,
    ) -> None:
        extended = KEYEVENTF_EXTENDEDKEY if is_extended else 0
        pressed = False
        try:
            self.send_scan_input(scan_code, extended)
            pressed = True
            actual_hold = hold_time_ms + self._rng.randint(
                -self.hold_jitter_ms,
                self.hold_jitter_ms,
            )
            time.sleep(max(0.005, actual_hold / 1000.0))
        finally:
            if pressed:
                self.send_scan_input(scan_code, extended | KEYEVENTF_KEYUP)

    def char_to_scan_info(self, char: str) -> ScanInfo | None:
        if user32 is None:
            return None
        result = ctypes.c_short(user32.VkKeyScanW(char)).value
        if result == -1:
            return None
        vk = result & 0xFF
        shift_state = (result >> 8) & 0xFF
        scan = user32.MapVirtualKeyW(vk, 0)
        if scan == 0:
            return None
        return ScanInfo(
            vk=vk,
            scan=scan,
            need_shift=bool(shift_state & 1),
            need_ctrl_alt=bool(shift_state & 6),
        )

    def send_char(self, char: str, hold_time_ms: int) -> None:
        if len(char) != 1:
            raise ValueError("send_char requires exactly one character")
        if char == "\r":
            return
        if char == "\n":
            self.press_key_scan(SC_ENTER, hold_time_ms)
            return
        if char == " ":
            self.press_key_scan(SC_SPACE, hold_time_ms)
            return
        if char == "\t":
            self.press_key_scan(SC_TAB, hold_time_ms)
            return

        info = self.char_to_scan_info(char)
        if info is None:
            self.send_unicode_char(char)
            return

        held_modifiers: list[int] = []
        try:
            if info.need_ctrl_alt:
                self._press_modifier(SC_LCTRL, held_modifiers)
                self._press_modifier(SC_LALT, held_modifiers)
            if info.need_shift:
                self._press_modifier(SC_LSHIFT, held_modifiers)
            self.press_key_scan(info.scan, hold_time_ms)
        finally:
            release_error: OSError | None = None
            original_error_active = sys.exc_info()[0] is not None
            for scan_code in reversed(held_modifiers):
                time.sleep(self._rng.uniform(0.005, 0.015))
                try:
                    self.send_scan_input(scan_code, KEYEVENTF_KEYUP)
                except OSError as exc:
                    release_error = release_error or exc
            if release_error is not None and not original_error_active:
                raise release_error

    def _press_modifier(self, scan_code: int, held_modifiers: list[int]) -> None:
        self.send_scan_input(scan_code)
        held_modifiers.append(scan_code)
        time.sleep(self._rng.uniform(0.005, 0.015))

    def send_unicode_char(self, char: str) -> None:
        if user32 is None:
            return
        encoded = char.encode("utf-16-le")
        for index in range(0, len(encoded), 2):
            scan = int.from_bytes(encoded[index : index + 2], "little")
            self._send_unicode_unit(scan, keyup=False)
            self._send_unicode_unit(scan, keyup=True)

    def _send_unicode_unit(self, scan: int, *, keyup: bool) -> None:
        if user32 is None:
            return
        flags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if keyup else 0)
        input_struct = INPUT(
            type=INPUT_KEYBOARD,
            union=INPUT_UNION(
                ki=KEYBDINPUT(
                    wVk=0,
                    wScan=scan,
                    dwFlags=flags,
                    time=0,
                    dwExtraInfo=0,
                )
            ),
        )
        sent = user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))
        if sent != 1:
            error = ctypes.get_last_error()
            raise OSError(error, "Unicode SendInput failed")

    def press_backspace(self, hold_time_ms: int) -> None:
        self.press_key_scan(SC_BACKSPACE, hold_time_ms)

    def foreground_window(self) -> int | None:
        if user32 is None:
            return None
        handle = user32.GetForegroundWindow()
        return int(handle) if handle else None

    def foreground_window_title(self) -> str:
        if user32 is None:
            return ""
        handle = user32.GetForegroundWindow()
        if not handle:
            return ""
        length = user32.GetWindowTextLengthW(handle)
        if length <= 0:
            return "Unknown window"
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(handle, buffer, len(buffer))
        return buffer.value or "Unknown window"


@contextmanager
def high_resolution_timer() -> Iterator[None]:
    if winmm is None:
        yield
        return
    result = winmm.timeBeginPeriod(1)
    if result != 0:
        yield
        return
    try:
        yield
    finally:
        winmm.timeEndPeriod(1)
