# -*- coding: utf-8 -*-
"""
렌더링 단독 테스트
─────────────────────────────────────────────────────────────
목적: 이 PC 에서 QtWebEngine(내장 브라우저)이 화면을 제대로 그리는지 확인.

실행:  python test_render.py
       (백엔드를 바꿔서 시험하려면)
       set TC_GL=software & python test_render.py
       set TC_GL=desktop  & python test_render.py
       set TC_GL=angle    & python test_render.py

결과 해석:
  · 보라색 배경 + "렌더링 정상!" 글자가 보이면  → 정상 (위젯도 잘 보일 것)
  · 흰 화면만 보이면                         → 그 백엔드는 이 PC 와 안 맞음
                                              (다른 TC_GL 값으로 다시 시도)
화면 아래에 현재 백엔드 이름이 표시됩니다. 잘 보이는 값을 알려주세요.
"""
import os, sys

os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView

GL = os.environ.get("TC_GL", "software").lower()

Aa = Qt.ApplicationAttribute
QApplication.setAttribute(Aa.AA_ShareOpenGLContexts, True)
if GL == "software":
    QApplication.setAttribute(Aa.AA_UseSoftwareOpenGL, True)
elif GL == "desktop":
    QApplication.setAttribute(Aa.AA_UseDesktopOpenGL, True)
elif GL == "angle":
    QApplication.setAttribute(Aa.AA_UseOpenGLES, True)

app = QApplication(sys.argv)

html = """<!doctype html><html><head><meta charset='utf-8'><style>
 html,body{height:100%;margin:0;
   background:linear-gradient(135deg,#6d28d9,#2563eb);
   color:#fff;font-family:sans-serif;
   display:flex;flex-direction:column;align-items:center;justify-content:center}
 h1{font-size:42px;margin:0} p{font-size:20px;opacity:.85}
</style></head><body>
 <h1>✅ 렌더링 정상!</h1>
 <p>이 색깔 화면이 보이면 성공입니다.</p>
 <p>백엔드(TC_GL) = __GL__</p>
</body></html>""".replace("__GL__", GL)

view = QWebEngineView()
view.setWindowTitle("렌더링 테스트 — TC_GL=%s" % GL)
view.resize(640, 460)
view.setHtml(html)
view.show()

sys.exit(app.exec())
