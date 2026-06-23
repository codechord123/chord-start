@echo off
title Teacher Calendar - Install (Python 3.12)
echo ============================================
echo  Teacher Calendar - Install for Python 3.12
echo ============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python Launcher (py.exe) not found.
    echo   Install Python 3.12 from: https://www.python.org/downloads/
    echo   Check "Add python.exe to PATH" during install.
    echo.
    pause
    exit /b 1
)

py -3.12 --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3.12 is not installed.
    echo   Download Python 3.12 from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('py -3.12 --version 2^>^&1') do echo Python: %%v
echo.

echo [1/2] Installing PyQt6 and PyQt6-WebEngine for Python 3.12...
echo       (First run downloads about 150MB, please wait)
py -3.12 -m pip install --upgrade PyQt6 PyQt6-WebEngine
if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed.
    echo   Try running as Administrator.
    echo.
    pause
    exit /b 1
)
echo.

echo [2/2] Adding to Windows startup (Python 3.12)...
set "VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TeacherCalendar.vbs"
echo CreateObject("WScript.Shell").Run "pyw -3.12 ""%~dp0desktop_app.py""", 0, False> "%VBS%"
echo   Registered: %VBS%
echo.

echo ============================================
echo  Done! Starting the calendar now...
echo  (Starts automatically with Windows)
echo ============================================
echo.
start "" pyw -3.12 "%~dp0desktop_app.py"

echo Press any key to close this window.
pause >nul
