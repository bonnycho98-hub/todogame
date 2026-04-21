import json
import google.generativeai as genai
from app.config import GEMINI_API_KEY

_model = None


def _get_model():
    global _model
    if _model is None:
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-2.5-flash")
    return _model


_SCHEMA ='{"type": "quest 또는 need", "npc_id": "UUID문자열 또는 null", "title": "제목", "subtasks": ["항목1", "항목2"], "quest_type": "one_time 또는 daily", "need_id": "기존 니즈 UUID 또는 null (quest일 때만)"}'

_CRITERIA = """판단 기준:
- need: 바람/욕구/관계적 필요 (예: "엄마가 보고싶다")
- quest: 실행 가능한 행동 (예: "엄마 선물 보내기")
- daily: 반복 습관 (예: "매일 물 2L")
- one_time: 일회성 작업
- npc_id: NPC 목록에서 관련 NPC의 id, 없으면 null
- subtasks: 퀘스트를 위한 세부 단계들, need이면 반드시 빈 배열
- need_id: quest일 때 기존 니즈 목록에서 가장 잘 연결되는 니즈의 id. 의미적으로 가장 가까운 니즈 하나를 반드시 골라야 함. 니즈 목록이 비어있을 때만 null.
- need의 title 작성 규칙: 사용자가 말한 핵심 의미와 구체적인 키워드는 살리되, 캐릭터의 목소리로 자연스럽게 다듬는다. 원문을 그대로 복붙하거나 과도하게 추상화하지 말 것. NPC가 있으면 그 NPC 캐릭터가 주인공에게 직접 말하는 게임 대사 스타일로 작성 (예: npc=엄마, 입력="엄마가 보고싶다" → "보고 싶었어, 우리 아이. 엄마도 네 생각 많이 했어."). NPC가 없으면 주인공이 자신의 목소리로 욕구를 직접 말하는 스타일로 작성 — 감정의 온도에 맞게 열정적일 수도, 잔잔할 수도 있음 (예: 입력="더 성장하고 싶고 멋진 결과물을 만들고 싶은 사람들이 가득한 환경에서 일하고 싶어" → "성장하고 싶어. 멋진 결과물을 함께 만드는 사람들 사이에서 일하고 싶어!", 입력="그냥 쉬고 싶다 오늘" → "오늘은 그냥 쉬어도 괜찮아. 충분히 달려왔잖아.")"""


def parse_intake(
    text: str,
    npcs: list[dict],
    needs: list[dict] | None = None,
    previous_result: dict | None = None,
    correction: str | None = None,
) -> dict:
    """자유 텍스트를 Gemini로 분석해 구조화된 dict를 반환한다.

    Args:
        text: 사용자 원문 (수정 모드에선 무시됨)
        npcs: [{"id": "uuid", "name": "이름"}, ...]
        needs: [{"id": "uuid", "title": "제목"}, ...] — quest 연결용 기존 니즈 목록
        previous_result: 수정 모드일 때 이전 AI 결과
        correction: 수정 모드일 때 사용자의 수정 지시

    Returns:
        {"type", "npc_id", "title", "subtasks", "quest_type", "need_id"}

    Raises:
        ValueError: Gemini 응답이 JSON으로 파싱되지 않을 때
    """
    npc_json = json.dumps(npcs, ensure_ascii=False)
    needs_json = json.dumps(needs or [], ensure_ascii=False)

    if previous_result and correction:
        prompt = f"""당신은 할일 관리 앱의 입력 파서입니다.
JSON만 응답하세요. 마크다운 코드블록 없이 순수 JSON만.

등록된 NPC 목록: {npc_json}
기존 니즈 목록: {needs_json}

이전 결과: {json.dumps(previous_result, ensure_ascii=False)}
수정 지시: {correction}

{_CRITERIA}

응답 형식: {_SCHEMA}"""
    else:
        prompt = f"""당신은 할일 관리 앱의 입력 파서입니다.
JSON만 응답하세요. 마크다운 코드블록 없이 순수 JSON만.

등록된 NPC 목록: {npc_json}
기존 니즈 목록: {needs_json}

사용자 입력: {text}

{_CRITERIA}

응답 형식: {_SCHEMA}"""

    response = _get_model().generate_content(prompt)
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
        result["need_id"] = None
    elif result.get("type") == "quest":
        if result.get("quest_type") not in ("one_time", "daily"):
            result["quest_type"] = "one_time"
        # need_id 검증: 실제 존재하는 니즈 id인지 확인
        valid_need_ids = {n["id"] for n in (needs or [])}
        if result.get("need_id") not in valid_need_ids:
            result["need_id"] = None

    return result


def save_intake(db, result: dict) -> None:
    """parse_intake 결과를 DB에 저장한다."""
    import uuid as _uuid
    from app import models

    raw_npc_id = result.get("npc_id")
    npc_id = _uuid.UUID(raw_npc_id) if raw_npc_id else None

    if result["type"] == "need":
        need = models.Need(npc_id=npc_id, title=result["title"])
        db.add(need)
        db.commit()
        return

    # quest — 기존 니즈에 연결하거나 새 니즈 생성
    raw_need_id = result.get("need_id")
    if raw_need_id:
        need_id = _uuid.UUID(raw_need_id)
    else:
        need = models.Need(npc_id=npc_id, title=result["title"])
        db.add(need)
        db.flush()
        need_id = need.id

    qt = result.get("quest_type", "one_time")
    if qt not in ("one_time", "daily"):
        qt = "one_time"
    routine = result.get("routine") if qt == "daily" else None
    if qt == "daily" and routine is None:
        routine = {"type": "daily"}
    quest = models.Quest(
        need_id=need_id,
        title=result["title"],
        quest_type=qt,
        routine=routine,
        intimacy_reward=10,
    )
    db.add(quest)
    db.flush()
    for i, st_title in enumerate(result.get("subtasks", [])):
        db.add(models.Subtask(quest_id=quest.id, title=st_title, order=i))
    db.commit()
