@echo off
title Teacher Calendar - Uninstall
echo ============================================
echo  Teacher Calendar - Uninstall
echo ============================================
echo.

set "VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TeacherCalendar.vbs"
if exist "%VBS%" (
    del "%VBS%"
    echo Removed from Windows startup.
) else (
    echo Not found in startup - nothing to remove.
)
echo.

echo To fully remove, delete the google-calendar folder manually.
echo.
pause
