// ─── 상수 ───────────────────────────────────────────────────
const COLORS = [
  '#ef4444','#f97316','#eab308','#22c55e',
  '#14b8a6','#3b82f6','#8b5cf6','#ec4899',
  '#06b6d4','#84cc16','#f59e0b','#6366f1'
];

const KOREAN_MONTHS = ['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월'];

// ─── 상태 ───────────────────────────────────────────────────
let currentYear, currentMonth;   // 현재 보는 월
let events = {};                 // { 'YYYY-MM-DD': [event, ...] }
let teachers = [];               // [{ id, name, color }, ...]
let myId = null;                 // 내 teacher id
let editingEventId = null;       // 편집 중인 이벤트 id (null = 신규)
let fbAvailable = false;         // Firebase 연결 여부
let unsubEvents = null;          // Firestore 리스너 해제 함수
let unsubTeachers = null;

// ─── 유틸 ───────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const today = () => {
  const d = new Date();
  return { y: d.getFullYear(), m: d.getMonth(), d: d.getDate() };
};
const dateKey = (y, m, d) =>
  `${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
const isoToKey = iso => iso.slice(0,10);

function showToast(msg, ms = 2500) {
  const t = $('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), ms);
}

function genId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2,7);
}

// ─── Firebase 초기화 ──────────────────────────────────────
function initFirebase() {
  try {
    const db = window.db;
    if (!db) throw new Error('db not ready');

    // 설정이 플레이스홀더인지 확인
    const app = firebase.app();
    const cfg = app.options;
    if (!cfg.projectId || cfg.projectId.includes('여기에')) throw new Error('placeholder');

    fbAvailable = true;
    subscribeFirestore();
  } catch {
    fbAvailable = false;
    $('firebase-warning').style.display = '';
    loadLocalData();
  }
}

// ─── Firestore 구독 ───────────────────────────────────────
function subscribeFirestore() {
  const db = window.db;

  // Teachers 컬렉션
  unsubTeachers = db.collection('teachers').onSnapshot(snap => {
    teachers = snap.docs.map(d => ({ id: d.id, ...d.data() }));
    renderSidebar();
    renderCalendar();
    renderTeacherSelect();
  });

  // Events 컬렉션
  unsubEvents = db.collection('events').onSnapshot(snap => {
    events = {};
    snap.docs.forEach(d => {
      const ev = { id: d.id, ...d.data() };
      const key = isoToKey(ev.date);
      if (!events[key]) events[key] = [];
      events[key].push(ev);
    });
    renderCalendar();
  });
}

// ─── 로컬 저장 (Firebase 미설정 시) ──────────────────────
function loadLocalData() {
  try {
    teachers = JSON.parse(localStorage.getItem('teachers') || '[]');
    const stored = JSON.parse(localStorage.getItem('events') || '[]');
    events = {};
    stored.forEach(ev => {
      const key = isoToKey(ev.date);
      if (!events[key]) events[key] = [];
      events[key].push(ev);
    });
  } catch { teachers = []; events = {}; }
  renderSidebar();
  renderCalendar();
  renderTeacherSelect();
}

function saveLocalData() {
  localStorage.setItem('teachers', JSON.stringify(teachers));
  const all = Object.values(events).flat();
  localStorage.setItem('events', JSON.stringify(all));
}

// ─── Teacher CRUD ─────────────────────────────────────────
async function saveTeacher(teacher) {
  if (fbAvailable) {
    await window.db.collection('teachers').doc(teacher.id).set(teacher);
  } else {
    const idx = teachers.findIndex(t => t.id === teacher.id);
    if (idx >= 0) teachers[idx] = teacher; else teachers.push(teacher);
    saveLocalData();
    renderSidebar();
    renderTeacherSelect();
  }
}

async function deleteTeacher(id) {
  if (fbAvailable) {
    await window.db.collection('teachers').doc(id).delete();
  } else {
    teachers = teachers.filter(t => t.id !== id);
    saveLocalData();
    renderSidebar();
  }
}

// ─── Event CRUD ───────────────────────────────────────────
async function saveEvent(ev) {
  const key = isoToKey(ev.date);
  if (fbAvailable) {
    await window.db.collection('events').doc(ev.id).set(ev);
  } else {
    if (!events[key]) events[key] = [];
    const idx = events[key].findIndex(e => e.id === ev.id);
    if (idx >= 0) events[key][idx] = ev; else events[key].push(ev);
    saveLocalData();
    renderCalendar();
  }
}

async function deleteEvent(id) {
  if (fbAvailable) {
    await window.db.collection('events').doc(id).delete();
  } else {
    Object.keys(events).forEach(key => {
      events[key] = events[key].filter(e => e.id !== id);
    });
    saveLocalData();
    renderCalendar();
  }
}

// ─── 달력 렌더 ────────────────────────────────────────────
function renderCalendar() {
  const grid = $('calendar-grid');
  const t = today();
  const firstDay = new Date(currentYear, currentMonth, 1).getDay();
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
  const prevDays = new Date(currentYear, currentMonth, 0).getDate();

  $('month-label').textContent = `${currentYear}년 ${KOREAN_MONTHS[currentMonth]}`;

  // 6행 × 7열 = 42칸
  const cells = [];
  for (let i = 0; i < firstDay; i++) {
    const d = prevDays - firstDay + 1 + i;
    cells.push({ year: currentYear, month: currentMonth - 1, day: d, current: false });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({ year: currentYear, month: currentMonth, day: d, current: true });
  }
  while (cells.length < 42) {
    cells.push({ year: currentYear, month: currentMonth + 1, day: cells.length - firstDay - daysInMonth + 1, current: false });
  }

  grid.innerHTML = '';
  cells.forEach(cell => {
    const realDate = new Date(cell.year, cell.month, cell.day);
    const key = dateKey(realDate.getFullYear(), realDate.getMonth(), realDate.getDate());
    const dayEvents = events[key] || [];
    const dow = realDate.getDay();
    const isToday = cell.year === t.y && cell.month === t.m && cell.day === t.d;

    const cellEl = document.createElement('div');
    cellEl.className = [
      'day-cell',
      !cell.current ? 'other-month' : '',
      isToday ? 'today' : '',
      dow === 0 ? 'sunday' : '',
      dow === 6 ? 'saturday' : '',
      dayEvents.length > 0 ? 'has-events' : ''
    ].filter(Boolean).join(' ');

    cellEl.dataset.key = key;
    cellEl.dataset.date = key;

    const numEl = document.createElement('div');
    numEl.className = 'day-number';
    numEl.textContent = cell.day;
    cellEl.appendChild(numEl);

    const evContainer = document.createElement('div');
    evContainer.className = 'events-container';

    const maxShow = 3;
    dayEvents.slice(0, maxShow).forEach(ev => {
      const teacher = teachers.find(t => t.id === ev.teacherId);
      const color = teacher?.color || '#94a3b8';
      const chip = document.createElement('div');
      chip.className = 'event-chip';
      chip.style.background = color;
      chip.textContent = ev.startTime ? `${ev.startTime} ${ev.title}` : ev.title;
      chip.title = ev.title;
      chip.addEventListener('click', e => { e.stopPropagation(); openEditModal(ev); });
      evContainer.appendChild(chip);
    });

    if (dayEvents.length > maxShow) {
      const more = document.createElement('div');
      more.className = 'more-events';
      more.textContent = `+${dayEvents.length - maxShow}개 더`;
      evContainer.appendChild(more);
    }

    cellEl.appendChild(evContainer);
    cellEl.addEventListener('click', () => openAddModal(key));
    grid.appendChild(cellEl);
  });
}

// ─── 사이드바 ─────────────────────────────────────────────
function renderSidebar() {
  const list = $('teacher-list');
  list.innerHTML = '';

  teachers.forEach(t => {
    const item = document.createElement('div');
    item.className = 'teacher-item' + (t.id === myId ? ' me' : '');

    item.innerHTML = `
      <div class="teacher-dot" style="background:${t.color}"></div>
      <span class="teacher-name">${escHtml(t.name)}</span>
      ${t.id === myId ? '<span class="teacher-badge">나</span>' : ''}
      ${t.id !== myId ? `<button class="teacher-delete" data-id="${t.id}" title="삭제">✕</button>` : ''}
    `;

    item.querySelector('.teacher-delete')?.addEventListener('click', e => {
      e.stopPropagation();
      if (confirm(`"${t.name}" 선생님을 목록에서 삭제할까요?`)) deleteTeacher(t.id);
    });

    list.appendChild(item);
  });
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── Teacher Select ───────────────────────────────────────
function renderTeacherSelect() {
  const sel = $('ef-teacher');
  sel.innerHTML = '';
  teachers.forEach(t => {
    const opt = document.createElement('option');
    opt.value = t.id;
    opt.textContent = t.name;
    if (t.id === myId) opt.selected = true;
    sel.appendChild(opt);
  });
}

// ─── 모달 ─────────────────────────────────────────────────
function openAddModal(dateStr) {
  editingEventId = null;
  $('event-modal-title').textContent = '일정 추가';
  $('ef-title').value = '';
  $('ef-date').value = dateStr;
  $('ef-start').value = '';
  $('ef-end').value = '';
  $('ef-desc').value = '';
  renderTeacherSelect();
  $('ef-delete').classList.add('hidden');
  showModal('event-modal');
  setTimeout(() => $('ef-title').focus(), 100);
}

function openEditModal(ev) {
  editingEventId = ev.id;
  $('event-modal-title').textContent = '일정 수정';
  $('ef-title').value = ev.title;
  $('ef-date').value = isoToKey(ev.date);
  $('ef-start').value = ev.startTime || '';
  $('ef-end').value = ev.endTime || '';
  $('ef-desc').value = ev.description || '';
  renderTeacherSelect();
  $('ef-teacher').value = ev.teacherId;
  $('ef-delete').classList.remove('hidden');
  showModal('event-modal');
}

function showModal(id) {
  $('modal-overlay').classList.remove('hidden');
  $(id).classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeModal(id) {
  if (id) $(id).classList.add('hidden');
  else {
    $('event-modal').classList.add('hidden');
    $('my-info-modal').classList.add('hidden');
  }
  $('modal-overlay').classList.add('hidden');
  document.body.style.overflow = '';
}

// ─── 이벤트 폼 제출 ──────────────────────────────────────
$('event-form').addEventListener('submit', async e => {
  e.preventDefault();
  const title = $('ef-title').value.trim();
  if (!title) return;

  const ev = {
    id: editingEventId || genId(),
    title,
    date: $('ef-date').value,
    startTime: $('ef-start').value,
    endTime: $('ef-end').value,
    description: $('ef-desc').value.trim(),
    teacherId: $('ef-teacher').value,
    createdAt: editingEventId ? undefined : new Date().toISOString()
  };
  if (editingEventId) delete ev.createdAt;

  await saveEvent(ev);
  closeModal('event-modal');
  showToast(editingEventId ? '일정이 수정되었습니다.' : '일정이 추가되었습니다.');
});

$('ef-delete').addEventListener('click', async () => {
  if (!editingEventId) return;
  if (!confirm('이 일정을 삭제할까요?')) return;
  await deleteEvent(editingEventId);
  closeModal('event-modal');
  showToast('일정이 삭제되었습니다.');
});

// ─── 내 정보 모달 ─────────────────────────────────────────
function openMyInfoModal() {
  const me = teachers.find(t => t.id === myId);
  if (!me) return;
  $('mi-name').value = me.name;
  renderColorPicker('mi-color-picker', me.color, (c) => {});
  showModal('my-info-modal');
}

$('my-info-btn').addEventListener('click', openMyInfoModal);
$('close-my-info-modal').addEventListener('click', () => closeModal('my-info-modal'));

$('mi-save-btn').addEventListener('click', async () => {
  const name = $('mi-name').value.trim();
  if (!name) return showToast('이름을 입력해 주세요.');
  const color = document.querySelector('#mi-color-picker .color-swatch.selected')?.dataset.color;
  if (!color) return showToast('색상을 선택해 주세요.');
  const me = teachers.find(t => t.id === myId) || { id: myId };
  me.name = name;
  me.color = color;
  localStorage.setItem('myId', myId);
  localStorage.setItem('myName', name);
  localStorage.setItem('myColor', color);
  await saveTeacher(me);
  closeModal('my-info-modal');
  showToast('내 정보가 저장되었습니다.');
});

// ─── 색상 선택기 ──────────────────────────────────────────
function renderColorPicker(containerId, selected, onChange) {
  const container = $(containerId);
  container.innerHTML = '';
  COLORS.forEach(c => {
    const sw = document.createElement('div');
    sw.className = 'color-swatch' + (c === selected ? ' selected' : '');
    sw.style.background = c;
    sw.dataset.color = c;
    sw.addEventListener('click', () => {
      container.querySelectorAll('.color-swatch').forEach(s => s.classList.remove('selected'));
      sw.classList.add('selected');
      onChange(c);
    });
    container.appendChild(sw);
  });
}

// ─── 최초 설정 ────────────────────────────────────────────
function initSetupScreen() {
  renderColorPicker('setup-color-picker', COLORS[5], () => {});

  $('setup-save-btn').addEventListener('click', async () => {
    const name = $('setup-name').value.trim();
    if (!name) return showToast('이름을 입력해 주세요.');
    const color = document.querySelector('#setup-color-picker .color-swatch.selected')?.dataset.color;
    if (!color) return showToast('색상을 선택해 주세요.');

    myId = genId();
    localStorage.setItem('myId', myId);
    localStorage.setItem('myName', name);
    localStorage.setItem('myColor', color);

    const teacher = { id: myId, name, color };
    await saveTeacher(teacher);

    $('setup-screen').classList.add('hidden');
    showToast(`${name} 선생님, 환영합니다! 🎉`);
  });
}

// ─── 사이드바 토글 (모바일) ───────────────────────────────
$('sidebar-toggle').addEventListener('click', () => {
  const sb = $('sidebar');
  sb.classList.toggle('open');
});

$('modal-overlay').addEventListener('click', () => {
  closeModal();
  $('sidebar').classList.remove('open');
});

// ─── 월 탐색 ──────────────────────────────────────────────
$('prev-month').addEventListener('click', () => {
  currentMonth--;
  if (currentMonth < 0) { currentMonth = 11; currentYear--; }
  renderCalendar();
});

$('next-month').addEventListener('click', () => {
  currentMonth++;
  if (currentMonth > 11) { currentMonth = 0; currentYear++; }
  renderCalendar();
});

$('today-btn').addEventListener('click', () => {
  const t = today();
  currentYear = t.y;
  currentMonth = t.m;
  renderCalendar();
});

$('close-event-modal').addEventListener('click', () => closeModal('event-modal'));

// ─── 키보드 단축키 ────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

// ─── 앱 시작 ──────────────────────────────────────────────
function start() {
  const t = today();
  currentYear = t.y;
  currentMonth = t.m;

  // 서비스 워커 등록 (PWA)
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js').catch(() => {});
  }

  // 기존 내 ID 확인
  myId = localStorage.getItem('myId');

  if (!myId) {
    // 최초 실행 → 설정 화면
    initSetupScreen();
    initFirebase();
  } else {
    // 재방문 → 바로 시작
    $('setup-screen').classList.add('hidden');
    initFirebase();
  }
}

start();
