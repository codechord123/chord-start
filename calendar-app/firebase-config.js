// ============================================================
//  Firebase 설정 방법:
//  1. https://console.firebase.google.com 접속
//  2. 새 프로젝트 생성 (예: "teacher-calendar")
//  3. 웹 앱 추가 (</> 아이콘 클릭)
//  4. 앱 등록 후 아래 firebaseConfig 값을 복사해서 붙여넣기
//  5. Firestore Database 생성 (테스트 모드로 시작)
// ============================================================

const firebaseConfig = {
  apiKey: "여기에-API키-입력",
  authDomain: "여기에-authDomain-입력",
  projectId: "여기에-projectId-입력",
  storageBucket: "여기에-storageBucket-입력",
  messagingSenderId: "여기에-messagingSenderId-입력",
  appId: "여기에-appId-입력"
};

// Firebase 초기화
firebase.initializeApp(firebaseConfig);
const db = firebase.firestore();
window.db = db;
