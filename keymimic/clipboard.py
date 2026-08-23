from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QClipboard, QGuiApplication

logger = logging.getLogger(__name__)


def get_clipboard_text() -> str:
    """Return clipboard text through Qt, which handles Windows clipboard retries."""
    application = QGuiApplication.instance()
    if application is None:
        return ""
    clipboard = QGuiApplication.clipboard()
    mime_data = clipboard.mimeData(QClipboard.Mode.Clipboard)
    if mime_data is None or not mime_data.hasText():
        return ""
    try:
        return mime_data.text()
    except RuntimeError:
        logger.warning("Clipboard contents became unavailable while reading")
        return ""


class ClipboardService(QObject):
    text_changed = Signal(str)

    def __init__(self, reader: Callable[[], str] = get_clipboard_text) -> None:
        super().__init__()
        self._reader = reader
        self._text = ""
        self._clipboard = QGuiApplication.clipboard()
        self._clipboard.dataChanged.connect(self.refresh)
        self.refresh()

    @property
    def text(self) -> str:
        return self._text

    def snapshot(self) -> str:
        self.refresh()
        return self._text

    def refresh(self) -> None:
        try:
            text = self._reader()
        except (OSError, RuntimeError) as exc:
            logger.warning("Clipboard read failed: %s", exc)
            return
        if text != self._text:
            self._text = text
            self.text_changed.emit(text)
