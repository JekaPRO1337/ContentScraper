import os
from dotenv import load_dotenv

# Force loading .env from the same directory as config.py
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Telegram API Credentials (from .env)
_api_id = os.getenv('API_ID', '0')
API_ID = int(_api_id) if _api_id.isdigit() else 0
API_HASH = os.getenv('API_HASH', '').strip("'\" ")

# Bot Token (from .env)
BOT_TOKEN = os.getenv('BOT_TOKEN', '0').strip("'\" ")

# Admin User ID (from .env)
_admin_id = os.getenv('ADMIN_ID', '0')
ADMIN_ID = int(_admin_id) if _admin_id.isdigit() else 0

# Sniffer License (Yearly VIP only)
SNIFFER_LICENSE = os.getenv('SNIFFER_LICENSE', '').strip("'\" ")

# Database
DATABASE_PATH = 'content_cloner.db'

# FloodWait settings
FLOODWAIT_RETRY_DELAY = 1
MAX_FLOODWAIT_RETRIES = 5
