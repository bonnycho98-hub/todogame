# Telegram AI Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 텔레그램에 자유 텍스트를 보내면 Gemini AI가 니즈/퀘스트로 분류·구조화하고, 사용자 확인(+ 자연어 수정) 후 DB에 저장한다.

**Architecture:** 기존 python-telegram-bot ConversationHandler 패턴 사용. `app/services/ai_intake.py`가 Gemini API를 호출해 구조화 JSON 반환. 핸들러가 상태머신(AWAITING_CONFIRM) 관리. 저장은 기존 models.Need / models.Quest 재활용.

**Tech Stack:** FastAPI, python-telegram-bot 21.x, google-generativeai, SQLAlchemy (sync), SQLite(test)/PostgreSQL(prod)

---

## File Map

| 파일 | 유형 | 역할 |
|------|------|------|
| `requirements.txt` | Modify | `google-generativeai` 추가 |
| `.env.example` | Modify | `GEMINI_API_KEY=` 추가 |
| `app/config.py` | Modify | `GEMINI_API_KEY` 환경변수 로드 |
| `app/services/ai_intake.py` | Create | Gemini 호출 + JSON 파싱 + DB 저장 |
| `tests/test_ai_intake.py` | Create | `parse_intake` 단위 테스트 (Gemini mock) |
| `app/telegram/handlers.py` | Modify | 자유텍스트·수정·저장·취소 핸들러 추가 |
| `app/telegram/bot.py` | Modify | ConversationHandler 등록 |

---

### Task 1: 환경 설정 — requirements, config, env

**Files:**
- Modify: `requirements.txt`
- Modify: `app/config.py`
- Modify: `.env.example`

- [ ] **Step 1: requirements.txt에 패키지 추가**

`requirements.txt` 끝에 추가:

```
google-generativeai>=0.7.0
```

- [ ] **Step 2: config.py에 GEMINI_API_KEY 추가**

`app/config.py` 전체를 다음으로 교체:

```python
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")
BRIEFING_HOUR = int(os.environ.get("BRIEFING_HOUR", "8"))
BRIEFING_MINUTE = int(os.environ.get("BRIEFING_MINUTE", "0"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
```

- [ ] **Step 3: .env.example에 키 추가**

`.env.example` 파일 끝에 추가:

```
GEMINI_API_KEY=your_google_ai_studio_key_here
```

- [ ] **Step 4: 패키지 설치**

```bash
pip install "google-generativeai>=0.7.0"
```

Expected: 설치 완료 (에러 없음)

- [ ] **Step 5: 커밋**

```bash
git add requirements.txt app/config.py .env.example
git commit -m "chore: add Gemini API key config and dependency"
```

---

### Task 2: AI Intake 서비스 + 테스트

**Files:**
- Create: `app/services/ai_intake.py`
- Create: `tests/test_ai_intake.py`

- [ ] **Step 1: 테스트 파일 작성**

`tests/test_ai_intake.py` 파일 생성:

```python
import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_intake import parse_intake

NPCS = [{"id": "11111111-1111-1111-1111-111111111111", "name": "엄마"}]


def _mock_gemini(json_str: str):
    """Gemini _model을 모킹하는 컨텍스트 매니저를 반환한다."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = json_str
    return patch("app.services.ai_intake._model", mock_model)


def test_parse_quest_with_npc():
    response = '{"type": "quest", "npc_id": "11111111-1111-1111-1111-111111111111", "title": "생일 선물", "subtasks": ["구매", "포장"], "quest_type": "one_time"}'
    with _mock_gemini(response):
        result = parse_intake("엄마 생일 선물 사고 포장하기", NPCS)
    assert result["type"] == "quest"
    assert result["npc_id"] == "11111111-1111-1111-1111-111111111111"
    assert result["title"] == "생일 선물"
    assert result["subtasks"] == ["구매", "포장"]
    assert result["quest_type"] == "one_time"


def test_parse_need_without_npc():
    response = '{"type": "need", "npc_id": null, "title": "운동하고싶어", "subtasks": [], "quest_type": null}'
    with _mock_gemini(response):
        result = parse_intake("운동하고싶어", [])
    assert result["type"] == "need"
    assert result["npc_id"] is None
    assert result["subtasks"] == []
    assert result["quest_type"] is None


def test_parse_with_correction():
    previous = {
        "type": "quest",
        "npc_id": "11111111-1111-1111-1111-111111111111",
        "title": "생일 선물",
        "subtasks": ["구매", "포장"],
        "quest_type": "one_time",
    }
    response = '{"type": "quest", "npc_id": "11111111-1111-1111-1111-111111111111", "title": "생일 선물", "subtasks": ["구매", "포장", "카드 쓰기"], "quest_type": "one_time"}'
    with _mock_gemini(response):
        result = parse_intake("", NPCS, previous_result=previous, correction="카드 쓰기도 추가해줘")
    assert "카드 쓰기" in result["subtasks"]
    assert len(result["subtasks"]) == 3


def test_parse_strips_markdown_codeblock():
    response = '```json\n{"type": "need", "npc_id": null, "title": "물 마시기", "subtasks": [], "quest_type": null}\n```'
    with _mock_gemini(response):
        result = parse_intake("물 마시기", [])
    assert result["title"] == "물 마시기"


def test_parse_invalid_json_raises_value_error():
    with _mock_gemini("이건 JSON이 아닙니다"):
        with pytest.raises((ValueError, Exception)):
            parse_intake("뭔가 입력", [])


def test_parse_need_subtasks_always_empty():
    """need 타입이면 Gemini가 subtasks를 반환해도 []로 정규화한다."""
    response = '{"type": "need", "npc_id": null, "title": "운동", "subtasks": ["뭔가"], "quest_type": null}'
    with _mock_gemini(response):
        result = parse_intake("운동하고싶어", [])
    assert result["subtasks"] == []
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/bonny/Dev/todogame
pytest tests/test_ai_intake.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.ai_intake'`

- [ ] **Step 3: ai_intake.py 구현**

`app/services/ai_intake.py` 파일 생성:

```python
import json
import google.generativeai as genai
from app.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.0-flash")

_SCHEMA = '{"type": "quest 또는 need", "npc_id": "UUID문자열 또는 null", "title": "제목", "subtasks": ["항목1", "항목2"], "quest_type": "one_time 또는 daily"}'

_CRITERIA = """판단 기준:
- need: 바람/욕구/관계적 필요 (예: "엄마가 보고싶다")
- quest: 실행 가능한 행동 (예: "엄마 선물 보내기")
- daily: 반복 습관 (예: "매일 물 2L")
- one_time: 일회성 작업
- npc_id: NPC 목록에서 관련 NPC의 id, 없으면 null
- subtasks: 퀘스트를 위한 세부 단계들, need이면 반드시 빈 배열"""


def parse_intake(
    text: str,
    npcs: list[dict],
    previous_result: dict | None = None,
    correction: str | None = None,
) -> dict:
    """자유 텍스트를 Gemini로 분석해 구조화된 dict를 반환한다.

    Args:
        text: 사용자 원문 (수정 모드에선 무시됨)
        npcs: [{"id": "uuid", "name": "이름"}, ...]
        previous_result: 수정 모드일 때 이전 AI 결과
        correction: 수정 모드일 때 사용자의 수정 지시

    Returns:
        {"type", "npc_id", "title", "subtasks", "quest_type"}

    Raises:
        ValueError: Gemini 응답이 JSON으로 파싱되지 않을 때
    """
    npc_json = json.dumps(npcs, ensure_ascii=False)

    if previous_result and correction:
        prompt = f"""당신은 할일 관리 앱의 입력 파서입니다.
JSON만 응답하세요. 마크다운 코드블록 없이 순수 JSON만.

등록된 NPC 목록: {npc_json}

이전 결과: {json.dumps(previous_result, ensure_ascii=False)}
수정 지시: {correction}

{_CRITERIA}

응답 형식: {_SCHEMA}"""
    else:
        prompt = f"""당신은 할일 관리 앱의 입력 파서입니다.
JSON만 응답하세요. 마크다운 코드블록 없이 순수 JSON만.

등록된 NPC 목록: {npc_json}

사용자 입력: {text}

{_CRITERIA}

응답 형식: {_SCHEMA}"""

    response = _model.generate_content(prompt)
    raw = response.text.strip()

    # 마크다운 코드블록 제거
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini 응답 파싱 실패: {e}\n원문: {raw}")

    # 정규화
    if result.get("npc_id") in ("null", "", None):
        result["npc_id"] = None
    if result.get("type") == "need":
        result["subtasks"] = []
        result["quest_type"] = None

    return result


def save_intake(db, result: dict) -> None:
    """parse_intake 결과를 DB에 저장한다."""
    from app import models

    npc_id = result.get("npc_id")

    if result["type"] == "need":
        need = models.Need(npc_id=npc_id, title=result["title"])
        db.add(need)
        db.commit()
        return

    # quest
    if npc_id:
        need = models.Need(npc_id=npc_id, title=result["title"])
        db.add(need)
        db.flush()
        need_id = need.id
    else:
        need_id = None

    quest = models.Quest(
        need_id=need_id,
        title=result["title"],
        quest_type=result["quest_type"],
        intimacy_reward=10,
    )
    db.add(quest)
    db.flush()
    for i, st_title in enumerate(result.get("subtasks", [])):
        db.add(models.Subtask(quest_id=quest.id, title=st_title, order=i))
    db.commit()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_ai_intake.py -v
```

Expected: 6개 모두 PASS

- [ ] **Step 5: 전체 테스트 통과 확인**

```bash
pytest tests/ -v
```

Expected: 모두 PASS

- [ ] **Step 6: 커밋**

```bash
git add app/services/ai_intake.py tests/test_ai_intake.py
git commit -m "feat: add AI intake service with Gemini + unit tests"
```

---

### Task 3: 텔레그램 핸들러 추가

**Files:**
- Modify: `app/telegram/handlers.py`

- [ ] **Step 1: handlers.py 전체 교체**

`app/telegram/handlers.py` 를 다음으로 교체:

```python
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Message
from telegram.ext import ContextTypes, ConversationHandler
from app.database import get_session_local
from app.telegram.formatter import format_briefing, format_status
from app.services.quest import complete_subtask
from app import models

# ConversationHandler 상태
AWAITING_CONFIRM = 1


# ── 기존 커맨드 핸들러 ────────────────────────────────────────────

async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_session_local()()
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
    db = get_session_local()()
    try:
        text = format_status(db)
        await update.message.reply_text(text, parse_mode="MarkdownV2")
    finally:
        db.close()


async def callback_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    subtask_id = query.data.replace("done:", "")
    db = get_session_local()()
    try:
        result = complete_subtask(db, subtask_id)
        if result["subtask_done"]:
            msg = "✅ 완료!"
            if result["quest_done"]:
                msg += " 퀘스트 달성! 🎉"
            if result["level_up"]:
                msg += f"\n🎊 LEVEL UP\\! lv\\.{result['level_up']}"
            await query.edit_message_text(query.message.text + f"\n\n{msg}", parse_mode="MarkdownV2")
        else:
            await query.answer("이미 완료됐어요!")
    finally:
        db.close()


# ── AI Intake 핸들러 ────────────────────────────────────────────

async def handle_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """자유 텍스트 수신 → Gemini 처리 → 결과 표시."""
    from app.services.ai_intake import parse_intake

    text = update.message.text
    processing_msg = await update.message.reply_text("⏳ 처리 중...")

    db = get_session_local()()
    try:
        npcs = [{"id": str(n.id), "name": n.name} for n in db.query(models.NPC).all()]
    finally:
        db.close()

    try:
        result = parse_intake(text, npcs)
    except Exception:
        await processing_msg.edit_text("처리 중 오류가 났어요. 다시 입력해주세요.")
        return ConversationHandler.END

    context.user_data["current_result"] = result
    context.user_data["original_text"] = text

    result_msg = await _send_result(update, result)
    context.user_data["result_message_id"] = result_msg.message_id
    await processing_msg.delete()
    return AWAITING_CONFIRM


async def handle_correction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """수정 지시 텍스트 수신 → Gemini 재처리 → 결과 표시."""
    from app.services.ai_intake import parse_intake

    correction = update.message.text
    previous_result = context.user_data.get("current_result")
    original_text = context.user_data.get("original_text", "")

    processing_msg = await update.message.reply_text("⏳ 수정 중...")

    db = get_session_local()()
    try:
        npcs = [{"id": str(n.id), "name": n.name} for n in db.query(models.NPC).all()]
    finally:
        db.close()

    try:
        result = parse_intake(
            text=original_text,
            npcs=npcs,
            previous_result=previous_result,
            correction=correction,
        )
    except Exception:
        await processing_msg.edit_text("수정 중 오류가 났어요. 다시 수정 지시를 보내주세요.")
        return AWAITING_CONFIRM

    context.user_data["current_result"] = result
    result_msg = await _send_result(update, result)
    context.user_data["result_message_id"] = result_msg.message_id
    await processing_msg.delete()
    return AWAITING_CONFIRM


async def handle_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """[✓ 저장] 버튼 → DB 저장 → 종료."""
    from app.services.ai_intake import save_intake

    query = update.callback_query
    await query.answer()

    result = context.user_data.get("current_result")
    db = get_session_local()()
    try:
        save_intake(db, result)
    finally:
        db.close()

    await query.edit_message_text("✅ 저장됐어요!")
    context.user_data.clear()
    return ConversationHandler.END


async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """[✗ 취소] 버튼 → 대화 종료."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("취소했어요.")
    context.user_data.clear()
    return ConversationHandler.END


# ── 내부 헬퍼 ────────────────────────────────────────────────────

def _format_result_text(result: dict, npc_name: str | None) -> str:
    type_label = "📋 퀘스트" if result["type"] == "quest" else "💬 니즈"
    npc_label = npc_name if npc_name else "나"
    lines = [
        f"{type_label} · {npc_label}",
        "",
        result["title"],
    ]
    for st in result.get("subtasks", []):
        lines.append(f"  • {st}")
    lines.append("")
    lines.append("수정하려면 이 메시지에 답장하세요.")
    return "\n".join(lines)


async def _send_result(update: Update, result: dict) -> Message:
    db = get_session_local()()
    try:
        npc_name = None
        if result.get("npc_id"):
            npc = db.get(models.NPC, result["npc_id"])
            npc_name = npc.name if npc else None
    finally:
        db.close()

    text = _format_result_text(result, npc_name)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✓ 저장", callback_data="save"),
        InlineKeyboardButton("✗ 취소", callback_data="cancel"),
    ]])
    return await update.effective_message.reply_text(text, reply_markup=keyboard)
```

- [ ] **Step 2: 전체 테스트 통과 확인**

```bash
pytest tests/ -v
```

Expected: 모두 PASS (핸들러는 통합 테스트 없음, 기존 테스트가 깨지지 않아야 함)

- [ ] **Step 3: 커밋**

```bash
git add app/telegram/handlers.py
git commit -m "feat: add telegram free-text and AI intake handlers"
```

---

### Task 4: ConversationHandler 등록

**Files:**
- Modify: `app/telegram/bot.py`

- [ ] **Step 1: bot.py 전체 교체**

`app/telegram/bot.py` 를 다음으로 교체:

```python
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters,
)
from app.config import TELEGRAM_TOKEN, GEMINI_API_KEY
from app.telegram.handlers import (
    cmd_brief, cmd_status, callback_done,
    handle_free_text, handle_correction, handle_save, handle_cancel,
    AWAITING_CONFIRM,
)

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

        if GEMINI_API_KEY:
            conv_handler = ConversationHandler(
                entry_points=[
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_text),
                ],
                states={
                    AWAITING_CONFIRM: [
                        CallbackQueryHandler(handle_save, pattern="^save$"),
                        CallbackQueryHandler(handle_cancel, pattern="^cancel$"),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_correction),
                    ],
                },
                fallbacks=[
                    CallbackQueryHandler(handle_cancel, pattern="^cancel$"),
                ],
                conversation_timeout=300,
            )
            _app.add_handler(conv_handler)
        else:
            import logging
            logging.warning("GEMINI_API_KEY not set — AI intake handler disabled")

    return _app
```

- [ ] **Step 2: 전체 테스트 통과 확인**

```bash
pytest tests/ -v
```

Expected: 모두 PASS

- [ ] **Step 3: 커밋**

```bash
git add app/telegram/bot.py
git commit -m "feat: register ConversationHandler for AI intake (disabled if no GEMINI_API_KEY)"
```

---

## 배포

Railway 환경변수에 `GEMINI_API_KEY` 추가 후 푸시:

```bash
git push
```

Railway 대시보드 → Variables → `GEMINI_API_KEY` 추가.  
Google AI Studio(aistudio.google.com)에서 발급한 키 사용.

---

## 수동 테스트 체크리스트

Railway 배포 또는 로컬 ngrok 터널 후:

1. 텔레그램에서 "엄마 생일 선물 사고 포장해서 보내기" 전송
2. "⏳ 처리 중..." 메시지 확인
3. 결과 메시지에 `📋 퀘스트 · 엄마` + 서브태스크 표시 확인
4. `[✓ 저장]` `[✗ 취소]` 버튼 표시 확인
5. 결과 메시지에 답장으로 "카드 쓰기도 추가해줘" 전송
6. 수정된 결과 재표시 확인
7. `[✓ 저장]` 클릭 → "✅ 저장됐어요!" 확인
8. 웹 대시보드에서 퀘스트 생성 확인
9. `[✗ 취소]` 시나리오도 확인
