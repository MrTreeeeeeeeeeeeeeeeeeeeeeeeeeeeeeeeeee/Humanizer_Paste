import platform

import pytest

from keymimic.hotkeys import (
    GlobalHotkeyManager,
    HotkeyParseError,
    normalize_hotkey,
    parse_hotkey,
    validate_hotkey_settings,
)
from keymimic.models import HotkeySettings


def test_normalizes_user_friendly_hotkeys():
    assert normalize_hotkey("Ctrl+Alt+Shift+v") == "Ctrl+Shift+Alt+V"
    assert normalize_hotkey("+^!v") == "Ctrl+Shift+Alt+V"
    assert normalize_hotkey("escape") == "Esc"


def test_parse_rejects_invalid_hotkey_strings():
    with pytest.raises(HotkeyParseError):
        parse_hotkey("Ctrl+Shift")
    with pytest.raises(HotkeyParseError):
        parse_hotkey("Ctrl+A+B")


def test_duplicate_hotkeys_are_rejected():
    settings = HotkeySettings(
        start_pause_typing="Ctrl+Shift+Alt+V",
        stop_typing="Ctrl+Shift+Alt+V",
        show_hide_window="Ctrl+Shift+Alt+K",
    )

    with pytest.raises(HotkeyParseError):
        validate_hotkey_settings(settings)


def test_stop_hotkey_is_required():
    settings = HotkeySettings(
        start_pause_typing="Ctrl+Shift+Alt+V",
        stop_typing="",
        show_hide_window="",
    )

    with pytest.raises(HotkeyParseError):
        validate_hotkey_settings(settings)


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows API required")
def test_global_hotkey_manager_can_apply_empty_bindings():
    manager = GlobalHotkeyManager()
    try:
        assert manager.apply_bindings({}) == {}
    finally:
        manager.stop()
