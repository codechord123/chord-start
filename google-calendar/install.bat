@echo off
title Teacher Calendar - Install
echo ============================================
echo  Teacher Calendar - Install
echo ============================================
echo.

set PY=
where py >nul 2>nul && set PY=py
if not defined PY (
    where python >nul 2>nul && set PY=python
)
if not defined PY (
    echo [ERROR] Python not found.
    echo   Install from: https://www.python.org/downloads/
    echo   Check "Add python.exe to PATH" during install.
    echo.
    pause
    exit /b 1
)

set PYW=pythonw
if "%PY%"=="py" set PYW=pyw

for /f "tokens=*" %%v in ('%PY% --version 2^>^&1') do echo Python: %%v
echo.

echo [1/2] Installing PyQt6 and PyQt6-WebEngine...
echo       (First run downloads about 150MB, please wait)
%PY% -m pip install --upgrade PyQt6 PyQt6-WebEngine
if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed.
    echo   Try running as Administrator.
    echo.
    pause
    exit /b 1
)
echo.

echo [2/2] Adding to Windows startup...
set "VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TeacherCalendar.vbs"
echo CreateObject("WScript.Shell").Run "%PYW% ""%~dp0desktop_app.py""", 0, False> "%VBS%"
echo   Registered: %VBS%
echo.

echo ============================================
echo  Done! Starting the calendar now...
echo  (Starts automatically with Windows)
echo ============================================
echo.
start "" %PYW% "%~dp0desktop_app.py"

echo Press any key to close this window.
pause >nul
