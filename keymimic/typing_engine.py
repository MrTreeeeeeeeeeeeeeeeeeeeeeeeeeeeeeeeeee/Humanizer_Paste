from __future__ import annotations

import logging
import random
import string
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .models import TypingProfile
from .timing import human_delay_seconds
from .win_input import WindowsInput, high_resolution_timer


logger = logging.getLogger(__name__)


class InputBackend(Protocol):
    def send_char(self, char: str, hold_time_ms: int) -> None:
        ...

    def press_backspace(self, hold_time_ms: int) -> None:
        ...


@dataclass(frozen=True)
class TypingEvent:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)


TypingEventCallback = Callable[[TypingEvent], None]


class TypingEngine:
    def __init__(
        self,
        input_backend: InputBackend | None = None,
        event_callback: TypingEventCallback | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._input = input_backend or WindowsInput()
        self._event_callback = event_callback
        self._rng = rng or random.Random()
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._paused = False

    def start(
        self,
        text: str,
        profile: TypingProfile,
        countdown_seconds: int = 5,
    ) -> None:
        profile.validate()
        with self._lock:
            if self._running:
                raise RuntimeError("Typing is already running")
            self._cancel_event.clear()
            self._pause_event.clear()
            self._running = True
            self._paused = False
            self._thread = threading.Thread(
                target=self._run,
                args=(text, profile, countdown_seconds),
                name="KeyMimicTypingEngine",
                daemon=True,
            )
            self._thread.start()

    def pause(self) -> None:
        with self._lock:
            if self._running and not self._paused:
                self._pause_event.set()

    def resume(self) -> None:
        with self._lock:
            if self._running:
                self._pause_event.clear()

    def cancel(self) -> None:
        self._cancel_event.set()
        self._pause_event.clear()

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def is_paused(self) -> bool:
        with self._lock:
            return self._paused

    def join(self, timeout: float | None = None) -> None:
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

    def _run(
        self,
        text: str,
        profile: TypingProfile,
        countdown_seconds: int,
    ) -> None:
        started = time.perf_counter()
        try:
            self._emit(
                "started",
                characters=len(text),
                profile=profile.name,
                countdown_seconds=countdown_seconds,
            )
            if not self._run_countdown(countdown_seconds):
                self._emit("cancelled", characters_typed=0)
                return

            with high_resolution_timer():
                typed = self._type_text(text, profile)
            if self._cancel_event.is_set():
                self._emit("cancelled", characters_typed=typed)
                logger.info("Typing cancelled after %s characters", typed)
            else:
                elapsed = time.perf_counter() - started
                self._emit("completed", characters_typed=typed, elapsed_seconds=elapsed)
                logger.info("Typing completed: %s characters in %.2fs", typed, elapsed)
        except Exception as exc:
            logger.exception("Typing failed")
            self._emit("failed", error=str(exc))
        finally:
            with self._lock:
                self._running = False
                self._paused = False
                self._pause_event.clear()

    def _run_countdown(self, countdown_seconds: int) -> bool:
        for remaining in range(countdown_seconds, 0, -1):
            self._emit("countdown_tick", remaining=remaining)
            if not self._interruptible_wait(1.0):
                return False
        return True

    def _type_text(self, text: str, profile: TypingProfile) -> int:
        last_progress = 0.0
        total = len(text)
        typed = 0

        for index, char in enumerate(text, start=1):
            if self._cancel_event.is_set():
                break

            if self._rng.random() < profile.mistake_chance and char not in "\r\n\t":
                wrong_char = self._rng.choice(string.ascii_lowercase)
                self._input.send_char(wrong_char, profile.hold_time_ms)
                if not self._wait_human_delay(profile):
                    break
                self._input.press_backspace(profile.hold_time_ms)
                if not self._wait_human_delay(profile):
                    break

            if char != "\r":
                self._input.send_char(char, profile.hold_time_ms)
            typed += 1

            now = time.perf_counter()
            if now - last_progress >= 0.1 or index == total:
                self._emit("progress_changed", characters_typed=typed, total=total)
                last_progress = now

            if not self._wait_human_delay(profile):
                break

            if char in "\n\r":
                if self._rng.random() < profile.line_break_chance:
                    wait = self._rng.uniform(
                        profile.line_break_min_seconds,
                        profile.line_break_max_seconds,
                    )
                    self._emit("paused_for_delay", reason="line_break", seconds=wait)
                    if not self._interruptible_wait(wait):
                        break
            elif self._rng.random() < profile.pause_chance:
                wait = self._rng.uniform(
                    profile.pause_min_seconds,
                    profile.pause_max_seconds,
                )
                self._emit("paused_for_delay", reason="thinking", seconds=wait)
                if not self._interruptible_wait(wait):
                    break

        return typed

    def _wait_human_delay(self, profile: TypingProfile) -> bool:
        wait = human_delay_seconds(
            profile.base_delay_seconds,
            profile.delay_variation_seconds,
            self._rng,
        )
        return self._interruptible_wait(wait)

    def _interruptible_wait(self, seconds: float) -> bool:
        deadline = time.perf_counter() + max(0.0, seconds)
        while True:
            if self._cancel_event.is_set():
                return False
            if self._pause_event.is_set():
                self._set_paused(True)
                while self._pause_event.is_set():
                    if self._cancel_event.wait(0.05):
                        return False
                self._set_paused(False)
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                return True
            if self._cancel_event.wait(min(remaining, 0.05)):
                return False

    def _set_paused(self, value: bool) -> None:
        with self._lock:
            if self._paused == value:
                return
            self._paused = value
        self._emit("paused" if value else "resumed")

    def _emit(self, name: str, **payload: Any) -> None:
        callback = self._event_callback
        if callback is not None:
            callback(TypingEvent(name=name, payload=payload))
