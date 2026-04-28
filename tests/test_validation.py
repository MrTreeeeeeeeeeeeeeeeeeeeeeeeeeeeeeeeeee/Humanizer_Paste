import pytest

from keymimic.models import TypingProfile, ValidationError
from keymimic.presets import default_custom_profile


def test_profile_validation_rejects_bad_chance():
    profile = default_custom_profile("Bad")
    profile.pause_chance = 1.5

    with pytest.raises(ValidationError):
        profile.validate()


def test_profile_validation_rejects_negative_delay():
    profile = default_custom_profile("Bad")
    profile.base_delay_seconds = 0

    with pytest.raises(ValidationError):
        profile.validate()


def test_profile_validation_rejects_reversed_ranges():
    profile = default_custom_profile("Bad")
    profile.pause_min_seconds = 5
    profile.pause_max_seconds = 1

    with pytest.raises(ValidationError):
        profile.validate()


def test_profile_from_dict_validates_values():
    data = default_custom_profile("Good").to_dict()
    data["hold_time_ms"] = 300

    with pytest.raises(ValidationError):
        TypingProfile.from_dict(data)
