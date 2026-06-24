@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>nul
title Teacher Calendar Installer
cd /d "%~dp0"

echo ============================================================
echo   Teacher Calendar - Installer
echo ============================================================
echo.

rem --- Python 3.12 가 이미 설치돼 있으면 우선 사용 ---
py -3.12 --version >nul 2>nul
if not errorlevel 1 (
    py -3.12 "%~dp0install.py"
    set "RC=!ERRORLEVEL!"
    goto DONE
)

rem --- 다른 Python 시도 (install.py 가 버전 자동 업그레이드 처리) ---
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY goto NOPY

!PY! "%~dp0install.py"
set "RC=!ERRORLEVEL!"
goto DONE

:DONE
echo.
if "!RC!"=="0" (
    echo Installation finished. You may close this window.
) else (
    echo [ERROR] Installation did not complete. See messages above.
)
echo.
pause
exit /b !RC!

:NOPY
echo [ERROR] Python not found on this PC.
echo.
echo   1. Download Python 3.12 from:
echo      https://www.python.org/downloads/release/python-3129/
echo   2. During install CHECK "Add python.exe to PATH"
echo   3. Run install.bat again
echo.
pause
exit /b 1
