from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from app.config import TELEGRAM_TOKEN
from app.telegram.handlers import cmd_brief, cmd_status, callback_done

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
    return _app
