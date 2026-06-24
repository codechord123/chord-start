"""
선생님 캘린더 — 데스크탑 위젯
─────────────────────────────────────────────────────────────────────
실행:   pythonw desktop_app.py
필요:   pip install PyQt6 PyQt6-WebEngine
선택:   pip install pywin32   (WorkerW 벽지 박기 기능)

구조
  ┌──────────────────────────────────────────────────────┐
  │ CalendarWidget   (위젯 본체, 바탕화면에 투명으로 표시) │
  │  - 버튼 전혀 없음, 상단 드래그 핸들만 존재             │
  │  - 트레이 아이콘(📅)만 작업표시줄에 표시               │
  ├──────────────────────────────────────────────────────┤
  │ SettingsWindow   (설정 프로그램 창, 별도 창)           │
  │  - 트레이 아이콘 클릭 → 설정창 열림                    │
  │  - 투명도·크기·위치·항상위·새로고침·종료 제어            │
  └──────────────────────────────────────────────────────┘
"""
import os, sys, json, socket, threading, functools, webbrowser, http.server
from urllib.parse import urlparse, parse_qs, unquote

# ── 흰 화면(white screen) 방지 ────────────────────────────────────────────
# QtWebEngine 은 일부 Windows GPU/드라이버에서 화면을 못 그리고 하얗게 멈춘다.
# QApplication / QtWebEngine 을 만들기 "전에" 아래 플래그로 소프트웨어 렌더링을
# 강제하면 어떤 PC 에서도 안정적으로 그려진다. (캘린더는 GPU 가속이 필요 없음)
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--disable-gpu --disable-gpu-compositing --no-sandbox")
os.environ.setdefault("QT_OPENGL", "software")

try:
    from PyQt6.QtCore import Qt, QUrl, QSettings, QTimer, QPoint
    from PyQt6.QtGui  import QIcon, QPixmap, QPainter, QColor, QFont, QAction
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QSizeGrip, QSystemTrayIcon, QMenu, QCheckBox,
        QFrame, QSlider, QSpacerItem, QSizePolicy
    )
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore    import QWebEngineProfile, QWebEnginePage
except ImportError as _e:
    try:
        import tkinter as _tk, tkinter.messagebox as _mb
        _tk.Tk().withdraw()
        _mb.showerror("패키지 없음",
            f"필수 패키지가 설치되지 않았습니다:\n{_e}\n\n"
            "install.bat 을 다시 실행해 주세요.")
    except Exception:
        pass
    sys.exit(1)

# PyInstaller 로 .exe 빌드되면(frozen) 경로가 달라진다.
#   BUNDLE_DIR : index.html 등 읽기용 자원이 들어 있는 곳
#   DATA_DIR   : .webdata(로그인·설정) 를 저장할 쓰기 가능한 곳
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    DATA_DIR   = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR   = BUNDLE_DIR

APP_DIR   = BUNDLE_DIR          # 정적 파일 서빙 기준 폴더
HTML_FILE = 'index.html'

# ── 진단 로그 (흰 화면/멈춤 원인 추적용) ──────────────────────────────────
# 위젯이 무엇을 했는지 widget.log 에 남긴다. 문제가 생기면 이 파일을 보면 된다.
_LOG_PATH = os.path.join(DATA_DIR, "widget.log")


def wlog(msg: str):
    try:
        import time
        line = time.strftime("%H:%M:%S") + "  " + str(msg)
    except Exception:
        line = str(msg)
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    try:
        print(line, flush=True)
    except Exception:
        pass

# ── Windows WorkerW (벽지 레이어 임베딩) ──────────────────────────────────
try:
    import ctypes
    from ctypes import wintypes
    _user32  = ctypes.windll.user32
    HAS_WIN32 = True
except Exception:
    HAS_WIN32 = False


def _find_workerw():
    if not HAS_WIN32:
        return None
    progman = _user32.FindWindowW("Progman", None)
    if not progman:
        return None
    _user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0x0000, 1000, None)
    workerw = ctypes.c_void_p(0)

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lp):
        shell = _user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
        if shell:
            nxt = _user32.FindWindowExW(None, hwnd, "WorkerW", None)
            if nxt:
                workerw.value = nxt
        return True

    _user32.EnumWindows(_enum, 0)
    return workerw.value


# ── 로컬 HTTP 서버 (정적 파일 + OAuth 중계) ──────────────────────────────
def _find_free_port():
    for p in [8765, 8766, 8767, 8768, 8770, 8800]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', p)) != 0:
                return p
    return 8765


_oauth_token: dict | None = None   # 외부 브라우저에서 받은 토큰 임시 보관

# 구글 OAuth implicit flow 콜백 — URL hash 에서 토큰 파싱 후 서버로 POST
_CALLBACK_HTML = """<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<title>로그인 완료</title>
<style>
 body{font-family:'Malgun Gothic',sans-serif;background:#0f172a;color:#e2e8f0;
      display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
 .card{text-align:center;padding:40px 52px;background:#1e293b;
       border-radius:18px;box-shadow:0 20px 60px rgba(0,0,0,.5)}
 h1{font-size:20px;margin:0 0 8px} p{color:#94a3b8;margin:0;font-size:14px}
 .ok{color:#34d399} .err{color:#f87171}
</style></head><body>
<div class='card'><h1 id='m'>로그인 처리 중…</h1><p id='s'>잠시만 기다려 주세요.</p></div>
<script>
(function(){
  var p=new URLSearchParams(location.hash.slice(1));
  var tok=p.get('access_token');
  var m=$('m'),s=$('s');
  function $(_id){return document.getElementById(_id);}
  if(!tok){m.innerHTML='<span class=err>⚠ 로그인 실패</span>';
           s.textContent='위젯에서 다시 시도해 주세요.';return;}
  fetch('/oauth2token',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({access_token:tok,expires_in:p.get('expires_in')})})
  .then(function(){
    m.innerHTML='<span class=ok>✅ 로그인 완료!</span>';
    s.textContent='이 창을 닫고 바탕화면 위젯으로 돌아가세요.';
    setTimeout(function(){try{window.close();}catch(e){}},2000);
  }).catch(function(){m.innerHTML='<span class=err>연결 오류</span>';
    s.textContent='위젯이 실행 중인지 확인하세요.';});
})();
</script></body></html>"""


class _AppHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        global _oauth_token
        p = urlparse(self.path)
        if p.path == '/oauth2callback':
            self._html(_CALLBACK_HTML)
            return
        if p.path == '/oauth2open':
            url = unquote(parse_qs(p.query).get('u', [''])[0])
            if url.startswith('https://accounts.google.com/'):
                try:
                    webbrowser.open(url)
                except Exception:
                    pass
            self._json({'ok': True})
            return
        if p.path == '/oauth2token':
            tok = _oauth_token
            _oauth_token = None
            self._json(tok or {})
            return
        super().do_GET()

    def do_POST(self):
        global _oauth_token
        if urlparse(self.path).path == '/oauth2token':
            n = int(self.headers.get('Content-Length', 0) or 0)
            raw = self.rfile.read(n) if n else b'{}'
            try:
                _oauth_token = json.loads(raw.decode())
            except Exception:
                _oauth_token = None
            self._json({'ok': True})
            return
        self.send_error(404)

    def _html(self, s):
        d = s.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(d)))
        self.end_headers()
        self.wfile.write(d)

    def _json(self, obj):
        d = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(d)))
        self.end_headers()
        self.wfile.write(d)


def _start_server(port):
    h = functools.partial(_AppHandler, directory=APP_DIR)
    s = http.server.ThreadingHTTPServer(('127.0.0.1', port), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


# 로드 실패 시 흰 화면 대신 보여줄 어두운 진단 페이지
_ERROR_HTML = """<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<style>
 html,body{height:100%;margin:0;background:#0f172a;color:#e2e8f0;
   font-family:'Malgun Gothic',sans-serif;
   display:flex;align-items:center;justify-content:center}
 .b{max-width:420px;text-align:center;padding:32px}
 h1{font-size:20px;margin:0 0 12px;color:#f87171}
 p{font-size:14px;line-height:1.7;color:#94a3b8;margin:6px 0}
 code{background:#1e293b;padding:2px 7px;border-radius:6px;color:#93c5fd}
</style></head><body><div class='b'>
 <h1>화면을 불러오지 못했습니다</h1>
 <p>잠시 후 자동으로 다시 시도합니다.<br>계속 이 화면이면 아래를 확인하세요.</p>
 <p>· 주소: <code>__URL__</code></p>
 <p>· 백신/방화벽이 로컬 연결을 막고 있지 않은지<br>· 폴더 안에 <code>index.html</code> 이 있는지</p>
 <p style='margin-top:16px;color:#64748b;font-size:12px'>
   트레이(📅) → 설정 → 새로고침 으로 다시 시도할 수 있습니다.</p>
</div></body></html>"""

# 내장 엔진(QtWebEngine)이 아예 켜지지 않을 때(주로 Python 버전 문제) 안내
_ENGINE_HTML = """<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<style>
 html,body{height:100%;margin:0;background:#0f172a;color:#e2e8f0;
   font-family:'Malgun Gothic',sans-serif;
   display:flex;align-items:center;justify-content:center}
 .b{max-width:460px;text-align:left;padding:32px}
 h1{font-size:19px;margin:0 0 14px;color:#fbbf24;text-align:center}
 p{font-size:14px;line-height:1.75;color:#cbd5e1;margin:8px 0}
 ol{font-size:14px;line-height:1.9;color:#cbd5e1;padding-left:20px}
 code{background:#1e293b;padding:2px 7px;border-radius:6px;color:#93c5fd}
 b{color:#fff}
</style></head><body><div class='b'>
 <h1>내장 브라우저 엔진이 켜지지 않았습니다</h1>
 <p>화면(캘린더)을 그리는 엔진이 시작되지 않았습니다.<br>
    대부분 <b>Python 버전이 너무 최신</b>일 때 생깁니다.</p>
 <p><b>해결 방법 (권장):</b></p>
 <ol>
   <li>현재 Python(3.14 등)을 제거</li>
   <li><code>python.org</code> 에서 <b>Python 3.12</b> 설치<br>
       (설치 시 "Add python.exe to PATH" 체크)</li>
   <li><code>install.bat</code> 다시 실행</li>
 </ol>
 <p style='margin-top:14px;color:#64748b;font-size:12px'>
   같은 폴더의 <code>widget.log</code> 를 보내주시면 더 정확히 도와드립니다.</p>
</div></body></html>"""


# ── 드래그 핸들 (위젯 상단, 투명 — 버튼 전혀 없음) ─────────────────────────
class _DragHandle(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self._win  = win
        self._drag = None
        self.setFixedHeight(20)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._dot = QLabel("· · ·")
        self._dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._dot)
        self._style(False)

    def _style(self, hov):
        if hov:
            self.setStyleSheet(
                "background:rgba(255,255,255,0.08);"
                "border-radius:20px 20px 0 0;")
            self._dot.setStyleSheet("color:rgba(255,255,255,.45);font-size:13px;letter-spacing:5px;")
        else:
            self.setStyleSheet("background:transparent;")
            self._dot.setStyleSheet("color:rgba(255,255,255,0);font-size:13px;")

    def enterEvent(self, _): self._style(True)
    def leaveEvent(self, _): self._style(False)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self._win.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag and (e.buttons() & Qt.MouseButton.LeftButton):
            self._win.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _):
        self._drag = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._win.save_geo()


# ── 위젯 본체 ───────────────────────────────────────────────────────────────
class CalendarWidget(QWidget):
    def __init__(self, url: str):
        super().__init__()
        self._url      = url
        self._cfg      = QSettings("TeacherCalendar", "widget")
        self._pinned   = False
        self._embedded = False

        self.setWindowTitle("선생님 캘린더")
        self._apply_flags()
        # 주의: WA_TranslucentBackground 는 일부 GPU/드라이버에서 '흰 화면'으로
        # 잘못 렌더링되므로 쓰지 않는다. 대신 불투명한 어두운 배경으로 칠하고,
        # 반투명이 필요하면 setWindowOpacity(창 전체 알파)로 처리한다.

        # 영구 WebEngine 프로파일
        profile = QWebEngineProfile("teacher_cal", self)
        store   = os.path.join(DATA_DIR, ".webdata")
        os.makedirs(store, exist_ok=True)
        profile.setPersistentStoragePath(store)
        profile.setCachePath(os.path.join(store, "cache"))
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        # Chrome UA — 임베디드 웹뷰 차단 우회
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

        page = _CalPage(profile, None)
        page.setBackgroundColor(QColor("#0f172a"))   # 로딩 중에도 어두운 배경
        # 렌더 프로세스가 죽으면(흰 화면의 주요 원인) 기록 후 다시 로드
        try:
            page.renderProcessTerminated.connect(self._on_render_dead)
        except Exception:
            pass

        self._view = QWebEngineView()
        self._view.setPage(page)
        self._view.setStyleSheet("background:#0f172a;")
        # 로드 실패(흰 화면) 시 한 번 자동 재시도
        self._reloaded_once = False
        self._loaded = False
        self._view.loadStarted.connect(lambda: wlog("loadStarted " + self._url))
        self._view.loadFinished.connect(self._on_load_finished)
        wlog("위젯 생성, URL = " + url)
        self._view.setUrl(QUrl(url))
        wlog("setUrl 호출 완료 — 엔진 응답 대기")
        # 감시 타이머: 8초 안에 로드가 시작/완료되지 않으면 엔진 이상으로 간주
        QTimer.singleShot(8000, self._watchdog)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._view)

        # 오버레이: 드래그 핸들(상단) + 크기 그립(우하단)
        self._handle = _DragHandle(self)
        self._grip   = QSizeGrip(self)
        self._grip.setStyleSheet("background:transparent;")

        # 저장된 크기/위치 복원, 없으면 화면 가운데
        geo = self._cfg.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(920, 660)
            self._center()

        # 저장된 불투명도 복원
        op = float(self._cfg.value("opacity", 1.0))
        self.setWindowOpacity(op)

    # ── 창 플래그 ─────────────────────────────────────────────────────
    def _apply_flags(self):
        f = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        f |= (Qt.WindowType.WindowStaysOnTopHint if self._pinned
              else Qt.WindowType.WindowStaysOnBottomHint)
        self.setWindowFlags(f)

    # ── 오버레이 위치 갱신 ────────────────────────────────────────────
    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_handle"):
            self._handle.setGeometry(0, 0, self.width(), 20)
            self._handle.raise_()
        if hasattr(self, "_grip"):
            g = 16
            self._grip.setGeometry(self.width() - g, self.height() - g, g, g)
            self._grip.raise_()
        self.save_geo()

    # ── 설정창이 호출하는 공개 API ────────────────────────────────────
    def set_opacity(self, pct: int):
        """pct: 20 ~ 100"""
        val = max(0.20, min(1.0, pct / 100))
        self.setWindowOpacity(val)
        self._cfg.setValue("opacity", val)

    def get_opacity_pct(self) -> int:
        return round(self.windowOpacity() * 100)

    def set_on_top(self, on: bool):
        if self._embedded:
            self._detach()
        self._pinned = bool(on)
        self._apply_flags()
        self.show()
        self.raise_() if self._pinned else self.lower()

    def is_on_top(self) -> bool:
        return self._pinned

    def apply_size(self, w: int, h: int):
        self.resize(w, h)
        self._center()

    def move_to(self, pos: str):
        """pos: 'center' | 'topright' | 'topleft' | 'bottomright' | 'bottomleft'"""
        sc = QApplication.primaryScreen().availableGeometry()
        m  = 20
        w, h = self.width(), self.height()
        targets = {
            'center':      ((sc.width() - w) // 2,      (sc.height() - h) // 2),
            'topright':    (sc.right() - w - m,          sc.top() + m),
            'topleft':     (sc.left() + m,               sc.top() + m),
            'bottomright': (sc.right() - w - m,          sc.bottom() - h - m),
            'bottomleft':  (sc.left() + m,               sc.bottom() - h - m),
        }
        x, y = targets.get(pos, targets['center'])
        self.move(x, y)
        self.save_geo()

    def toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_() if self._pinned else self.lower()

    def reload(self):
        self._reloaded_once = False
        self._view.setUrl(QUrl(self._url))

    def _watchdog(self):
        # 8초가 지나도 한 번도 로드되지 않음 = 내장 엔진(QtWebEngine)이 안 켜짐.
        # 대개 Python 버전이 너무 최신이거나 PyQt6-WebEngine 설치 문제.
        if not self._loaded:
            wlog("[경고] 8초간 로드 없음 — QtWebEngine 미동작 의심 "
                 "(Python 버전/WebEngine 설치 확인 필요)")
            try:
                self._view.setHtml(_ENGINE_HTML)
            except Exception:
                pass

    def _on_load_finished(self, ok: bool):
        wlog("loadFinished ok=%s" % ok)
        if ok:
            self._loaded = True
            return
        # 로드 실패(흰 화면/연결 실패) → 1초 뒤 한 번만 자동 재시도
        if not self._reloaded_once:
            self._reloaded_once = True
            QTimer.singleShot(1000, lambda: self._view.setUrl(QUrl(self._url)))
        else:
            # 재시도도 실패 → 흰 화면 대신 어두운 진단 화면을 띄운다
            wlog("재시도 실패 → 진단 화면 표시")
            self._view.setHtml(_ERROR_HTML.replace("__URL__", self._url))

    def _on_render_dead(self, status, code):
        # 렌더 프로세스 비정상 종료 = 대표적 '흰 화면' 원인. 기록 후 1회 재로드.
        wlog("renderProcessTerminated status=%s code=%s" % (status, code))
        if not self._reloaded_once:
            self._reloaded_once = True
            QTimer.singleShot(800, lambda: self._view.setUrl(QUrl(self._url)))

    def save_geo(self):
        self._cfg.setValue("geometry", self.saveGeometry())

    def _center(self):
        sc = QApplication.primaryScreen().availableGeometry()
        self.move((sc.width() - self.width()) // 2,
                  (sc.height() - self.height()) // 2)
        self.save_geo()

    # ── WorkerW 임베딩 (선택) ─────────────────────────────────────────
    def embed(self) -> bool:
        if not HAS_WIN32:
            return False
        w = _find_workerw()
        if not w:
            return False
        try:
            geo  = self.frameGeometry()
            hwnd = int(self.winId())
            _user32.SetParent(hwnd, w)
            pt   = wintypes.POINT(geo.x(), geo.y())
            _user32.ScreenToClient(w, ctypes.byref(pt))
            _user32.MoveWindow(hwnd, pt.x, pt.y, geo.width(), geo.height(), True)
            self._embedded = True
            return True
        except Exception:
            return False

    def _detach(self):
        if not (HAS_WIN32 and self._embedded):
            return
        try:
            _user32.SetParent(int(self.winId()), None)
        except Exception:
            pass
        self._embedded = False
        self._apply_flags()
        self.show()
        self.raise_()

    def toggle_embed(self):
        if self._embedded:
            self._detach()
        else:
            if not self.embed():
                self._apply_flags()
                self.show()
                self.lower()

    def closeEvent(self, e):
        self.save_geo()
        super().closeEvent(e)


# ── WebEngine 팝업 처리 ───────────────────────────────────────────────────
class _CalPage(QWebEnginePage):
    _popups: list = []

    def createWindow(self, _type):
        v = QWebEngineView()
        v.setWindowTitle("Google 로그인")
        v.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        v.resize(480, 640)
        v.show()
        _CalPage._popups.append(v)
        pg = _CalPage(self.profile(), v)
        v.setPage(pg)
        v.destroyed.connect(lambda: _CalPage._popups.remove(v)
                            if v in _CalPage._popups else None)
        return pg


# ── 설정 창 ──────────────────────────────────────────────────────────────
class SettingsWindow(QWidget):

    _STYLE = """
    QWidget          { background:#111827; color:#f1f5f9;
                       font-family:'Malgun Gothic','Noto Sans KR',sans-serif; }
    QWidget#card     { background:#1e293b; border-radius:12px; }
    QLabel#hd        { font-size:18px; font-weight:700; color:#ffffff; }
    QLabel#sub       { font-size:12px; color:#64748b; }
    QLabel#sec       { font-size:11px; font-weight:700; color:#38bdf8;
                       text-transform:uppercase; letter-spacing:1px; }
    QLabel#val       { font-size:12px; color:#94a3b8; min-width:36px;
                       qproperty-alignment:AlignRight; }
    QPushButton      { background:#1e293b; border:1px solid #334155;
                       border-radius:8px; padding:8px 10px;
                       color:#e2e8f0; font-size:13px; }
    QPushButton:hover{ background:#273449; border-color:#3b82f6; color:#fff; }
    QPushButton#pri  { background:#2563eb; border:none;
                       color:#fff; font-weight:700; }
    QPushButton#pri:hover { background:#1d4ed8; }
    QPushButton#pos  { padding:7px 6px; font-size:12px; }
    QPushButton#del  { background:#1f1015; border:1px solid #7f1d1f;
                       color:#fca5a5; }
    QPushButton#del:hover { background:#2d1217; }
    QCheckBox        { font-size:13px; spacing:8px; }
    QCheckBox::indicator            { width:18px; height:18px; border-radius:5px;
                                      border:2px solid #475569; background:#0f172a; }
    QCheckBox::indicator:checked    { background:#2563eb; border-color:#2563eb; }
    QSlider::groove:horizontal      { height:4px; background:#334155;
                                      border-radius:2px; }
    QSlider::handle:horizontal      { width:16px; height:16px; margin:-6px 0;
                                      background:#3b82f6; border-radius:8px; }
    QSlider::sub-page:horizontal    { background:#3b82f6; border-radius:2px; }
    QFrame#ln { background:#1e293b; max-height:1px; }
    """

    SIZES = [("소", 720, 520), ("중", 920, 660), ("대", 1120, 800), ("전체", 0, 0)]

    def __init__(self, widget: CalendarWidget, app: QApplication):
        super().__init__()
        self._w   = widget
        self._app = app
        self.setWindowTitle("선생님 캘린더 — 설정")
        self.setWindowFlag(Qt.WindowType.Window)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(360)
        self.setStyleSheet(self._STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ── 헤더 ──────────────────────────────────────────────────────
        hd = QLabel("📅  선생님 캘린더")
        hd.setObjectName("hd")
        root.addWidget(hd)
        sb = QLabel("트레이(📅)를 닫아도 위젯은 계속 실행됩니다.")
        sb.setObjectName("sub")
        root.addWidget(sb)
        root.addWidget(self._line())

        # ── 위젯 표시 ─────────────────────────────────────────────────
        root.addWidget(self._sec("위젯 표시"))
        self._btn_vis = self._btn("👁  위젯 보이기 / 숨기기",
                                  self._w.toggle_visible, pri=True)
        root.addWidget(self._btn_vis)

        # ── 투명도 ────────────────────────────────────────────────────
        root.addWidget(self._sec("투명도"))
        op_row = QHBoxLayout()
        op_row.setSpacing(8)
        self._sld_op = QSlider(Qt.Orientation.Horizontal)
        self._sld_op.setRange(20, 100)
        self._sld_op.setValue(self._w.get_opacity_pct())
        self._sld_op.setTickInterval(10)
        self._lbl_op = QLabel(f"{self._sld_op.value()}%")
        self._lbl_op.setObjectName("val")
        op_row.addWidget(self._sld_op)
        op_row.addWidget(self._lbl_op)
        root.addLayout(op_row)
        self._sld_op.valueChanged.connect(self._on_opacity)

        # ── 크기 ──────────────────────────────────────────────────────
        root.addWidget(self._sec("크기"))
        sz_row = QHBoxLayout()
        sz_row.setSpacing(6)
        for name, w, h in self.SIZES:
            b = QPushButton(name)
            b.setObjectName("pos")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if w == 0:   # 전체화면
                sc = QApplication.primaryScreen().availableGeometry()
                _w, _h = sc.width(), sc.height()
                b.clicked.connect(lambda _, w=_w, h=_h: self._w.apply_size(w, h))
            else:
                b.clicked.connect(lambda _, w=w, h=h: self._w.apply_size(w, h))
            sz_row.addWidget(b)
        root.addLayout(sz_row)

        # ── 위치 ──────────────────────────────────────────────────────
        root.addWidget(self._sec("위치"))
        pos_grid = [
            [("↖ 왼위", "topleft"),    ("⬆ 가운데", "center"),    ("↗ 오른위", "topright")],
            [("↙ 왼아래", "bottomleft"), None,                   ("↘ 오른아래", "bottomright")],
        ]
        for row in pos_grid:
            r = QHBoxLayout()
            r.setSpacing(6)
            for item in row:
                if item is None:
                    r.addStretch()
                else:
                    label, key = item
                    b = QPushButton(label)
                    b.setObjectName("pos")
                    b.setCursor(Qt.CursorShape.PointingHandCursor)
                    b.clicked.connect(lambda _, k=key: self._w.move_to(k))
                    r.addWidget(b)
            root.addLayout(r)

        # ── 옵션 ──────────────────────────────────────────────────────
        root.addWidget(self._sec("옵션"))
        self._chk_top = QCheckBox("항상 맨 위에 표시")
        self._chk_top.setChecked(self._w.is_on_top())
        self._chk_top.toggled.connect(self._w.set_on_top)
        root.addWidget(self._chk_top)

        if HAS_WIN32:
            self._chk_embed = QCheckBox("벽지에 완전히 박기  (보기 전용 · 클릭 불가)")
            self._chk_embed.toggled.connect(self._on_embed)
            root.addWidget(self._chk_embed)

        root.addWidget(self._btn("↻  위젯 새로고침", self._w.reload))

        # ── 하단 ──────────────────────────────────────────────────────
        root.addStretch()
        root.addWidget(self._line())
        root.addWidget(self._btn("⏻  완전히 종료", self._app.quit, danger=True))

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────
    def _btn(self, text, slot, pri=False, danger=False):
        b = QPushButton(text)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        if pri:
            b.setObjectName("pri")
        elif danger:
            b.setObjectName("del")
        b.clicked.connect(slot)
        return b

    def _sec(self, text):
        l = QLabel(text)
        l.setObjectName("sec")
        return l

    def _line(self):
        f = QFrame()
        f.setObjectName("ln")
        f.setFrameShape(QFrame.Shape.HLine)
        return f

    def _on_opacity(self, v):
        self._lbl_op.setText(f"{v}%")
        self._w.set_opacity(v)

    def _on_embed(self, on):
        if on and not self._w._embedded:
            self._w.toggle_embed()
        elif not on and self._w._embedded:
            self._w._detach()

    def open(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, e):
        e.ignore()
        self.hide()


# ── 트레이 아이콘 ────────────────────────────────────────────────────────
def _make_icon() -> QIcon:
    px = QPixmap(64, 64)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#2563eb"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(4, 4, 56, 56, 14, 14)
    p.setPen(QColor("white"))
    p.setFont(QFont("Segoe UI Emoji", 26))
    p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "📅")
    p.end()
    return QIcon(px)


# ── 메인 ──────────────────────────────────────────────────────────────────
def main():
    wlog("=" * 50)
    wlog("위젯 시작  python=%s" % sys.version.split()[0])
    wlog("APP_DIR=%s" % APP_DIR)
    wlog("CHROMIUM_FLAGS=%s" % os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS"))

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("선생님 캘린더")

    html_path = os.path.join(APP_DIR, HTML_FILE)
    if not os.path.exists(html_path):
        wlog("[치명] index.html 없음: %s" % html_path)
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "오류",
            f"{HTML_FILE} 파일을 찾을 수 없습니다.\n{html_path}")
        sys.exit(1)

    port = _find_free_port()
    try:
        _start_server(port)
        wlog("로컬 서버 시작 OK  port=%d" % port)
    except Exception as e:
        wlog("[치명] 서버 시작 실패: %r" % e)
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "오류",
            f"로컬 서버를 시작하지 못했습니다.\n{e}")
        sys.exit(1)
    url = f"http://localhost:{port}/{HTML_FILE}"

    widget   = CalendarWidget(url)
    settings = SettingsWindow(widget, app)

    widget.show()
    QTimer.singleShot(400, widget.lower)

    tray = QSystemTrayIcon(_make_icon(), app)
    tray.setToolTip("선생님 캘린더  —  클릭하면 설정 창이 열립니다")

    def _first_run():
        if not widget._cfg.value("hint_shown"):
            tray.showMessage(
                "선생님 캘린더 위젯",
                "바탕화면에 위젯이 실행됐습니다.\n"
                "트레이(📅) 아이콘 클릭 → 설정창 열기",
                QSystemTrayIcon.MessageIcon.Information, 5000)
            widget._cfg.setValue("hint_shown", True)
    QTimer.singleShot(800, _first_run)

    menu = QMenu()
    menu.setStyleSheet(
        "QMenu{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:4px;color:#e2e8f0;}"
        "QMenu::item{padding:8px 20px;border-radius:6px;font-size:13px;}"
        "QMenu::item:selected{background:#2563eb;color:white;}"
        "QMenu::separator{height:1px;background:#334155;margin:4px 8px;}"
    )
    a_cfg  = QAction("⚙  설정 열기", app)
    a_show = QAction("👁  위젯 표시 / 숨기기", app)
    a_quit = QAction("⏻  종료", app)
    a_cfg.triggered.connect(settings.open)
    a_show.triggered.connect(widget.toggle_visible)
    a_quit.triggered.connect(app.quit)
    menu.addAction(a_cfg)
    menu.addAction(a_show)
    menu.addSeparator()
    menu.addAction(a_quit)
    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda r: settings.open()
        if r == QSystemTrayIcon.ActivationReason.Trigger else None)
    tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        tb = traceback.format_exc()
        wlog("[치명적 예외]\n" + tb)
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance() is None:
                QApplication(sys.argv)
            QMessageBox.critical(
                None, "선생님 캘린더 — 오류",
                "위젯 실행 중 오류가 발생했습니다.\n\n"
                + tb + "\n\n이 내용과 widget.log 파일을 보내주세요.")
        except Exception:
            pass
        sys.exit(1)
