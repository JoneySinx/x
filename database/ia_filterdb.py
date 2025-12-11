import logging
import re
import base64
from struct import pack
from hydrogram.file_id import FileId
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import TEXT
from pymongo.errors import DuplicateKeyError, OperationFailure
from info import DATA_DATABASE_URL, DATABASE_NAME, COLLECTION_NAME, MAX_BTN, USE_CAPTION_FILTER

logger = logging.getLogger(__name__)

client = AsyncIOMotorClient(DATA_DATABASE_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# --- ⚡ COMPILED REGEX PATTERNS ---
RE_SPECIAL = re.compile(r"[\.\+\-_]")
RE_USERNAMES = re.compile(r"@\w+")
RE_BRACKETS = re.compile(r"[\[\(\{].*?[\]\}\)]")
RE_EXTENSIONS = re.compile(r"\b(mkv|mp4|avi|m4v|webm|flv)\b", flags=re.IGNORECASE)
RE_SPACES = re.compile(r"\s+")

async def create_text_index():
    try:
        await collection.create_index([("file_name", TEXT), ("caption", TEXT)], name="file_search_index")
    except Exception as e:
        logger.warning(f"Index Error: {e}")

async def save_file(media):
    file_id = unpack_new_file_id(media.file_id)
    
    # --- FILENAME CLEANING ---
    original_name = str(media.file_name or "")
    
    clean_name = RE_SPECIAL.sub(" ", original_name)
    clean_name = RE_USERNAMES.sub("", clean_name)
    clean_name = RE_BRACKETS.sub("", clean_name)
    clean_name = RE_SPACES.sub(" ", clean_name)
    
    # 🔥 CHANGE: .lower() -> .title() (For "Iron Man" look)
    file_name = clean_name.strip().title()
    
    # --- CAPTION CLEANING ---
    original_caption = str(media.caption or "")
    clean_caption = RE_SPECIAL.sub(" ", original_caption)
    clean_caption = RE_USERNAMES.sub("", clean_caption)
    clean_caption = RE_BRACKETS.sub("", clean_caption)
    clean_caption = RE_EXTENSIONS.sub("", clean_caption)
    clean_caption = RE_SPACES.sub(" ", clean_caption)
    
    file_caption = clean_caption.strip() # Keep caption case as is or .lower()
    
    document = {
        '_id': file_id,
        'file_name': file_name,
        'file_size': media.file_size,
        'caption': file_caption,
        'file_type': media.file_type,
        'mime_type': media.mime_type
    }
    
    try:
        await collection.insert_one(document)
        logger.info(f"✅ Saved: {file_name[:50]}...") 
        return 'suc'
    except DuplicateKeyError:
        return 'dup'
    except Exception as e:
        logger.error(f"❌ Error Saving: {e}")
        return 'err'

async def get_search_results(query, max_results=MAX_BTN, offset=0, lang=None):
    query = str(query).strip().lower()
    query = RE_SPECIAL.sub(" ", query)
    query = RE_SPACES.sub(" ", query).strip()

    if not query:
        return [], "", 0

    # --- LAYER 1: Text Search ---
    text_results = []
    total_text_results = 0
    text_search_failed = False

    try:
        if lang:
            search_query = f'"{query}" "{lang}"' 
            filter_dict = {'$text': {'$search': search_query}}
        else:
            filter_dict = {'$text': {'$search': query}} 
        
        total_text_results = await collection.count_documents(filter_dict)
        
        if total_text_results > 0:
            cursor = collection.find(filter_dict, {'score': {'$meta': 'textScore'}}).sort([('score', {'$meta': 'textScore'})])
            cursor.skip(offset).limit(max_results)
            text_results = [doc async for doc in cursor]
            
            next_offset = offset + len(text_results)
            if next_offset >= total_text_results or len(text_results) == 0:
                next_offset = ""
            return text_results, next_offset, total_text_results
            
    except OperationFailure:
        text_search_failed = True
    except Exception as e:
        logger.error(f"Text Search Error: {e}")
        text_search_failed = True

    # --- LAYER 2: Regex Search (Fallback) ---
    # 🔥 FIXED: Added Pagination logic here too!
    if total_text_results == 0 or text_search_failed:
        try:
            words = query.split()
            if len(words) > 0: 
                regex_pattern = ""
                for word in words:
                    regex_pattern += f"(?=.*{re.escape(word)})"
                
                if USE_CAPTION_FILTER:
                    regex_filter = {
                        '$or': [
                            {'file_name': {'$regex': regex_pattern, '$options': 'i'}},
                            {'caption': {'$regex': regex_pattern, '$options': 'i'}}
                        ]
                    }
                else:
                    regex_filter = {'file_name': {'$regex': regex_pattern, '$options': 'i'}}
                
                total_results_regex = await collection.count_documents(regex_filter)
                
                if total_results_regex > 0:
                    cursor = collection.find(regex_filter).sort('_id', -1)
                    cursor.skip(offset).limit(max_results) # 🔥 Added SKIP
                    files = [doc async for doc in cursor]
                    
                    # 🔥 Calculate Next Offset
                    next_offset = offset + len(files)
                    if next_offset >= total_results_regex or len(files) == 0:
                        next_offset = ""
                        
                    return files, next_offset, total_results_regex
        except Exception as e:
            logger.error(f"Regex Search Error: {e}")
            return [], "", 0

    return [], "", 0

async def get_file_details(query):
    try:
        file_details = await collection.find_one({'_id': query})
        return file_details
    except Exception:
        return None

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    return file_id

async def db_count_documents():
     return await collection.count_documents({})

async def delete_files(query):
    query = query.strip()
    if not query: return 0
    filter = {'file_name': {'$regex': query, '$options': 'i'}}
    result1 = await collection.delete_many(filter)
    logger.info(f"🗑️ Deleted {result1.deleted_count} files for query: {query}")
    return result1.deleted_count
