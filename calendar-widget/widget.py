from PyQt6.QtWidgets import QWidget, QApplication, QMenu, QToolTip
from PyQt6.QtCore import Qt, QDate, QRect, QPoint, QTimer, QSize
from PyQt6.QtGui import (QPainter, QPainterPath, QColor, QFont, QPen,
                          QLinearGradient, QAction, QFontMetrics)

DAYS_KO = ['일', '월', '화', '수', '목', '금', '토']

P  = 14          # outer padding
HH = 54          # header height
DH = 26          # day-of-week header height
CR = 14          # corner radius


class CalendarWidget(QWidget):

    def __init__(self, data):
        super().__init__()
        self._data = data
        today = QDate.currentDate()
        self._vy = today.year()
        self._vm = today.month()
        self._drag = None          # QPoint while dragging
        self._hover = -1           # hovered cell index
        self._cells = []           # [(QRect, date_str, day, is_curr, dow)]
        self._btn_prev = QRect()
        self._btn_next = QRect()
        self._btn_gear = QRect()

        opacity = int(data.get_setting('opacity', 90))
        self._bg_alpha = max(30, min(255, int(opacity / 100 * 255)))

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnBottomHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setMinimumSize(360, 420)
        self.resize(400, 460)

        pos = data.get_setting('pos')
        if pos:
            self.move(pos[0], pos[1])
        else:
            geo = QApplication.primaryScreen().availableGeometry()
            self.move(geo.right() - 420, geo.bottom() - 490)

        # Repaint every minute (keep "today" highlight fresh)
        t = QTimer(self)
        t.timeout.connect(self.update)
        t.start(60_000)

    # ── Paint ────────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # Background card
        path = QPainterPath()
        path.addRoundedRect(0, 0, W, H, CR, CR)
        painter.fillPath(path, QColor(255, 255, 255, self._bg_alpha))
        painter.setPen(QPen(QColor(0, 0, 0, 25), 1))
        painter.drawPath(path)

        self._paint_header(painter, W)
        self._paint_weekdays(painter, W)
        self._paint_grid(painter, W, H)

    def _paint_header(self, painter, W):
        # ── Teacher dot + name ───────────────────────────────────────────────
        me = self._data.get_me()
        if me:
            dot_x, dot_y, dot_r = P, HH // 2 - 6, 12
            painter.setBrush(QColor(me['color']))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(dot_x, dot_y, dot_r, dot_r)
            painter.setPen(QColor('#1e293b'))
            f = QFont('Malgun Gothic', 9, QFont.Weight.Medium)
            painter.setFont(f)
            painter.drawText(P + dot_r + 6, 0, W // 3, HH,
                             Qt.AlignmentFlag.AlignVCenter, me['name'])

        # ── Month label ──────────────────────────────────────────────────────
        month_txt = f'{self._vy}년 {self._vm}월'
        f = QFont('Malgun Gothic', 13, QFont.Weight.Bold)
        painter.setFont(f)
        painter.setPen(QColor('#1e293b'))
        painter.drawText(0, 0, W, HH, Qt.AlignmentFlag.AlignCenter, month_txt)

        # ── Nav buttons ──────────────────────────────────────────────────────
        fm = QFontMetrics(f)
        txt_w = fm.horizontalAdvance(month_txt)
        cx = W // 2
        btn_w, btn_h = 28, 28
        by = (HH - btn_h) // 2
        self._btn_prev = QRect(cx - txt_w // 2 - btn_w - 6, by, btn_w, btn_h)
        self._btn_next = QRect(cx + txt_w // 2 + 6, by, btn_w, btn_h)

        for rect, char in [(self._btn_prev, '‹'), (self._btn_next, '›')]:
            painter.setBrush(QColor(0, 0, 0, 18))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 7, 7)
            painter.setPen(QColor('#475569'))
            f2 = QFont('Malgun Gothic', 14)
            painter.setFont(f2)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, char)

        # ── Gear button ──────────────────────────────────────────────────────
        self._btn_gear = QRect(W - P - btn_w, by, btn_w, btn_h)
        painter.setBrush(QColor(0, 0, 0, 18))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self._btn_gear, 7, 7)
        painter.setPen(QColor('#475569'))
        f3 = QFont('Malgun Gothic', 12)
        painter.setFont(f3)
        painter.drawText(self._btn_gear, Qt.AlignmentFlag.AlignCenter, '⚙')

    def _paint_weekdays(self, painter, W):
        cell_w = (W - P * 2) / 7
        y = HH
        DOW_COLORS = ['#ef4444','#64748b','#64748b','#64748b','#64748b','#64748b','#3b82f6']
        f = QFont('Malgun Gothic', 9, QFont.Weight.Bold)
        painter.setFont(f)
        for i, (day, color) in enumerate(zip(DAYS_KO, DOW_COLORS)):
            x = P + i * cell_w
            painter.setPen(QColor(color))
            painter.drawText(int(x), y, int(cell_w), DH, Qt.AlignmentFlag.AlignCenter, day)

    def _paint_grid(self, painter, W, H):
        grid_top = HH + DH
        grid_h = H - grid_top - P
        cell_w = (W - P * 2) / 7
        cell_h = grid_h / 6

        today = QDate.currentDate()
        first = QDate(self._vy, self._vm, 1)
        dim = first.daysInMonth()
        # dayOfWeek(): Mon=1 … Sun=7 → convert to Sun=0 … Sat=6
        fdow = first.dayOfWeek() % 7

        self._cells.clear()

        for idx in range(42):
            row, col = divmod(idx, 7)
            day = idx - fdow + 1
            if day < 1:
                qd = QDate(self._vy, self._vm, 1).addDays(day - 1)
                is_curr = False
            elif day > dim:
                qd = QDate(self._vy, self._vm, dim).addDays(day - dim)
                is_curr = False
            else:
                qd = QDate(self._vy, self._vm, day)
                is_curr = True

            is_today = (qd == today)
            date_str = qd.toString('yyyy-MM-dd')
            dow = col  # 0=Sun … 6=Sat

            cx = P + col * cell_w
            cy = grid_top + row * cell_h
            rect = QRect(int(cx), int(cy), int(cell_w), int(cell_h))
            self._cells.append((rect, date_str, qd.day(), is_curr, dow))

            # Hover bg
            if is_curr and self._hover == idx:
                painter.fillRect(rect.adjusted(2, 2, -2, -2),
                                 QColor(59, 130, 246, 22))

            # Day number
            num_rect = QRect(int(cx) + 3, int(cy) + 3, 22, 22)
            if is_today:
                painter.setBrush(QColor('#3b82f6'))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(num_rect)
                num_color = QColor('white')
            else:
                if not is_curr:
                    num_color = QColor('#d1d5db')
                elif dow == 0:
                    num_color = QColor('#ef4444')
                elif dow == 6:
                    num_color = QColor('#3b82f6')
                else:
                    num_color = QColor('#1e293b')

            f = QFont('Malgun Gothic', 9,
                      QFont.Weight.Bold if is_today else QFont.Weight.Normal)
            painter.setFont(f)
            painter.setPen(num_color)
            painter.drawText(num_rect, Qt.AlignmentFlag.AlignCenter, str(qd.day()))

            # Events
            if not is_curr:
                continue
            day_evs = self._data.get_events(date_str)
            ev_y = int(cy) + 28
            ev_h = 13
            ev_gap = 2
            max_ev = max(0, int((cell_h - 30) / (ev_h + ev_gap)))
            for i, ev in enumerate(day_evs[:max_ev]):
                t = self._data.get_teacher(ev.get('teacher_id', ''))
                color = QColor(t['color'] if t else '#94a3b8')
                bar = QRect(int(cx) + 3, ev_y + i * (ev_h + ev_gap),
                            int(cell_w) - 6, ev_h)
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bar, 3, 3)
                painter.setPen(QColor('white'))
                f2 = QFont('Malgun Gothic', 7)
                painter.setFont(f2)
                title = ev.get('start_time', '') + (' ' if ev.get('start_time') else '') + ev.get('title', '')
                fm = QFontMetrics(f2)
                title = fm.elidedText(title, Qt.TextElideMode.ElideRight, bar.width() - 4)
                painter.drawText(bar.adjusted(3, 0, -2, 0), Qt.AlignmentFlag.AlignVCenter, title)

            if len(day_evs) > max_ev:
                more_y = ev_y + max_ev * (ev_h + ev_gap)
                painter.setPen(QColor('#94a3b8'))
                f3 = QFont('Malgun Gothic', 7)
                painter.setFont(f3)
                painter.drawText(int(cx) + 3, more_y, int(cell_w) - 6, ev_h,
                                 Qt.AlignmentFlag.AlignVCenter,
                                 f'+{len(day_evs)-max_ev}개')

    # ── Mouse ────────────────────────────────────────────────────────────────
    def mousePressEvent(self, ev):
        pos = ev.position().toPoint()
        if ev.button() == Qt.MouseButton.LeftButton:
            if self._btn_prev.contains(pos):
                self._prev_month()
                return
            if self._btn_next.contains(pos):
                self._next_month()
                return
            if self._btn_gear.contains(pos):
                self._open_settings()
                return
            if pos.y() < HH:          # header drag
                self._drag = pos
                return
            for i, (rect, date_str, day, is_curr, dow) in enumerate(self._cells):
                if rect.contains(pos) and is_curr:
                    self._open_add_event(date_str)
                    return
        elif ev.button() == Qt.MouseButton.RightButton:
            self._context_menu(ev.globalPosition().toPoint())

    def mouseMoveEvent(self, ev):
        pos = ev.position().toPoint()
        if self._drag and ev.buttons() & Qt.MouseButton.LeftButton:
            self.move(self.pos() + (pos - self._drag))
            return
        hover = -1
        for i, (rect, _, _, is_curr, _) in enumerate(self._cells):
            if rect.contains(pos) and is_curr:
                hover = i
                break
        if hover != self._hover:
            self._hover = hover
            self.setCursor(Qt.CursorShape.PointingHandCursor
                           if hover >= 0 else Qt.CursorShape.ArrowCursor)
            self.update()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and self._drag:
            self._data.set_setting('pos', [self.pos().x(), self.pos().y()])
            self._drag = None

    def mouseDoubleClickEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and ev.position().toPoint().y() < HH:
            self.setWindowFlags(self.windowFlags() ^ Qt.WindowType.WindowStaysOnBottomHint)
            self.show()

    # ── Actions ──────────────────────────────────────────────────────────────
    def _prev_month(self):
        self._vm -= 1
        if self._vm < 1:
            self._vm, self._vy = 12, self._vy - 1
        self.update()

    def _next_month(self):
        self._vm += 1
        if self._vm > 12:
            self._vm, self._vy = 1, self._vy + 1
        self.update()

    def _open_add_event(self, date_str):
        from dialogs import EventDialog
        dlg = EventDialog(self._data, date_str=date_str)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        if dlg.exec() and dlg.result_event:
            self._data.save_event(dlg.result_event)
            self.update()

    def open_edit_event(self, event):
        from dialogs import EventDialog
        dlg = EventDialog(self._data, event=event)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        if dlg.exec():
            if dlg.deleted:
                self._data.delete_event(event['id'])
            elif dlg.result_event:
                self._data.save_event(dlg.result_event)
            self.update()

    def _open_settings(self):
        from dialogs import SettingsDialog
        dlg = SettingsDialog(self._data)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        if dlg.exec():
            op = int(self._data.get_setting('opacity', 90))
            self._bg_alpha = max(30, min(255, int(op / 100 * 255)))
            self.update()

    def _context_menu(self, gpos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 7px 20px; border-radius: 5px; font-size: 13px; }
            QMenu::item:selected { background: #eff6ff; color: #2563eb; }
        """)
        today_str = QDate.currentDate().toString('yyyy-MM-dd')
        a1 = menu.addAction('📅  오늘 일정 추가')
        menu.addSeparator()
        a2 = menu.addAction('⚙️  설정')
        a3 = menu.addAction('오늘로 이동')
        menu.addSeparator()
        a4 = menu.addAction('종료')
        act = menu.exec(gpos)
        if act == a1:
            self._open_add_event(today_str)
        elif act == a2:
            self._open_settings()
        elif act == a3:
            t = QDate.currentDate()
            self._vy, self._vm = t.year(), t.month()
            self.update()
        elif act == a4:
            QApplication.quit()

    def toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
