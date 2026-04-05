from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Message
from telegram.ext import ContextTypes, ConversationHandler
from app.database import get_session_local
from app.telegram.formatter import format_briefing, format_status
from app.services.quest import complete_subtask
from app import models

# ConversationHandler 상태
AWAITING_CONFIRM = 1


# ── 기존 커맨드 핸들러 ────────────────────────────────────────────

async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_session_local()()
    try:
        text, button_rows = format_briefing(db)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"])]
             for row in button_rows for btn in row]
        ) if button_rows else None
        await update.message.reply_text(text, parse_mode="MarkdownV2", reply_markup=keyboard)
    finally:
        db.close()


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_session_local()()
    try:
        text = format_status(db)
        await update.message.reply_text(text, parse_mode="MarkdownV2")
    finally:
        db.close()


async def callback_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    subtask_id = query.data.replace("done:", "")
    db = get_session_local()()
    try:
        result = complete_subtask(db, subtask_id)
        if result["subtask_done"]:
            msg = "✅ 완료!"
            if result["quest_done"]:
                msg += " 퀘스트 달성! 🎉"
            if result["level_up"]:
                msg += f"\n🎊 LEVEL UP\\! lv\\.{result['level_up']}"
            await query.edit_message_text(query.message.text + f"\n\n{msg}", parse_mode="MarkdownV2")
        else:
            await query.answer("이미 완료됐어요!")
    finally:
        db.close()


# ── AI Intake 핸들러 ────────────────────────────────────────────

async def handle_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """자유 텍스트 수신 → Gemini 처리 → 결과 표시."""
    from app.services.ai_intake import parse_intake

    text = update.message.text
    processing_msg = await update.message.reply_text("⏳ 처리 중...")

    db = get_session_local()()
    try:
        npcs = [{"id": str(n.id), "name": n.name} for n in db.query(models.NPC).all()]
    finally:
        db.close()

    try:
        result = parse_intake(text, npcs)
    except Exception:
        await processing_msg.edit_text("처리 중 오류가 났어요. 다시 입력해주세요.")
        return ConversationHandler.END

    context.user_data["current_result"] = result
    context.user_data["original_text"] = text

    result_msg = await _send_result(update, result)
    context.user_data["result_message_id"] = result_msg.message_id
    await processing_msg.delete()
    return AWAITING_CONFIRM


async def handle_correction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """수정 지시 텍스트 수신 → Gemini 재처리 → 결과 표시."""
    from app.services.ai_intake import parse_intake

    correction = update.message.text
    previous_result = context.user_data.get("current_result")
    original_text = context.user_data.get("original_text", "")

    processing_msg = await update.message.reply_text("⏳ 수정 중...")

    db = get_session_local()()
    try:
        npcs = [{"id": str(n.id), "name": n.name} for n in db.query(models.NPC).all()]
    finally:
        db.close()

    try:
        result = parse_intake(
            text=original_text,
            npcs=npcs,
            previous_result=previous_result,
            correction=correction,
        )
    except Exception:
        await processing_msg.edit_text("수정 중 오류가 났어요. 다시 수정 지시를 보내주세요.")
        return AWAITING_CONFIRM

    context.user_data["current_result"] = result
    result_msg = await _send_result(update, result)
    context.user_data["result_message_id"] = result_msg.message_id
    await processing_msg.delete()
    return AWAITING_CONFIRM


async def handle_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """[✓ 저장] 버튼 → DB 저장 → 종료."""
    from app.services.ai_intake import save_intake

    query = update.callback_query
    await query.answer()

    result = context.user_data.get("current_result")
    db = get_session_local()()
    try:
        save_intake(db, result)
    finally:
        db.close()

    await query.edit_message_text("✅ 저장됐어요!")
    context.user_data.clear()
    return ConversationHandler.END


async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """[✗ 취소] 버튼 → 대화 종료."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("취소했어요.")
    context.user_data.clear()
    return ConversationHandler.END


# ── 내부 헬퍼 ────────────────────────────────────────────────────

def _format_result_text(result: dict, npc_name: str | None) -> str:
    type_label = "📋 퀘스트" if result["type"] == "quest" else "💬 니즈"
    npc_label = npc_name if npc_name else "나"
    lines = [
        f"{type_label} · {npc_label}",
        "",
        result["title"],
    ]
    for st in result.get("subtasks", []):
        lines.append(f"  • {st}")
    lines.append("")
    lines.append("수정하려면 이 메시지에 답장하세요.")
    return "\n".join(lines)


async def _send_result(update: Update, result: dict) -> Message:
    db = get_session_local()()
    try:
        npc_name = None
        if result.get("npc_id"):
            npc = db.get(models.NPC, result["npc_id"])
            npc_name = npc.name if npc else None
    finally:
        db.close()

    text = _format_result_text(result, npc_name)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✓ 저장", callback_data="save"),
        InlineKeyboardButton("✗ 취소", callback_data="cancel"),
    ]])
    return await update.effective_message.reply_text(text, reply_markup=keyboard)
