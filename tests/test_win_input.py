from contextlib import suppress

from keymimic.win_input import KEYEVENTF_KEYUP, SC_LSHIFT, ScanInfo, WindowsInput


def test_modifiers_are_released_when_character_injection_fails():
    actions: list[tuple[int, int]] = []

    class FailingInput(WindowsInput):
        def char_to_scan_info(self, char: str):
            return ScanInfo(vk=65, scan=30, need_shift=True, need_ctrl_alt=False)

        def send_scan_input(self, scan_code: int, flags: int = 0) -> None:
            actions.append((scan_code, flags))

        def press_key_scan(self, *args, **kwargs):
            raise OSError("injection failed")

    backend = FailingInput(hold_jitter_ms=0)

    with suppress(OSError):
        backend.send_char("A", 5)

    assert actions[0] == (SC_LSHIFT, 0)
    assert actions[-1] == (SC_LSHIFT, KEYEVENTF_KEYUP)
