from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QMenu,
)

from ..clipboard import get_clipboard_text
from ..config import export_profiles, import_profiles, save_config
from ..hotkeys import GlobalHotkeyManager, HotkeyError
from ..models import AppConfig, HotkeySettings, TypingProfile, ValidationError
from ..timing import estimate_speed, summarize_typing_plan
from ..typing_engine import TypingEngine, TypingEvent
from .hotkeys_panel import HotkeysPanel
from .pauses_panel import PausesPanel
from .preview_panel import PreviewPanel
from .profile_panel import ProfileSidebar
from .realism_panel import RealismPanel
from .speed_panel import SpeedPanel
from .status_bar import StatusBarWidget


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    engine_event_received = Signal(object)
    hotkey_triggered = Signal(str)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.current_profile_name = config.last_profile
        self._typing_hotkeys_active = False

        self.engine = TypingEngine(event_callback=self.engine_event_received.emit)
        self.hotkeys = GlobalHotkeyManager(callback=self.hotkey_triggered.emit)

        self.setWindowTitle("KeyMimic")
        self.resize(config.window.width, config.window.height)
        if config.window.x is not None and config.window.y is not None:
            self.move(config.window.x, config.window.y)

        self._build_ui()
        self._connect_signals()
        self._load_profile(self.current_profile_name)
        self._refresh_profiles()
        self._refresh_clipboard_preview()
        self._setup_tray()
        try:
            self._apply_hotkey_registrations(active_typing=False)
        except HotkeyError as exc:
            logger.warning("Initial hotkey registration failed: %s", exc)
            self.hotkeys_panel.set_status(f"Hotkeys not registered: {exc}", ok=False)
            self.status_widget.set_idle("Hotkeys unavailable; use Start button")

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("MainRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        self.profile_sidebar = ProfileSidebar()
        splitter.addWidget(self.profile_sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 0)
        content_layout.setSpacing(8)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("KeyMimic")
        title.setStyleSheet("font-size: 15pt; font-weight: 700;")
        self.description_label = QLabel("")
        self.description_label.setObjectName("MutedLabel")
        self.description_label.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(self.description_label)
        self.profile_name_edit = QLineEdit()
        self.profile_name_edit.setPlaceholderText("Profile name")
        self.save_profile_button = QPushButton("Save Profile")
        self.save_profile_button.setObjectName("PrimaryButton")
        header.addLayout(title_box, 1)
        header.addWidget(self.profile_name_edit)
        header.addWidget(self.save_profile_button)

        self.tabs = QTabWidget()
        self.speed_panel = SpeedPanel()
        self.pauses_panel = PausesPanel()
        self.realism_panel = RealismPanel()
        self.preview_panel = PreviewPanel()
        self.hotkeys_panel = HotkeysPanel()
        self.settings_panel = self._build_settings_panel()

        self.tabs.addTab(self.speed_panel, "Speed")
        self.tabs.addTab(self.pauses_panel, "Pauses")
        self.tabs.addTab(self.realism_panel, "Realism")
        self.tabs.addTab(self.preview_panel, "Preview")
        self.tabs.addTab(self.hotkeys_panel, "Hotkeys")
        self.tabs.addTab(self.settings_panel, "Settings")

        self.validation_label = QLabel("")
        self.validation_label.setObjectName("ErrorLabel")
        self.validation_label.setWordWrap(True)

        content_layout.addLayout(header)
        content_layout.addWidget(self.tabs, 1)
        content_layout.addWidget(self.validation_label)
        splitter.addWidget(content)
        splitter.setStretchFactor(1, 1)

        self.status_widget = StatusBarWidget()
        root_layout.addWidget(splitter, 1)
        root_layout.addWidget(self.status_widget)
        self.setCentralWidget(root)

    def _build_settings_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)

        form = QFormLayout()
        self.countdown_spin = QSpinBox()
        self.countdown_spin.setRange(0, 30)
        self.countdown_spin.setSuffix(" s")
        self.tooltips_check = QCheckBox("Enable status tooltips")
        self.tray_check = QCheckBox("Show tray icon while running")
        self.start_minimized_check = QCheckBox("Start minimized")
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])

        form.addRow("Countdown", self.countdown_spin)
        form.addRow("", self.tooltips_check)
        form.addRow("", self.tray_check)
        form.addRow("", self.start_minimized_check)
        form.addRow("Log level", self.log_level_combo)
        layout.addLayout(form)

        self.save_settings_button = QPushButton("Save Settings")
        self.save_settings_button.setObjectName("PrimaryButton")
        layout.addWidget(self.save_settings_button, alignment=Qt.AlignRight)
        layout.addStretch(1)
        return panel

    def _connect_signals(self) -> None:
        self.profile_sidebar.profile_selected.connect(self._on_profile_selected)
        self.profile_sidebar.add_requested.connect(self._add_profile)
        self.profile_sidebar.duplicate_requested.connect(self._duplicate_profile)
        self.profile_sidebar.import_requested.connect(self._import_profiles)
        self.profile_sidebar.export_requested.connect(self._export_profiles)
        self.profile_sidebar.move_up_requested.connect(lambda: self._move_profile(-1))
        self.profile_sidebar.move_down_requested.connect(lambda: self._move_profile(1))
        self.save_profile_button.clicked.connect(self._save_profile_from_fields)
        self.preview_panel.refresh_button.clicked.connect(self._refresh_clipboard_preview)
        self.hotkeys_panel.save_requested.connect(self._save_hotkeys)
        self.hotkeys_panel.reset_requested.connect(self._reset_hotkeys)
        self.save_settings_button.clicked.connect(self._save_general_settings)
        self.status_widget.start_pause_requested.connect(self._start_or_toggle_pause)
        self.status_widget.stop_requested.connect(self._stop_typing)
        self.engine_event_received.connect(self._on_engine_event)
        self.hotkey_triggered.connect(self._on_hotkey_triggered)

        for control in self._profile_controls():
            if hasattr(control, "valueChanged"):
                control.valueChanged.connect(self._update_estimates)

        self._clipboard_timer = QTimer(self)
        self._clipboard_timer.setInterval(1500)
        self._clipboard_timer.timeout.connect(self._refresh_clipboard_count)
        self._clipboard_timer.start()

    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        )
        self.tray.setToolTip("KeyMimic")

        menu = QMenu()
        show_action = QAction("Show KeyMimic", self)
        exit_action = QAction("Exit", self)
        show_action.triggered.connect(self._show_window)
        exit_action.triggered.connect(self._exit_from_tray)
        menu.addAction(show_action)
        menu.addAction(exit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self._show_window()
            if reason == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )
        if self.config.minimize_to_tray:
            self.tray.show()
        else:
            self.tray.hide()

    def _profile_controls(self) -> list[QWidget]:
        return (
            self.speed_panel.controls()
            + self.pauses_panel.controls()
            + self.realism_panel.controls()
        )

    def _refresh_profiles(self) -> None:
        self.config.validate()
        names = list(self.config.profile_order)
        self.profile_sidebar.set_profiles(names, self.current_profile_name)
        self.hotkeys_panel.set_hotkeys(self.config.hotkeys)
        self.status_widget.set_hotkeys(self.config.hotkeys)
        self._load_general_settings()

    def _on_profile_selected(self, name: str) -> None:
        if not name or name not in self.config.profiles:
            return
        self.current_profile_name = name
        self.config.last_profile = name
        self._load_profile(name)
        self._save_config_quietly()

    def _load_profile(self, name: str) -> None:
        profile = self.config.profiles[name]
        self.current_profile_name = name
        self.profile_name_edit.setText(profile.name)
        self.profile_name_edit.setReadOnly(profile.is_builtin)
        self.save_profile_button.setEnabled(not profile.is_builtin)
        self.description_label.setText(profile.description)

        self.speed_panel.base_delay.setValue(profile.base_delay_seconds)
        self.speed_panel.variation.setValue(profile.delay_variation_seconds)
        self.speed_panel.hold_time.setValue(profile.hold_time_ms)
        self.pauses_panel.pause_chance.setValue(profile.pause_chance)
        self.pauses_panel.pause_min.setValue(profile.pause_min_seconds)
        self.pauses_panel.pause_max.setValue(profile.pause_max_seconds)
        self.pauses_panel.line_break_chance.setValue(profile.line_break_chance)
        self.pauses_panel.line_break_min.setValue(profile.line_break_min_seconds)
        self.pauses_panel.line_break_max.setValue(profile.line_break_max_seconds)
        self.realism_panel.mistake_chance.setValue(profile.mistake_chance)
        self._set_profile_value_editing_enabled(not profile.is_builtin)
        self._update_estimates()

    def _profile_from_fields(self) -> TypingProfile:
        current = self.config.profiles[self.current_profile_name]
        name = self.profile_name_edit.text().strip() or current.name
        profile = TypingProfile(
            name=name,
            description=current.description
            if not current.is_builtin
            else "Custom profile copied from a built-in preset",
            base_delay_seconds=self.speed_panel.base_delay.value(),
            delay_variation_seconds=self.speed_panel.variation.value(),
            hold_time_ms=self.speed_panel.hold_time.value(),
            pause_chance=self.pauses_panel.pause_chance.value(),
            pause_min_seconds=self.pauses_panel.pause_min.value(),
            pause_max_seconds=self.pauses_panel.pause_max.value(),
            line_break_chance=self.pauses_panel.line_break_chance.value(),
            line_break_min_seconds=self.pauses_panel.line_break_min.value(),
            line_break_max_seconds=self.pauses_panel.line_break_max.value(),
            mistake_chance=self.realism_panel.mistake_chance.value(),
            is_builtin=False,
        )
        profile.validate()
        return profile

    def _save_profile_from_fields(self) -> None:
        try:
            current = self.config.profiles[self.current_profile_name]
            if current.is_builtin:
                self.validation_label.setText(
                    "Built-in profiles are read-only. Duplicate this profile to customize it."
                )
                return
            profile = self._profile_from_fields()
            old_name = self.current_profile_name
            if profile.name != self.current_profile_name:
                profile.name = self._unique_profile_name(profile.name)
                del self.config.profiles[old_name]
                self._replace_profile_order_name(old_name, profile.name)
            self.config.profiles[profile.name] = profile
            if profile.name not in self.config.profile_order:
                self.config.profile_order.append(profile.name)
            self.current_profile_name = profile.name
            self.config.last_profile = profile.name
            self.validation_label.setText("")
            self._save_config_quietly()
            self._refresh_profiles()
            self._load_profile(profile.name)
            self.status_widget.set_idle(f"Saved profile: {profile.name}")
        except ValidationError as exc:
            self.validation_label.setText(str(exc))

    def _add_profile(self) -> None:
        name = self._unique_profile_name("New Profile")
        base = self.config.profiles[self.current_profile_name]
        profile = TypingProfile(
            name=name,
            description="Custom profile",
            base_delay_seconds=base.base_delay_seconds,
            delay_variation_seconds=base.delay_variation_seconds,
            hold_time_ms=base.hold_time_ms,
            pause_chance=base.pause_chance,
            pause_min_seconds=base.pause_min_seconds,
            pause_max_seconds=base.pause_max_seconds,
            line_break_chance=base.line_break_chance,
            line_break_min_seconds=base.line_break_min_seconds,
            line_break_max_seconds=base.line_break_max_seconds,
            mistake_chance=base.mistake_chance,
            is_builtin=False,
        )
        self.config.profiles[name] = profile
        self.config.profile_order.append(name)
        self.current_profile_name = name
        self.config.last_profile = name
        self._save_config_quietly()
        self._refresh_profiles()
        self._load_profile(name)

    def _duplicate_profile(self) -> None:
        base = self.config.profiles[self.current_profile_name]
        name = self._unique_profile_name(f"{base.name} Copy")
        profile = TypingProfile(
            name=name,
            description=f"Custom profile copied from {base.name}",
            base_delay_seconds=base.base_delay_seconds,
            delay_variation_seconds=base.delay_variation_seconds,
            hold_time_ms=base.hold_time_ms,
            pause_chance=base.pause_chance,
            pause_min_seconds=base.pause_min_seconds,
            pause_max_seconds=base.pause_max_seconds,
            line_break_chance=base.line_break_chance,
            line_break_min_seconds=base.line_break_min_seconds,
            line_break_max_seconds=base.line_break_max_seconds,
            mistake_chance=base.mistake_chance,
            is_builtin=False,
        )
        self.config.profiles[name] = profile
        self.config.profile_order.append(name)
        self.current_profile_name = name
        self.config.last_profile = name
        self._save_config_quietly()
        self._refresh_profiles()
        self._load_profile(name)

    def _unique_profile_name(self, requested: str) -> str:
        base = requested.strip() or "Profile"
        if base not in self.config.profiles:
            return base
        index = 2
        while f"{base} {index}" in self.config.profiles:
            index += 1
        return f"{base} {index}"

    def _import_profiles(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Profiles",
            str(Path.home()),
            "JSON files (*.json)",
        )
        if not path:
            return
        try:
            profiles = import_profiles(Path(path))
            for name, profile in profiles.items():
                profile.is_builtin = False
                profile.name = self._unique_profile_name(profile.name or name)
                self.config.profiles[profile.name] = profile
                self.config.profile_order.append(profile.name)
            self._save_config_quietly()
            self._refresh_profiles()
            self.status_widget.set_idle(f"Imported {len(profiles)} profiles")
        except Exception as exc:
            QMessageBox.warning(self, "Import failed", str(exc))

    def _export_profiles(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Custom Profiles",
            str(Path.home() / "keymimic_profiles.json"),
            "JSON files (*.json)",
        )
        if not path:
            return
        try:
            export_profiles(Path(path), self.config.profiles)
            self.status_widget.set_idle("Profiles exported")
        except Exception as exc:
            QMessageBox.warning(self, "Export failed", str(exc))

    def _load_general_settings(self) -> None:
        self.countdown_spin.setValue(self.config.countdown_seconds)
        self.tooltips_check.setChecked(self.config.enable_tooltips)
        self.tray_check.setChecked(self.config.minimize_to_tray)
        self.start_minimized_check.setChecked(self.config.start_minimized)
        index = self.log_level_combo.findText(self.config.log_level)
        self.log_level_combo.setCurrentIndex(max(0, index))

    def _save_general_settings(self) -> None:
        self.config.countdown_seconds = self.countdown_spin.value()
        self.config.enable_tooltips = self.tooltips_check.isChecked()
        self.config.minimize_to_tray = self.tray_check.isChecked()
        self.config.start_minimized = self.start_minimized_check.isChecked()
        self.config.log_level = self.log_level_combo.currentText()
        if hasattr(self, "tray"):
            self.tray.setVisible(self.config.minimize_to_tray)
        self._save_config_quietly()
        self.status_widget.set_idle("Settings saved")

    def _save_hotkeys(self, settings: HotkeySettings) -> None:
        old = self.config.hotkeys
        self.config.hotkeys = settings
        try:
            self._apply_hotkey_registrations(active_typing=self._typing_hotkeys_active)
            self.status_widget.set_hotkeys(self.config.hotkeys)
            self._save_config_quietly()
            self.hotkeys_panel.set_status("Hotkeys saved and registered.", ok=True)
        except HotkeyError as exc:
            self.config.hotkeys = old
            self._apply_hotkey_registrations(active_typing=self._typing_hotkeys_active)
            self.status_widget.set_hotkeys(old)
            self.hotkeys_panel.set_hotkeys(old)
            self.hotkeys_panel.set_status(str(exc), ok=False)

    def _reset_hotkeys(self) -> None:
        self.hotkeys_panel.set_hotkeys(HotkeySettings())

    def _active_hotkey_bindings(self, *, active_typing: bool) -> dict[str, str]:
        hotkeys = self.config.hotkeys.normalized()
        bindings = {
            "start_pause_typing": hotkeys.start_pause_typing,
            "show_hide_window": hotkeys.show_hide_window,
        }
        if active_typing:
            bindings["stop_typing"] = hotkeys.stop_typing
        return bindings

    def _apply_hotkey_registrations(self, *, active_typing: bool) -> None:
        self._typing_hotkeys_active = active_typing
        bindings = self._active_hotkey_bindings(active_typing=active_typing)
        statuses = self.hotkeys.apply_bindings(bindings)
        logger.info("Hotkey statuses: %s", statuses)

    def _refresh_clipboard_count(self) -> None:
        text = get_clipboard_text()
        self.status_widget.set_clipboard_count(len(text))

    def _refresh_clipboard_preview(self) -> None:
        text = get_clipboard_text()
        self.status_widget.set_clipboard_count(len(text))
        self.preview_panel.preview.setPlainText(text[:5000])
        try:
            summary = summarize_typing_plan(
                text,
                self.config.profiles[self.current_profile_name],
            )
            self.preview_panel.summary_label.setText(
                "Chars: {chars} | Est: {seconds:.1f}s with pauses | "
                "Mistakes: {mistakes:.1f} | Thinking pauses: {pauses:.1f}".format(
                    chars=summary.characters,
                    seconds=summary.estimated_seconds_with_pauses,
                    mistakes=summary.expected_mistakes,
                    pauses=summary.expected_thinking_pauses,
                )
            )
        except Exception as exc:
            self.preview_panel.summary_label.setText(str(exc))

    def _move_profile(self, delta: int) -> None:
        name = self.profile_sidebar.current_profile()
        if not name:
            return
        self.config.validate()
        order = list(self.config.profile_order)
        index = order.index(name)
        new_index = index + delta
        if new_index < 0 or new_index >= len(order):
            return
        order[index], order[new_index] = order[new_index], order[index]
        self.config.profile_order = order
        self.config.profiles = {profile_name: self.config.profiles[profile_name] for profile_name in order}
        self.current_profile_name = name
        self._save_config_quietly()
        self._refresh_profiles()

    def _replace_profile_order_name(self, old_name: str, new_name: str) -> None:
        self.config.profile_order = [
            new_name if name == old_name else name for name in self.config.profile_order
        ]

    def _set_profile_value_editing_enabled(self, enabled: bool) -> None:
        for control in self._profile_controls():
            control.setEnabled(enabled)

    def _update_estimates(self) -> None:
        try:
            profile = self._profile_from_fields()
            estimate = estimate_speed(profile)
            self.speed_panel.estimate_label.setText(
                "Estimated speed: {wpm} WPM ({low}-{high} WPM range), "
                "{cpm} CPM. With thinking pauses: {pause_wpm} WPM.".format(
                    wpm=estimate.wpm_average,
                    low=estimate.wpm_min,
                    high=estimate.wpm_max,
                    cpm=estimate.cpm_average,
                    pause_wpm=estimate.wpm_with_pauses,
                )
            )
            self.validation_label.setText("")
            self._refresh_clipboard_preview()
        except Exception as exc:
            self.validation_label.setText(str(exc))

    def _start_typing(self) -> None:
        if self.engine.is_running():
            return
        text = get_clipboard_text()
        if not text:
            self.status_widget.set_idle("Clipboard is empty")
            return
        try:
            profile = self._profile_from_fields()
            profile.validate()
            self._apply_hotkey_registrations(active_typing=True)
            self.engine.start(
                text,
                profile,
                countdown_seconds=self.config.countdown_seconds,
            )
        except Exception as exc:
            self._apply_hotkey_registrations(active_typing=False)
            QMessageBox.warning(self, "Could not start typing", str(exc))

    def _start_or_toggle_pause(self) -> None:
        if self.engine.is_running():
            self._toggle_pause()
        else:
            self._start_typing()

    def _toggle_pause(self) -> None:
        if not self.engine.is_running():
            return
        if self.engine.is_paused():
            self.engine.resume()
        else:
            self.engine.pause()

    def _stop_typing(self) -> None:
        self.engine.cancel()

    def _on_engine_event(self, event: TypingEvent) -> None:
        name = event.name
        payload = event.payload
        if name == "started":
            self.status_widget.set_running("Starting")
        elif name == "countdown_tick":
            self.status_widget.set_running(
                f"Starting in {payload.get('remaining')} seconds"
            )
        elif name == "progress_changed":
            typed = int(payload.get("characters_typed", 0))
            total = int(payload.get("total", 0))
            self.status_widget.set_running(f"Typing {typed}/{total}")
            self.status_widget.set_progress(typed, total)
        elif name == "paused":
            self.status_widget.set_paused()
        elif name == "resumed":
            self.status_widget.set_resumed()
        elif name == "paused_for_delay":
            reason = payload.get("reason", "pause")
            seconds = float(payload.get("seconds", 0.0))
            self.status_widget.status_label.setText(f"{reason} pause: {seconds:.1f}s")
        elif name == "completed":
            typed = int(payload.get("characters_typed", 0))
            self.status_widget.set_idle(f"Completed: {typed} characters")
            self._apply_hotkey_registrations(active_typing=False)
        elif name == "cancelled":
            typed = int(payload.get("characters_typed", 0))
            self.status_widget.set_idle(f"Cancelled after {typed} characters")
            self._apply_hotkey_registrations(active_typing=False)
        elif name == "failed":
            self.status_widget.set_idle("Typing failed")
            self._apply_hotkey_registrations(active_typing=False)
            QMessageBox.warning(self, "Typing failed", str(payload.get("error", "")))

    def _on_hotkey_triggered(self, action: str) -> None:
        if action in {"start_pause_typing", "start_typing", "pause_resume_typing"}:
            self._start_or_toggle_pause()
        elif action == "stop_typing":
            self._stop_typing()
        elif action == "show_hide_window":
            if self.isVisible() and self.isActiveWindow():
                self.hide()
            else:
                self._show_window()

    def _show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _exit_from_tray(self) -> None:
        self.config.minimize_to_tray = False
        self.close()

    def _save_config_quietly(self) -> None:
        geometry = self.geometry()
        self.config.window.width = geometry.width()
        self.config.window.height = geometry.height()
        self.config.window.x = geometry.x()
        self.config.window.y = geometry.y()
        try:
            save_config(self.config)
        except Exception as exc:
            logger.exception("Failed to save config")
            self.validation_label.setText(f"Could not save settings: {exc}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._save_general_settings()
        self._save_config_quietly()
        self.engine.cancel()
        self.hotkeys.stop()
        self.tray.hide()
        event.accept()
        app = QApplication.instance()
        if app is not None:
            QTimer.singleShot(0, app.quit)
