from pathlib import Path

from keymimic.config import config_path, load_config, save_config
from keymimic.models import HotkeySettings


def test_config_round_trip_preserves_hotkeys(tmp_path: Path):
    config = load_config(base_dir=tmp_path)
    config.hotkeys = HotkeySettings(
        start_pause_typing="Ctrl+Shift+Alt+X",
        stop_typing="F12",
        show_hide_window="Ctrl+Shift+Alt+Z",
    ).normalized()
    save_config(config, base_dir=tmp_path)

    loaded = load_config(base_dir=tmp_path)

    assert loaded.hotkeys.start_pause_typing == "Ctrl+Shift+Alt+X"
    assert loaded.hotkeys.stop_typing == "F12"
    assert loaded.hotkeys.show_hide_window == "Ctrl+Shift+Alt+Z"
    assert config_path(tmp_path).exists()


def test_load_config_creates_default_json_when_missing(tmp_path: Path):
    path = config_path(tmp_path)

    config = load_config(base_dir=tmp_path)

    assert path.exists()
    assert config.last_profile == "Human"
    assert config.hotkeys.start_pause_typing == "Ctrl+Shift+Alt+V"
    assert config.hotkeys.stop_typing == "Esc"
    assert config.hotkeys.show_hide_window == "Ctrl+Shift+Alt+K"


def test_config_round_trip_preserves_profile_order(tmp_path: Path):
    config = load_config(base_dir=tmp_path)
    config.profile_order = ["Custom 2", "Human", "Custom 1"]
    save_config(config, base_dir=tmp_path)

    loaded = load_config(base_dir=tmp_path)

    assert loaded.profile_order[:3] == ["Custom 2", "Human", "Custom 1"]
    assert list(loaded.profiles)[:3] == ["Custom 2", "Human", "Custom 1"]
