import logging
from hydrogram import Client, filters
from info import INDEX_CHANNELS
from database.ia_filterdb import save_file, update_file # 🔥 Import update_file
from database.users_chats_db import db

logger = logging.getLogger(__name__)

@Client.on_message(filters.channel & filters.incoming)
async def index_handler(bot, message):
    # 1. Check Media
    if not message.media:
        return 

    # 2. Chat ID Check
    chat_id = message.chat.id
    
    is_indexed = False
    if chat_id in INDEX_CHANNELS:
        is_indexed = True
    else:
        try:
            db_channels = await db.get_index_channels_db()
            if chat_id in db_channels:
                is_indexed = True
        except:
            pass

    if not is_indexed:
        return

    # 4. Media Extract
    try:
        media = getattr(message, message.media.value)
    except:
        return

    # 5. Junk Filter
    if media.file_size < 2 * 1024 * 1024:
        return 

    # 6. Save to DB
    media.file_type = message.media.value
    media.caption = message.caption

    try:
        sts = await save_file(media)
        
        if sts == 'suc':
            try: await message.react(emoji="💖")
            except: pass
            logger.info(f"✅ Indexed: {getattr(media, 'file_name', 'Unknown')}")
            
        elif sts == 'dup':
            try: await message.react(emoji="🦄")
            except: pass
            
        elif sts == 'err':
            try: await message.react(emoji="💔")
            except: pass
            
    except Exception as e:
        logger.error(f"Channel Index Error: {e}")

# --- EDIT HANDLER ---
@Client.on_edited_message(filters.channel)
async def edit_handler(bot, message):
    if not message.media: return
    
    # ID Check logic same as above
    chat_id = message.chat.id
    is_indexed = False
    if chat_id in INDEX_CHANNELS:
        is_indexed = True
    else:
        try:
            db_channels = await db.get_index_channels_db()
            if chat_id in db_channels:
                is_indexed = True
        except: pass
        
    if not is_indexed: return
    
    try: media = getattr(message, message.media.value)
    except: return
    
    if media.file_size < 2 * 1024 * 1024: return

    media.file_type = message.media.value
    media.caption = message.caption
    
    # 🔥 USE UPDATE_FILE INSTEAD OF SAVE_FILE
    try:
        await update_file(media)
        try: await message.react(emoji="✍️")
        except: pass
        logger.info(f"📝 File Updated: {getattr(media, 'file_name', 'Unknown')}")
    except Exception as e:
        logger.error(f"Edit Error: {e}")
