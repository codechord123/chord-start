import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
from PyQt6.QtCore import Qt

from data import DataManager
from widget import CalendarWidget


def make_tray_icon():
    px = QPixmap(64, 64)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor('#3b82f6'))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(4, 4, 56, 56, 12, 12)
    p.setPen(QColor('white'))
    f = QFont('Malgun Gothic', 22, QFont.Weight.Bold)
    p.setFont(f)
    p.drawText(0, 0, 64, 64, Qt.AlignmentFlag.AlignCenter, '📅')
    p.end()
    return QIcon(px)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName('선생님 캘린더')

    data = DataManager()

    # First-run setup
    if not data.is_setup_done():
        from dialogs import SetupDialog
        dlg = SetupDialog()
        if dlg.exec():
            data.setup_me(dlg.result_name, dlg.result_color)
        else:
            sys.exit(0)

    widget = CalendarWidget(data)
    widget.show()

    # System tray
    tray = QSystemTrayIcon(make_tray_icon(), app)
    tray.setToolTip('선생님 캘린더')

    menu = QMenu()
    menu.setStyleSheet("""
        QMenu { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px; }
        QMenu::item { padding: 7px 20px; border-radius: 5px; font-size: 13px; }
        QMenu::item:selected { background: #eff6ff; color: #2563eb; }
    """)

    show_act = QAction('캘린더 표시 / 숨기기', app)
    show_act.triggered.connect(widget.toggle_visible)
    menu.addAction(show_act)

    today_act = QAction('📅  오늘 일정 추가', app)
    from PyQt6.QtCore import QDate
    today_act.triggered.connect(
        lambda: widget._open_add_event(QDate.currentDate().toString('yyyy-MM-dd'))
    )
    menu.addAction(today_act)

    menu.addSeparator()

    quit_act = QAction('종료', app)
    quit_act.triggered.connect(app.quit)
    menu.addAction(quit_act)

    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: widget.toggle_visible()
        if reason == QSystemTrayIcon.ActivationReason.Trigger else None
    )
    tray.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
