import asyncio
from pyrogram import Client, errors
from config import BOT_TOKEN, ADMIN_ID, API_ID, API_HASH
from database import db
from handlers.scraper import setup_scraper_handler, set_sender_client
from handlers.admin_menu import setup_admin_handlers, send_admin_menu, set_user_client
import os
import logging

try:
    from config import DEBUG_MODE
except ImportError:
    DEBUG_MODE = 'False'

def setup_logging():
    level = logging.DEBUG if str(DEBUG_MODE).lower() == 'true' else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Reduce noise from pyrogram if not debug
    if level == logging.INFO:
        logging.getLogger("pyrogram").setLevel(logging.WARNING)

async def main():
    """Main function to start the bot"""
    setup_logging()
    
    # Initialize database
    print("Initializing database...")
    await db.init_db()
    print("Database initialized!")

    # Validate mandatory Telegram API credentials
    try:
        current_api_id = int(API_ID) if str(API_ID).isdigit() else 0
    except:
        current_api_id = 0

    if current_api_id == 0 or not API_HASH:
        print("\n" + "!"*50)
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: API_ID или API_HASH не настроены!")
        print("Пожалуйста, откройте файл config.py и введите ваши данные.")
        print("Получить их можно на сайте https://my.telegram.org/apps")
        print("!"*50 + "\n")
        return

    # Mode Selection
    print("\n" + "="*30)
    print("ВЫБЕРИТЕ РЕЖИМ РАБОТЫ:")
    print("1. Запустить Бот-Скрапер (основной)")
    print("2. Запустить Channel ID Sniffer (поиск ID)")
    print("="*30)
    
    choice = input("Введите 1 или 2: ").strip()
    
    if choice == "2":
        from config import SNIFFER_LICENSE
        from utils.license_check import verify_license
        
        if not verify_license(SNIFFER_LICENSE):
            print("\n" + "!"*50)
            print("🛑 ДОСТУП ОГРАНИЧЕН")
            print("Sniffer ID Tool доступен только для пользователей с ПОЖИЗНЕННОЙ или ГОДОВОЙ VIP подпиской.")
            print("Для получения доступа напишите администратору: @admin")
            print("!"*50 + "\n")
            return
            
        from sniffer import start_sniffer
        session_name = "content_cloner_user"
        user_client = Client(session_name, api_id=current_api_id, api_hash=API_HASH)
        async with user_client:
            await start_sniffer(user_client)
        return
    
    # Create pyrogram client - use user session for reading channels without admin rights
    session_name = "content_cloner_user"
    
    # Check if session file exists
    session_file = f"{session_name}.session"
    if not os.path.exists(session_file):
        print("\n⚠️  Сессия не найдена. Нужна авторизация как пользователь.")
        print("Для чтения каналов без админских прав нужна user session.")
        print("При первом запуске вам нужно будет ввести номер телефона в международном формате (например, +380... или +7...) и код подтверждения.\n")
    
    # Custom callbacks for authorization prompts
    async def get_phone_number():
        return input("Enter phone number: ")

    async def get_code():
        return input("Enter code: ")

    # Create user client (for reading channels)
    user_client = Client(
        session_name,
        api_id=current_api_id,
        api_hash=API_HASH,
        phone_number_callback=get_phone_number,
        code_callback=get_code
    )
    
    # Create bot client (for admin commands, optional)
    bot_client = None
    if BOT_TOKEN:
        bot_client = Client(
            "content_cloner_bot",
            api_id=current_api_id,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )
    
    # Start user client (for reading channels)
    print("Starting user client...")
    try:
        await user_client.start()
    except errors.ApiIdInvalid:
        print("\n❌ ОШИБКА: Указанный API_ID или API_HASH недействительны.")
        print("Проверьте правильность данных в файле config.py")
        return
    except Exception as e:
        print(f"\n❌ Ошибка при запуске сессии: {e}")
        return
    
    user_info = await user_client.get_me()
    print(f"✅ User client запущен: {user_info.first_name} (@{user_info.username or 'нет имени'})")
    print(f"ID пользователя: {user_info.id}")
    
    # Start bot client if available (for admin commands)
    if bot_client:
        print("Starting bot client...")
        await bot_client.start()
        bot_info = await bot_client.get_me()
        print(f"Bot started as @{bot_info.username}")
        print(f"Bot ID: {bot_info.id}")
        
        # Setup admin handlers on bot client
        print("Setting up admin handlers...")
        set_user_client(user_client)
        setup_admin_handlers(bot_client)
        set_sender_client(bot_client)
        
        try:
            current_admin_id = int(ADMIN_ID)
        except ValueError:
            print(f"❌ ERROR: ADMIN_ID '{ADMIN_ID}' is not a valid integer. Check config.py.")
            current_admin_id = None

        if current_admin_id:
            try:
                await send_admin_menu(bot_client, current_admin_id, user_id=current_admin_id)
                print(f"✅ Admin menu sent to {current_admin_id}")
            except Exception as e:
                print(f"⚠️  Could not send admin menu to {current_admin_id}: {e}")
                print("   (Make sure you have started the bot with /start)")
    else:
        print("⚠️  Bot token not set. Admin commands will not work.")
        print("   Set BOT_TOKEN in config.py file to enable admin panel.")
    
    # Setup scraper on user client (for reading channels)
    print("Setting up scraper...")
    setup_scraper_handler(user_client)
    print("Handlers setup complete!")
    
    # Keep running
    print("\n✅ Bot is running. Press Ctrl+C to stop.")
    try:
        # Keep the bot running using asyncio.Event
        stop_event = asyncio.Event()
        await stop_event.wait()  # Wait indefinitely until stopped
    except KeyboardInterrupt:
        pass
    finally:
        # Stop clients
        print("\nStopping clients...")
        await user_client.stop()
        if bot_client:
            await bot_client.stop()
        print("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Error: {str(e)}")
