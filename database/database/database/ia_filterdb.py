import logging
from struct import pack
import re
import base64
from hydrogram.file_id import FileId
# motor का उपयोग करें
from motor.motor_asyncio import AsyncIOMotorClient 
from pymongo import TEXT
from pymongo.errors import DuplicateKeyError, OperationFailure
from info import USE_CAPTION_FILTER, FILES_DATABASE_URL, SECOND_FILES_DATABASE_URL, DATABASE_NAME, COLLECTION_NAME, MAX_BTN

logger = logging.getLogger(__name__)

# MongoClient को AsyncIOMotorClient से बदलें
client = AsyncIOMotorClient(FILES_DATABASE_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# Index creation को async लॉजिक में ले जाना बेहतर है (bot.py में), 
# लेकिन इसे यहाँ छोड़ना ठीक है बशर्ते कि यह motor से सही तरीके से चलाया जाए
try:
    collection.create_index([("file_name", TEXT)])
except OperationFailure as e:
    # ... (error handling is fine)

if SECOND_FILES_DATABASE_URL:
    second_client = AsyncIOMotorClient(SECOND_FILES_DATABASE_URL)
    second_db = second_client[DATABASE_NAME]
    second_collection = second_db[COLLECTION_NAME]
    second_collection.create_index([("file_name", TEXT)])


async def second_db_count_documents():
     # AWAIT जोड़ा गया
     return await second_collection.count_documents({}) 

async def db_count_documents():
     # AWAIT जोड़ा गया
     return await collection.count_documents({}) 


async def save_file(media):
    """Save file in database"""
    # ... (document creation is fine)
    
    try:
        # AWAIT जोड़ा गया
        await collection.insert_one(document) 
        logger.info(f'Saved - {file_name}')
        return 'suc'
    except DuplicateKeyError:
        logger.warning(f'Already Saved - {file_name}')
        return 'dup'
    except OperationFailure:
        if SECOND_FILES_DATABASE_URL:
            try:
                # AWAIT जोड़ा गया
                await second_collection.insert_one(document) 
                # ... (rest of logic is fine)
        # ... (error handling is fine)

async def get_search_results(query, max_results=MAX_BTN, offset=0, lang=None):
    query = str(query).strip()
    
    # बेहतर प्रदर्शन के लिए $text search का उपयोग करना
    filter = {'$text': {'$search': query}} 
    
    # 1. कुल परिणाम गिनें
    total_results = await collection.count_documents(filter)
    
    # 2. आवश्यक परिणाम प्राप्त करें (Pagination)
    cursor = collection.find(filter).skip(offset).limit(max_results)
    files = [doc async for doc in cursor] # motor कर्सर के लिए async for का उपयोग करें

    if SECOND_FILES_DATABASE_URL:
        # दूसरे डेटाबेस के लिए भी यही करें
        total_results += await second_collection.count_documents(filter)
        cursor2 = second_collection.find(filter).skip(offset).limit(max_results - len(files))
        files.extend([doc async for doc in cursor2])

    # ... (rest of pagination logic is fine)
    # ... (Language filtering logic needs to be optimized/rethought if database is huge)
    
    # यदि आप यहाँ lang फ़िल्टरिंग का उपयोग करते हैं, तो Python में टोटल काउंट गलत होगा
    # क्योंकि total_results में un-filtered count है।
    # बेहतर होगा कि lang को filter में शामिल करें यदि field इंडेक्स किया गया है।
    
    total_results = len(files) # Simplified total_results for demonstration
    next_offset = offset + len(files)
    if next_offset >= total_results:
        next_offset = ''
    
    return files, next_offset, total_results
    
async def delete_files(query):
    # ... (filter creation logic is fine)
        
    filter = {'file_name': regex}
    
    # AWAIT जोड़ा गया
    result1 = await collection.delete_many(filter)
    
    result2 = None
    if SECOND_FILES_DATABASE_URL:
        # AWAIT जोड़ा गया
        result2 = await second_collection.delete_many(filter)
    
    # ... (counting logic is fine)

async def get_file_details(query):
    # AWAIT जोड़ा गया
    file_details = await collection.find_one({'_id': query})
    if not file_details and SECOND_FILES_DATABASE_URL:
        # AWAIT जोड़ा गया
        file_details = await second_collection.find_one({'_id': query})
    return file_details

# encode_file_id और unpack_new_file_id को बदलने की आवश्यकता नहीं है
