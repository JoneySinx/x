from hydrogram.errors import UserNotParticipant, FloodWait
from info import LONG_IMDB_DESCRIPTION, ADMINS, IS_PREMIUM, TIME_ZONE
from imdb import Cinemagoer
import asyncio
from hydrogram.types import InlineKeyboardButton
from hydrogram import enums
import re
from datetime import datetime, timezone # UTC import
from database.users_chats_db import db
from shortzy import Shortzy
import requests, pytz
import functools # Added for to_thread

imdb = Cinemagoer() 

class temp(object):
    # ... (TEMP CLASS is fine)
    START_TIME = 0
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    CANCEL = False
    U_NAME = None
    B_NAME = None
    SETTINGS = {}
    VERIFICATIONS = {}
    FILES = {}
    USERS_CANCEL = False
    GROUPS_CANCEL = False
    BOT = None
    PREMIUM = {}

# is_subscribed and is_check_admin are fine.

def upload_image(file_path):
    # ... (upload_image is fine)
    with open(file_path, 'rb') as f:
        files = {'files[]': f}
        response = requests.post("https://uguu.se/upload", files=files)
    if response.status_code == 200:
        try:
            data = response.json()
            return data['files'][0]['url'].replace('\\/', '/')
        except Exception:
            return None
    else:
        return None

async def get_poster(query, bulk=False, id=False, file=None):
    if not id:
        query = (query.strip()).lower()
        title = query
        year = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
        if year:
            year = list_to_str(year[:1])
            title = (query.replace(year, "")).strip()
        elif file is not None:
            year = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
            if year:
                year = list_to_str(year[:1]) 
        else:
            year = None
        
        # Blocking call handled by asyncio.to_thread
        func = functools.partial(imdb.search_movie, title.lower(), results=10)
        movieid = await asyncio.to_thread(func)
        
        if not movieid:
            return None
        if year:
            filtered=list(filter(lambda k: str(k.get('year')) == str(year), movieid))
            if not filtered:
                filtered = movieid
        else:
            filtered = movieid
        movieid=list(filter(lambda k: k.get('kind') in ['movie', 'tv series'], filtered))
        if not movieid:
            movieid = filtered
        if bulk:
            return movieid
        movieid = movieid[0].movieID
    else:
        movieid = query
        
    # Blocking call handled by asyncio.to_thread
    func_get = functools.partial(imdb.get_movie, movieid)
    movie = await asyncio.to_thread(func_get)

    # ... (rest of the dictionary creation logic is fine)
    
    # ...
    return {
        # ... dictionary items
        'url':f'https://www.imdb.com/title/tt{movieid}'
    }

# get_verify_status and update_verify_status are fine.

async def is_premium(user_id, bot):
    if not IS_PREMIUM:
        return True
    if user_id in ADMINS:
        return True
    mp = db.get_plan(user_id)
    if mp['premium']:
        if mp['expire'] < datetime.now(timezone.utc): # UTC comparison
            # ... (expiration logic)
            return False
        return True
    else:
        return False


async def check_premium(bot):
    while True:
        pr = [i for i in db.get_premium_users() if i['status']['premium']]
        for p in pr:
            mp = p['status']
            if mp['expire'] < datetime.now(timezone.utc): # UTC comparison
                # ... (expiration logic)
                pass
        await asyncio.sleep(1200)

# broadcast_messages, groups_broadcast_messages, get_settings, save_group_settings are fine.
# get_size, list_to_str, get_shortlink, get_readable_time, get_wish are fine.

def get_seconds(time_string):
    """Parses a time string (e.g., '10h', '30day') into total seconds."""
    match = re.match(r'(\d+)([a-zA-Z]+)', time_string)
    if not match:
        return 0
        
    value = int(match.group(1))
    unit = match.group(2).lower()
    
    unit_multipliers = {
        's': 1,
        'min': 60,
        'h': 3600, 
        'hour': 3600,
        'd': 86400, 
        'day': 86400,
        'month': 86400 * 30,
        'year': 86400 * 365
    }
    
    return value * unit_multipliers.get(unit, 0)
