from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QWidget,
)

from ..models import HotkeySettings


class StatusBarWidget(QWidget):
    start_pause_requested = Signal()
    start_requested = Signal()
    pause_requested = Signal()
    stop_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._hotkeys = HotkeySettings()
        self._start_pause_action = "start"
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        self.status_label = QLabel("Ready")
        self.status_label.setMinimumWidth(260)
        self.detail_label = QLabel("Clipboard: 0 chars")
        self.detail_label.setObjectName("MutedLabel")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedWidth(180)

        self.start_pause_button = QPushButton("Start")
        self.start_pause_button.setObjectName("PrimaryButton")
        self.start_button = self.start_pause_button
        self.pause_button = self.start_pause_button
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("DangerButton")
        self.stop_button.setEnabled(False)

        self.start_pause_button.clicked.connect(self._emit_start_pause_requested)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.set_hotkeys(self._hotkeys)

        layout.addWidget(self.status_label, 1)
        layout.addWidget(self.detail_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.start_pause_button)
        layout.addWidget(self.stop_button)

    def set_idle(self, text: str = "Ready") -> None:
        self.status_label.setText(text)
        self.progress.setValue(0)
        self.start_pause_button.setEnabled(True)
        self._start_pause_action = "start"
        self._set_button_text(
            self.start_pause_button,
            "Start",
            self._hotkeys.start_pause_typing,
        )
        self.stop_button.setEnabled(False)

    def set_running(self, text: str = "Typing") -> None:
        self.status_label.setText(text)
        self.start_pause_button.setEnabled(True)
        self._start_pause_action = "pause"
        self._set_button_text(
            self.start_pause_button,
            "Pause",
            self._hotkeys.start_pause_typing,
        )
        self.stop_button.setEnabled(True)

    def set_paused(self) -> None:
        self.status_label.setText("Paused")
        self._start_pause_action = "pause"
        self._set_button_text(
            self.start_pause_button,
            "Resume",
            self._hotkeys.start_pause_typing,
        )

    def set_resumed(self) -> None:
        self.status_label.setText("Typing")
        self._start_pause_action = "pause"
        self._set_button_text(
            self.start_pause_button,
            "Pause",
            self._hotkeys.start_pause_typing,
        )

    def set_progress(self, typed: int, total: int) -> None:
        if total <= 0:
            self.progress.setValue(0)
            return
        self.progress.setValue(round((typed / total) * 100))

    def set_clipboard_count(self, count: int) -> None:
        self.detail_label.setText(f"Clipboard: {count} chars")

    def set_hotkeys(self, hotkeys: HotkeySettings) -> None:
        self._hotkeys = hotkeys.normalized()
        self._apply_button_hotkey(
            self.start_pause_button,
            self._current_start_pause_text(),
            "Start, pause, or resume typing",
            self._hotkeys.start_pause_typing,
        )
        self._apply_button_hotkey(
            self.stop_button,
            "Stop",
            "Stop typing immediately",
            self._hotkeys.stop_typing,
        )

    def _apply_button_hotkey(
        self,
        button: QPushButton,
        action_text: str,
        tooltip_action: str,
        hotkey: str,
    ) -> None:
        button.setShortcut(QKeySequence(hotkey) if hotkey else QKeySequence())
        self._set_button_text(button, action_text, hotkey)
        if hotkey:
            button.setToolTip(f"{tooltip_action}: {hotkey}")
        else:
            button.setToolTip(tooltip_action)

    def _current_start_pause_text(self) -> str:
        text = self.start_pause_button.text()
        if text.startswith("Resume"):
            return "Resume"
        if text.startswith("Pause"):
            return "Pause"
        return "Start"

    def _emit_start_pause_requested(self) -> None:
        self.start_pause_requested.emit()
        if self._start_pause_action == "start":
            self.start_requested.emit()
        else:
            self.pause_requested.emit()

    @staticmethod
    def _set_button_text(button: QPushButton, action_text: str, hotkey: str) -> None:
        if hotkey:
            button.setText(f"{action_text} ({hotkey})")
        else:
            button.setText(action_text)
