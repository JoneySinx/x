import logging
from hydrogram import Client, filters
from info import INDEX_CHANNELS
from database.ia_filterdb import save_file

# लॉगिंग सेट करें ताकि हम कंसोल में देख सकें कि क्या हो रहा है
logger = logging.getLogger(__name__)

media_filter = filters.document | filters.video | filters.audio

@Client.on_message(filters.chat(INDEX_CHANNELS) & media_filter)
async def media(bot, message):
    """Media Handler: इंडेक्स चैनलों से नई फाइलें सेव करता है"""
    
    media = None
    file_type = None

    # फ़ाइल प्रकार की पहचान करें
    for type in ("document", "video", "audio"):
        media_obj = getattr(message, type, None)
        if media_obj is not None:
            media = media_obj
            file_type = type
            break

    # अगर कोई मीडिया नहीं है (सुरक्षा जांच)
    if media is None:
        return

    # मीडिया ऑब्जेक्ट में एक्स्ट्रा जानकारी जोड़ें
    media.file_type = file_type
    media.caption = message.caption

    try:
        # डेटाबेस में सेव करें (save_file async होना चाहिए)
        sts = await save_file(media)
        
        if sts == 'suc':
            logger.info(f"File Saved: {getattr(media, 'file_name', 'Unknown')}")
        elif sts == 'dup':
            logger.info(f"File Already Exists: {getattr(media, 'file_name', 'Unknown')}")
        elif sts == 'err':
            logger.error(f"Error Saving File: {getattr(media, 'file_name', 'Unknown')}")
            
    except Exception as e:
        # अगर कोई क्रैश या एरर आता है, तो बॉट रुकेगा नहीं, बस लॉग करेगा
        logger.error(f"Media Handler Error: {e}")
