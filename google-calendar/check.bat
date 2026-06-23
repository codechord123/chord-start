@echo off
title Teacher Calendar - 진단
echo ============================================
echo  환경 진단 결과
echo ============================================
echo.

echo [1] Python 설치 여부 확인...
where py >nul 2>nul
if not errorlevel 1 (
    echo   [OK] py 명령 발견
    py --version
    goto :check_pkg
)
where python >nul 2>nul
if not errorlevel 1 (
    echo   [OK] python 명령 발견
    python --version
    goto :check_pkg
)
echo   [FAIL] Python이 설치되어 있지 않습니다.
echo.
echo   해결: https://www.python.org/downloads/
echo         설치 시 반드시 "Add python.exe to PATH" 체크!
echo.
pause
exit /b

:check_pkg
echo.
echo [2] PyQt6 설치 여부 확인...
python -c "import PyQt6; print('  [OK] PyQt6 버전:', PyQt6.QtCore.PYQT_VERSION_STR)" 2>nul || (
    echo   [FAIL] PyQt6 미설치
    set PKG_MISSING=1
)
python -c "import PyQt6.QtWebEngineWidgets; print('  [OK] PyQt6-WebEngine OK')" 2>nul || (
    echo   [FAIL] PyQt6-WebEngine 미설치
    set PKG_MISSING=1
)

echo.
echo [3] pythonw 확인...
where pythonw >nul 2>nul && echo   [OK] pythonw 있음 || echo   [WARN] pythonw 없음 (python 으로 대체 실행)

echo.
echo ============================================

if defined PKG_MISSING (
    echo  패키지 재설치가 필요합니다.
    echo  아래 명령을 CMD 에서 실행하세요:
    echo.
    echo    pip install PyQt6 PyQt6-WebEngine
    echo.
) else (
    echo  환경 OK - 앱을 직접 실행합니다...
    echo.
    start "" python "%~dp0desktop_app.py"
    echo  위젯이 바탕화면에 떠야 합니다.
    echo  안 보이면 작업표시줄 오른쪽 트레이(숨겨진 아이콘) 확인
)

echo.
pause
