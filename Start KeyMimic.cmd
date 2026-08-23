@echo off
setlocal

set "KEYMIMIC_POINTER=%~dp0dist\current.txt"
set "KEYMIMIC_EXE="

if exist "%KEYMIMIC_POINTER%" (
    set /p KEYMIMIC_RELATIVE=<"%KEYMIMIC_POINTER%"
)

if defined KEYMIMIC_RELATIVE (
    set "KEYMIMIC_EXE=%~dp0%KEYMIMIC_RELATIVE%"
)

if not exist "%KEYMIMIC_EXE%" (
    echo KeyMimic could not be found.
    echo Expected file: "%KEYMIMIC_EXE%"
    echo.
    echo Run "Build KeyMimic.cmd" once, then try this launcher again.
    pause
    exit /b 1
)

start "" "%KEYMIMIC_EXE%"
