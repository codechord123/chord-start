@echo off
chcp 65001 >nul
title 선생님 캘린더 - 제거
cd /d "%~dp0"

echo ============================================================
echo   선생님 캘린더 - 완전 제거
echo ============================================================
echo.

echo [1/4] 실행 중인 위젯 종료...
taskkill /f /im TeacherCalendar.exe >nul 2>nul
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*desktop_app.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>nul
echo       완료.

echo [2/4] 시작프로그램 등록 해제...
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP%\TeacherCalendar.lnk" del /f /q "%STARTUP%\TeacherCalendar.lnk" >nul 2>nul
if exist "%STARTUP%\TeacherCalendar.vbs" del /f /q "%STARTUP%\TeacherCalendar.vbs" >nul 2>nul
echo       완료.

echo [3/4] 빌드 결과물 삭제...
if exist "build" rmdir /s /q "build" >nul 2>nul
if exist "dist"  rmdir /s /q "dist"  >nul 2>nul
if exist "TeacherCalendar.spec" del /f /q "TeacherCalendar.spec" >nul 2>nul
echo       완료.

echo [4/4] 로그인/설정 데이터(.webdata) 삭제...
if exist ".webdata" rmdir /s /q ".webdata" >nul 2>nul
echo       완료.

echo.
echo 제거가 끝났습니다. 폴더 전체를 지우면 완전히 삭제됩니다.
echo.
pause
