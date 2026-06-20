@echo off
chcp 65001 > nul
echo ================================
echo  선생님 캘린더 빌드 시작
echo ================================

echo [1/2] 필수 라이브러리 설치 중...
pip install PyQt6 pyinstaller --quiet

echo [2/2] .exe 파일 생성 중...

REM data.json / config.json 이 없으면 빈 파일 생성
if not exist data.json echo {} > data.json
if not exist config.json echo {} > config.json

pyinstaller --onefile --windowed --name "TeacherCalendar" main.py

echo.
echo ================================
echo  완료! dist\TeacherCalendar.exe 를 실행하세요.
echo  첫 실행 시 방화벽 허용 창이 뜰 수 있습니다.
echo ================================
pause
