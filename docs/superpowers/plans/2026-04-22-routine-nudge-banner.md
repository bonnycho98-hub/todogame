# 루틴 유도 배너 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 대시보드 Hero 카드 아래에 루틴 미완료 시 긴급 배너를 표시하고, 모두 완료하면 칭찬 배너로 교체 후 3초 뒤 사라지게 한다.

**Architecture:** 백엔드 변경 없이 프론트엔드 3개 파일만 수정. `loadDashboard()` 호출 시 `routine_quests` 데이터와 `streak`을 읽어 배너 상태를 계산하고 DOM을 업데이트한다. 완료 배너는 3초 후 CSS transition으로 fade-out한다.

**Tech Stack:** Vanilla JS, CSS (기존 style.css), HTML

---

### Task 1: HTML에 배너 요소 추가

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1: 배너 요소를 Hero 카드 아래에 삽입**

`static/index.html`에서 Hero 카드 닫는 태그(`</div>`) 바로 뒤, 루틴 섹션 레이블(`<div class="section-label">`) 바로 앞에 아래 HTML을 추가한다.

현재 해당 위치 (약 49~51번째 줄):
```html
    </div>

    <!-- 루틴 섹션 -->
    <div class="section-label">
```

추가 후:
```html
    </div>

    <!-- 루틴 유도 배너 -->
    <div id="routine-nudge-banner" style="display:none"></div>

    <!-- 루틴 섹션 -->
    <div class="section-label">
```

- [ ] **Step 2: 커밋**

```bash
git add static/index.html
git commit -m "feat: add routine nudge banner placeholder"
```

---

### Task 2: CSS 스타일 추가

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1: 배너 스타일 추가**

`static/style.css` 파일 끝에 아래를 추가한다.

```css
/* ── 루틴 유도 배너 ────────────────────────────────────── */
#routine-nudge-banner {
  margin: 8px 0 4px;
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: opacity 0.6s ease;
}
#routine-nudge-banner.warn {
  background: linear-gradient(135deg, #c1121f, #e63946);
  box-shadow: 0 4px 16px rgba(230, 57, 70, 0.35);
}
#routine-nudge-banner.done {
  background: linear-gradient(135deg, #2d6a4f, #40916c);
  box-shadow: 0 4px 16px rgba(64, 145, 108, 0.35);
}
#routine-nudge-banner.fade-out {
  opacity: 0;
}
.nudge-icon {
  font-size: 24px;
  flex-shrink: 0;
}
.nudge-text {
  flex: 1;
}
.nudge-title {
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 2px;
}
.nudge-sub {
  color: rgba(255, 255, 255, 0.8);
  font-size: 11px;
}
.nudge-action {
  background: rgba(255, 255, 255, 0.25);
  border-radius: 8px;
  padding: 6px 12px;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
  border: none;
}
```

- [ ] **Step 2: 커밋**

```bash
git add static/style.css
git commit -m "feat: add routine nudge banner styles"
```

---

### Task 3: JS 배너 렌더 로직 추가

**Files:**
- Modify: `static/app.js`

- [ ] **Step 1: `renderRoutineNudgeBanner` 함수 추가**

`static/app.js`에서 `loadDashboard` 함수 바로 위(약 187번째 줄)에 아래 함수를 추가한다.

```js
function renderRoutineNudgeBanner(routines, streak) {
  const banner = document.getElementById('routine-nudge-banner');
  if (!banner) return;

  const remaining = routines.filter(q => !q.is_all_done_today).length;
  const total = routines.length;

  if (total === 0) {
    banner.style.display = 'none';
    return;
  }

  if (remaining > 0) {
    banner.className = 'warn';
    banner.style.display = 'flex';
    banner.style.opacity = '1';
    banner.innerHTML = `
      <div class="nudge-icon">🔥</div>
      <div class="nudge-text">
        <div class="nudge-title">오늘 루틴 ${remaining}개 남았어요</div>
        <div class="nudge-sub">스트릭 ${streak}일 — 오늘 놓치면 리셋돼요!</div>
      </div>
      <button class="nudge-action" onclick="document.getElementById('routine-list').scrollIntoView({behavior:'smooth'})">지금 하기 →</button>
    `;
  } else {
    banner.className = 'done';
    banner.style.display = 'flex';
    banner.style.opacity = '1';
    banner.innerHTML = `
      <div class="nudge-icon">🎉</div>
      <div class="nudge-text">
        <div class="nudge-title">오늘 루틴 완료!</div>
        <div class="nudge-sub">스트릭 ${streak}일 달성 · 잘했어요 ✨</div>
      </div>
    `;
    setTimeout(() => {
      banner.classList.add('fade-out');
      setTimeout(() => { banner.style.display = 'none'; }, 600);
    }, 3000);
  }
}
```

- [ ] **Step 2: `loadDashboard`에서 배너 함수 호출**

`loadDashboard` 함수 내부에서 루틴 배지를 업데이트하는 코드(약 198번째 줄) 바로 뒤에 배너 호출을 추가한다.

현재 코드:
```js
  const routineDone = routines.filter(q => q.is_all_done_today).length;
  const badge = document.getElementById('routine-badge');
  if (badge) badge.textContent = `${routineDone} / ${routines.length}`;
```

변경 후:
```js
  const routineDone = routines.filter(q => q.is_all_done_today).length;
  const badge = document.getElementById('routine-badge');
  if (badge) badge.textContent = `${routineDone} / ${routines.length}`;
  renderRoutineNudgeBanner(routines, data.streak || 0);
```

- [ ] **Step 3: 커밋**

```bash
git add static/app.js
git commit -m "feat: add routine nudge banner render logic"
```

---

### Task 4: 수동 검증

**Files:** 없음 (검증만)

- [ ] **Step 1: 서버 실행 및 대시보드 열기**

```bash
cd /Users/bonny/Dev/todogame
uvicorn app.main:app --reload
```

브라우저에서 `http://localhost:8000` 열기.

- [ ] **Step 2: 미완료 상태 확인**

루틴이 1개 이상 미완료인 경우:
- Hero 카드 아래에 빨간 배너가 표시되어야 함
- "오늘 루틴 N개 남았어요" 텍스트에 실제 미완료 개수가 표시되어야 함
- 스트릭 숫자가 현재 스트릭과 일치해야 함
- "지금 하기 →" 버튼 클릭 시 루틴 섹션으로 스크롤돼야 함

- [ ] **Step 3: 완료 상태 확인**

루틴을 모두 완료한 후:
- 배너가 초록색으로 바뀌어야 함
- "오늘 루틴 완료!" 텍스트가 표시되어야 함
- 3초 후 배너가 서서히 사라져야 함

- [ ] **Step 4: 루틴 없을 때 확인**

루틴 퀘스트가 0개인 경우 배너가 표시되지 않아야 함.

- [ ] **Step 5: 최종 커밋**

모든 검증 통과 후:
```bash
git add .
git commit -m "feat: routine nudge banner — complete implementation"
```
