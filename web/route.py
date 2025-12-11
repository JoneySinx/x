import time
import math
import logging
from aiohttp import web
from utils import temp
from info import BIN_CHANNEL
from web.utils.render_template import media_watch

routes = web.RouteTableDef()
logger = logging.getLogger(__name__)

# --- WATCH PAGE ---
@routes.get("/watch/{message_id}")
async def watch_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        return web.Response(text=await media_watch(message_id), content_type='text/html')
    except ValueError:
        return web.Response(text="Invalid Request", status=400)

# --- THUMBNAIL SERVER (NEW) ---
@routes.get("/thumbnail/{message_id}")
async def thumbnail_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        msg = await temp.BOT.get_messages(BIN_CHANNEL, message_id)
        
        # Determine media type and get thumbnail file_id
        media = getattr(msg, msg.media.value, None)
        if not media: return web.Response(status=404)
        
        thumb = getattr(media, 'thumb', None)
        if not thumb: return web.Response(status=404)
        
        # Download Thumbnail to Memory
        file = await temp.BOT.download_media(thumb.file_id, in_memory=True)
        return web.Response(body=file.getvalue(), content_type='image/jpeg')
        
    except Exception as e:
        logger.error(f"Thumbnail Error: {e}")
        return web.Response(status=500)

# --- FILE STREAMER ---
@routes.get("/download/{message_id}")
async def stream_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        msg = await temp.BOT.get_messages(BIN_CHANNEL, message_id)
        if not msg or not msg.media:
            return web.Response(status=404, text="File Not Found")
            
        media = getattr(msg, msg.media.value, None)
        file_id = media.file_id
        file_size = media.file_size
        file_name = getattr(media, 'file_name', 'file')
        
        # Range Handling
        offset = 0
        limit = file_size
        headers = request.headers
        range_header = headers.get("Range")
        
        if range_header:
            parts = range_header.replace("bytes=", "").split("-")
            offset = int(parts[0]) if parts[0] else 0
            limit = int(parts[1]) + 1 if len(parts) > 1 and parts[1] else file_size
            
        # Stream Content
        async def file_stream():
            async for chunk in temp.BOT.stream_media(file_id, limit=limit - offset, offset=offset):
                yield chunk

        response = web.StreamResponse(
            status=206 if range_header else 200,
            reason='Partial Content' if range_header else 'OK'
        )
        response.headers['Content-Type'] = getattr(media, 'mime_type', 'application/octet-stream')
        response.headers['Content-Range'] = f'bytes {offset}-{limit - 1}/{file_size}'
        response.headers['Content-Length'] = str(limit - offset)
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Disposition'] = f'attachment; filename="{file_name}"'
        
        await response.prepare(request)
        
        async for chunk in file_stream():
            await response.write(chunk)
            
        return response
        
    except Exception as e:
        logger.error(f"Stream Error: {e}")
        return web.Response(status=500)
