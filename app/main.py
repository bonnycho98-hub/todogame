from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import npcs, needs, quests, subtasks, rewards, dashboard
from app.config import TELEGRAM_TOKEN, WEBHOOK_BASE_URL

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
    if not TELEGRAM_TOKEN:
        return
    from app.telegram.bot import get_bot_app
    bot = get_bot_app()
    await bot.initialize()
    if WEBHOOK_BASE_URL:
        webhook_url = f"{WEBHOOK_BASE_URL}/telegram/webhook"
        await bot.bot.set_webhook(webhook_url)
    _start_scheduler()


@app.on_event("shutdown")
async def on_shutdown():
    if not TELEGRAM_TOKEN:
        return
    from app.telegram.bot import get_bot_app
    bot = get_bot_app()
    await bot.shutdown()


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    if not TELEGRAM_TOKEN:
        return Response(status_code=404)
    from telegram import Update
    from app.telegram.bot import get_bot_app
    data = await request.json()
    bot = get_bot_app()
    update = Update.de_json(data, bot.bot)
    await bot.process_update(update)
    return Response(status_code=200)


def _start_scheduler():
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from app.config import BRIEFING_HOUR, BRIEFING_MINUTE, EVENING_HOUR, EVENING_MINUTE, TELEGRAM_CHAT_ID
    from app.database import get_session_local
    from app.telegram.formatter import format_briefing, format_evening_briefing
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton

    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    async def _send(formatter):
        db = get_session_local()()
        try:
            text, button_rows = formatter(db)
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

    async def send_morning_brief():
        await _send(format_briefing)

    async def send_evening_brief():
        await _send(format_evening_briefing)

    scheduler.add_job(send_morning_brief, "cron", hour=BRIEFING_HOUR, minute=BRIEFING_MINUTE)
    scheduler.add_job(send_evening_brief, "cron", hour=EVENING_HOUR, minute=EVENING_MINUTE)
    scheduler.start()


@app.post("/telegram/test-briefing")
async def test_briefing():
    """아침/저녁 브리핑을 즉시 전송 (테스트용)"""
    if not TELEGRAM_TOKEN:
        return Response(status_code=404)
    from app.config import TELEGRAM_CHAT_ID
    from app.database import get_session_local
    from app.telegram.formatter import format_briefing, format_evening_briefing
    from app.telegram.bot import get_bot_app
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton

    bot = get_bot_app()

    async def _send(formatter):
        db = get_session_local()()
        try:
            text, button_rows = formatter(db)
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"])]
                 for row in button_rows for btn in row]
            ) if button_rows else None
            await bot.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=text,
                parse_mode="MarkdownV2",
                reply_markup=keyboard,
            )
        finally:
            db.close()

    await _send(format_briefing)
    await _send(format_evening_briefing)
    return {"status": "sent"}


@app.get("/")
def root():
    return FileResponse("static/index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
