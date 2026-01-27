import os
from dotenv import load_dotenv

# Force loading .env from the same directory as config.py
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Telegram API Credentials (now in keys.py)

# Bot Token (from .env)
BOT_TOKEN = os.getenv('BOT_TOKEN', '0')

# Admin User ID (from .env)
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

# Sniffer License (Yearly VIP only)
SNIFFER_LICENSE = os.getenv('SNIFFER_LICENSE', '')

# Database
DATABASE_PATH = 'content_cloner.db'

# FloodWait settings
FLOODWAIT_RETRY_DELAY = 1
MAX_FLOODWAIT_RETRIES = 5
