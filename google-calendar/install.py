# -*- coding: utf-8 -*-
"""
선생님 캘린더 — 설치 스크립트
install.bat 이 이 파일을 호출합니다. (직접 실행해도 됩니다)

하는 일
  0) Python 버전 확인 — 3.14+ 이면 Python 3.12 자동 설치 후 재실행
  1) 이전 버전 정리 (실행 중인 위젯 종료 + 시작프로그램 해제)
  2) 필요한 패키지 설치 (PyQt6, PyQt6-WebEngine)
  3) 설치 확인
  4) Windows 시작프로그램에 위젯 자동실행 등록 + 즉시 실행
"""
import os
import sys
import subprocess
import traceback
import platform

# Python 3.7+ : 콘솔 한글 출력 보장
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


_log_file = None

def log(msg=""):
    print(msg, flush=True)
    if _log_file:
        try:
            _log_file.write(msg + "\n")
            _log_file.flush()
        except Exception:
            pass


HERE        = os.path.dirname(os.path.abspath(__file__))
SCRIPT      = os.path.join(HERE, "desktop_app.py")
HTML        = os.path.join(HERE, "index.html")
CONFIG_JS   = os.path.join(HERE, "config.js")
CONFIG_EXAM = os.path.join(HERE, "config.js.example")

# ── Python 3.12 자동 설치 지원 ───────────────────────────────────────────────
_PY312_VER     = "3.12.9"
_PY312_URL_64  = f"https://www.python.org/ftp/python/{_PY312_VER}/python-{_PY312_VER}-amd64.exe"
_PY312_URL_32  = f"https://www.python.org/ftp/python/{_PY312_VER}/python-{_PY312_VER}.exe"


def _is_64bit():
    return platform.machine().endswith("64")


def _find_py312():
    """Python 3.12 실행 파일 경로를 반환. 없으면 None.

    1) py.exe 런처 시도 (가장 빠름)
    2) 일반 설치 경로 직접 탐색 — 신규 설치 직후 PATH 갱신 전에도 동작
    """
    # 1. py.exe 런처
    try:
        out = subprocess.check_output(
            ["py", "-3.12", "-c", "import sys; print(sys.executable)"],
            stderr=subprocess.DEVNULL, text=True)
        path = out.strip()
        if path and os.path.exists(path):
            return path
    except Exception:
        pass

    # 2. 경로 직접 탐색
    roots = []
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        roots.append(os.path.join(local_app, "Programs", "Python"))
    for var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        val = os.environ.get(var, "")
        if val:
            roots.append(os.path.join(val, "Python"))
            roots.append(val)

    for root in roots:
        for folder in ("Python312", "Python3.12"):
            exe = os.path.join(root, folder, "python.exe")
            if not os.path.exists(exe):
                continue
            try:
                out = subprocess.check_output(
                    [exe, "-c",
                     "import sys; v=sys.version_info; print(v.major, v.minor)"],
                    stderr=subprocess.DEVNULL, text=True)
                parts = out.strip().split()
                if len(parts) == 2 and int(parts[0]) == 3 and int(parts[1]) == 12:
                    return exe
            except Exception:
                pass

    return None


def _download_python312():
    """Python 3.12 설치 파일을 다운로드하고 설치한다. 성공하면 True 반환."""
    import urllib.request
    import tempfile

    url  = _PY312_URL_64 if _is_64bit() else _PY312_URL_32
    dest = os.path.join(tempfile.gettempdir(), f"python-{_PY312_VER}-installer.exe")

    log(f"  다운로드 중: {url}")
    log("  (약 25 MB — 인터넷 속도에 따라 1 ~ 5 분 소요)")

    try:
        def _progress(count, block, total):
            if total > 0:
                pct  = min(100, count * block * 100 // total)
                done = min(count * block, total) / 1024 / 1024
                tot  = total / 1024 / 1024
                print(f"\r  진행: {pct:3d}%  ({done:.1f} / {tot:.1f} MB)   ",
                      end="", flush=True)
        urllib.request.urlretrieve(url, dest, _progress)
        print()
        log(f"  다운로드 완료.")
    except Exception as e:
        log(f"\n  [오류] 다운로드 실패: {e}")
        return False

    log("  Python 3.12 설치 중... (잠시 설치 창이 나타납니다)")
    log("  설치가 완료될 때까지 기다려 주세요.")
    ret = subprocess.call([
        dest,
        "/passive",           # 최소 UI (자동 진행)
        "InstallAllUsers=0",  # 현재 사용자만 (관리자 권한 불필요)
        "PrependPath=1",      # PATH 자동 등록
        "Include_launcher=1", # py.exe 런처 포함
        "Include_test=0",     # 테스트 제외 (용량 절약)
    ])
    try:
        os.remove(dest)
    except Exception:
        pass
    return ret == 0


def _find_python_uninstall_command(major, minor):
    """레지스트리에서 지정 Python 버전의 제거 커맨드를 반환. 없으면 None."""
    if os.name != "nt":
        return None, None
    try:
        import winreg
    except ImportError:
        return None, None

    roots = [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]
    paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    for root in roots:
        for path in paths:
            try:
                with winreg.OpenKey(root, path) as base:
                    count = winreg.QueryInfoKey(base)[0]
                    for i in range(count):
                        try:
                            sub_name = winreg.EnumKey(base, i)
                            with winreg.OpenKey(base, sub_name) as sub:
                                name = winreg.QueryValueEx(sub, "DisplayName")[0]
                                if f"Python {major}.{minor}" in str(name):
                                    try:
                                        cmd = winreg.QueryValueEx(
                                            sub, "QuietUninstallString")[0]
                                    except Exception:
                                        cmd = winreg.QueryValueEx(
                                            sub, "UninstallString")[0]
                                    return cmd, name
                        except Exception:
                            continue
            except Exception:
                continue
    return None, None


def _uninstall_python(major, minor):
    """지정 Python 버전을 제거한다. 성공 여부 반환."""
    cmd, display = _find_python_uninstall_command(major, minor)
    if not cmd:
        log(f"  [경고] Python {major}.{minor} 제거 프로그램을 찾지 못했습니다.")
        log("         제어판 > 프로그램 제거 에서 직접 제거해 주세요.")
        return False
    log(f"  제거 중: {display}")
    try:
        # QuietUninstallString 이 이미 /quiet 포함 여부 확인 후 실행
        if "/quiet" in cmd.lower() or "/passive" in cmd.lower():
            ret = subprocess.call(cmd, shell=True)
        else:
            ret = subprocess.call(cmd + " /quiet", shell=True)
        return ret == 0
    except Exception as e:
        log(f"  [오류] 제거 실패: {e}")
        return False


def _rerun_with_312(py312_path):
    """Python 3.12 로 이 스크립트를 재실행하고 현재 프로세스를 종료한다."""
    log(f"  Python 3.12 로 재실행합니다: {py312_path}")
    result = subprocess.call([py312_path] + sys.argv)
    sys.exit(result)


def _handle_version_upgrade():
    """Python 3.14+ 감지 시 3.12 설치 후 재실행. 실행 중이면 False 를 반환."""
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 14):
        return False  # 정상 버전 — 계속 진행

    log("=" * 60)
    log(f"  Python {major}.{minor} 감지됨 — 버전 자동 조정 시작")
    log("=" * 60)
    log()
    log("  PyQt6-WebEngine(내장 브라우저)이 Python 3.14 와")
    log("  완전히 호환되지 않아 위젯이 흰 화면으로 멈출 수 있습니다.")
    log("  Python 3.12 가 필요합니다.")
    log()

    # 이미 Python 3.12 가 설치돼 있으면 그걸로 재실행
    py312 = _find_py312()
    if py312:
        log(f"  Python 3.12 발견: {py312}")
        log()
        _rerun_with_312(py312)   # 돌아오지 않음

    # Python 3.12 없음 — 자동 설치
    log("  Python 3.12 가 설치되어 있지 않습니다.")
    log("  지금 자동으로 다운로드 및 설치를 진행합니다.")
    log()

    if not _download_python312():
        log()
        log("  [오류] Python 3.12 자동 설치에 실패했습니다.")
        log()
        log("  수동 설치 방법:")
        log(f"    1. 아래 주소에서 설치 파일을 받으세요:")
        log(f"       https://www.python.org/ftp/python/{_PY312_VER}/"
            f"python-{_PY312_VER}-{'amd64' if _is_64bit() else ''}.exe")
        log("    2. 설치 시 'Add python.exe to PATH' 체크")
        log("    3. 설치 완료 후 install.bat 을 다시 실행")
        input("\n  [Enter] 를 누르면 종료합니다...")
        sys.exit(1)

    log()
    log("  Python 3.12 설치 완료!")
    log()

    # 설치 후 Python 3.12 경로 확인
    py312 = _find_py312()
    if not py312:
        log("  [경고] py -3.12 로 Python 3.12 를 찾지 못했습니다.")
        log("         install.bat 을 다시 실행해 주세요.")
        input("\n  [Enter] 를 누르면 종료합니다...")
        sys.exit(0)

    # 기존 Python 3.14 제거 여부 확인
    log("-" * 60)
    log(f"  기존 Python {major}.{minor} 을(를) 제거하시겠습니까?")
    log("  · '예' — 제거 (깔끔하게 정리, 권장)")
    log("  · '아니오' — 유지 (다른 용도로 사용 중이라면 유지)")
    log()
    answer = input("  Python 3.14 제거? [Y/N]: ").strip().lower()
    if answer in ("y", "ㅛ", "yes"):
        log()
        log(f"  Python {major}.{minor} 제거 중...")
        if _uninstall_python(major, minor):
            log("  제거 완료.")
        log()
    else:
        log("  기존 Python 유지.")
        log()

    log("-" * 60)
    log()
    _rerun_with_312(py312)   # 돌아오지 않음
    return True


# ── 공통 유틸 ───────────────────────────────────────────────────────────────

def pythonw_path():
    """콘솔 없이 실행되는 pythonw.exe 경로 (없으면 일반 python)."""
    d = os.path.dirname(sys.executable)
    for name in ("pythonw.exe", "pythonw"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return sys.executable


def startup_dir():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        log("[경고] APPDATA 환경변수가 없습니다. 시작프로그램 등록을 건너뜁니다.")
        return None
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")


def pip_install(*pkgs):
    return subprocess.call(
        [sys.executable, "-m", "pip", "install", "--upgrade", *pkgs])


def quiet(cmd):
    try:
        return subprocess.call(cmd, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    except Exception:
        return 1


# ── 메인 ────────────────────────────────────────────────────────────────────

def main():
    global _log_file
    log_path = os.path.join(HERE, "install.log")
    try:
        _log_file = open(log_path, "w", encoding="utf-8")
    except Exception:
        _log_file = None

    log("=" * 60)
    log("  선생님 캘린더 — 설치를 시작합니다")
    log("=" * 60)
    log()
    log(f"  Python : {sys.version.split()[0]}")
    log(f"  위치   : {HERE}")
    log()

    # ── 0) Python 버전 확인 및 자동 업그레이드 ──────────────────────────
    _handle_version_upgrade()   # 3.14+ 이면 3.12 설치 후 재실행(돌아오지 않음)

    # 여기까지 왔으면 Python 3.12 이하 → 정상 진행
    log(f"  Python {sys.version.split()[0]} — 버전 정상")
    log()

    # 필수 파일 확인
    for path, name in ((SCRIPT, "desktop_app.py"), (HTML, "index.html")):
        if not os.path.exists(path):
            log(f"[오류] {name} 파일을 찾을 수 없습니다:")
            log(f"       {path}")
            log("       이 폴더 안의 모든 파일을 함께 복사했는지 확인하세요.")
            return 1

    # config.js 확인 (Google/Firebase 인증 정보)
    if not os.path.exists(CONFIG_JS):
        log()
        log("=" * 60)
        log("  [설정 필요] config.js 파일이 없습니다!")
        log()
        log("  구글 캘린더·Firebase 연동을 위해 인증 정보가 필요합니다.")
        log()
        if os.path.exists(CONFIG_EXAM):
            log("  자동으로 config.js.example 을 config.js 로 복사합니다.")
            import shutil
            try:
                shutil.copy2(CONFIG_EXAM, CONFIG_JS)
                log(f"  복사 완료: {CONFIG_JS}")
            except Exception as _e:
                log(f"  [경고] 자동 복사 실패: {_e}")
                log(f"         수동으로 config.js.example 을 config.js 로 복사하세요.")
        else:
            log("  config.js.example 도 없습니다. 설치 파일이 온전한지 확인하세요.")
        log()
        log("  config.js 를 열어 아래 값을 실제 값으로 바꾸세요:")
        log("    CLIENT_ID      — Google OAuth 클라이언트 ID")
        log("    API_KEY        — Google API 키")
        log("    FIREBASE_CONFIG — Firebase 프로젝트 설정")
        log("    CALENDARS      — 표시할 캘린더 ID 목록")
        log()
        log("  설정 후 install.bat 을 다시 실행하거나,")
        log("  값을 입력했다면 지금 바로 계속할 수 있습니다.")
        log("=" * 60)
        log()
        ans = input("  config.js 값 입력 후 계속하려면 Enter, 종료하려면 Q: ").strip().lower()
        if ans in ("q", "quit", "exit"):
            return 0
        if not os.path.exists(CONFIG_JS):
            log("[오류] config.js 가 아직 없습니다. 설정 후 install.bat 을 다시 실행하세요.")
            return 1
        log()

    startup = startup_dir()   # None 이면 APPDATA 없음

    # ── 1) 기존 버전 정리 ───────────────────────────────────────────────
    log("[1/4] 기존 버전 정리 중...")
    quiet(["taskkill", "/f", "/im", "TeacherCalendar.exe"])
    # 현재 사용자의 desktop_app.py 실행 중인 pythonw 프로세스만 종료
    quiet([
        "powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | "
        "Where-Object { $_.CommandLine -like '*desktop_app.py*' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force "
        "-ErrorAction SilentlyContinue }"])
    if startup:
        for name in ("TeacherCalendar.lnk", "TeacherCalendar.vbs"):
            try:
                p = os.path.join(startup, name)
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
    log("      완료.")
    log()

    # ── 2) 패키지 설치 ──────────────────────────────────────────────────
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

    # ── 3) 설치 확인 ────────────────────────────────────────────────────
    log("[3/4] 설치 확인 중...")
    check = quiet([sys.executable, "-c",
                   "from PyQt6.QtWebEngineWidgets import QWebEngineView"])
    if check != 0:
        log("[오류] PyQt6-WebEngine 이 정상적으로 설치되지 않았습니다.")
        log("       아래 명령을 직접 실행한 뒤 다시 시도하세요:")
        log(f"       \"{sys.executable}\" -m pip install "
            "--force-reinstall PyQt6 PyQt6-WebEngine")
        return 1
    try:
        out = subprocess.check_output(
            [sys.executable, "-c",
             "import importlib.metadata as m;"
             "print('PyQt6              ', m.version('PyQt6'));"
             "print('PyQt6-Qt6          ', m.version('PyQt6-Qt6'));"
             "print('PyQt6-WebEngine    ', m.version('PyQt6-WebEngine'));"
             "print('PyQt6-WebEngine-Qt6', m.version('PyQt6-WebEngine-Qt6'))"],
            stderr=subprocess.STDOUT, text=True)
        for line in out.strip().splitlines():
            log("      " + line)
    except Exception:
        pass
    log("      정상.")
    log()

    # ── 4) 시작프로그램 등록 + 즉시 실행 ───────────────────────────────
    log("[4/4] 시작프로그램 등록 중...")
    pyw = pythonw_path()
    if startup:
        try:
            os.makedirs(startup, exist_ok=True)
            vbs = os.path.join(startup, "TeacherCalendar.vbs")
            vbs_body = (
                'Set WshShell = CreateObject("WScript.Shell")\r\n'
                f'WshShell.Run """{pyw}"" ""{SCRIPT}""", 0, False\r\n')
            with open(vbs, "w", encoding="utf-8") as f:
                f.write(vbs_body)
            log(f"      등록됨: {vbs}")
        except Exception as e:
            log(f"[경고] 시작프로그램 등록에 실패했습니다: {e}")
            log("       위젯은 지금 실행되지만, 재부팅 시 자동 실행은 안 될 수 있어요.")
    else:
        log("[경고] APPDATA 없음 — 시작프로그램 등록 건너뜀.")
    log()

    log("위젯을 실행합니다...")
    try:
        flags = 0x00000008 if os.name == "nt" else 0  # DETACHED_PROCESS
        subprocess.Popen([pyw, SCRIPT], cwd=HERE, close_fds=True,
                         creationflags=flags)
    except Exception as e:
        log(f"[경고] 즉시 실행에 실패했습니다: {e}")
        log("       컴퓨터를 다시 켜면 자동으로 실행됩니다.")
    log()

    log("=" * 60)
    log("  설치 완료!")
    log()
    log("  · 잠시 뒤 바탕화면에 캘린더 위젯이 나타납니다.")
    log("  · 작업표시줄 오른쪽 아래 트레이의 📅 아이콘 클릭 → 설정창")
    log("  · 컴퓨터를 켤 때마다 위젯이 자동으로 실행됩니다.")
    if _log_file:
        log(f"  · 설치 로그: {log_path}")
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
    finally:
        if _log_file:
            try:
                _log_file.close()
            except Exception:
                pass
    sys.exit(code)
