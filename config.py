import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB max file size
DATABASE_URL = "sqlite:///bot.db" 