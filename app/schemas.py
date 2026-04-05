from __future__ import annotations
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List
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

    class Config:
        orm_mode = True


# ── Need ──────────────────────────────────────────────────────
class NeedCreate(BaseModel):
    npc_id: Optional[UUID] = None
    title: str


class NeedOut(BaseModel):
    id: UUID
    npc_id: Optional[UUID]
    title: str
    is_archived: bool = False
    created_at: datetime

    class Config:
        orm_mode = True


# ── Quest ──────────────────────────────────────────────────────
class RoutineConfig(BaseModel):
    type: str
    days: Optional[List[int]] = None
    dates: Optional[List[int]] = None


class SubtaskOut(BaseModel):
    id: UUID
    title: str
    order: int
    is_done_today: bool = False

    class Config:
        orm_mode = True


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
    subtasks: List[SubtaskOut] = []
    is_all_done_today: bool = False  # 프론트에서 완료 시각 상태(취소선/회색) 처리용

    class Config:
        orm_mode = True


# ── Need Update ──────────────────────────────────────────────────────
class NeedUpdate(BaseModel):
    title: str


class NeedCompleteOut(BaseModel):
    done: bool


# ── Quest Update ──────────────────────────────────────────────────────
class QuestUpdate(BaseModel):
    title: Optional[str] = None
    quest_type: Optional[QuestType] = None
    routine: Optional[RoutineConfig] = None
    intimacy_reward: Optional[int] = None


# ── Subtask ──────────────────────────────────────────────────────
class SubtaskCreate(BaseModel):
    quest_id: UUID
    title: str
    order: int = 0


class SubtaskUpdate(BaseModel):
    title: str


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

    class Config:
        orm_mode = True


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
    needs: List[NeedOut] = []


class NeedWithQuests(BaseModel):
    need: NeedOut
    quests: List[QuestOut]


class SelfSection(BaseModel):
    needs: List[NeedWithQuests]


class NPCSectionItem(BaseModel):
    npc: NPCSummary
    needs: List[NeedWithQuests]


class DashboardOut(BaseModel):
    routine_quests: List[QuestOut]
    self_section: SelfSection
    npc_section: List[NPCSectionItem]
    happiness: HappinessOut
    pending_level_reward: Optional[LevelRewardOut]
