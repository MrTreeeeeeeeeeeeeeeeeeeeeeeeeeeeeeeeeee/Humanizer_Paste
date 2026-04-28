from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .config import load_config
from .logging_setup import setup_logging
from .ui.main_window import MainWindow
from .ui.theme import apply_theme


def main() -> int:
    config = load_config()
    setup_logging(config.log_level)

    app = QApplication(sys.argv)
    app.setApplicationName("KeyMimic")
    app.setOrganizationName("KeyMimic")
    apply_theme(app)

    window = MainWindow(config)
    if not config.start_minimized:
        window.show()
    return app.exec()
