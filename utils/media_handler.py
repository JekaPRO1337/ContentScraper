from typing import List, Optional
from pyrogram import Client
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio
from utils.button_replacer import replace_markup
from config import FLOODWAIT_RETRY_DELAY, MAX_FLOODWAIT_RETRIES
import asyncio


async def send_message_with_retry(client: Client, chat_id, **kwargs):
    """Send a message with FloodWait retry logic"""
    retries = 0
    while retries < MAX_FLOODWAIT_RETRIES:
        try:
            return await client.send_message(chat_id=chat_id, **kwargs)
        except Exception as e:
            error_msg = str(e)
            if "FLOOD_WAIT" in error_msg or "flood" in error_msg.lower():
                # Extract wait time if available
                wait_time = FLOODWAIT_RETRY_DELAY
                try:
                    # Try to extract wait time from error message
                    import re
                    match = re.search(r'(\d+)', error_msg)
                    if match:
                        wait_time = min(int(match.group(1)) + 1, 60)  # Cap at 60 seconds
                except:
                    pass
                
                retries += 1
                if retries < MAX_FLOODWAIT_RETRIES:
                    await asyncio.sleep(wait_time)
                    continue
            raise


async def download_and_clone_message(client: Client, message: Message, target_channel: str, pair_id: int):
    """Download media and clone message to target channel (for closed channels)"""
    from database import db
    import os
    
    # Replace markup if exists
    reply_markup = None
    if message.reply_markup:
        reply_markup = await replace_markup(message.reply_markup)
    
    # Handle media groups (albums) - should be handled separately
    if message.media_group_id:
        return None
    
    file_path = None
    try:
        # Download media if present (for closed channels)
        if message.photo or message.video or message.document or message.audio or message.voice:
            file_path = await client.download_media(message)
        
        # Handle different media types using downloaded file or file_id
        if message.photo:
            await send_message_with_retry(
                client,
                chat_id=target_channel,
                photo=file_path if file_path else message.photo.file_id,
                caption=message.caption,
                caption_entities=message.caption_entities,
                reply_markup=reply_markup
            )
        elif message.video:
            await send_message_with_retry(
                client,
                chat_id=target_channel,
                video=file_path if file_path else message.video.file_id,
                caption=message.caption,
                caption_entities=message.caption_entities,
                reply_markup=reply_markup
            )
        elif message.document:
            await send_message_with_retry(
                client,
                chat_id=target_channel,
                document=file_path if file_path else message.document.file_id,
                caption=message.caption,
                caption_entities=message.caption_entities,
                reply_markup=reply_markup
            )
        elif message.audio:
            await send_message_with_retry(
                client,
                chat_id=target_channel,
                audio=file_path if file_path else message.audio.file_id,
                caption=message.caption,
                caption_entities=message.caption_entities,
                reply_markup=reply_markup
            )
        elif message.voice:
            await send_message_with_retry(
                client,
                chat_id=target_channel,
                voice=file_path if file_path else message.voice.file_id,
                caption=message.caption,
                caption_entities=message.caption_entities,
                reply_markup=reply_markup
            )
        elif message.video_note:
            await send_message_with_retry(
                client,
                chat_id=target_channel,
                video_note=message.video_note.file_id,
                reply_markup=reply_markup
            )
        elif message.sticker:
            await send_message_with_retry(
                client,
                chat_id=target_channel,
                sticker=message.sticker.file_id,
                reply_markup=reply_markup
            )
        elif message.text or message.caption:
            # Text message
            await send_message_with_retry(
                client,
                chat_id=target_channel,
                text=message.text or message.caption,
                entities=message.entities or message.caption_entities,
                reply_markup=reply_markup
            )
        else:
            # Fallback: try to copy the message
            await send_message_with_retry(
                client,
                chat_id=target_channel,
                text="[Unsupported message type]",
                reply_markup=reply_markup
            )
        
        # Update statistics
        await db.increment_statistics(pair_id)
        
    except Exception as e:
        print(f"Error cloning message {message.id}: {str(e)}")
        raise
    finally:
        # Cleanup downloaded file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass


async def clone_message(client: Client, message: Message, target_channel: str, pair_id: int):
    """Clone a message to target channel with button replacement (legacy, uses file_id)"""
    # For compatibility, redirect to download_and_clone_message
    # but try file_id first for open channels
    return await download_and_clone_message(client, message, target_channel, pair_id)


async def clone_media_group(
    client: Client,
    messages_data: List,
    target_channel: str,
    pair_id: int,
    caption: str = None,
    caption_entities = None,
    reply_markup = None
):
    """Clone a media group (album) to target channel using downloaded files"""
    from database import db
    
    if not messages_data:
        return
    
    # Prepare media array
    media = []
    
    # Build media array - set caption on first item
    for i, item in enumerate(messages_data):
        msg = item.get('message') if isinstance(item, dict) else item
        file_path = item.get('file_path') if isinstance(item, dict) else None
        
        is_first = i == 0
        current_caption = caption if is_first and caption else None
        current_caption_entities = caption_entities if is_first and caption_entities else None
        
        # Use downloaded file if available, otherwise use file_id
        if msg.photo:
            media.append(InputMediaPhoto(
                file_path if file_path else msg.photo.file_id,
                caption=current_caption,
                caption_entities=current_caption_entities
            ))
        elif msg.video:
            media.append(InputMediaVideo(
                file_path if file_path else msg.video.file_id,
                caption=current_caption,
                caption_entities=current_caption_entities
            ))
        elif msg.document:
            media.append(InputMediaDocument(
                file_path if file_path else msg.document.file_id,
                caption=current_caption,
                caption_entities=current_caption_entities
            ))
        elif msg.audio:
            media.append(InputMediaAudio(
                file_path if file_path else msg.audio.file_id,
                caption=current_caption,
                caption_entities=current_caption_entities
            ))
    
    if media:
        try:
            # Use send_media_group for albums
            retries = 0
            while retries < MAX_FLOODWAIT_RETRIES:
                try:
                    # Send media group
                    result = await client.send_media_group(
                        chat_id=target_channel,
                        media=media
                    )
                    # Edit first message to add reply_markup if needed
                    if result and reply_markup:
                        await client.edit_message_reply_markup(
                            chat_id=target_channel,
                            message_id=result[0].id,
                            reply_markup=reply_markup
                        )
                    break
                except Exception as e:
                    error_msg = str(e)
                    if "FLOOD_WAIT" in error_msg or "flood" in error_msg.lower():
                        wait_time = FLOODWAIT_RETRY_DELAY
                        try:
                            import re
                            match = re.search(r'(\d+)', error_msg)
                            if match:
                                wait_time = min(int(match.group(1)) + 1, 60)
                        except:
                            pass
                        retries += 1
                        if retries < MAX_FLOODWAIT_RETRIES:
                            await asyncio.sleep(wait_time)
                            continue
                    raise
            # Update statistics
            await db.increment_statistics(pair_id)
        except Exception as e:
            print(f"Error cloning media group: {str(e)}")
            raise
