from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QDateEdit, QTimeEdit, QTextEdit,
                               QComboBox, QPushButton, QWidget, QCheckBox,
                               QFrame, QApplication)
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QFont

COLORS = [
    '#ef4444','#f97316','#eab308','#22c55e',
    '#14b8a6','#3b82f6','#8b5cf6','#ec4899',
    '#06b6d4','#84cc16','#f59e0b','#6366f1',
]

BASE_STYLE = """
QDialog { background: white; border-radius: 12px; }
QLabel { color: #374151; font-size: 13px; }
QLineEdit, QDateEdit, QTimeEdit, QTextEdit, QComboBox {
    border: 1px solid #d1d5db;
    border-radius: 7px;
    padding: 7px 10px;
    font-size: 13px;
    color: #111827;
    background: white;
}
QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus,
QTextEdit:focus, QComboBox:focus {
    border-color: #3b82f6;
}
QPushButton {
    border-radius: 7px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}
"""

def label(text):
    l = QLabel(text)
    l.setStyleSheet('font-size: 12px; font-weight: 600; color: #6b7280; margin-bottom: 2px;')
    return l


class ColorSwatch(QWidget):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.selected = False
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(2, 2, 26, 26)
        p.fillPath(path, QColor(self.color))
        if self.selected:
            p.setPen(QColor('#1e293b') if True else QColor(self.color))
            from PyQt6.QtGui import QPen
            p.setPen(QPen(QColor('#1e293b'), 2.5))
            p.drawEllipse(3, 3, 24, 24)

    def mousePressEvent(self, _):
        parent = self.parent()
        if hasattr(parent, '_swatches'):
            for sw in parent._swatches:
                sw.selected = False
                sw.update()
        self.selected = True
        self.update()


class ColorPicker(QWidget):
    def __init__(self, selected_color=COLORS[5], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._swatches = []
        for c in COLORS:
            sw = ColorSwatch(c, self)
            sw.selected = (c == selected_color)
            layout.addWidget(sw)
            self._swatches.append(sw)
        layout.addStretch()

    def selected_color(self):
        for sw in self._swatches:
            if sw.selected:
                return sw.color
        return COLORS[5]


# ── Setup Dialog (first run) ─────────────────────────────────────────────────
class SetupDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('선생님 캘린더 설정')
        self.setFixedWidth(380)
        self.setStyleSheet(BASE_STYLE)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(28, 28, 28, 24)

        title = QLabel('📅 선생님 캘린더')
        title.setStyleSheet('font-size: 20px; font-weight: 800; color: #1e293b;')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        sub = QLabel('이름과 색상을 선택해 주세요')
        sub.setStyleSheet('font-size: 13px; color: #64748b;')
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet('color: #e2e8f0; margin: 4px 0;')
        lay.addWidget(line)

        lay.addWidget(label('이름'))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText('예: 김선생님')
        self.name_edit.setMaxLength(20)
        lay.addWidget(self.name_edit)

        lay.addSpacing(4)
        lay.addWidget(label('내 색상'))
        self.color_picker = ColorPicker()
        lay.addWidget(self.color_picker)

        lay.addSpacing(8)
        self.btn = QPushButton('시작하기')
        self.btn.setStyleSheet(
            'QPushButton { background: #3b82f6; color: white; }'
            'QPushButton:hover { background: #2563eb; }'
        )
        self.btn.clicked.connect(self._accept)
        lay.addWidget(self.btn)

        self.result_name = ''
        self.result_color = COLORS[5]

    def _accept(self):
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setFocus()
            return
        self.result_name = name
        self.result_color = self.color_picker.selected_color()
        self.accept()


# ── Event Dialog ─────────────────────────────────────────────────────────────
class EventDialog(QDialog):
    def __init__(self, data, date_str=None, event=None):
        super().__init__()
        self._data = data
        self._event = event
        self.setWindowTitle('일정 수정' if event else '일정 추가')
        self.setFixedWidth(400)
        self.setStyleSheet(BASE_STYLE)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(24, 24, 24, 20)

        # Title
        h = QLabel('✏️ ' + self.windowTitle())
        h.setStyleSheet('font-size: 16px; font-weight: 700; color: #1e293b; margin-bottom: 6px;')
        lay.addWidget(h)

        # Title field
        lay.addWidget(label('제목 *'))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText('일정 제목')
        self.title_edit.setMaxLength(60)
        lay.addWidget(self.title_edit)

        # Date
        lay.addWidget(label('날짜 *'))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat('yyyy-MM-dd')
        lay.addWidget(self.date_edit)

        # Time row
        time_row = QHBoxLayout()
        time_row.setSpacing(10)
        tc1 = QVBoxLayout()
        tc1.addWidget(label('시작'))
        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat('HH:mm')
        self.start_edit.setSpecialValueText('없음')
        tc1.addWidget(self.start_edit)

        tc2 = QVBoxLayout()
        tc2.addWidget(label('종료'))
        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat('HH:mm')
        self.end_edit.setSpecialValueText('없음')
        tc2.addWidget(self.end_edit)

        self.has_time = QCheckBox('시간 설정')
        self.has_time.setStyleSheet('font-size: 12px; color: #6b7280;')
        self.has_time.toggled.connect(self._toggle_time)
        time_row.addLayout(tc1)
        time_row.addLayout(tc2)
        lay.addWidget(self.has_time)
        lay.addLayout(time_row)

        # Description
        lay.addWidget(label('내용'))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText('내용 (선택사항)')
        self.desc_edit.setFixedHeight(70)
        lay.addWidget(self.desc_edit)

        # Teacher
        lay.addWidget(label('작성 선생님'))
        self.teacher_combo = QComboBox()
        for t in data.all_teachers():
            self.teacher_combo.addItem(t['name'], t['id'])
        me = data.get_me()
        if me:
            idx = self.teacher_combo.findData(me['id'])
            if idx >= 0:
                self.teacher_combo.setCurrentIndex(idx)
        lay.addWidget(self.teacher_combo)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        if event:
            del_btn = QPushButton('삭제')
            del_btn.setStyleSheet(
                'QPushButton { background: white; color: #ef4444; border: 1px solid #ef4444; }'
                'QPushButton:hover { background: #ef4444; color: white; }'
            )
            del_btn.clicked.connect(self._delete)
            btn_row.addWidget(del_btn)
        btn_row.addStretch()
        save_btn = QPushButton('저장')
        save_btn.setStyleSheet(
            'QPushButton { background: #3b82f6; color: white; }'
            'QPushButton:hover { background: #2563eb; }'
        )
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

        # Prefill
        d = QDate.fromString(date_str or (event['date'] if event else ''), 'yyyy-MM-dd')
        self.date_edit.setDate(d if d.isValid() else QDate.currentDate())
        if event:
            self.title_edit.setText(event.get('title', ''))
            self.desc_edit.setPlainText(event.get('description', ''))
            if event.get('start_time'):
                self.has_time.setChecked(True)
                self.start_edit.setTime(QTime.fromString(event['start_time'], 'HH:mm'))
                self.end_edit.setTime(QTime.fromString(event.get('end_time', '00:00'), 'HH:mm'))
            idx = self.teacher_combo.findData(event.get('teacher_id', ''))
            if idx >= 0:
                self.teacher_combo.setCurrentIndex(idx)

        self._toggle_time(self.has_time.isChecked())
        self.result_event = None
        self.deleted = False

    def _toggle_time(self, on):
        self.start_edit.setEnabled(on)
        self.end_edit.setEnabled(on)

    def _save(self):
        title = self.title_edit.text().strip()
        if not title:
            self.title_edit.setFocus()
            return
        ev = {
            'id': self._event['id'] if self._event else DataManager_new_id(),
            'title': title,
            'date': self.date_edit.date().toString('yyyy-MM-dd'),
            'description': self.desc_edit.toPlainText().strip(),
            'teacher_id': self.teacher_combo.currentData() or '',
        }
        if self.has_time.isChecked():
            ev['start_time'] = self.start_edit.time().toString('HH:mm')
            ev['end_time'] = self.end_edit.time().toString('HH:mm')
        self.result_event = ev
        self.accept()

    def _delete(self):
        self.deleted = True
        self.accept()


def DataManager_new_id():
    import uuid
    return uuid.uuid4().hex[:8]


# ── Settings Dialog ───────────────────────────────────────────────────────────
class SettingsDialog(QDialog):
    def __init__(self, data):
        super().__init__()
        self._data = data
        self.setWindowTitle('설정')
        self.setFixedWidth(380)
        self.setStyleSheet(BASE_STYLE)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(24, 24, 24, 20)

        h = QLabel('⚙️ 설정')
        h.setStyleSheet('font-size: 16px; font-weight: 700; color: #1e293b; margin-bottom: 6px;')
        lay.addWidget(h)

        lay.addWidget(label('내 이름'))
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(20)
        lay.addWidget(self.name_edit)

        lay.addWidget(label('내 색상'))
        me = data.get_me()
        self.color_picker = ColorPicker(me['color'] if me else COLORS[5])
        lay.addWidget(self.color_picker)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet('color: #e2e8f0; margin: 8px 0;')
        lay.addWidget(line)

        lay.addWidget(label('위젯 투명도 (0~100, 기본 90)'))
        self.opacity_edit = QLineEdit()
        self.opacity_edit.setPlaceholderText('90')
        lay.addWidget(self.opacity_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton('저장')
        save_btn.setStyleSheet(
            'QPushButton { background: #3b82f6; color: white; }'
            'QPushButton:hover { background: #2563eb; }'
        )
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

        # Prefill
        if me:
            self.name_edit.setText(me['name'])
        opacity = int(data.get_setting('opacity', 90))
        self.opacity_edit.setText(str(opacity))

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setFocus()
            return
        color = self.color_picker.selected_color()
        self._data.setup_me(name, color)
        try:
            op = max(10, min(100, int(self.opacity_edit.text())))
        except ValueError:
            op = 90
        self._data.set_setting('opacity', op)
        self.accept()
