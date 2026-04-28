from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QWidget,
)


class StatusBarWidget(QWidget):
    start_requested = Signal()
    pause_requested = Signal()
    stop_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
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

        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("PrimaryButton")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("DangerButton")
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.start_button.clicked.connect(self.start_requested.emit)
        self.pause_button.clicked.connect(self.pause_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)

        layout.addWidget(self.status_label, 1)
        layout.addWidget(self.detail_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.start_button)
        layout.addWidget(self.pause_button)
        layout.addWidget(self.stop_button)

    def set_idle(self, text: str = "Ready") -> None:
        self.status_label.setText(text)
        self.progress.setValue(0)
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("Pause")
        self.stop_button.setEnabled(False)

    def set_running(self, text: str = "Typing") -> None:
        self.status_label.setText(text)
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.pause_button.setText("Pause")
        self.stop_button.setEnabled(True)

    def set_paused(self) -> None:
        self.status_label.setText("Paused")
        self.pause_button.setText("Resume")

    def set_resumed(self) -> None:
        self.status_label.setText("Typing")
        self.pause_button.setText("Pause")

    def set_progress(self, typed: int, total: int) -> None:
        if total <= 0:
            self.progress.setValue(0)
            return
        self.progress.setValue(round((typed / total) * 100))

    def set_clipboard_count(self, count: int) -> None:
        self.detail_label.setText(f"Clipboard: {count} chars")
