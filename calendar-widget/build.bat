@echo off
chcp 65001 > nul
echo ================================
echo  선생님 캘린더 빌드 시작
echo ================================

echo [1/2] 필수 라이브러리 설치 중...
pip install PyQt6 pyinstaller --quiet

echo [2/2] .exe 파일 생성 중...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "선생님캘린더" ^
  --add-data "data.json;." ^
  --add-data "config.json;." ^
  main.py

echo.
echo ================================
echo  완료! dist\선생님캘린더.exe 를 실행하세요.
echo ================================
pause
