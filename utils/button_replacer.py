from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
import re


async def replace_markup(markup: InlineKeyboardMarkup | None) -> InlineKeyboardMarkup | None:
    """
    Build buttons based on global button rules.
    If custom_buttons_mode is enabled, the original donor buttons are completely ignored
    and replaced with our custom buttons.
    Otherwise, we only replace donor buttons IF they existed.
    Supports up to 3 buttons.
    """
    rules = await db.get_all_button_rules()
    if not rules:
        return markup

    rule = rules[0]
    # custom_mode = bool(rule.get("custom_buttons_mode", 0)) # We ignore this toggle now as per user request
    mode = (rule.get("mode") or "one").lower()

    # If rules exist, we proceed. We no longer check if donor had buttons.

    buttons = []
    
    # Button 1
    text1 = (rule.get("text1") or "").strip()
    url1 = (rule.get("url1") or "").strip()
    if text1 and url1:
        buttons.append(InlineKeyboardButton(text1, url=url1))

    # Button 2
    if mode in ["two", "three"]:
        text2 = (rule.get("text2") or "").strip()
        url2 = (rule.get("url2") or "").strip()
        if text2 and url2:
            buttons.append(InlineKeyboardButton(text2, url=url2))

    # Button 3
    if mode == "three":
        text3 = (rule.get("text3") or "").strip()
        url3 = (rule.get("url3") or "").strip()
        if text3 and url3:
            buttons.append(InlineKeyboardButton(text3, url=url3))

    if not buttons:
        # If no buttons configured, return original markup
        return markup

    # Return as a single row of buttons
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
