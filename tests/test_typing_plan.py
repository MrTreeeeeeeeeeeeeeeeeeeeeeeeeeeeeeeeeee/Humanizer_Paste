import random
import time

from keymimic.presets import default_custom_profile
from keymimic.typing_engine import TypingEngine


class FakeInput:
    def __init__(self) -> None:
        self.actions: list[tuple[str, str | None]] = []

    def send_char(self, char: str, hold_time_ms: int) -> None:
        self.actions.append(("char", char))

    def press_backspace(self, hold_time_ms: int) -> None:
        self.actions.append(("backspace", None))


def fast_profile():
    profile = default_custom_profile("Fast")
    profile.base_delay_seconds = 0.001
    profile.delay_variation_seconds = 0.0
    profile.hold_time_ms = 5
    profile.pause_chance = 0.0
    profile.line_break_chance = 0.0
    profile.mistake_chance = 0.0
    return profile


def test_typing_engine_completes_with_fake_input():
    events = []
    fake = FakeInput()
    engine = TypingEngine(
        input_backend=fake,
        event_callback=events.append,
        rng=random.Random(1),
    )

    engine.start("abc", fast_profile(), countdown_seconds=0)
    engine.join(timeout=2)

    assert [action for action, _ in fake.actions] == ["char", "char", "char"]
    assert events[-1].name == "completed"


def test_typing_engine_cancel_interrupts_wait():
    profile = fast_profile()
    profile.pause_chance = 1.0
    profile.pause_min_seconds = 10.0
    profile.pause_max_seconds = 10.0
    fake = FakeInput()
    engine = TypingEngine(input_backend=fake, rng=random.Random(1))

    engine.start("abc", profile, countdown_seconds=0)
    time.sleep(0.05)
    start = time.perf_counter()
    engine.cancel()
    engine.join(timeout=1)

    assert time.perf_counter() - start < 0.5
    assert not engine.is_running()


def test_typing_engine_pause_resume_preserves_progress():
    profile = fast_profile()
    profile.pause_chance = 1.0
    profile.pause_min_seconds = 0.2
    profile.pause_max_seconds = 0.2
    fake = FakeInput()
    events = []
    engine = TypingEngine(
        input_backend=fake,
        event_callback=events.append,
        rng=random.Random(2),
    )

    engine.start("abcd", profile, countdown_seconds=0)
    time.sleep(0.03)
    engine.pause()
    time.sleep(0.08)
    assert engine.is_paused()
    before_resume = len(fake.actions)
    engine.resume()
    engine.join(timeout=2)

    assert len(fake.actions) >= before_resume
    assert events[-1].name == "completed"
