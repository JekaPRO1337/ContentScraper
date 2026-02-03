from typing import List, Optional
from pyrogram import Client, enums
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio
from utils.button_replacer import replace_markup
from config import FLOODWAIT_RETRY_DELAY, MAX_FLOODWAIT_RETRIES
try:
    MAX_FLOODWAIT_RETRIES = int(MAX_FLOODWAIT_RETRIES)
    FLOODWAIT_RETRY_DELAY = int(FLOODWAIT_RETRY_DELAY)
except:
    MAX_FLOODWAIT_RETRIES = 5
    FLOODWAIT_RETRY_DELAY = 1
from utils.license_check import verify_license
from config import SNIFFER_LICENSE
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
        cmd = [
            FFMPEG_CMD, '-y',
            '-i', input_path,
            '-vf', 'crop=min(iw,ih):min(iw,ih),scale=384:384',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '26',
            '-c:a', 'aac',
            '-b:a', '64k',
            '-t', '59',
            '-pix_fmt', 'yuv420p',
            output_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"FFmpeg conversion error: {e}")
        return False


async def send_message_with_retry(client: Client, chat_id, **kwargs):
    """Send a message with FloodWait retry logic"""
    kwargs = kwargs.copy()
    
    # Determine correct send function
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
        # Stickers don't support caption/parse_mode
        kwargs.pop('caption', None)
        kwargs.pop('caption_entities', None)
        kwargs.pop('parse_mode', None)
    elif 'video_note' in kwargs:
        send_fn = client.send_video_note
        # Video notes don't support caption/parse_mode
        kwargs.pop('caption', None)
        kwargs.pop('caption_entities', None)
        kwargs.pop('parse_mode', None)

    # CRITICAL FIX: Remove parse_mode completely if it's None or problematic
    if 'parse_mode' in kwargs:
        pm = kwargs.get('parse_mode')
        if pm is None:
            kwargs.pop('parse_mode')
        elif isinstance(pm, str):
            pm_lower = pm.lower()
            if pm_lower == 'html':
                kwargs['parse_mode'] = enums.ParseMode.HTML
            elif pm_lower in ['markdown', 'md']:
                # DO NOT use markdown - remove it entirely to avoid errors
                kwargs.pop('parse_mode')
            else:
                kwargs.pop('parse_mode')

    retries = 0
    while retries < MAX_FLOODWAIT_RETRIES:
        try:
            return await send_fn(chat_id=chat_id, **kwargs)
        except Exception as e:
            error_msg = str(e)
            
            if "Invalid parse mode" in error_msg:
                print(f"Parse mode error, retrying without parse_mode: {error_msg}")
                kwargs.pop('parse_mode', None)
                return await send_fn(chat_id=chat_id, **kwargs)

            if "FLOOD_WAIT" in error_msg or "flood" in error_msg.lower():
                wait_time = FLOODWAIT_RETRY_DELAY
                try:
                    match = re.search(r'(\d+)', error_msg)
                    if match:
                        wait_time = min(int(match.group(1)) + 1, 60)
                except:
                    pass
                
                retries += 1
                if retries < MAX_FLOODWAIT_RETRIES:
                    await asyncio.sleep(wait_time)
                    continue
            
            if "PEER_ID_INVALID" in error_msg and retries == 0:
                try:
                    await client.get_chat(chat_id)
                    retries += 1
                    continue
                except Exception as resolve_error:
                    print(f"Failed to resolve peer {chat_id}: {resolve_error}")

            raise


async def apply_link_rules_to_text(text: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Apply link replacement rules to text. Returns (modified_text, parse_mode)"""
    if not text:
        return text, None

    rules = await db.get_all_link_rules()
    if not rules:
        return text, None

    result = text
    use_html = False

    for rule in rules:
        pattern = (rule.get("pattern") or "").strip()
        replacement = rule.get("replacement") or ""
        if not pattern:
            continue

        # Check if replacement contains markdown-style link
        if "[" in replacement and "](" in replacement:
            use_html = True
            # Convert [text](url) to <a href="url">text</a>
            replacement = re.sub(
                r'\[([^\]]+)\]\(([^)]+)\)',
                r'<a href="\2">\1</a>',
                replacement
            )

        if pattern.startswith("regex:"):
            try:
                regex = re.compile(pattern[6:], re.IGNORECASE)
            except Exception:
                continue
            if regex.search(result):
                result = regex.sub(replacement, result)
        else:
            if pattern.lower() in result.lower():
                try:
                    result = re.sub(
                        re.escape(pattern),
                        replacement,
                        result,
                        flags=re.IGNORECASE,
                    )
                except Exception:
                    continue

    # If we're using HTML, escape special chars in text parts (not in our HTML tags)
    if use_html:
        # Simple approach: escape < and > that are not part of our <a> tags
        # This is a basic implementation - for full safety we'd need proper HTML parsing
        pass  # Skip escaping for now since replacement already has proper HTML

    return result, ("html" if use_html else None)


async def download_and_clone_message(
    client: Client,
    message: Message,
    target_channel: str,
    pair_id: int,
    sender_client: Client | None = None,
):
    """Download media and clone message to target channel"""
    sender = sender_client or client
    
    # ALWAYS get button markup - this is critical for adding buttons to every post
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
            note_path = file_path
            if not note_path:
                note_path = await client.download_media(message)
                
            final_path = note_path
            converted_path = f"{note_path}_converted.mp4"
            
            if convert_video_note(note_path, converted_path):
                final_path = converted_path
            else:
                print("Video note conversion failed. Trying raw send.")

            await send_message_with_retry(
                sender,
                chat_id=target_channel,
                video_note=final_path,
                reply_markup=reply_markup
            )
            
            if final_path != note_path and os.path.exists(final_path):
                try:
                    os.remove(final_path)
                except:
                    pass
            
            if not file_path and note_path and os.path.exists(note_path):
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
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass


async def clone_message(client: Client, message: Message, target_channel: str, pair_id: int):
    """Clone a message to target channel with button replacement"""
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
    """Clone a media group (album) to target channel"""
    from database import db

    sender = sender_client or client
    
    if not messages_data:
        return
    
    media = []
    
    # Convert parse_mode string to enum if needed
    actual_parse_mode = None
    if caption_parse_mode:
        if caption_parse_mode.lower() == 'html':
            actual_parse_mode = enums.ParseMode.HTML
    
    for i, item in enumerate(messages_data):
        msg = item.get('message') if isinstance(item, dict) else item
        file_path = item.get('file_path') if isinstance(item, dict) else None
        
        is_first = i == 0
        current_caption = caption if is_first and caption else None
        current_caption_entities = caption_entities if is_first and caption_entities else None
        
        if msg.photo:
            media.append(InputMediaPhoto(
                file_path if file_path else msg.photo.file_id,
                caption=current_caption,
                caption_entities=current_caption_entities,
                parse_mode=actual_parse_mode if current_caption else None,
            ))
        elif msg.video:
            media.append(InputMediaVideo(
                file_path if file_path else msg.video.file_id,
                caption=current_caption,
                caption_entities=current_caption_entities,
                parse_mode=actual_parse_mode if current_caption else None,
            ))
        elif msg.document:
            media.append(InputMediaDocument(
                file_path if file_path else msg.document.file_id,
                caption=current_caption,
                caption_entities=current_caption_entities,
                parse_mode=actual_parse_mode if current_caption else None,
            ))
        elif msg.audio:
            media.append(InputMediaAudio(
                file_path if file_path else msg.audio.file_id,
                caption=current_caption,
                caption_entities=current_caption_entities,
                parse_mode=actual_parse_mode if current_caption else None,
            ))
    
    if media:
        try:
            retries = 0
            while retries < MAX_FLOODWAIT_RETRIES:
                try:
                    result = await sender.send_media_group(
                        chat_id=target_channel,
                        media=media
                    )
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
            await db.increment_statistics(pair_id)
        except Exception as e:
            print(f"Error cloning media group: {str(e)}")
            raise
