import os
import asyncio
from datetime import datetime
from pyrogram import Client, filters, errors
from config import API_ID, API_HASH

# HTML Template and Styles
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sniffer Logs | Premium Tools</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0a0a0f;
            --glass: rgba(255, 255, 255, 0.05);
            --accent: #8b5cf6;
            --accent-glow: rgba(139, 92, 246, 0.3);
            --text: #ffffff;
            --text-dim: #94a3b8;
        }
        body {
            background: var(--bg-dark);
            color: var(--text);
            font-family: 'Outfit', sans-serif;
            margin: 0;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            max-width: 900px;
            width: 100%;
        }
        .header {
            text-align: center;
            margin-bottom: 3rem;
        }
        h1 {
            font-size: 3rem;
            background: linear-gradient(135deg, #a78bfa, #8b5cf6, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        .actions {
            margin-bottom: 2rem;
            display: flex;
            justify-content: center;
        }
        .btn-copy-all {
            background: var(--accent);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 700;
            cursor: pointer;
            transition: box-shadow 0.2s;
        }
        .btn-copy-all:hover {
            box-shadow: 0 0 15px var(--accent-glow);
        }
        .log-entry {
            background: var(--glass);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 1.5rem;
            transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
            position: relative;
            overflow: hidden;
        }
        .log-entry:hover {
            transform: translateY(-4px);
            border-color: var(--accent);
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .log-entry::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 6px;
            height: 100%;
            background: var(--accent);
        }
        .flex {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        .id-badge {
            background: rgba(139, 92, 246, 0.15);
            border: 1px solid var(--accent);
            color: #c4b5fd;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 1rem;
            font-weight: 700;
            font-family: monospace;
            cursor: pointer;
            transition: background 0.2s;
        }
        .id-badge:hover {
            background: var(--accent);
            color: white;
        }
        .title {
            font-size: 1.5rem;
            font-weight: 700;
            color: white;
        }
        .time {
            color: var(--text-dim);
            font-size: 0.85rem;
            margin-top: 1rem;
            display: block;
            opacity: 0.6;
        }
        .preview {
            background: rgba(0,0,0,0.2);
            padding: 1rem;
            border-radius: 8px;
            color: var(--text-dim);
            font-size: 1rem;
            font-style: italic;
            margin-top: 0.5rem;
            border-left: 2px solid rgba(255,255,255,0.1);
        }
    </style>
    <script>
        function copyId(id, event) {
            navigator.clipboard.writeText(id);
            const badge = event.currentTarget;
            const originalText = badge.innerText;
            badge.innerText = 'Скопировано!';
            setTimeout(() => badge.innerText = originalText, 1000);
        }
        
        function copyAll() {
            const badges = document.querySelectorAll('.id-badge');
            const ids = Array.from(badges).map(b => b.innerText.split(' ')[0]).join('\\n');
            navigator.clipboard.writeText(ids);
            const btn = document.querySelector('.btn-copy-all');
            btn.innerText = 'Все ID скопированы!';
            setTimeout(() => btn.innerText = 'Скопировать все ID', 2000);
        }
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Channel ID Sniffer</h1>
            <p style="color: var(--text-dim); font-size: 1.2rem;">Результаты перехвата каналов в реальном времени</p>
        </div>
        <div class="actions">
            <button class="btn-copy-all" onclick="copyAll()">Скопировать все ID</button>
        </div>
        <div id="logs">
            <!-- LOGS_INSERTION_POINT -->
        </div>
    </div>
</body>
</html>
"""

LOG_FILE = "sniffer_log.html"

def init_html_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(HTML_TEMPLATE)
        print(f"✅ Создан файл логов: {LOG_FILE}")

def append_to_html(chat_id, chat_title, preview_text):
    time_str = datetime.now().strftime("%H:%M:%S")
    sanitized_title = str(chat_title).replace("<", "&lt;").replace(">", "&gt;")
    sanitized_preview = str(preview_text).replace("<", "&lt;").replace(">", "&gt;")[:100]
    
    entry_html = f"""
            <div class="log-entry">
                <div class="flex">
                    <div class="title">{sanitized_title}</div>
                    <div class="id-badge" onclick="copyId('{chat_id}', event)">{chat_id}</div>
                </div>
                <div class="preview">"{sanitized_preview}..."</div>
                <div class="time">Перехвачено в {time_str}</div>
            </div>
"""
    
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "<!-- LOGS_INSERTION_POINT -->" in content:
            new_content = content.replace("<!-- LOGS_INSERTION_POINT -->", entry_html + "\n            <!-- LOGS_INSERTION_POINT -->")
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write(new_content)
    except Exception as e:
        print(f"❌ Ошибка записи в HTML: {e}")

async def start_sniffer(client: Client):
    print("\n" + "="*50)
    print("🚀 SNIFFER MODE ACTIVATED")
    print("📡 Слушаю все входящие сообщения...")
    print(f"📁 Логи сохраняются в: {os.path.abspath(LOG_FILE)}")
    print("="*50 + "\n")
    
    init_html_log()

    @client.on_message(filters.all)
    async def sniffer_handler(client, message):
        if message.chat:
            chat_id = message.chat.id
            chat_name = message.chat.title or message.chat.first_name or "Unknown"
            text_preview = message.text or message.caption or "[Медиа]"
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Перехвачен ID: {chat_id} | Name: {chat_name}")
            append_to_html(chat_id, chat_name, text_preview)

    print("Сниффер запущен. Нажмите Ctrl+C для выхода.")
    # Keep running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    # For standalone testing if needed
    try:
        current_api_id = int(API_ID)
    except:
        current_api_id = 0
        
    app = Client("content_cloner_user", api_id=current_api_id, api_hash=API_HASH)
    
    async def run():
        async with app:
            await start_sniffer(app)
    
    asyncio.run(run())
