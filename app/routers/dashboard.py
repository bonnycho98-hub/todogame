from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload
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

    # NPC 목록 + 친밀도 + 활성 needs (selectinload로 N+1 방지)
    npcs = db.query(models.NPC).options(selectinload(models.NPC.needs)).all()
    npc_summaries = []
    others_totals = []
    for npc in npcs:
        total = _get_intimacy_total(db, npc.id)
        others_totals.append(total)
        active_needs = sorted(
            [n for n in npc.needs if not n.is_archived],
            key=lambda n: n.created_at,
        )
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
