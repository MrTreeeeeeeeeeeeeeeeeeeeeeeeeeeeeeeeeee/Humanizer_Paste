from keymimic.config import default_config
from keymimic.hotkeys import GlobalHotkeyManager
from keymimic.ui.main_window import MainWindow
from keymimic.ui.settings_panel import SettingsPanel
from keymimic.ui.status_bar import StatusBarWidget


def test_settings_panel_round_trip(qtbot):
    config = default_config()
    panel = SettingsPanel()
    qtbot.addWidget(panel)
    panel.load(config)

    panel.countdown.setValue(2)
    panel.focus_guard.setChecked(False)
    panel.sounds.setChecked(False)
    panel.close_to_tray.setChecked(True)
    panel.apply_to(config)

    assert config.countdown_seconds == 2
    assert not config.focus_guard_enabled
    assert not config.sounds_enabled
    assert config.close_to_tray


def test_status_bar_exposes_session_state(qtbot):
    status = StatusBarWidget()
    qtbot.addWidget(status)

    status.set_running("Typing 2/10")
    assert status.stop_button.isEnabled()
    assert status.start_pause_button.text().startswith("Pause")

    status.set_paused()
    assert status.start_pause_button.text().startswith("Resume")

    status.set_idle("Done")
    assert not status.stop_button.isEnabled()
    assert status.status_label.text() == "Done"


def test_main_window_constructs_with_services_isolated(qtbot, monkeypatch):
    monkeypatch.setattr(
        GlobalHotkeyManager,
        "apply_bindings",
        lambda self, bindings, callback=None: {action: "test" for action in bindings},
    )
    monkeypatch.setattr(GlobalHotkeyManager, "stop", lambda self: None)
    monkeypatch.setattr("keymimic.ui.main_window.save_config", lambda config: None)
    config = default_config()
    config.close_to_tray = False

    window = MainWindow(config)
    qtbot.addWidget(window)

    assert window.windowTitle() == "KeyMimic"
    assert window.profile_sidebar.list_widget.count() == 6
    assert window.session.state == "idle"
