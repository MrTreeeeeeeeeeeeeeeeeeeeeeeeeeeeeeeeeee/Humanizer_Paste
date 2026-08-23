from __future__ import annotations

import logging
from contextlib import suppress

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..clipboard import ClipboardService
from ..config import save_config
from ..events import TypingEvent, TypingEventKind
from ..hotkeys import GlobalHotkeyManager, HotkeyError
from ..logging_setup import set_log_level
from ..models import AppConfig, HotkeySettings, TypingProfile, ValidationError
from ..session_controller import TypingSessionController
from ..sounds import SystemSoundPlayer
from ..timing import summarize_typing_plan
from .hotkeys_panel import HotkeysPanel
from .pauses_panel import PausesPanel
from .preview_panel import PreviewPanel
from .profile_controller import ProfileController
from .profile_panel import ProfileSidebar
from .realism_panel import RealismPanel
from .settings_panel import SettingsPanel
from .speed_panel import SpeedPanel
from .status_bar import StatusBarWidget
from .tray_controller import TrayController

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    hotkey_triggered = Signal(str)

    def __init__(self, config: AppConfig, startup_warning: str = "") -> None:
        super().__init__()
        self.config = config
        self.clipboard = ClipboardService()
        self.sounds = SystemSoundPlayer(config.sounds_enabled)
        self.session = TypingSessionController(self.sounds)
        self.hotkeys = GlobalHotkeyManager(callback=self.hotkey_triggered.emit)
        self._typing_hotkeys_active = False
        self._force_exit = False
        self._shutdown_complete = False
        self._startup_warning = startup_warning

        self.setWindowTitle("KeyMimic")
        self._build_ui()
        self.profile_controller = ProfileController(
            self,
            config,
            self.profile_sidebar,
            self.profile_name_edit,
            self.save_profile_button,
            self.description_label,
            self.speed_panel,
            self.pauses_panel,
            self.realism_panel,
        )
        self._connect_signals()
        self._restore_geometry()
        self.profile_controller.initialize()
        self._refresh_config_panels()
        self._refresh_clipboard_preview()
        self._setup_tray()
        self._apply_tooltip_setting()

        try:
            self._apply_hotkey_registrations(active_typing=False)
        except HotkeyError as exc:
            logger.warning("Initial hotkey registration failed: %s", exc)
            self.hotkeys_panel.set_status(f"Hotkeys not registered: {exc}", ok=False)
            self.status_widget.set_idle("Hotkeys unavailable; use Start button")
        if startup_warning:
            QTimer.singleShot(0, self._show_startup_warning)

    @property
    def can_start_minimized(self) -> bool:
        return self.config.start_minimized and self.tray.available

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("MainRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
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
        self.settings_panel = SettingsPanel()
        for panel, label in (
            (self.speed_panel, "Speed"),
            (self.pauses_panel, "Pauses"),
            (self.realism_panel, "Realism"),
            (self.preview_panel, "Preview"),
            (self.hotkeys_panel, "Hotkeys"),
            (self.settings_panel, "Settings"),
        ):
            self.tabs.addTab(panel, label)

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

    def _connect_signals(self) -> None:
        self.profile_controller.save_requested.connect(self._save_config_quietly)
        self.profile_controller.status_changed.connect(self.status_widget.set_idle)
        self.profile_controller.validation_changed.connect(
            self.validation_label.setText
        )
        self.profile_controller.preview_profile_changed.connect(
            self._on_preview_profile_changed
        )
        self.preview_panel.refresh_button.clicked.connect(
            self._refresh_clipboard_preview
        )
        self.hotkeys_panel.save_requested.connect(self._save_hotkeys)
        self.hotkeys_panel.reset_requested.connect(self._reset_hotkeys)
        self.settings_panel.save_requested.connect(self._save_general_settings)
        self.status_widget.start_pause_requested.connect(self._start_or_toggle_pause)
        self.status_widget.stop_requested.connect(self._stop_typing)
        self.session.event_received.connect(self._on_engine_event)
        self.hotkey_triggered.connect(self._on_hotkey_triggered)
        self.clipboard.text_changed.connect(self._on_clipboard_changed)

    def _setup_tray(self) -> None:
        self.tray = TrayController(self)
        self.tray.show_requested.connect(self._show_window)
        self.tray.exit_requested.connect(self._exit_from_tray)
        if not self.tray.available:
            self.config.show_tray_icon = False
            self.config.close_to_tray = False
            self.config.start_minimized = False
        self.tray.set_visible(self.config.show_tray_icon)

    def _refresh_config_panels(self) -> None:
        self.hotkeys_panel.set_hotkeys(self.config.hotkeys)
        self.status_widget.set_hotkeys(self.config.hotkeys)
        self.settings_panel.load(self.config)

    def _on_preview_profile_changed(self, profile: TypingProfile) -> None:
        self._update_preview_summary(self.clipboard.text, profile)

    def _on_clipboard_changed(self, text: str) -> None:
        self.status_widget.set_clipboard_count(len(text))
        self.preview_panel.preview.setPlainText(text[:5000])
        with suppress(ValidationError):
            self._update_preview_summary(
                text, self.profile_controller.current_profile_snapshot()
            )

    def _refresh_clipboard_preview(self) -> None:
        self._on_clipboard_changed(self.clipboard.snapshot())

    def _update_preview_summary(self, text: str, profile: TypingProfile) -> None:
        summary = summarize_typing_plan(text, profile)
        self.preview_panel.summary_label.setText(
            f"Chars: {summary.characters} | Est: {summary.estimated_seconds_with_pauses:.1f}s with pauses | "
            f"Mistakes: {summary.expected_mistakes:.1f} | Thinking pauses: {summary.expected_thinking_pauses:.1f}"
        )

    def _save_general_settings(self) -> None:
        try:
            self.settings_panel.apply_to(self.config)
        except ValidationError as exc:
            QMessageBox.warning(self, "Invalid settings", str(exc))
            return
        self.sounds.enabled = self.config.sounds_enabled
        self.tray.set_visible(self.config.show_tray_icon)
        set_log_level(self.config.log_level)
        self._apply_tooltip_setting()
        self._save_config_quietly()
        self.status_widget.set_idle("Settings saved")

    def _apply_tooltip_setting(self) -> None:
        for widget in self.findChildren(QWidget):
            original = widget.property("keymimic_original_tooltip")
            if original is None and widget.toolTip():
                original = widget.toolTip()
                widget.setProperty("keymimic_original_tooltip", original)
            if original:
                widget.setToolTip(str(original) if self.config.enable_tooltips else "")

    def _save_hotkeys(self, settings: HotkeySettings) -> None:
        old = self.config.hotkeys
        self.config.hotkeys = settings
        try:
            self._apply_hotkey_registrations(active_typing=self._typing_hotkeys_active)
            self.status_widget.set_hotkeys(settings)
            self._save_config_quietly()
            self.hotkeys_panel.set_status("Hotkeys saved and registered.", ok=True)
        except HotkeyError as exc:
            self.config.hotkeys = old
            try:
                self._apply_hotkey_registrations(
                    active_typing=self._typing_hotkeys_active
                )
            except HotkeyError:
                logger.exception("Could not restore previous hotkeys")
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
        return {action: value for action, value in bindings.items() if value}

    def _apply_hotkey_registrations(self, *, active_typing: bool) -> None:
        statuses = self.hotkeys.apply_bindings(
            self._active_hotkey_bindings(active_typing=active_typing)
        )
        self._typing_hotkeys_active = active_typing
        logger.info("Hotkey statuses: %s", statuses)

    def _start_typing(self) -> None:
        if self.session.engine.is_running():
            return
        text = self.clipboard.snapshot()
        if not text:
            self.status_widget.set_idle("Clipboard is empty")
            return
        if self.config.focus_guard_enabled and self.config.countdown_seconds == 0:
            QMessageBox.warning(
                self,
                "Countdown required",
                "Focus protection needs at least a one-second countdown so you can "
                "select the target window.",
            )
            return
        try:
            profile = self.profile_controller.current_profile_snapshot()
            self._apply_hotkey_registrations(active_typing=True)
            self.profile_controller.set_session_running(True)
            self.session.start(
                text,
                profile,
                self.config.countdown_seconds,
                focus_guard=self.config.focus_guard_enabled,
            )
        except (ValidationError, HotkeyError, RuntimeError, OSError) as exc:
            try:
                self._apply_hotkey_registrations(active_typing=False)
            except HotkeyError:
                logger.exception("Could not restore idle hotkeys")
            self.profile_controller.set_session_running(False)
            QMessageBox.warning(self, "Could not start typing", str(exc))

    def _start_or_toggle_pause(self) -> None:
        if self.session.engine.is_running():
            self.session.toggle_pause()
        else:
            self._start_typing()

    def _stop_typing(self) -> None:
        self.session.stop()

    def _on_engine_event(self, event: TypingEvent) -> None:
        kind = event.kind
        if kind == TypingEventKind.STARTED:
            self.status_widget.set_running("Starting")
        elif kind == TypingEventKind.COUNTDOWN_TICK:
            suffix = "s" if event.remaining != 1 else ""
            self.status_widget.set_running(
                f"Starting in {event.remaining} second{suffix}"
            )
        elif kind == TypingEventKind.TARGET_ACQUIRED:
            self.status_widget.set_running(
                f"Typing into: {event.target_window or 'target window'}"
            )
        elif kind == TypingEventKind.PROGRESS_CHANGED:
            eta = max(0, round(event.estimated_remaining_seconds))
            self.status_widget.set_running(
                f"Typing {event.characters_typed}/{event.total} · about {eta}s remaining"
            )
            self.status_widget.set_progress(event.characters_typed, event.total)
        elif kind == TypingEventKind.PAUSED:
            self.status_widget.set_paused()
        elif kind == TypingEventKind.RESUMED:
            self.status_widget.set_resumed()
        elif kind == TypingEventKind.PAUSED_FOR_DELAY:
            self.status_widget.status_label.setText(
                f"{event.reason.title()} pause: {event.delay_seconds:.1f}s"
            )
        elif kind == TypingEventKind.COMPLETED:
            self.status_widget.set_idle(
                f"Completed: {event.characters_typed} characters in "
                f"{event.elapsed_seconds:.1f}s"
            )
            self.tray.notify(
                "KeyMimic finished", "Clipboard text was typed successfully."
            )
            self._return_to_idle_hotkeys()
        elif kind == TypingEventKind.CANCELLED:
            self.status_widget.set_idle(
                f"Cancelled after {event.characters_typed} characters"
            )
            self._return_to_idle_hotkeys()
        elif kind == TypingEventKind.FAILED:
            self.status_widget.set_idle("Typing stopped for safety")
            self._return_to_idle_hotkeys()
            QMessageBox.warning(self, "Typing stopped", event.error)

    def _return_to_idle_hotkeys(self) -> None:
        try:
            self._apply_hotkey_registrations(active_typing=False)
        except HotkeyError as exc:
            self.hotkeys_panel.set_status(str(exc), ok=False)
        self.profile_controller.set_session_running(False)

    def _on_hotkey_triggered(self, action: str) -> None:
        if action == "start_pause_typing":
            self._start_or_toggle_pause()
        elif action == "stop_typing":
            self.session.stop(escape_pressed=True)
        elif action == "show_hide_window":
            if self.isVisible() and self.isActiveWindow():
                self.hide()
            else:
                self._show_window()

    def _show_window(self) -> None:
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def _exit_from_tray(self) -> None:
        self._force_exit = True
        self.close()

    def _restore_geometry(self) -> None:
        window = self.config.window
        self.resize(window.width, window.height)
        if window.x is None or window.y is None:
            return
        requested = QPoint(window.x, window.y)
        if any(
            screen.availableGeometry().contains(requested)
            for screen in QApplication.screens()
        ):
            self.move(requested)
            return
        screen = QApplication.primaryScreen()
        if screen is not None:
            self.move(screen.availableGeometry().center() - self.rect().center())

    def _save_config_quietly(self) -> None:
        if self.isVisible():
            geometry = self.geometry()
            self.config.window.width = geometry.width()
            self.config.window.height = geometry.height()
            self.config.window.x = geometry.x()
            self.config.window.y = geometry.y()
        try:
            save_config(self.config)
        except (OSError, ValueError) as exc:
            logger.exception("Failed to save config")
            self.validation_label.setText(f"Could not save settings: {exc}")

    def _show_startup_warning(self) -> None:
        QMessageBox.warning(self, "Settings recovered", self._startup_warning)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.config.close_to_tray and not self._force_exit and self.tray.available:
            self.hide()
            self.tray.notify(
                "KeyMimic is still running", "Use the tray icon to reopen or exit."
            )
            event.ignore()
            return
        if self._shutdown_complete:
            event.accept()
            return
        self._shutdown_complete = True
        self._save_config_quietly()
        if not self.session.shutdown(timeout=2.0):
            logger.error("Typing worker did not stop within the shutdown timeout")
        try:
            self.hotkeys.stop()
        except HotkeyError:
            logger.exception("Hotkey worker did not stop cleanly")
        self.tray.hide()
        event.accept()
        app = QApplication.instance()
        if app is not None:
            QTimer.singleShot(0, app.quit)
