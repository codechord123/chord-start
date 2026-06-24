"""
선생님 캘린더 - 데스크탑 위젯
index.html (구글 캘린더 + TODO)을 바탕화면에 얹히는 위젯으로 띄웁니다.

실행: pythonw desktop_app.py
필요: pip install PyQt6 PyQt6-WebEngine
선택: pip install pywin32  (바탕화면에 진짜로 박는 위젯모드)
"""
import os
import sys
import socket
import threading
import functools
import http.server

try:
    from PyQt6.QtCore import Qt, QUrl, QSettings, QTimer
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QSizeGrip, QSystemTrayIcon, QMenu, QCheckBox, QFrame
    )
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
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

APP_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = 'index.html'

# ── 바탕화면 임베딩 (Lively/Wallpaper Engine 방식의 WorkerW 기법) ──────────
# pywin32 가 있으면 진짜 위젯처럼 바탕화면에 박고, 없으면 폴백한다.
try:
    import ctypes
    from ctypes import wintypes
    _user32 = ctypes.windll.user32
    HAS_WIN32 = True
except Exception:
    HAS_WIN32 = False


def find_workerw():
    """바탕화면 그림 위 / 아이콘 아래에 있는 WorkerW 핸들을 찾는다."""
    if not HAS_WIN32:
        return None
    # Progman 에게 WorkerW 레이어 생성을 요청
    progman = _user32.FindWindowW("Progman", None)
    if not progman:
        return None
    _user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0x0000, 1000, None)

    workerw = ctypes.c_void_p(0)

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, lparam):
        # SHELLDLL_DefView(바탕화면 아이콘 호스트)를 자식으로 가진 형제 WorkerW 탐색
        shell = _user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
        if shell:
            nxt = _user32.FindWindowExW(None, hwnd, "WorkerW", None)
            if nxt:
                workerw.value = nxt
        return True

    _user32.EnumWindows(_enum, 0)
    return workerw.value


# ── 로컬 웹서버 (구글 로그인 origin 문제 해결) ────────────────────────────
def find_free_port(preferred=8765):
    for port in [preferred, 8766, 8767, 8768, 8770, 8800]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return preferred


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def start_server(port):
    handler = functools.partial(QuietHandler, directory=APP_DIR)
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


# ── 위젯 이동용 드래그 핸들 (버튼 없음 = 순수 위젯) ───────────────────────
class DragHandle(QWidget):
    """위젯 상단의 가느다란 이동 영역. 버튼이 전혀 없어 위젯만 보인다.
    평소엔 투명, 마우스를 올리면 잡는 위치만 살짝 표시한다."""
    def __init__(self, window):
        super().__init__(window)
        self._win = window
        self._press = None
        self.setFixedHeight(18)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._dots = QLabel("⠿⠿⠿")
        self._dots.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._dots)
        self._apply_style(False)

    def _apply_style(self, hovered):
        if hovered:
            self.setStyleSheet("background: rgba(10,18,35,0.45); border-top-left-radius:20px; border-top-right-radius:20px;")
            self._dots.setStyleSheet("color: rgba(255,255,255,0.55); font-size:10px; letter-spacing:2px;")
        else:
            self.setStyleSheet("background: transparent;")
            self._dots.setStyleSheet("color: rgba(255,255,255,0.0); font-size:10px;")

    def enterEvent(self, e):
        self._apply_style(True)

    def leaveEvent(self, e):
        self._apply_style(False)

    # 임베드 호환용 (설정에서 핀 상태를 알려도 무시) — 위젯엔 버튼이 없다
    def set_pinned(self, pinned):
        pass

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press = e.globalPosition().toPoint() - self._win.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._press and e.buttons() & Qt.MouseButton.LeftButton:
            self._win.move(e.globalPosition().toPoint() - self._press)

    def mouseReleaseEvent(self, e):
        self._press = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._win.save_geometry()


# ── Google OAuth 팝업 핸들러 ──────────────────────────────────────────────
class _CalendarPage(QWebEnginePage):
    """signInWithPopup 이 여는 구글 로그인 팝업을 별도 창으로 받아줌."""
    _popups: list = []

    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)

    def createWindow(self, window_type):
        popup = QWebEngineView()
        popup.setWindowTitle("Google 로그인")
        popup.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint
        )
        popup.resize(480, 640)
        popup.show()
        _CalendarPage._popups.append(popup)   # GC 방지
        page = _CalendarPage(self.profile(), popup)
        popup.setPage(page)
        # 팝업이 닫히면 목록에서 제거
        popup.destroyed.connect(lambda: _CalendarPage._popups.remove(popup)
                                if popup in _CalendarPage._popups else None)
        return page


# ── 메인 위젯 창 ─────────────────────────────────────────────────────────
class CalendarWidget(QWidget):
    def __init__(self, url):
        super().__init__()
        self._url = url
        self._settings = QSettings("TeacherCalendar", "widget")
        self._pinned = False
        self._embedded = False   # 바탕화면에 박혀 있는가

        self.setWindowTitle("선생님 캘린더")
        self._apply_flags()
        # 창 배경 투명 → 바탕화면이 비쳐 '프로그램 창'이 아닌 '위젯'처럼 보인다
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # 영구 프로필 — TODO 등 localStorage 저장 유지
        profile = QWebEngineProfile("teacher_calendar", self)
        storage = os.path.join(APP_DIR, ".webdata")
        os.makedirs(storage, exist_ok=True)
        profile.setPersistentStoragePath(storage)
        profile.setCachePath(os.path.join(storage, "cache"))
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        # Google이 임베디드 웹뷰로 OAuth를 차단(disallowed_useragent)하지 않도록
        # 일반 데스크톱 Chrome User-Agent 로 위장한다.
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        self._view = QWebEngineView()
        page = _CalendarPage(profile, self._view)
        # 웹뷰 배경도 투명 처리 (기본은 흰색 → 둥근 모서리 밖이 흰 사각형으로 남음)
        page.setBackgroundColor(QColor(Qt.GlobalColor.transparent))
        self._view.setPage(page)
        self._view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._view.setStyleSheet("background: transparent;")
        self._view.setUrl(QUrl(url))

        # 웹뷰가 창 전체를 채우고, 드래그바·크기조절 그립은 그 위에 겹쳐(오버레이)
        # 떠 있게 한다 → 둥근 카드가 창을 꽉 채워 '프로그램 창'이 아닌 위젯처럼 보인다.
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._view, 1)

        self._bar = DragHandle(self)
        self._bar.setParent(self)
        self._bar.raise_()

        self._grip = QSizeGrip(self)
        self._grip.setParent(self)
        self._grip.raise_()

        # 저장된 위치/크기 복원 (없으면 화면 가운데에 배치)
        geo = self._settings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        else:
            self.resize(920, 660)
            self.center_on_screen()

    def _apply_flags(self):
        # 바탕화면 위젯: 프레임 없음, 작업표시줄 없음
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        flags |= Qt.WindowType.WindowStaysOnTopHint if self._pinned else Qt.WindowType.WindowStaysOnBottomHint
        self.setWindowFlags(flags)

    def _set_chrome_visible(self, visible):
        """드래그바·크기조절 그립(=프로그램 티)을 보이거나 숨긴다."""
        self._bar.setVisible(visible)
        self._grip.setVisible(visible)

    # ── 바탕화면에 진짜로 박기 ───────────────────────────────
    def embed_into_desktop(self):
        """WorkerW 의 자식으로 붙여 Lively 처럼 바탕화면에 고정한다."""
        if not HAS_WIN32:
            return False
        worker = find_workerw()
        if not worker:
            return False
        try:
            geo = self.frameGeometry()           # 현재 화면상 위치 기억
            hwnd = int(self.winId())
            _user32.SetParent(hwnd, worker)
            # WorkerW 기준 상대좌표로 재배치
            pt = wintypes.POINT(geo.x(), geo.y())
            _user32.ScreenToClient(worker, ctypes.byref(pt))
            _user32.MoveWindow(hwnd, pt.x, pt.y, geo.width(), geo.height(), True)
            self._embedded = True
            self._bar.set_pinned(False)
            self._set_chrome_visible(False)      # 순수 위젯 = 크롬 숨김
            return True
        except Exception:
            return False

    def detach_from_desktop(self):
        """바탕화면에서 떼어내 일반 창으로 되돌린다 (로그인·이동용)."""
        if not (HAS_WIN32 and self._embedded):
            return
        try:
            _user32.SetParent(int(self.winId()), None)
        except Exception:
            pass
        self._embedded = False
        self._set_chrome_visible(True)           # 조작모드 = 크롬 표시
        self._apply_flags()
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_embed(self):
        """위젯모드(바탕화면 고정) ↔ 일반 창모드 전환."""
        if self._embedded:
            self.detach_from_desktop()
        else:
            self._pinned = False
            if not self.embed_into_desktop():
                # 임베드 불가(구버전/pywin32 없음): 기존 '아래로 깔기' 유지
                self._apply_flags()
                self.show()
                self.lower()

    def toggle_pin(self):
        # 박혀 있으면 먼저 떼어낸 뒤 위로 띄운다
        if self._embedded:
            self.detach_from_desktop()
        self._pinned = not self._pinned
        self._apply_flags()
        self._bar.set_pinned(self._pinned)
        self.show()

    # ── 설정 프로그램 창에서 호출하는 제어 메서드들 ──────────────
    def set_always_on_top(self, on):
        if self._embedded:
            self.detach_from_desktop()
        self._pinned = bool(on)
        self._apply_flags()
        self.show()
        self.raise_() if self._pinned else self.lower()

    def is_on_top(self):
        return self._pinned

    def center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        fg = self.frameGeometry()
        fg.moveCenter(screen.center())
        self.move(fg.topLeft())
        self.save_geometry()

    def apply_size(self, w, h):
        self.resize(int(w), int(h))
        self.center_on_screen()

    def show_widget(self):
        self.show()
        self.raise_() if self._pinned else self.lower()

    def toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show_widget()

    def reload_page(self):
        self._view.setUrl(QUrl(self._url))

    def save_geometry(self):
        self._settings.setValue("geometry", self.saveGeometry())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # 오버레이 크롬 위치 재계산 (드래그바=상단 전체, 그립=우하단 모서리)
        if hasattr(self, "_bar"):
            self._bar.setGeometry(0, 0, self.width(), 18)
            self._bar.raise_()
        if hasattr(self, "_grip"):
            gs = 16
            self._grip.setGeometry(self.width() - gs, self.height() - gs, gs, gs)
            self._grip.raise_()
        self.save_geometry()

    def closeEvent(self, e):
        self.save_geometry()
        super().closeEvent(e)


# ── 프로그램(설정) 창 — 위젯과 완전히 분리 ────────────────────────────────
class SettingsWindow(QWidget):
    """'프로그램' 창. 위젯을 제어하는 모든 버튼이 여기에 모여 있다.
    위젯 본체에는 버튼이 없으므로 바탕화면엔 깔끔한 캘린더만 보인다."""

    SIZES = [("작게", 720, 520), ("보통", 920, 660), ("크게", 1180, 820)]

    def __init__(self, widget, app):
        super().__init__()
        self._w = widget
        self._app = app
        self.setWindowTitle("선생님 캘린더 — 프로그램")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.resize(380, 500)
        self.setStyleSheet(
            "QWidget{background:#0f172a;color:#e2e8f0;font-family:'Malgun Gothic','Noto Sans KR';}"
            "QLabel#title{font-size:17px;font-weight:bold;color:white;}"
            "QLabel#sub{color:#94a3b8;font-size:12px;}"
            "QLabel#sec{color:#7dd3fc;font-size:12px;font-weight:bold;margin-top:6px;}"
            "QPushButton{background:#1e293b;border:1px solid #334155;border-radius:8px;"
            "padding:9px 12px;color:#e2e8f0;font-size:13px;}"
            "QPushButton:hover{background:#273449;border-color:#3b82f6;}"
            "QPushButton#primary{background:#2563eb;border:none;color:white;font-weight:bold;}"
            "QPushButton#primary:hover{background:#1d4ed8;}"
            "QPushButton#danger{background:#3a1620;border:1px solid #7f1d2e;color:#fca5a5;}"
            "QPushButton#danger:hover{background:#4c1d2a;}"
            "QCheckBox{font-size:13px;spacing:8px;}"
            "QFrame#hr{background:#1e293b;max-height:1px;min-height:1px;}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(8)

        title = QLabel("📅 선생님 캘린더")
        title.setObjectName("title")
        root.addWidget(title)
        sub = QLabel("바탕화면 위젯을 여기서 제어합니다.")
        sub.setObjectName("sub")
        root.addWidget(sub)

        root.addWidget(self._hr())

        # 표시/숨기기
        root.addWidget(self._section("위젯 표시"))
        self._btn_toggle = self._mk("👁  위젯 보이기 / 숨기기", self._toggle_show, primary=True)
        root.addWidget(self._btn_toggle)

        # 위치 / 크기
        root.addWidget(self._section("위치 · 크기"))
        root.addWidget(self._mk("🎯  화면 가운데로 정렬", self._w.center_on_screen))
        size_row = QHBoxLayout()
        size_row.setSpacing(6)
        for name, w, h in self.SIZES:
            b = self._mk(name, lambda _=False, w=w, h=h: self._w.apply_size(w, h))
            size_row.addWidget(b)
        root.addLayout(size_row)
        hint = QLabel("· 위젯 위쪽 모서리를 끌어 이동\n· 오른쪽 아래 모서리를 끌어 크기 조절")
        hint.setObjectName("sub")
        root.addWidget(hint)

        # 옵션
        root.addWidget(self._section("옵션"))
        self._chk_top = QCheckBox("항상 맨 위에 표시")
        self._chk_top.setChecked(self._w.is_on_top())
        self._chk_top.toggled.connect(self._w.set_always_on_top)
        root.addWidget(self._chk_top)

        if HAS_WIN32:
            self._chk_embed = QCheckBox("벽지에 박기 (보기 전용 · 클릭 불가)")
            self._chk_embed.toggled.connect(self._on_embed_toggled)
            root.addWidget(self._chk_embed)

        root.addWidget(self._mk("↻  위젯 새로고침", self._w.reload_page))

        root.addStretch()
        root.addWidget(self._hr())
        root.addWidget(self._mk("⏻  완전히 종료", self._app.quit, danger=True))

    # 헬퍼 ---------------------------------------------------------------
    def _mk(self, text, slot, primary=False, danger=False):
        b = QPushButton(text)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        if primary:
            b.setObjectName("primary")
        elif danger:
            b.setObjectName("danger")
        b.clicked.connect(lambda: slot())
        return b

    def _section(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("sec")
        return lbl

    def _hr(self):
        f = QFrame()
        f.setObjectName("hr")
        f.setFrameShape(QFrame.Shape.HLine)
        return f

    def _toggle_show(self):
        self._w.toggle_visible()

    def _on_embed_toggled(self, on):
        # 체크 상태와 실제 임베드 상태를 맞춘다
        if on and not self._w._embedded:
            self._w.toggle_embed()
        elif not on and self._w._embedded:
            self._w.detach_from_desktop()

    def open(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, e):
        # 닫아도 프로그램은 트레이에 남는다 (위젯 계속 동작)
        e.ignore()
        self.hide()


# ── 트레이 아이콘 ────────────────────────────────────────────────────────
def make_icon():
    px = QPixmap(64, 64)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#3b82f6"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(4, 4, 56, 56, 14, 14)
    p.setPen(QColor("white"))
    p.setFont(QFont("Segoe UI Emoji", 26))
    p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "📅")
    p.end()
    return QIcon(px)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("선생님 캘린더")

    html_path = os.path.join(APP_DIR, HTML_FILE)
    if not os.path.exists(html_path):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "오류",
            f"{HTML_FILE} 파일을 찾을 수 없습니다.\n경로: {html_path}")
        sys.exit(1)

    port = find_free_port()
    start_server(port)
    url = f"http://localhost:{port}/{HTML_FILE}"

    win = CalendarWidget(url)
    win.show()
    win.lower()

    # 프로그램(설정) 창 — 위젯과 분리. 평소엔 숨겨져 있고 트레이에서 연다.
    settings = SettingsWindow(win, app)

    tray = QSystemTrayIcon(make_icon(), app)
    tray.setToolTip("선생님 캘린더")

    # 위젯은 맨 아래에 깔되 일반 창이라 스크롤·클릭·크기조절 모두 가능.
    def _settle():
        win.lower()
        if not win._settings.value("hint_shown"):
            tray.showMessage(
                "선생님 캘린더 위젯",
                "바탕화면에 위젯이 떴습니다.\n"
                "설정·종료는 트레이(📅) 아이콘을 클릭하세요.",
                QSystemTrayIcon.MessageIcon.Information, 6000)
            win._settings.setValue("hint_shown", True)
    QTimer.singleShot(600, _settle)

    menu = QMenu()
    menu.setStyleSheet(
        "QMenu{background:white;border:1px solid #e2e8f0;border-radius:8px;padding:4px;}"
        "QMenu::item{padding:7px 22px;border-radius:5px;font-size:13px;}"
        "QMenu::item:selected{background:#eff6ff;color:#2563eb;}"
        "QMenu::separator{height:1px;background:#e2e8f0;margin:4px 6px;}"
    )

    a_settings = QAction("⚙  프로그램 설정 열기", app)
    a_settings.triggered.connect(settings.open)
    menu.addAction(a_settings)

    a_show = QAction("👁  위젯 표시 / 숨기기", app)
    a_show.triggered.connect(win.toggle_visible)
    menu.addAction(a_show)

    menu.addSeparator()

    a_quit = QAction("⏻  종료", app)
    a_quit.triggered.connect(app.quit)
    menu.addAction(a_quit)

    tray.setContextMenu(menu)
    # 트레이 아이콘 클릭 → 프로그램 설정 창 열기
    tray.activated.connect(
        lambda r: settings.open()
        if r == QSystemTrayIcon.ActivationReason.Trigger else None
    )
    tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
