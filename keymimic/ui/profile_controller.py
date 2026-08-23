from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QWidget,
)

from ..config import export_profiles, import_profiles
from ..models import AppConfig, TypingProfile, ValidationError
from ..profile_service import ProfileService
from ..timing import estimate_speed
from .pauses_panel import PausesPanel
from .profile_panel import ProfileSidebar
from .realism_panel import RealismPanel
from .speed_panel import SpeedPanel


class ProfileController(QObject):
    save_requested = Signal()
    status_changed = Signal(str)
    validation_changed = Signal(str)
    preview_profile_changed = Signal(object)

    def __init__(
        self,
        owner: QWidget,
        config: AppConfig,
        sidebar: ProfileSidebar,
        name_edit: QLineEdit,
        save_button: QPushButton,
        description_label: QLabel,
        speed: SpeedPanel,
        pauses: PausesPanel,
        realism: RealismPanel,
    ) -> None:
        super().__init__(owner)
        self.owner = owner
        self.config = config
        self.service = ProfileService(config)
        self.sidebar = sidebar
        self.name_edit = name_edit
        self.save_button = save_button
        self.description_label = description_label
        self.speed = speed
        self.pauses = pauses
        self.realism = realism
        self.current_name = config.last_profile
        self._loading = False
        self._dirty = False
        self._session_running = False

        self._estimate_timer = QTimer(self)
        self._estimate_timer.setSingleShot(True)
        self._estimate_timer.setInterval(120)
        self._estimate_timer.timeout.connect(self._update_estimate)
        self._connect()

    def initialize(self) -> None:
        self.refresh()
        self.load(self.current_name)

    def refresh(self) -> None:
        self.config.validate()
        self.sidebar.set_profiles(list(self.config.profile_order), self.current_name)

    def current_profile_snapshot(self) -> TypingProfile:
        return self._profile_from_fields()

    def set_session_running(self, running: bool) -> None:
        self._session_running = running
        profile = self.config.profiles[self.current_name]
        self._set_value_editing_enabled(not profile.is_builtin and not running)
        self.name_edit.setEnabled(not profile.is_builtin and not running)
        self.save_button.setEnabled(not profile.is_builtin and not running)
        self.sidebar.setEnabled(not running)

    def load(self, name: str) -> None:
        profile = self.config.profiles[name]
        self._loading = True
        try:
            self.current_name = name
            self.name_edit.setText(profile.name)
            self.name_edit.setReadOnly(profile.is_builtin)
            self.description_label.setText(profile.description)
            self.speed.base_delay.setValue(profile.base_delay_seconds)
            self.speed.variation.setValue(profile.delay_variation_seconds)
            self.speed.hold_time.setValue(profile.hold_time_ms)
            self.pauses.pause_chance.setValue(profile.pause_chance)
            self.pauses.pause_min.setValue(profile.pause_min_seconds)
            self.pauses.pause_max.setValue(profile.pause_max_seconds)
            self.pauses.line_break_chance.setValue(profile.line_break_chance)
            self.pauses.line_break_min.setValue(profile.line_break_min_seconds)
            self.pauses.line_break_max.setValue(profile.line_break_max_seconds)
            self.realism.mistake_chance.setValue(profile.mistake_chance)
            self.sidebar.delete_button.setEnabled(not profile.is_builtin)
            self._dirty = False
            self.set_session_running(self._session_running)
        finally:
            self._loading = False
        self._update_estimate()

    def _connect(self) -> None:
        self.sidebar.profile_selected.connect(self._select)
        self.sidebar.add_requested.connect(self._add)
        self.sidebar.duplicate_requested.connect(self._duplicate)
        self.sidebar.delete_requested.connect(self._delete)
        self.sidebar.import_requested.connect(self._import)
        self.sidebar.export_requested.connect(self._export)
        self.sidebar.move_up_requested.connect(lambda: self._move(-1))
        self.sidebar.move_down_requested.connect(lambda: self._move(1))
        self.save_button.clicked.connect(self._save)
        self.name_edit.textEdited.connect(self._field_edited)
        for control in self._controls():
            control.valueChanged.connect(self._field_edited)  # type: ignore[attr-defined]

    def _select(self, name: str) -> None:
        if self._loading or not name or name not in self.config.profiles:
            return
        if name == self.current_name:
            return
        if not self._resolve_dirty():
            self._reselect()
            return
        self.current_name = name
        self.service.select(name)
        self.load(name)
        self.save_requested.emit()

    def _resolve_dirty(self) -> bool:
        current = self.config.profiles[self.current_name]
        if not self._dirty or current.is_builtin:
            return True
        choice = QMessageBox.question(
            self.owner,
            "Unsaved profile changes",
            f"Save changes to {current.name}?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if choice == QMessageBox.StandardButton.Cancel:
            return False
        if choice == QMessageBox.StandardButton.Save:
            return self._save()
        self._dirty = False
        return True

    def _reselect(self) -> None:
        self._loading = True
        self.sidebar.set_profiles(list(self.config.profile_order), self.current_name)
        self._loading = False

    def _profile_from_fields(self) -> TypingProfile:
        current = self.config.profiles[self.current_name]
        profile = TypingProfile(
            name=self.name_edit.text().strip() or current.name,
            description=current.description,
            base_delay_seconds=self.speed.base_delay.value(),
            delay_variation_seconds=self.speed.variation.value(),
            hold_time_ms=self.speed.hold_time.value(),
            pause_chance=self.pauses.pause_chance.value(),
            pause_min_seconds=self.pauses.pause_min.value(),
            pause_max_seconds=self.pauses.pause_max.value(),
            line_break_chance=self.pauses.line_break_chance.value(),
            line_break_min_seconds=self.pauses.line_break_min.value(),
            line_break_max_seconds=self.pauses.line_break_max.value(),
            mistake_chance=self.realism.mistake_chance.value(),
            is_builtin=current.is_builtin,
            profile_id=current.profile_id,
        )
        profile.validate()
        return profile

    def _save(self) -> bool:
        try:
            current = self.config.profiles[self.current_name]
            if current.is_builtin:
                raise ValidationError(
                    "Built-in profiles are read-only. Duplicate one to customize it."
                )
            profile = self._profile_from_fields()
            self.service.replace(self.current_name, profile)
            self.current_name = profile.name
            self._dirty = False
            self.validation_changed.emit("")
            self.save_requested.emit()
            self.refresh()
            self.load(profile.name)
            self.status_changed.emit(f"Saved profile: {profile.name}")
            return True
        except ValidationError as exc:
            self.validation_changed.emit(str(exc))
            return False

    def _add(self) -> None:
        profile = self.service.clone(
            self.current_name, self.service.unique_name("New Profile")
        )
        profile.description = "Custom profile"
        self.current_name = profile.name
        self._after_mutation(profile.name)

    def _duplicate(self) -> None:
        profile = self.service.clone(self.current_name)
        self.current_name = profile.name
        self._after_mutation(profile.name)

    def _delete(self) -> None:
        current = self.config.profiles[self.current_name]
        if current.is_builtin:
            return
        choice = QMessageBox.question(
            self.owner,
            "Delete profile",
            f"Permanently delete the profile {current.name!r}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        try:
            replacement = self.service.delete(current.name)
        except ValidationError as exc:
            QMessageBox.warning(self.owner, "Could not delete profile", str(exc))
            return
        self.current_name = replacement
        self._after_mutation(replacement)

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.owner, "Import Profiles", str(Path.home()), "JSON files (*.json)"
        )
        if not path:
            return
        try:
            names = self.service.add_imported(import_profiles(Path(path)))
            if names:
                self.current_name = names[-1]
            self._after_mutation(self.current_name)
            self.status_changed.emit(f"Imported {len(names)} profiles")
        except (OSError, ValueError, ValidationError) as exc:
            QMessageBox.warning(self.owner, "Import failed", str(exc))

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self.owner,
            "Export Custom Profiles",
            str(Path.home() / "keymimic_profiles.json"),
            "JSON files (*.json)",
        )
        if not path:
            return
        try:
            export_profiles(Path(path), self.config.profiles)
            self.status_changed.emit("Profiles exported")
        except OSError as exc:
            QMessageBox.warning(self.owner, "Export failed", str(exc))

    def _move(self, delta: int) -> None:
        name = self.sidebar.current_profile()
        if name and self.service.move(name, delta):
            self.current_name = name
            self.save_requested.emit()
            self.refresh()

    def _after_mutation(self, name: str) -> None:
        self.save_requested.emit()
        self.refresh()
        self.load(name)

    def _field_edited(self, *_args: object) -> None:
        if self._loading:
            return
        self._dirty = True
        self._estimate_timer.start()

    def _update_estimate(self) -> None:
        try:
            profile = self._profile_from_fields()
            estimate = estimate_speed(profile)
            self.speed.estimate_label.setText(
                f"Estimated speed: {estimate.wpm_average} WPM ({estimate.wpm_min}-{estimate.wpm_max} range), {estimate.cpm_average} CPM. "
                f"With thinking pauses: {estimate.wpm_with_pauses} WPM."
            )
            self.validation_changed.emit("")
            self.preview_profile_changed.emit(profile)
        except ValidationError as exc:
            self.validation_changed.emit(str(exc))

    def _controls(self) -> list[QWidget]:
        return self.speed.controls() + self.pauses.controls() + self.realism.controls()

    def _set_value_editing_enabled(self, enabled: bool) -> None:
        for control in self._controls():
            control.setEnabled(enabled)
