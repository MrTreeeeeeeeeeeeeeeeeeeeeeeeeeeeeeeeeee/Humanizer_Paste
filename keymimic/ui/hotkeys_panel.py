from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QKeySequenceEdit,
)

from ..hotkeys import HotkeyParseError, normalize_hotkey
from ..models import HotkeySettings


class HotkeysPanel(QWidget):
    save_requested = Signal(HotkeySettings)
    reset_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.status_label = QLabel("Hotkeys are saved with the rest of settings.")
        self.status_label.setObjectName("MutedLabel")
        layout.addWidget(self.status_label)

        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())
        self.start_pause_edit = QKeySequenceEdit()
        self.stop_edit = QKeySequenceEdit()
        self.show_edit = QKeySequenceEdit()

        form.addRow("Start / pause / resume typing", self.start_pause_edit)
        form.addRow("Stop typing immediately", self.stop_edit)
        form.addRow("Show / hide window", self.show_edit)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.save_button = QPushButton("Save Hotkeys")
        self.save_button.setObjectName("PrimaryButton")
        self.reset_button = QPushButton("Reset Hotkeys")
        buttons.addStretch(1)
        buttons.addWidget(self.reset_button)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)
        layout.addStretch(1)

        self.save_button.clicked.connect(self._save)
        self.reset_button.clicked.connect(self.reset_requested.emit)

    def set_hotkeys(self, hotkeys: HotkeySettings) -> None:
        self.start_pause_edit.setKeySequence(QKeySequence(hotkeys.start_pause_typing))
        self.stop_edit.setKeySequence(QKeySequence(hotkeys.stop_typing))
        self.show_edit.setKeySequence(QKeySequence(hotkeys.show_hide_window))
        self.set_status("Hotkeys loaded.", ok=True)

    def settings(self) -> HotkeySettings:
        return HotkeySettings(
            start_pause_typing=self._sequence_text(self.start_pause_edit),
            stop_typing=self._sequence_text(self.stop_edit),
            show_hide_window=self._sequence_text(self.show_edit),
        ).normalized()

    def set_status(self, message: str, *, ok: bool) -> None:
        self.status_label.setText(message)
        self.status_label.setObjectName("OkLabel" if ok else "ErrorLabel")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _save(self) -> None:
        try:
            settings = self.settings()
            settings.validate()
        except HotkeyParseError as exc:
            self.set_status(str(exc), ok=False)
            return
        self.save_requested.emit(settings)

    @staticmethod
    def _sequence_text(edit: QKeySequenceEdit) -> str:
        sequence = edit.keySequence()
        value = sequence.toString(QKeySequence.PortableText)
        if not value:
            return ""
        return normalize_hotkey(value)
