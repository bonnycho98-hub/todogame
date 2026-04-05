from uuid import UUID
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
    return schemas.SubtaskOut(
        id=subtask.id, title=subtask.title, order=subtask.order, is_done_today=False
    )


@router.post("/{subtask_id}/complete", response_model=schemas.CompleteSubtaskOut)
def complete(subtask_id: UUID, db: Session = Depends(get_db)):
    try:
        result = complete_subtask(db, subtask_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result


@router.patch("/{subtask_id}", response_model=schemas.SubtaskOut)
def update_subtask(subtask_id: UUID, body: schemas.SubtaskUpdate, db: Session = Depends(get_db)):
    subtask = db.get(models.Subtask, subtask_id)
    if not subtask:
        raise HTTPException(404)
    subtask.title = body.title
    db.commit()
    db.refresh(subtask)
    return schemas.SubtaskOut(id=subtask.id, title=subtask.title, order=subtask.order, is_done_today=False)


@router.delete("/{subtask_id}", status_code=204)
def delete_subtask(subtask_id: UUID, db: Session = Depends(get_db)):
    subtask = db.get(models.Subtask, subtask_id)
    if not subtask:
        raise HTTPException(404)
    db.delete(subtask)
    db.commit()
