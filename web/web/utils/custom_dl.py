import math
import asyncio
import logging
from typing import Union
from hydrogram.types import Message
from utils import temp
from hydrogram import Client, utils, raw
from hydrogram.session import Session, Auth
from hydrogram.errors import AuthBytesInvalid
from hydrogram.file_id import FileId, FileType, ThumbnailSource

logger = logging.getLogger(__name__)

# सेशन निर्माण के लिए लॉक ताकि एक ही समय में कई बार ऑथराइजेशन न हो
session_lock = asyncio.Lock()

async def chunk_size(length):
    return 2 ** max(min(math.ceil(math.log2(length / 1024)), 10), 2) * 1024

async def offset_fix(offset, chunksize):
    offset -= offset % chunksize
    return offset

class TGCustomYield:
    def __init__(self):
        """ A custom method to stream files from telegram. """
        self.main_bot = temp.BOT

    @staticmethod
    async def generate_file_properties(msg: Message):
        media = getattr(msg, msg.media.value, None)
        file_id_obj = FileId.decode(media.file_id)
        return file_id_obj

    async def generate_media_session(self, client: Client, msg: Message):
        data = await self.generate_file_properties(msg)

        # रेस कंडीशन से बचने के लिए लॉक का उपयोग करें
        async with session_lock:
            media_session = client.media_sessions.get(data.dc_id, None)

            if media_session is None:
                if data.dc_id != await client.storage.dc_id():
                    media_session = Session(
                        client, data.dc_id, await Auth(client, data.dc_id, await client.storage.test_mode()).create(),
                        await client.storage.test_mode(), is_media=True
                    )
                    await media_session.start()

                    for _ in range(3):
                        try:
                            exported_auth = await client.invoke(
                                raw.functions.auth.ExportAuthorization(
                                    dc_id=data.dc_id
                                )
                            )
                            await media_session.send(
                                raw.functions.auth.ImportAuthorization(
                                    id=exported_auth.id,
                                    bytes=exported_auth.bytes
                                )
                            )
                            break
                        except AuthBytesInvalid:
                            continue
                        except Exception as e:
                            logger.error(f"Failed to export auth: {e}")
                            await media_session.stop()
                            raise e
                    else:
                        await media_session.stop()
                        raise AuthBytesInvalid
                else:
                    media_session = Session(
                        client, data.dc_id, await client.storage.auth_key(),
                        await client.storage.test_mode(), is_media=True
                    )
                    await media_session.start()

                client.media_sessions[data.dc_id] = media_session

        return media_session

    @staticmethod
    async def get_location(file_id: FileId):
        file_type = file_id.file_type

        if file_type == FileType.CHAT_PHOTO:
            if file_id.chat_id > 0:
                peer = raw.types.InputPeerUser(
                    user_id=file_id.chat_id,
                    access_hash=file_id.chat_access_hash
                )
            else:
                if file_id.chat_access_hash == 0:
                    peer = raw.types.InputPeerChat(
                        chat_id=-file_id.chat_id
                    )
                else:
                    peer = raw.types.InputPeerChannel(
                        channel_id=utils.get_channel_id(file_id.chat_id),
                        access_hash=file_id.chat_access_hash
                    )

            location = raw.types.InputPeerPhotoFileLocation(
                peer=peer,
                volume_id=file_id.volume_id,
                local_id=file_id.local_id,
                big=file_id.thumbnail_source == ThumbnailSource.CHAT_PHOTO_BIG
            )
        elif file_type == FileType.PHOTO:
            location = raw.types.InputPhotoFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size
            )
        else:
            location = raw.types.InputDocumentFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size
            )

        return location

    async def yield_file(self, media_msg: Message, offset: int, first_part_cut: int,
                         last_part_cut: int, part_count: int, chunk_size: int):
        client = self.main_bot
        data = await self.generate_file_properties(media_msg)
        media_session = await self.generate_media_session(client, media_msg)

        current_part = 1
        location = await self.get_location(data)

        try:
            r = await media_session.send(
                raw.functions.upload.GetFile(
                    location=location,
                    offset=offset,
                    limit=chunk_size
                ),
            )

            if isinstance(r, raw.types.upload.File):
                while current_part <= part_count:
                    chunk = r.bytes
                    if not chunk:
                        break
                    
                    # Logic Fix: Slicing the chunk correctly
                    to_yield = chunk
                    
                    # If it's the first part, cut the beginning
                    if current_part == 1:
                        to_yield = to_yield[first_part_cut:]
                    
                    # If it's the last part, cut the end (Critical Fix)
                    if current_part == part_count:
                        # Note: If it's both first AND last part (single chunk file), apply both cuts
                        # Since we already sliced the start, we adjust the end slice relative to the new length is tricky.
                        # Easier method: Apply end cut to the original chunk logic or adjust carefully.
                        
                        # Correct logic:
                        # If current_part == 1, we sliced off `first_part_cut`.
                        # The `last_part_cut` is relative to the *chunk start*.
                        # So if we sliced the start, we need to return up to `last_part_cut - first_part_cut`? No.
                        
                        # Let's simplify:
                        if part_count == 1:
                            yield chunk[first_part_cut:last_part_cut]
                            break
                        else:
                            yield to_yield[:last_part_cut]
                    else:
                        yield to_yield

                    offset += chunk_size
                    current_part += 1

                    # Fetch next chunk if needed
                    if current_part <= part_count:
                        r = await media_session.send(
                            raw.functions.upload.GetFile(
                                location=location,
                                offset=offset,
                                limit=chunk_size
                            ),
                        )
        except Exception as e:
            logger.error(f"Error yielding file: {e}")
            raise e

    async def download_as_bytesio(self, media_msg: Message):
        client = self.main_bot
        data = await self.generate_file_properties(media_msg)
        media_session = await self.generate_media_session(client, media_msg)

        location = await self.get_location(data)
        limit = 1024 * 1024
        offset = 0

        m_file = bytearray()

        while True:
            r = await media_session.send(
                raw.functions.upload.GetFile(
                    location=location,
                    offset=offset,
                    limit=limit
                )
            )

            if isinstance(r, raw.types.upload.File):
                chunk = r.bytes
                if not chunk:
                    break
                m_file.extend(chunk)
                offset += limit
            else:
                break
                
        return bytes(m_file)
