from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import AppConfig, HotkeySettings, TypingProfile, WindowSettings
from .presets import default_profiles


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


def load_config(base_dir: Path | None = None) -> AppConfig:
    path = config_path(base_dir)
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            config = AppConfig.from_dict(json.load(handle))
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
