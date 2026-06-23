@echo off
echo ================================
echo  Teacher Calendar - Build
echo ================================
echo.

echo [1/2] Installing libraries...
pip install PyQt6 pyinstaller

echo.
echo [2/2] Building TeacherCalendar.exe ...

if not exist data.json echo {}> data.json
if not exist config.json echo {}> config.json

pyinstaller --onefile --windowed --name TeacherCalendar main.py

echo.
echo ================================
echo  Done!  Run: dist\TeacherCalendar.exe
echo ================================
pause
