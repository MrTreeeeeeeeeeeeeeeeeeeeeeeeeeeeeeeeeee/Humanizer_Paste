@echo off
setlocal

set "KEYMIMIC_EXE=%~dp0dist\rebuilt\KeyMimic\KeyMimic.exe"

if not exist "%KEYMIMIC_EXE%" (
    echo KeyMimic could not be found.
    echo Expected file: "%KEYMIMIC_EXE%"
    echo.
    echo Rebuild the app, then try this launcher again.
    pause
    exit /b 1
)

start "" "%KEYMIMIC_EXE%"
