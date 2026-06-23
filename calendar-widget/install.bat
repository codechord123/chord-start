@echo off
echo ================================
echo  Teacher Calendar - Install
echo ================================
echo.

REM ── Python 찾기 ──────────────────────────────────────
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
    echo   4. Click Install Now
    echo   5. Run this file again
    echo.
    pause
    exit /b 1
)

echo Python found: %PY%
echo.

REM ── PyQt6 설치 ───────────────────────────────────────
echo [1/2] Installing PyQt6 (first time may take a minute)...
%PY% -m pip install PyQt6
if errorlevel 1 (
    echo [ERROR] PyQt6 install failed. Check internet connection.
    pause
    exit /b 1
)

REM ── 시작프로그램 등록 ────────────────────────────────
echo.
echo [2/2] Registering startup...

set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set CALDIR=%~dp0

REM 시작폴더에 VBS 런처 생성 (검은 창 없이 실행)
(
    echo Dim fso, dir, ws
    echo Set fso = CreateObject^("Scripting.FileSystemObject"^)
    echo dir = "%CALDIR:~0,-1%"
    echo Set ws = CreateObject^("WScript.Shell"^)
    echo ws.CurrentDirectory = dir
    echo ws.Run "pythonw """ ^& dir ^& "\main.py""", 0, False
    echo Set ws = Nothing
    echo Set fso = Nothing
) > "%STARTUP%\TeacherCalendar.vbs"

echo.
echo ================================
echo  Install complete!
echo.
echo  - Calendar will start automatically when Windows starts
echo  - To remove from startup: run uninstall.bat
echo ================================
echo.
echo Starting calendar now...
%PY% main.py
