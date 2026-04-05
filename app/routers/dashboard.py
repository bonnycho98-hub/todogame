from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload
from datetime import date, datetime
from app.database import get_db
from app import models, schemas
from app.services.happiness import calculate_happiness
from app.services.quest import (
    is_quest_active_today,
    is_subtask_done_today,
    is_quest_all_done_today,
    _get_intimacy_total,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _build_quest_out(quest: models.Quest, db: Session, today: date) -> schemas.QuestOut:
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
    out.is_all_done_today = is_quest_all_done_today(db, quest, today)
    return out


@router.get("", response_model=schemas.DashboardOut)
def get_dashboard(db: Session = Depends(get_db)):
    today = date.today()

    # ── 오늘의 루틴 ──────────────────────────────────────────
    # DAILY 타입이고 오늘 스케줄에 해당하는 미archived 퀘스트
    all_daily = (
        db.query(models.Quest)
        .filter_by(quest_type=models.QuestType.DAILY, is_archived=False)
        .options(selectinload(models.Quest.subtasks))
        .all()
    )
    routine_quests_raw = [q for q in all_daily if is_quest_active_today(q, today)]
    routine_outs = [_build_quest_out(q, db, today) for q in routine_quests_raw]
    # 미완료 먼저, 완료는 하단
    routine_quests = sorted(routine_outs, key=lambda q: q.is_all_done_today)

    # ── 나를 사랑하기 (self section) ─────────────────────────
    # need.npc_id IS NULL 인 활성 needs
    self_needs = (
        db.query(models.Need)
        .filter(models.Need.npc_id.is_(None), models.Need.is_archived.is_(False))
        .options(selectinload(models.Need.quests).selectinload(models.Quest.subtasks))
        .order_by(models.Need.created_at)
        .all()
    )
    self_need_with_quests = []
    for need in self_needs:
        active_quests = [
            _build_quest_out(q, db, today)
            for q in need.quests
            if not q.is_archived
        ]
        self_need_with_quests.append(schemas.NeedWithQuests(
            need=schemas.NeedOut.from_orm(need),
            quests=active_quests,
        ))
    self_section = schemas.SelfSection(needs=self_need_with_quests)

    # ── 타인을 사랑하기 (NPC section) ────────────────────────
    npcs = (
        db.query(models.NPC)
        .options(
            selectinload(models.NPC.needs)
            .selectinload(models.Need.quests)
            .selectinload(models.Quest.subtasks)
        )
        .all()
    )
    npc_section = []
    others_totals = []
    for npc in npcs:
        total = _get_intimacy_total(db, npc.id)
        others_totals.append(total)

        active_needs = sorted(
            [n for n in npc.needs if not n.is_archived],
            key=lambda n: n.created_at or datetime.min,
        )
        npc_needs_with_quests = []
        for need in active_needs:
            active_quests = [
                _build_quest_out(q, db, today)
                for q in need.quests
                if not q.is_archived
            ]
            npc_needs_with_quests.append(schemas.NeedWithQuests(
                need=schemas.NeedOut.from_orm(need),
                quests=active_quests,
            ))

        npc_summary = schemas.NPCSummary(
            id=npc.id,
            name=npc.name,
            sprite=npc.sprite,
            color=npc.color,
            intimacy_total=total,
            needs=[schemas.NeedOut.from_orm(n) for n in active_needs],
        )
        npc_section.append(schemas.NPCSectionItem(
            npc=npc_summary,
            needs=npc_needs_with_quests,
        ))

    # ── 행복 레벨 ─────────────────────────────────────────────
    self_total = _get_intimacy_total(db, None)
    happiness = calculate_happiness(self_total, others_totals)

    # ── 미수령 레벨 보상 ──────────────────────────────────────
    pending_reward = db.query(models.LevelReward).filter_by(
        level=happiness["level"], is_claimed=False
    ).first()

    return schemas.DashboardOut(
        routine_quests=routine_quests,
        self_section=self_section,
        npc_section=npc_section,
        happiness=schemas.HappinessOut(**happiness),
        pending_level_reward=pending_reward,
    )
