# -*- coding: utf-8 -*-
"""
선생님 캘린더 — 설치 스크립트
install.bat 이 이 파일을 호출합니다. (직접 실행해도 됩니다)

하는 일
  1) 이전 버전 정리 (실행 중인 위젯 종료 + 시작프로그램 해제)
  2) 필요한 패키지 설치 (PyQt6, PyQt6-WebEngine)
  3) 설치 확인
  4) Windows 시작프로그램에 위젯 자동실행 등록 + 즉시 실행
"""
import os
import sys
import subprocess
import traceback

# Python 3.7+ : 콘솔 한글 출력 보장
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def log(msg=""):
    print(msg, flush=True)


HERE   = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "desktop_app.py")
HTML   = os.path.join(HERE, "index.html")


def pythonw_path():
    """콘솔 없이 실행되는 pythonw.exe 경로 (없으면 일반 python)."""
    d = os.path.dirname(sys.executable)
    for name in ("pythonw.exe", "pythonw"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return sys.executable


def startup_dir():
    return os.path.join(
        os.environ.get("APPDATA", ""),
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup")


def pip_install(*pkgs):
    return subprocess.call(
        [sys.executable, "-m", "pip", "install", "--upgrade", *pkgs])


def quiet(cmd):
    try:
        return subprocess.call(cmd, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    except Exception:
        return 1


def main():
    log("=" * 60)
    log("  선생님 캘린더 — 설치를 시작합니다")
    log("=" * 60)
    log()
    log(f"  Python : {sys.version.split()[0]}")
    log(f"  위치   : {HERE}")
    log()

    # 너무 최신 Python(3.14+)은 PyQt6-WebEngine 이 아직 불안정해서
    # 위젯이 '흰 화면'으로 멈출 수 있다. 미리 강하게 안내한다.
    if sys.version_info[:2] >= (3, 14):
        log("  " + "!" * 56)
        log(f"  [경고] 현재 Python {sys.version_info.major}."
            f"{sys.version_info.minor} 은(는) 너무 최신 버전입니다.")
        log("         내장 브라우저(PyQt6-WebEngine)가 제대로 동작하지")
        log("         않아 위젯이 '흰 화면'으로 멈출 수 있습니다.")
        log("")
        log("         → python.org 에서 Python 3.12 를 설치한 뒤")
        log("           install.bat 을 다시 실행하시길 권장합니다.")
        log("  " + "!" * 56)
        log("")
        log("  (그래도 일단 이대로 설치를 계속 시도합니다...)")
        log()

    # 필수 파일 확인
    for path, name in ((SCRIPT, "desktop_app.py"), (HTML, "index.html")):
        if not os.path.exists(path):
            log(f"[오류] {name} 파일을 찾을 수 없습니다:")
            log(f"       {path}")
            log("       이 폴더 안의 모든 파일을 함께 복사했는지 확인하세요.")
            return 1

    startup = startup_dir()

    # ── 1) 기존 버전 정리 ──────────────────────────────────────────────
    log("[1/4] 기존 버전 정리 중...")
    quiet(["taskkill", "/f", "/im", "TeacherCalendar.exe"])
    quiet([
        "powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | "
        "Where-Object { $_.CommandLine -like '*desktop_app.py*' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force "
        "-ErrorAction SilentlyContinue }"])
    for name in ("TeacherCalendar.lnk", "TeacherCalendar.vbs"):
        try:
            p = os.path.join(startup, name)
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass
    log("      완료.")
    log()

    # ── 2) 패키지 설치 ────────────────────────────────────────────────
    log("[2/4] 필요한 패키지 설치 중...")
    log("      처음에는 수백 MB 를 내려받습니다. 몇 분 걸릴 수 있어요.")
    log("      (인터넷 연결이 필요합니다)")
    log()
    quiet([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    if pip_install("PyQt6", "PyQt6-WebEngine") != 0:
        log()
        log("[오류] 패키지 설치에 실패했습니다.")
        log("       · 인터넷 연결을 확인하세요.")
        log("       · 회사/학교 네트워크라면 방화벽이 막을 수 있습니다.")
        log("       · 잠시 후 install.bat 을 다시 실행해 보세요.")
        return 1
    pip_install("pywin32")   # 선택 기능(벽지 박기). 실패해도 무방.
    log()

    # ── 3) 설치 확인 ──────────────────────────────────────────────────
    log("[3/4] 설치 확인 중...")
    check = quiet([sys.executable, "-c",
                   "from PyQt6.QtWebEngineWidgets import QWebEngineView"])
    if check != 0:
        log("[오류] PyQt6-WebEngine 이 정상적으로 설치되지 않았습니다.")
        log("       아래 명령을 직접 실행한 뒤 다시 시도하세요:")
        log(f"       \"{sys.executable}\" -m pip install "
            "--force-reinstall PyQt6 PyQt6-WebEngine")
        return 1
    # 설치된 버전 출력 (PyQt6 와 WebEngine 버전이 어긋나면 흰 화면 원인이 됨)
    try:
        out = subprocess.check_output(
            [sys.executable, "-c",
             "import importlib.metadata as m;"
             "print('PyQt6', m.version('PyQt6'));"
             "print('PyQt6-Qt6', m.version('PyQt6-Qt6'));"
             "print('PyQt6-WebEngine', m.version('PyQt6-WebEngine'));"
             "print('PyQt6-WebEngine-Qt6', m.version('PyQt6-WebEngine-Qt6'))"],
            stderr=subprocess.STDOUT, text=True)
        for line in out.strip().splitlines():
            log("      " + line)
    except Exception:
        pass
    log("      정상.")
    log()

    # ── 4) 시작프로그램 등록 + 즉시 실행 ──────────────────────────────
    log("[4/4] 시작프로그램 등록 중...")
    pyw = pythonw_path()
    try:
        os.makedirs(startup, exist_ok=True)
        vbs = os.path.join(startup, "TeacherCalendar.vbs")
        # pythonw 로 콘솔 없이 조용히 위젯 실행하는 VBS 런처
        vbs_body = (
            'Set WshShell = CreateObject("WScript.Shell")\r\n'
            f'WshShell.Run """{pyw}"" ""{SCRIPT}""", 0, False\r\n')
        with open(vbs, "w", encoding="utf-8") as f:
            f.write(vbs_body)
        log(f"      등록됨: {vbs}")
    except Exception as e:
        log(f"[경고] 시작프로그램 등록에 실패했습니다: {e}")
        log("       위젯은 지금 실행되지만, 재부팅 시 자동 실행은 안 될 수 있어요.")
    log()

    # 위젯 즉시 실행 (콘솔 없는 pythonw, 독립 프로세스)
    log("위젯을 실행합니다...")
    try:
        flags = 0
        if os.name == "nt":
            flags = 0x00000008  # DETACHED_PROCESS
        subprocess.Popen([pyw, SCRIPT], cwd=HERE, close_fds=True,
                         creationflags=flags)
    except Exception as e:
        log(f"[경고] 즉시 실행에 실패했습니다: {e}")
        log("       컴퓨터를 다시 켜면 자동으로 실행됩니다.")
    log()

    log("=" * 60)
    log("  ✅ 설치 완료!")
    log()
    log("  · 잠시 뒤 바탕화면에 캘린더 위젯이 나타납니다.")
    log("  · 작업표시줄 오른쪽 아래 트레이의 📅 아이콘을 클릭 → 설정창")
    log("  · 컴퓨터를 켤 때마다 위젯이 자동으로 실행됩니다.")
    log("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        log()
        log("[예기치 못한 오류] 아래 내용을 그대로 캡처해서 전달해 주세요:")
        log("-" * 60)
        log(traceback.format_exc())
        log("-" * 60)
        code = 1
    sys.exit(code)
