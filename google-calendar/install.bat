@echo off
chcp 65001 >nul 2>nul
title Teacher Calendar Installer
cd /d "%~dp0"

echo ============================================================
echo   Teacher Calendar - Installer
echo ============================================================
echo.

rem --- find Python launcher ---
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)

if not defined PY goto NOPY

rem --- run the real installer (Python handles all the work) ---
%PY% "%~dp0install.py"
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" goto FAIL
echo Installation finished. You may close this window.
echo.
pause
exit /b 0

:FAIL
echo [ERROR] Installation did not complete. See messages above.
echo.
pause
exit /b 1

:NOPY
echo [ERROR] Python was not found on this PC.
echo.
echo   1. Download Python 3.11 or newer:
echo      https://www.python.org/downloads/
echo   2. During install, CHECK "Add python.exe to PATH".
echo   3. After install, run this install.bat again.
echo.
pause
exit /b 1
