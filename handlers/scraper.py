from pyrogram import Client
from pyrogram.types import Message
from database import db
from utils.media_handler import clone_message, clone_media_group, download_and_clone_message
import asyncio
import os


_client_is_bot_cache = {}

_sender_client: Client | None = None


def set_sender_client(client: Client | None):
    global _sender_client
    _sender_client = client


async def _is_bot_client(client: Client) -> bool:
    key = id(client)
    if key in _client_is_bot_cache:
        return _client_is_bot_cache[key]
    try:
        me = await client.get_me()
        val = bool(getattr(me, "is_bot", False))
        _client_is_bot_cache[key] = val
        return val
    except Exception:
        return False


async def _resolve_chat(client: Client, donor_channel: str):
    try:
        if donor_channel.startswith('@'):
            return await client.get_chat(donor_channel)

        normalized = (
            str(donor_channel)
            .strip()
            .replace("−", "-")
            .replace("–", "-")
            .replace("—", "-")
        )
        chat_id = int(normalized)
        try:
            return await client.get_chat(chat_id)
        except Exception:
            if await _is_bot_client(client):
                raise
            async for dialog in client.get_dialogs(limit=2000):
                _ = dialog.chat.id
            return await client.get_chat(chat_id)
    except Exception:
        raise


# Track last processed message IDs per channel
last_message_ids = {}


def clear_memory_cache(channel_id: str):
    """Clear memory cache for a channel"""
    if channel_id in last_message_ids:
        del last_message_ids[channel_id]


async def monitor_channel(client: Client, donor_channel: str, target_channel: str, pair_id: int):
    """Monitor a donor channel and clone new messages"""
    try:
        # Get channel chat
        try:
            chat = await _resolve_chat(client, donor_channel)
        except Exception as e:
            if "BOT_METHOD_INVALID" in str(e):
                print(
                    f"Error getting chat {donor_channel}: {str(e)}. "
                    f"It looks like the scraper is running under a BOT account. "
                    f"Scraping must run under the USER session (content_cloner_user.session)."
                )
                return
            if "PEER_ID_INVALID" in str(e):
                print(
                    f"Error getting chat {donor_channel}: {str(e)}. "
                    f"Hint: If using ID, ensure the USER account has joined the channel. "
                    f"For private channels, you must be a member."
                )
                return
            print(
                f"Error getting chat {donor_channel}: {str(e)}. "
                f"Hint: make sure the USER account is member/admin of that channel and the ID is correct."
            )
            return
        
        # Use donor_channel from DB as the key for consistency
        channel_key = donor_channel
        
        # Get last processed message ID
        last_id = last_message_ids.get(channel_key, 0)
        
        # Get recent messages (limit 10 for efficiency)
        messages_list = []
        try:
            async for message in client.get_chat_history(chat.id, limit=10):
                # Skip if already processed
                if await db.is_message_processed(channel_key, message.id):
                    continue
                
                # Skip if older than last processed
                if message.id <= last_id:
                    continue
                
                messages_list.append(message)
                last_message_ids[channel_key] = max(last_message_ids.get(channel_key, 0), message.id)
        except Exception as e:
            print(f"Error getting chat history for {donor_channel}: {str(e)}")
            return
        
        if not messages_list:
            return
        
        # Reverse to process in chronological order
        messages_list.reverse()
        
        # Process messages
        for message in messages_list:
            try:
                # Check if already processed (double check)
                if await db.is_message_processed(channel_key, message.id):
                    continue

                if getattr(message, "service", False):
                    await db.mark_message_processed(channel_key, message.id)
                    continue
                
                # Handle media groups
                if message.media_group_id:
                    # Collect all messages in the group
                    group_messages = [message]
                    group_id = message.media_group_id
                    
                    # Wait a bit for all messages in group to arrive
                    await asyncio.sleep(1)
                    
                    # Try to get other messages in the group
                    async for msg in client.get_chat_history(chat.id, limit=20):
                        if msg.media_group_id == group_id and msg.id != message.id:
                            if not await db.is_message_processed(channel_key, msg.id):
                                group_messages.append(msg)
                    
                    # Sort by message ID
                    group_messages.sort(key=lambda x: x.id)
                    
                    # Clone media group
                    await download_and_clone_media_group(
                        client,
                        group_messages,
                        target_channel,
                        pair_id
                    )
                    
                    # Mark all as processed
                    for msg in group_messages:
                        await db.mark_message_processed(channel_key, msg.id)
                else:
                    # Regular message
                    await download_and_clone_message(
                        client,
                        message,
                        target_channel,
                        pair_id,
                        sender_client=_sender_client
                    )
                    await db.mark_message_processed(channel_key, message.id)
                    
            except Exception as e:
                # Specific error handling for PEER_ID_INVALID during processing
                if "PEER_ID_INVALID" in str(e):
                     print(f"Error cloning message {message.id}: PEER_ID_INVALID. Target: {target_channel}. Hint: Ensure the BOT is an admin in the target channel (or User is a member if using User mode).")
                else:
                    print(f"Error processing message {message.id} from {donor_channel}: {str(e)}")
                continue
    
    except Exception as e:
        print(f"Error monitoring channel {donor_channel}: {str(e)}")


async def scrape_latest_n_messages(client: Client, pair_id: int, limit: int):
    pair = await db.get_pair_by_id(pair_id)
    if not pair:
        return
    donor_channel = pair["donor_channel"]
    target_channel = pair["target_channel"]
    try:
        chat = await _resolve_chat(client, donor_channel)
    except Exception as e:
        print(f"Error getting chat {donor_channel} for latest scrape: {str(e)}")
        return

    channel_key = donor_channel
    messages_list = []
    try:
        async for message in client.get_chat_history(chat.id, limit=limit):
            if await db.is_message_processed(channel_key, message.id):
                continue
            messages_list.append(message)
    except Exception as e:
        print(f"Error getting chat history for {donor_channel} (latest): {str(e)}")
        return

    if not messages_list:
        return

    messages_list.reverse()

    for message in messages_list:
        try:
            if await db.is_message_processed(channel_key, message.id):
                continue

            if getattr(message, "service", False):
                await db.mark_message_processed(channel_key, message.id)
                continue

            if message.media_group_id:
                group_messages = [message]
                group_id = message.media_group_id
                await asyncio.sleep(1)
                async for msg in client.get_chat_history(chat.id, limit=20):
                    if msg.media_group_id == group_id and msg.id != message.id:
                        if not await db.is_message_processed(channel_key, msg.id):
                            group_messages.append(msg)
                group_messages.sort(key=lambda x: x.id)
                await download_and_clone_media_group(
                    client,
                    group_messages,
                    target_channel,
                    pair_id,
                )
                for msg in group_messages:
                    await db.mark_message_processed(channel_key, msg.id)
            else:
                await download_and_clone_message(
                    client,
                    message,
                    target_channel,
                    pair_id,
                    sender_client=_sender_client,
                )
                await db.mark_message_processed(channel_key, message.id)
        except Exception as e:
            if "PEER_ID_INVALID" in str(e):
                print(
                    f"Error cloning message {message.id}: PEER_ID_INVALID. Target: {target_channel}. Hint: Ensure the BOT is an admin in the target channel (or User is a member if using User mode)."
                )
            else:
                print(
                    f"Error processing message {message.id} from {donor_channel} (latest): {str(e)}"
                )
            continue


async def scrape_full_history(client: Client, pair_id: int):
    pair = await db.get_pair_by_id(pair_id)
    if not pair:
        return
    donor_channel = pair["donor_channel"]
    target_channel = pair["target_channel"]
    try:
        chat = await _resolve_chat(client, donor_channel)
    except Exception as e:
        print(f"Error getting chat {donor_channel} for full scrape: {str(e)}")
        return

    channel_key = donor_channel
    offset_id = 0

    while True:
        batch = []
        try:
            async for message in client.get_chat_history(
                chat.id, offset_id=offset_id, limit=100
            ):
                batch.append(message)
        except Exception as e:
            print(f"Error getting chat history for {donor_channel} (full): {str(e)}")
            return

        if not batch:
            break

        batch.sort(key=lambda x: x.id)

        for message in batch:
            try:
                if await db.is_message_processed(channel_key, message.id):
                    continue

                if getattr(message, "service", False):
                    await db.mark_message_processed(channel_key, message.id)
                    continue

                if message.media_group_id:
                    group_messages = [message]
                    group_id = message.media_group_id
                    await asyncio.sleep(1)
                    async for msg in client.get_chat_history(chat.id, limit=20):
                        if msg.media_group_id == group_id and msg.id != message.id:
                            if not await db.is_message_processed(channel_key, msg.id):
                                group_messages.append(msg)
                    group_messages.sort(key=lambda x: x.id)
                    await download_and_clone_media_group(
                        client,
                        group_messages,
                        target_channel,
                        pair_id,
                    )
                    for msg in group_messages:
                        await db.mark_message_processed(channel_key, msg.id)
                else:
                    await download_and_clone_message(
                        client,
                        message,
                        target_channel,
                        pair_id,
                        sender_client=_sender_client,
                    )
                    await db.mark_message_processed(channel_key, message.id)
            except Exception as e:
                if "PEER_ID_INVALID" in str(e):
                    print(
                        f"Error cloning message {message.id}: PEER_ID_INVALID. Target: {target_channel}. Hint: Ensure the BOT is an admin in the target channel (or User is a member if using User mode)."
                    )
                else:
                    print(
                        f"Error processing message {message.id} from {donor_channel} (full): {str(e)}"
                    )
                continue

        offset_id = batch[0].id


async def scrape_first_n_messages(client: Client, pair_id: int, limit: int):
    pair = await db.get_pair_by_id(pair_id)
    if not pair:
        return
    donor_channel = pair["donor_channel"]
    target_channel = pair["target_channel"]
    try:
        chat = await _resolve_chat(client, donor_channel)
    except Exception as e:
        print(f"Error getting chat {donor_channel} for first-n scrape: {str(e)}")
        return

    channel_key = donor_channel
    buffer = []
    offset_id = 0

    while True:
        batch = []
        try:
            async for message in client.get_chat_history(
                chat.id, offset_id=offset_id, limit=100
            ):
                batch.append(message)
        except Exception as e:
            print(f"Error getting chat history for {donor_channel} (first-n): {str(e)}")
            return

        if not batch:
            break

        for message in batch:
            if await db.is_message_processed(channel_key, message.id):
                continue
            if getattr(message, "service", False):
                await db.mark_message_processed(channel_key, message.id)
                continue
            if message.media_group_id:
                continue
            buffer.insert(0, message)
            if len(buffer) > limit:
                buffer.pop()

        offset_id = batch[-1].id

    if not buffer:
        return

    buffer.sort(key=lambda x: x.id)

    for message in buffer:
        try:
            if await db.is_message_processed(channel_key, message.id):
                continue

            await download_and_clone_message(
                client,
                message,
                target_channel,
                pair_id,
                sender_client=_sender_client,
            )
            await db.mark_message_processed(channel_key, message.id)
        except Exception as e:
            if "PEER_ID_INVALID" in str(e):
                print(
                    f"Error cloning message {message.id}: PEER_ID_INVALID. Target: {target_channel}. Hint: Ensure the BOT is an admin in the target channel (or User is a member if using User mode)."
                )
            else:
                print(
                    f"Error processing message {message.id} from {donor_channel} (first-n): {str(e)}"
                )
            continue


async def download_and_clone_media_group(
    client: Client,
    messages: list,
    target_channel: str,
    pair_id: int
):
    """Download and clone a media group"""
    from utils.media_handler import clone_media_group
    from utils.button_replacer import replace_markup
    
    # Download all media first
    downloaded_media = []
    caption = None
    caption_entities = None
    reply_markup = None
    
    for i, msg in enumerate(messages):
        # Download media if needed (for closed channels)
        file_path = None
        try:
            if msg.photo or msg.video or msg.document or msg.audio:
                file_path = await client.download_media(msg)
        except Exception as e:
            print(f"Warning: Could not download media for message {msg.id}: {str(e)}")
            # Continue with file_id if download fails
        
        # Get caption and markup from last message
        if i == len(messages) - 1:
            caption = msg.caption
            caption_entities = msg.caption_entities
            if msg.reply_markup:
                reply_markup = await replace_markup(msg.reply_markup)
        
        downloaded_media.append({
            'message': msg,
            'file_path': file_path
        })
    
    try:
        # Clone using downloaded files
        await clone_media_group(
            client,
            downloaded_media,
            target_channel,
            pair_id,
            caption,
            caption_entities,
            reply_markup,
            sender_client=_sender_client
        )
    finally:
        # Cleanup downloaded files
        for item in downloaded_media:
            if item.get('file_path') and os.path.exists(item['file_path']):
                try:
                    os.remove(item['file_path'])
                except:
                    pass


async def start_monitoring(client: Client):
    """Start monitoring all configured channel pairs"""
    while True:
        try:
            pairs = await db.get_all_pairs()
            if not pairs:
                await asyncio.sleep(30)  # Wait 30 seconds if no pairs
                continue
            
            # Monitor each pair
            tasks = []
            for pair in pairs:
                if not pair.get('realtime_enabled'):
                    continue
                task = monitor_channel(
                    client,
                    pair['donor_channel'],
                    pair['target_channel'],
                    pair['id']
                )
                tasks.append(task)
            
            # Run all monitoring tasks concurrently
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Wait before next check
            await asyncio.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"Error in monitoring loop: {str(e)}")
            await asyncio.sleep(10)


def setup_scraper_handler(client: Client):
    """Setup scraper - start monitoring task"""
    # Start monitoring in background
    asyncio.create_task(start_monitoring(client))
