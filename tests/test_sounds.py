import winsound

from keymimic.sounds import SystemSoundPlayer


def test_stop_and_completion_use_distinct_windows_system_sounds(monkeypatch):
    played: list[int] = []
    monkeypatch.setattr(winsound, "MessageBeep", played.append)
    player = SystemSoundPlayer(enabled=True)

    player.play_stop()
    player.play_completed()

    assert played == [0x10, 0x40]


def test_sounds_can_be_disabled(monkeypatch):
    played: list[int] = []
    monkeypatch.setattr(winsound, "MessageBeep", played.append)

    SystemSoundPlayer(enabled=False).play_completed()

    assert played == []
