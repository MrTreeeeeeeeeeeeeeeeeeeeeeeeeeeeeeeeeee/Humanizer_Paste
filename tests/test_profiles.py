from dataclasses import replace

import pytest

from keymimic.config import default_config
from keymimic.models import ValidationError
from keymimic.profile_service import ProfileService


def test_profile_service_clones_with_a_stable_unique_id():
    config = default_config()
    service = ProfileService(config)

    clone = service.clone("Human")

    assert clone.name == "Human Copy"
    assert clone.profile_id != config.profiles["Human"].profile_id
    assert not clone.is_builtin


def test_profile_service_rejects_name_collisions():
    config = default_config()
    service = ProfileService(config)
    service.clone("Human", "Copy")

    with pytest.raises(ValidationError):
        service.rename("Custom 1", "Copy")


def test_profile_service_protects_builtins_and_deletes_customs():
    config = default_config()
    service = ProfileService(config)

    with pytest.raises(ValidationError):
        service.delete("Human")
    replacement = service.delete("Custom 1")

    assert "Custom 1" not in config.profiles
    assert replacement in config.profiles


def test_profile_import_resolves_collisions_before_mutating_config():
    config = default_config()
    service = ProfileService(config)
    source = replace(config.profiles["Custom 1"], is_builtin=False)

    names = service.add_imported({"first": source, "second": source})

    assert names == ["Custom 1 2", "Custom 1 3"]
    assert all(name in config.profiles for name in names)
