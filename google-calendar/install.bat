@echo off
title Teacher Calendar Install
echo ============================================
echo  Teacher Calendar (Desktop App) - Install
echo ============================================
echo.

REM ── Find Python ──────────────────────────────────────
set PY=
where py >nul 2>nul && set PY=py
if not defined PY (
    where python >nul 2>nul && set PY=python
)
if not defined PY (
    echo [ERROR] Python not found.
    echo   Install from https://www.python.org/downloads/
    echo   and CHECK "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

REM windowless launcher name
set PYW=pythonw
if "%PY%"=="py" set PYW=pyw

echo Python found: %PY%
echo.

REM ── Install PyQt6 + WebEngine ────────────────────────
echo [1/2] Installing PyQt6 and PyQt6-WebEngine...
echo       (first time downloads ~150MB, please wait)
%PY% -m pip install PyQt6 PyQt6-WebEngine
echo.

REM ── Register startup (single safe line) ──────────────
echo [2/2] Registering Windows startup...
set "VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TeacherCalendar.vbs"
echo CreateObject("WScript.Shell").Run "%PYW% ""%~dp0desktop_app.py""", 0, False> "%VBS%"

echo.
echo ============================================
echo  Done! Starting the calendar now...
echo  (It will also start automatically with Windows)
echo ============================================
start "" %PYW% "%~dp0desktop_app.py"

echo.
echo Setup complete. You can close this window.
pause
