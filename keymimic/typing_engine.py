from __future__ import annotations

import copy
import logging
import random
import string
import threading
import time
from collections.abc import Callable
from typing import Protocol

from .events import SessionState, TypingEvent, TypingEventKind
from .models import TypingProfile
from .timing import human_delay_seconds
from .win_input import WindowsInput, high_resolution_timer

logger = logging.getLogger(__name__)


class InputBackend(Protocol):
    def send_char(self, char: str, hold_time_ms: int) -> None: ...

    def press_backspace(self, hold_time_ms: int) -> None: ...


TypingEventCallback = Callable[[TypingEvent], None]


class TypingFocusChangedError(RuntimeError):
    pass


class TypingEngine:
    def __init__(
        self,
        input_backend: InputBackend | None = None,
        event_callback: TypingEventCallback | None = None,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._rng = rng or random.Random()
        self._input = input_backend or WindowsInput(rng=self._rng)
        self._event_callback = event_callback
        self._clock = clock
        self._condition = threading.Condition(threading.RLock())
        self._thread: threading.Thread | None = None
        self._state = SessionState.IDLE
        self._resume_state = SessionState.TYPING
        self._cancel_requested = False
        self._focus_guard = False
        self._target_window: int | None = None
        self._target_title = ""

    @property
    def state(self) -> SessionState:
        with self._condition:
            return self._state

    def start(
        self,
        text: str,
        profile: TypingProfile,
        countdown_seconds: int = 5,
        *,
        focus_guard: bool = False,
    ) -> None:
        profile.validate()
        if not 0 <= countdown_seconds <= 30:
            raise ValueError("Countdown must be between 0 and 30 seconds")
        normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
        profile_snapshot = copy.deepcopy(profile)
        with self._condition:
            if self.is_running():
                raise RuntimeError("Typing is already running")
            self._cancel_requested = False
            self._focus_guard = focus_guard
            self._target_window = None
            self._target_title = ""
            self._state = (
                SessionState.COUNTDOWN if countdown_seconds else SessionState.TYPING
            )
            self._thread = threading.Thread(
                target=self._run,
                args=(normalized_text, profile_snapshot, countdown_seconds),
                name="KeyMimicTypingEngine",
                daemon=False,
            )
            self._thread.start()

    def pause(self) -> None:
        changed = False
        with self._condition:
            if self.is_running() and self._state not in {
                SessionState.PAUSED,
                SessionState.STOPPING,
            }:
                self._resume_state = self._state
                self._state = SessionState.PAUSED
                changed = True
                self._condition.notify_all()
        if changed:
            self._emit(TypingEventKind.PAUSED, SessionState.PAUSED)

    def resume(self) -> None:
        changed = False
        with self._condition:
            if self._state == SessionState.PAUSED:
                self._state = self._resume_state
                changed = True
                self._condition.notify_all()
        if changed:
            self._emit(TypingEventKind.RESUMED, self.state)

    def cancel(self) -> None:
        with self._condition:
            if self.is_running():
                self._cancel_requested = True
                self._state = SessionState.STOPPING
                self._condition.notify_all()

    def is_running(self) -> bool:
        return self._state in {
            SessionState.COUNTDOWN,
            SessionState.TYPING,
            SessionState.PAUSED,
            SessionState.STOPPING,
        }

    def is_paused(self) -> bool:
        return self.state == SessionState.PAUSED

    def join(self, timeout: float | None = None) -> bool:
        thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def shutdown(self, timeout: float = 2.0) -> bool:
        self.cancel()
        return self.join(timeout)

    def _run(
        self,
        text: str,
        profile: TypingProfile,
        countdown_seconds: int,
    ) -> None:
        started = self._clock()
        typed = 0
        total = len(text)
        try:
            self._emit(
                TypingEventKind.STARTED,
                self.state,
                total=total,
                remaining=countdown_seconds,
            )
            if not self._run_countdown(countdown_seconds):
                self._finish_cancelled(typed, total)
                return

            self._set_state(SessionState.TYPING)
            self._acquire_target()
            with high_resolution_timer():
                typed = self._type_text(text, profile, started)
            if self._is_cancel_requested():
                self._finish_cancelled(typed, total)
            else:
                elapsed = self._clock() - started
                self._set_state(SessionState.COMPLETED)
                self._emit(
                    TypingEventKind.COMPLETED,
                    SessionState.COMPLETED,
                    characters_typed=typed,
                    total=total,
                    elapsed_seconds=elapsed,
                )
                logger.info("Typing completed: %s characters in %.2fs", typed, elapsed)
        except Exception as exc:
            logger.exception("Typing failed")
            self._set_state(SessionState.FAILED)
            self._emit(
                TypingEventKind.FAILED,
                SessionState.FAILED,
                characters_typed=typed,
                total=total,
                error=str(exc),
            )
        finally:
            with self._condition:
                self._cancel_requested = False
                self._target_window = None
                self._condition.notify_all()

    def _run_countdown(self, countdown_seconds: int) -> bool:
        for remaining in range(countdown_seconds, 0, -1):
            self._emit(
                TypingEventKind.COUNTDOWN_TICK,
                SessionState.COUNTDOWN,
                remaining=remaining,
            )
            if not self._interruptible_wait(1.0):
                return False
        return True

    def _type_text(
        self,
        text: str,
        profile: TypingProfile,
        started: float,
    ) -> int:
        last_progress = 0.0
        total = len(text)
        typed = 0
        for char in text:
            if self._is_cancel_requested():
                break
            self._wait_while_paused()
            self._verify_target()

            if self._should_make_mistake(char, profile):
                wrong_char = self._wrong_character(char)
                self._input.send_char(wrong_char, profile.hold_time_ms)
                if not self._wait_human_delay(profile):
                    break
                self._input.press_backspace(profile.hold_time_ms)
                if not self._wait_human_delay(profile):
                    break

            self._input.send_char(char, profile.hold_time_ms)
            typed += 1
            now = self._clock()
            if now - last_progress >= 0.1 or typed == total:
                elapsed = max(0.0, now - started)
                eta = (elapsed / typed) * (total - typed) if typed else 0.0
                self._emit(
                    TypingEventKind.PROGRESS_CHANGED,
                    SessionState.TYPING,
                    characters_typed=typed,
                    total=total,
                    elapsed_seconds=elapsed,
                    estimated_remaining_seconds=eta,
                )
                last_progress = now

            if not self._wait_human_delay(profile):
                break

            if char == "\n":
                if self._rng.random() < profile.line_break_chance:
                    wait = self._rng.uniform(
                        profile.line_break_min_seconds,
                        profile.line_break_max_seconds,
                    )
                    if not self._run_natural_pause("line break", wait):
                        break
            elif self._rng.random() < profile.pause_chance:
                wait = self._rng.uniform(
                    profile.pause_min_seconds,
                    profile.pause_max_seconds,
                )
                if not self._run_natural_pause("thinking", wait):
                    break
        return typed

    def _should_make_mistake(self, char: str, profile: TypingProfile) -> bool:
        return char not in "\n\t" and self._rng.random() < profile.mistake_chance

    def _wrong_character(self, actual: str) -> str:
        choices = string.ascii_lowercase.replace(actual.casefold(), "")
        return self._rng.choice(choices or string.ascii_lowercase)

    def _run_natural_pause(self, reason: str, seconds: float) -> bool:
        self._emit(
            TypingEventKind.PAUSED_FOR_DELAY,
            SessionState.TYPING,
            reason=reason,
            delay_seconds=seconds,
        )
        return self._interruptible_wait(seconds)

    def _wait_human_delay(self, profile: TypingProfile) -> bool:
        wait = human_delay_seconds(
            profile.base_delay_seconds,
            profile.delay_variation_seconds,
            self._rng,
        )
        return self._interruptible_wait(wait)

    def _interruptible_wait(self, seconds: float) -> bool:
        remaining = max(0.0, seconds)
        with self._condition:
            while remaining > 0:
                if self._cancel_requested:
                    return False
                while self._state == SessionState.PAUSED and not self._cancel_requested:
                    self._condition.wait()
                if self._cancel_requested:
                    return False
                wait_started = self._clock()
                self._condition.wait(timeout=remaining)
                remaining -= max(0.0, self._clock() - wait_started)
        return not self._is_cancel_requested()

    def _wait_while_paused(self) -> None:
        with self._condition:
            while self._state == SessionState.PAUSED and not self._cancel_requested:
                self._condition.wait()

    def _acquire_target(self) -> None:
        if not self._focus_guard:
            return
        foreground = getattr(self._input, "foreground_window", None)
        title_reader = getattr(self._input, "foreground_window_title", None)
        if not callable(foreground):
            return
        self._target_window = foreground()
        self._target_title = title_reader() if callable(title_reader) else ""
        if self._target_window is not None:
            self._emit(
                TypingEventKind.TARGET_ACQUIRED,
                SessionState.TYPING,
                target_window=self._target_title,
            )

    def _verify_target(self) -> None:
        if not self._focus_guard or self._target_window is None:
            return
        foreground = getattr(self._input, "foreground_window", None)
        if callable(foreground) and foreground() != self._target_window:
            raise TypingFocusChangedError(
                "Typing stopped because focus moved away from "
                f"{self._target_title or 'the target window'}."
            )

    def _finish_cancelled(self, typed: int, total: int) -> None:
        self._set_state(SessionState.CANCELLED)
        self._emit(
            TypingEventKind.CANCELLED,
            SessionState.CANCELLED,
            characters_typed=typed,
            total=total,
        )
        logger.info("Typing cancelled after %s characters", typed)

    def _set_state(self, state: SessionState) -> None:
        with self._condition:
            if self._state != SessionState.PAUSED:
                self._state = state
            else:
                self._resume_state = state
            self._condition.notify_all()

    def _is_cancel_requested(self) -> bool:
        with self._condition:
            return self._cancel_requested

    def _emit(
        self,
        kind: TypingEventKind,
        state: SessionState,
        **values: object,
    ) -> None:
        callback = self._event_callback
        if callback is None:
            return
        event = TypingEvent(kind=kind, state=state, **values)  # type: ignore[arg-type]
        try:
            callback(event)
        except Exception:
            logger.exception("Typing event callback failed: %s", kind.value)
