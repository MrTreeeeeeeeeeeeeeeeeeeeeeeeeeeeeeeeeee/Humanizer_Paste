import random
import threading

from keymimic.presets import default_custom_profile
from keymimic.typing_engine import TypingEngine


class FakeInput:
    def __init__(self) -> None:
        self.actions: list[tuple[str, str | None]] = []
        self.action_received = threading.Event()

    def send_char(self, char: str, hold_time_ms: int) -> None:
        self.actions.append(("char", char))
        self.action_received.set()

    def press_backspace(self, hold_time_ms: int) -> None:
        self.actions.append(("backspace", None))
        self.action_received.set()


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
    assert fake.action_received.wait(timeout=1)
    engine.cancel()
    engine.join(timeout=1)

    assert not engine.is_running()


def test_typing_engine_pause_resume_preserves_progress():
    profile = fast_profile()
    profile.pause_chance = 1.0
    profile.pause_min_seconds = 0.2
    profile.pause_max_seconds = 0.2
    fake = FakeInput()
    events = []
    natural_pause_started = threading.Event()

    def on_event(event):
        events.append(event)
        if event.name == "paused_for_delay":
            natural_pause_started.set()

    engine = TypingEngine(
        input_backend=fake,
        event_callback=on_event,
        rng=random.Random(2),
    )

    engine.start("abcd", profile, countdown_seconds=0)
    assert natural_pause_started.wait(timeout=1)
    engine.pause()
    assert engine.is_paused()
    before_resume = len(fake.actions)
    engine.resume()
    engine.join(timeout=2)

    assert len(fake.actions) >= before_resume
    assert events[-1].name == "completed"


def test_typing_engine_normalizes_windows_line_endings():
    fake = FakeInput()
    engine = TypingEngine(input_backend=fake, rng=random.Random(3))

    engine.start("a\r\nb\rc", fast_profile(), countdown_seconds=0)
    engine.join(timeout=2)

    assert [value for action, value in fake.actions if action == "char"] == [
        "a",
        "\n",
        "b",
        "\n",
        "c",
    ]


def test_typing_engine_focus_guard_stops_before_wrong_window():
    class FocusInput(FakeInput):
        target = 100

        def foreground_window(self):
            return self.target

        def foreground_window_title(self):
            return "Editor"

        def send_char(self, char: str, hold_time_ms: int) -> None:
            super().send_char(char, hold_time_ms)
            self.target = 200

    fake = FocusInput()
    events = []
    engine = TypingEngine(input_backend=fake, event_callback=events.append)

    engine.start("abc", fast_profile(), countdown_seconds=0, focus_guard=True)
    engine.join(timeout=2)

    assert fake.actions == [("char", "a")]
    assert events[-1].name == "failed"
    assert "focus moved" in events[-1].error
