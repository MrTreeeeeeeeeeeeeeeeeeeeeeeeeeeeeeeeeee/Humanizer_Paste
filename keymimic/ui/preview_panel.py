from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


class PreviewPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        self.refresh_button = QPushButton("Refresh Clipboard Preview")
        self.summary_label = QLabel("No clipboard text loaded.")
        self.summary_label.setObjectName("MutedLabel")
        self.summary_label.setWordWrap(True)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Clipboard text preview")

        layout.addWidget(self.refresh_button)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.preview, 1)
