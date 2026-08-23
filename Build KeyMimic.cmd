@echo off
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\build_release.ps1"
if errorlevel 1 (
    echo.
    echo KeyMimic build failed. Review the messages above.
    pause
    exit /b 1
)

echo.
echo KeyMimic is ready. Double-click "Start KeyMimic.cmd" to run it.
pause
