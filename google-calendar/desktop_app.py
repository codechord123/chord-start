"""
선생님 캘린더 - 데스크탑 앱
index.html (구글 캘린더 + TODO 위젯)을 그대로 데스크탑 창으로 띄웁니다.

실행: pythonw desktop_app.py   (검은 창 없이)
필요: pip install PyQt6 PyQt6-WebEngine
"""
import os
import sys
import socket
import threading
import functools
import http.server

from PyQt6.QtCore import Qt, QUrl, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSizeGrip, QSystemTrayIcon, QMenu
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage

APP_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = 'index.html'


# ── 로컬 웹서버 (구글 로그인 origin 문제 해결을 위해 http로 서빙) ──────────
def find_free_port(preferred=8765):
    for port in [preferred, 8766, 8767, 8768, 8770, 8800]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return preferred


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass  # 콘솔 로그 끄기


def start_server(port):
    handler = functools.partial(QuietHandler, directory=APP_DIR)
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


# ── 드래그 가능한 상단 바 ────────────────────────────────────────────────
class DragBar(QWidget):
    def __init__(self, window):
        super().__init__()
        self._win = window
        self._press = None
        self.setFixedHeight(30)
        self.setStyleSheet("background: rgba(10,18,35,0.92);")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 6, 0)
        lay.setSpacing(4)

        title = QLabel("📅  선생님 캘린더")
        title.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 12px; font-weight: bold;")
        lay.addWidget(title)
        lay.addStretch()

        self._pin_btn = self._make_btn("📌", "항상 위에 고정", self._win.toggle_pin)
        lay.addWidget(self._pin_btn)
        lay.addWidget(self._make_btn("—", "트레이로 숨기기", self._win.hide))
        lay.addWidget(self._make_btn("✕", "종료", QApplication.quit))

    def _make_btn(self, text, tip, slot):
        b = QPushButton(text)
        b.setToolTip(tip)
        b.setFixedSize(26, 22)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: rgba(255,255,255,0.7);
                          font-size: 13px; border-radius: 5px; }
            QPushButton:hover { background: rgba(255,255,255,0.15); color: white; }
        """)
        b.clicked.connect(slot)
        return b

    def set_pinned(self, pinned):
        self._pin_btn.setStyleSheet(
            "QPushButton { background: %s; border: none; color: white; font-size: 13px; border-radius: 5px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.25); }"
            % ("rgba(59,130,246,0.8)" if pinned else "transparent")
        )

    # 드래그로 창 이동
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press = e.globalPosition().toPoint() - self._win.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._press and e.buttons() & Qt.MouseButton.LeftButton:
            self._win.move(e.globalPosition().toPoint() - self._press)

    def mouseReleaseEvent(self, e):
        self._press = None


# ── 메인 창 ──────────────────────────────────────────────────────────────
class CalendarWindow(QWidget):
    def __init__(self, url):
        super().__init__()
        self._pinned = False
        self.setWindowTitle("선생님 캘린더")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(920, 660)

        # 영구 프로필 (TODO 등 localStorage 저장 유지)
        profile = QWebEngineProfile("teacher_calendar", self)
        storage = os.path.join(APP_DIR, ".webdata")
        os.makedirs(storage, exist_ok=True)
        profile.setPersistentStoragePath(storage)
        profile.setCachePath(os.path.join(storage, "cache"))
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        self._view = QWebEngineView()
        page = QWebEnginePage(profile, self._view)
        self._view.setPage(page)
        self._view.setUrl(QUrl(url))

        self._bar = DragBar(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._bar)
        root.addWidget(self._view, 1)

        # 우하단 크기 조절 그립
        grip = QSizeGrip(self)
        grip_lay = QHBoxLayout()
        grip_lay.setContentsMargins(0, 0, 2, 2)
        grip_lay.addStretch()
        grip_lay.addWidget(grip)
        root.addLayout(grip_lay)

    def toggle_pin(self):
        self._pinned = not self._pinned
        flags = Qt.WindowType.FramelessWindowHint
        if self._pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self._bar.set_pinned(self._pinned)
        self.show()  # 플래그 변경 후 다시 표시 필요

    def toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()


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

    if not os.path.exists(os.path.join(APP_DIR, HTML_FILE)):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "오류",
            f"{HTML_FILE} 파일을 찾을 수 없습니다.\n이 파일은 index.html과 같은 폴더에 있어야 합니다.")
        sys.exit(1)

    port = find_free_port()
    start_server(port)
    url = f"http://localhost:{port}/{HTML_FILE}"

    win = CalendarWindow(url)
    win.show()

    tray = QSystemTrayIcon(make_icon(), app)
    tray.setToolTip("선생님 캘린더")
    menu = QMenu()
    menu.setStyleSheet("""
        QMenu { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px; }
        QMenu::item { padding: 7px 22px; border-radius: 5px; font-size: 13px; }
        QMenu::item:selected { background: #eff6ff; color: #2563eb; }
    """)
    a_show = QAction("캘린더 표시 / 숨기기", app)
    a_show.triggered.connect(win.toggle_visible)
    menu.addAction(a_show)
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
