from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/needs", tags=["needs"])


@router.get("", response_model=list[schemas.NeedOut])
def list_needs(npc_id: str = None, db: Session = Depends(get_db)):
    q = db.query(models.Need)
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


@router.delete("/{need_id}", status_code=204)
def delete_need(need_id: UUID, db: Session = Depends(get_db)):
    need = db.get(models.Need, need_id)
    if not need:
        raise HTTPException(404)
    db.delete(need)
    db.commit()
