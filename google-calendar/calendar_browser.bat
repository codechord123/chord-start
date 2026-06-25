@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>nul
title Teacher Calendar (Browser Mode)
cd /d "%~dp0"

rem ── 안전 모드 실행기 ────────────────────────────────────────────────
rem 내장 위젯이 안 뜨는 PC 에서도 캘린더를 기본 브라우저로 띄운다.

set "PYCMD="
for /f "usebackq delims=" %%v in (`python -c "print('PYOK')" 2^>nul`) do set "OUT=%%v"
if "!OUT!"=="PYOK" set "PYCMD=python"
if not defined PYCMD (
    for /f "usebackq delims=" %%v in (`py -3 -c "print('PYOK')" 2^>nul`) do set "OUT2=%%v"
    if "!OUT2!"=="PYOK" set "PYCMD=py -3"
)
if not defined PYCMD (
    echo Python 을 찾지 못했습니다. 먼저 install.bat 을 실행하세요.
    pause
    exit /b 1
)

start "" !PYCMD! "%~dp0desktop_app.py" --browser
