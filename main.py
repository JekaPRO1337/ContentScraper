import asyncio
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, ADMIN_ID
from database import db
from handlers.scraper import setup_scraper_handler
from handlers.admin_menu import setup_admin_handlers
import os


async def main():
    """Main function to start the bot"""
    # Validate configuration
    if ADMIN_ID == 0:
        print("WARNING: ADMIN_ID not set. Admin commands will not work.")
    
    # Initialize database
    print("Initializing database...")
    await db.init_db()
    print("Database initialized!")
    
    # Create Pyrogram client - use user session for reading channels without admin rights
    # Bot token is optional and only used for admin commands
    session_name = "content_cloner_user"
    
    # Check if session file exists
    session_file = f"{session_name}.session"
    if not os.path.exists(session_file):
        print("\n⚠️  Сессия не найдена. Нужна авторизация как пользователь.")
        print("Для чтения каналов без админских прав нужна user session.")
        print("При первом запуске вам нужно будет ввести номер телефона и код подтверждения.\n")
    
    # Create user client (for reading channels)
    user_client = Client(
        session_name,
        api_id=API_ID,
        api_hash=API_HASH
    )
    
    # Create bot client (for admin commands, optional)
    bot_client = None
    if BOT_TOKEN:
        bot_client = Client(
            "content_cloner_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )
    
    # Start user client (for reading channels)
    print("Starting user client...")
    await user_client.start()
    
    user_info = await user_client.get_me()
    print(f"User client started: {user_info.first_name} (@{user_info.username or 'no username'})")
    print(f"User ID: {user_info.id}")
    
    # Start bot client if available (for admin commands)
    if bot_client:
        print("Starting bot client...")
        await bot_client.start()
        bot_info = await bot_client.get_me()
        print(f"Bot started as @{bot_info.username}")
        print(f"Bot ID: {bot_info.id}")
        
        # Setup admin handlers on bot client
        print("Setting up admin handlers...")
        setup_admin_handlers(bot_client)
        
        if ADMIN_ID:
            try:
                await bot_client.send_message(
                    ADMIN_ID,
                    "🤖 **Content Cloner Bot Started!**\n\n"
                    "Use /admin to open the admin panel."
                )
            except:
                print("Could not send startup message to admin.")
    else:
        print("⚠️  Bot token not set. Admin commands will not work.")
        print("   Set BOT_TOKEN in .env file to enable admin panel.")
    
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
