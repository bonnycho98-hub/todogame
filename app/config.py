from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")
BRIEFING_HOUR = int(os.environ.get("BRIEFING_HOUR", "6"))
BRIEFING_MINUTE = int(os.environ.get("BRIEFING_MINUTE", "0"))
EVENING_HOUR = int(os.environ.get("EVENING_HOUR", "19"))
EVENING_MINUTE = int(os.environ.get("EVENING_MINUTE", "0"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
