from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import ADMIN_ID
import re


async def show_admin_menu(client: Client, message: Message):
    """Show main admin menu"""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
            InlineKeyboardButton("➕ Add Channel Pair", callback_data="admin_add_pair")
        ],
        [
            InlineKeyboardButton("➖ Remove Channel Pair", callback_data="admin_remove_pair"),
            InlineKeyboardButton("🔗 Link Rules", callback_data="admin_link_rules")
        ],
        [
            InlineKeyboardButton("📋 List Pairs", callback_data="admin_list_pairs"),
            InlineKeyboardButton("❌ Close", callback_data="admin_close")
        ]
    ])
    
    await message.reply_text(
        "**🤖 Admin Panel**\n\n"
        "Select an option:",
        reply_markup=keyboard
    )


async def handle_admin_stats(client: Client, callback_query):
    """Show statistics"""
    stats = await db.get_statistics()
    
    if not stats:
        await callback_query.answer("No channel pairs configured.", show_alert=True)
        return
    
    text = "**📊 Statistics**\n\n"
    total_posts = 0
    
    for stat in stats:
        text += f"**Pair ID:** {stat['id']}\n"
        text += f"**Donor:** `{stat['donor_channel']}`\n"
        text += f"**Target:** `{stat['target_channel']}`\n"
        text += f"**Posts Cloned:** {stat['posts_cloned']}\n"
        if stat['last_cloned_at']:
            text += f"**Last Cloned:** {stat['last_cloned_at']}\n"
        text += "\n"
        total_posts += stat['posts_cloned']
    
    text += f"**Total Posts Cloned:** {total_posts}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="admin_menu")]
    ])
    
    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_list_pairs(client: Client, callback_query):
    """List all channel pairs"""
    pairs = await db.get_statistics()
    
    if not pairs:
        await callback_query.answer("No channel pairs configured.", show_alert=True)
        return
    
    text = "**📋 Channel Pairs**\n\n"
    for pair in pairs:
        text += f"**ID:** {pair['id']}\n"
        text += f"**Donor:** `{pair['donor_channel']}`\n"
        text += f"**Target:** `{pair['target_channel']}`\n"
        text += f"**Posts:** {pair['posts_cloned']}\n\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="admin_menu")]
    ])
    
    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_add_pair(client: Client, callback_query):
    """Prompt for adding channel pair"""
    await callback_query.answer()
    
    text = (
        "**➕ Add Channel Pair**\n\n"
        "Please send the channel pair in the following format:\n"
        "`/addpair donor_channel target_channel`\n\n"
        "Example:\n"
        "`/addpair @donorchannel @targetchannel`\n\n"
        "Or use channel IDs:\n"
        "`/addpair -1001234567890 -1009876543210`"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="admin_menu")]
    ])
    
    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_remove_pair(client: Client, callback_query):
    """Prompt for removing channel pair"""
    pairs = await db.get_statistics()
    
    if not pairs:
        await callback_query.answer("No channel pairs to remove.", show_alert=True)
        return
    
    text = "**➖ Remove Channel Pair**\n\n"
    text += "Send the pair ID to remove:\n"
    text += "`/removepair <pair_id>`\n\n"
    text += "Available pairs:\n"
    for pair in pairs:
        text += f"**{pair['id']}:** `{pair['donor_channel']}` → `{pair['target_channel']}`\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="admin_menu")]
    ])
    
    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_link_rules(client: Client, callback_query):
    """Show link rules menu"""
    rules = await db.get_all_link_rules()
    
    text = "**🔗 Link Replacement Rules**\n\n"
    
    if rules:
        for rule in rules:
            text += f"**ID {rule['id']}:**\n"
            text += f"Pattern: `{rule['pattern'][:50]}...`\n"
            text += f"Replacement: `{rule['replacement'][:50]}...`\n\n"
    else:
        text += "No rules configured.\n\n"
    
    text += "**Commands:**\n"
    text += "`/addrule <pattern> <replacement>`\n"
    text += "`/removerule <rule_id>`\n\n"
    text += "For regex patterns, prefix with `regex:`"
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_menu")
        ]
    ])
    
    await callback_query.edit_message_text(text, reply_markup=keyboard)


async def handle_admin_menu_callback(client: Client, callback_query):
    """Handle admin menu callbacks"""
    data = callback_query.data
    
    if data == "admin_menu":
        await show_admin_menu(client, callback_query.message)
        await callback_query.answer()
    elif data == "admin_stats":
        await handle_admin_stats(client, callback_query)
    elif data == "admin_list_pairs":
        await handle_list_pairs(client, callback_query)
    elif data == "admin_add_pair":
        await handle_add_pair(client, callback_query)
    elif data == "admin_remove_pair":
        await handle_remove_pair(client, callback_query)
    elif data == "admin_link_rules":
        await handle_link_rules(client, callback_query)
    elif data == "admin_close":
        await callback_query.message.delete()
        await callback_query.answer()


# Command handlers
async def admin_command(client: Client, message: Message):
    """Admin command handler"""
    await show_admin_menu(client, message)


async def add_pair_command(client: Client, message: Message):
    """Add channel pair command"""
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.reply_text(
                "**Использование:** `/addpair donor_channel target_channel`\n\n"
                "**Примеры:**\n"
                "`/addpair @testchannel @targetchannel`\n"
                "`/addpair -1001234567890 -1009876543210`\n\n"
                "💡 **Для каналов без username используйте ID канала**\n"
                "Получить ID можно через @userinfobot или @getidsbot"
            )
            return
        
        donor_channel = parts[1].strip()
        target_channel = parts[2].strip()
        
        # Try to resolve channel IDs if usernames provided
        try:
            # If it's a username, try to get the chat
            if donor_channel.startswith('@'):
                try:
                    donor_chat = await client.get_chat(donor_channel)
                    # Store both username and ID for flexibility
                    donor_channel = f"@{donor_chat.username}" if donor_chat.username else str(donor_chat.id)
                except:
                    pass  # Keep original if can't resolve
            elif not donor_channel.startswith('-'):
                # Assume it's a username without @
                try:
                    donor_chat = await client.get_chat(f"@{donor_channel}")
                    donor_channel = f"@{donor_chat.username}" if donor_chat.username else str(donor_chat.id)
                except:
                    donor_channel = f"@{donor_channel}"
            
            if target_channel.startswith('@'):
                try:
                    target_chat = await client.get_chat(target_channel)
                    target_channel = f"@{target_chat.username}" if target_chat.username else str(target_chat.id)
                except:
                    pass
            elif not target_channel.startswith('-'):
                try:
                    target_chat = await client.get_chat(f"@{target_channel}")
                    target_channel = f"@{target_chat.username}" if target_chat.username else str(target_chat.id)
                except:
                    target_channel = f"@{target_channel}"
        except Exception as e:
            await message.reply_text(f"⚠️ Не удалось проверить каналы: {str(e)}\nПродолжаю с указанными значениями...")
        
        pair_id = await db.add_channel_pair(donor_channel, target_channel)
        await message.reply_text(
            f"✅ **Пара каналов успешно добавлена!**\n\n"
            f"**ID пары:** {pair_id}\n"
            f"**Донор:** `{donor_channel}`\n"
            f"**Целевой:** `{target_channel}`\n\n"
            f"⚠️ **Важно:** Убедитесь, что бот добавлен как администратор в оба канала!"
        )
    except Exception as e:
        await message.reply_text(f"❌ Ошибка: {str(e)}")


async def remove_pair_command(client: Client, message: Message):
    """Remove channel pair command"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply_text("**Usage:** `/removepair <pair_id>`")
            return
        
        pair_id = int(parts[1])
        await db.remove_channel_pair(pair_id)
        await message.reply_text(f"✅ Channel pair {pair_id} removed successfully!")
    except ValueError:
        await message.reply_text("❌ Invalid pair ID. Please provide a number.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


async def add_rule_command(client: Client, message: Message):
    """Add link replacement rule"""
    try:
        # Parse command: /addrule pattern replacement
        # Handle patterns and replacements that may contain spaces
        text = message.text
        if not text or len(text.split()) < 3:
            await message.reply_text(
                "**Usage:** `/addrule <pattern> <replacement>`\n\n"
                "Example: `/addrule https://example.com https://myaffiliate.com`\n"
                "For regex: `/addrule regex:example\\.com myaffiliate.com`"
            )
            return
        
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            parts = text.split()
        
        pattern = parts[1] if len(parts) > 1 else ""
        replacement = parts[2] if len(parts) > 2 else ""
        
        if not pattern or not replacement:
            await message.reply_text("❌ Pattern and replacement are required.")
            return
        
        rule_id = await db.add_link_rule(pattern, replacement)
        await message.reply_text(
            f"✅ Link rule added successfully!\n\n"
            f"**Rule ID:** {rule_id}\n"
            f"**Pattern:** `{pattern[:100]}`\n"
            f"**Replacement:** `{replacement[:100]}`"
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


async def remove_rule_command(client: Client, message: Message):
    """Remove link replacement rule"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply_text("**Usage:** `/removerule <rule_id>`")
            return
        
        rule_id = int(parts[1])
        await db.remove_link_rule(rule_id)
        await message.reply_text(f"✅ Link rule {rule_id} removed successfully!")
    except ValueError:
        await message.reply_text("❌ Invalid rule ID. Please provide a number.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


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
    addpair_filter = filters.command("addpair") & filters.user(ADMIN_ID)
    removepair_filter = filters.command("removepair") & filters.user(ADMIN_ID)
    addrule_filter = filters.command("addrule") & filters.user(ADMIN_ID)
    removerule_filter = filters.command("removerule") & filters.user(ADMIN_ID)
    
    client.add_handler(MessageHandler(admin_command, admin_filter))
    client.add_handler(MessageHandler(add_pair_command, addpair_filter))
    client.add_handler(MessageHandler(remove_pair_command, removepair_filter))
    client.add_handler(MessageHandler(add_rule_command, addrule_filter))
    client.add_handler(MessageHandler(remove_rule_command, removerule_filter))
