from uuid import UUID
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import models, schemas
from app.services.sprite import generate_sprite, serialize_sprite

router = APIRouter(prefix="/api/npcs", tags=["npcs"])


def _get_intimacy_total(db: Session, npc_id) -> int:
    result = db.query(func.sum(models.IntimacyLog.delta)).filter(
        models.IntimacyLog.npc_id == npc_id
    ).scalar()
    return result or 0


@router.get("", response_model=list[schemas.NPCOut])
def list_npcs(db: Session = Depends(get_db)):
    npcs = db.query(models.NPC).order_by(models.NPC.created_at).all()
    result = []
    for npc in npcs:
        out = schemas.NPCOut.from_orm(npc)
        out.intimacy_total = _get_intimacy_total(db, npc.id)
        result.append(out)
    return result


@router.post("", response_model=schemas.NPCOut, status_code=201)
def create_npc(body: schemas.NPCCreate, db: Session = Depends(get_db)):
    sprite_data = generate_sprite(seed=random.randint(0, 10 ** 9))
    color = body.color or sprite_data["color"]
    sprite_json = body.sprite or serialize_sprite(sprite_data)

    npc = models.NPC(
        name=body.name,
        relation_type=body.relation_type,
        sprite=sprite_json,
        color=color,
    )
    db.add(npc)
    db.commit()
    db.refresh(npc)
    out = schemas.NPCOut.from_orm(npc)
    out.intimacy_total = 0
    return out


@router.post("/{npc_id}/regenerate-sprite", response_model=schemas.NPCOut)
def regenerate_sprite(npc_id: UUID, db: Session = Depends(get_db)):
    npc = db.get(models.NPC, npc_id)
    if not npc:
        raise HTTPException(404)
    sprite_data = generate_sprite(seed=random.randint(0, 10 ** 9))
    npc.sprite = serialize_sprite(sprite_data)
    npc.color = sprite_data["color"]
    db.commit()
    db.refresh(npc)
    out = schemas.NPCOut.from_orm(npc)
    out.intimacy_total = _get_intimacy_total(db, npc.id)
    return out


@router.delete("/{npc_id}", status_code=204)
def delete_npc(npc_id: UUID, db: Session = Depends(get_db)):
    npc = db.get(models.NPC, npc_id)
    if not npc:
        raise HTTPException(404)
    db.delete(npc)
    db.commit()
