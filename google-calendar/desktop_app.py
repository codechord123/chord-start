"""
선생님 캘린더 - 데스크탑 위젯
index.html (구글 캘린더 + TODO)을 바탕화면에 얹히는 위젯으로 띄웁니다.

실행: pythonw desktop_app.py
필요: pip install PyQt6 PyQt6-WebEngine
"""
import os
import sys
import socket
import threading
import functools
import http.server

try:
    from PyQt6.QtCore import Qt, QUrl, QSettings
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
        flags = (Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        if self._pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags |= Qt.WindowType.WindowStaysOnBottomHint
        self.setWindowFlags(flags)

    def toggle_pin(self):
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

    a_pin = QAction("항상 위에 고정 켜기/끄기", app)
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
