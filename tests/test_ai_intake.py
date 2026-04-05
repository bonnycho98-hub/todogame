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
        with pytest.raises(ValueError):
            parse_intake("뭔가 입력", [])


def test_parse_need_subtasks_always_empty():
    """need 타입이면 Gemini가 subtasks를 반환해도 []로 정규화한다."""
    response = '{"type": "need", "npc_id": null, "title": "운동", "subtasks": ["뭔가"], "quest_type": null}'
    with _mock_gemini(response):
        result = parse_intake("운동하고싶어", [])
    assert result["subtasks"] == []


# ── save_intake 테스트 ──────────────────────────────────────────

def test_save_intake_need(db):
    """need 타입은 Need 레코드 하나만 생성한다."""
    from app import models
    result = {"type": "need", "npc_id": None, "title": "운동하고싶어", "subtasks": [], "quest_type": None}
    from app.services.ai_intake import save_intake
    save_intake(db, result)
    need = db.query(models.Need).filter_by(title="운동하고싶어").first()
    assert need is not None
    assert need.npc_id is None


def test_save_intake_quest_without_npc(db):
    """quest + npc_id 없음 → Quest(need_id=None) + Subtask 생성."""
    from app import models
    result = {
        "type": "quest",
        "npc_id": None,
        "title": "물 마시기",
        "subtasks": ["아침", "저녁"],
        "quest_type": "daily",
    }
    from app.services.ai_intake import save_intake
    save_intake(db, result)
    quest = db.query(models.Quest).filter_by(title="물 마시기").first()
    assert quest is not None
    assert quest.need_id is None
    assert len(quest.subtasks) == 2


def test_save_intake_quest_with_npc(db):
    """quest + npc_id 있음 → Need 자동 생성 후 Quest(need_id=...) 생성."""
    import json
    from app import models
    from app.services.sprite import generate_sprite
    sprite = generate_sprite()
    npc = models.NPC(name="테스트NPC", relation_type="기타",
                     sprite=json.dumps(sprite), color=sprite["color"])
    db.add(npc)
    db.commit()
    db.refresh(npc)

    result = {
        "type": "quest",
        "npc_id": str(npc.id),
        "title": "선물 보내기",
        "subtasks": ["구매", "포장"],
        "quest_type": "one_time",
    }
    from app.services.ai_intake import save_intake
    save_intake(db, result)

    quest = db.query(models.Quest).filter_by(title="선물 보내기").first()
    assert quest is not None
    assert quest.need_id is not None
    need = db.get(models.Need, quest.need_id)
    assert need.npc_id == npc.id
