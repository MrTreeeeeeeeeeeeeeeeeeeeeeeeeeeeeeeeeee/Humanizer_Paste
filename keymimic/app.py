from __future__ import annotations

import logging
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .config import load_config_result
from .logging_setup import set_log_level, setup_logging
from .resources import asset_path
from .single_instance import SingleInstanceGuard
from .ui.main_window import MainWindow
from .ui.theme import apply_theme

APP_VERSION = "1.0.0"
logger = logging.getLogger(__name__)


def main() -> int:
    if "--version" in sys.argv:
        print(f"KeyMimic {APP_VERSION}")
        return 0

    setup_logging("INFO")
    load_result = load_config_result()
    config = load_result.config
    set_log_level(config.log_level)

    if "--smoke-test" in sys.argv:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QApplication.instance() or QApplication([sys.argv[0]])
        app.setApplicationName("KeyMimic")
        app.setApplicationVersion(APP_VERSION)
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("KeyMimic")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("KeyMimic")
    app.setWindowIcon(QIcon(str(asset_path("keymimic.svg"))))
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)

    guard = SingleInstanceGuard()
    try:
        if not guard.acquire():
            QMessageBox.information(
                None,
                "KeyMimic is already running",
                "Only one copy of KeyMimic can run at a time. Use the existing "
                "window or its tray icon.",
            )
            return 0

        window = MainWindow(config, startup_warning=load_result.warning)
        if not window.can_start_minimized:
            window.show()
        return app.exec()
    except Exception as exc:
        logger.exception("KeyMimic could not start")
        QMessageBox.critical(None, "KeyMimic could not start", str(exc))
        return 1
    finally:
        guard.release()
