# KeyMimic

KeyMimic is a Windows desktop utility that types clipboard text with configurable
human-like timing. This Python rewrite keeps the original AutoHotkey workflow
and adds a native UI, JSON settings, configurable hotkeys, profile management,
pause/resume, import/export, and a background typing engine.

## Requirements

- Windows 10 or newer
- Python 3.12+

## Run From Source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m keymimic
```

## Settings

Settings are stored in:

```text
%APPDATA%\KeyMimic\config.json
```

On first launch, the app migrates `Humanizer_paste_Settings.ini` if it exists in
the current working directory. The original INI file is left unchanged.

Saved settings include:

- Last selected profile
- Custom profiles
- All hotkeys
- Countdown duration
- Tooltip, tray, startup, log level, and window settings

## Default Hotkeys

```text
Start / pause / resume typing    Ctrl+Shift+Alt+V
Stop typing immediately          Esc
Show / hide KeyMimic window      Ctrl+Shift+Alt+K
```

All hotkeys can be changed in the Hotkeys tab and are saved with the rest of the
settings. Duplicate hotkeys and invalid key strings are rejected before saving.

## Build A Windows EXE

```powershell
python -m pip install -e ".[dev]"
python -m PyInstaller --noconfirm KeyMimic.spec
```

The generated app will be under `dist\KeyMimic`.

## Tests

```powershell
python -m pytest
```

Most tests are platform-safe. Tests that require native Windows hotkey APIs are
skipped automatically outside Windows.
