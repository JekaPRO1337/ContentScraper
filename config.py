# --- ContentScraper Configuration ---
# Все настройки находятся здесь.
# ВАЖНО: Все значения должны быть в ОДИНАРНЫХ кавычках ('...').

# --- Telegram API Settings ---
# Получить можно здесь: https://my.telegram.org/apps
# Введите полученные api_id и api_hash ниже.
_api_id_str = '12345678'  # Ваш App api_id
API_HASH = 'abcdef1234567890abcdef1234567890'

# --- Bot Settings ---
# Токен вашего бота от @BotFather
BOT_TOKEN = '1234567890:AAH5RfuBAl852cn5ZFxSGG8hWu2tITnOfVE'

# Ваш Telegram ID (узнать можно у @userinfobot)
_admin_id_str = '123456789'

# --- Licenses ---
# Вставьте сюда ваш лицензионный ключ для активации Сниффера (Mode 2)
# Пустой ключ '' означает ограниченный режим.
SNIFFER_LICENSE = ''

# --- Advanced Settings ---
DATABASE_PATH = 'content_cloner.db'
FLOODWAIT_RETRY_DELAY = 1
MAX_FLOODWAIT_RETRIES = 5

# --- System Logic (Не трогать) ---
# Автоматическая конвертация строк в числа для работы программы
try:
    API_ID = int(_api_id_str)
except ValueError:
    API_ID = 0

try:
    ADMIN_ID = int(_admin_id_str)
except ValueError:
    ADMIN_ID = 0
