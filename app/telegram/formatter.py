import re
from sqlalchemy.orm import Session
from app import models
from app.utils import today_kst
from app.services.quest import (
    is_quest_active_today,
    is_subtask_done_today,
    is_quest_all_done_today,
    is_quest_done_today,
)
from app.services.happiness import calculate_happiness
from app.services.quest import _get_intimacy_total


def _esc(text: str) -> str:
    """MarkdownV2 특수문자 이스케이프"""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', str(text))


def _happiness_line(db: Session) -> str:
    self_total = _get_intimacy_total(db, None)
    npc_ids = [row.id for row in db.query(models.NPC.id).all()]
    others = [_get_intimacy_total(db, nid) for nid in npc_ids]
    h = calculate_happiness(self_total, others)
    filled = "■" * h["filled_blocks"] + "□" * (h["total_blocks"] - h["filled_blocks"])
    return f"행복 레벨: {filled} lv\\.{h['level']}"


def format_briefing(db: Session) -> tuple[str, list[dict]]:
    """
    아침 브리핑: 오늘 할 일 전체.
    반환: (text, [[{"text": label, "callback_data": f"done:{subtask_id}"}]])
    """
    today = today_kst()
    all_quests = db.query(models.Quest).filter_by(is_archived=False).all()
    active = [q for q in all_quests if is_quest_active_today(q, today)]

    lines = ["🎮 *LOVE QUEST — 오늘의 브리핑*\n"]
    buttons = []

    self_quests = [q for q in active if q.need_id is None]
    npc_quests = [q for q in active if q.need_id is not None]

    if self_quests:
        lines.append("*\\[ 나를 사랑하기 \\]*")
        for q in self_quests:
            if q.subtasks:
                done = sum(1 for st in q.subtasks if is_subtask_done_today(db, st, today))
                total = len(q.subtasks)
                lines.append(f"◆ {_esc(q.title)} \\({done}/{total}\\)")
                for st in q.subtasks:
                    done_st = is_subtask_done_today(db, st, today)
                    mark = "☑" if done_st else "☐"
                    lines.append(f"  {mark} {_esc(st.title)}")
                    if not done_st:
                        buttons.append([{"text": f"✓ {st.title[:20]}", "callback_data": f"done:{st.id}"}])
            else:
                done_q = is_quest_done_today(db, q, today)
                mark = "☑" if done_q else "☐"
                lines.append(f"  {mark} {_esc(q.title)}")
                if not done_q:
                    buttons.append([{"text": f"✓ {q.title[:20]}", "callback_data": f"quest:{q.id}"}])
        lines.append("")

    if npc_quests:
        lines.append("*\\[ 타인을 사랑하기 \\]*")
        for q in npc_quests:
            npc_name = q.need.npc.name if q.need and q.need.npc else "?"
            if q.subtasks:
                done = sum(1 for st in q.subtasks if is_subtask_done_today(db, st, today))
                total = len(q.subtasks)
                lines.append(f"◆ {_esc(npc_name)} — {_esc(q.title)} \\({done}/{total}\\)")
                for st in q.subtasks:
                    done_st = is_subtask_done_today(db, st, today)
                    mark = "☑" if done_st else "☐"
                    lines.append(f"  {mark} {_esc(st.title)}")
                    if not done_st:
                        buttons.append([{"text": f"✓ {st.title[:20]}", "callback_data": f"done:{st.id}"}])
            else:
                done_q = is_quest_done_today(db, q, today)
                mark = "☑" if done_q else "☐"
                lines.append(f"◆ {_esc(npc_name)} — {_esc(q.title)}")
                lines.append(f"  {mark} {_esc(q.title)}")
                if not done_q:
                    buttons.append([{"text": f"✓ {q.title[:20]}", "callback_data": f"quest:{q.id}"}])
        lines.append("")

    lines.append(_happiness_line(db))
    return "\n".join(lines), buttons


def format_evening_briefing(db: Session) -> tuple[str, list[dict]]:
    """
    저녁 브리핑: 오늘 미완료 할일만 표시.
    반환: (text, [[{"text": label, "callback_data": ...}]])
    """
    today = today_kst()
    all_quests = db.query(models.Quest).filter_by(is_archived=False).all()
    active = [q for q in all_quests if is_quest_active_today(q, today)]

    # 미완료 퀘스트만
    remaining = [q for q in active if not is_quest_all_done_today(db, q, today)]

    lines = ["🌙 *LOVE QUEST — 저녁 브리핑*\n"]
    buttons = []

    if not remaining:
        lines.append("✨ 오늘 할 일을 모두 완료했어요\\!")
        lines.append("")
        lines.append(_happiness_line(db))
        return "\n".join(lines), buttons

    self_quests = [q for q in remaining if q.need_id is None]
    npc_quests = [q for q in remaining if q.need_id is not None]

    if self_quests:
        lines.append("*\\[ 나를 사랑하기 \\]*")
        for q in self_quests:
            if q.subtasks:
                undone = [st for st in q.subtasks if not is_subtask_done_today(db, st, today)]
                total = len(q.subtasks)
                done = total - len(undone)
                lines.append(f"◆ {_esc(q.title)} \\({done}/{total}\\)")
                for st in undone:
                    lines.append(f"  ☐ {_esc(st.title)}")
                    buttons.append([{"text": f"✓ {st.title[:20]}", "callback_data": f"done:{st.id}"}])
            else:
                lines.append(f"  ☐ {_esc(q.title)}")
                buttons.append([{"text": f"✓ {q.title[:20]}", "callback_data": f"quest:{q.id}"}])
        lines.append("")

    if npc_quests:
        lines.append("*\\[ 타인을 사랑하기 \\]*")
        for q in npc_quests:
            npc_name = q.need.npc.name if q.need and q.need.npc else "?"
            if q.subtasks:
                undone = [st for st in q.subtasks if not is_subtask_done_today(db, st, today)]
                total = len(q.subtasks)
                done = total - len(undone)
                lines.append(f"◆ {_esc(npc_name)} — {_esc(q.title)} \\({done}/{total}\\)")
                for st in undone:
                    lines.append(f"  ☐ {_esc(st.title)}")
                    buttons.append([{"text": f"✓ {st.title[:20]}", "callback_data": f"done:{st.id}"}])
            else:
                lines.append(f"  ☐ {_esc(npc_name)} — {_esc(q.title)}")
                buttons.append([{"text": f"✓ {q.title[:20]}", "callback_data": f"quest:{q.id}"}])
        lines.append("")

    lines.append(_happiness_line(db))
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
        lines.append(f"  {_esc(npc.name)}: {total}")

    return "\n".join(lines)
