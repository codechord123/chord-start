@echo off
echo ================================
echo  Teacher Calendar - Run
echo ================================
echo.

REM --- Find Python (py launcher or python) ---
set PY=
where py >nul 2>nul && set PY=py
if "%PY%"=="" (
    where python >nul 2>nul && set PY=python
)

if "%PY%"=="" (
    echo [ERROR] Python was not found.
    echo.
    echo Please install Python first:
    echo   1. Open https://www.python.org/downloads/
    echo   2. Run the installer
    echo   3. IMPORTANT: check "Add python.exe to PATH" at the bottom
    echo   4. Click "Install Now"
    echo   5. Close this window, then run this file again
    echo.
    pause
    exit /b
)

echo Using Python: %PY%
echo.
echo Installing PyQt6 (first time only)...
%PY% -m pip install PyQt6 >nul 2>nul

echo Starting calendar...
%PY% main.py

pause
