from __future__ import annotations

from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SpeedPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        group = QGroupBox("Typing Speed")
        form = QFormLayout(group)
        self.base_delay = QDoubleSpinBox()
        self.base_delay.setDecimals(4)
        self.base_delay.setRange(0.001, 2.0)
        self.base_delay.setSingleStep(0.001)
        self.variation = QDoubleSpinBox()
        self.variation.setDecimals(4)
        self.variation.setRange(0.0, 2.0)
        self.variation.setSingleStep(0.001)
        self.hold_time = QSpinBox()
        self.hold_time.setRange(5, 200)
        self.hold_time.setSuffix(" ms")
        form.addRow("Base delay", self.base_delay)
        form.addRow("Delay variation", self.variation)
        form.addRow("Key hold duration", self.hold_time)

        self.estimate_label = QLabel()
        self.estimate_label.setWordWrap(True)
        self.estimate_label.setObjectName("MutedLabel")
        layout.addWidget(group)
        layout.addWidget(self.estimate_label)
        layout.addStretch(1)

    def controls(self) -> list[QWidget]:
        return [self.base_delay, self.variation, self.hold_time]
