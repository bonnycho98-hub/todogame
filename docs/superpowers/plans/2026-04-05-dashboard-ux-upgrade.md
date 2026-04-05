# Dashboard UX Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 대시보드를 개선해 진행 중인 퀘스트 목록(클릭 시 서브태스크 모달), NPC 니즈 말풍선 + 완료 버튼, 행복 레벨 난이도 하향을 구현한다.

**Architecture:** 기존 FastAPI SPA 구조 유지. 백엔드는 Need 모델에 is_archived 추가, 대시보드 API에 NPC needs 포함. 프론트엔드는 대시보드 렌더링 함수 교체 + 새 퀘스트 상세 모달 추가.

**Tech Stack:** FastAPI, SQLAlchemy (Pydantic v1), Alembic, SQLite(test)/PostgreSQL(prod), Vanilla JS SPA, Courier New 레트로 CSS

---

## File Map

| 파일 | 변경 유형 | 역할 |
|------|----------|------|
| `app/models.py` | Modify | Need.is_archived 컬럼 추가 |
| `alembic/versions/b3f9a1c2d4e5_add_need_is_archived.py` | Create | needs 테이블 컬럼 추가 마이그레이션 |
| `app/schemas.py` | Modify | NeedOut에 is_archived, NPCSummary에 needs, NeedCompleteOut 추가 |
| `app/routers/needs.py` | Modify | complete 엔드포인트 추가, list 필터링 |
| `app/routers/dashboard.py` | Modify | NPC별 활성 needs 포함 |
| `app/services/happiness.py` | Modify | POINTS_PER_LEVEL 100 → 30 |
| `tests/test_happiness.py` | Modify | POINTS_PER_LEVEL 변경에 맞게 수치 업데이트 |
| `tests/test_api.py` | Modify | need complete + dashboard needs 테스트 추가 |
| `static/index.html` | Modify | 퀘스트 상세 모달 추가 |
| `static/app.js` | Modify | 대시보드 퀘스트/NPC 렌더링 교체, 새 함수 추가 |

---

### Task 1: Need 모델에 is_archived 추가 + Alembic 마이그레이션

**Files:**
- Modify: `app/models.py`
- Create: `alembic/versions/b3f9a1c2d4e5_add_need_is_archived.py`

- [ ] **Step 1: 테스트 작성 — Need 생성 시 is_archived=False**

`tests/test_api.py` 파일 끝에 추가:

```python
def test_need_is_not_archived_by_default(client):
    npc = client.post("/api/npcs", json={"name": "테스트NPC", "relation_type": "기타"}).json()
    need = client.post("/api/needs", json={"npc_id": npc["id"], "title": "테스트 니즈"}).json()
    assert need["is_archived"] is False
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/bonny/Dev/todogame
pytest tests/test_api.py::test_need_is_not_archived_by_default -v
```

Expected: FAIL — `KeyError: 'is_archived'` 또는 assertion error

- [ ] **Step 3: models.py — Need에 is_archived 추가**

`app/models.py` 의 Need 클래스에서 `created_at` 줄 바로 앞에 추가:

```python
class Need(Base):
    __tablename__ = "needs"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    npc_id = Column(Uuid(as_uuid=True), ForeignKey("npcs.id", ondelete="CASCADE"), nullable=True)
    title = Column(Text, nullable=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    npc = relationship("NPC", back_populates="needs")
    quests = relationship("Quest", back_populates="need", cascade="all, delete-orphan")
```

- [ ] **Step 4: schemas.py — NeedOut에 is_archived 추가**

`app/schemas.py`의 `NeedOut` 클래스:

```python
class NeedOut(BaseModel):
    id: UUID
    npc_id: Optional[UUID]
    title: str
    is_archived: bool = False
    created_at: datetime

    class Config:
        orm_mode = True
```

- [ ] **Step 5: 테스트 통과 확인 (conftest가 테이블 재생성하므로 마이그레이션 없이 가능)**

```bash
pytest tests/test_api.py::test_need_is_not_archived_by_default -v
```

Expected: PASS

- [ ] **Step 6: Alembic 마이그레이션 파일 생성**

파일 생성: `alembic/versions/b3f9a1c2d4e5_add_need_is_archived.py`

```python
"""add need is_archived

Revision ID: b3f9a1c2d4e5
Revises: 6c6edb007ef7
Create Date: 2026-04-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b3f9a1c2d4e5'
down_revision = '6c6edb007ef7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'needs',
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade():
    op.drop_column('needs', 'is_archived')
```

- [ ] **Step 7: 커밋**

```bash
git add app/models.py app/schemas.py alembic/versions/b3f9a1c2d4e5_add_need_is_archived.py tests/test_api.py
git commit -m "feat: add is_archived to Need model + migration"
```

---

### Task 2: Need 완료 엔드포인트 + list 필터링

**Files:**
- Modify: `app/schemas.py`
- Modify: `app/routers/needs.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: 테스트 작성 — 완료 처리 + 목록에서 제외**

`tests/test_api.py` 끝에 추가:

```python
def test_complete_need_archives_it(client):
    npc = client.post("/api/npcs", json={"name": "니즈완료테스트NPC", "relation_type": "기타"}).json()
    need = client.post("/api/needs", json={"npc_id": npc["id"], "title": "완료할 니즈"}).json()

    res = client.post(f"/api/needs/{need['id']}/complete")
    assert res.status_code == 200
    assert res.json()["done"] is True

    # 목록에서 제외됐는지 확인
    needs_list = client.get(f"/api/needs?npc_id={npc['id']}").json()
    assert not any(n["id"] == need["id"] for n in needs_list)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_api.py::test_complete_need_archives_it -v
```

Expected: FAIL — 404 (엔드포인트 없음)

- [ ] **Step 3: schemas.py — NeedCompleteOut 추가**

`app/schemas.py`의 `NeedUpdate` 클래스 아래에 추가:

```python
class NeedCompleteOut(BaseModel):
    done: bool
```

- [ ] **Step 4: routers/needs.py — complete 엔드포인트 추가 + list 필터링**

`app/routers/needs.py` 전체를 다음으로 교체:

```python
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/needs", tags=["needs"])


@router.get("", response_model=list[schemas.NeedOut])
def list_needs(npc_id: str = None, db: Session = Depends(get_db)):
    q = db.query(models.Need).filter_by(is_archived=False)
    if npc_id is not None:
        q = q.filter(models.Need.npc_id == npc_id)
    else:
        q = q.filter(models.Need.npc_id.is_(None))
    return q.order_by(models.Need.created_at).all()


@router.post("", response_model=schemas.NeedOut, status_code=201)
def create_need(body: schemas.NeedCreate, db: Session = Depends(get_db)):
    need = models.Need(npc_id=body.npc_id, title=body.title)
    db.add(need)
    db.commit()
    db.refresh(need)
    return need


@router.post("/{need_id}/complete", response_model=schemas.NeedCompleteOut)
def complete_need(need_id: UUID, db: Session = Depends(get_db)):
    need = db.get(models.Need, need_id)
    if not need:
        raise HTTPException(404)
    need.is_archived = True
    db.commit()
    return {"done": True}


@router.patch("/{need_id}", response_model=schemas.NeedOut)
def update_need(need_id: UUID, body: schemas.NeedUpdate, db: Session = Depends(get_db)):
    need = db.get(models.Need, need_id)
    if not need:
        raise HTTPException(404)
    need.title = body.title
    db.commit()
    db.refresh(need)
    return need


@router.delete("/{need_id}", status_code=204)
def delete_need(need_id: UUID, db: Session = Depends(get_db)):
    need = db.get(models.Need, need_id)
    if not need:
        raise HTTPException(404)
    db.delete(need)
    db.commit()
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_api.py::test_complete_need_archives_it -v
```

Expected: PASS

- [ ] **Step 6: 전체 테스트 통과 확인**

```bash
pytest tests/ -v
```

Expected: 모두 PASS

- [ ] **Step 7: 커밋**

```bash
git add app/schemas.py app/routers/needs.py tests/test_api.py
git commit -m "feat: add need complete endpoint and filter archived needs"
```

---

### Task 3: 행복 레벨 난이도 하향 (POINTS_PER_LEVEL 30)

**Files:**
- Modify: `app/services/happiness.py`
- Modify: `tests/test_happiness.py`

- [ ] **Step 1: 기존 테스트들이 현재 통과하는지 확인**

```bash
pytest tests/test_happiness.py -v
```

Expected: 모두 PASS (기준선 확인)

- [ ] **Step 2: happiness.py 수정 — POINTS_PER_LEVEL 변경**

`app/services/happiness.py`의 `POINTS_PER_LEVEL = 100` 줄을:

```python
POINTS_PER_LEVEL = 30
```

- [ ] **Step 3: test_happiness.py 수정 — 수치를 POINTS_PER_LEVEL 기준으로 표현**

`tests/test_happiness.py` 전체를 다음으로 교체:

```python
from app.services.happiness import calculate_happiness, POINTS_PER_LEVEL


def test_zero_intimacy_is_level_1():
    result = calculate_happiness(self_total=0, others_totals=[])
    assert result["level"] == 1
    assert result["progress"] == 0


def test_level_increases_with_score():
    # POINTS_PER_LEVEL만큼 score → lv.2
    total = POINTS_PER_LEVEL
    result = calculate_happiness(self_total=total, others_totals=[total])
    assert result["level"] == 2


def test_progress_within_level():
    # 레벨의 절반 → progress=0.5
    half = POINTS_PER_LEVEL // 2
    result = calculate_happiness(self_total=half, others_totals=[half])
    assert result["level"] == 1
    assert abs(result["progress"] - 0.5) < 0.01


def test_others_avg_used_not_sum():
    # 두 NPC 각각 같은 값 → others_avg 동일 → 레벨 동일
    total = POINTS_PER_LEVEL
    result_one = calculate_happiness(self_total=total, others_totals=[total])
    result_two = calculate_happiness(self_total=total, others_totals=[total, total])
    assert result_one["level"] == result_two["level"]


def test_pixel_blocks():
    # 레벨의 60% → 6 블록
    pts = int(POINTS_PER_LEVEL * 0.6)
    result = calculate_happiness(self_total=pts, others_totals=[pts])
    assert result["filled_blocks"] == 6
    assert result["total_blocks"] == 10
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_happiness.py -v
```

Expected: 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add app/services/happiness.py tests/test_happiness.py
git commit -m "feat: lower happiness level difficulty (POINTS_PER_LEVEL 100 -> 30)"
```

---

### Task 4: 대시보드 API에 NPC needs 포함

**Files:**
- Modify: `app/schemas.py`
- Modify: `app/routers/dashboard.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: 테스트 작성 — 대시보드 NPC에 needs 포함**

`tests/test_api.py` 끝에 추가:

```python
def test_dashboard_npc_includes_needs(client):
    npc = client.post("/api/npcs", json={"name": "대시보드테스트NPC", "relation_type": "기타"}).json()
    client.post("/api/needs", json={"npc_id": npc["id"], "title": "대시보드용 니즈"})

    res = client.get("/api/dashboard")
    assert res.status_code == 200
    dashboard = res.json()

    npc_data = next((n for n in dashboard["npcs"] if n["name"] == "대시보드테스트NPC"), None)
    assert npc_data is not None
    assert "needs" in npc_data
    assert any(n["title"] == "대시보드용 니즈" for n in npc_data["needs"])
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_api.py::test_dashboard_npc_includes_needs -v
```

Expected: FAIL — `needs` 키 없음

- [ ] **Step 3: schemas.py — NPCSummary에 needs 추가**

`app/schemas.py`의 `NPCSummary` 클래스:

```python
class NPCSummary(BaseModel):
    id: UUID
    name: str
    sprite: str
    color: str
    intimacy_total: int
    needs: List[NeedOut] = []
```

- [ ] **Step 4: routers/dashboard.py — NPC 조회 시 needs 포함**

`app/routers/dashboard.py` 전체를 다음으로 교체:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
from app.database import get_db
from app import models, schemas
from app.services.happiness import calculate_happiness
from app.services.quest import is_quest_active_today, is_subtask_done_today, _get_intimacy_total

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardOut)
def get_dashboard(db: Session = Depends(get_db)):
    today = date.today()

    # 오늘의 퀘스트 (archived 제외)
    all_quests = db.query(models.Quest).filter_by(is_archived=False).all()
    today_quests = []
    for q in all_quests:
        if is_quest_active_today(q, today):
            out = schemas.QuestOut.from_orm(q)
            out.subtasks = [
                schemas.SubtaskOut(
                    id=st.id, title=st.title, order=st.order,
                    is_done_today=is_subtask_done_today(db, st, today),
                )
                for st in q.subtasks
            ]
            today_quests.append(out)

    # NPC 목록 + 친밀도 + 활성 needs
    npcs = db.query(models.NPC).all()
    npc_summaries = []
    others_totals = []
    for npc in npcs:
        total = _get_intimacy_total(db, npc.id)
        others_totals.append(total)
        active_needs = db.query(models.Need).filter_by(
            npc_id=npc.id, is_archived=False
        ).order_by(models.Need.created_at).all()
        npc_summaries.append(schemas.NPCSummary(
            id=npc.id, name=npc.name,
            sprite=npc.sprite, color=npc.color,
            intimacy_total=total,
            needs=[schemas.NeedOut.from_orm(n) for n in active_needs],
        ))

    # 행복 레벨
    self_total = _get_intimacy_total(db, None)
    happiness = calculate_happiness(self_total, others_totals)

    # 미수령 레벨 보상
    pending_reward = db.query(models.LevelReward).filter_by(
        level=happiness["level"], is_claimed=False
    ).first()

    return schemas.DashboardOut(
        today_quests=today_quests,
        npcs=npc_summaries,
        happiness=happiness,
        pending_level_reward=pending_reward,
    )
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_api.py::test_dashboard_npc_includes_needs -v
```

Expected: PASS

- [ ] **Step 6: 전체 테스트 통과 확인**

```bash
pytest tests/ -v
```

Expected: 모두 PASS

- [ ] **Step 7: 커밋**

```bash
git add app/schemas.py app/routers/dashboard.py tests/test_api.py
git commit -m "feat: include NPC active needs in dashboard API response"
```

---

### Task 5: 프론트엔드 — 퀘스트 상세 모달 + 대시보드 퀘스트 섹션

**Files:**
- Modify: `static/index.html`
- Modify: `static/app.js`

- [ ] **Step 1: index.html — 퀘스트 상세 모달 추가**

`static/index.html`에서 `<!-- 레벨업 팝업 -->` 블록 바로 앞에 다음을 추가:

```html
<!-- 퀘스트 상세 모달 -->
<div class="modal-overlay" id="modal-quest-detail">
  <div class="modal">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
      <div>
        <div id="quest-detail-type" style="color:var(--muted);font-size:10px;letter-spacing:1px;margin-bottom:3px"></div>
        <h2 id="quest-detail-title" style="color:var(--yellow)"></h2>
      </div>
      <button class="btn btn-sm" onclick="closeModal('modal-quest-detail')">[ X ]</button>
    </div>
    <div id="quest-detail-subtasks" style="margin-bottom:16px"></div>
    <button class="btn btn-primary" id="btn-complete-quest-modal" style="width:100%">[ 퀘스트 전체 완료 ]</button>
  </div>
</div>
```

- [ ] **Step 2: app.js — loadDashboard 퀘스트 섹션 교체**

`app.js`의 `loadDashboard` 함수에서 아래 블록을 찾아 교체한다.

찾을 블록 (line 66-88 부근):
```javascript
  // 오늘의 퀘스트
  const todayEl = document.getElementById('today-list');
  if (!data.today_quests.length) {
    todayEl.innerHTML = '<span style="color:var(--muted)">오늘 퀘스트 없음</span>';
  } else {
    todayEl.innerHTML = data.today_quests.map(q => {
      const doneCount = q.subtasks.filter(s => s.is_done_today).length;
      return `
        <div style="margin-bottom:10px">
          <div style="color:var(--text);margin-bottom:4px">
            ${q.quest_type === 'daily' ? '◆' : '◇'} ${q.title}
            <span style="color:var(--muted);font-size:10px">${doneCount}/${q.subtasks.length}</span>
          </div>
          ${q.subtasks.map(st => `
            <div class="check-item${st.is_done_today ? ' done' : ''}">
              <input type="checkbox" ${st.is_done_today ? 'checked' : ''}
                onchange="completeSubtask('${st.id}', this)"
                ${st.is_done_today ? 'disabled' : ''}>
              <label>${st.title}</label>
            </div>
          `).join('')}
        </div>
      `;
    }).join('');
  }
```

교체할 내용:
```javascript
  // 오늘의 퀘스트
  const todayEl = document.getElementById('today-list');
  if (!data.today_quests.length) {
    todayEl.innerHTML = '<span style="color:var(--muted)">오늘 퀘스트 없음</span>';
  } else {
    todayEl.innerHTML = data.today_quests.map(q => {
      const doneCount = q.subtasks.filter(s => s.is_done_today).length;
      const total = q.subtasks.length;
      const progress = total > 0 ? `[${doneCount}/${total}]` : '[–]';
      const hasProgress = doneCount > 0 && doneCount < total;
      const borderStyle = hasProgress ? 'border-color:var(--red)' : '';
      const typeLabel = q.quest_type === 'daily' ? 'DAILY' : 'QUEST';
      return `
        <div onclick="openQuestModal('${q.id}')"
             style="display:flex;align-items:center;gap:10px;padding:7px 10px;margin-bottom:6px;
                    background:var(--bg3);border:1px solid var(--border);border-radius:3px;cursor:pointer;${borderStyle}">
          <span style="color:var(--muted);font-size:10px;white-space:nowrap">${progress}</span>
          <span style="flex:1">${q.title}</span>
          <span style="color:var(--muted);font-size:10px">${typeLabel}</span>
          <span style="color:var(--muted)">›</span>
        </div>
      `;
    }).join('');
  }
```

- [ ] **Step 3: app.js — openQuestModal, completeSubtaskFromModal, completeQuestFromModal 추가**

`app.js`의 `// ── 모달 헬퍼` 섹션 바로 앞에 다음 함수들을 추가:

```javascript
// ── 퀘스트 상세 모달 ─────────────────────────────────────────────
function openQuestModal(questId) {
  const quest = state.dashboard && state.dashboard.today_quests.find(q => q.id === questId);
  if (!quest) return;

  const typeLabel = quest.quest_type === 'daily' ? 'DAILY QUEST' : 'QUEST';
  const subtasksHtml = quest.subtasks.length
    ? quest.subtasks.map(st => `
        <div class="check-item${st.is_done_today ? ' done' : ''}" style="padding:4px 0">
          <input type="checkbox" ${st.is_done_today ? 'checked disabled' : ''}
            onchange="completeSubtaskFromModal('${st.id}', '${questId}', this)">
          <label>${st.title}</label>
        </div>
      `).join('')
    : '<span style="color:var(--muted);font-size:11px">서브태스크 없음</span>';

  document.getElementById('quest-detail-type').textContent = typeLabel;
  document.getElementById('quest-detail-title').textContent = quest.title;
  document.getElementById('quest-detail-subtasks').innerHTML = subtasksHtml;
  document.getElementById('btn-complete-quest-modal').onclick = () => completeQuestFromModal(questId);
  document.getElementById('modal-quest-detail').classList.add('open');
}

async function completeSubtaskFromModal(subtaskId, questId, checkbox) {
  try {
    const result = await api('POST', `/subtasks/${subtaskId}/complete`);
    if (result.quest_done) {
      closeModal('modal-quest-detail');
      await loadDashboard();
    } else {
      checkbox.disabled = true;
      checkbox.closest('.check-item').classList.add('done');
    }
  } catch (e) {
    checkbox.checked = false;
    alert(e.message);
  }
}

async function completeQuestFromModal(questId) {
  const result = await api('POST', `/quests/${questId}/complete`);
  closeModal('modal-quest-detail');
  await loadDashboard();
}

```

- [ ] **Step 4: 브라우저에서 수동 확인**

앱을 로컬에서 실행하거나 Railway 배포 후:
1. 대시보드 접속 → 퀘스트 목록이 클릭 가능한 행으로 표시됨
2. 진행 중인 퀘스트(1개 이상 완료)는 빨간 테두리로 강조됨
3. 퀘스트 클릭 → 모달이 열리고 서브태스크 목록 표시
4. 서브태스크 체크 → 완료 처리됨
5. `[ 퀘스트 전체 완료 ]` 버튼 클릭 → 완료 처리 후 모달 닫힘

- [ ] **Step 5: 커밋**

```bash
git add static/index.html static/app.js
git commit -m "feat: dashboard quest list with subtask modal"
```

---

### Task 6: 프론트엔드 — NPC 카드 + 니즈 완료

**Files:**
- Modify: `static/app.js`

- [ ] **Step 1: app.js — loadDashboard NPC 섹션 교체**

`app.js`의 `loadDashboard` 함수에서 아래 블록을 찾아 교체한다.

찾을 블록 (line 91-100 부근):
```javascript
  // NPC 목록
  const npcEl = document.getElementById('npc-list');
  npcEl.innerHTML = data.npcs.map(npc => `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
      ${renderSprite(npc.sprite, npc.color)}
      <div>
        <div style="color:var(--text)">${npc.name}</div>
        <div style="color:var(--muted);font-size:10px">친밀도 ${npc.intimacy_total}</div>
      </div>
    </div>
  `).join('') || '<span style="color:var(--muted)">NPC 없음</span>';
```

교체할 내용:
```javascript
  // NPC 목록
  const npcEl = document.getElementById('npc-list');
  npcEl.innerHTML = data.npcs.map(npc => {
    const needsHtml = npc.needs && npc.needs.length
      ? npc.needs.map(n => `
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:5px">
            <span style="color:var(--muted);font-size:10px">▷</span>
            <span style="flex:1;font-size:11px">"${n.title}"</span>
            <button class="btn btn-sm" style="border-color:var(--green);color:var(--green);white-space:nowrap"
              onclick="completeNeed('${n.id}')">완료</button>
          </div>
        `).join('')
      : '<span style="color:var(--muted);font-size:10px">— 니즈 없음 —</span>';
    return `
      <div style="margin-bottom:10px;padding:10px 12px;background:var(--bg3);border:1px solid var(--border);border-radius:3px">
        <div style="display:flex;align-items:flex-start;gap:12px">
          ${renderSprite(npc.sprite, npc.color)}
          <div style="flex:1">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px">
              <span style="color:var(--yellow)">${npc.name}</span>
              <span style="color:var(--muted);font-size:10px">♥ ${npc.intimacy_total}</span>
            </div>
            ${needsHtml}
          </div>
        </div>
      </div>
    `;
  }).join('') || '<span style="color:var(--muted)">NPC 없음</span>';
```

- [ ] **Step 2: app.js — completeNeed 함수 추가**

`completeQuestFromModal` 함수 바로 아래에 추가:

```javascript
async function completeNeed(id) {
  if (!confirm('니즈를 완료 처리할까요?')) return;
  await api('POST', `/needs/${id}/complete`);
  await loadDashboard();
}
```

- [ ] **Step 3: 브라우저에서 수동 확인**

1. 대시보드 접속 → NPC 카드에 ASCII 스프라이트 + 이름 + `♥ 친밀도` 표시
2. NPC 카드에 `▷ "니즈 내용"` + `완료` 버튼 표시
3. `완료` 버튼 클릭 → 확인 후 니즈가 카드에서 사라짐
4. 니즈가 없는 NPC는 `— 니즈 없음 —` 표시

- [ ] **Step 4: 전체 테스트 통과 확인**

```bash
pytest tests/ -v
```

Expected: 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add static/app.js
git commit -m "feat: NPC cards with needs bubbles and complete button on dashboard"
```

---

## 배포

모든 태스크 완료 후 Railway에 푸시하면 자동 배포:

```bash
git push
```

Railway 배포 로그에서 `alembic upgrade head` 가 `b3f9a1c2d4e5` 마이그레이션을 적용하는지 확인.
