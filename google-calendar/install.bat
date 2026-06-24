@echo off
chcp 65001 >nul
title 선생님 캘린더 - 설치
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "LOG=%~dp0install.log"
echo 설치 시작: %DATE% %TIME% > "%LOG%"

echo ============================================================
echo   선생님 캘린더 - 설치 프로그램
echo ============================================================
echo.
echo  로그 파일: %LOG%
echo.

REM ── Python 확인 ─────────────────────────────────────────────────────────
set "PY="
where py     >nul 2>nul && set "PY=py"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
    echo [오류] Python 을 찾을 수 없습니다.
    echo.
    echo  해결 방법:
    echo   1) https://www.python.org/downloads/ 에서 Python 3.11 이상 설치
    echo   2) 설치 시 "Add python.exe to PATH" 반드시 체크
    echo   3) 설치 완료 후 이 파일을 다시 실행
    echo.
    pause & exit /b 1
)

for /f "tokens=*" %%v in ('%PY% --version 2^>^&1') do (
    echo  - %%v
    echo Python: %%v >> "%LOG%"
)
echo.

REM ── 1. 기존 버전 정리 ───────────────────────────────────────────────────
echo [1/4] 기존 버전 정리 중...
taskkill /f /im TeacherCalendar.exe >nul 2>nul
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object {$_.CommandLine -like '*desktop_app.py*'} | ForEach-Object {Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue}" >nul 2>nul

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP%\TeacherCalendar.lnk" del /f /q "%STARTUP%\TeacherCalendar.lnk" >nul 2>nul
if exist "%STARTUP%\TeacherCalendar.vbs" del /f /q "%STARTUP%\TeacherCalendar.vbs" >nul 2>nul
if exist "build"    rmdir /s /q "build"    >nul 2>nul
if exist "dist"     rmdir /s /q "dist"     >nul 2>nul
if exist ".webdata" rmdir /s /q ".webdata" >nul 2>nul
echo       완료.

REM ── 2. 패키지 설치 ──────────────────────────────────────────────────────
echo.
echo [2/4] 패키지 설치 중... (첫 설치는 수백 MB 다운로드, 몇 분 소요)
echo       인터넷 연결이 필요합니다.
echo.
%PY% -m pip install --upgrade pip >> "%LOG%" 2>&1
%PY% -m pip install --upgrade PyQt6 PyQt6-WebEngine pyinstaller
if errorlevel 1 (
    echo.
    echo [오류] 패키지 설치에 실패했습니다.
    echo   - 인터넷 연결 상태를 확인하세요.
    echo   - 우클릭 ^-^> "관리자 권한으로 실행" 후 다시 시도하세요.
    echo   - 자세한 내용: %LOG%
    pause & exit /b 1
)
%PY% -m pip install --upgrade pywin32 >> "%LOG%" 2>&1
echo       완료.

REM ── PyQt6 WebEngine 동작 확인 ───────────────────────────────────────────
echo.
echo  PyQt6 WebEngine 확인 중...
%PY% -c "from PyQt6.QtWebEngineWidgets import QWebEngineView; print('OK')" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [오류] PyQt6-WebEngine 설치가 올바르지 않습니다.
    echo        아래 명령으로 수동 설치 후 다시 실행하세요:
    echo        %PY% -m pip install --force-reinstall PyQt6 PyQt6-WebEngine
    pause & exit /b 1
)
echo       확인됨.

REM ── 3. PyInstaller exe 빌드 ─────────────────────────────────────────────
echo.
echo [3/4] TeacherCalendar.exe 빌드 중...
echo       ※ 창이 멈춘 것처럼 보여도 빌드 중입니다. 5~10분 기다려 주세요!
echo       빌드 상세 로그: %LOG%
echo.

%PY% -m PyInstaller --noconfirm --clean --windowed ^
    --name "TeacherCalendar" ^
    --add-data "index.html;." ^
    --hidden-import "PyQt6.QtWebEngineWidgets" ^
    --hidden-import "PyQt6.QtWebEngineCore" ^
    --hidden-import "PyQt6.QtWebChannel" ^
    --hidden-import "PyQt6.QtNetwork" ^
    desktop_app.py >> "%LOG%" 2>&1

if errorlevel 1 (
    echo.
    echo [안내] exe 빌드에 실패했습니다. Python 스크립트 방식으로 대체합니다.
    goto :SIMPLE_INSTALL
)

set "EXE=%~dp0dist\TeacherCalendar\TeacherCalendar.exe"
if not exist "%EXE%" (
    echo [안내] exe 파일이 생성되지 않았습니다. Python 스크립트 방식으로 대체합니다.
    goto :SIMPLE_INSTALL
)

REM ── exe 빌드 성공 → 시작프로그램 등록 ────────────────────────────────
echo [4/4] 시작프로그램 등록 중...
set "EXEDIR=%~dp0dist\TeacherCalendar"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%STARTUP%\TeacherCalendar.lnk'); $s.TargetPath='%EXE%'; $s.WorkingDirectory='%EXEDIR%'; $s.Description='선생님 캘린더 위젯'; $s.Save()"
echo       등록됨: %STARTUP%\TeacherCalendar.lnk

echo.
echo ============================================================
echo   설치 완료! (exe 방식)
echo   실행 파일: %EXE%
echo   시작프로그램 자동 등록 완료
echo   트레이(우하단 📅) 아이콘으로 설정창 열기
echo ============================================================
echo.
start "" "%EXE%"
pause >nul
endlocal
exit /b 0

REM ── exe 빌드 실패 → Python 스크립트 방식으로 대체 ───────────────────────
:SIMPLE_INSTALL
echo.
echo ============================================================
echo  [대안 설치] Python 스크립트 방식으로 설치합니다.
echo   기능은 exe 방식과 동일합니다.
echo ============================================================
echo.

REM pythonw.exe 경로 찾기
set "PYW_FULL=pythonw"
for /f "tokens=*" %%i in ('where pythonw 2^>nul') do set "PYW_FULL=%%i"
set "SCRIPT=%~dp0desktop_app.py"

REM 시작프로그램에 VBS 런처 등록
(
  echo Set WshShell = CreateObject^("WScript.Shell"^)
  echo WshShell.Run Chr^(34^) ^& "%PYW_FULL%" ^& Chr^(34^) ^& " " ^& Chr^(34^) ^& "%SCRIPT%" ^& Chr^(34^), 0, False
) > "%STARTUP%\TeacherCalendar.vbs"

echo [4/4] 시작프로그램 등록 완료.
echo       등록됨: %STARTUP%\TeacherCalendar.vbs

echo.
echo  위젯을 지금 실행합니다...
start "" "%PYW_FULL%" "%SCRIPT%"

echo.
echo ============================================================
echo   설치 완료! (Python 스크립트 방식)
echo   Windows 시작 시 위젯이 자동 실행됩니다.
echo   빌드 오류 내용: %LOG% 파일 참고
echo ============================================================
echo.
pause >nul
endlocal
exit /b 0
