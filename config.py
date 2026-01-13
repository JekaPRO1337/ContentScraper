import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API Credentials
API_ID = 33824752
API_HASH = '6697c31639102932cfb5ec76299fecdd'

# Bot Token (from .env)
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Admin User ID (from .env)
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

# Database
DATABASE_PATH = 'content_cloner.db'

# FloodWait settings
FLOODWAIT_RETRY_DELAY = 1
MAX_FLOODWAIT_RETRIES = 5
