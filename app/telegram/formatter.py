from datetime import date
from sqlalchemy.orm import Session
from app import models
from app.services.quest import is_quest_active_today, is_subtask_done_today
from app.services.happiness import calculate_happiness
from app.services.quest import _get_intimacy_total


def format_briefing(db: Session) -> tuple[str, list[dict]]:
    """
    오늘의 브리핑 텍스트와 인라인 버튼 목록을 반환한다.
    반환: (text, [[{"text": label, "callback_data": f"done:{subtask_id}"}]])
    """
    today = date.today()
    all_quests = db.query(models.Quest).filter_by(is_archived=False).all()
    active = [q for q in all_quests if is_quest_active_today(q, today)]

    lines = ["🎮 *LOVE QUEST — 오늘의 브리핑*\n"]
    buttons = []

    self_quests = [q for q in active if q.need_id is None]
    npc_quests = [q for q in active if q.need_id is not None]

    if self_quests:
        lines.append("*\\[ 나를 사랑하기 \\]*")
        for q in self_quests:
            done = sum(1 for st in q.subtasks if is_subtask_done_today(db, st, today))
            lines.append(f"◆ {q.title} \\({done}/{len(q.subtasks)}\\)")
            for st in q.subtasks:
                done_st = is_subtask_done_today(db, st, today)
                mark = "☑" if done_st else "☐"
                lines.append(f"  {mark} {st.title}")
                if not done_st:
                    buttons.append([{"text": f"✓ {st.title[:20]}", "callback_data": f"done:{st.id}"}])
        lines.append("")

    if npc_quests:
        lines.append("*\\[ 타인을 사랑하기 \\]*")
        for q in npc_quests:
            npc_name = q.need.npc.name if q.need and q.need.npc else "?"
            done = sum(1 for st in q.subtasks if is_subtask_done_today(db, st, today))
            lines.append(f"◆ {npc_name} — {q.title} \\({done}/{len(q.subtasks)}\\)")
            for st in q.subtasks:
                done_st = is_subtask_done_today(db, st, today)
                mark = "☑" if done_st else "☐"
                lines.append(f"  {mark} {st.title}")
                if not done_st:
                    buttons.append([{"text": f"✓ {st.title[:20]}", "callback_data": f"done:{st.id}"}])
        lines.append("")

    # 행복 레벨
    self_total = _get_intimacy_total(db, None)
    npc_ids = [row.id for row in db.query(models.NPC.id).all()]
    others = [_get_intimacy_total(db, nid) for nid in npc_ids]
    h = calculate_happiness(self_total, others)
    filled = "■" * h["filled_blocks"] + "□" * (h["total_blocks"] - h["filled_blocks"])
    lines.append(f"행복 레벨: {filled} lv\\.{h['level']}")

    return "\n".join(lines), buttons


def format_status(db: Session) -> str:
    self_total = _get_intimacy_total(db, None)
    npcs = db.query(models.NPC).all()
    others = [_get_intimacy_total(db, n.id) for n in npcs]
    h = calculate_happiness(self_total, others)

    lines = [
        "📊 *STATUS*\n",
        f"행복 레벨: lv\\.{h['level']} \\({round(h['progress']*100)}%\\)",
        f"나 자신 친밀도: {self_total}",
        "",
        "*\\[ NPC 친밀도 \\]*",
    ]
    for npc, total in zip(npcs, others):
        lines.append(f"  {npc.name}: {total}")

    return "\n".join(lines)
