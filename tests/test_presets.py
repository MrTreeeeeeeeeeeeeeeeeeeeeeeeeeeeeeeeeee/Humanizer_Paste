from keymimic.presets import built_in_profiles, default_profiles


def test_built_in_presets_match_ahk_values():
    profiles = built_in_profiles()

    assert profiles["Human"].base_delay_seconds == 0.065
    assert profiles["Human"].delay_variation_seconds == 0.030
    assert profiles["Human"].hold_time_ms == 55
    assert profiles["Human"].pause_chance == 0.020
    assert profiles["Human"].line_break_chance == 0.350
    assert profiles["Human"].mistake_chance == 0.060

    assert profiles["Super Human"].base_delay_seconds == 0.018
    assert profiles["Extreme Human"].hold_time_ms == 20
    assert profiles["Super Extreme Human"].hold_time_ms == 12


def test_default_profiles_include_custom_slots():
    profiles = default_profiles()

    assert "Custom 1" in profiles
    assert "Custom 2" in profiles
    assert not profiles["Custom 1"].is_builtin
    assert profiles["Human"].is_builtin
