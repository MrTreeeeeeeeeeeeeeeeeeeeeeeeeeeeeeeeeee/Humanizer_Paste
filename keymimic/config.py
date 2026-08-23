from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import AppConfig, HotkeySettings, TypingProfile, WindowSettings
from .presets import default_profiles

APP_NAME = "KeyMimic"
CONFIG_FILENAME = "config.json"
CURRENT_CONFIG_VERSION = 2


@dataclass(frozen=True, slots=True)
class ConfigLoadResult:
    config: AppConfig
    warning: str = ""
    recovered_from: Path | None = None


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
        config_version=CURRENT_CONFIG_VERSION,
        last_profile="Human",
        profiles=dict(profiles),
        hotkeys=HotkeySettings(),
        profile_order=list(profiles),
        countdown_seconds=5,
        enable_tooltips=True,
        log_level="INFO",
        start_minimized=False,
        show_tray_icon=True,
        close_to_tray=False,
        focus_guard_enabled=True,
        sounds_enabled=True,
        window=WindowSettings(),
    )
    config.normalize()
    config.validate()
    return config


def _merge_current_builtins(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    raw_profiles = migrated.get("profiles")
    saved_profiles = raw_profiles if isinstance(raw_profiles, dict) else {}
    defaults = default_profiles()
    merged: dict[str, Any] = {
        name: profile.to_dict()
        for name, profile in defaults.items()
        if profile.is_builtin
    }
    for name, raw_profile in saved_profiles.items():
        if not isinstance(raw_profile, dict):
            raise ValueError(f"Profile {name!r} must be an object")
        if name in merged and bool(raw_profile.get("is_builtin", False)):
            continue
        merged[str(name)] = raw_profile

    if not saved_profiles:
        for name, profile in defaults.items():
            if not profile.is_builtin:
                merged[name] = profile.to_dict()

    saved_order = migrated.get("profile_order")
    order = [str(name) for name in saved_order] if isinstance(saved_order, list) else []
    order = [name for name in order if name in merged]
    order.extend(name for name in merged if name not in order)

    migrated["config_version"] = CURRENT_CONFIG_VERSION
    migrated["profiles"] = merged
    migrated["profile_order"] = order
    return migrated


def load_config_result(base_dir: Path | None = None) -> ConfigLoadResult:
    path = config_path(base_dir)
    if not path.exists():
        config = default_config()
        save_config(config, base_dir=base_dir, create_backup=False)
        return ConfigLoadResult(config=config)

    try:
        data = _read_json_object(path)
        config = AppConfig.from_dict(_merge_current_builtins(data))
        return ConfigLoadResult(config=config)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as primary_error:
        corrupt_copy = _preserve_corrupt_file(path)
        backup = path.with_suffix(path.suffix + ".bak")
        if backup.exists():
            try:
                data = _read_json_object(backup)
                config = AppConfig.from_dict(_merge_current_builtins(data))
                save_config(config, base_dir=base_dir, create_backup=False)
                return ConfigLoadResult(
                    config=config,
                    warning=(
                        "Settings were recovered from the automatic backup because "
                        f"config.json was invalid: {primary_error}"
                    ),
                    recovered_from=backup,
                )
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass

        config = default_config()
        save_config(config, base_dir=base_dir, create_backup=False)
        return ConfigLoadResult(
            config=config,
            warning=(
                "Settings were reset to safe defaults because config.json could not "
                f"be read: {primary_error}. The damaged file was preserved as "
                f"{corrupt_copy.name}."
            ),
            recovered_from=corrupt_copy,
        )


def load_config(base_dir: Path | None = None) -> AppConfig:
    return load_config_result(base_dir).config


def save_config(
    config: AppConfig,
    base_dir: Path | None = None,
    *,
    create_backup: bool = True,
) -> Path:
    config.config_version = CURRENT_CONFIG_VERSION
    config.normalize()
    config.validate()
    path = config_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(config.to_dict(), indent=2, ensure_ascii=False) + "\n"

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        if create_backup and path.exists():
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return path


def import_profiles(path: Path) -> dict[str, TypingProfile]:
    data: Any = _read_json(path)
    if isinstance(data, dict) and "profiles" in data:
        data = data["profiles"]
    if not isinstance(data, dict):
        raise ValueError("Profile import file must contain an object")
    profiles: dict[str, TypingProfile] = {}
    for name, profile_data in data.items():
        if not isinstance(profile_data, dict):
            raise ValueError(f"Profile {name!r} must be an object")
        profile = TypingProfile.from_dict(profile_data)
        profile.is_builtin = False
        profiles[str(name)] = profile
    return profiles


def export_profiles(path: Path, profiles: dict[str, TypingProfile]) -> None:
    payload = {
        "config_version": CURRENT_CONFIG_VERSION,
        "profiles": {
            name: profile.to_dict()
            for name, profile in profiles.items()
            if not profile.is_builtin
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(path, payload)


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_json_object(path: Path) -> dict[str, Any]:
    data = _read_json(path)
    if not isinstance(data, dict):
        raise ValueError("Settings file must contain a JSON object")
    return data


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _preserve_corrupt_file(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = path.with_name(f"config.corrupt-{stamp}.json")
    try:
        shutil.copy2(path, destination)
    except OSError:
        return path
    return destination
