from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..models import AppConfig


class SettingsPanel(QWidget):
    save_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        form = QFormLayout()
        self.countdown = QSpinBox()
        self.countdown.setRange(0, 30)
        self.countdown.setSuffix(" s")
        self.tooltips = QCheckBox("Enable explanatory tooltips")
        self.show_tray = QCheckBox("Show tray icon")
        self.close_to_tray = QCheckBox("Hide in tray when the window is closed")
        self.start_minimized = QCheckBox("Start minimized in the tray")
        self.focus_guard = QCheckBox("Stop typing if focus leaves the target window")
        self.sounds = QCheckBox(
            "Play Windows sounds when stopped with Esc or completed"
        )
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])

        form.addRow("Countdown", self.countdown)
        form.addRow("", self.tooltips)
        form.addRow("", self.show_tray)
        form.addRow("", self.close_to_tray)
        form.addRow("", self.start_minimized)
        form.addRow("", self.focus_guard)
        form.addRow("", self.sounds)
        form.addRow("Log level", self.log_level)
        layout.addLayout(form)

        note = QLabel(
            "The emergency Stop hotkey remains active while typing. Focus protection "
            "prevents text from being sent to a window you did not intend."
        )
        note.setObjectName("MutedLabel")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.save_button = QPushButton("Save Settings")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.clicked.connect(self.save_requested.emit)
        layout.addWidget(self.save_button)
        layout.addStretch(1)

        self.show_tray.toggled.connect(self._update_dependencies)

    def load(self, config: AppConfig) -> None:
        self.countdown.setValue(config.countdown_seconds)
        self.tooltips.setChecked(config.enable_tooltips)
        self.show_tray.setChecked(config.show_tray_icon)
        self.close_to_tray.setChecked(config.close_to_tray)
        self.start_minimized.setChecked(config.start_minimized)
        self.focus_guard.setChecked(config.focus_guard_enabled)
        self.sounds.setChecked(config.sounds_enabled)
        index = self.log_level.findText(config.log_level)
        self.log_level.setCurrentIndex(max(0, index))
        self._update_dependencies()

    def apply_to(self, config: AppConfig) -> None:
        config.countdown_seconds = self.countdown.value()
        config.enable_tooltips = self.tooltips.isChecked()
        config.show_tray_icon = self.show_tray.isChecked()
        config.close_to_tray = self.close_to_tray.isChecked()
        config.start_minimized = self.start_minimized.isChecked()
        config.focus_guard_enabled = self.focus_guard.isChecked()
        config.sounds_enabled = self.sounds.isChecked()
        config.log_level = self.log_level.currentText()
        config.validate()

    def _update_dependencies(self) -> None:
        enabled = self.show_tray.isChecked()
        self.close_to_tray.setEnabled(enabled)
        self.start_minimized.setEnabled(enabled)
        if not enabled:
            self.close_to_tray.setChecked(False)
            self.start_minimized.setChecked(False)
