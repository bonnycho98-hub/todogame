from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func
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
    return True  # one_time은 archived 전까지 항상 표시


def is_subtask_done_today(db: Session, subtask: models.Subtask, today: date) -> bool:
    """서브태스크가 오늘 완료됐는지 확인한다."""
    if subtask.quest.quest_type == models.QuestType.DAILY:
        return db.query(models.DailyCompletion).filter_by(
            subtask_id=subtask.id, completed_date=today
        ).first() is not None
    return subtask.one_time_completion is not None


def _get_intimacy_total(db: Session, npc_id) -> int:
    result = db.query(func.sum(models.IntimacyLog.delta)).filter(
        models.IntimacyLog.npc_id == npc_id
    ).scalar()
    return result or 0


def _check_level_up(db: Session, npc_id, reward: int) -> int | None:
    """친밀도 보상 지급 후 레벨업 여부를 반환한다. 레벨업 없으면 None."""
    from app.services.happiness import calculate_happiness

    self_total = _get_intimacy_total(db, None)
    npc_ids = [row.id for row in db.query(models.NPC.id).all()]
    others_totals = [_get_intimacy_total(db, nid) for nid in npc_ids]

    current = calculate_happiness(self_total, others_totals)

    # 방금 추가된 delta를 빼서 이전 상태 계산
    if npc_id is None:
        prev_self = self_total - reward
        prev_others = others_totals
    else:
        prev_self = self_total
        prev_others = [
            (t - reward if npc_ids[i] == npc_id else t)
            for i, t in enumerate(others_totals)
        ]
    prev = calculate_happiness(prev_self, prev_others)

    if current["level"] > prev["level"]:
        return current["level"]
    return None


def complete_quest(db: Session, quest_id: str, today: date = None) -> dict:
    """
    퀘스트를 직접 완료 처리한다. 서브태스크 전부 완료 + 친밀도 보상 지급.
    반환: {"quest_done": bool, "level_up": int | None}
    """
    today = today or date.today()
    quest = db.get(models.Quest, quest_id)
    if quest is None:
        raise ValueError(f"Quest {quest_id} not found")

    if quest.is_archived:
        return {"quest_done": False, "level_up": None}

    # 서브태스크 모두 완료 처리
    for subtask in quest.subtasks:
        if not is_subtask_done_today(db, subtask, today):
            if quest.quest_type == models.QuestType.DAILY:
                db.add(models.DailyCompletion(subtask_id=subtask.id, completed_date=today))
            else:
                db.add(models.OneTimeCompletion(subtask_id=subtask.id))

    db.flush()

    npc_id = None
    if quest.need and quest.need.npc_id:
        npc_id = quest.need.npc_id

    db.add(models.IntimacyLog(
        npc_id=npc_id,
        delta=quest.intimacy_reward,
        reason=f"퀘스트 완료: {quest.title}",
    ))
    db.flush()

    if quest.quest_type == models.QuestType.ONE_TIME:
        quest.is_archived = True

    level_up = _check_level_up(db, npc_id, quest.intimacy_reward)
    db.commit()
    return {"quest_done": True, "level_up": level_up}


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
        npc_id = None
        if quest.need and quest.need.npc_id:
            npc_id = quest.need.npc_id

        db.add(models.IntimacyLog(
            npc_id=npc_id,
            delta=quest.intimacy_reward,
            reason=f"퀘스트 완료: {quest.title}",
        ))
        db.flush()

        if quest.quest_type == models.QuestType.ONE_TIME:
            quest.is_archived = True

        level_up = _check_level_up(db, npc_id, quest.intimacy_reward)

    db.commit()
    return {"subtask_done": True, "quest_done": all_done, "level_up": level_up}
