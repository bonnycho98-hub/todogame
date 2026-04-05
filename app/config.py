from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")
BRIEFING_HOUR = int(os.environ.get("BRIEFING_HOUR", "8"))
BRIEFING_MINUTE = int(os.environ.get("BRIEFING_MINUTE", "0"))
