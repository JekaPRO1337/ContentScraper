from typing import List, Optional
from pyrogram import Client
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio
from utils.button_replacer import replace_markup
from config import FLOODWAIT_RETRY_DELAY, MAX_FLOODWAIT_RETRIES
try:
    MAX_FLOODWAIT_RETRIES = int(MAX_FLOODWAIT_RETRIES)
    FLOODWAIT_RETRY_DELAY = int(FLOODWAIT_RETRY_DELAY)
except:
    MAX_FLOODWAIT_RETRIES = 5
    FLOODWAIT_RETRY_DELAY = 1
from database import db
import asyncio
import re
import os
import subprocess
import shutil

# Check for local ffmpeg
LOCAL_FFMPEG = os.path.join(os.getcwd(), 'ffmpeg.exe')
FFMPEG_CMD = LOCAL_FFMPEG if os.path.exists(LOCAL_FFMPEG) else 'ffmpeg'

def convert_video_note(input_path: str, output_path: str) -> bool:
    """
    Convert video to a 1:1 round video note format (384x384).
    Returns True if successful, False otherwise.
    """
    try:
        # 1. Probe for duration (limit to 59s) and dimensions if needed, 
        # but simpler to just force crop and scale.
        
        # Command explanation:
        # -vf "crop=min(iw\,ih):min(iw\,ih),scale=384:384" -> Crop to square, then resize to 384x384
        # -c:v libx264 -> H.264 video
        # -preset fast -> Fast encoding
        # -crf 26 -> Reasonable quality
        # -c:a copy -> Copy audio (no re-encode)
        # -t 59 -> Trim to 59 seconds max (video note limit is 1m)
        # -pix_fmt yuv420p -> Ensure compatibility
        
        cmd = [
            FFMPEG_CMD, '-y',
            '-i', input_path,
            '-vf', 'crop=min(iw,ih):min(iw,ih),scale=384:384',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '26',
            '-c:a', 'aac', # Re-encode audio to aac to be safe
            '-b:a', '64k',
            '-t', '59',
            '-pix_fmt', 'yuv420p',
            output_path
        ]
        
        # Suppress output unless debug
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"FFmpeg conversion error: {e}")
        return False



async def send_message_with_retry(client: Client, chat_id, **kwargs):
    """Send a message with FloodWait retry logic"""
    send_fn = client.send_message
    if 'photo' in kwargs:
        send_fn = client.send_photo
    elif 'video' in kwargs:
        send_fn = client.send_video
    elif 'document' in kwargs:
        send_fn = client.send_document
    elif 'audio' in kwargs:
        send_fn = client.send_audio
    elif 'voice' in kwargs:
        send_fn = client.send_voice
    elif 'sticker' in kwargs:
        send_fn = client.send_sticker
    elif 'video_note' in kwargs:
        send_fn = client.send_video_note

    retries = 0
    while retries < MAX_FLOODWAIT_RETRIES:
        try:
            return await send_fn(chat_id=chat_id, **kwargs)
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
            
            if "PEER_ID_INVALID" in error_msg and retries == 0:
                # Try to resolve peer and retry
                try:
                    await client.get_chat(chat_id)
                    retries += 1
                    continue
                except Exception as resolve_error:
                    print(f"Failed to resolve peer {chat_id}: {resolve_error}")

            raise


async def apply_link_rules_to_text(text: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not text:
        return text, None

    rules = await db.get_all_link_rules()
    if not rules:
        return text, None

    result = text
    use_markdown = False

    for rule in rules:
        pattern = (rule.get("pattern") or "").strip()
        replacement = rule.get("replacement") or ""
        if not pattern:
            continue

        if pattern.startswith("regex:"):
            try:
                regex = re.compile(pattern[6:], re.IGNORECASE)
            except Exception:
                continue
            if not regex.search(result):
                continue
            result = regex.sub(replacement, result)
        else:
            if pattern.lower() not in result.lower():
                continue
            try:
                result = re.sub(
                    re.escape(pattern),
                    replacement,
                    result,
                    flags=re.IGNORECASE,
                )
            except Exception:
                continue

        if "[" in replacement and "](" in replacement:
            use_markdown = True

    return result, ("markdown" if use_markdown else None)


async def download_and_clone_message(
    client: Client,
    message: Message,
    target_channel: str,
    pair_id: int,
    sender_client: Client | None = None,
):
    """Download media and clone message to target channel (for closed channels)"""
    import os

    sender = sender_client or client
    
    # Replace markup if exists
    reply_markup = None
    if message.reply_markup:
        reply_markup = await replace_markup(message.reply_markup)
    
    if message.media_group_id:
        return None
    
    if getattr(message, "service", False):
        return

    has_supported_type = bool(
        message.photo
        or message.video
        or message.document
        or message.audio
        or message.voice
        or message.video_note
        or message.sticker
        or message.text
        or message.caption
    )
    if not has_supported_type:
        return

    caption = message.caption
    caption_entities = message.caption_entities
    text_body = message.text
    text_entities = message.entities

    caption, caption_parse_mode = await apply_link_rules_to_text(caption)
    if caption_parse_mode:
        caption_entities = None

    text_body, text_parse_mode = await apply_link_rules_to_text(text_body)
    if text_parse_mode:
        text_entities = None

    file_path = None
    try:
        if message.photo or message.video or message.document or message.audio or message.voice:
            file_path = await client.download_media(message)
        
        if message.photo:
            await send_message_with_retry(
                sender,
                chat_id=target_channel,
                photo=file_path if file_path else message.photo.file_id,
                caption=caption,
                caption_entities=caption_entities,
                parse_mode=caption_parse_mode,
                reply_markup=reply_markup
            )
        elif message.video:
            await send_message_with_retry(
                sender,
                chat_id=target_channel,
                video=file_path if file_path else message.video.file_id,
                caption=caption,
                caption_entities=caption_entities,
                parse_mode=caption_parse_mode,
                reply_markup=reply_markup
            )
        elif message.document:
            await send_message_with_retry(
                sender,
                chat_id=target_channel,
                document=file_path if file_path else message.document.file_id,
                caption=caption,
                caption_entities=caption_entities,
                parse_mode=caption_parse_mode,
                reply_markup=reply_markup
            )
        elif message.audio:
            await send_message_with_retry(
                sender,
                chat_id=target_channel,
                audio=file_path if file_path else message.audio.file_id,
                caption=caption,
                caption_entities=caption_entities,
                parse_mode=caption_parse_mode,
                reply_markup=reply_markup
            )
        elif message.voice:
            await send_message_with_retry(
                sender,
                chat_id=target_channel,
                voice=file_path if file_path else message.voice.file_id,
                caption=caption,
                caption_entities=caption_entities,
                parse_mode=caption_parse_mode,
                reply_markup=reply_markup
            )
        elif message.video_note:
            # Video notes need special handling: 
            # 1. Download
            # 2. Convert to square 1:1 using ffmpeg if available
            # 3. Send as video_note
            
            note_path = file_path
            
            # If we didn't download it yet (e.g. file_path is None because we only dl for photo/video/doc/audio/voice above)
            # We must download it now.
            if not note_path:
                note_path = await client.download_media(message)
                
            final_path = note_path
            converted_path = f"{note_path}_converted.mp4"
            
            # Try conversion
            if convert_video_note(note_path, converted_path):
                final_path = converted_path
            else:
                print("Video note conversion failed or ffmpeg missing. Trying raw send.")

            await send_message_with_retry(
                sender,
                chat_id=target_channel,
                video_note=final_path,
                reply_markup=reply_markup
            )
            
            # Cleanup converted file if exists
            if final_path != note_path and os.path.exists(final_path):
                try:
                    os.remove(final_path)
                except:
                    pass
            
            # Original file cleaned up in finally block IF it was assigned to file_path
            # But here we might have downloaded it separately into note_path.
            # So let's ensure cleanup of the downloaded file logic is consistent.
            if not file_path and os.path.exists(note_path):
                 try:
                    os.remove(note_path)
                 except:
                    pass

        elif message.sticker:
            await send_message_with_retry(
                sender,
                chat_id=target_channel,
                sticker=message.sticker.file_id,
                reply_markup=reply_markup
            )
        elif message.text or message.caption:
            await send_message_with_retry(
                sender,
                chat_id=target_channel,
                text=text_body or caption,
                entities=text_entities or caption_entities,
                parse_mode=text_parse_mode or caption_parse_mode,
                reply_markup=reply_markup
            )
        else:
            return
        
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
    reply_markup = None,
    caption_parse_mode: Optional[str] = None,
    sender_client: Client | None = None,
):
    """Clone a media group (album) to target channel using downloaded files"""
    from database import db

    sender = sender_client or client
    
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
                caption_entities=current_caption_entities,
                parse_mode=caption_parse_mode if current_caption else None,
            ))
        elif msg.video:
            media.append(InputMediaVideo(
                file_path if file_path else msg.video.file_id,
                caption=current_caption,
                caption_entities=current_caption_entities,
                parse_mode=caption_parse_mode if current_caption else None,
            ))
        elif msg.document:
            media.append(InputMediaDocument(
                file_path if file_path else msg.document.file_id,
                caption=current_caption,
                caption_entities=current_caption_entities,
                parse_mode=caption_parse_mode if current_caption else None,
            ))
        elif msg.audio:
            media.append(InputMediaAudio(
                file_path if file_path else msg.audio.file_id,
                caption=current_caption,
                caption_entities=current_caption_entities,
                parse_mode=caption_parse_mode if current_caption else None,
            ))
    
    if media:
        try:
            # Use send_media_group for albums
            retries = 0
            while retries < MAX_FLOODWAIT_RETRIES:
                try:
                    # Send media group
                    result = await sender.send_media_group(
                        chat_id=target_channel,
                        media=media
                    )
                    # Edit first message to add reply_markup if needed
                    if result and reply_markup:
                        await sender.edit_message_reply_markup(
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
