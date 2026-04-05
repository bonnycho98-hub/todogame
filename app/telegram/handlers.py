from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.database import SessionLocal
from app.telegram.formatter import format_briefing, format_status
from app.services.quest import complete_subtask


async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
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
    db = SessionLocal()
    try:
        text = format_status(db)
        await update.message.reply_text(text, parse_mode="MarkdownV2")
    finally:
        db.close()


async def callback_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    subtask_id = query.data.replace("done:", "")
    db = SessionLocal()
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
