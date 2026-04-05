from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.database import get_db
from app import models, schemas
from app.services.quest import is_subtask_done_today

router = APIRouter(prefix="/api/quests", tags=["quests"])


def _enrich_quest(quest: models.Quest, db: Session, today: date) -> schemas.QuestOut:
    out = schemas.QuestOut.from_orm(quest)
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
        routine=body.routine.dict() if body.routine else None,
        intimacy_reward=body.intimacy_reward,
    )
    db.add(quest)
    db.commit()
    db.refresh(quest)
    return _enrich_quest(quest, db, date.today())


@router.patch("/{quest_id}", response_model=schemas.QuestOut)
def update_quest(quest_id: UUID, body: schemas.QuestUpdate, db: Session = Depends(get_db)):
    quest = db.get(models.Quest, quest_id)
    if not quest:
        raise HTTPException(404)
    if body.title is not None:
        quest.title = body.title
    if body.quest_type is not None:
        quest.quest_type = body.quest_type
    if body.routine is not None:
        quest.routine = body.routine.dict()
    if body.intimacy_reward is not None:
        quest.intimacy_reward = body.intimacy_reward
    db.commit()
    db.refresh(quest)
    return _enrich_quest(quest, db, date.today())


@router.post("/{quest_id}/complete")
def complete_quest(quest_id: UUID, db: Session = Depends(get_db)):
    from app.services.quest import complete_quest as svc_complete
    try:
        return svc_complete(db, quest_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/{quest_id}", status_code=204)
def delete_quest(quest_id: UUID, db: Session = Depends(get_db)):
    quest = db.get(models.Quest, quest_id)
    if not quest:
        raise HTTPException(404)
    db.delete(quest)
    db.commit()
