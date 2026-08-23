from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5


class ValidationError(ValueError):
    """Raised when user-editable settings are invalid."""


def _as_float(data: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(data.get(key, default))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{key} must be a number") from exc


def _as_int(data: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(data.get(key, default))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{key} must be an integer") from exc


def _as_optional_int(data: dict[str, Any], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{key} must be an integer or null") from exc


@dataclass
class TypingProfile:
    name: str
    description: str
    base_delay_seconds: float
    delay_variation_seconds: float
    hold_time_ms: int
    pause_chance: float
    pause_min_seconds: float
    pause_max_seconds: float
    line_break_chance: float
    line_break_min_seconds: float
    line_break_max_seconds: float
    mistake_chance: float
    is_builtin: bool = False
    profile_id: str = field(default_factory=lambda: str(uuid4()))

    def validate(self) -> None:
        if not self.name.strip():
            raise ValidationError("Profile name is required")
        if self.base_delay_seconds <= 0:
            raise ValidationError("Base delay must be greater than zero")
        if self.delay_variation_seconds < 0:
            raise ValidationError("Delay variation cannot be negative")
        if self.base_delay_seconds - self.delay_variation_seconds < 0:
            raise ValidationError("Delay variation cannot exceed base delay")
        if not 5 <= self.hold_time_ms <= 200:
            raise ValidationError("Hold time must be between 5 and 200 ms")

        for field_name in (
            "pause_chance",
            "line_break_chance",
            "mistake_chance",
        ):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValidationError(f"{field_name} must be between 0 and 1")

        if self.pause_min_seconds < 0 or self.pause_max_seconds < 0:
            raise ValidationError("Pause durations cannot be negative")
        if self.line_break_min_seconds < 0 or self.line_break_max_seconds < 0:
            raise ValidationError("Line break durations cannot be negative")
        if self.pause_min_seconds > self.pause_max_seconds:
            raise ValidationError("Pause minimum cannot exceed pause maximum")
        if self.line_break_min_seconds > self.line_break_max_seconds:
            raise ValidationError("Line break minimum cannot exceed line break maximum")
        if not self.profile_id.strip():
            raise ValidationError("Profile ID is required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TypingProfile:
        profile = cls(
            name=str(data.get("name", "")).strip(),
            description=str(data.get("description", "")),
            base_delay_seconds=_as_float(data, "base_delay_seconds", 0.06),
            delay_variation_seconds=_as_float(data, "delay_variation_seconds", 0.03),
            hold_time_ms=_as_int(data, "hold_time_ms", 50),
            pause_chance=_as_float(data, "pause_chance", 0.02),
            pause_min_seconds=_as_float(data, "pause_min_seconds", 0.5),
            pause_max_seconds=_as_float(data, "pause_max_seconds", 2.5),
            line_break_chance=_as_float(data, "line_break_chance", 0.35),
            line_break_min_seconds=_as_float(data, "line_break_min_seconds", 3.0),
            line_break_max_seconds=_as_float(data, "line_break_max_seconds", 8.0),
            mistake_chance=_as_float(data, "mistake_chance", 0.06),
            is_builtin=_as_bool(data, "is_builtin", False),
            profile_id=str(data.get("profile_id", "")).strip()
            or str(uuid5(NAMESPACE_URL, f"keymimic-profile:{data.get('name', '')}")),
        )
        profile.validate()
        return profile


DEFAULT_START_PAUSE_HOTKEY = "Ctrl+Shift+Alt+V"
DEFAULT_STOP_HOTKEY = "Esc"
DEFAULT_SHOW_HIDE_HOTKEY = "Ctrl+Shift+Alt+K"


@dataclass
class HotkeySettings:
    start_pause_typing: str = DEFAULT_START_PAUSE_HOTKEY
    stop_typing: str = DEFAULT_STOP_HOTKEY
    show_hide_window: str = DEFAULT_SHOW_HIDE_HOTKEY

    def validate(self) -> None:
        from .hotkeys import validate_hotkey_settings

        validate_hotkey_settings(self)

    def normalized(self) -> HotkeySettings:
        from .hotkeys import normalize_hotkey

        return HotkeySettings(
            start_pause_typing=normalize_hotkey(self.start_pause_typing),
            stop_typing=normalize_hotkey(self.stop_typing),
            show_hide_window=normalize_hotkey(self.show_hide_window),
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> HotkeySettings:
        if not data:
            settings = cls()
        else:
            settings = cls(
                start_pause_typing=str(
                    data.get("start_pause_typing", DEFAULT_START_PAUSE_HOTKEY)
                ),
                stop_typing=str(data.get("stop_typing", DEFAULT_STOP_HOTKEY)),
                show_hide_window=str(
                    data.get("show_hide_window", DEFAULT_SHOW_HIDE_HOTKEY)
                ),
            )
        normalized = settings.normalized()
        normalized.validate()
        return normalized


@dataclass
class WindowSettings:
    width: int = 980
    height: int = 680
    x: int | None = None
    y: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> WindowSettings:
        if not data:
            return cls()
        return cls(
            width=max(760, _as_int(data, "width", cls.width)),
            height=max(560, _as_int(data, "height", cls.height)),
            x=_as_optional_int(data, "x"),
            y=_as_optional_int(data, "y"),
        )


@dataclass
class AppConfig:
    last_profile: str
    profiles: dict[str, TypingProfile]
    hotkeys: HotkeySettings = field(default_factory=HotkeySettings)
    profile_order: list[str] = field(default_factory=list)
    countdown_seconds: int = 5
    config_version: int = 2
    enable_tooltips: bool = True
    log_level: str = "INFO"
    start_minimized: bool = False
    show_tray_icon: bool = True
    close_to_tray: bool = False
    focus_guard_enabled: bool = True
    sounds_enabled: bool = True
    window: WindowSettings = field(default_factory=WindowSettings)

    def normalize(self) -> None:
        ordered = [
            name
            for index, name in enumerate(self.profile_order)
            if name in self.profiles and name not in self.profile_order[:index]
        ]
        ordered.extend(name for name in self.profiles if name not in ordered)
        self.profile_order = ordered
        self.profiles = {name: self.profiles[name] for name in ordered}
        if self.profiles and self.last_profile not in self.profiles:
            self.last_profile = next(iter(self.profiles))
        self.log_level = self.log_level.upper()
        if self.start_minimized and not self.show_tray_icon:
            self.start_minimized = False

    def validate(self) -> None:
        if not self.profiles:
            raise ValidationError("At least one profile is required")
        ids: set[str] = set()
        for key, profile in self.profiles.items():
            profile.validate()
            if key != profile.name:
                raise ValidationError(f"Profile key does not match profile name: {key}")
            if profile.profile_id in ids:
                raise ValidationError(f"Duplicate profile ID: {profile.profile_id}")
            ids.add(profile.profile_id)
        if self.profile_order != list(self.profiles):
            raise ValidationError("Profile order does not match stored profiles")
        if self.last_profile not in self.profiles:
            raise ValidationError("Selected profile does not exist")
        self.hotkeys.validate()
        if not 0 <= self.countdown_seconds <= 30:
            raise ValidationError("Countdown must be between 0 and 30 seconds")
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            raise ValidationError("Unsupported log level")
        if self.start_minimized and not self.show_tray_icon:
            raise ValidationError("Start minimized requires the tray icon")

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "last_profile": self.last_profile,
            "profile_order": list(self.profile_order),
            "profiles": {
                name: profile.to_dict()
                for name, profile in self.profiles.items()
                if not profile.is_builtin
            },
            "hotkeys": self.hotkeys.normalized().to_dict(),
            "countdown_seconds": self.countdown_seconds,
            "enable_tooltips": self.enable_tooltips,
            "log_level": self.log_level,
            "start_minimized": self.start_minimized,
            "show_tray_icon": self.show_tray_icon,
            "close_to_tray": self.close_to_tray,
            "focus_guard_enabled": self.focus_guard_enabled,
            "sounds_enabled": self.sounds_enabled,
            "window": self.window.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        profiles_data = data.get("profiles") or {}
        profiles = {
            str(name): TypingProfile.from_dict(profile_data)
            for name, profile_data in profiles_data.items()
        }
        config = cls(
            last_profile=str(data.get("last_profile", "")),
            profiles=profiles,
            hotkeys=HotkeySettings.from_dict(data.get("hotkeys")),
            profile_order=[
                str(name) for name in data.get("profile_order", []) if str(name)
            ],
            config_version=_as_int(data, "config_version", 2),
            countdown_seconds=_as_int(data, "countdown_seconds", 5),
            enable_tooltips=_as_bool(data, "enable_tooltips", True),
            log_level=str(data.get("log_level", "INFO")),
            start_minimized=_as_bool(data, "start_minimized", False),
            show_tray_icon=_as_bool(
                data,
                "show_tray_icon",
                _as_bool(data, "minimize_to_tray", True),
            ),
            close_to_tray=_as_bool(data, "close_to_tray", False),
            focus_guard_enabled=_as_bool(data, "focus_guard_enabled", True),
            sounds_enabled=_as_bool(data, "sounds_enabled", True),
            window=WindowSettings.from_dict(data.get("window")),
        )
        config.normalize()
        config.validate()
        return config


def _as_bool(data: dict[str, Any], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise ValidationError(f"{key} must be true or false")
