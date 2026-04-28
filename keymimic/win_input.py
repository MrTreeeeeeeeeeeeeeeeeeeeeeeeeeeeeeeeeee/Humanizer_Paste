from __future__ import annotations

import ctypes
import platform
import random
import time
from contextlib import contextmanager
from dataclasses import dataclass


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


if is_windows():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    winmm = ctypes.WinDLL("winmm", use_last_error=True)
else:
    user32 = None
    winmm = None


ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


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


@dataclass(frozen=True)
class ScanInfo:
    vk: int
    scan: int
    need_shift: bool
    need_ctrl_alt: bool


class WindowsInput:
    def __init__(self, hold_jitter_ms: int = 10) -> None:
        self.hold_jitter_ms = hold_jitter_ms

    @property
    def available(self) -> bool:
        return user32 is not None

    def send_scan_input(self, scan_code: int, flags: int = 0) -> None:
        if user32 is None:
            return
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
        self.send_scan_input(scan_code, extended)
        actual_hold = hold_time_ms + random.randint(
            -self.hold_jitter_ms,
            self.hold_jitter_ms,
        )
        time.sleep(max(0.005, actual_hold / 1000.0))
        self.send_scan_input(scan_code, extended | KEYEVENTF_KEYUP)

    def char_to_scan_info(self, char: str) -> ScanInfo | None:
        if user32 is None:
            return None
        result = ctypes.c_short(user32.VkKeyScanW(ord(char))).value
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

        if info.need_ctrl_alt:
            self.send_scan_input(SC_LCTRL)
            time.sleep(random.uniform(0.005, 0.015))
            self.send_scan_input(SC_LALT)
            time.sleep(random.uniform(0.005, 0.015))
        if info.need_shift:
            self.send_scan_input(SC_LSHIFT)
            time.sleep(random.uniform(0.005, 0.015))

        self.press_key_scan(info.scan, hold_time_ms)

        if info.need_shift:
            time.sleep(random.uniform(0.005, 0.015))
            self.send_scan_input(SC_LSHIFT, KEYEVENTF_KEYUP)
        if info.need_ctrl_alt:
            time.sleep(random.uniform(0.005, 0.015))
            self.send_scan_input(SC_LALT, KEYEVENTF_KEYUP)
            time.sleep(random.uniform(0.005, 0.015))
            self.send_scan_input(SC_LCTRL, KEYEVENTF_KEYUP)

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


@contextmanager
def high_resolution_timer():
    if winmm is None:
        yield
        return
    winmm.timeBeginPeriod(1)
    try:
        yield
    finally:
        winmm.timeEndPeriod(1)
