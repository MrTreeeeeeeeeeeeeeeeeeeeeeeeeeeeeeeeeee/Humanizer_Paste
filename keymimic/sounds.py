from __future__ import annotations

import logging
import platform

logger = logging.getLogger(__name__)


class SystemSoundPlayer:
    """Plays familiar Windows system sounds without shipping media files."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def play_stop(self) -> None:
        self._message_beep(0x00000010)  # MB_ICONHAND

    def play_completed(self) -> None:
        self._message_beep(0x00000040)  # MB_ICONASTERISK

    def _message_beep(self, sound_type: int) -> None:
        if not self.enabled or platform.system() != "Windows":
            return
        try:
            import winsound

            winsound.MessageBeep(sound_type)
        except (ImportError, RuntimeError, OSError):
            logger.exception("Could not play Windows system sound")
