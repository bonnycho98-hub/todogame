# LOVE QUEST Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 게임 퀘스트 형태의 할일 관리 웹앱과 텔레그램 봇을 FastAPI 모노리스로 구현

**Architecture:** FastAPI 단일 서버에서 REST API, Vanilla JS 프론트엔드 서빙, 텔레그램 웹훅을 모두 처리. SQLAlchemy(sync) + PostgreSQL로 데이터 관리. APScheduler로 매일 브리핑 전송.

**Tech Stack:** Python 3.11, FastAPI 0.111, SQLAlchemy 2.0 (sync), Alembic 1.13, psycopg2-binary, python-telegram-bot 21.x, APScheduler 3.10, python-dotenv, pytest, httpx

---

## File Map

```
todogame/
├── app/
│   ├── main.py              # FastAPI 앱 진입점, 라우터 등록, 텔레그램 웹훅 엔드포인트
│   ├── config.py            # 환경변수 로드 (DATABASE_URL, TELEGRAM_TOKEN 등)
│   ├── database.py          # SQLAlchemy 엔진, 세션, Base
│   ├── models.py            # 모든 ORM 모델
│   ├── schemas.py           # Pydantic 요청/응답 스키마
│   ├── routers/
│   │   ├── npcs.py          # NPC CRUD
│   │   ├── needs.py         # Need CRUD
│   │   ├── quests.py        # Quest CRUD
│   │   ├── subtasks.py      # Subtask CRUD + 완료 처리
│   │   ├── rewards.py       # LevelReward CRUD + claim
│   │   └── dashboard.py     # 대시보드 집계 데이터
│   ├── services/
│   │   ├── sprite.py        # NPC 특수문자 스프라이트 랜덤 생성
│   │   ├── quest.py         # 퀘스트 완료 판정, 친밀도 보상 지급
│   │   ├── happiness.py     # 행복 레벨 계산
│   │   └── scheduler.py     # APScheduler 일일 브리핑
│   └── telegram/
│       ├── bot.py           # Bot Application 생성 및 웹훅 핸들러
│       ├── handlers.py      # /brief /quests /status 커맨드
│       └── formatter.py     # 텔레그램 메시지 포맷터
├── static/
│   ├── style.css            # 레트로 RPG CSS 테마
│   ├── app.js               # 프론트엔드 SPA 로직
│   └── index.html           # 단일 HTML 파일
├── tests/
│   ├── conftest.py          # pytest fixtures
│   ├── test_sprite.py
│   ├── test_quest_service.py
│   ├── test_happiness.py
│   └── test_api.py
├── requirements.txt
├── .env.example
├── alembic.ini
├── alembic/
│   └── versions/
│       └── 001_initial.py
└── railway.toml
```

---

### Task 1: 프로젝트 셋업

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `app/__init__.py`, `app/routers/__init__.py`, `app/services/__init__.py`, `app/telegram/__init__.py`
- Create: `app/config.py`
- Create: `app/main.py`

- [ ] **Step 1: 디렉터리 구조 생성**

```bash
mkdir -p app/routers app/services app/telegram static tests
touch app/__init__.py app/routers/__init__.py app/services/__init__.py app/telegram/__init__.py tests/__init__.py
```

- [ ] **Step 2: requirements.txt 작성**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
alembic==1.13.1
psycopg2-binary==2.9.9
python-telegram-bot==21.3
apscheduler==3.10.4
python-dotenv==1.0.1
httpx==0.27.0
pytest==8.2.0
pytest-httpx==0.30.0
```

- [ ] **Step 3: .env.example 작성**

```
DATABASE_URL=postgresql://user:password@localhost:5432/lovequest
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
WEBHOOK_BASE_URL=https://your-app.railway.app
BRIEFING_HOUR=8
BRIEFING_MINUTE=0
```

- [ ] **Step 4: app/config.py 작성**

```python
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")
BRIEFING_HOUR = int(os.environ.get("BRIEFING_HOUR", "8"))
BRIEFING_MINUTE = int(os.environ.get("BRIEFING_MINUTE", "0"))
```

- [ ] **Step 5: app/main.py 작성 (골격)**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Love Quest")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")
```

- [ ] **Step 6: 패키지 설치 확인**

```bash
pip install -r requirements.txt
python -c "import fastapi, sqlalchemy, telegram; print('OK')"
```

Expected: `OK`

---

### Task 2: 데이터베이스 모델

**Files:**
- Create: `app/database.py`
- Create: `app/models.py`

- [ ] **Step 1: app/database.py 작성**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: app/models.py 작성**

```python
import uuid
import enum
from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class QuestType(str, enum.Enum):
    DAILY = "daily"
    ONE_TIME = "one_time"


class NPC(Base):
    __tablename__ = "npcs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    relationship = Column(String, nullable=False)
    sprite = Column(Text, nullable=False)       # JSON string: {"lines": [...], "color": "#hex"}
    color = Column(String(7), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    needs = relationship("Need", back_populates="npc", cascade="all, delete-orphan")
    intimacy_logs = relationship("IntimacyLog", back_populates="npc")


class Need(Base):
    __tablename__ = "needs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    npc_id = Column(UUID(as_uuid=True), ForeignKey("npcs.id", ondelete="CASCADE"), nullable=True)  # NULL = self
    title = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    npc = relationship("NPC", back_populates="needs")
    quests = relationship("Quest", back_populates="need", cascade="all, delete-orphan")


class Quest(Base):
    __tablename__ = "quests"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    need_id = Column(UUID(as_uuid=True), ForeignKey("needs.id", ondelete="CASCADE"), nullable=True)  # NULL = self direct
    title = Column(String, nullable=False)
    quest_type = Column(SAEnum(QuestType), nullable=False)
    routine = Column(JSONB, nullable=True)       # {"type":"daily"} | {"type":"weekly","days":[0,2]} | {"type":"monthly","dates":[1,15]}
    intimacy_reward = Column(Integer, default=10)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    need = relationship("Need", back_populates="quests")
    subtasks = relationship("Subtask", back_populates="quest", cascade="all, delete-orphan", order_by="Subtask.order")


class Subtask(Base):
    __tablename__ = "subtasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quest_id = Column(UUID(as_uuid=True), ForeignKey("quests.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    order = Column(Integer, default=0)

    quest = relationship("Quest", back_populates="subtasks")
    daily_completions = relationship("DailyCompletion", back_populates="subtask", cascade="all, delete-orphan")
    one_time_completion = relationship("OneTimeCompletion", back_populates="subtask", uselist=False, cascade="all, delete-orphan")


class DailyCompletion(Base):
    __tablename__ = "daily_completions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subtask_id = Column(UUID(as_uuid=True), ForeignKey("subtasks.id", ondelete="CASCADE"), nullable=False)
    completed_date = Column(Date, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow)

    subtask = relationship("Subtask", back_populates="daily_completions")


class OneTimeCompletion(Base):
    __tablename__ = "one_time_completions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subtask_id = Column(UUID(as_uuid=True), ForeignKey("subtasks.id", ondelete="CASCADE"), nullable=False, unique=True)
    completed_at = Column(DateTime, default=datetime.utcnow)

    subtask = relationship("Subtask", back_populates="one_time_completion")


class IntimacyLog(Base):
    __tablename__ = "intimacy_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    npc_id = Column(UUID(as_uuid=True), ForeignKey("npcs.id", ondelete="CASCADE"), nullable=True)  # NULL = self
    delta = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    npc = relationship("NPC", back_populates="intimacy_logs")


class LevelReward(Base):
    __tablename__ = "level_rewards"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(Integer, nullable=False, unique=True)
    message = Column(Text, nullable=False)
    is_claimed = Column(Boolean, default=False)
    claimed_at = Column(DateTime, nullable=True)
```

- [ ] **Step 3: 커밋**

```bash
git add app/ tests/ requirements.txt .env.example
git commit -m "feat: project skeleton + DB models"
```

---

### Task 3: Alembic 마이그레이션

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/001_initial.py`

- [ ] **Step 1: Alembic 초기화**

```bash
alembic init alembic
```

- [ ] **Step 2: alembic/env.py 수정 — target_metadata 설정**

`alembic/env.py`의 상단에 추가:
```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.database import Base
from app import models  # 모든 모델 임포트 (자동 감지용)
from app.config import DATABASE_URL
```

같은 파일에서 아래 두 줄 수정:
```python
# 변경 전:
target_metadata = None
# 변경 후:
target_metadata = Base.metadata
```

`run_migrations_offline()` 함수 내 `url = config.get_main_option("sqlalchemy.url")` 줄을:
```python
url = DATABASE_URL
```

`run_migrations_online()` 함수 내 `connectable = engine_from_config(...)` 블록을:
```python
from sqlalchemy import create_engine
connectable = create_engine(DATABASE_URL)
```

- [ ] **Step 3: 마이그레이션 생성 및 적용**

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

Expected: 테이블 7개 생성 (npcs, needs, quests, subtasks, daily_completions, one_time_completions, intimacy_logs, level_rewards)

- [ ] **Step 4: 커밋**

```bash
git add alembic/ alembic.ini
git commit -m "feat: alembic migrations"
```

---

### Task 4: 스프라이트 생성 서비스

**Files:**
- Create: `app/services/sprite.py`
- Create: `tests/test_sprite.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_sprite.py
from app.services.sprite import generate_sprite, SPRITE_COLORS

def test_sprite_has_five_lines():
    result = generate_sprite(seed=42)
    assert len(result["lines"]) == 5

def test_sprite_color_is_valid_hex():
    result = generate_sprite(seed=42)
    color = result["color"]
    assert color.startswith("#")
    assert len(color) == 7

def test_same_seed_produces_same_sprite():
    a = generate_sprite(seed=123)
    b = generate_sprite(seed=123)
    assert a == b

def test_different_seeds_likely_differ():
    results = [generate_sprite(seed=i) for i in range(20)]
    unique = {tuple(r["lines"]) for r in results}
    assert len(unique) > 5  # 20개 중 최소 5개는 달라야 함

def test_face_line_contains_parentheses():
    result = generate_sprite(seed=1)
    face_line = result["lines"][1]
    assert "(" in face_line and ")" in face_line
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_sprite.py -v
```

Expected: FAIL (모듈 없음)

- [ ] **Step 3: app/services/sprite.py 구현**

```python
import random
import json

SPRITE_COLORS = [
    "#ff9f43", "#67e5ff", "#a29bfe", "#fd79a8", "#0be881",
    "#ffd32a", "#00cec9", "#6c5ce7", "#fab1a0", "#74b9ff",
]

HEADS    = ["╭✿╮", "∧∧∧", "★─★", "♡♡♡", "◈✦◈", "∿∿∿", "≋≋≋", "~∇~"]
EYES     = ["◉", "⊙", "★", "♥", "─", "˘", "ω", "≧", "◕", "✦", "▲", "■"]
MOUTHS   = ["ω", "▽", "‿", "3", "▿", "ᵕ", "益", "ᴗ", "◡", "∇"]
UPPERS   = ["╰─╯", "─══─", "╔══╗", "╭──╮", "〔  〕", "【  】", "⌈  ⌉"]
LOWERS   = ["/||\\", "╱  ╲", "║  ║", "╰──╯", "│  │", "⎸  ⎹"]
FEET     = ["◡ ◡", "▔ ▔", "╚══╝", "∪ ∪", "⌣ ⌣", "﹂ ﹂"]


def generate_sprite(seed: int = None) -> dict:
    """5줄 특수문자 스프라이트를 랜덤 생성한다."""
    rng = random.Random(seed)
    eye = rng.choice(EYES)
    mouth = rng.choice(MOUTHS)
    lines = [
        rng.choice(HEADS),
        f"({eye}{mouth}{eye})",
        rng.choice(UPPERS),
        rng.choice(LOWERS),
        rng.choice(FEET),
    ]
    color = rng.choice(SPRITE_COLORS)
    return {"lines": lines, "color": color}


def sprite_to_text(sprite_data: dict) -> str:
    """스프라이트 dict를 줄바꿈 문자열로 변환한다."""
    return "\n".join(sprite_data["lines"])


def serialize_sprite(sprite_data: dict) -> str:
    return json.dumps(sprite_data, ensure_ascii=False)


def deserialize_sprite(sprite_json: str) -> dict:
    return json.loads(sprite_json)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_sprite.py -v
```

Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add app/services/sprite.py tests/test_sprite.py
git commit -m "feat: sprite generation service"
```

---

### Task 5: 행복 레벨 서비스

**Files:**
- Create: `app/services/happiness.py`
- Create: `tests/test_happiness.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_happiness.py
from app.services.happiness import calculate_happiness, POINTS_PER_LEVEL

def test_zero_intimacy_is_level_1():
    result = calculate_happiness(self_total=0, others_totals=[])
    assert result["level"] == 1
    assert result["progress"] == 0

def test_level_increases_with_score():
    # score = 100*0.4 + 100*0.6 = 100 → lv.2
    result = calculate_happiness(self_total=100, others_totals=[100])
    assert result["level"] == 2

def test_progress_within_level():
    # score = 50 → lv.1, progress = 50/100 = 0.5
    result = calculate_happiness(self_total=50, others_totals=[50])
    assert result["level"] == 1
    assert abs(result["progress"] - 0.5) < 0.01

def test_others_avg_used_not_sum():
    # 두 NPC 각각 100 → others_avg=100, self=100 → score=100 → lv.2
    result_one = calculate_happiness(self_total=100, others_totals=[100])
    result_two = calculate_happiness(self_total=100, others_totals=[100, 100])
    assert result_one["level"] == result_two["level"]

def test_pixel_blocks():
    # progress=0.6 → 6 blocks filled out of 10
    result = calculate_happiness(self_total=60, others_totals=[60])
    assert result["filled_blocks"] == 6
    assert result["total_blocks"] == 10
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_happiness.py -v
```

Expected: FAIL

- [ ] **Step 3: app/services/happiness.py 구현**

```python
import math

POINTS_PER_LEVEL = 100


def calculate_happiness(self_total: int, others_totals: list[int]) -> dict:
    """
    self_total: 나 자신 친밀도 누적 합계
    others_totals: 각 NPC 친밀도 누적 합계 리스트

    반환:
      level       : 현재 행복 레벨 (1부터 시작)
      score       : 현재 행복 점수 (소수점 가능)
      progress    : 현재 레벨 내 진행도 0.0 ~ 1.0
      filled_blocks: 채워진 픽셀 블록 수 (0~10)
      total_blocks: 10
    """
    others_avg = sum(others_totals) / len(others_totals) if others_totals else 0
    score = (self_total * 0.4) + (others_avg * 0.6)

    level = math.floor(score / POINTS_PER_LEVEL) + 1
    progress_score = score % POINTS_PER_LEVEL
    progress = progress_score / POINTS_PER_LEVEL

    total_blocks = 10
    filled_blocks = math.floor(progress * total_blocks)

    return {
        "level": level,
        "score": round(score, 1),
        "progress": round(progress, 3),
        "filled_blocks": filled_blocks,
        "total_blocks": total_blocks,
    }
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_happiness.py -v
```

Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add app/services/happiness.py tests/test_happiness.py
git commit -m "feat: happiness level service"
```

---

### Task 6: 퀘스트 완료 서비스

**Files:**
- Create: `app/services/quest.py`
- Create: `tests/test_quest_service.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_quest_service.py
from datetime import date
from app.services.quest import is_quest_active_today, is_routine_match

def test_daily_routine_always_active():
    assert is_routine_match({"type": "daily"}, date(2026, 4, 5)) is True

def test_weekly_routine_matches_correct_day():
    # 2026-04-06 = 월요일 (weekday=0)
    assert is_routine_match({"type": "weekly", "days": [0]}, date(2026, 4, 6)) is True

def test_weekly_routine_skips_wrong_day():
    # 2026-04-06 = 월요일, 화(1) 목(3) 은 아님
    assert is_routine_match({"type": "weekly", "days": [1, 3]}, date(2026, 4, 6)) is False

def test_monthly_routine_matches_correct_date():
    assert is_routine_match({"type": "monthly", "dates": [5, 15]}, date(2026, 4, 5)) is True

def test_monthly_routine_skips_wrong_date():
    assert is_routine_match({"type": "monthly", "dates": [1, 15]}, date(2026, 4, 5)) is False

def test_none_routine_not_active():
    assert is_routine_match(None, date.today()) is False
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_quest_service.py -v
```

Expected: FAIL

- [ ] **Step 3: app/services/quest.py 구현**

```python
from datetime import date
from sqlalchemy.orm import Session
from app import models


def is_routine_match(routine: dict | None, today: date) -> bool:
    """루틴 설정이 오늘 날짜에 해당하는지 확인한다."""
    if routine is None:
        return False
    t = routine.get("type")
    if t == "daily":
        return True
    if t == "weekly":
        return today.weekday() in routine.get("days", [])
    if t == "monthly":
        return today.day in routine.get("dates", [])
    return False


def is_quest_active_today(quest: models.Quest, today: date = None) -> bool:
    today = today or date.today()
    if quest.quest_type == models.QuestType.ONE_TIME and quest.is_archived:
        return False
    if quest.quest_type == models.QuestType.DAILY:
        return is_routine_match(quest.routine, today)
    return True  # one_time always shown until archived


def is_subtask_done_today(db: Session, subtask: models.Subtask, today: date) -> bool:
    """서브태스크가 오늘 완료됐는지 확인한다."""
    if subtask.quest.quest_type == models.QuestType.DAILY:
        return db.query(models.DailyCompletion).filter_by(
            subtask_id=subtask.id, completed_date=today
        ).first() is not None
    return subtask.one_time_completion is not None


def complete_subtask(db: Session, subtask_id: str, today: date = None) -> dict:
    """
    서브태스크를 완료 처리한다.
    모든 서브태스크 완료 시 퀘스트 완료 → 친밀도 보상 지급.
    반환: {"subtask_done": bool, "quest_done": bool, "level_up": int | None}
    """
    today = today or date.today()
    subtask = db.get(models.Subtask, subtask_id)
    if subtask is None:
        raise ValueError(f"Subtask {subtask_id} not found")

    quest = subtask.quest

    # 이미 완료된 경우 건너뜀
    if is_subtask_done_today(db, subtask, today):
        return {"subtask_done": False, "quest_done": False, "level_up": None}

    # 완료 기록 추가
    if quest.quest_type == models.QuestType.DAILY:
        db.add(models.DailyCompletion(subtask_id=subtask.id, completed_date=today))
    else:
        db.add(models.OneTimeCompletion(subtask_id=subtask.id))

    db.flush()

    # 퀘스트 완료 여부 확인
    all_done = all(is_subtask_done_today(db, st, today) for st in quest.subtasks)
    level_up = None

    if all_done:
        # 친밀도 보상
        npc_id = None
        if quest.need and quest.need.npc_id:
            npc_id = quest.need.npc_id

        db.add(models.IntimacyLog(
            npc_id=npc_id,
            delta=quest.intimacy_reward,
            reason=f"퀘스트 완료: {quest.title}",
        ))

        if quest.quest_type == models.QuestType.ONE_TIME:
            quest.is_archived = True

        # 레벨업 확인
        level_up = _check_level_up(db, npc_id)

    db.commit()
    return {"subtask_done": True, "quest_done": all_done, "level_up": level_up}


def _check_level_up(db: Session, npc_id) -> int | None:
    """친밀도 변화 후 레벨업 여부를 반환한다. 레벨업 없으면 None."""
    from app.services.happiness import calculate_happiness

    self_total = _get_intimacy_total(db, None)
    npc_ids = [row.id for row in db.query(models.NPC.id).all()]
    others_totals = [_get_intimacy_total(db, nid) for nid in npc_ids]

    # 방금 추가된 delta 포함된 현재 레벨
    current = calculate_happiness(self_total, others_totals)

    # delta 하나 빼고 이전 레벨 계산
    prev_self = self_total - (10 if npc_id is None else 0)
    prev_others = [
        (t - 10 if npc_ids[i] == npc_id else t)
        for i, t in enumerate(others_totals)
    ]
    prev = calculate_happiness(prev_self, prev_others)

    if current["level"] > prev["level"]:
        return current["level"]
    return None


def _get_intimacy_total(db: Session, npc_id) -> int:
    from sqlalchemy import func
    result = db.query(func.sum(models.IntimacyLog.delta)).filter(
        models.IntimacyLog.npc_id == npc_id
    ).scalar()
    return result or 0
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_quest_service.py -v
```

Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add app/services/quest.py tests/test_quest_service.py
git commit -m "feat: quest completion service"
```

---

### Task 7: Pydantic 스키마

**Files:**
- Create: `app/schemas.py`

- [ ] **Step 1: app/schemas.py 작성**

```python
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models import QuestType


# ── NPC ─────────────────────────────────────────────
class NPCCreate(BaseModel):
    name: str
    relationship: str
    sprite: Optional[str] = None  # None이면 자동 생성
    color: Optional[str] = None

class NPCOut(BaseModel):
    id: UUID
    name: str
    relationship: str
    sprite: str
    color: str
    created_at: datetime
    intimacy_total: int = 0

    model_config = {"from_attributes": True}


# ── Need ─────────────────────────────────────────────
class NeedCreate(BaseModel):
    npc_id: Optional[UUID] = None
    title: str

class NeedOut(BaseModel):
    id: UUID
    npc_id: Optional[UUID]
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Quest ─────────────────────────────────────────────
class RoutineConfig(BaseModel):
    type: str                          # "daily" | "weekly" | "monthly"
    days: Optional[list[int]] = None   # weekly: 0=Mon..6=Sun
    dates: Optional[list[int]] = None  # monthly: 1..31

class QuestCreate(BaseModel):
    need_id: Optional[UUID] = None
    title: str
    quest_type: QuestType
    routine: Optional[RoutineConfig] = None
    intimacy_reward: int = 10

class SubtaskOut(BaseModel):
    id: UUID
    title: str
    order: int
    is_done_today: bool = False

    model_config = {"from_attributes": True}

class QuestOut(BaseModel):
    id: UUID
    need_id: Optional[UUID]
    title: str
    quest_type: QuestType
    routine: Optional[dict]
    intimacy_reward: int
    is_archived: bool
    subtasks: list[SubtaskOut] = []

    model_config = {"from_attributes": True}


# ── Subtask ─────────────────────────────────────────────
class SubtaskCreate(BaseModel):
    quest_id: UUID
    title: str
    order: int = 0

class CompleteSubtaskOut(BaseModel):
    subtask_done: bool
    quest_done: bool
    level_up: Optional[int]


# ── LevelReward ─────────────────────────────────────────────
class LevelRewardCreate(BaseModel):
    level: int
    message: str

class LevelRewardOut(BaseModel):
    id: UUID
    level: int
    message: str
    is_claimed: bool
    claimed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Dashboard ─────────────────────────────────────────────
class HappinessOut(BaseModel):
    level: int
    score: float
    progress: float
    filled_blocks: int
    total_blocks: int

class NPCSummary(BaseModel):
    id: UUID
    name: str
    sprite: str
    color: str
    intimacy_total: int

class DashboardOut(BaseModel):
    today_quests: list[QuestOut]
    npcs: list[NPCSummary]
    happiness: HappinessOut
    pending_level_reward: Optional[LevelRewardOut]
```

- [ ] **Step 2: 임포트 확인**

```bash
python -c "from app.schemas import DashboardOut; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add app/schemas.py
git commit -m "feat: pydantic schemas"
```

---

### Task 8: NPC / Need / Quest / Subtask API

**Files:**
- Create: `app/routers/npcs.py`
- Create: `app/routers/needs.py`
- Create: `app/routers/quests.py`
- Create: `app/routers/subtasks.py`
- Modify: `app/main.py`
- Create: `tests/conftest.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: tests/conftest.py 작성**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

SQLALCHEMY_TEST_URL = "postgresql://postgres:postgres@localhost:5432/lovequesttest"

engine_test = create_engine(SQLALCHEMY_TEST_URL)
TestSession = sessionmaker(bind=engine_test)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

- [ ] **Step 2: app/routers/npcs.py 작성**

```python
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import models, schemas
from app.services.sprite import generate_sprite, serialize_sprite, SPRITE_COLORS

router = APIRouter(prefix="/api/npcs", tags=["npcs"])


def _get_intimacy_total(db: Session, npc_id) -> int:
    result = db.query(func.sum(models.IntimacyLog.delta)).filter(
        models.IntimacyLog.npc_id == npc_id
    ).scalar()
    return result or 0


@router.get("", response_model=list[schemas.NPCOut])
def list_npcs(db: Session = Depends(get_db)):
    npcs = db.query(models.NPC).order_by(models.NPC.created_at).all()
    result = []
    for npc in npcs:
        out = schemas.NPCOut.model_validate(npc)
        out.intimacy_total = _get_intimacy_total(db, npc.id)
        result.append(out)
    return result


@router.post("", response_model=schemas.NPCOut, status_code=201)
def create_npc(body: schemas.NPCCreate, db: Session = Depends(get_db)):
    sprite_data = generate_sprite(seed=random.randint(0, 10**9))
    color = body.color or sprite_data["color"]
    sprite_json = body.sprite or serialize_sprite(sprite_data)

    npc = models.NPC(
        name=body.name,
        relationship=body.relationship,
        sprite=sprite_json,
        color=color,
    )
    db.add(npc)
    db.commit()
    db.refresh(npc)
    out = schemas.NPCOut.model_validate(npc)
    out.intimacy_total = 0
    return out


@router.post("/{npc_id}/regenerate-sprite", response_model=schemas.NPCOut)
def regenerate_sprite(npc_id: str, db: Session = Depends(get_db)):
    npc = db.get(models.NPC, npc_id)
    if not npc:
        raise HTTPException(404)
    sprite_data = generate_sprite(seed=random.randint(0, 10**9))
    npc.sprite = serialize_sprite(sprite_data)
    npc.color = sprite_data["color"]
    db.commit()
    db.refresh(npc)
    out = schemas.NPCOut.model_validate(npc)
    out.intimacy_total = _get_intimacy_total(db, npc.id)
    return out


@router.delete("/{npc_id}", status_code=204)
def delete_npc(npc_id: str, db: Session = Depends(get_db)):
    npc = db.get(models.NPC, npc_id)
    if not npc:
        raise HTTPException(404)
    db.delete(npc)
    db.commit()
```

- [ ] **Step 3: app/routers/needs.py 작성**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/needs", tags=["needs"])


@router.get("", response_model=list[schemas.NeedOut])
def list_needs(npc_id: str = None, db: Session = Depends(get_db)):
    q = db.query(models.Need)
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


@router.delete("/{need_id}", status_code=204)
def delete_need(need_id: str, db: Session = Depends(get_db)):
    need = db.get(models.Need, need_id)
    if not need:
        raise HTTPException(404)
    db.delete(need)
    db.commit()
```

- [ ] **Step 4: app/routers/quests.py 작성**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.database import get_db
from app import models, schemas
from app.services.quest import is_subtask_done_today

router = APIRouter(prefix="/api/quests", tags=["quests"])


def _enrich_quest(quest: models.Quest, db: Session, today: date) -> schemas.QuestOut:
    out = schemas.QuestOut.model_validate(quest)
    out.subtasks = [
        schemas.SubtaskOut(
            id=st.id,
            title=st.title,
            order=st.order,
            is_done_today=is_subtask_done_today(db, st, today),
        )
        for st in quest.subtasks
    ]
    return out


@router.get("", response_model=list[schemas.QuestOut])
def list_quests(need_id: str = None, db: Session = Depends(get_db)):
    today = date.today()
    q = db.query(models.Quest)
    if need_id:
        q = q.filter(models.Quest.need_id == need_id)
    else:
        q = q.filter(models.Quest.need_id.is_(None))
    return [_enrich_quest(quest, db, today) for quest in q.all()]


@router.post("", response_model=schemas.QuestOut, status_code=201)
def create_quest(body: schemas.QuestCreate, db: Session = Depends(get_db)):
    quest = models.Quest(
        need_id=body.need_id,
        title=body.title,
        quest_type=body.quest_type,
        routine=body.routine.model_dump() if body.routine else None,
        intimacy_reward=body.intimacy_reward,
    )
    db.add(quest)
    db.commit()
    db.refresh(quest)
    return _enrich_quest(quest, db, date.today())


@router.delete("/{quest_id}", status_code=204)
def delete_quest(quest_id: str, db: Session = Depends(get_db)):
    quest = db.get(models.Quest, quest_id)
    if not quest:
        raise HTTPException(404)
    db.delete(quest)
    db.commit()
```

- [ ] **Step 5: app/routers/subtasks.py 작성**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.services.quest import complete_subtask

router = APIRouter(prefix="/api/subtasks", tags=["subtasks"])


@router.post("", response_model=schemas.SubtaskOut, status_code=201)
def create_subtask(body: schemas.SubtaskCreate, db: Session = Depends(get_db)):
    subtask = models.Subtask(
        quest_id=body.quest_id,
        title=body.title,
        order=body.order,
    )
    db.add(subtask)
    db.commit()
    db.refresh(subtask)
    return schemas.SubtaskOut(id=subtask.id, title=subtask.title, order=subtask.order, is_done_today=False)


@router.post("/{subtask_id}/complete", response_model=schemas.CompleteSubtaskOut)
def complete(subtask_id: str, db: Session = Depends(get_db)):
    try:
        result = complete_subtask(db, subtask_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result


@router.delete("/{subtask_id}", status_code=204)
def delete_subtask(subtask_id: str, db: Session = Depends(get_db)):
    subtask = db.get(models.Subtask, subtask_id)
    if not subtask:
        raise HTTPException(404)
    db.delete(subtask)
    db.commit()
```

- [ ] **Step 6: app/routers/rewards.py 작성**

```python
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


@router.get("", response_model=list[schemas.LevelRewardOut])
def list_rewards(db: Session = Depends(get_db)):
    return db.query(models.LevelReward).order_by(models.LevelReward.level).all()


@router.post("", response_model=schemas.LevelRewardOut, status_code=201)
def create_reward(body: schemas.LevelRewardCreate, db: Session = Depends(get_db)):
    existing = db.query(models.LevelReward).filter_by(level=body.level).first()
    if existing:
        raise HTTPException(400, f"Level {body.level} reward already exists")
    reward = models.LevelReward(level=body.level, message=body.message)
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward


@router.post("/{reward_id}/claim", response_model=schemas.LevelRewardOut)
def claim_reward(reward_id: str, db: Session = Depends(get_db)):
    reward = db.get(models.LevelReward, reward_id)
    if not reward:
        raise HTTPException(404)
    if reward.is_claimed:
        raise HTTPException(400, "Already claimed")
    reward.is_claimed = True
    reward.claimed_at = datetime.utcnow()
    db.commit()
    db.refresh(reward)
    return reward


@router.delete("/{reward_id}", status_code=204)
def delete_reward(reward_id: str, db: Session = Depends(get_db)):
    reward = db.get(models.LevelReward, reward_id)
    if not reward:
        raise HTTPException(404)
    db.delete(reward)
    db.commit()
```

- [ ] **Step 7: app/routers/dashboard.py 작성**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.database import get_db
from app import models, schemas
from app.services.happiness import calculate_happiness
from app.services.quest import is_quest_active_today, is_subtask_done_today, _get_intimacy_total
from app.services.sprite import deserialize_sprite

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardOut)
def get_dashboard(db: Session = Depends(get_db)):
    today = date.today()

    # 오늘의 퀘스트 (self + NPC 모두)
    all_quests = db.query(models.Quest).filter_by(is_archived=False).all()
    today_quests = []
    for q in all_quests:
        if is_quest_active_today(q, today):
            out = schemas.QuestOut.model_validate(q)
            out.subtasks = [
                schemas.SubtaskOut(
                    id=st.id, title=st.title, order=st.order,
                    is_done_today=is_subtask_done_today(db, st, today),
                )
                for st in q.subtasks
            ]
            today_quests.append(out)

    # NPC 목록
    npcs = db.query(models.NPC).all()
    npc_summaries = []
    others_totals = []
    for npc in npcs:
        total = _get_intimacy_total(db, npc.id)
        others_totals.append(total)
        npc_summaries.append(schemas.NPCSummary(
            id=npc.id, name=npc.name,
            sprite=npc.sprite, color=npc.color,
            intimacy_total=total,
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

- [ ] **Step 8: app/main.py 라우터 등록**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import npcs, needs, quests, subtasks, rewards, dashboard

app = FastAPI(title="Love Quest")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(npcs.router)
app.include_router(needs.router)
app.include_router(quests.router)
app.include_router(subtasks.router)
app.include_router(rewards.router)
app.include_router(dashboard.router)

@app.get("/")
def root():
    return FileResponse("static/index.html")
```

- [ ] **Step 9: API 통합 테스트 작성**

```python
# tests/test_api.py
def test_create_and_list_npc(client):
    res = client.post("/api/npcs", json={"name": "엄마", "relationship": "가족"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "엄마"
    assert data["sprite"]  # 자동 생성됨

    res2 = client.get("/api/npcs")
    assert res2.status_code == 200
    assert any(n["name"] == "엄마" for n in res2.json())


def test_create_quest_with_subtask_and_complete(client):
    # NPC 생성
    npc = client.post("/api/npcs", json={"name": "친구", "relationship": "친구"}).json()
    # Need 생성
    need = client.post("/api/needs", json={"npc_id": npc["id"], "title": "연락받고싶어함"}).json()
    # Quest 생성
    quest = client.post("/api/quests", json={
        "need_id": need["id"], "title": "주 1회 전화",
        "quest_type": "daily", "routine": {"type": "daily"}, "intimacy_reward": 20
    }).json()
    # Subtask 생성
    st = client.post("/api/subtasks", json={
        "quest_id": quest["id"], "title": "안부 묻기", "order": 0
    }).json()

    # 완료 처리
    res = client.post(f"/api/subtasks/{st['id']}/complete")
    assert res.status_code == 200
    result = res.json()
    assert result["subtask_done"] is True
    assert result["quest_done"] is True


def test_dashboard_returns_data(client):
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "happiness" in data
    assert data["happiness"]["level"] >= 1
```

- [ ] **Step 10: 테스트 실행**

```bash
pytest tests/test_api.py -v
```

Expected: 3 passed

- [ ] **Step 11: 커밋**

```bash
git add app/routers/ app/main.py tests/conftest.py tests/test_api.py
git commit -m "feat: all API routers + integration tests"
```

---

### Task 9: 프론트엔드 — 기반 HTML/CSS

**Files:**
- Create: `static/index.html`
- Create: `static/style.css`
- Create: `static/app.js`

- [ ] **Step 1: static/style.css 작성**

```css
/* static/style.css */
:root {
  --bg: #0d1117;
  --bg2: #0f1923;
  --bg3: #1c2333;
  --border: #2a3344;
  --red: #e94560;
  --yellow: #ffd32a;
  --blue: #a8dadc;
  --green: #3fb950;
  --text: #cdd9e5;
  --muted: #768390;
  --font: 'Courier New', Courier, monospace;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font);
  font-size: 13px;
  min-height: 100vh;
}

/* 레이아웃 */
.app { display: flex; flex-direction: column; min-height: 100vh; }

.navbar {
  background: var(--bg2);
  border-bottom: 1px solid var(--red);
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.navbar-brand { color: var(--red); font-size: 16px; letter-spacing: 2px; }
.navbar-links { display: flex; gap: 16px; }
.navbar-links a { color: var(--muted); cursor: pointer; text-decoration: none; }
.navbar-links a.active, .navbar-links a:hover { color: var(--text); }

.page { display: none; padding: 20px; max-width: 900px; margin: 0 auto; width: 100%; }
.page.active { display: block; }

/* 카드 */
.card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 14px;
  margin-bottom: 12px;
}
.card-title { color: var(--yellow); margin-bottom: 10px; font-size: 11px; letter-spacing: 1px; }

/* 버튼 */
.btn {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text);
  padding: 5px 12px;
  cursor: pointer;
  font-family: var(--font);
  font-size: 12px;
  border-radius: 3px;
}
.btn:hover { border-color: var(--red); color: var(--red); }
.btn-primary { background: var(--red); border-color: var(--red); color: #fff; }
.btn-primary:hover { background: #c73650; }
.btn-sm { padding: 3px 8px; font-size: 11px; }

/* 인풋 */
.input {
  background: var(--bg3);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 6px 10px;
  font-family: var(--font);
  font-size: 12px;
  border-radius: 3px;
  width: 100%;
}
.input:focus { outline: none; border-color: var(--red); }

/* 탭 */
.tabs { display: flex; gap: 4px; margin-bottom: 14px; flex-wrap: wrap; }
.tab {
  background: var(--bg3);
  border: 1px solid var(--border);
  color: var(--muted);
  padding: 4px 12px;
  cursor: pointer;
  border-radius: 3px;
  font-family: var(--font);
  font-size: 11px;
}
.tab.active { background: var(--red); border-color: var(--red); color: #fff; }
.tab:hover:not(.active) { color: var(--text); }

/* 행복 픽셀 블록 */
.pixel-blocks { display: flex; gap: 4px; align-items: center; }
.pixel-block { width: 16px; height: 16px; background: var(--bg3); border: 1px solid var(--border); }
.pixel-block.filled { background: var(--red); border-color: var(--red); }

/* NPC 스프라이트 */
.sprite { white-space: pre; line-height: 1.4; font-size: 12px; }

/* 체크박스 */
.check-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; }
.check-item input[type=checkbox] { accent-color: var(--red); width: 14px; height: 14px; }
.check-item.done label { color: var(--muted); text-decoration: line-through; }

/* 아코디언 */
.accordion-header {
  display: flex; align-items: center; gap: 8px;
  cursor: pointer; padding: 6px 0; color: var(--text);
}
.accordion-header:hover { color: var(--blue); }
.accordion-arrow { color: var(--muted); font-size: 10px; width: 12px; }
.accordion-body { padding-left: 20px; display: none; }
.accordion-body.open { display: block; }

/* 친밀도 바 */
.intimacy-bar { background: var(--bg3); height: 6px; border-radius: 2px; margin: 4px 0; }
.intimacy-fill { background: var(--red); height: 100%; border-radius: 2px; transition: width .3s; }

/* 모달 */
.modal-overlay {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,0.7); z-index: 100;
  align-items: center; justify-content: center;
}
.modal-overlay.open { display: flex; }
.modal {
  background: var(--bg2); border: 2px solid var(--red);
  border-radius: 6px; padding: 24px; max-width: 400px; width: 90%;
}
.modal h2 { color: var(--red); margin-bottom: 16px; }

/* 레벨업 팝업 */
.levelup-popup {
  border-color: var(--yellow);
  text-align: center;
}
.levelup-popup h2 { color: var(--yellow); }

/* 폼 */
.form-row { margin-bottom: 10px; }
.form-label { color: var(--muted); font-size: 11px; letter-spacing: 1px; display: block; margin-bottom: 4px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

/* 그리드 */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 600px) { .grid-2 { grid-template-columns: 1fr; } }

/* 섹션 헤더 */
.section-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px;
}
.section-title { color: var(--blue); font-size: 11px; letter-spacing: 1px; }
```

- [ ] **Step 2: static/index.html 작성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LOVE QUEST</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="app">

  <nav class="navbar">
    <span class="navbar-brand">♛ LOVE QUEST</span>
    <div class="navbar-links">
      <a onclick="showPage('dashboard')" id="nav-dashboard" class="active">DASHBOARD</a>
      <a onclick="showPage('quests')" id="nav-quests">QUESTS</a>
      <a onclick="showPage('npcs')" id="nav-npcs">NPC</a>
      <a onclick="showPage('rewards')" id="nav-rewards">REWARDS</a>
    </div>
  </nav>

  <!-- 대시보드 -->
  <div id="page-dashboard" class="page active">
    <div class="grid-2" style="margin-bottom:12px">
      <div class="card" id="today-card">
        <div class="card-title">TODAY</div>
        <div id="today-list"></div>
      </div>
      <div class="card" id="npc-card">
        <div class="card-title">NPC</div>
        <div id="npc-list"></div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">HAPPINESS LEVEL</div>
      <div id="happiness-display"></div>
    </div>
  </div>

  <!-- 퀘스트 보드 -->
  <div id="page-quests" class="page">
    <div class="section-header">
      <span class="section-title">QUEST BOARD</span>
      <button class="btn btn-sm btn-primary" onclick="openAddQuestModal()">+ 퀘스트 추가</button>
    </div>
    <div class="tabs" id="quest-tabs"></div>
    <div id="quest-content"></div>
  </div>

  <!-- NPC 관리 -->
  <div id="page-npcs" class="page">
    <div class="section-header">
      <span class="section-title">NPC 관리</span>
      <button class="btn btn-sm btn-primary" onclick="openAddNPCModal()">+ NPC 추가</button>
    </div>
    <div id="npc-detail-list"></div>
  </div>

  <!-- 보상 설정 -->
  <div id="page-rewards" class="page">
    <div class="section-header">
      <span class="section-title">레벨업 보상</span>
      <button class="btn btn-sm btn-primary" onclick="openAddRewardModal()">+ 보상 추가</button>
    </div>
    <div id="rewards-list"></div>
  </div>

</div><!-- /app -->

<!-- NPC 추가 모달 -->
<div class="modal-overlay" id="modal-npc">
  <div class="modal">
    <h2>NPC 추가</h2>
    <div class="form-row">
      <label class="form-label">이름</label>
      <input class="input" id="npc-name" placeholder="엄마">
    </div>
    <div class="form-row">
      <label class="form-label">관계</label>
      <input class="input" id="npc-relationship" placeholder="가족">
    </div>
    <div style="display:flex;gap:8px;margin-top:16px">
      <button class="btn btn-primary" onclick="submitNPC()">추가</button>
      <button class="btn" onclick="closeModal('modal-npc')">취소</button>
    </div>
  </div>
</div>

<!-- 퀘스트 추가 모달 -->
<div class="modal-overlay" id="modal-quest">
  <div class="modal">
    <h2>퀘스트 추가</h2>
    <div class="form-row">
      <label class="form-label">제목</label>
      <input class="input" id="quest-title" placeholder="주 1회 전화하기">
    </div>
    <div class="form-row">
      <label class="form-label">타입</label>
      <select class="input" id="quest-type" onchange="toggleRoutine()">
        <option value="daily">반복 (daily)</option>
        <option value="one_time">일회성 (one-time)</option>
      </select>
    </div>
    <div id="routine-section" class="form-row">
      <label class="form-label">루틴</label>
      <select class="input" id="routine-type" onchange="toggleRoutineDetail()">
        <option value="daily">매일</option>
        <option value="weekly">매주 특정 요일</option>
        <option value="monthly">매월 특정 날짜</option>
      </select>
      <div id="routine-days" style="display:none;margin-top:6px">
        <label class="form-label">요일 선택 (복수 가능)</label>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <label><input type="checkbox" value="0"> 월</label>
          <label><input type="checkbox" value="1"> 화</label>
          <label><input type="checkbox" value="2"> 수</label>
          <label><input type="checkbox" value="3"> 목</label>
          <label><input type="checkbox" value="4"> 금</label>
          <label><input type="checkbox" value="5"> 토</label>
          <label><input type="checkbox" value="6"> 일</label>
        </div>
      </div>
      <div id="routine-dates" style="display:none;margin-top:6px">
        <label class="form-label">날짜 입력 (쉼표 구분, 예: 1,15)</label>
        <input class="input" id="routine-dates-input" placeholder="1,15">
      </div>
    </div>
    <div class="form-row">
      <label class="form-label">친밀도 보상</label>
      <input class="input" id="quest-reward" type="number" value="10">
    </div>
    <input type="hidden" id="quest-need-id">
    <div style="display:flex;gap:8px;margin-top:16px">
      <button class="btn btn-primary" onclick="submitQuest()">추가</button>
      <button class="btn" onclick="closeModal('modal-quest')">취소</button>
    </div>
  </div>
</div>

<!-- 보상 추가 모달 -->
<div class="modal-overlay" id="modal-reward">
  <div class="modal">
    <h2>레벨업 보상 설정</h2>
    <div class="form-row">
      <label class="form-label">레벨</label>
      <input class="input" id="reward-level" type="number" placeholder="5">
    </div>
    <div class="form-row">
      <label class="form-label">보상 내용</label>
      <input class="input" id="reward-message" placeholder="좋아하는 카페에서 케이크 먹기">
    </div>
    <div style="display:flex;gap:8px;margin-top:16px">
      <button class="btn btn-primary" onclick="submitReward()">저장</button>
      <button class="btn" onclick="closeModal('modal-reward')">취소</button>
    </div>
  </div>
</div>

<!-- 레벨업 팝업 -->
<div class="modal-overlay" id="modal-levelup">
  <div class="modal levelup-popup">
    <h2>🎉 LEVEL UP!</h2>
    <div id="levelup-message" style="color:var(--text);margin:16px 0"></div>
    <div id="levelup-reward" style="color:var(--yellow);margin-bottom:16px"></div>
    <button class="btn btn-primary" id="btn-claim-reward" onclick="claimReward()">보상 받기</button>
    <button class="btn" style="margin-left:8px" onclick="closeModal('modal-levelup')">닫기</button>
  </div>
</div>

<script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 3: 커밋**

```bash
git add static/index.html static/style.css
git commit -m "feat: frontend HTML/CSS base"
```

---

### Task 10: 프론트엔드 — JavaScript SPA

**Files:**
- Create: `static/app.js`

- [ ] **Step 1: static/app.js 작성**

```javascript
// static/app.js
// ── 상태 ─────────────────────────────────────────────
const state = {
  npcs: [],
  dashboard: null,
  activeQuestTab: 'self',
  pendingRewardId: null,
};

// ── API 헬퍼 ─────────────────────────────────────────────
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch('/api' + path, opts);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`${res.status}: ${err}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── 페이지 전환 ─────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.navbar-links a').forEach(a => a.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  document.getElementById('nav-' + name).classList.add('active');

  if (name === 'dashboard') loadDashboard();
  if (name === 'quests') loadQuestBoard();
  if (name === 'npcs') loadNPCDetail();
  if (name === 'rewards') loadRewards();
}

// ── 스프라이트 렌더링 ─────────────────────────────────────────────
function renderSprite(spriteJson, color) {
  try {
    const data = typeof spriteJson === 'string' ? JSON.parse(spriteJson) : spriteJson;
    return `<pre class="sprite" style="color:${color || data.color}">${data.lines.join('\n')}</pre>`;
  } catch { return '<pre class="sprite">(?)</pre>'; }
}

// ── 행복 레벨 렌더링 ─────────────────────────────────────────────
function renderHappiness(h) {
  const blocks = Array.from({ length: h.total_blocks }, (_, i) =>
    `<div class="pixel-block${i < h.filled_blocks ? ' filled' : ''}"></div>`
  ).join('');
  return `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">
      <span style="color:var(--yellow);font-size:20px">lv.${h.level}</span>
      <div class="pixel-blocks">${blocks}</div>
      <span style="color:var(--muted);font-size:11px">lv.${h.level + 1}까지 ${Math.round((1 - h.progress) * 100)}%</span>
    </div>
    <div style="color:var(--muted);font-size:10px">score: ${h.score}</div>
  `;
}

// ── 대시보드 ─────────────────────────────────────────────
async function loadDashboard() {
  const data = await api('GET', '/dashboard');
  state.dashboard = data;

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

  // 행복 레벨
  document.getElementById('happiness-display').innerHTML = renderHappiness(data.happiness);

  // 레벨업 보상 팝업
  if (data.pending_level_reward) {
    const r = data.pending_level_reward;
    document.getElementById('levelup-message').textContent = `lv.${r.level} 달성!`;
    document.getElementById('levelup-reward').textContent = `✨ ${r.message}`;
    state.pendingRewardId = r.id;
    document.getElementById('modal-levelup').classList.add('open');
  }
}

async function completeSubtask(id, checkbox) {
  try {
    const result = await api('POST', `/subtasks/${id}/complete`);
    if (result.quest_done) {
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

// ── 퀘스트 보드 ─────────────────────────────────────────────
async function loadQuestBoard() {
  const npcs = await api('GET', '/npcs');
  state.npcs = npcs;

  // 탭 렌더링
  const tabsEl = document.getElementById('quest-tabs');
  tabsEl.innerHTML = `
    <div class="tab${state.activeQuestTab === 'self' ? ' active' : ''}" onclick="selectQuestTab('self')">나 자신</div>
    ${npcs.map(n => `
      <div class="tab${state.activeQuestTab === n.id ? ' active' : ''}" onclick="selectQuestTab('${n.id}')">${n.name}</div>
    `).join('')}
  `;

  await renderQuestContent();
}

async function selectQuestTab(tabId) {
  state.activeQuestTab = tabId;
  await loadQuestBoard();
}

async function renderQuestContent() {
  const contentEl = document.getElementById('quest-content');
  const isNPC = state.activeQuestTab !== 'self';
  const npcId = isNPC ? state.activeQuestTab : null;

  // 니즈 목록 로드
  const needsUrl = npcId ? `/needs?npc_id=${npcId}` : '/needs';
  const needs = await api('GET', needsUrl);

  contentEl.innerHTML = `
    <div style="margin-bottom:8px;display:flex;justify-content:flex-end;gap:6px">
      <button class="btn btn-sm" onclick="openAddNeedModal('${npcId || ''}')">+ 니즈 추가</button>
    </div>
    <div id="needs-accordion"></div>
  `;

  const accordion = document.getElementById('needs-accordion');
  for (const need of needs) {
    const quests = await api('GET', `/quests?need_id=${need.id}`);
    accordion.innerHTML += renderNeedAccordion(need, quests);
  }
}

function renderNeedAccordion(need, quests) {
  return `
    <div class="card" style="margin-bottom:8px">
      <div class="accordion-header" onclick="toggleAccordion('need-${need.id}')">
        <span class="accordion-arrow" id="arrow-need-${need.id}">▶</span>
        <span>${need.title}</span>
        <span style="color:var(--muted);font-size:10px;margin-left:auto">${quests.length}개</span>
        <button class="btn btn-sm" style="margin-left:8px" onclick="event.stopPropagation();openAddQuestModal('${need.id}')">+ 퀘스트</button>
      </div>
      <div class="accordion-body" id="need-${need.id}">
        ${quests.map(q => renderQuestAccordion(q)).join('')}
      </div>
    </div>
  `;
}

function renderQuestAccordion(q) {
  const routineLabel = q.routine ? formatRoutine(q.routine) : '';
  const doneCount = q.subtasks.filter(s => s.is_done_today).length;
  return `
    <div style="margin-left:16px;margin-bottom:6px;border-left:1px solid var(--border);padding-left:12px">
      <div class="accordion-header" onclick="toggleAccordion('quest-${q.id}')">
        <span class="accordion-arrow" id="arrow-quest-${q.id}">▶</span>
        <span style="color:var(--text)">${q.title}</span>
        <span style="color:var(--muted);font-size:10px;margin-left:8px">[${routineLabel}]</span>
        <span style="color:var(--muted);font-size:10px;margin-left:auto">${doneCount}/${q.subtasks.length}</span>
        <button class="btn btn-sm" style="margin-left:8px" onclick="event.stopPropagation();openAddSubtaskModal('${q.id}')">+ 항목</button>
      </div>
      <div class="accordion-body" id="quest-${q.id}">
        ${q.subtasks.map(st => `
          <div class="check-item${st.is_done_today ? ' done' : ''}" style="padding-left:12px">
            <input type="checkbox" ${st.is_done_today ? 'checked disabled' : ''}
              onchange="completeSubtaskInBoard('${st.id}', this)">
            <label>${st.title}</label>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function toggleAccordion(id) {
  const body = document.getElementById(id);
  const arrow = document.getElementById('arrow-' + id);
  if (!body) return;
  body.classList.toggle('open');
  if (arrow) arrow.textContent = body.classList.contains('open') ? '▼' : '▶';
}

function formatRoutine(routine) {
  const days = ['월','화','수','목','금','토','일'];
  if (routine.type === 'daily') return '매일';
  if (routine.type === 'weekly') return '매주 ' + (routine.days || []).map(d => days[d]).join('·');
  if (routine.type === 'monthly') return '매월 ' + (routine.dates || []).join('·') + '일';
  return routine.type;
}

async function completeSubtaskInBoard(id, checkbox) {
  try {
    await api('POST', `/subtasks/${id}/complete`);
    await renderQuestContent();
  } catch (e) {
    checkbox.checked = false;
    alert(e.message);
  }
}

// ── NPC 상세 ─────────────────────────────────────────────
async function loadNPCDetail() {
  const npcs = await api('GET', '/npcs');
  state.npcs = npcs;
  const el = document.getElementById('npc-detail-list');
  el.innerHTML = npcs.map(npc => {
    const maxIntimacy = 100;
    const pct = Math.min((npc.intimacy_total / maxIntimacy) * 100, 100);
    return `
      <div class="card">
        <div style="display:flex;gap:16px;align-items:flex-start">
          <div style="text-align:center;min-width:60px">
            ${renderSprite(npc.sprite, npc.color)}
            <div style="color:var(--text);margin-top:4px">${npc.name}</div>
            <div style="color:var(--muted);font-size:10px">${npc.relationship}</div>
            <button class="btn btn-sm" style="margin-top:4px" onclick="regenSprite('${npc.id}')">재생성</button>
          </div>
          <div style="flex:1">
            <div style="color:var(--muted);font-size:10px;letter-spacing:1px;margin-bottom:4px">INTIMACY</div>
            <div class="intimacy-bar"><div class="intimacy-fill" style="width:${pct}%"></div></div>
            <div style="color:var(--muted);font-size:10px">${npc.intimacy_total} 누적</div>
            <button class="btn btn-sm" style="margin-top:8px;color:var(--red);border-color:var(--red)"
              onclick="deleteNPC('${npc.id}','${npc.name}')">삭제</button>
          </div>
        </div>
      </div>
    `;
  }).join('') || '<span style="color:var(--muted)">NPC 없음. 추가해보세요.</span>';
}

async function regenSprite(npcId) {
  await api('POST', `/npcs/${npcId}/regenerate-sprite`);
  await loadNPCDetail();
}

async function deleteNPC(id, name) {
  if (!confirm(`${name}을(를) 삭제할까요? 관련 퀘스트도 모두 삭제됩니다.`)) return;
  await api('DELETE', `/npcs/${id}`);
  await loadNPCDetail();
}

// ── 보상 관리 ─────────────────────────────────────────────
async function loadRewards() {
  const rewards = await api('GET', '/rewards');
  const el = document.getElementById('rewards-list');
  el.innerHTML = rewards.map(r => `
    <div class="card" style="display:flex;align-items:center;justify-content:space-between">
      <div>
        <span style="color:var(--yellow)">lv.${r.level}</span>
        <span style="margin-left:12px;color:var(--text)">${r.message}</span>
        ${r.is_claimed ? '<span style="margin-left:8px;color:var(--muted);font-size:10px">✓ 수령완료</span>' : ''}
      </div>
      <button class="btn btn-sm" onclick="deleteReward('${r.id}')">삭제</button>
    </div>
  `).join('') || '<span style="color:var(--muted)">설정된 보상 없음</span>';
}

async function deleteReward(id) {
  await api('DELETE', `/rewards/${id}`);
  await loadRewards();
}

async function claimReward() {
  if (!state.pendingRewardId) return;
  await api('POST', `/rewards/${state.pendingRewardId}/claim`);
  state.pendingRewardId = null;
  closeModal('modal-levelup');
  await loadDashboard();
}

// ── 모달 헬퍼 ─────────────────────────────────────────────
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

function openAddNPCModal() {
  document.getElementById('npc-name').value = '';
  document.getElementById('npc-relationship').value = '';
  document.getElementById('modal-npc').classList.add('open');
}

async function submitNPC() {
  const name = document.getElementById('npc-name').value.trim();
  const rel = document.getElementById('npc-relationship').value.trim();
  if (!name) return alert('이름을 입력하세요');
  await api('POST', '/npcs', { name, relationship: rel || '기타' });
  closeModal('modal-npc');
  await loadNPCDetail();
}

function openAddNeedModal(npcId) {
  const title = prompt('니즈 내용 입력:');
  if (!title) return;
  api('POST', '/needs', { npc_id: npcId || null, title }).then(() => renderQuestContent());
}

function openAddQuestModal(needId) {
  document.getElementById('quest-title').value = '';
  document.getElementById('quest-type').value = 'daily';
  document.getElementById('quest-reward').value = '10';
  document.getElementById('quest-need-id').value = needId || '';
  document.getElementById('routine-section').style.display = '';
  document.getElementById('routine-type').value = 'daily';
  document.getElementById('routine-days').style.display = 'none';
  document.getElementById('routine-dates').style.display = 'none';
  document.getElementById('modal-quest').classList.add('open');
}

function toggleRoutine() {
  const type = document.getElementById('quest-type').value;
  document.getElementById('routine-section').style.display = type === 'daily' ? '' : 'none';
}

function toggleRoutineDetail() {
  const type = document.getElementById('routine-type').value;
  document.getElementById('routine-days').style.display = type === 'weekly' ? '' : 'none';
  document.getElementById('routine-dates').style.display = type === 'monthly' ? '' : 'none';
}

async function submitQuest() {
  const title = document.getElementById('quest-title').value.trim();
  if (!title) return alert('제목을 입력하세요');

  const questType = document.getElementById('quest-type').value;
  const needId = document.getElementById('quest-need-id').value || null;
  const reward = parseInt(document.getElementById('quest-reward').value) || 10;

  let routine = null;
  if (questType === 'daily') {
    const rType = document.getElementById('routine-type').value;
    if (rType === 'daily') {
      routine = { type: 'daily' };
    } else if (rType === 'weekly') {
      const checked = [...document.querySelectorAll('#routine-days input:checked')].map(c => parseInt(c.value));
      if (!checked.length) return alert('요일을 선택하세요');
      routine = { type: 'weekly', days: checked };
    } else {
      const raw = document.getElementById('routine-dates-input').value;
      const dates = raw.split(',').map(d => parseInt(d.trim())).filter(d => d >= 1 && d <= 31);
      if (!dates.length) return alert('날짜를 입력하세요');
      routine = { type: 'monthly', dates };
    }
  }

  await api('POST', '/quests', {
    need_id: needId, title, quest_type: questType, routine, intimacy_reward: reward
  });
  closeModal('modal-quest');
  await renderQuestContent();
}

function openAddSubtaskModal(questId) {
  const title = prompt('서브태스크 내용:');
  if (!title) return;
  api('POST', '/subtasks', { quest_id: questId, title, order: 0 }).then(() => renderQuestContent());
}

function openAddRewardModal() {
  document.getElementById('reward-level').value = '';
  document.getElementById('reward-message').value = '';
  document.getElementById('modal-reward').classList.add('open');
}

async function submitReward() {
  const level = parseInt(document.getElementById('reward-level').value);
  const message = document.getElementById('reward-message').value.trim();
  if (!level || !message) return alert('레벨과 보상 내용을 입력하세요');
  await api('POST', '/rewards', { level, message });
  closeModal('modal-reward');
  await loadRewards();
}

// ── 초기화 ─────────────────────────────────────────────
loadDashboard();
```

- [ ] **Step 2: 커밋**

```bash
git add static/app.js
git commit -m "feat: frontend SPA JavaScript"
```

---

### Task 11: 텔레그램 봇

**Files:**
- Create: `app/telegram/formatter.py`
- Create: `app/telegram/handlers.py`
- Create: `app/telegram/bot.py`
- Modify: `app/main.py`

- [ ] **Step 1: app/telegram/formatter.py 작성**

```python
from datetime import date
from sqlalchemy.orm import Session
from app import models
from app.services.quest import is_quest_active_today, is_subtask_done_today
from app.services.happiness import calculate_happiness
from app.services.quest import _get_intimacy_total


def format_briefing(db: Session) -> tuple[str, list[dict]]:
    """
    오늘의 브리핑 텍스트와 인라인 버튼 목록을 반환한다.
    반환: (text, [[{"text": label, "callback_data": f"done:{subtask_id}"}]])
    """
    today = date.today()
    all_quests = db.query(models.Quest).filter_by(is_archived=False).all()
    active = [q for q in all_quests if is_quest_active_today(q, today)]

    lines = ["🎮 *LOVE QUEST — 오늘의 브리핑*\n"]
    buttons = []

    self_quests = [q for q in active if q.need_id is None]
    npc_quests = [q for q in active if q.need_id is not None]

    if self_quests:
        lines.append("*[ 나를 사랑하기 ]*")
        for q in self_quests:
            done = sum(1 for st in q.subtasks if is_subtask_done_today(db, st, today))
            lines.append(f"◆ {q.title} ({done}/{len(q.subtasks)})")
            for st in q.subtasks:
                done_st = is_subtask_done_today(db, st, today)
                mark = "☑" if done_st else "☐"
                lines.append(f"  {mark} {st.title}")
                if not done_st:
                    buttons.append([{"text": f"✓ {st.title[:20]}", "callback_data": f"done:{st.id}"}])
        lines.append("")

    if npc_quests:
        lines.append("*[ 타인을 사랑하기 ]*")
        for q in npc_quests:
            npc_name = q.need.npc.name if q.need and q.need.npc else "?"
            done = sum(1 for st in q.subtasks if is_subtask_done_today(db, st, today))
            lines.append(f"◆ {npc_name} — {q.title} ({done}/{len(q.subtasks)})")
            for st in q.subtasks:
                done_st = is_subtask_done_today(db, st, today)
                mark = "☑" if done_st else "☐"
                lines.append(f"  {mark} {st.title}")
                if not done_st:
                    buttons.append([{"text": f"✓ {st.title[:20]}", "callback_data": f"done:{st.id}"}])
        lines.append("")

    # 행복 레벨
    self_total = _get_intimacy_total(db, None)
    npc_ids = [row.id for row in db.query(models.NPC.id).all()]
    others = [_get_intimacy_total(db, nid) for nid in npc_ids]
    h = calculate_happiness(self_total, others)
    filled = "■" * h["filled_blocks"] + "□" * (h["total_blocks"] - h["filled_blocks"])
    lines.append(f"행복 레벨: {filled} lv\\.{h['level']}")

    return "\n".join(lines), buttons


def format_status(db: Session) -> str:
    self_total = _get_intimacy_total(db, None)
    npcs = db.query(models.NPC).all()
    others = [_get_intimacy_total(db, n.id) for n in npcs]
    h = calculate_happiness(self_total, others)

    lines = [
        "📊 *STATUS*\n",
        f"행복 레벨: lv\\.{h['level']} \\({round(h['progress']*100)}%\\)",
        f"나 자신 친밀도: {self_total}",
        "",
        "*[ NPC 친밀도 ]*",
    ]
    for npc, total in zip(npcs, others):
        lines.append(f"  {npc.name}: {total}")

    return "\n".join(lines)
```

- [ ] **Step 2: app/telegram/handlers.py 작성**

```python
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.database import SessionLocal
from app.telegram.formatter import format_briefing, format_status
from app.services.quest import complete_subtask


async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        text, button_rows = format_briefing(db)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"])]
             for row in button_rows for btn in row]
        ) if button_rows else None
        await update.message.reply_text(text, parse_mode="MarkdownV2", reply_markup=keyboard)
    finally:
        db.close()


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        text = format_status(db)
        await update.message.reply_text(text, parse_mode="MarkdownV2")
    finally:
        db.close()


async def callback_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    subtask_id = query.data.replace("done:", "")
    db = SessionLocal()
    try:
        result = complete_subtask(db, subtask_id)
        if result["subtask_done"]:
            msg = "✅ 완료!"
            if result["quest_done"]:
                msg += " 퀘스트 달성! 🎉"
            if result["level_up"]:
                msg += f"\n🎊 LEVEL UP! lv.{result['level_up']}"
            await query.edit_message_text(query.message.text + f"\n\n{msg}", parse_mode="MarkdownV2")
        else:
            await query.answer("이미 완료됐어요!")
    finally:
        db.close()
```

- [ ] **Step 3: app/telegram/bot.py 작성**

```python
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from app.config import TELEGRAM_TOKEN
from app.telegram.handlers import cmd_brief, cmd_status, callback_done

_app: Application = None


def get_bot_app() -> Application:
    global _app
    if _app is None:
        _app = (
            Application.builder()
            .token(TELEGRAM_TOKEN)
            .build()
        )
        _app.add_handler(CommandHandler("brief", cmd_brief))
        _app.add_handler(CommandHandler("quests", cmd_brief))   # alias
        _app.add_handler(CommandHandler("status", cmd_status))
        _app.add_handler(CallbackQueryHandler(callback_done, pattern="^done:"))
    return _app
```

- [ ] **Step 4: app/main.py 텔레그램 웹훅 추가**

```python
import json
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from telegram import Update
from app.routers import npcs, needs, quests, subtasks, rewards, dashboard
from app.config import TELEGRAM_TOKEN, WEBHOOK_BASE_URL
from app.telegram.bot import get_bot_app

app = FastAPI(title="Love Quest")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(npcs.router)
app.include_router(needs.router)
app.include_router(quests.router)
app.include_router(subtasks.router)
app.include_router(rewards.router)
app.include_router(dashboard.router)


@app.on_event("startup")
async def on_startup():
    bot = get_bot_app()
    await bot.initialize()
    if WEBHOOK_BASE_URL:
        webhook_url = f"{WEBHOOK_BASE_URL}/telegram/webhook"
        await bot.bot.set_webhook(webhook_url)
    _start_scheduler()


@app.on_event("shutdown")
async def on_shutdown():
    bot = get_bot_app()
    await bot.shutdown()


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    bot = get_bot_app()
    update = Update.de_json(data, bot.bot)
    await bot.process_update(update)
    return Response(status_code=200)


def _start_scheduler():
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from app.config import BRIEFING_HOUR, BRIEFING_MINUTE, TELEGRAM_CHAT_ID
    from app.database import SessionLocal
    from app.telegram.formatter import format_briefing
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton

    scheduler = AsyncIOScheduler()

    async def send_daily_brief():
        db = SessionLocal()
        try:
            text, button_rows = format_briefing(db)
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"])]
                 for row in button_rows for btn in row]
            ) if button_rows else None
            bot = get_bot_app()
            await bot.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=keyboard,
            )
        finally:
            db.close()

    scheduler.add_job(send_daily_brief, "cron", hour=BRIEFING_HOUR, minute=BRIEFING_MINUTE)
    scheduler.start()


@app.get("/")
def root():
    return FileResponse("static/index.html")
```

- [ ] **Step 5: 로컬 동작 확인**

```bash
# .env 파일 생성 후
uvicorn app.main:app --reload
# http://localhost:8000 접속 확인
```

- [ ] **Step 6: 커밋**

```bash
git add app/telegram/ app/main.py
git commit -m "feat: telegram bot + daily scheduler"
```

---

### Task 12: Railway 배포

**Files:**
- Create: `railway.toml`
- Create: `.gitignore`
- Create: `Procfile`

- [ ] **Step 1: .gitignore 작성**

```
.env
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
.superpowers/
```

- [ ] **Step 2: railway.toml 작성**

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
```

- [ ] **Step 3: Railway 프로젝트 생성 및 배포**

Railway 웹사이트에서 진행:
1. railway.app → New Project → Deploy from GitHub
2. PostgreSQL 플러그인 추가 → `DATABASE_URL` 자동 주입 확인
3. Variables 탭에서 환경변수 입력:
   - `TELEGRAM_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `WEBHOOK_BASE_URL` = `https://<your-app>.railway.app`
   - `BRIEFING_HOUR`, `BRIEFING_MINUTE`

- [ ] **Step 4: 웹훅 등록 확인**

배포 후 로그에서 확인:
```
INFO: Webhook set to https://<your-app>.railway.app/telegram/webhook
```

텔레그램에서 `/brief` 명령어 테스트.

- [ ] **Step 5: 최종 커밋**

```bash
git add railway.toml .gitignore
git commit -m "feat: railway deployment config"
```

---

## 자체 검토 결과

| 스펙 요구사항 | 구현 태스크 |
|---|---|
| 웹앱 + 무료 서버 | Task 1 (FastAPI) + Task 12 (Railway) |
| NPC 등록 + 캐릭터 | Task 4 (NPC API) + Task 4 (Sprite) |
| NPC 니즈 → 퀘스트 드릴다운 | Task 8 (퀘스트 보드 accordion) |
| daily/one-time 퀘스트 + 루틴 설정 | Task 6 (Quest API) + Task 10 (JS) |
| 서브태스크 전부 완료 → 퀘스트 완료 | Task 6 (quest.py service) |
| 친밀도 무한 누적 | Task 6 (intimacy_logs, no clamp) |
| 행복 레벨 (픽셀 블록) | Task 5 (happiness.py) + Task 9/10 (UI) |
| 레벨업 보상 메시지 | Task 8 (rewards router) + Task 10 (popup) |
| 텔레그램 일일 브리핑 | Task 11 (formatter + scheduler) |
| 텔레그램 완료 처리 | Task 11 (callback_done handler) |
| /brief /quests /status | Task 11 (handlers.py) |
