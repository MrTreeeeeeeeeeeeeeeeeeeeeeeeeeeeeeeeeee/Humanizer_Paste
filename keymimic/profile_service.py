from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from .models import AppConfig, TypingProfile, ValidationError


class ProfileService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def unique_name(self, requested: str) -> str:
        base = requested.strip() or "Profile"
        if base not in self.config.profiles:
            return base
        index = 2
        while f"{base} {index}" in self.config.profiles:
            index += 1
        return f"{base} {index}"

    def clone(
        self, source_name: str, requested_name: str | None = None
    ) -> TypingProfile:
        source = self.config.profiles[source_name]
        name = self.unique_name(requested_name or f"{source.name} Copy")
        profile = replace(
            source,
            name=name,
            description=f"Custom profile copied from {source.name}",
            is_builtin=False,
            profile_id=str(uuid4()),
        )
        self.add(profile)
        return profile

    def add(self, profile: TypingProfile) -> None:
        profile.validate()
        if profile.name in self.config.profiles:
            raise ValidationError(f"A profile named {profile.name!r} already exists")
        if any(
            existing.profile_id == profile.profile_id
            for existing in self.config.profiles.values()
        ):
            profile.profile_id = str(uuid4())
        self.config.profiles[profile.name] = profile
        self.config.profile_order.append(profile.name)
        self.select(profile.name)

    def rename(self, old_name: str, new_name: str) -> TypingProfile:
        profile = self.config.profiles[old_name]
        requested = new_name.strip()
        if not requested:
            raise ValidationError("Profile name is required")
        if requested != old_name and requested in self.config.profiles:
            raise ValidationError(f"A profile named {requested!r} already exists")
        if requested == old_name:
            return profile

        updated = replace(profile, name=requested)
        items = list(self.config.profiles.items())
        self.config.profiles = {
            (requested if name == old_name else name): (
                updated if name == old_name else value
            )
            for name, value in items
        }
        self.config.profile_order = [
            requested if name == old_name else name
            for name in self.config.profile_order
        ]
        self.select(requested)
        return updated

    def replace(self, old_name: str, profile: TypingProfile) -> TypingProfile:
        if self.config.profiles[old_name].is_builtin:
            raise ValidationError("Built-in profiles cannot be changed")
        if profile.name != old_name:
            self.rename(old_name, profile.name)
        self.config.profiles[profile.name] = profile
        self.select(profile.name)
        return profile

    def delete(self, name: str) -> str:
        profile = self.config.profiles[name]
        if profile.is_builtin:
            raise ValidationError("Built-in profiles cannot be deleted")
        if len(self.config.profiles) <= 1:
            raise ValidationError("At least one profile is required")
        index = self.config.profile_order.index(name)
        del self.config.profiles[name]
        self.config.profile_order.remove(name)
        replacement_index = min(index, len(self.config.profile_order) - 1)
        replacement = self.config.profile_order[replacement_index]
        self.select(replacement)
        return replacement

    def add_imported(self, profiles: dict[str, TypingProfile]) -> list[str]:
        prepared: list[TypingProfile] = []
        reserved_names = set(self.config.profiles)
        reserved_ids = {profile.profile_id for profile in self.config.profiles.values()}
        for source_name, profile in profiles.items():
            base_name = (profile.name or source_name).strip() or "Profile"
            name = base_name
            index = 2
            while name in reserved_names:
                name = f"{base_name} {index}"
                index += 1
            profile = replace(
                profile,
                name=name,
                is_builtin=False,
                profile_id=str(uuid4()),
            )
            profile.validate()
            while profile.profile_id in reserved_ids:
                profile.profile_id = str(uuid4())
            reserved_names.add(profile.name)
            reserved_ids.add(profile.profile_id)
            prepared.append(profile)

        for profile in prepared:
            self.config.profiles[profile.name] = profile
            self.config.profile_order.append(profile.name)
        if prepared:
            self.select(prepared[-1].name)
        return [profile.name for profile in prepared]

    def move(self, name: str, delta: int) -> bool:
        order = list(self.config.profile_order)
        index = order.index(name)
        new_index = index + delta
        if new_index < 0 or new_index >= len(order):
            return False
        order[index], order[new_index] = order[new_index], order[index]
        self.config.profile_order = order
        self.config.profiles = {
            profile_name: self.config.profiles[profile_name] for profile_name in order
        }
        return True

    def select(self, name: str) -> None:
        if name not in self.config.profiles:
            raise ValidationError(f"Unknown profile: {name}")
        self.config.last_profile = name
