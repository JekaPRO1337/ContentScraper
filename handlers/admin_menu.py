from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import ADMIN_ID
from handlers.scraper import (
    clear_memory_cache,
    scrape_latest_n_messages,
    scrape_full_history,
    scrape_first_n_messages,
)
import re
import asyncio


_user_client: Client | None = None
SCRAPE_N = 50


def set_user_client(client: Client | None):
    global _user_client
    _user_client = client


def _normalize_chat_ref(chat_ref: str) -> str:
    return (
        str(chat_ref)
        .strip()
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
    )


async def _resolve_chat_for_admin(client: Client, chat_ref: str):
    ref = _normalize_chat_ref(chat_ref)
    if ref.startswith("@"):
        return await client.get_chat(ref)
    if ref.startswith("-") or ref.isdigit():
        return await client.get_chat(int(ref))
    return await client.get_chat(f"@{ref}")


def _t(lang: str, key: str) -> str:
    lang = (lang or "ru").lower()
    texts = {
        "ru": {
            "admin_panel_title": "**🤖 Админ-панель**\n\nВыберите действие:",
            "btn_stats": "📊 Статистика",
            "btn_add_pair": "➕ Добавить пару",
            "btn_remove_pair": "➖ Удалить пару",
            "btn_button_rules": "🧷 Кнопки",
            "btn_list_pairs": "📋 Список пар",
            "btn_language": "🌐 Язык",
            "btn_close": "❌ Закрыть",
            "btn_back": "🔙 Назад",
            "btn_scrape_menu": "⚙️ Скрапинг",
            "btn_yes": "✅ Да",
            "btn_no": "❌ Нет",
            "language_title": "**🌐 Язык**\n\nВыберите язык интерфейса:",
            "btn_lang_ru": "Русский ✅",
            "btn_lang_en": "English",
            "language_updated_ru": "Язык переключен на русский.",
            "language_updated_en": "Language switched to English.",
            "no_pairs": "Нет настроенных пар каналов.",
            "no_pairs_remove": "Нет пар для удаления.",
            "stats_title": "**📊 Статистика**\n\n",
            "list_pairs_title": "**📋 Пары каналов**\n\n",
            "add_pair_title": "**➕ Добавить пару**\n\n",
            "add_pair_prompt": "Отправьте пару в формате:\n`/addpair donor_channel target_channel`\n\nПример:\n`/addpair @donorchannel @targetchannel`\n\nИли используйте ID каналов:\n`/addpair -1001234567890 -1009876543210`",
            "remove_pair_title": "**➖ Удалить пару**\n\n",
            "remove_pair_prompt": "Отправьте ID пары для удаления:\n`/removepair <pair_id>`\n\nДоступные пары:\n",
            "button_rules_title": "**🧷 Кнопки**\n\n",
            "button_rules_none": "Кнопки не настроены.\n\n",
            "button_rules_commands": "**Команды:**\n`/addbtn1 текст|url`\n`/addbtn2 t1|u1 || t2|u2`\n`/removebtn` — удалить кнопки",
            "label_mode": "Режим",
            "label_btn1": "Кнопка 1",
            "label_btn2": "Кнопка 2",
            "addbtn1_usage": "**Использование:** `/addbtn1 текст|url`",
            "addbtn2_usage": "**Использование:** `/addbtn2 t1|u1 || t2|u2`",
            "removebtn_usage": "**Использование:** `/removebtn`",
            "button_rule_added": "✅ Кнопки обновлены!",
            "button_rule_removed": "✅ Кнопки удалены!",
            "button_rule_invalid": "❌ Некорректный формат. Проверь команду.",
            "label_pair_id": "ID пары",
            "label_donor": "Донор",
            "label_target": "Цель",
            "label_posts_cloned": "Постов",
            "label_last_cloned": "Последний",
            "label_total_posts": "Всего постов",
            "label_rule_id": "ID правила",
            "label_pattern": "Шаблон",
            "label_replacement": "Замена",
            "cleardb_done": "✅ База очищена (пары/статистика/обработанные сообщения).",
            "cleardb_done_all": "✅ База очищена (включая правила ссылок).",
            "addpair_usage": "**Использование:** `/addpair donor_channel target_channel`\n\n**Примеры:**\n`/addpair @testchannel @targetchannel`\n`/addpair -1001234567890 -1009876543210`\n\n💡 **Для каналов без username используйте ID канала**\nПолучить ID можно через @userinfobot или @getidsbot",
            "addpair_resolve_warn": "⚠️ Не удалось проверить каналы: {error}\nПродолжаю с указанными значениями...",
            "addpair_success": "✅ **Пара каналов успешно добавлена!**\n\n**ID пары:** {pair_id}\n**Донор:** `{donor}`\n**Целевой:** `{target}`",
            "remove_usage": "**Использование:** `/removepair <pair_id>`",
            "remove_success": "✅ Пара каналов {pair_id} успешно удалена!",
            "remove_invalid": "❌ Некорректный ID пары. Укажите число.",
            "addrule_usage": "**Использование:** `/addrule <pattern> [replacement]`\n\n"
                             "Что такое pattern и replacement:\n"
                             "• pattern — слово/фраза для поиска. Можно начать с `regex:` для регулярного выражения.\n"
                             "• replacement — чем заменить. Необязательный параметр: если не указан, слово будет удалено.\n\n"
                             "Как работает замена:\n"
                             "• Регистр игнорируется (Parimatch = париматч).\n"
                             "• Можно создавать много правил — они применяются по очереди.\n"
                             "• Гиперссылка в формате Markdown: `[текст](https://example.com)`.\n\n"
                             "Примеры:\n"
                             "• Удалить слово: `/addrule Париматч`\n"
                             "• Заменить на текст: `/addrule Parimatch Мойтекст`\n"
                             "• Заменить на гиперссылку: `/addrule Favbet [Наш партнёр](https://example.com)`\n"
                             "• Regex для вариаций: `/addrule regex:(parimatch|парик|париматч)\\d* [Ссылка](https://example.com)`\n"
                             "• Удалить вариации по regex: `/addrule regex:(Parik|Парик)\\d*`",
            "addrule_required": "❌ Шаблон обязателен.",
            "addrule_success": "✅ Правило добавлено!\n\n**ID правила:** {rule_id}\n**Шаблон:** `{pattern}`\n**Замена:** `{replacement}`",
            "removerule_usage": "**Использование:** `/removerule <rule_id>`",
            "removerule_success": "✅ Правило {rule_id} удалено!",
            "removerule_invalid": "❌ Некорректный ID правила. Укажите число.",
            "generic_error": "❌ Ошибка: {error}",
            "scrape_menu_title": "**⚙️ Режимы скрапа**\n\nВыберите пару каналов:",
            "scrape_menu_no_pairs": "Нет пар для скрапа.",
            "scrape_pair_title": "**⚙️ Режимы скрапа для пары {pair_id}**\n\n",
            "scrape_pair_description": "Донор: `{donor}`\nЦель: `{target}`\n\n",
            "scrape_modes_help": "Режимы:\n"
                                "• Скрап N последних постов — берёт последние {n} сообщений.\n"
                                "• Скрап N первых постов — берёт самые старые {n} сообщений, которые ещё не скрапились.\n"
                                "• Полный скрап — проходит по всей истории и добавляет все ещё не скрапленные посты.\n\n",
            "scrape_bot_admin_note": "Важно: бот должен быть администратором в целевом канале, иначе он не сможет публиковать посты.\n\n",
            "btn_scrape_latest": "▶️ Скрап N последних постов",
            "btn_scrape_first": "⏮️ Скрап N первых постов",
            "btn_scrape_full": "📥 Полный скрап",
            "btn_scrape_realtime_on": "🔄 Скрап в реальном времени: Включён",
            "btn_scrape_realtime_off": "🔄 Скрап в реальном времени: Выключен",
            "scrape_full_confirm": "Вы уверены, что хотите запустить полный скрап для этой пары?\nЭто может занять время при большом количестве постов.",
            "scrape_started_latest": "Запущен скрап {n} последних постов для пары {pair_id}.",
            "scrape_started_first": "Запущен скрап {n} первых постов для пары {pair_id}.",
            "scrape_started_full": "Запущен полный скрап для пары {pair_id}.\n\n"
                                   "После завершения вы можете включить режим скрапа в реальном "
                                   "времени кнопкой ниже.",
            "scrape_no_pair": "Пара не найдена.",
            "realtime_enabled": "Режим скрапа в реальном времени включён для пары {pair_id}.",
            "realtime_disabled": "Режим скрапа в реальном времени выключен для пары {pair_id}.",
            "scrape_choose_n_latest": "**▶️ Скрап последних постов**\n\nВыберите, сколько последних сообщений скрапить:",
            "scrape_choose_n_first": "**⏮️ Скрап первых постов**\n\nВыберите, сколько самых старых сообщений скрапить:",
            "btn_scrape_n_10": "10",
            "btn_scrape_n_50": "50",
            "btn_scrape_n_100": "100",
            "btn_scrape_n_200": "200",
            "btn_scrape_reset": "♻️ Сбросить прогресс скрапа",
            "scrape_reset_done": "Прогресс скрапа и счётчик постов для пары {pair_id} сброшены. Можно скрапить заново.",
            "btn_link_rules": "🧮 Замена ключевых слов",
            "link_rules_title": "**🧮 Замена ключевых слов**\n\n",
            "link_rules_none": "Правила ещё не настроены.\n\n",
            "link_rules_commands": "**Команды:**\n"
                                  "`/addrule <pattern> [replacement]` — добавить правило\n"
                                  "`/removerule <rule_id>` — удалить правило по ID\n"
                                  "`/removerulepat <pattern>` — удалить по шаблону\n\n"
                                  "**Примеры:**\n"
                                  "• Удаление: `/addrule Париматч`\n"
                                  "• Замена текстом: `/addrule Parimatch 1win`\n"
                                  "• Замена гиперссылкой: `/addrule Favbet [Наш сайт](https://site.ua)`\n"
                                  "• Regex: `/addrule regex:(parimatch|париматч)\\d* [Партнёр](https://example.com)`\n\n"
                                  "Примечания:\n"
                                  "• Можно создавать много правил — они применяются по очереди.\n"
                                  "• Шаблон может быть текстом или `regex:`.\n"
                                  "• Замена может содержать текст и ссылки (Markdown).",
        },
        "en": {
            "admin_panel_title": "**🤖 Admin Panel**\n\nSelect an option:",
            "btn_stats": "📊 Statistics",
            "btn_add_pair": "➕ Add Channel Pair",
            "btn_remove_pair": "➖ Remove Channel Pair",
            "btn_button_rules": "🧷 Buttons",
            "btn_list_pairs": "📋 Channel Pairs",
            "btn_language": "🌐 Language",
            "btn_close": "❌ Close",
            "btn_back": "🔙 Back",
            "btn_scrape_menu": "⚙️ Scraping",
            "btn_yes": "✅ Yes",
            "btn_no": "❌ No",
            "language_title": "**🌐 Language**\n\nChoose interface language:",
            "btn_lang_ru": "Русский",
            "btn_lang_en": "English ✅",
            "language_updated_ru": "Язык переключен на русский.",
            "language_updated_en": "Language switched to English.",
            "no_pairs": "No channel pairs configured.",
            "no_pairs_remove": "No channel pairs to remove.",
            "stats_title": "**📊 Statistics**\n\n",
            "list_pairs_title": "**📋 Channel Pairs**\n\n",
            "add_pair_title": "**➕ Add Channel Pair**\n\n",
            "add_pair_prompt": "Send the pair in format:\n`/addpair donor_channel target_channel`\n\nExample:\n`/addpair @donorchannel @targetchannel`\n\nOr use channel IDs:\n`/addpair -1001234567890 -1009876543210`",
            "remove_pair_title": "**➖ Remove Channel Pair**\n\n",
            "remove_pair_prompt": "Send pair ID to remove:\n`/removepair <pair_id>`\n\nAvailable pairs:\n",
            "button_rules_title": "**🧷 Buttons**\n\n",
            "button_rules_none": "Buttons are not configured.\n\n",
            "button_rules_commands": "**Commands:**\n`/addbtn1 text|url`\n`/addbtn2 t1|u1 || t2|u2`\n`/removebtn` — remove buttons",
            "label_mode": "Mode",
            "label_btn1": "Button 1",
            "label_btn2": "Button 2",
            "addbtn1_usage": "**Usage:** `/addbtn1 text|url`",
            "addbtn2_usage": "**Usage:** `/addbtn2 t1|u1 || t2|u2`",
            "removebtn_usage": "**Usage:** `/removebtn`",
            "button_rule_added": "✅ Buttons updated!",
            "button_rule_removed": "✅ Buttons removed!",
            "button_rule_invalid": "❌ Invalid format. Please check the command.",
            "label_pair_id": "Pair ID",
            "label_donor": "Donor",
            "label_target": "Target",
            "label_posts_cloned": "Posts",
            "label_last_cloned": "Last",
            "label_total_posts": "Total posts",
            "label_rule_id": "Rule ID",
            "label_pattern": "Pattern",
            "label_replacement": "Replacement",
            "cleardb_done": "✅ Database cleared (pairs/statistics/processed messages).",
            "cleardb_done_all": "✅ Database cleared (including link rules).",
            "addpair_usage": "**Usage:** `/addpair donor_channel target_channel`\n\n**Examples:**\n`/addpair @testchannel @targetchannel`\n`/addpair -1001234567890 -1009876543210`\n\n💡 **For channels without username use channel ID**\nYou can get IDs via @userinfobot or @getidsbot",
            "addpair_resolve_warn": "⚠️ Could not validate channels: {error}\nContinuing with provided values...",
            "addpair_success": "✅ **Channel pair added!**\n\n**Pair ID:** {pair_id}\n**Donor:** `{donor}`\n**Target:** `{target}`",
            "remove_usage": "**Usage:** `/removepair <pair_id>`",
            "remove_success": "✅ Channel pair {pair_id} removed successfully!",
            "remove_invalid": "❌ Invalid pair ID. Please provide a number.",
            "addrule_usage": "**Usage:** `/addrule <pattern> <replacement>`\n\nExample: `/addrule https://example.com https://myaffiliate.com`\nFor regex: `/addrule regex:example\\.com myaffiliate.com`",
            "addrule_required": "❌ Pattern is required.",
            "addrule_success": "✅ Link rule added!\n\n**Rule ID:** {rule_id}\n**Pattern:** `{pattern}`\n**Replacement:** `{replacement}`",
            "removerule_usage": "**Usage:** `/removerule <rule_id>`",
            "removerule_success": "✅ Link rule {rule_id} removed successfully!",
            "removerule_invalid": "❌ Invalid rule ID. Please provide a number.",
            "generic_error": "❌ Error: {error}",
            "scrape_menu_title": "**⚙️ Scraping Modes**\n\nSelect a channel pair:",
            "scrape_menu_no_pairs": "No channel pairs for scraping.",
            "scrape_pair_title": "**⚙️ Scraping modes for pair {pair_id}**\n\n",
            "scrape_pair_description": "Donor: `{donor}`\nTarget: `{target}`\n\n",
            "scrape_modes_help": "Modes:\n"
                                "• Scrape N latest posts — takes the last {n} messages.\n"
                                "• Scrape N first posts — takes the oldest {n} messages that were not scraped yet.\n"
                                "• Full scrape — walks through the entire history and adds all not yet scraped posts.\n\n",
            "scrape_bot_admin_note": "Important: the bot must be an admin in the target channel, otherwise it cannot send posts.\n\n",
            "btn_scrape_latest": "▶️ Scrape N latest posts",
            "btn_scrape_first": "⏮️ Scrape N first posts",
            "btn_scrape_full": "📥 Full scrape",
            "btn_scrape_realtime_on": "🔄 Realtime scraping: Enabled",
            "btn_scrape_realtime_off": "🔄 Realtime scraping: Disabled",
            "scrape_full_confirm": "Are you sure you want to start a full scrape for this pair?\nThis may take time for large channels.",
            "scrape_started_latest": "Started scraping {n} latest posts for pair {pair_id}.",
            "scrape_started_first": "Started scraping {n} first posts for pair {pair_id}.",
            "scrape_started_full": "Started full scrape for pair {pair_id}.\n\n"
                                   "When it finishes you can enable realtime scraping using the "
                                   "button below.",
            "scrape_no_pair": "Channel pair not found.",
            "realtime_enabled": "Realtime scraping mode enabled for pair {pair_id}.",
            "realtime_disabled": "Realtime scraping mode disabled for pair {pair_id}.",
            "scrape_choose_n_latest": "**▶️ Scrape latest posts**\n\nChoose how many latest messages to scrape:",
            "scrape_choose_n_first": "**⏮️ Scrape first posts**\n\nChoose how many oldest messages to scrape:",
            "btn_scrape_n_10": "10",
            "btn_scrape_n_50": "50",
            "btn_scrape_n_100": "100",
            "btn_scrape_n_200": "200",
            "btn_scrape_reset": "♻️ Reset scrape progress",
            "scrape_reset_done": "Scrape progress and post counter for pair {pair_id} have been reset. You can scrape again.",
            "btn_link_rules": "🧮 Keyword replacement",
            "link_rules_title": "**🧮 Keyword / link replacement**\n\n",
            "link_rules_none": "No rules configured yet.\n\n",
            "link_rules_commands": "**Commands:**\n"
                                  "`/addrule <pattern> [replacement]` — add rule\n"
                                  "`/removerule <rule_id>` — remove by ID\n"
                                  "`/removerulepat <pattern>` — remove by pattern\n\n"
                                  "**Examples:**\n"
                                  "• Delete: `/addrule Parimatch`\n"
                                  "• Replace with text: `/addrule Parimatch MyText`\n"
                                  "• Replace with hyperlink: `/addrule Favbet [Partner](https://example.com)`\n"
                                  "• Regex: `/addrule regex:(parimatch|parik)\\d* [Link](https://example.com)`\n\n"
                                  "Notes:\n"
                                  "• Multiple rules are supported and applied in order.\n"
                                  "• Pattern can be plain text or `regex:`.\n"
                                  "• Replacement may contain text or Markdown links.",
        },
    }

    return texts.get(lang, texts["ru"]).get(key, key)


async def _get_lang_from_message(message: Message) -> str:
    try:
        if message and message.from_user:
            return await db.get_user_lang(message.from_user.id)
    except Exception:
        pass
    return "ru"


async def _get_lang_from_callback(callback_query) -> str:
    try:
        if callback_query and callback_query.from_user:
            return await db.get_user_lang(callback_query.from_user.id)
    except Exception:
        pass
    return "ru"

async def _pair_access_report(bot_client: Client, donor: str, target: str) -> str:
    lang = await db.get_user_lang(ADMIN_ID or 0)
    donor_status = "✅"
    donor_hint = ""
    target_status = "✅"
    target_hint = ""
    try:
        resolver = _user_client or bot_client
        ref = donor.strip().replace("−", "-").replace("–", "-").replace("—", "-")
        chat_obj = await resolver.get_chat(int(ref) if ref.startswith("-") or ref.isdigit() else ref if ref.startswith("@") else f"@{ref}")
        _ = chat_obj.id
    except Exception as e:
        donor_status = "❌"
        donor_hint = "Пользовательская сессия не имеет доступа к донору. Подпишитесь на канал."
    try:
        me = await bot_client.get_me()
        ref_t = target.strip().replace("−", "-").replace("–", "-").replace("—", "-")
        member = await bot_client.get_chat_member(int(ref_t) if ref_t.startswith("-") or ref_t.isdigit() else ref_t if ref_t.startswith("@") else f"@{ref_t}", me.id)
        role = str(getattr(member, "status", "")).lower()
        if role not in {"administrator", "owner"}:
            target_status = "❌"
            target_hint = "Бот не администратор целевого канала."
    except Exception as e:
        target_status = "❌"
        target_hint = "Бот не может получить доступ к целевому каналу."
    report = ""
    report += f"Доступ к донору: {donor_status}"
    if donor_hint:
        report += f" — {donor_hint}\n"
    else:
        report += "\n"
    report += f"Доступ бота к цели: {target_status}"
    if target_hint:
        report += f" — {target_hint}\n\n"
    else:
        report += "\n\n"
    return report

def _admin_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(_t(lang, "btn_stats"), callback_data="admin_stats"),
            InlineKeyboardButton(_t(lang, "btn_add_pair"), callback_data="admin_add_pair"),
        ],
        [
            InlineKeyboardButton(_t(lang, "btn_remove_pair"), callback_data="admin_remove_pair"),
            InlineKeyboardButton(_t(lang, "btn_list_pairs"), callback_data="admin_list_pairs"),
        ],
        [
            InlineKeyboardButton(_t(lang, "btn_button_rules"), callback_data="admin_button_rules"),
            InlineKeyboardButton(_t(lang, "btn_link_rules"), callback_data="admin_link_rules"),
        ],
        [
            InlineKeyboardButton(_t(lang, "btn_scrape_menu"), callback_data="admin_scrape_menu"),
            InlineKeyboardButton(_t(lang, "btn_language"), callback_data="admin_language"),
        ],
        [
            InlineKeyboardButton(_t(lang, "btn_close"), callback_data="admin_close"),
        ],
    ])


async def send_admin_menu(client: Client, chat_id: int, user_id: int | None = None):
    """Send main admin menu to a chat (used on startup)."""
    uid = int(user_id) if user_id is not None else int(chat_id)
    lang = await db.get_user_lang(uid)
    await client.send_message(
        chat_id,
        _t(lang, "admin_panel_title"),
        reply_markup=_admin_menu_keyboard(lang)
    )

async def show_admin_menu(client: Client, message: Message):
    """Show main admin menu"""
    lang = await _get_lang_from_message(message)
    keyboard = _admin_menu_keyboard(lang)
    
    await message.reply_text(
        _t(lang, "admin_panel_title"),
        reply_markup=keyboard
    )


async def handle_admin_stats(client: Client, callback_query):
    """Show statistics"""
    stats = await db.get_statistics()
    
    if not stats:
        lang = await _get_lang_from_callback(callback_query)
        await callback_query.answer(_t(lang, "no_pairs"), show_alert=True)
        return
    
    lang = await _get_lang_from_callback(callback_query)
    text = _t(lang, "stats_title")
    total_posts = 0
    
    for stat in stats:
        text += f"**{_t(lang, 'label_pair_id')}:** {stat['id']}\n"
        text += f"**{_t(lang, 'label_donor')}:** `{stat['donor_channel']}`\n"
        text += f"**{_t(lang, 'label_target')}:** `{stat['target_channel']}`\n"
        text += f"**{_t(lang, 'label_posts_cloned')}:** {stat['posts_cloned']}\n"
        if stat['last_cloned_at']:
            text += f"**{_t(lang, 'label_last_cloned')}:** {stat['last_cloned_at']}\n"
        text += "\n"
        total_posts += stat['posts_cloned']
    
    text += f"**{_t(lang, 'label_total_posts')}:** {total_posts}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(_t(await _get_lang_from_callback(callback_query), "btn_back"), callback_data="admin_menu")]
    ])
    
    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_scrape_menu(client: Client, callback_query):
    pairs = await db.get_statistics()

    lang = await _get_lang_from_callback(callback_query)

    if not pairs:
        await callback_query.answer(_t(lang, "scrape_menu_no_pairs"), show_alert=True)
        return

    text = _t(lang, "scrape_menu_title")
    for pair in pairs:
        text += f"**{_t(lang, 'label_pair_id')}:** {pair['id']}\n"
        text += f"**{_t(lang, 'label_donor')}:** `{pair['donor_channel']}`\n"
        text += f"**{_t(lang, 'label_target')}:** `{pair['target_channel']}`\n\n"

    keyboard_rows = []
    for pair in pairs:
        keyboard_rows.append([
            InlineKeyboardButton(
                f"{pair['id']}: {pair['donor_channel']} → {pair['target_channel']}",
                callback_data=f"admin_scrape_pair:{pair['id']}",
            )
        ])
    keyboard_rows.append(
        [InlineKeyboardButton(_t(lang, "btn_back"), callback_data="admin_menu")]
    )

    keyboard = InlineKeyboardMarkup(keyboard_rows)

    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_scrape_pair(client: Client, callback_query, pair_id: int):
    lang = await _get_lang_from_callback(callback_query)
    pair = await db.get_pair_by_id(pair_id)
    if not pair:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return

    text = _t(lang, "scrape_pair_title").format(pair_id=pair_id)
    text += _t(lang, "scrape_pair_description").format(
        donor=pair["donor_channel"],
        target=pair["target_channel"],
    )
    text += await _pair_access_report(client, pair["donor_channel"], pair["target_channel"])
    text += _t(lang, "scrape_modes_help").format(n=SCRAPE_N)
    text += _t(lang, "scrape_bot_admin_note")

    realtime_enabled = bool(pair.get("realtime_enabled"))
    if realtime_enabled:
        realtime_button_text = _t(lang, "btn_scrape_realtime_on")
    else:
        realtime_button_text = _t(lang, "btn_scrape_realtime_off")

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                _t(lang, "btn_scrape_latest").replace("N", str(SCRAPE_N)),
                callback_data=f"admin_scrape_latest_choose:{pair_id}",
            )
        ],
        [
            InlineKeyboardButton(
                _t(lang, "btn_scrape_first").replace("N", str(SCRAPE_N)),
                callback_data=f"admin_scrape_first_choose:{pair_id}",
            )
        ],
        [
            InlineKeyboardButton(
                _t(lang, "btn_scrape_full"),
                callback_data=f"admin_scrape_full_confirm:{pair_id}",
            )
        ],
        [
            InlineKeyboardButton(
                _t(lang, "btn_scrape_reset"),
                callback_data=f"admin_scrape_reset:{pair_id}",
            )
        ],
        [
            InlineKeyboardButton(
                realtime_button_text,
                callback_data=f"admin_scrape_realtime_toggle:{pair_id}",
            )
        ],
        [
            InlineKeyboardButton(_t(lang, "btn_back"), callback_data="admin_scrape_menu")
        ],
    ])

    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_button_rules(client: Client, callback_query):
    rules = await db.get_all_button_rules()

    lang = await _get_lang_from_callback(callback_query)
    text = _t(lang, "button_rules_title")

    if rules:
        rule = rules[0]
        mode = (rule.get('mode') or '').lower()
        text += f"{_t(lang, 'label_mode')}: `{mode}`\n"
        text += f"{_t(lang, 'label_btn1')}: `{(rule.get('text1') or '')}` | `{(rule.get('url1') or '')}`\n"
        if mode == 'two':
            text += f"{_t(lang, 'label_btn2')}: `{(rule.get('text2') or '')}` | `{(rule.get('url2') or '')}`\n"
        text += "\n"
    else:
        text += _t(lang, "button_rules_none")

    text += "\n" + _t(lang, "button_rules_commands")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(_t(lang, "btn_back"), callback_data="admin_menu")]
    ])
    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_list_pairs(client: Client, callback_query):
    """List all channel pairs"""
    pairs = await db.get_statistics()
    
    if not pairs:
        lang = await _get_lang_from_callback(callback_query)
        await callback_query.answer(_t(lang, "no_pairs"), show_alert=True)
        return
    
    lang = await _get_lang_from_callback(callback_query)
    text = _t(lang, "list_pairs_title")
    for pair in pairs:
        text += f"**{_t(lang, 'label_pair_id')}:** {pair['id']}\n"
        text += f"**{_t(lang, 'label_donor')}:** `{pair['donor_channel']}`\n"
        text += f"**{_t(lang, 'label_target')}:** `{pair['target_channel']}`\n"
        text += f"**{_t(lang, 'label_posts_cloned')}:** {pair['posts_cloned']}\n\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(_t(await _get_lang_from_callback(callback_query), "btn_back"), callback_data="admin_menu")]
    ])
    
    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_add_pair(client: Client, callback_query):
    """Prompt for adding channel pair"""
    await callback_query.answer()

    lang = await _get_lang_from_callback(callback_query)
    text = _t(lang, "add_pair_title") + _t(lang, "add_pair_prompt")
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(_t(await _get_lang_from_callback(callback_query), "btn_back"), callback_data="admin_menu")]
    ])
    
    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_remove_pair(client: Client, callback_query):
    """Prompt for removing channel pair"""
    pairs = await db.get_statistics()
    
    if not pairs:
        lang = await _get_lang_from_callback(callback_query)
        await callback_query.answer(_t(lang, "no_pairs_remove"), show_alert=True)
        return
    
    lang = await _get_lang_from_callback(callback_query)
    text = _t(lang, "remove_pair_title")
    text += _t(lang, "remove_pair_prompt")
    for pair in pairs:
        text += f"**{pair['id']}:** `{pair['donor_channel']}` → `{pair['target_channel']}`\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(_t(await _get_lang_from_callback(callback_query), "btn_back"), callback_data="admin_menu")]
    ])
    
    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_link_rules(client: Client, callback_query):
    """Show link rules menu"""
    rules = await db.get_all_link_rules()

    lang = await _get_lang_from_callback(callback_query)
    text = _t(lang, "link_rules_title")
    
    if rules:
        for rule in rules:
            text += f"**{_t(lang, 'label_rule_id')} {rule['id']}:**\n"
            text += f"{_t(lang, 'label_pattern')}: `{rule['pattern'][:50]}...`\n"
            text += f"{_t(lang, 'label_replacement')}: `{rule['replacement'][:50]}...`\n\n"
    else:
        text += _t(lang, "link_rules_none")

    text += _t(lang, "link_rules_commands")
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(_t(await _get_lang_from_callback(callback_query), "btn_back"), callback_data="admin_menu")
        ]
    ])
    
    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_language_menu(client: Client, callback_query):
    """Show language selection menu"""
    lang = await _get_lang_from_callback(callback_query)
    ru_btn = _t(lang, "btn_lang_ru")
    en_btn = _t(lang, "btn_lang_en")

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(ru_btn, callback_data="admin_set_lang:ru"),
            InlineKeyboardButton(en_btn, callback_data="admin_set_lang:en"),
        ],
        [InlineKeyboardButton(_t(lang, "btn_back"), callback_data="admin_menu")],
    ])

    await callback_query.edit_message_text(_t(lang, "language_title"), reply_markup=keyboard)


async def handle_scrape_latest(client: Client, callback_query):
    lang = await _get_lang_from_callback(callback_query)
    try:
        _, pair_part, n_part = callback_query.data.split(":", 2)
        pair_id = int(pair_part)
        n = int(n_part)
    except Exception:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return

    pair = await db.get_pair_by_id(pair_id)
    if not pair:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return
    report = await _pair_access_report(client, pair["donor_channel"], pair["target_channel"])
    if "❌" in report:
        await callback_query.answer(report, show_alert=True)
        return

    worker_client = _user_client or client
    asyncio.create_task(scrape_latest_n_messages(worker_client, pair_id, n))

    await callback_query.answer(
        _t(lang, "scrape_started_latest").format(n=n, pair_id=pair_id),
        show_alert=True,
    )
    await handle_scrape_pair(client, callback_query, pair_id)


async def handle_scrape_first(client: Client, callback_query):
    lang = await _get_lang_from_callback(callback_query)
    try:
        _, pair_part, n_part = callback_query.data.split(":", 2)
        pair_id = int(pair_part)
        n = int(n_part)
    except Exception:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return

    pair = await db.get_pair_by_id(pair_id)
    if not pair:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return
    report = await _pair_access_report(client, pair["donor_channel"], pair["target_channel"])
    if "❌" in report:
        await callback_query.answer(report, show_alert=True)
        return

    worker_client = _user_client or client
    asyncio.create_task(scrape_first_n_messages(worker_client, pair_id, n))

    await callback_query.answer(
        _t(lang, "scrape_started_first").format(n=n, pair_id=pair_id),
        show_alert=True,
    )
    await handle_scrape_pair(client, callback_query, pair_id)


async def handle_scrape_latest_choose(client: Client, callback_query):
    lang = await _get_lang_from_callback(callback_query)
    try:
        pair_id = int(callback_query.data.split(":", 1)[1])
    except Exception:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return

    pair = await db.get_pair_by_id(pair_id)
    if not pair:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return

    text = _t(lang, "scrape_choose_n_latest")
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                _t(lang, "btn_scrape_n_10"),
                callback_data=f"admin_scrape_latest:{pair_id}:10",
            ),
            InlineKeyboardButton(
                _t(lang, "btn_scrape_n_50"),
                callback_data=f"admin_scrape_latest:{pair_id}:50",
            ),
        ],
        [
            InlineKeyboardButton(
                _t(lang, "btn_scrape_n_100"),
                callback_data=f"admin_scrape_latest:{pair_id}:100",
            ),
            InlineKeyboardButton(
                _t(lang, "btn_scrape_n_200"),
                callback_data=f"admin_scrape_latest:{pair_id}:200",
            ),
        ],
        [
            InlineKeyboardButton(
                _t(lang, "btn_back"),
                callback_data=f"admin_scrape_pair:{pair_id}",
            )
        ],
    ])

    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_scrape_first_choose(client: Client, callback_query):
    lang = await _get_lang_from_callback(callback_query)
    try:
        pair_id = int(callback_query.data.split(":", 1)[1])
    except Exception:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return

    pair = await db.get_pair_by_id(pair_id)
    if not pair:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return

    text = _t(lang, "scrape_choose_n_first")
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                _t(lang, "btn_scrape_n_10"),
                callback_data=f"admin_scrape_first:{pair_id}:10",
            ),
            InlineKeyboardButton(
                _t(lang, "btn_scrape_n_50"),
                callback_data=f"admin_scrape_first:{pair_id}:50",
            ),
        ],
        [
            InlineKeyboardButton(
                _t(lang, "btn_scrape_n_100"),
                callback_data=f"admin_scrape_first:{pair_id}:100",
            ),
            InlineKeyboardButton(
                _t(lang, "btn_scrape_n_200"),
                callback_data=f"admin_scrape_first:{pair_id}:200",
            ),
        ],
        [
            InlineKeyboardButton(
                _t(lang, "btn_back"),
                callback_data=f"admin_scrape_pair:{pair_id}",
            )
        ],
    ])

    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_scrape_full_confirm(client: Client, callback_query):
    lang = await _get_lang_from_callback(callback_query)
    try:
        pair_id = int(callback_query.data.split(":", 1)[1])
    except Exception:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return

    text = _t(lang, "scrape_full_confirm")
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                _t(lang, "btn_yes"),
                callback_data=f"admin_scrape_full:{pair_id}",
            )
        ],
        [
            InlineKeyboardButton(
                _t(lang, "btn_no"),
                callback_data=f"admin_scrape_pair:{pair_id}",
            )
        ],
    ])
    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_scrape_full(client: Client, callback_query):
    lang = await _get_lang_from_callback(callback_query)
    try:
        pair_id = int(callback_query.data.split(":", 1)[1])
    except Exception:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return

    pair = await db.get_pair_by_id(pair_id)
    if not pair:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return
    report = await _pair_access_report(client, pair["donor_channel"], pair["target_channel"])
    if "❌" in report:
        await callback_query.answer(report, show_alert=True)
        return

    worker_client = _user_client or client
    asyncio.create_task(scrape_full_history(worker_client, pair_id))

    await callback_query.answer(
        _t(lang, "scrape_started_full").format(pair_id=pair_id),
        show_alert=True,
    )
    await handle_scrape_pair(client, callback_query, pair_id)


async def handle_scrape_realtime_toggle(client: Client, callback_query):
    lang = await _get_lang_from_callback(callback_query)
    try:
        pair_id = int(callback_query.data.split(":", 1)[1])
    except Exception:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return

    pair = await db.get_pair_by_id(pair_id)
    if not pair:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return

    current = bool(pair.get("realtime_enabled"))
    new_value = not current
    await db.set_realtime_enabled(pair_id, new_value)

    if new_value:
        await callback_query.answer(
            _t(lang, "realtime_enabled").format(pair_id=pair_id),
            show_alert=True,
        )
    else:
        await callback_query.answer(
            _t(lang, "realtime_disabled").format(pair_id=pair_id),
            show_alert=True,
        )

    await handle_scrape_pair(client, callback_query, pair_id)


async def handle_scrape_reset(client: Client, callback_query):
    lang = await _get_lang_from_callback(callback_query)
    try:
        pair_id = int(callback_query.data.split(":", 1)[1])
    except Exception:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return

    pair = await db.get_pair_by_id(pair_id)
    if not pair:
        await callback_query.answer(_t(lang, "scrape_no_pair"), show_alert=True)
        return

    await db.reset_pair_progress(pair_id)
    clear_memory_cache(pair["donor_channel"])

    await callback_query.answer(
        _t(lang, "scrape_reset_done").format(pair_id=pair_id),
        show_alert=True,
    )
    await handle_scrape_pair(client, callback_query, pair_id)


async def handle_set_language(client: Client, callback_query, lang_code: str):
    """Persist language selection"""
    user_id = callback_query.from_user.id
    await db.set_user_lang(user_id, lang_code)

    new_lang = await db.get_user_lang(user_id)
    if new_lang == "en":
        await callback_query.answer(_t("en", "language_updated_en"), show_alert=False)
    else:
        await callback_query.answer(_t("ru", "language_updated_ru"), show_alert=False)

    await callback_query.edit_message_text(
        _t(new_lang, "admin_panel_title"),
        reply_markup=_admin_menu_keyboard(new_lang)
    )


async def handle_admin_menu_callback(client: Client, callback_query):
    """Handle admin menu callbacks"""
    data = callback_query.data
    
    if data == "admin_menu":
        lang = await _get_lang_from_callback(callback_query)
        await callback_query.edit_message_text(
            _t(lang, "admin_panel_title"),
            reply_markup=_admin_menu_keyboard(lang)
        )
        await callback_query.answer()
    elif data == "admin_stats":
        await handle_admin_stats(client, callback_query)
    elif data == "admin_list_pairs":
        await handle_list_pairs(client, callback_query)
    elif data == "admin_add_pair":
        await handle_add_pair(client, callback_query)
    elif data == "admin_remove_pair":
        await handle_remove_pair(client, callback_query)
    elif data == "admin_button_rules":
        await callback_query.answer()
        await handle_button_rules(client, callback_query)
    elif data == "admin_link_rules":
        await callback_query.answer()
        await handle_link_rules(client, callback_query)
    elif data == "admin_scrape_menu":
        await callback_query.answer()
        await handle_scrape_menu(client, callback_query)
    elif data.startswith("admin_scrape_pair:"):
        await callback_query.answer()
        try:
            pair_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        await handle_scrape_pair(client, callback_query, pair_id)
    elif data.startswith("admin_scrape_latest:"):
        await handle_scrape_latest(client, callback_query)
    elif data.startswith("admin_scrape_first:"):
        await handle_scrape_first(client, callback_query)
    elif data.startswith("admin_scrape_latest_choose:"):
        await handle_scrape_latest_choose(client, callback_query)
    elif data.startswith("admin_scrape_first_choose:"):
        await handle_scrape_first_choose(client, callback_query)
    elif data.startswith("admin_scrape_full_confirm:"):
        await handle_scrape_full_confirm(client, callback_query)
    elif data.startswith("admin_scrape_full:"):
        await handle_scrape_full(client, callback_query)
    elif data.startswith("admin_scrape_realtime_toggle:"):
        await handle_scrape_realtime_toggle(client, callback_query)
    elif data.startswith("admin_scrape_reset:"):
        await handle_scrape_reset(client, callback_query)
    elif data == "admin_language":
        await callback_query.answer()
        await handle_language_menu(client, callback_query)
    elif data.startswith("admin_set_lang:"):
        await callback_query.answer()
        lang_code = data.split(":", 1)[1].strip().lower()
        await handle_set_language(client, callback_query, lang_code)
    elif data == "admin_close":
        await callback_query.message.delete()
        await callback_query.answer()


# Command handlers
async def admin_command(client: Client, message: Message):
    """Admin command handler"""
    await show_admin_menu(client, message)


async def menu_command(client: Client, message: Message):
    """Menu command handler"""
    await show_admin_menu(client, message)


async def clear_db_command(client: Client, message: Message):
    include_rules = False
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1 and parts[1].strip().lower() == "all":
            include_rules = True
    except Exception:
        include_rules = False

    await db.clear_data(include_rules=include_rules)
    lang = await _get_lang_from_message(message)
    await message.reply_text(_t(lang, "cleardb_done_all" if include_rules else "cleardb_done"))


async def add_pair_command(client: Client, message: Message):
    """Add channel pair command"""
    lang = await _get_lang_from_message(message)
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.reply_text(_t(lang, "addpair_usage"))
            return
        
        donor_channel = parts[1].strip()
        target_channel = parts[2].strip()

        resolver_client = _user_client or client
        
        # Try to resolve channel IDs if usernames provided
        try:
            # If it's a username, try to get the chat
            if donor_channel.startswith('@'):
                try:
                    donor_chat = await _resolve_chat_for_admin(resolver_client, donor_channel)
                    # Store both username and ID for flexibility
                    donor_channel = f"@{donor_chat.username}" if donor_chat.username else str(donor_chat.id)
                except:
                    pass  # Keep original if can't resolve
            elif not donor_channel.startswith('-'):
                # Assume it's a username without @
                try:
                    donor_chat = await _resolve_chat_for_admin(resolver_client, donor_channel)
                    donor_channel = f"@{donor_chat.username}" if donor_chat.username else str(donor_chat.id)
                except:
                    donor_channel = f"@{donor_channel}"
            else:
                donor_channel = _normalize_chat_ref(donor_channel)
            
            if target_channel.startswith('@'):
                try:
                    target_chat = await _resolve_chat_for_admin(resolver_client, target_channel)
                    target_channel = f"@{target_chat.username}" if target_chat.username else str(target_chat.id)
                except:
                    pass
            elif not target_channel.startswith('-'):
                try:
                    target_chat = await _resolve_chat_for_admin(resolver_client, target_channel)
                    target_channel = f"@{target_chat.username}" if target_chat.username else str(target_chat.id)
                except:
                    target_channel = f"@{target_channel}"
            else:
                target_channel = _normalize_chat_ref(target_channel)
        except Exception as e:
            await message.reply_text(_t(lang, "addpair_resolve_warn").format(error=str(e)))
        
        pair_id = await db.add_channel_pair(donor_channel, target_channel)
        await message.reply_text(
            _t(lang, "addpair_success").format(
                pair_id=pair_id,
                donor=donor_channel,
                target=target_channel,
            )
        )
    except Exception as e:
        await message.reply_text(_t(lang, "generic_error").format(error=str(e)))


async def add_button_rule_one_command(client: Client, message: Message):
    lang = await _get_lang_from_message(message)
    try:
        payload = message.text.split(maxsplit=1)
        if len(payload) < 2:
            await message.reply_text(_t(lang, "addbtn1_usage"))
            return
        raw = payload[1].strip()
        parts = [p.strip() for p in raw.split('|')]
        if len(parts) != 2:
            await message.reply_text(_t(lang, "button_rule_invalid"))
            return

        await db.clear_button_rules()
        await db.add_button_rule('one', '', parts[0], parts[1])
        await message.reply_text(_t(lang, "button_rule_added"))
    except Exception as e:
        await message.reply_text(_t(lang, "generic_error").format(error=str(e)))


async def add_button_rule_two_command(client: Client, message: Message):
    lang = await _get_lang_from_message(message)
    try:
        payload = message.text.split(maxsplit=1)
        if len(payload) < 2:
            await message.reply_text(_t(lang, "addbtn2_usage"))
            return
        raw = payload[1].strip()
        groups = [g.strip() for g in raw.split('||')]
        if len(groups) != 2:
            await message.reply_text(_t(lang, "button_rule_invalid"))
            return

        p1 = [p.strip() for p in groups[0].split('|')]
        p2 = [p.strip() for p in groups[1].split('|')]
        if len(p1) != 2 or len(p2) != 2:
            await message.reply_text(_t(lang, "button_rule_invalid"))
            return

        await db.clear_button_rules()
        await db.add_button_rule('two', '', p1[0], p1[1], '', p2[0], p2[1])
        await message.reply_text(_t(lang, "button_rule_added"))
    except Exception as e:
        await message.reply_text(_t(lang, "generic_error").format(error=str(e)))


async def remove_button_rule_command(client: Client, message: Message):
    lang = await _get_lang_from_message(message)
    try:
        await db.clear_button_rules()
        await message.reply_text(_t(lang, "button_rule_removed"))
    except Exception as e:
        await message.reply_text(_t(lang, "generic_error").format(error=str(e)))


async def remove_pair_command(client: Client, message: Message):
    """Remove channel pair command"""
    lang = await _get_lang_from_message(message)
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply_text(_t(lang, "remove_usage"))
            return
        
        pair_id = int(parts[1])
        removed_donor = await db.remove_channel_pair(pair_id)
        if removed_donor:
            clear_memory_cache(removed_donor)
        await message.reply_text(_t(lang, "remove_success").format(pair_id=pair_id))
    except ValueError:
        await message.reply_text(_t(lang, "remove_invalid"))
    except Exception as e:
        await message.reply_text(_t(lang, "generic_error").format(error=str(e)))


async def add_rule_command(client: Client, message: Message):
    """Add link replacement rule"""
    lang = await _get_lang_from_message(message)
    try:
        # Parse command: /addrule pattern [replacement]
        text = message.text
        parts = text.split(maxsplit=2)
        if len(parts) < 2:
            await message.reply_text(_t(lang, "addrule_usage"))
            return
        pattern = parts[1]
        replacement = parts[2] if len(parts) > 2 else ""
        if not pattern:
            await message.reply_text(_t(lang, "addrule_required"))
            return
        
        rule_id = await db.add_link_rule(pattern, replacement)
        await message.reply_text(
            _t(lang, "addrule_success").format(
                rule_id=rule_id,
                pattern=pattern[:100],
                replacement=(replacement[:100] if replacement else ("⛔ (пусто/удаление)" if lang == "ru" else "⛔ (empty/remove)")),
            )
        )
    except Exception as e:
        await message.reply_text(_t(lang, "generic_error").format(error=str(e)))


async def remove_rule_command(client: Client, message: Message):
    """Remove link replacement rule"""
    lang = await _get_lang_from_message(message)
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply_text(_t(lang, "removerule_usage"))
            return
        
        rule_id = int(parts[1])
        await db.remove_link_rule(rule_id)
        await message.reply_text(_t(lang, "removerule_success").format(rule_id=rule_id))
    except ValueError:
        await message.reply_text(_t(lang, "removerule_invalid"))
    except Exception as e:
        await message.reply_text(_t(lang, "generic_error").format(error=str(e)))


async def remove_rule_by_pattern_command(client: Client, message: Message):
    """Remove link replacement rules by pattern"""
    lang = await _get_lang_from_message(message)
    try:
        payload = message.text.split(maxsplit=1)
        if len(payload) < 2 or not payload[1].strip():
            # Reuse usage but adapt text inline for pattern removal
            usage = _t(lang, "removerule_usage") + "\n\nПример удаления по шаблону:\n`/removerulepat Париматч`\n`/removerulepat regex:(parimatch|париматч)\\d*`"
            await message.reply_text(usage)
            return
        pattern = payload[1].strip()
        await db.remove_link_rule_by_pattern(pattern)
        await message.reply_text(f"✅ Удалены правила с шаблоном: `{pattern}`")
    except Exception as e:
        await message.reply_text(_t(lang, "generic_error").format(error=str(e)))


async def handle_forwarded_message(client: Client, message: Message):
    """Handle forwarded messages to resolve chat ID"""
    if message.forward_from_chat:
        chat = message.forward_from_chat
        info = f"**📢 Channel Info**\n\n"
        info += f"**Title:** {chat.title}\n"
        info += f"**ID:** `{chat.id}`\n"
        if chat.username:
            info += f"**Username:** @{chat.username}\n"
        
        await message.reply_text(info)
    elif message.forward_from:
        user = message.forward_from
        info = f"**👤 User Info**\n\n"
        info += f"**Name:** {user.first_name} {user.last_name or ''}\n"
        info += f"**ID:** `{user.id}`\n"
        if user.username:
            info += f"**Username:** @{user.username}\n"
        
        await message.reply_text(info)


# Setup callback query handler
def setup_admin_handlers(client: Client):
    """Setup admin menu handlers"""
    from pyrogram.handlers import CallbackQueryHandler, MessageHandler
    
    # Setup callback query handler
    client.add_handler(CallbackQueryHandler(
        handle_admin_menu_callback,
        filters.create(lambda _, __, query: query.data.startswith("admin_"))
    ))
    
    # Setup command handlers
    admin_filter = filters.command("admin") & filters.user(ADMIN_ID)
    menu_filter = (filters.command(["start", "menu"]) & filters.user(ADMIN_ID))
    cleardb_filter = filters.command("cleardb") & filters.user(ADMIN_ID)
    addpair_filter = filters.command("addpair") & filters.user(ADMIN_ID)
    removepair_filter = filters.command("removepair") & filters.user(ADMIN_ID)
    addrule_filter = filters.command("addrule") & filters.user(ADMIN_ID)
    removerule_filter = filters.command("removerule") & filters.user(ADMIN_ID)
    removerulepat_filter = filters.command("removerulepat") & filters.user(ADMIN_ID)
    addbtn1_filter = filters.command("addbtn1") & filters.user(ADMIN_ID)
    addbtn2_filter = filters.command("addbtn2") & filters.user(ADMIN_ID)
    removebtn_filter = filters.command("removebtn") & filters.user(ADMIN_ID)
    
    # Setup ID resolver
    id_resolver_filter = filters.forwarded & filters.user(ADMIN_ID)
    client.add_handler(MessageHandler(handle_forwarded_message, id_resolver_filter))
    
    client.add_handler(MessageHandler(admin_command, admin_filter))
    client.add_handler(MessageHandler(menu_command, menu_filter))
    client.add_handler(MessageHandler(clear_db_command, cleardb_filter))
    client.add_handler(MessageHandler(add_pair_command, addpair_filter))
    client.add_handler(MessageHandler(remove_pair_command, removepair_filter))
    client.add_handler(MessageHandler(add_rule_command, addrule_filter))
    client.add_handler(MessageHandler(remove_rule_command, removerule_filter))
    client.add_handler(MessageHandler(remove_rule_by_pattern_command, removerulepat_filter))
    client.add_handler(MessageHandler(add_button_rule_one_command, addbtn1_filter))
    client.add_handler(MessageHandler(add_button_rule_two_command, addbtn2_filter))
    client.add_handler(MessageHandler(remove_button_rule_command, removebtn_filter))
