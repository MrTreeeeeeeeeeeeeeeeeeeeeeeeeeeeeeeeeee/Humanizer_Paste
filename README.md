# KeyMimic

KeyMimic is a Windows desktop utility that types clipboard text with configurable,
human-like timing. It supports profiles, global hotkeys, pause/resume, an emergency
stop, focus protection, import/export, tray operation, and native Windows sounds.

## Start KeyMimic

Double-click **`Start KeyMimic.cmd`** in this folder.

That launcher follows `dist\current.txt` to the latest verified packaged build. It
does not require a terminal, an activated virtual environment, or a Python command.

If no packaged build exists yet, double-click **`Build KeyMimic.cmd`** once. When the
build finishes, double-click **`Start KeyMimic.cmd`** normally from then on.

## Basic use

1. Copy the text you want KeyMimic to type.
2. Choose a typing profile.
3. Click **Start** or use `Ctrl+Shift+Alt+V`.
4. During the countdown, select the application where the text belongs.
5. KeyMimic stops automatically if focus leaves that target window.

Press **Esc** at any time while typing to stop immediately. Windows plays a stop
sound when Esc is used and a different completion sound after successful typing.
Both sounds can be disabled in Settings.

## Default hotkeys

| Action | Hotkey |
| --- | --- |
| Start, pause, or resume | `Ctrl+Shift+Alt+V` |
| Emergency stop | `Esc` |
| Show or hide the window | `Ctrl+Shift+Alt+K` |

Start/show hotkeys must include Ctrl, Shift, Alt, or Win so a normal letter can
never become a dangerous system-wide trigger. Esc is only registered while a
typing session is active.

## Profiles and settings

Built-in profiles are refreshed from each application release and remain read-only.
Duplicate one to customize it. Custom profiles can be added, renamed, reordered,
deleted, imported, and exported.

Settings are stored at:

```text
%APPDATA%\KeyMimic\config.json
```

Writes are atomic and the previous settings file is retained as `config.json.bak`.
If the main file is damaged, KeyMimic restores the backup or safe defaults and
preserves the damaged file for diagnosis. Configuration upgrades are automatic.

Tray options are separate:

- **Show tray icon** controls whether the icon exists.
- **Hide in tray when closed** makes the window's close button hide the app.
- **Start minimized in the tray** starts without showing the main window.

Using **Exit KeyMimic** in the tray does not change any saved tray setting.

## Safety and privacy

- Clipboard text remains local and is never sent to a network service.
- KeyMimic snapshots the clipboard when a session begins.
- Focus protection stops input if another window becomes active.
- Only one KeyMimic process can run at once.
- Shutdown waits for the input and hotkey workers to stop cleanly.
- Shift, Ctrl, and Alt are released even if Windows input injection fails.

## Logs and troubleshooting

Logs are written to:

```text
%APPDATA%\KeyMimic\logs\keymimic.log
```

If a global hotkey is unavailable, another application probably owns it. Choose a
different combination in the Hotkeys tab. If a build is locked by OneDrive or a
running executable, the release script creates a new versioned directory instead
of overwriting the locked build.

## Run from source

Python 3.12 or newer is required only for source development:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m keymimic
```

## Quality checks

```powershell
python -m ruff check keymimic tests
python -m mypy keymimic
python -m pytest --cov=keymimic --cov-report=term-missing
```

## Package a release

Double-click `Build KeyMimic.cmd`, or run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_release.ps1
```

Each release is written under `dist\releases\<timestamp>`. The packaged smoke test
must pass before `dist\current.txt` is updated, so the normal launcher never points
at an unverified build.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the internal design.
