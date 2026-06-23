@echo off
title Teacher Calendar Uninstall
echo ============================================
echo  Teacher Calendar (Desktop App) - Uninstall
echo ============================================
echo.

set "VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TeacherCalendar.vbs"
if exist "%VBS%" (
    del "%VBS%"
    echo Removed from startup.
) else (
    echo Not found in startup - nothing to remove.
)
echo.
pause
