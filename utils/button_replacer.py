import re
from typing import List, Dict
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import db


async def replace_url_in_button(button: InlineKeyboardButton) -> InlineKeyboardButton:
    """Replace URL in a single button based on rules"""
    if not button.url:
        return button
    
    original_url = button.url
    new_url = original_url
    
    # Get all link replacement rules
    rules = await db.get_all_link_rules()
    
    # Apply rules (first match wins)
    for rule in rules:
        pattern = rule['pattern']
        replacement = rule['replacement']
        
        # Simple string replacement
        if pattern in original_url:
            new_url = original_url.replace(pattern, replacement)
            break
        # Regex replacement
        elif pattern.startswith('regex:'):
            regex_pattern = pattern[6:]  # Remove 'regex:' prefix
            try:
                new_url = re.sub(regex_pattern, replacement, original_url)
                if new_url != original_url:
                    break
            except re.error:
                continue
    
    # Create new button with replaced URL or same button if no replacement
    if new_url != original_url:
        return InlineKeyboardButton(
            text=button.text,
            url=new_url,
            callback_data=button.callback_data,
            web_app=button.web_app,
            login_url=button.login_url,
            switch_inline_query=button.switch_inline_query,
            switch_inline_query_current_chat=button.switch_inline_query_current_chat,
            callback_game=button.callback_game,
            pay=button.pay
        )
    
    return button


async def replace_markup(markup: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    """Replace URLs in all buttons of a markup"""
    if not markup or not markup.inline_keyboard:
        return markup
    
    new_keyboard = []
    for row in markup.inline_keyboard:
        new_row = []
        for button in row:
            new_button = await replace_url_in_button(button)
            new_row.append(new_button)
        new_keyboard.append(new_row)
    
    return InlineKeyboardMarkup(new_keyboard) if new_keyboard else None
