from __future__ import annotations

from collections import OrderedDict

from .models import TypingProfile


def built_in_profiles() -> OrderedDict[str, TypingProfile]:
    profiles: OrderedDict[str, TypingProfile] = OrderedDict()
    profiles["Human"] = TypingProfile(
        name="Human",
        description="Natural typist around 100 WPM",
        base_delay_seconds=0.065,
        delay_variation_seconds=0.030,
        hold_time_ms=55,
        pause_chance=0.020,
        pause_min_seconds=0.500,
        pause_max_seconds=2.500,
        line_break_chance=0.350,
        line_break_min_seconds=3.000,
        line_break_max_seconds=8.000,
        mistake_chance=0.060,
        is_builtin=True,
        profile_id="builtin:human",
    )
    profiles["Super Human"] = TypingProfile(
        name="Super Human",
        description="Very fast typist around 250 WPM",
        base_delay_seconds=0.018,
        delay_variation_seconds=0.009,
        hold_time_ms=30,
        pause_chance=0.010,
        pause_min_seconds=0.300,
        pause_max_seconds=1.500,
        line_break_chance=0.200,
        line_break_min_seconds=1.500,
        line_break_max_seconds=4.000,
        mistake_chance=0.030,
        is_builtin=True,
        profile_id="builtin:super-human",
    )
    profiles["Extreme Human"] = TypingProfile(
        name="Extreme Human",
        description="Extremely fast typist around 450 WPM",
        base_delay_seconds=0.0067,
        delay_variation_seconds=0.0030,
        hold_time_ms=20,
        pause_chance=0.005,
        pause_min_seconds=0.200,
        pause_max_seconds=0.800,
        line_break_chance=0.100,
        line_break_min_seconds=1.000,
        line_break_max_seconds=2.500,
        mistake_chance=0.015,
        is_builtin=True,
        profile_id="builtin:extreme-human",
    )
    profiles["Super Extreme Human"] = TypingProfile(
        name="Super Extreme Human",
        description="Near max speed around 650 WPM",
        base_delay_seconds=0.0065,
        delay_variation_seconds=0.0030,
        hold_time_ms=12,
        pause_chance=0.002,
        pause_min_seconds=0.100,
        pause_max_seconds=0.400,
        line_break_chance=0.050,
        line_break_min_seconds=0.500,
        line_break_max_seconds=1.500,
        mistake_chance=0.008,
        is_builtin=True,
        profile_id="builtin:super-extreme-human",
    )
    return profiles


def default_custom_profile(name: str) -> TypingProfile:
    return TypingProfile(
        name=name,
        description="Your custom configuration",
        base_delay_seconds=0.060,
        delay_variation_seconds=0.035,
        hold_time_ms=50,
        pause_chance=0.020,
        pause_min_seconds=0.500,
        pause_max_seconds=2.500,
        line_break_chance=0.350,
        line_break_min_seconds=3.000,
        line_break_max_seconds=8.000,
        mistake_chance=0.060,
        is_builtin=False,
    )


def default_profiles() -> OrderedDict[str, TypingProfile]:
    profiles = built_in_profiles()
    profiles["Custom 1"] = default_custom_profile("Custom 1")
    profiles["Custom 2"] = default_custom_profile("Custom 2")
    return profiles
