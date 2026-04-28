from keymimic.presets import built_in_profiles
from keymimic.timing import estimate_speed, human_delay_seconds, summarize_typing_plan


def test_wpm_estimate_matches_ahk_formula():
    profile = built_in_profiles()["Human"]
    estimate = estimate_speed(profile)

    assert estimate.cpm_average == 500
    assert estimate.wpm_average == 100
    assert estimate.wpm_min == 80
    assert estimate.wpm_max == 133


def test_human_delay_never_goes_negative():
    for _ in range(100):
        assert human_delay_seconds(0.001, 10.0) >= 0.001


def test_typing_plan_counts_expected_pauses():
    profile = built_in_profiles()["Human"]
    summary = summarize_typing_plan("abc\nxyz", profile)

    assert summary.characters == 7
    assert summary.expected_line_break_pauses == profile.line_break_chance
    assert summary.expected_mistakes == 7 * profile.mistake_chance
