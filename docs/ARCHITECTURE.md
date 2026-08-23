# KeyMimic architecture

KeyMimic uses four explicit layers.

## Domain

- `models.py` contains validated, serializable settings and profile values.
- `events.py` defines typed session states and events.
- `timing.py` calculates delays and user-facing estimates.

## Application services

- `typing_engine.py` owns the countdown and input worker state machine.
- `session_controller.py` bridges worker events to Qt and owns session sounds.
- `profile_service.py` performs profile mutations while preserving stable IDs.
- `config.py` owns schema migration, atomic persistence, backup, and recovery.

## Windows adapters

- `win_input.py` wraps `SendInput`, keyboard layout mapping, focus detection, and
  high-resolution timer control.
- `hotkeys.py` owns `RegisterHotKey` registrations in one message-loop thread.
- `single_instance.py` owns the Windows mutex.
- `sounds.py` uses Windows system sounds instead of shipping media files.

## Presentation

- `ui/main_window.py` coordinates top-level application behavior.
- `ui/profile_controller.py` isolates profile editing and dirty-state workflow.
- Panel modules own their controls but do not perform persistence or input work.
- `ui/tray_controller.py` owns tray-only behavior.

Worker-to-UI communication always crosses Qt signals. Native workers never mutate
widgets. Shutdown proceeds in the opposite order of startup: cancel typing, join
the typing worker, stop the hotkey message loop, hide the tray icon, then quit Qt.

## Session states

```text
idle -> countdown -> typing -> completed
                 |       |  -> failed
                 |       |  -> cancelled
                 +-> paused -> typing
```

`stopping` is an intermediate cancellation state. Terminal states are retained for
diagnostics until the next session begins.
