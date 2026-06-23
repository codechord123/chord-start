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
        QPushButton, QSizeGrip, QSystemTrayIcon, QMenu
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


# ── 자동 숨김 드래그 바 (마우스 올리면 나타남) ───────────────────────────
class DragBar(QWidget):
    def __init__(self, window):
        super().__init__()
        self._win = window
        self._press = None
        self.setFixedHeight(22)
        self.setMouseTracking(True)
        self._hovered = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 6, 0)
        lay.setSpacing(4)

        self._grip = QLabel("☰  선생님 캘린더")
        lay.addWidget(self._grip)
        lay.addStretch()

        self._pin_btn = self._make_btn("📌", "항상 위에 고정", self._win.toggle_pin)
        self._buttons = [
            self._pin_btn,
            self._make_btn("↻", "새로고침", self._win.reload_page),
            self._make_btn("—", "숨기기", self._win.hide),
            self._make_btn("✕", "종료", QApplication.quit),
        ]
        for b in self._buttons:
            lay.addWidget(b)

        self._apply_style(False)

    def _make_btn(self, text, tip, slot):
        b = QPushButton(text)
        b.setToolTip(tip)
        b.setFixedSize(24, 18)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(
            "QPushButton{background:transparent;border:none;color:rgba(255,255,255,0.85);"
            "font-size:11px;border-radius:4px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.25);}"
        )
        b.clicked.connect(slot)
        return b

    def _apply_style(self, hovered):
        if hovered:
            self.setStyleSheet("background: rgba(10,18,35,0.85);")
            self._grip.setStyleSheet("color: rgba(255,255,255,0.9); font-size:11px; font-weight:bold;")
            for b in self._buttons:
                b.setVisible(True)
        else:
            self.setStyleSheet("background: transparent;")
            self._grip.setStyleSheet("color: rgba(255,255,255,0.0); font-size:11px;")
            for b in self._buttons:
                b.setVisible(False)

    def enterEvent(self, e):
        self._hovered = True
        self._apply_style(True)

    def leaveEvent(self, e):
        self._hovered = False
        self._apply_style(False)

    def set_pinned(self, pinned):
        self._pin_btn.setStyleSheet(
            "QPushButton{background:%s;border:none;color:white;font-size:11px;border-radius:4px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.3);}"
            % ("rgba(59,130,246,0.85)" if pinned else "transparent")
        )

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press = e.globalPosition().toPoint() - self._win.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._press and e.buttons() & Qt.MouseButton.LeftButton:
            self._win.move(e.globalPosition().toPoint() - self._press)

    def mouseReleaseEvent(self, e):
        self._press = None
        self._win.save_geometry()


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

        # 영구 프로필 — TODO 등 localStorage 저장 유지
        profile = QWebEngineProfile("teacher_calendar", self)
        storage = os.path.join(APP_DIR, ".webdata")
        os.makedirs(storage, exist_ok=True)
        profile.setPersistentStoragePath(storage)
        profile.setCachePath(os.path.join(storage, "cache"))
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        self._view = QWebEngineView()
        self._view.setPage(QWebEnginePage(profile, self._view))
        self._view.setUrl(QUrl(url))

        self._bar = DragBar(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._bar)
        root.addWidget(self._view, 1)

        grip = QSizeGrip(self)
        grow = QHBoxLayout()
        grow.setContentsMargins(0, 0, 2, 2)
        grow.addStretch()
        grow.addWidget(grip)
        root.addLayout(grow)

        # 저장된 위치/크기 복원
        geo = self._settings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        else:
            self.resize(920, 660)
            screen = QApplication.primaryScreen().availableGeometry()
            self.move(screen.right() - 960, screen.bottom() - 720)

    def _apply_flags(self):
        # 바탕화면 위젯: 프레임 없음, 작업표시줄 없음
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        flags |= Qt.WindowType.WindowStaysOnTopHint if self._pinned else Qt.WindowType.WindowStaysOnBottomHint
        self.setWindowFlags(flags)

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
        self._apply_flags()
        self.show()

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

    def toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.lower() if not self._pinned else self.raise_()

    def reload_page(self):
        self._view.setUrl(QUrl(self._url))

    def save_geometry(self):
        self._settings.setValue("geometry", self.saveGeometry())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.save_geometry()

    def closeEvent(self, e):
        self.save_geometry()
        super().closeEvent(e)


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

    # 시작 1초 뒤 바탕화면에 자동으로 박는다 (창 핸들·이벤트 루프 준비 후)
    def _auto_embed():
        if not win.embed_into_desktop():
            win.lower()   # 폴백: 그냥 아래로 깔기
    QTimer.singleShot(1000, _auto_embed)

    tray = QSystemTrayIcon(make_icon(), app)
    tray.setToolTip("선생님 캘린더")

    menu = QMenu()
    menu.setStyleSheet(
        "QMenu{background:white;border:1px solid #e2e8f0;border-radius:8px;padding:4px;}"
        "QMenu::item{padding:7px 22px;border-radius:5px;font-size:13px;}"
        "QMenu::item:selected{background:#eff6ff;color:#2563eb;}"
    )

    a_show = QAction("표시 / 숨기기", app)
    a_show.triggered.connect(win.toggle_visible)
    menu.addAction(a_show)

    a_embed = QAction("🖼️ 바탕화면 위젯모드 켜기/끄기", app)
    a_embed.triggered.connect(win.toggle_embed)
    menu.addAction(a_embed)
    if not HAS_WIN32:
        a_embed.setEnabled(False)
        a_embed.setText("🖼️ 위젯모드 (pywin32 필요)")

    a_pin = QAction("📌 항상 위에 띄우기 (로그인·이동용)", app)
    a_pin.triggered.connect(win.toggle_pin)
    menu.addAction(a_pin)

    a_reload = QAction("새로고침", app)
    a_reload.triggered.connect(win.reload_page)
    menu.addAction(a_reload)

    menu.addSeparator()

    a_quit = QAction("종료", app)
    a_quit.triggered.connect(app.quit)
    menu.addAction(a_quit)

    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda r: win.toggle_visible() if r == QSystemTrayIcon.ActivationReason.Trigger else None
    )
    tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
