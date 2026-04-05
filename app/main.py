import logging

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import npcs, needs, quests, subtasks, rewards, dashboard
from app.config import TELEGRAM_TOKEN, WEBHOOK_BASE_URL

logger = logging.getLogger(__name__)

app = FastAPI(title="Love Quest")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(npcs.router)
app.include_router(needs.router)
app.include_router(quests.router)
app.include_router(subtasks.router)
app.include_router(rewards.router)
app.include_router(dashboard.router)


@app.on_event("startup")
async def on_startup():
    logger.info("=== on_startup() called ===")
    logger.info("TELEGRAM_TOKEN: %s", "SET" if TELEGRAM_TOKEN else "NOT SET (empty)")
    logger.info("WEBHOOK_BASE_URL: %s", WEBHOOK_BASE_URL if WEBHOOK_BASE_URL else "NOT SET (empty)")

    if not TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_TOKEN is not set — skipping bot initialization")
        return

    from app.telegram.bot import get_bot_app
    bot = get_bot_app()
    await bot.initialize()
    logger.info("Bot initialized successfully")

    if WEBHOOK_BASE_URL:
        webhook_url = f"{WEBHOOK_BASE_URL}/telegram/webhook"
        logger.info("Attempting to set webhook: %s", webhook_url)
        try:
            await bot.bot.set_webhook(webhook_url)
            logger.info("Webhook set successfully: %s", webhook_url)
        except Exception as e:
            logger.error("Failed to set webhook: %s", e, exc_info=True)
    else:
        logger.warning("WEBHOOK_BASE_URL is not set — webhook will not be registered")

    logger.info("Starting scheduler...")
    _start_scheduler()
    logger.info("Scheduler started")


@app.on_event("shutdown")
async def on_shutdown():
    if not TELEGRAM_TOKEN:
        return
    from app.telegram.bot import get_bot_app
    bot = get_bot_app()
    await bot.shutdown()


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    logger.info("Webhook request received from %s", request.client.host if request.client else "unknown")
    if not TELEGRAM_TOKEN:
        logger.warning("Webhook request received but TELEGRAM_TOKEN is not set — returning 404")
        return Response(status_code=404)
    from telegram import Update
    from app.telegram.bot import get_bot_app
    data = await request.json()
    logger.info("Webhook payload update_id=%s type=%s",
                data.get("update_id"), next((k for k in data if k != "update_id"), "unknown"))
    bot = get_bot_app()
    update = Update.de_json(data, bot.bot)
    await bot.process_update(update)
    logger.info("Webhook update processed successfully (update_id=%s)", data.get("update_id"))
    return Response(status_code=200)


def _start_scheduler():
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from app.config import BRIEFING_HOUR, BRIEFING_MINUTE, TELEGRAM_CHAT_ID
    from app.database import get_session_local
    from app.telegram.formatter import format_briefing
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton

    scheduler = AsyncIOScheduler()

    async def send_daily_brief():
        db = get_session_local()()
        try:
            text, button_rows = format_briefing(db)
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"])]
                 for row in button_rows for btn in row]
            ) if button_rows else None
            from app.telegram.bot import get_bot_app
            bot = get_bot_app()
            await bot.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=keyboard,
            )
        finally:
            db.close()

    scheduler.add_job(send_daily_brief, "cron", hour=BRIEFING_HOUR, minute=BRIEFING_MINUTE)
    scheduler.start()


@app.get("/")
def root():
    return FileResponse("static/index.html")
