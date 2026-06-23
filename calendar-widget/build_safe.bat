@echo off
echo ================================
echo  Teacher Calendar - Build
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

echo [1/3] Upgrading pip...
%PY% -m pip install --upgrade pip

echo.
echo [2/3] Installing PyQt6 and PyInstaller...
%PY% -m pip install PyQt6 pyinstaller

echo.
echo [3/3] Building TeacherCalendar.exe ...

if not exist data.json echo {}> data.json
if not exist config.json echo {}> config.json

%PY% -m PyInstaller --onefile --windowed --name TeacherCalendar main.py

echo.
echo ================================
echo  Done!  Opening the dist folder...
echo  Run: dist\TeacherCalendar.exe
echo ================================

REM Open the dist folder in Explorer automatically
if exist dist\TeacherCalendar.exe (
    explorer dist
) else (
    echo [ERROR] Build did not produce the exe. Scroll up to see the error.
)
pause
