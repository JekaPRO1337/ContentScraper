from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
import re


async def replace_markup(markup: InlineKeyboardMarkup) -> InlineKeyboardMarkup | None:
    """
    Build buttons based on global button rules.
    If rules are configured, original buttons are ignored and replaced with one row
    containing 1 or 2 buttons from the config.
    If no rules are configured, the original markup is returned.
    """
    if not markup or not markup.inline_keyboard:
        return None

    rules = await db.get_all_button_rules()
    if not rules:
        return markup

    rule = rules[0]
    mode = (rule.get("mode") or "").lower()

    buttons = []

    text1 = (rule.get("text1") or "").strip()
    url1 = (rule.get("url1") or "").strip()
    if text1 and url1:
        buttons.append(InlineKeyboardButton(text1, url=url1))

    if mode == "two":
        text2 = (rule.get("text2") or "").strip()
        url2 = (rule.get("url2") or "").strip()
        if text2 and url2:
            buttons.append(InlineKeyboardButton(text2, url=url2))

    if not buttons:
        return None

    return InlineKeyboardMarkup([buttons])


def _is_match(pattern: str, text: str) -> bool:
    if not text:
        return False

    if pattern.startswith("regex:"):
        try:
            return bool(re.search(pattern[6:], text, re.IGNORECASE))
        except:
            return False

    return pattern.lower() in text.lower()
