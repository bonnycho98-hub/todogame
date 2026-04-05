import logging

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters,
)
from app.config import TELEGRAM_TOKEN, GEMINI_API_KEY
from app.telegram.handlers import (
    cmd_brief, cmd_status, callback_done,
    handle_free_text, handle_correction, handle_save, handle_cancel,
    AWAITING_CONFIRM,
)

_app: Application = None


def get_bot_app() -> Application:
    global _app
    if _app is None:
        _app = (
            Application.builder()
            .token(TELEGRAM_TOKEN)
            .build()
        )
        _app.add_handler(CommandHandler("brief", cmd_brief))
        _app.add_handler(CommandHandler("quests", cmd_brief))   # alias
        _app.add_handler(CommandHandler("status", cmd_status))
        _app.add_handler(CallbackQueryHandler(callback_done, pattern="^done:"))

        if GEMINI_API_KEY:
            conv_handler = ConversationHandler(
                entry_points=[
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_text),
                ],
                states={
                    AWAITING_CONFIRM: [
                        CallbackQueryHandler(handle_save, pattern="^save$"),
                        CallbackQueryHandler(handle_cancel, pattern="^cancel$"),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_correction),
                    ],
                },
                fallbacks=[
                    CallbackQueryHandler(handle_cancel, pattern="^cancel$"),
                ],
                conversation_timeout=300,
            )
            _app.add_handler(conv_handler)
        else:
            logging.warning("GEMINI_API_KEY not set — AI intake handler disabled")

    return _app
