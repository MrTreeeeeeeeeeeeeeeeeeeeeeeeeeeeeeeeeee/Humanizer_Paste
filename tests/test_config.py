import json
from pathlib import Path

from keymimic.config import config_path, load_config, load_config_result, save_config
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


def test_config_persists_custom_profiles_but_refreshes_builtins(tmp_path: Path):
    config = load_config(base_dir=tmp_path)
    save_config(config, base_dir=tmp_path)

    raw = json.loads(config_path(tmp_path).read_text(encoding="utf-8"))

    assert raw["config_version"] == 2
    assert "Human" not in raw["profiles"]
    assert "Custom 1" in raw["profiles"]
    assert load_config(base_dir=tmp_path).profiles["Human"].is_builtin


def test_corrupt_config_is_preserved_and_recovered(tmp_path: Path):
    path = config_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{broken", encoding="utf-8")

    result = load_config_result(base_dir=tmp_path)

    assert result.warning
    assert result.config.last_profile == "Human"
    assert list(tmp_path.glob("config.corrupt-*.json"))


def test_atomic_save_creates_backup(tmp_path: Path):
    config = load_config(base_dir=tmp_path)
    config.countdown_seconds = 3
    save_config(config, base_dir=tmp_path)

    assert config_path(tmp_path).with_suffix(".json.bak").exists()
