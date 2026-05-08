from __future__ import annotations

import configparser
import json
import os
from pathlib import Path
from typing import Any

from .hotkeys import normalize_hotkey
from .models import AppConfig, HotkeySettings, TypingProfile, WindowSettings
from .presets import default_custom_profile, default_profiles


APP_NAME = "KeyMimic"
CONFIG_FILENAME = "config.json"


def config_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / ".keymimic"


def config_path(base_dir: Path | None = None) -> Path:
    root = base_dir if base_dir is not None else config_dir()
    return root / CONFIG_FILENAME


def default_config() -> AppConfig:
    profiles = default_profiles()
    config = AppConfig(
        last_profile="Human",
        profiles=dict(profiles),
        hotkeys=HotkeySettings(),
        profile_order=list(profiles),
        countdown_seconds=5,
        enable_tooltips=True,
        log_level="INFO",
        start_minimized=False,
        minimize_to_tray=True,
        window=WindowSettings(),
    )
    config.validate()
    return config


def load_config(
    base_dir: Path | None = None,
    legacy_ini_path: Path | None = None,
) -> AppConfig:
    path = config_path(base_dir)
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            config = AppConfig.from_dict(json.load(handle))
        return config

    if legacy_ini_path is None:
        legacy_ini_path = Path.cwd() / "Humanizer_paste_Settings.ini"
    if legacy_ini_path.exists():
        config = migrate_ini_config(legacy_ini_path)
        save_config(config, base_dir=base_dir)
        return config

    config = default_config()
    save_config(config, base_dir=base_dir)
    return config


def save_config(config: AppConfig, base_dir: Path | None = None) -> Path:
    config.validate()
    path = config_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(config.to_dict(), handle, indent=2)
        handle.write("\n")
    return path


def migrate_ini_config(path: Path) -> AppConfig:
    parser = configparser.ConfigParser()
    parser.read_string(_read_legacy_ini_text(path), source=str(path))

    profiles = default_profiles()
    for custom_name in ("Custom 1", "Custom 2"):
        section = custom_name.replace(" ", "")
        profiles[custom_name] = _read_custom_profile(parser, section, custom_name)

    hotkey = parser.get("Settings", "Hotkey", fallback="Ctrl+Shift+Alt+V")
    last_profile = parser.get("Settings", "LastPreset", fallback="Human")
    if last_profile not in profiles:
        last_profile = "Human"

    config = AppConfig(
        last_profile=last_profile,
        profiles=dict(profiles),
        hotkeys=HotkeySettings(
            start_pause_typing=normalize_hotkey(hotkey, required=True),
            stop_typing="Esc",
            show_hide_window="Ctrl+Shift+Alt+K",
        ),
        profile_order=list(profiles),
        countdown_seconds=5,
        enable_tooltips=True,
        log_level="INFO",
        start_minimized=False,
        minimize_to_tray=True,
        window=WindowSettings(),
    )
    config.validate()
    return config


def _read_legacy_ini_text(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    if _looks_like_utf16_without_bom(data):
        encoding = "utf-16-le" if data[1:2] == b"\x00" else "utf-16-be"
        return data.decode(encoding)

    for encoding in ("utf-8", "mbcs", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeError:
            continue
        except LookupError:
            continue
    return data.decode("utf-8", errors="replace")


def _looks_like_utf16_without_bom(data: bytes) -> bool:
    sample = data[:128]
    if len(sample) < 4:
        return False
    odd_nulls = sample[1::2].count(0)
    even_nulls = sample[0::2].count(0)
    return odd_nulls > len(sample) // 4 or even_nulls > len(sample) // 4


def _read_custom_profile(
    parser: configparser.ConfigParser,
    section: str,
    name: str,
) -> TypingProfile:
    default = default_custom_profile(name)
    if not parser.has_section(section):
        return default

    def read_float(key: str, fallback: float) -> float:
        return parser.getfloat(section, key, fallback=fallback)

    def read_int(key: str, fallback: int) -> int:
        return parser.getint(section, key, fallback=fallback)

    profile = TypingProfile(
        name=name,
        description="Your custom configuration",
        base_delay_seconds=read_float("Speed", default.base_delay_seconds),
        delay_variation_seconds=read_float("Var", default.delay_variation_seconds),
        hold_time_ms=read_int("HoldTime", default.hold_time_ms),
        pause_chance=read_float("PauseChance", default.pause_chance),
        pause_min_seconds=read_float("PauseMin", default.pause_min_seconds),
        pause_max_seconds=read_float("PauseMax", default.pause_max_seconds),
        line_break_chance=read_float("BreakChance", default.line_break_chance),
        line_break_min_seconds=read_float(
            "BreakMin", default.line_break_min_seconds
        ),
        line_break_max_seconds=read_float(
            "BreakMax", default.line_break_max_seconds
        ),
        mistake_chance=read_float("MistakeChance", default.mistake_chance),
        is_builtin=False,
    )
    profile.validate()
    return profile


def import_profiles(path: Path) -> dict[str, TypingProfile]:
    with path.open("r", encoding="utf-8") as handle:
        data: Any = json.load(handle)
    if isinstance(data, dict) and "profiles" in data:
        data = data["profiles"]
    if not isinstance(data, dict):
        raise ValueError("Profile import file must contain an object")
    return {
        str(name): TypingProfile.from_dict(profile_data)
        for name, profile_data in data.items()
    }


def export_profiles(path: Path, profiles: dict[str, TypingProfile]) -> None:
    payload = {
        "profiles": {
            name: profile.to_dict()
            for name, profile in profiles.items()
            if not profile.is_builtin
        }
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
