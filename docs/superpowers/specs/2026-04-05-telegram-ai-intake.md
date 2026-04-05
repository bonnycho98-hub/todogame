# Telegram AI Intake Design Spec

**Date:** 2026-04-05  
**Feature:** 텔레그램 자유 텍스트 → AI 구조화 → 니즈/퀘스트 저장

---

## 목표

컴퓨터 없이 이동 중에도 텔레그램으로 자유롭게 할일/니즈를 입력하면, AI가 자동으로 분류·구조화하고 사용자 확인 후 DB에 저장한다.

---

## 사용자 플로우

1. 사용자가 텔레그램에 자유 텍스트 전송 (커맨드 아님)
2. 봇이 "처리 중..." 메시지 전송
3. Gemini API가 텍스트를 분석해 구조화된 JSON 반환
4. 봇이 결과를 포맷해서 표시 + `[✓ 저장]` `[✗ 취소]` 버튼
5. 사용자가 결과 메시지에 **답장**으로 수정 지시 → AI 재처리 → 4번 반복
6. `[✓ 저장]` 클릭 → DB 저장 → 완료 메시지
7. `[✗ 취소]` 클릭 → 대화 종료

---

## 아키텍처

### 새 파일

| 파일 | 역할 |
|------|------|
| `app/services/ai_intake.py` | Gemini API 호출, 텍스트 → 구조화 JSON |

### 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `app/telegram/handlers.py` | `handle_free_text`, `handle_correction`, `handle_save`, `handle_cancel` 추가 |
| `app/telegram/bot.py` | `ConversationHandler` 등록 |
| `app/config.py` | `GEMINI_API_KEY` 환경변수 추가 |
| `requirements.txt` | `google-generativeai` 추가 |
| `.env.example` | `GEMINI_API_KEY=` 추가 |

---

## AI Intake 서비스 (`app/services/ai_intake.py`)

### 입력

```python
def parse_intake(
    text: str,
    npcs: list[dict],          # [{"id": "...", "name": "엄마"}, ...]
    previous_result: dict | None = None,   # 이전 AI 결과 (수정 시)
    correction: str | None = None,         # 수정 지시 텍스트
) -> dict
```

### Gemini 프롬프트 구조

```
당신은 할일 관리 앱의 입력 파서입니다.
JSON만 응답하세요. 설명 없이.

등록된 NPC 목록: {npc_list_json}

[수정 모드일 때만]
이전 결과: {previous_result_json}
수정 지시: {correction}

[최초 입력일 때]
사용자 입력: {text}

판단 기준:
- need: 바람/욕구/관계적 필요 (예: "엄마가 보고싶다")
- quest: 실행 가능한 행동 (예: "엄마 선물 보내기")
- daily: 반복 습관 (예: "매일 물 2L")
- one_time: 일회성 작업

응답 형식:
{
  "type": "quest" | "need",
  "npc_id": "<UUID 또는 null>",
  "title": "...",
  "subtasks": ["...", "..."],
  "quest_type": "one_time" | "daily"
}
```

### 반환값

```python
{
    "type": "quest",           # "quest" | "need"
    "npc_id": "uuid-or-null",  # null = 나 자신
    "title": "엄마 생일 선물",
    "subtasks": ["선물 구매", "포장", "발송"],  # need이면 []
    "quest_type": "one_time"   # need이면 None
}
```

### 에러 처리

- JSON 파싱 실패 → `ValueError` 발생 → 핸들러에서 "다시 시도해주세요" 메시지
- Gemini API 오류 → 동일하게 재시도 안내

---

## ConversationHandler 상태

```
AWAITING_CONFIRM = 1

States:
  ConversationHandler.END
    → MessageHandler(TEXT, handle_free_text)
    → AWAITING_CONFIRM

  AWAITING_CONFIRM
    → CallbackQueryHandler("save:", handle_save) → END
    → CallbackQueryHandler("cancel:", handle_cancel) → END
    → MessageHandler(REPLY, handle_correction) → AWAITING_CONFIRM
```

### 컨텍스트 저장 (`context.user_data`)

```python
{
    "current_result": { ... },   # 현재 AI 결과
    "original_text": "...",      # 최초 입력 텍스트
    "result_message_id": 123,    # 수정 답장 대상 메시지 ID
}
```

### 메시지 포맷

```
📋 퀘스트 · 엄마           (need이면 💬 니즈 · 엄마)
                           (npc_id=null이면 · 나)
생일 선물
  • 선물 구매
  • 포장
  • 발송

[✓ 저장]  [✗ 취소]
수정하려면 이 메시지에 답장하세요.
```

---

## DB 저장 로직

Quest 모델은 `need_id`를 통해서만 NPC와 연결된다. 따라서 NPC가 지정된 퀘스트는 Need를 자동 생성해 연결한다.

### type = "quest" + npc_id 있음

```python
# NPC와 연결하기 위해 Need 자동 생성
need = Need(npc_id=result["npc_id"], title=result["title"])
db.add(need)
db.flush()
quest = Quest(need_id=need.id, title=result["title"],
              quest_type=result["quest_type"], intimacy_reward=10)
db.add(quest)
db.flush()
for i, st_title in enumerate(result["subtasks"]):
    db.add(Subtask(quest_id=quest.id, title=st_title, order=i))
db.commit()
```

### type = "quest" + npc_id 없음 (나 자신)

```python
quest = Quest(need_id=None, title=result["title"],
              quest_type=result["quest_type"], intimacy_reward=10)
db.add(quest)
db.flush()
for i, st_title in enumerate(result["subtasks"]):
    db.add(Subtask(quest_id=quest.id, title=st_title, order=i))
db.commit()
```

### type = "need"

```python
need = Need(
    npc_id=result["npc_id"],  # None = 나 자신
    title=result["title"],
)
db.add(need)
db.commit()
```

---

## 엣지 케이스

| 상황 | 처리 |
|------|------|
| NPC 추론 불가 | `npc_id: null` → 나 자신 할일로 저장 |
| JSON 파싱 실패 | "처리 중 오류가 났어요. 다시 입력해주세요." |
| 5분 타임아웃 | ConversationHandler 자동 종료 (`conversation_timeout=300`) |
| subtasks 빈 배열 | quest 저장 시 서브태스크 없이 저장 |
| `GEMINI_API_KEY` 미설정 | 봇 시작 시 경고 로그, 해당 핸들러 비활성화 |

---

## 환경변수

```
GEMINI_API_KEY=your_key_here   # Google AI Studio에서 발급
```

---

## 테스트 범위

- `test_ai_intake.py` — `parse_intake` 단위 테스트 (Gemini API mock)
  - 퀘스트 분류 + NPC 매핑
  - 니즈 분류
  - 수정 지시 반영
  - JSON 파싱 오류 처리
