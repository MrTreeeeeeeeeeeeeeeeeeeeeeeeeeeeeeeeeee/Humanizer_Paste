from __future__ import annotations

from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class RealismPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        group = QGroupBox("Typing Mistakes")
        form = QFormLayout(group)
        self.mistake_chance = QDoubleSpinBox()
        self.mistake_chance.setRange(0.0, 1.0)
        self.mistake_chance.setDecimals(4)
        self.mistake_chance.setSingleStep(0.001)
        form.addRow("Mistake rate", self.mistake_chance)

        info = QLabel(
            "Mistakes type a random lowercase letter, then backspace and continue. "
            "Mapped characters use scan codes; unmapped characters use Unicode input."
        )
        info.setObjectName("MutedLabel")
        info.setWordWrap(True)

        layout.addWidget(group)
        layout.addWidget(info)
        layout.addStretch(1)

    def controls(self) -> list[QWidget]:
        return [self.mistake_chance]
