from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon, QWidget


class TrayController(QObject):
    show_requested = Signal()
    exit_requested = Signal()

    def __init__(self, owner: QWidget) -> None:
        super().__init__(owner)
        self.icon = QSystemTrayIcon(owner)
        app_icon = QApplication.windowIcon()
        self.icon.setIcon(
            app_icon
            if not app_icon.isNull()
            else owner.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        )
        self.icon.setToolTip("KeyMimic")

        menu = QMenu(owner)
        show_action = QAction("Show KeyMimic", owner)
        exit_action = QAction("Exit KeyMimic", owner)
        show_action.triggered.connect(self.show_requested.emit)
        exit_action.triggered.connect(self.exit_requested.emit)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        self.icon.setContextMenu(menu)
        self.icon.activated.connect(self._activated)

    @property
    def available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def set_visible(self, visible: bool) -> None:
        self.icon.setVisible(visible and self.available)

    def notify(self, title: str, message: str) -> None:
        if self.icon.isVisible() and self.icon.supportsMessages():
            self.icon.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Information,
                2500,
            )

    def hide(self) -> None:
        self.icon.hide()

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.show_requested.emit()
