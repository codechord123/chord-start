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

APP_DIR   = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = 'index.html'

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
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 영구 WebEngine 프로파일
        profile = QWebEngineProfile("teacher_cal", self)
        store   = os.path.join(APP_DIR, ".webdata")
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
        page.setBackgroundColor(QColor(0, 0, 0, 0))

        self._view = QWebEngineView()
        self._view.setPage(page)
        self._view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._view.setStyleSheet("background:transparent;")
        self._view.setUrl(QUrl(url))

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
        self._view.setUrl(QUrl(self._url))

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
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("선생님 캘린더")

    html_path = os.path.join(APP_DIR, HTML_FILE)
    if not os.path.exists(html_path):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "오류",
            f"{HTML_FILE} 파일을 찾을 수 없습니다.\n{html_path}")
        sys.exit(1)

    port = _find_free_port()
    _start_server(port)
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
    main()
