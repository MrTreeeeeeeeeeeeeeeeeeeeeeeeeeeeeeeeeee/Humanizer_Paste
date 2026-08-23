from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ProfileSidebar(QWidget):
    profile_selected = Signal(str)
    add_requested = Signal()
    duplicate_requested = Signal()
    delete_requested = Signal()
    import_requested = Signal()
    export_requested = Signal()
    move_up_requested = Signal()
    move_down_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setFixedWidth(250)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 8, 10)
        layout.setSpacing(8)

        title = QLabel("Profiles")
        title.setStyleSheet("font-size: 12pt; font-weight: 700;")
        hint = QLabel("Built-ins are read-only. Duplicate one to customize it.")
        hint.setObjectName("MutedLabel")
        hint.setWordWrap(True)

        self.list_widget = QListWidget()
        self.list_widget.currentTextChanged.connect(self.profile_selected.emit)

        self.add_button = QPushButton("Add")
        self.duplicate_button = QPushButton("Duplicate")
        self.delete_button = QPushButton("Delete")
        self.import_button = QPushButton("Import")
        self.export_button = QPushButton("Export")
        self.move_up_button = QPushButton("Move Up")
        self.move_down_button = QPushButton("Move Down")

        self.add_button.clicked.connect(self.add_requested.emit)
        self.duplicate_button.clicked.connect(self.duplicate_requested.emit)
        self.delete_button.clicked.connect(self.delete_requested.emit)
        self.import_button.clicked.connect(self.import_requested.emit)
        self.export_button.clicked.connect(self.export_requested.emit)
        self.move_up_button.clicked.connect(self.move_up_requested.emit)
        self.move_down_button.clicked.connect(self.move_down_requested.emit)
        self.list_widget.currentRowChanged.connect(self._update_move_buttons)

        row_one = QHBoxLayout()
        row_one.addWidget(self.add_button)
        row_one.addWidget(self.duplicate_button)
        row_one.addWidget(self.delete_button)
        row_two = QHBoxLayout()
        row_two.addWidget(self.import_button)
        row_two.addWidget(self.export_button)
        row_three = QHBoxLayout()
        row_three.addWidget(self.move_up_button)
        row_three.addWidget(self.move_down_button)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.list_widget, 1)
        layout.addLayout(row_one)
        layout.addLayout(row_two)
        layout.addLayout(row_three)
        self._update_move_buttons()

    def set_profiles(self, names: list[str], current: str) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        self.list_widget.addItems(names)
        matches = self.list_widget.findItems(current, Qt.MatchFlag.MatchExactly)
        if matches:
            self.list_widget.setCurrentItem(matches[0])
        elif names:
            self.list_widget.setCurrentRow(0)
        self.list_widget.blockSignals(False)
        self._update_move_buttons()

    def current_profile(self) -> str:
        item = self.list_widget.currentItem()
        return "" if item is None else item.text()

    def _update_move_buttons(self) -> None:
        row = self.list_widget.currentRow()
        count = self.list_widget.count()
        self.move_up_button.setEnabled(row > 0)
        self.move_down_button.setEnabled(row >= 0 and row < count - 1)
