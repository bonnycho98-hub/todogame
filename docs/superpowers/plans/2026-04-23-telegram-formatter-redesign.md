# Telegram Formatter Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `app/telegram/formatter.py`의 메시지 포맷을 개선한다 — 철학 문구 고정 추가, 체크박스 기호 변경, ? NPC 버그 수정, 서브태스크 없는 퀘스트 중복 제거, 전반 어조 변경.

**Architecture:** 단일 파일(`formatter.py`) 수정. `format_briefing`, `format_evening_briefing`, `format_status`, `_happiness_line` 함수를 모두 업데이트한다. 퀘스트 그룹핑 로직을 변경해 NPC가 없는 퀘스트는 "나를 사랑하기" 섹션으로, NPC가 있는 퀘스트는 NPC 이름을 헤더로 표시한다.

**Tech Stack:** Python 3.11, SQLAlchemy, python-telegram-bot, MarkdownV2

---

## 파일 구조

- Modify: `app/telegram/formatter.py` — 포맷 함수 전체 수정
- Create: `tests/test_formatter.py` — 포맷터 유닛 테스트

---

### Task 1: 테스트 파일 작성 및 실패 확인

**Files:**
- Create: `tests/test_formatter.py`

- [ ] **Step 1: 테스트 파일 작성**

```python
import pytest
from unittest.mock import MagicMock, patch
from datetime import date


def make_subtask(title, done=False):
    st = MagicMock()
    st.id = "st-1"
    st.title = title
    return st, done


def make_quest(title, subtasks=None, npc_name=None):
    """npc_name=None → 나 자신 퀘스트 (NPC 없음)"""
    q = MagicMock()
    q.title = title
    q.need_id = "need-1"
    q.is_archived = False
    if npc_name:
        npc = MagicMock()
        npc.name = npc_name
        q.need.npc = npc
    else:
        q.need.npc = None
    q.subtasks = subtasks or []
    return q


# ── _happiness_line ──────────────────────────────────────────

def test_happiness_line_format():
    """lv.N ■■□□ 형식으로 반환"""
    from app.telegram.formatter import _happiness_line
    db = MagicMock()
    with patch("app.telegram.formatter._get_intimacy_total", return_value=0), \
         patch("app.telegram.formatter.calculate_happiness", return_value={
             "level": 3, "filled_blocks": 7, "total_blocks": 10, "progress": 0.7
         }):
        result = _happiness_line(db)
    assert result == r"lv\.3 ■■■■■■■□□□"


# ── format_status ────────────────────────────────────────────

def test_format_status_header():
    """헤더가 '지금 너의 상태야.' 로 시작"""
    from app.telegram.formatter import format_status
    db = MagicMock()
    db.query.return_value.all.return_value = []
    with patch("app.telegram.formatter._get_intimacy_total", return_value=40), \
         patch("app.telegram.formatter.calculate_happiness", return_value={
             "level": 3, "filled_blocks": 7, "total_blocks": 10, "progress": 0.8
         }):
        result = format_status(db)
    assert result.startswith(r"📊 지금 너의 상태야\.")


def test_format_status_self_intimacy():
    """나 자신 친밀도 표시"""
    from app.telegram.formatter import format_status
    db = MagicMock()
    db.query.return_value.all.return_value = []
    with patch("app.telegram.formatter._get_intimacy_total", return_value=40), \
         patch("app.telegram.formatter.calculate_happiness", return_value={
             "level": 3, "filled_blocks": 7, "total_blocks": 10, "progress": 0.8
         }):
        result = format_status(db)
    assert "나 자신: 40" in result


# ── format_briefing ─────────────────────────────────────────

def test_briefing_contains_philosophy():
    """철학 문구가 항상 포함됨"""
    from app.telegram.formatter import format_briefing, PHILOSOPHY
    db = MagicMock()
    db.query.return_value.filter_by.return_value.all.return_value = []
    with patch("app.telegram.formatter.today_kst", return_value=date.today()), \
         patch("app.telegram.formatter.is_quest_active_today", return_value=False), \
         patch("app.telegram.formatter._happiness_line", return_value="lv\\.1 □□□□□□□□□□"):
        text, _ = format_briefing(db)
    assert PHILOSOPHY in text


def test_briefing_no_question_mark_npc():
    """NPC 없는 퀘스트는 '?' 대신 '나를 사랑하기' 섹션에 표시"""
    from app.telegram.formatter import format_briefing
    q = make_quest("허리 요가하기", npc_name=None)
    st = MagicMock()
    st.id = "st-1"
    st.title = "허리 요가하기"
    q.subtasks = [st]

    db = MagicMock()
    db.query.return_value.filter_by.return_value.all.return_value = [q]

    with patch("app.telegram.formatter.today_kst", return_value=date.today()), \
         patch("app.telegram.formatter.is_quest_active_today", return_value=True), \
         patch("app.telegram.formatter.is_subtask_done_today", return_value=False), \
         patch("app.telegram.formatter._happiness_line", return_value="lv\\.1 □"):
        text, _ = format_briefing(db)

    assert "?" not in text
    assert "나를 사랑하기" in text


def test_briefing_no_duplicate_title_without_subtasks():
    """서브태스크 없는 퀘스트에서 제목이 한 번만 표시됨"""
    from app.telegram.formatter import format_briefing
    q = make_quest("가치토크 리뷰 준비", npc_name="신정철 본부장")
    q.subtasks = []

    db = MagicMock()
    db.query.return_value.filter_by.return_value.all.return_value = [q]

    with patch("app.telegram.formatter.today_kst", return_value=date.today()), \
         patch("app.telegram.formatter.is_quest_active_today", return_value=True), \
         patch("app.telegram.formatter.is_quest_done_today", return_value=False), \
         patch("app.telegram.formatter._happiness_line", return_value="lv\\.1 □"):
        text, _ = format_briefing(db)

    assert text.count("가치토크 리뷰 준비") == 1


def test_briefing_uses_dot_for_incomplete():
    """미완료 서브태스크는 · 기호 사용"""
    from app.telegram.formatter import format_briefing
    q = make_quest("퀘스트", npc_name="신정철 본부장")
    st = MagicMock()
    st.id = "st-1"
    st.title = "할일"
    q.subtasks = [st]

    db = MagicMock()
    db.query.return_value.filter_by.return_value.all.return_value = [q]

    with patch("app.telegram.formatter.today_kst", return_value=date.today()), \
         patch("app.telegram.formatter.is_quest_active_today", return_value=True), \
         patch("app.telegram.formatter.is_subtask_done_today", return_value=False), \
         patch("app.telegram.formatter._happiness_line", return_value="lv\\.1 □"):
        text, _ = format_briefing(db)

    assert "· 할일" in text
    assert "□" not in text
    assert "☐" not in text


def test_briefing_uses_checkmark_for_complete():
    """완료된 서브태스크는 ✓ 기호 사용"""
    from app.telegram.formatter import format_briefing
    q = make_quest("퀘스트", npc_name="신정철 본부장")
    st = MagicMock()
    st.id = "st-1"
    st.title = "할일"
    q.subtasks = [st]

    db = MagicMock()
    db.query.return_value.filter_by.return_value.all.return_value = [q]

    with patch("app.telegram.formatter.today_kst", return_value=date.today()), \
         patch("app.telegram.formatter.is_quest_active_today", return_value=True), \
         patch("app.telegram.formatter.is_subtask_done_today", return_value=True), \
         patch("app.telegram.formatter._happiness_line", return_value="lv\\.1 □"):
        text, _ = format_briefing(db)

    assert "✓ 할일" in text
    assert "☑" not in text
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd /Users/bonny/Dev/todogame && python -m pytest tests/test_formatter.py -v 2>&1 | head -50
```

Expected: 여러 테스트 FAIL (포맷이 아직 안 바뀌었으므로)

---

### Task 2: formatter.py 수정

**Files:**
- Modify: `app/telegram/formatter.py`

- [ ] **Step 1: formatter.py 전체 교체**

`app/telegram/formatter.py`를 아래 내용으로 교체한다:

```python
import re
from sqlalchemy.orm import Session
from app import models
from app.utils import today_kst
from app.services.quest import (
    is_quest_active_today,
    is_subtask_done_today,
    is_quest_all_done_today,
    is_quest_done_today,
)
from app.services.happiness import calculate_happiness
from app.services.quest import _get_intimacy_total

PHILOSOPHY = "언제나 본질은 상대를 사랑하는 거야\\. 그걸 위해 널 사랑해줘\\."


def _esc(text: str) -> str:
    """MarkdownV2 특수문자 이스케이프"""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', str(text))


def _happiness_line(db: Session) -> str:
    self_total = _get_intimacy_total(db, None)
    npc_ids = [row.id for row in db.query(models.NPC.id).all()]
    others = [_get_intimacy_total(db, nid) for nid in npc_ids]
    h = calculate_happiness(self_total, others)
    filled = "■" * h["filled_blocks"] + "□" * (h["total_blocks"] - h["filled_blocks"])
    return f"lv\\.{h['level']} {filled}"


def format_briefing(db: Session) -> tuple[str, list[dict]]:
    today = today_kst()
    all_quests = db.query(models.Quest).filter_by(is_archived=False).all()
    active = [q for q in all_quests if is_quest_active_today(q, today)]

    lines = ["🎮 오늘의 브리핑", "", PHILOSOPHY]
    buttons = []

    self_quests = [q for q in active if not (q.need and q.need.npc)]
    npc_quests = [q for q in active if q.need and q.need.npc]

    if self_quests:
        lines.append("")
        lines.append("나를 사랑하기")
        for q in self_quests:
            if q.subtasks:
                for st in q.subtasks:
                    done_st = is_subtask_done_today(db, st, today)
                    mark = "✓" if done_st else "·"
                    lines.append(f"  {mark} {_esc(st.title)}")
                    if not done_st:
                        buttons.append([{"text": f"✓ {st.title[:20]}", "callback_data": f"done:{st.id}"}])
            else:
                done_q = is_quest_done_today(db, q, today)
                mark = "✓" if done_q else "·"
                lines.append(f"  {mark} {_esc(q.title)}")
                if not done_q:
                    buttons.append([{"text": f"✓ {q.title[:20]}", "callback_data": f"quest:{q.id}"}])

    for q in npc_quests:
        npc_name = q.need.npc.name
        lines.append("")
        lines.append(_esc(npc_name))
        if q.subtasks:
            for st in q.subtasks:
                done_st = is_subtask_done_today(db, st, today)
                mark = "✓" if done_st else "·"
                lines.append(f"  {mark} {_esc(st.title)}")
                if not done_st:
                    buttons.append([{"text": f"✓ {st.title[:20]}", "callback_data": f"done:{st.id}"}])
        else:
            done_q = is_quest_done_today(db, q, today)
            mark = "✓" if done_q else "·"
            lines.append(f"  {mark} {_esc(q.title)}")
            if not done_q:
                buttons.append([{"text": f"✓ {q.title[:20]}", "callback_data": f"quest:{q.id}"}])

    lines.append("")
    lines.append(_happiness_line(db))
    return "\n".join(lines), buttons


def format_evening_briefing(db: Session) -> tuple[str, list[dict]]:
    today = today_kst()
    all_quests = db.query(models.Quest).filter_by(is_archived=False).all()
    active = [q for q in all_quests if is_quest_active_today(q, today)]
    remaining = [q for q in active if not is_quest_all_done_today(db, q, today)]

    buttons = []

    if not remaining:
        lines = [
            "🌙 오늘 할 일을 모두 했어\\! 잘했어\\.",
            "",
            _happiness_line(db),
        ]
        return "\n".join(lines), buttons

    lines = ["🌙 아직 남아있어\\.", "", PHILOSOPHY]

    self_quests = [q for q in remaining if not (q.need and q.need.npc)]
    npc_quests = [q for q in remaining if q.need and q.need.npc]

    if self_quests:
        lines.append("")
        lines.append("나를 사랑하기")
        for q in self_quests:
            if q.subtasks:
                undone = [st for st in q.subtasks if not is_subtask_done_today(db, st, today)]
                for st in undone:
                    lines.append(f"  · {_esc(st.title)}")
                    buttons.append([{"text": f"✓ {st.title[:20]}", "callback_data": f"done:{st.id}"}])
            else:
                lines.append(f"  · {_esc(q.title)}")
                buttons.append([{"text": f"✓ {q.title[:20]}", "callback_data": f"quest:{q.id}"}])

    for q in npc_quests:
        npc_name = q.need.npc.name
        lines.append("")
        lines.append(_esc(npc_name))
        if q.subtasks:
            undone = [st for st in q.subtasks if not is_subtask_done_today(db, st, today)]
            for st in undone:
                lines.append(f"  · {_esc(st.title)}")
                buttons.append([{"text": f"✓ {st.title[:20]}", "callback_data": f"done:{st.id}"}])
        else:
            lines.append(f"  · {_esc(q.title)}")
            buttons.append([{"text": f"✓ {q.title[:20]}", "callback_data": f"quest:{q.id}"}])

    lines.append("")
    lines.append(_happiness_line(db))
    return "\n".join(lines), buttons


def format_status(db: Session) -> str:
    self_total = _get_intimacy_total(db, None)
    npcs = db.query(models.NPC).all()
    others = [_get_intimacy_total(db, n.id) for n in npcs]
    h = calculate_happiness(self_total, others)

    lines = [
        "📊 지금 너의 상태야\\.",
        "",
        f"나 자신: {self_total}",
    ]
    for npc, total in zip(npcs, others):
        lines.append(f"{_esc(npc.name)}: {total}")

    filled = "■" * h["filled_blocks"] + "□" * (h["total_blocks"] - h["filled_blocks"])
    lines.append("")
    lines.append(f"lv\\.{h['level']} {filled} \\({round(h['progress']*100)}%\\)")

    return "\n".join(lines)
```

- [ ] **Step 2: 테스트 실행 — 통과 확인**

```bash
cd /Users/bonny/Dev/todogame && python -m pytest tests/test_formatter.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 3: 기존 테스트 전체 실행 — 회귀 확인**

```bash
cd /Users/bonny/Dev/todogame && python -m pytest tests/ -v --ignore=tests/test_ai_intake.py
```

Expected: 기존 테스트 전부 PASS (test_ai_intake는 외부 API 의존 → 제외)

- [ ] **Step 4: 커밋**

```bash
cd /Users/bonny/Dev/todogame && git add app/telegram/formatter.py tests/test_formatter.py && git commit -m "feat: redesign telegram formatter — philosophy quote, new symbols, bug fixes"
```
