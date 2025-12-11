import logging
import re
import base64
from struct import pack
from hydrogram.file_id import FileId
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import TEXT
from pymongo.errors import DuplicateKeyError
from info import DATA_DATABASE_URL, DATABASE_NAME, COLLECTION_NAME, MAX_BTN, USE_CAPTION_FILTER

logger = logging.getLogger(__name__)

# --- Single Database Connection ---
client = AsyncIOMotorClient(DATA_DATABASE_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

async def save_file(media):
    """
    Save file using standard logic (Cleaning Filename Only).
    NO Smart Caption Logic here.
    """
    file_id = unpack_new_file_id(media.file_id)
    
    # --- FILENAME CLEANING ---
    original_name = str(media.file_name or "")
    
    # 1. Replace dots, underscores, hyphens with space
    clean_name = re.sub(r"[\.\+\-_]", " ", original_name)
    
    # 2. Remove @usernames
    clean_name = re.sub(r"@\w+", "", clean_name)
    
    # 3. Remove content inside brackets: [720p], (2024), {Dual}
    clean_name = re.sub(r"[\[\(\{].*?[\]\}\)]", "", clean_name)
    
    # 4. Remove file extensions
    clean_name = re.sub(r"\b(mkv|mp4|avi|m4v|webm|flv)\b", "", clean_name, flags=re.IGNORECASE)
    
    # 5. Collapse multiple spaces into one
    clean_name = re.sub(r"\s+", " ", clean_name)
    
    # 6. Final cleanup
    file_name = clean_name.strip().lower()
    
    # --- CAPTION CLEANING ---
    original_caption = str(media.caption or "")
    clean_caption = re.sub(r"[\.\+\-_]", " ", original_caption)
    clean_caption = re.sub(r"@\w+", "", clean_caption)
    clean_caption = re.sub(r"[\[\(\{].*?[\]\}\)]", "", clean_caption)
    clean_caption = re.sub(r"\b(mkv|mp4|avi|m4v|webm|flv)\b", "", clean_caption, flags=re.IGNORECASE)
    clean_caption = re.sub(r"\s+", " ", clean_caption)
    file_caption = clean_caption.strip().lower()
    
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
        return 'suc'
    except DuplicateKeyError:
        return 'dup'
    except Exception:
        return 'err'

async def get_search_results(query, max_results=MAX_BTN, offset=0, lang=None):
    """
    Hybrid Search Implementation:
    Layer 1: MongoDB Text Search (Fast & Accurate)
    Layer 2: Regex Split Search (Smart Fallback + Caption Support)
    """
    
    # Cleaning the query
    query = str(query).strip().lower()
    query = re.sub(r"[\.\+\-_]", " ", query)
    query = re.sub(r"\s+", " ", query).strip()

    if not query:
        return [], "", 0

    # --- LAYER 1: Text Search (Standard) ---
    if lang:
        search_query = f'"{query}" "{lang}"' 
        filter_dict = {'$text': {'$search': search_query}}
    else:
        filter_dict = {'$text': {'$search': query}} 
    
    try:
        total_results = await collection.count_documents(filter_dict)
        
        if total_results > 0:
            cursor = collection.find(filter_dict, {'score': {'$meta': 'textScore'}}).sort([('score', {'$meta': 'textScore'})])
            cursor.skip(offset).limit(max_results)
            files = [doc async for doc in cursor]
            
            next_offset = offset + len(files)
            if next_offset >= total_results or len(files) == 0:
                next_offset = ""
            return files, next_offset, total_results

        # --- LAYER 2: Smart Regex Search (Fallback + Caption Filter) ---
        if offset == 0:
            words = query.split()
            if len(words) > 0: 
                regex_pattern = ""
                for word in words:
                    regex_pattern += f"(?=.*{re.escape(word)})"
                
                # Check USE_CAPTION_FILTER from Info
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
                    cursor.limit(max_results)
                    files = [doc async for doc in cursor]
                    return files, "", total_results_regex

        return [], "", 0
        
    except Exception as e:
        logger.error(f"Search Error: {e}")
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

async def second_db_count_documents():
     return 0

async def delete_files(query):
    query = query.strip()
    if not query: return 0
    filter = {'$text': {'$search': query}}
    result1 = await collection.delete_many(filter)
    return result1.deleted_count
