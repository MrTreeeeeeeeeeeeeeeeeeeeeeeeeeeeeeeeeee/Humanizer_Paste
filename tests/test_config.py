from pathlib import Path

from keymimic.config import config_path, load_config, migrate_ini_config, save_config
from keymimic.models import HotkeySettings


def test_config_round_trip_preserves_hotkeys(tmp_path: Path):
    config = load_config(base_dir=tmp_path, legacy_ini_path=tmp_path / "missing.ini")
    config.hotkeys = HotkeySettings(
        start_typing="Ctrl+Shift+Alt+X",
        pause_resume_typing="Ctrl+Shift+Alt+Y",
        stop_typing="F12",
        show_hide_window="Ctrl+Shift+Alt+Z",
    ).normalized()
    save_config(config, base_dir=tmp_path)

    loaded = load_config(base_dir=tmp_path)

    assert loaded.hotkeys.start_typing == "Ctrl+Shift+Alt+X"
    assert loaded.hotkeys.pause_resume_typing == "Ctrl+Shift+Alt+Y"
    assert loaded.hotkeys.stop_typing == "F12"
    assert loaded.hotkeys.show_hide_window == "Ctrl+Shift+Alt+Z"
    assert config_path(tmp_path).exists()


def test_config_round_trip_preserves_profile_order(tmp_path: Path):
    config = load_config(base_dir=tmp_path, legacy_ini_path=tmp_path / "missing.ini")
    config.profile_order = ["Custom 2", "Human", "Custom 1"]
    save_config(config, base_dir=tmp_path)

    loaded = load_config(base_dir=tmp_path)

    assert loaded.profile_order[:3] == ["Custom 2", "Human", "Custom 1"]
    assert list(loaded.profiles)[:3] == ["Custom 2", "Human", "Custom 1"]


def test_ini_migration_maps_old_hotkey_and_last_profile(tmp_path: Path):
    ini = tmp_path / "Humanizer_paste_Settings.ini"
    ini.write_text(
        "[Settings]\nHotkey=+^!v\nLastPreset=Super Human\n"
        "[Custom1]\nSpeed=0.04\nVar=0.01\nHoldTime=44\n",
        encoding="utf-8",
    )

    config = migrate_ini_config(ini)

    assert config.hotkeys.start_typing == "Ctrl+Shift+Alt+V"
    assert config.hotkeys.stop_typing == "Esc"
    assert config.last_profile == "Super Human"
    assert config.profiles["Custom 1"].base_delay_seconds == 0.04
    assert config.profiles["Custom 1"].hold_time_ms == 44


def test_ini_migration_reads_autohotkey_utf16_ini(tmp_path: Path):
    ini = tmp_path / "Humanizer_paste_Settings.ini"
    ini.write_text(
        "[Settings]\r\nHotkey=+^!v\r\nLastPreset=Super Human\r\n",
        encoding="utf-16",
    )

    config = migrate_ini_config(ini)

    assert config.hotkeys.start_typing == "Ctrl+Shift+Alt+V"
    assert config.last_profile == "Super Human"


def test_load_config_migrates_when_json_missing(tmp_path: Path):
    ini = tmp_path / "settings.ini"
    ini.write_text("[Settings]\nHotkey=^!x\nLastPreset=Human\n", encoding="utf-8")

    config = load_config(base_dir=tmp_path, legacy_ini_path=ini)

    assert config.hotkeys.start_typing == "Ctrl+Alt+X"
    assert config_path(tmp_path).exists()
