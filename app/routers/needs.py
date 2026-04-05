from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/needs", tags=["needs"])


@router.get("", response_model=list[schemas.NeedOut])
def list_needs(npc_id: Optional[UUID] = None, db: Session = Depends(get_db)):
    q = db.query(models.Need).filter_by(is_archived=False)
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


@router.post("/{need_id}/complete", response_model=schemas.NeedCompleteOut)
def complete_need(need_id: UUID, db: Session = Depends(get_db)):
    need = db.get(models.Need, need_id)
    if not need:
        raise HTTPException(404)
    if need.is_archived:
        raise HTTPException(409, detail="Need is already completed")
    need.is_archived = True
    db.commit()
    return {"done": True}


@router.patch("/{need_id}", response_model=schemas.NeedOut)
def update_need(need_id: UUID, body: schemas.NeedUpdate, db: Session = Depends(get_db)):
    need = db.get(models.Need, need_id)
    if not need:
        raise HTTPException(404)
    need.title = body.title
    db.commit()
    db.refresh(need)
    return need


@router.delete("/{need_id}", status_code=204)
def delete_need(need_id: UUID, db: Session = Depends(get_db)):
    need = db.get(models.Need, need_id)
    if not need:
        raise HTTPException(404)
    db.delete(need)
    db.commit()
