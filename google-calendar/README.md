# 선생님 캘린더 (데스크탑 앱)

선생님이 만든 구글 캘린더 + TODO 위젯(`index.html`)을 **그대로** Windows 데스크탑 프로그램으로 띄웁니다.
파이썬(PyQt6 WebEngine)이 내부 브라우저로 `index.html`을 표시하므로 화면과 기능이 웹 버전과 100% 동일합니다.

## 설치 (한 번만)

1. 이 폴더 전체를 Windows PC에 복사
2. **`install.bat` 더블클릭**
   - PyQt6 + PyQt6-WebEngine 자동 설치 (처음엔 몇 분 걸림)
   - Windows 시작프로그램에 자동 등록
   - 캘린더 바로 실행

이후 컴퓨터를 켤 때마다 캘린더가 자동으로 뜹니다.

## 파일 설명

| 파일 | 용도 |
|------|------|
| `index.html` | 실제 캘린더 화면 (수정하면 앱에도 그대로 반영) |
| `desktop_app.py` | index.html을 데스크탑 창으로 띄우는 파이썬 런처 |
| `install.bat` | **처음 한 번** 실행 → 설치 + 시작프로그램 등록 |
| `start_silent.vbs` | 수동으로 켤 때 더블클릭 (검은 창 없음) |
| `uninstall.bat` | 시작프로그램에서 제거 |

## 창 조작

- 상단 바를 **드래그**해서 위치 이동
- 상단 바 **📌** : 항상 위에 고정 on/off
- 상단 바 **—** : 트레이로 숨기기 (오른쪽 아래 📅 아이콘 클릭하면 다시 표시)
- 우하단 모서리를 **드래그**하면 크기 조절

## ⚠️ 구글 로그인 관련 (중요)

데스크탑 앱은 `http://localhost:8765` 주소로 페이지를 띄웁니다.
구글 로그인이 작동하려면 **구글 클라우드 콘솔**에서 이 주소를 허용해야 합니다.

1. https://console.cloud.google.com/apis/credentials 접속
2. 사용 중인 OAuth 클라이언트 ID 클릭
3. **승인된 자바스크립트 원본(Authorized JavaScript origins)** 에 아래 추가:
   - `http://localhost:8765`
   - `http://localhost:8766`
   - `http://localhost:8767`
4. 저장 후 몇 분 기다렸다가 앱에서 로그인

> TODO 목록은 로그인 없이도 바로 사용 가능합니다 (이 PC에 저장됨).
