from pyrogram import Client
from pyrogram.types import Message
from database import db
from utils.media_handler import clone_message, clone_media_group, download_and_clone_message
import asyncio
import os


# Track last processed message IDs per channel
last_message_ids = {}


async def monitor_channel(client: Client, donor_channel: str, target_channel: str, pair_id: int):
    """Monitor a donor channel and clone new messages"""
    try:
        # Get channel chat
        try:
            if donor_channel.startswith('@'):
                chat = await client.get_chat(donor_channel)
            else:
                chat = await client.get_chat(int(donor_channel))
        except Exception as e:
            print(f"Error getting chat {donor_channel}: {str(e)}")
            return
        
        channel_id = f"@{chat.username}" if chat.username else str(chat.id)
        
        # Get last processed message ID
        last_id = last_message_ids.get(channel_id, 0)
        
        # Get recent messages (limit 10 for efficiency)
        messages_list = []
        try:
            async for message in client.get_chat_history(chat.id, limit=10):
                # Skip if already processed
                if await db.is_message_processed(channel_id, message.id):
                    continue
                
                # Skip if older than last processed
                if message.id <= last_id:
                    continue
                
                messages_list.append(message)
                last_message_ids[channel_id] = max(last_message_ids.get(channel_id, 0), message.id)
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
                if await db.is_message_processed(channel_id, message.id):
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
                            if not await db.is_message_processed(channel_id, msg.id):
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
                        await db.mark_message_processed(channel_id, msg.id)
                else:
                    # Regular message
                    await download_and_clone_message(
                        client,
                        message,
                        target_channel,
                        pair_id
                    )
                    await db.mark_message_processed(channel_id, message.id)
                    
            except Exception as e:
                print(f"Error processing message {message.id} from {donor_channel}: {str(e)}")
                continue
    
    except Exception as e:
        print(f"Error monitoring channel {donor_channel}: {str(e)}")


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
            reply_markup
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
