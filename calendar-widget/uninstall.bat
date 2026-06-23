@echo off
echo ================================
echo  Teacher Calendar - Uninstall
echo ================================
echo.

set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

if exist "%STARTUP%\TeacherCalendar.vbs" (
    del "%STARTUP%\TeacherCalendar.vbs"
    echo Removed from startup successfully.
) else (
    echo Not found in startup - nothing to remove.
)

echo.
pause
