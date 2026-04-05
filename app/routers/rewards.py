from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


@router.get("", response_model=list[schemas.LevelRewardOut])
def list_rewards(db: Session = Depends(get_db)):
    return db.query(models.LevelReward).order_by(models.LevelReward.level).all()


@router.post("", response_model=schemas.LevelRewardOut, status_code=201)
def create_reward(body: schemas.LevelRewardCreate, db: Session = Depends(get_db)):
    existing = db.query(models.LevelReward).filter_by(level=body.level).first()
    if existing:
        raise HTTPException(400, f"Level {body.level} reward already exists")
    reward = models.LevelReward(level=body.level, message=body.message)
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward


@router.post("/{reward_id}/claim", response_model=schemas.LevelRewardOut)
def claim_reward(reward_id: UUID, db: Session = Depends(get_db)):
    reward = db.get(models.LevelReward, reward_id)
    if not reward:
        raise HTTPException(404)
    if reward.is_claimed:
        raise HTTPException(400, "Already claimed")
    reward.is_claimed = True
    reward.claimed_at = datetime.utcnow()
    db.commit()
    db.refresh(reward)
    return reward


@router.delete("/{reward_id}", status_code=204)
def delete_reward(reward_id: UUID, db: Session = Depends(get_db)):
    reward = db.get(models.LevelReward, reward_id)
    if not reward:
        raise HTTPException(404)
    db.delete(reward)
    db.commit()
