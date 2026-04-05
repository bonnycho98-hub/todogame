from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models import QuestType


# ── NPC ──────────────────────────────────────────────────────
class NPCCreate(BaseModel):
    name: str
    relation_type: str
    sprite: Optional[str] = None
    color: Optional[str] = None


class NPCOut(BaseModel):
    id: UUID
    name: str
    relation_type: str
    sprite: str
    color: str
    created_at: datetime
    intimacy_total: int = 0

    model_config = {"from_attributes": True}


# ── Need ──────────────────────────────────────────────────────
class NeedCreate(BaseModel):
    npc_id: Optional[UUID] = None
    title: str


class NeedOut(BaseModel):
    id: UUID
    npc_id: Optional[UUID]
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Quest ──────────────────────────────────────────────────────
class RoutineConfig(BaseModel):
    type: str                           # "daily" | "weekly" | "monthly"
    days: Optional[list[int]] = None    # weekly: 0=Mon..6=Sun
    dates: Optional[list[int]] = None   # monthly: 1..31


class SubtaskOut(BaseModel):
    id: UUID
    title: str
    order: int
    is_done_today: bool = False

    model_config = {"from_attributes": True}


class QuestCreate(BaseModel):
    need_id: Optional[UUID] = None
    title: str
    quest_type: QuestType
    routine: Optional[RoutineConfig] = None
    intimacy_reward: int = 10


class QuestOut(BaseModel):
    id: UUID
    need_id: Optional[UUID]
    title: str
    quest_type: QuestType
    routine: Optional[dict]
    intimacy_reward: int
    is_archived: bool
    subtasks: list[SubtaskOut] = []

    model_config = {"from_attributes": True}


# ── Subtask ──────────────────────────────────────────────────────
class SubtaskCreate(BaseModel):
    quest_id: UUID
    title: str
    order: int = 0


class CompleteSubtaskOut(BaseModel):
    subtask_done: bool
    quest_done: bool
    level_up: Optional[int]


# ── LevelReward ──────────────────────────────────────────────────────
class LevelRewardCreate(BaseModel):
    level: int
    message: str


class LevelRewardOut(BaseModel):
    id: UUID
    level: int
    message: str
    is_claimed: bool
    claimed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Dashboard ──────────────────────────────────────────────────────
class HappinessOut(BaseModel):
    level: int
    score: float
    progress: float
    filled_blocks: int
    total_blocks: int


class NPCSummary(BaseModel):
    id: UUID
    name: str
    sprite: str
    color: str
    intimacy_total: int


class DashboardOut(BaseModel):
    today_quests: list[QuestOut]
    npcs: list[NPCSummary]
    happiness: HappinessOut
    pending_level_reward: Optional[LevelRewardOut]
