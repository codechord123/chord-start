@echo off
chcp 65001 >nul 2>nul
title Teacher Calendar Uninstaller
cd /d "%~dp0"

echo ============================================================
echo   Teacher Calendar - Uninstall
echo ============================================================
echo.

echo [1/4] Stopping running widget...
taskkill /f /im TeacherCalendar.exe >nul 2>nul
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*desktop_app.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>nul
echo       done.

echo [2/4] Removing startup entries...
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP%\TeacherCalendar.lnk" del /f /q "%STARTUP%\TeacherCalendar.lnk" >nul 2>nul
if exist "%STARTUP%\TeacherCalendar.vbs" del /f /q "%STARTUP%\TeacherCalendar.vbs" >nul 2>nul
echo       done.

echo [3/4] Removing build output...
if exist "build" rmdir /s /q "build" >nul 2>nul
if exist "dist"  rmdir /s /q "dist"  >nul 2>nul
if exist "TeacherCalendar.spec" del /f /q "TeacherCalendar.spec" >nul 2>nul
if exist "install.log" del /f /q "install.log" >nul 2>nul
echo       done.

echo [4/4] Removing login/settings data (.webdata)...
if exist ".webdata" rmdir /s /q ".webdata" >nul 2>nul
echo       done.

echo.
echo Uninstall complete. Delete this folder to remove everything.
echo.
pause
