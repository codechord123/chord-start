@echo off
echo ============================================
echo  Teacher Calendar (Desktop App) - Install
echo ============================================
echo.

REM ── Find Python ──────────────────────────────────────
set PY=
where py >nul 2>nul     && set PY=py
if "%PY%"=="" (
    where python >nul 2>nul && set PY=python
)
if "%PY%"=="" (
    echo [ERROR] Python not found.
    echo.
    echo   1. Open https://www.python.org/downloads/
    echo   2. Run the installer
    echo   3. CHECK "Add python.exe to PATH" at the bottom
    echo   4. Click Install Now, then run this file again
    echo.
    pause
    exit /b 1
)
echo Python found: %PY%
echo.

REM ── Install PyQt6 + WebEngine (downloads Chromium, ~150MB) ──
echo [1/2] Installing PyQt6 and PyQt6-WebEngine...
echo       (first time can take a few minutes - please wait)
%PY% -m pip install PyQt6 PyQt6-WebEngine
if errorlevel 1 (
    echo [ERROR] Install failed. Check your internet connection.
    pause
    exit /b 1
)

REM ── Register in Windows startup ──────────────────────
echo.
echo [2/2] Registering startup...
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set CALDIR=%~dp0

(
    echo Set ws = CreateObject^("WScript.Shell"^)
    echo ws.CurrentDirectory = "%CALDIR:~0,-1%"
    echo ws.Run "pythonw """ ^& "%CALDIR:~0,-1%" ^& "\desktop_app.py""", 0, False
) > "%STARTUP%\TeacherCalendar.vbs"

echo.
echo ============================================
echo  Done! The calendar will start with Windows.
echo  (To remove: run uninstall.bat)
echo ============================================
echo.
echo Starting calendar now...
start "" pythonw "%CALDIR%desktop_app.py"
echo.
echo You can close this window.
pause
