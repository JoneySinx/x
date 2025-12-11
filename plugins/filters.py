import re
import logging
from hydrogram import Client, filters, enums
from database.users_chats_db import db
from utils import is_check_admin

logger = logging.getLogger(__name__)

# --- ➕ ADD FILTER (/filter or /add) ---
@Client.on_message(filters.command(["filter", "add"]) & filters.group)
async def add_filter(client, message):
    if not await is_check_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("<b>🛑 Aᴄᴄᴇss Dᴇɴɪᴇᴅ!</b>\nOnly Admins can save filters.")
    
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply("<b>⚠️ Usᴀɢᴇ:</b>\nReply to a message with <code>/filter name</code> to save it.")
    
    try:
        name = message.text.split(None, 1)[1].lower().strip()
    except IndexError:
        return await message.reply("<b>❌ Eʀʀᴏʀ:</b> Please provide a name!\nExample: <code>/filter rules</code>")
    
    reply = message.reply_to_message
    filter_data = {}
    
    if reply:
        if reply.text:
            filter_data['type'] = 'text'
            filter_data['text'] = reply.text
        elif reply.media:
            filter_data['type'] = 'media'
            # file_id और media_type को सुरक्षित तरीके से निकालें
            media_obj = getattr(reply, reply.media.value)
            filter_data['file_id'] = media_obj.file_id
            filter_data['media_type'] = str(reply.media.value)
            filter_data['caption'] = reply.caption or ""
        else:
            return await message.reply("<b>❌ Uɴsᴜᴘᴘᴏʀᴛᴇᴅ Mᴇssᴀɢᴇ Tʏᴘᴇ!</b>")
    else:
        return await message.reply("<b>⚠️ Pʟᴇᴀsᴇ Rᴇᴘʟʏ ᴛᴏ ᴀ Mᴇssᴀɢᴇ!</b>")

    await db.add_filter(message.chat.id, name, filter_data)
    await message.reply(f"<b>✅ Fɪʟᴛᴇʀ Sᴀᴠᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n\n<b>🔖 Nᴀᴍᴇ:</b> <code>{name}</code>")

# --- 🗑️ DELETE FILTER (/stop or /del) ---
@Client.on_message(filters.command(["stop", "del"]) & filters.group)
async def stop_filter(client, message):
    if not await is_check_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("<b>🛑 Aᴄᴄᴇss Dᴇɴɪᴇᴅ!</b>\nOnly Admins can delete filters.")
        
    if len(message.command) < 2:
        return await message.reply("<b>⚠️ Usᴀɢᴇ:</b> <code>/stop name</code>")
    
    name = message.text.split(None, 1)[1].lower().strip()
    
    deleted = await db.delete_filter(message.chat.id, name)
    if deleted:
        await message.reply(f"<b>🗑️ Fɪʟᴛᴇʀ Dᴇʟᴇᴛᴇᴅ:</b> <code>{name}</code>")
    else:
        await message.reply("<b>❌ Fɪʟᴛᴇʀ Nᴏᴛ Fᴏᴜɴᴅ!</b>")

# --- ♻️ DELETE ALL FILTERS (/stopall or /delall) ---
@Client.on_message(filters.command(["stopall", "delall"]) & filters.group)
async def stop_all_filters(client, message):
    if not await is_check_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("<b>🛑 Aᴅᴍɪɴ Oɴʟʏ!</b>")
    
    await db.delete_all_filters(message.chat.id)
    await message.reply("<b>♻️ Aʟʟ Fɪʟᴛᴇʀs Hᴀᴠᴇ Bᴇᴇɴ Cʟᴇᴀɴᴇᴅ!</b>")

# --- 📑 LIST FILTERS (/filters) ---
@Client.on_message(filters.command("filters") & filters.group)
async def list_filters(client, message):
    filters_list = await db.get_filters(message.chat.id)
    
    if not filters_list:
        return await message.reply("<b>📂 Nᴏ Aᴄᴛɪᴠᴇ Fɪʟᴛᴇʀs ɪɴ ᴛʜɪs Gʀᴏᴜᴘ.</b>")
    
    text = "<b>📑 <u>Sᴀᴠᴇᴅ Fɪʟᴛᴇʀs Lɪsᴛ</u></b>\n\n"
    for f in filters_list:
        text += f"🔹 <code>{f}</code>\n"
    
    await message.reply(text)

# --- 🤖 AUTO REPLY HANDLER ---
# Priority Group=1 ensures it runs alongside other handlers but we stop propagation if matched
@Client.on_message(filters.group & filters.text & filters.incoming, group=1)
async def filter_check(client, message):
    if not message.text or message.text.startswith("/"):
        return
        
    name = message.text.lower().strip()
    
    # Check Database
    filter_data = await db.get_filter(message.chat.id, name)
    
    if filter_data:
        try:
            if filter_data['type'] == 'text':
                await message.reply(
                    filter_data['text'], 
                    disable_web_page_preview=True,
                    parse_mode=enums.ParseMode.MARKDOWN
                )
            elif filter_data['type'] == 'media':
                await client.send_cached_media(
                    chat_id=message.chat.id,
                    file_id=filter_data['file_id'],
                    caption=filter_data.get('caption', "")
                )
            
            # 🛑 STOP PROPAGATION (Important)
            # अगर फिल्टर मिल गया, तो बॉट इसे मूवी समझकर सर्च नहीं करेगा
            message.stop_propagation()
            
        except Exception as e:
            logger.error(f"Filter Error: {e}")
