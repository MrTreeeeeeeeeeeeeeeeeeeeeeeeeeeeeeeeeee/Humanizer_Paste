from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .events import SessionState, TypingEvent, TypingEventKind
from .models import TypingProfile
from .sounds import SystemSoundPlayer
from .typing_engine import TypingEngine


class TypingSessionController(QObject):
    event_received = Signal(object)
    state_changed = Signal(object)

    def __init__(
        self,
        sound_player: SystemSoundPlayer,
        engine: TypingEngine | None = None,
    ) -> None:
        super().__init__()
        self.sound_player = sound_player
        self.engine = engine or TypingEngine(event_callback=self.event_received.emit)
        self.event_received.connect(self._handle_event)

    @property
    def state(self) -> SessionState:
        return self.engine.state

    def start(
        self,
        text: str,
        profile: TypingProfile,
        countdown_seconds: int,
        *,
        focus_guard: bool,
    ) -> None:
        self.engine.start(
            text,
            profile,
            countdown_seconds,
            focus_guard=focus_guard,
        )

    def toggle_pause(self) -> None:
        if self.engine.is_paused():
            self.engine.resume()
        else:
            self.engine.pause()

    def stop(self, *, escape_pressed: bool = False) -> None:
        if escape_pressed and self.engine.is_running():
            self.sound_player.play_stop()
        self.engine.cancel()

    def shutdown(self, timeout: float = 2.0) -> bool:
        return self.engine.shutdown(timeout)

    def _handle_event(self, event: TypingEvent) -> None:
        self.state_changed.emit(event.state)
        if event.kind == TypingEventKind.COMPLETED:
            self.sound_player.play_completed()
