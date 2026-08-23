from __future__ import annotations

import random
from dataclasses import dataclass

from .models import TypingProfile


@dataclass(frozen=True)
class SpeedEstimate:
    wpm_average: int
    wpm_min: int
    wpm_max: int
    cpm_average: int
    seconds_per_character: float
    wpm_with_pauses: int


@dataclass(frozen=True)
class TypingPlanSummary:
    characters: int
    estimated_seconds: float
    estimated_seconds_with_pauses: float
    expected_mistakes: float
    expected_thinking_pauses: float
    expected_line_break_pauses: float
    wpm_average: int
    wpm_with_pauses: int


def clamp_delay(seconds: float) -> float:
    return max(0.001, seconds)


def human_delay_seconds(
    base_delay_seconds: float,
    variation_seconds: float,
    rng: random.Random | None = None,
) -> float:
    source = rng if rng is not None else random
    return clamp_delay(
        source.uniform(
            base_delay_seconds - variation_seconds,
            base_delay_seconds + variation_seconds,
        )
    )


def estimate_speed(profile: TypingProfile) -> SpeedEstimate:
    profile.validate()
    hold_seconds = profile.hold_time_ms / 1000.0
    min_delay = clamp_delay(
        profile.base_delay_seconds - profile.delay_variation_seconds
    )
    max_delay = clamp_delay(
        profile.base_delay_seconds + profile.delay_variation_seconds
    )

    seconds_per_character = hold_seconds + profile.base_delay_seconds
    seconds_per_character_min = hold_seconds + min_delay
    seconds_per_character_max = hold_seconds + max_delay

    cpm_average = round(60 / seconds_per_character)
    wpm_average = round(cpm_average / 5)
    wpm_min = round((60 / seconds_per_character_max) / 5)
    wpm_max = round((60 / seconds_per_character_min) / 5)

    average_pause = (profile.pause_min_seconds + profile.pause_max_seconds) / 2.0
    seconds_with_pauses = seconds_per_character + (profile.pause_chance * average_pause)
    wpm_with_pauses = round((60 / seconds_with_pauses) / 5)

    return SpeedEstimate(
        wpm_average=wpm_average,
        wpm_min=wpm_min,
        wpm_max=wpm_max,
        cpm_average=cpm_average,
        seconds_per_character=seconds_per_character,
        wpm_with_pauses=wpm_with_pauses,
    )


def summarize_typing_plan(text: str, profile: TypingProfile) -> TypingPlanSummary:
    profile.validate()
    characters = len(text)
    speed = estimate_speed(profile)
    base_seconds = speed.seconds_per_character * characters
    line_breaks = text.count("\n")
    thinking_characters = max(0, characters - line_breaks)

    average_pause = (profile.pause_min_seconds + profile.pause_max_seconds) / 2.0
    average_break = (
        profile.line_break_min_seconds + profile.line_break_max_seconds
    ) / 2.0
    expected_thinking_pauses = thinking_characters * profile.pause_chance
    expected_line_break_pauses = line_breaks * profile.line_break_chance
    pause_seconds = (
        expected_thinking_pauses * average_pause
        + expected_line_break_pauses * average_break
    )

    return TypingPlanSummary(
        characters=characters,
        estimated_seconds=base_seconds,
        estimated_seconds_with_pauses=base_seconds + pause_seconds,
        expected_mistakes=characters * profile.mistake_chance,
        expected_thinking_pauses=expected_thinking_pauses,
        expected_line_break_pauses=expected_line_break_pauses,
        wpm_average=speed.wpm_average,
        wpm_with_pauses=speed.wpm_with_pauses,
    )
