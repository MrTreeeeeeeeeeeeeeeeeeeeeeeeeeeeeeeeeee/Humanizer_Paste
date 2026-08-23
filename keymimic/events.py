from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SessionState(StrEnum):
    IDLE = "idle"
    COUNTDOWN = "countdown"
    TYPING = "typing"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TypingEventKind(StrEnum):
    STARTED = "started"
    COUNTDOWN_TICK = "countdown_tick"
    TARGET_ACQUIRED = "target_acquired"
    PROGRESS_CHANGED = "progress_changed"
    PAUSED = "paused"
    RESUMED = "resumed"
    PAUSED_FOR_DELAY = "paused_for_delay"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TypingEvent:
    kind: TypingEventKind
    state: SessionState
    characters_typed: int = 0
    total: int = 0
    remaining: int = 0
    reason: str = ""
    delay_seconds: float = 0.0
    elapsed_seconds: float = 0.0
    estimated_remaining_seconds: float = 0.0
    target_window: str = ""
    error: str = ""

    @property
    def name(self) -> str:
        """Compatibility accessor for older integrations and tests."""
        return self.kind.value

    @property
    def payload(self) -> dict[str, Any]:
        """Compatibility accessor for older UI integrations."""
        values: dict[str, Any] = {
            "characters_typed": self.characters_typed,
            "total": self.total,
            "remaining": self.remaining,
            "reason": self.reason,
            "seconds": self.delay_seconds,
            "elapsed_seconds": self.elapsed_seconds,
            "estimated_remaining_seconds": self.estimated_remaining_seconds,
            "target_window": self.target_window,
            "error": self.error,
        }
        return {
            key: value for key, value in values.items() if value not in (0, 0.0, "")
        }
