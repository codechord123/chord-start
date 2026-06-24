@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>nul
title Teacher Calendar Installer
cd /d "%~dp0"

echo ============================================================
echo   Teacher Calendar - Installer
echo ============================================================
echo.
echo Looking for a usable Python...
echo.

set "PYCMD="

rem --- Try interpreters in order of preference. Each is tested by
rem     actually running it, so a broken launcher default is skipped. ---
call :TRY py -3.12
if defined PYCMD goto RUN
call :TRY py -3.13
if defined PYCMD goto RUN
call :TRY py -3.11
if defined PYCMD goto RUN
call :TRY py -3.10
if defined PYCMD goto RUN
call :TRY python
if defined PYCMD goto RUN
call :TRY py -3.14
if defined PYCMD goto RUN
call :TRY py -3
if defined PYCMD goto RUN
call :TRY python3
if defined PYCMD goto RUN

goto BOOTSTRAP

:TRY
rem %* = candidate command (e.g. "py -3.12"). Test it silently.
%* -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYCMD=%*"
goto :eof

:RUN
echo Using Python: !PYCMD!
echo.
!PYCMD! "%~dp0install.py"
set "RC=!ERRORLEVEL!"
goto DONE

:BOOTSTRAP
echo No usable Python was found on this PC.
echo Attempting to download Python 3.12 automatically...
echo (about 25 MB - an internet connection is required)
echo.
set "PYINST=%TEMP%\python-3.12.9-amd64.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe' -OutFile $env:PYINST } catch { exit 1 }"
if errorlevel 1 goto MANUAL
echo.
echo Installing Python 3.12. A setup window may appear; please wait...
"%PYINST%" /passive InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0
del "%PYINST%" >nul 2>nul
py -3.12 -c "import sys" >nul 2>nul
if errorlevel 1 goto MANUAL
set "PYCMD=py -3.12"
goto RUN

:MANUAL
echo.
echo [ERROR] Could not set up Python automatically.
echo.
echo   1. Download Python 3.12 from:
echo      https://www.python.org/downloads/release/python-3129/
echo   2. During install, CHECK "Add python.exe to PATH"
echo   3. Run install.bat again
echo.
pause
exit /b 1

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
