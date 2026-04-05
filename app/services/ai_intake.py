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
