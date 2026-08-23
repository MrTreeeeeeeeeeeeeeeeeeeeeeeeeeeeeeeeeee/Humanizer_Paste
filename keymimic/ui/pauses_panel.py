from __future__ import annotations

from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QVBoxLayout,
    QWidget,
)


class PausesPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        thinking = QGroupBox("Thinking Pauses")
        thinking_form = QFormLayout(thinking)
        self.pause_chance = self._chance_box()
        self.pause_min = self._seconds_box()
        self.pause_max = self._seconds_box()
        thinking_form.addRow("Frequency", self.pause_chance)
        thinking_form.addRow("Minimum duration", self.pause_min)
        thinking_form.addRow("Maximum duration", self.pause_max)

        line_breaks = QGroupBox("Line Break Pauses")
        break_form = QFormLayout(line_breaks)
        self.line_break_chance = self._chance_box()
        self.line_break_min = self._seconds_box()
        self.line_break_max = self._seconds_box()
        break_form.addRow("Frequency", self.line_break_chance)
        break_form.addRow("Minimum duration", self.line_break_min)
        break_form.addRow("Maximum duration", self.line_break_max)

        layout.addWidget(thinking)
        layout.addWidget(line_breaks)
        layout.addStretch(1)

    def controls(self) -> list[QWidget]:
        return [
            self.pause_chance,
            self.pause_min,
            self.pause_max,
            self.line_break_chance,
            self.line_break_min,
            self.line_break_max,
        ]

    @staticmethod
    def _chance_box() -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setRange(0.0, 1.0)
        box.setDecimals(4)
        box.setSingleStep(0.001)
        return box

    @staticmethod
    def _seconds_box() -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setRange(0.0, 60.0)
        box.setDecimals(3)
        box.setSingleStep(0.1)
        box.setSuffix(" s")
        return box
