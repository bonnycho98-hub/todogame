import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date,
    ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class QuestType(str, enum.Enum):
    DAILY = "daily"
    ONE_TIME = "one_time"


class NPC(Base):
    __tablename__ = "npcs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    relation_type = Column(String, nullable=False)
    sprite = Column(Text, nullable=False)       # JSON: {"lines": [...], "color": "#hex"}
    color = Column(String(7), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    needs = relationship("Need", back_populates="npc", cascade="all, delete-orphan")
    intimacy_logs = relationship("IntimacyLog", back_populates="npc")


class Need(Base):
    __tablename__ = "needs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    npc_id = Column(UUID(as_uuid=True), ForeignKey("npcs.id", ondelete="CASCADE"), nullable=True)  # NULL = self
    title = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    npc = relationship("NPC", back_populates="needs")
    quests = relationship("Quest", back_populates="need", cascade="all, delete-orphan")


class Quest(Base):
    __tablename__ = "quests"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    need_id = Column(UUID(as_uuid=True), ForeignKey("needs.id", ondelete="CASCADE"), nullable=True)  # NULL = self direct
    title = Column(String, nullable=False)
    quest_type = Column(SAEnum(QuestType), nullable=False)
    routine = Column(JSONB, nullable=True)       # {"type":"daily"} | {"type":"weekly","days":[0,2]} | {"type":"monthly","dates":[1,15]}
    intimacy_reward = Column(Integer, default=10)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    need = relationship("Need", back_populates="quests")
    subtasks = relationship(
        "Subtask", back_populates="quest",
        cascade="all, delete-orphan",
        order_by="Subtask.order"
    )


class Subtask(Base):
    __tablename__ = "subtasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quest_id = Column(UUID(as_uuid=True), ForeignKey("quests.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    order = Column(Integer, default=0)

    quest = relationship("Quest", back_populates="subtasks")
    daily_completions = relationship(
        "DailyCompletion", back_populates="subtask", cascade="all, delete-orphan"
    )
    one_time_completion = relationship(
        "OneTimeCompletion", back_populates="subtask",
        uselist=False, cascade="all, delete-orphan"
    )


class DailyCompletion(Base):
    __tablename__ = "daily_completions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subtask_id = Column(UUID(as_uuid=True), ForeignKey("subtasks.id", ondelete="CASCADE"), nullable=False)
    completed_date = Column(Date, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow)

    subtask = relationship("Subtask", back_populates="daily_completions")


class OneTimeCompletion(Base):
    __tablename__ = "one_time_completions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subtask_id = Column(UUID(as_uuid=True), ForeignKey("subtasks.id", ondelete="CASCADE"), nullable=False, unique=True)
    completed_at = Column(DateTime, default=datetime.utcnow)

    subtask = relationship("Subtask", back_populates="one_time_completion")


class IntimacyLog(Base):
    __tablename__ = "intimacy_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    npc_id = Column(UUID(as_uuid=True), ForeignKey("npcs.id", ondelete="CASCADE"), nullable=True)  # NULL = self
    delta = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    npc = relationship("NPC", back_populates="intimacy_logs")


class LevelReward(Base):
    __tablename__ = "level_rewards"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(Integer, nullable=False, unique=True)
    message = Column(Text, nullable=False)
    is_claimed = Column(Boolean, default=False)
    claimed_at = Column(DateTime, nullable=True)
