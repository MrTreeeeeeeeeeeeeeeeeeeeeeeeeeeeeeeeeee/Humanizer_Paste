from __future__ import annotations

from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(
        """
        QWidget {
            font-family: "Segoe UI";
            font-size: 9pt;
            color: #e6e8ee;
        }
        QMainWindow, QWidget#MainRoot {
            background: #15171b;
        }
        QListWidget, QTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox,
        QComboBox, QKeySequenceEdit {
            background: #202329;
            border: 1px solid #3a3f49;
            border-radius: 4px;
            color: #f4f6fa;
            selection-background-color: #2f7dd1;
            selection-color: #ffffff;
        }
        QLineEdit, QComboBox, QKeySequenceEdit {
            padding: 5px 8px;
        }
        QSpinBox, QDoubleSpinBox {
            min-height: 28px;
            padding: 3px 34px 3px 8px;
        }
        QSpinBox:disabled, QDoubleSpinBox:disabled, QLineEdit:disabled,
        QComboBox:disabled, QTextEdit:disabled {
            background: #191b20;
            border-color: #2b2f37;
            color: #858b96;
        }
        QSpinBox::up-button, QDoubleSpinBox::up-button {
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 28px;
            border-left: 1px solid #3a3f49;
            border-bottom: 1px solid #3a3f49;
            border-top-right-radius: 4px;
            background: #292d35;
        }
        QSpinBox::down-button, QDoubleSpinBox::down-button {
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 28px;
            border-left: 1px solid #3a3f49;
            border-bottom-right-radius: 4px;
            background: #292d35;
        }
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
            background: #343944;
        }
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
            image: none;
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid #d7dce5;
        }
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
            image: none;
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #d7dce5;
        }
        QTextEdit {
            padding: 8px;
        }
        QListWidget::item {
            min-height: 30px;
            padding: 4px 8px;
        }
        QListWidget::item:selected {
            background: #263d54;
            color: #ffffff;
        }
        QPushButton {
            background: #242831;
            border: 1px solid #444a55;
            border-radius: 4px;
            color: #f4f6fa;
            padding: 6px 10px;
        }
        QPushButton:hover {
            background: #303642;
        }
        QPushButton:pressed {
            background: #1f232b;
        }
        QPushButton:disabled {
            background: #1b1e24;
            border-color: #2a2e36;
            color: #777d88;
        }
        QPushButton#PrimaryButton {
            background: #2f7dd1;
            border-color: #2f7dd1;
            color: #ffffff;
        }
        QPushButton#DangerButton {
            background: #a6423a;
            border-color: #a6423a;
            color: #ffffff;
        }
        QLabel#MutedLabel {
            color: #9aa1ad;
        }
        QLabel#ErrorLabel {
            color: #ff8a7a;
        }
        QLabel#OkLabel {
            color: #65d69a;
        }
        QTabWidget::pane {
            border: 1px solid #303640;
            background: #1a1d23;
            border-radius: 4px;
        }
        QTabBar::tab {
            background: #20242c;
            border: 1px solid #303640;
            color: #b9c0cb;
            padding: 7px 12px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #1a1d23;
            color: #ffffff;
            border-bottom-color: #1a1d23;
        }
        QGroupBox {
            border: 1px solid #303640;
            border-radius: 4px;
            margin-top: 14px;
            padding: 12px 8px 8px 8px;
            font-weight: 600;
            background: #1a1d23;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
            color: #f4f6fa;
            background: #15171b;
        }
        QProgressBar {
            background: #202329;
            border: 1px solid #3a3f49;
            border-radius: 4px;
            text-align: center;
        }
        QProgressBar::chunk {
            background: #36a37f;
            border-radius: 3px;
        }
        QSplitter::handle {
            background: #252932;
        }
        QMenu {
            background: #202329;
            border: 1px solid #3a3f49;
            color: #f4f6fa;
        }
        QMenu::item:selected {
            background: #303642;
        }
        """
    )
