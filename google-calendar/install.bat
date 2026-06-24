@echo off
chcp 65001 >nul
title 선생님 캘린더 - 설치 (exe 빌드)
setlocal enabledelayedexpansion

echo ============================================================
echo   선생님 캘린더 - 새로 설치 (.exe 빌드 + 시작프로그램 등록)
echo ============================================================
echo.

REM ── 0) 작업 폴더 = 이 배치 파일이 있는 곳 ──────────────────
cd /d "%~dp0"

REM ── 1) Python 확인 ────────────────────────────────────────
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
    echo [오류] Python 이 설치되어 있지 않습니다.
    echo        https://www.python.org/downloads/ 에서 설치하세요.
    echo        설치 시 "Add python.exe to PATH" 체크 필수!
    echo.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('%PY% --version 2^>^&1') do echo  - Python: %%v
echo.

REM ── 2) 기존 설치 제거 (실행 중인 위젯 종료 + 시작등록 삭제) ─
echo [1/5] 기존 버전 제거 중...
taskkill /f /im TeacherCalendar.exe >nul 2>nul
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*desktop_app.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>nul

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP%\TeacherCalendar.vbs" del /f /q "%STARTUP%\TeacherCalendar.vbs" >nul 2>nul
if exist "%STARTUP%\TeacherCalendar.lnk" del /f /q "%STARTUP%\TeacherCalendar.lnk" >nul 2>nul
if exist "build"  rmdir /s /q "build"  >nul 2>nul
if exist "dist"   rmdir /s /q "dist"   >nul 2>nul
if exist ".webdata" rmdir /s /q ".webdata" >nul 2>nul
echo       완료.
echo.

REM ── 3) 필요한 패키지 설치 ─────────────────────────────────
echo [2/5] 패키지 설치 중... (처음엔 수백 MB 다운로드, 시간 걸립니다)
%PY% -m pip install --upgrade pip >nul 2>nul
%PY% -m pip install --upgrade PyQt6 PyQt6-WebEngine pyinstaller
if errorlevel 1 (
    echo [오류] 패키지 설치 실패. 인터넷 연결 확인 후 다시 시도하세요.
    pause & exit /b 1
)
%PY% -m pip install --upgrade pywin32 >nul 2>nul
echo.

REM ── 4) PyInstaller 로 exe 빌드 ────────────────────────────
echo [3/5] exe 빌드 중... (몇 분 걸릴 수 있습니다. 기다려 주세요)
%PY% -m PyInstaller --noconfirm --clean --windowed ^
    --name "TeacherCalendar" ^
    --add-data "index.html;." ^
    --collect-all PyQt6.QtWebEngineCore ^
    desktop_app.py
if errorlevel 1 (
    echo.
    echo [오류] 빌드 실패. 위 메시지를 확인하세요.
    pause & exit /b 1
)
echo.

set "EXEDIR=%~dp0dist\TeacherCalendar"
set "EXE=%EXEDIR%\TeacherCalendar.exe"
if not exist "%EXE%" (
    echo [오류] 빌드된 exe 를 찾을 수 없습니다: %EXE%
    pause & exit /b 1
)

REM ── 5) 시작프로그램에 바로가기 등록 ───────────────────────
echo [4/5] 시작프로그램(Windows 시작 시 자동 실행) 등록 중...
powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%STARTUP%\TeacherCalendar.lnk'); $s.TargetPath='%EXE%'; $s.WorkingDirectory='%EXEDIR%'; $s.Description='선생님 캘린더 위젯'; $s.Save()"
echo       등록됨: %STARTUP%\TeacherCalendar.lnk
echo.

REM ── 완료 + 바로 실행 ──────────────────────────────────────
echo [5/5] 설치 완료! 위젯을 실행합니다.
echo ============================================================
echo   설치 위치 : %EXE%
echo   자동 실행 : Windows 시작 시 자동으로 켜집니다.
echo   제 거    : uninstall.bat 실행
echo ============================================================
echo.
start "" "%EXE%"

echo 아무 키나 누르면 이 창이 닫힙니다.
pause >nul
endlocal
