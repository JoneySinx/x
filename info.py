import re
import os
from os import environ
from Script import script  # सुनिश्चित करें कि Script.py फ़ाइल मौजूद है
import logging

# लॉगिंग सेट करें
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_enabled(data, default):
    """बूलियन मानों (True/False) को सुरक्षित रूप से हैंडल करने के लिए"""
    val = environ.get(data, str(default))
    if val.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif val.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        logger.warning(f'{data} is invalid, using default: {default}')
        return default

def is_valid_ip(ip):
    """IP एड्रेस की वैधता जांचने के लिए"""
    ip_pattern = r'\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    return re.match(ip_pattern, ip) is not None

# ==============================================================================
# REQUIRED VARIABLES (ज़रूरी वैरिएबल्स)
# ==============================================================================

# API ID
API_ID = environ.get('API_ID', '')
if not API_ID.isdigit():
    logger.error('API_ID is missing or invalid (must be an integer), exiting now')
    exit(1)
API_ID = int(API_ID)

# API HASH
API_HASH = environ.get('API_HASH', '')
if len(API_HASH) == 0:
    logger.error('API_HASH is missing, exiting now')
    exit(1)

# BOT TOKEN
BOT_TOKEN = environ.get('BOT_TOKEN', '')
if len(BOT_TOKEN) == 0:
    logger.error('BOT_TOKEN is missing, exiting now')
    exit(1)

try:
    BOT_ID = int(BOT_TOKEN.split(":")[0])
except ValueError:
    logger.error('BOT_TOKEN is invalid (BOT_ID part is not an integer), exiting now')
    exit(1)

# DATABASE URLs
DATA_DATABASE_URL = environ.get('DATA_DATABASE_URL', "")
if not DATA_DATABASE_URL.startswith('mongodb'):
    logger.error('DATA_DATABASE_URL is missing or invalid, exiting now')
    exit(1)

FILES_DATABASE_URL = environ.get('FILES_DATABASE_URL', "")
if not FILES_DATABASE_URL.startswith('mongodb'):
    logger.error('FILES_DATABASE_URL is missing or invalid, exiting now')
    exit(1)

# ADMINS
ADMINS_STR = environ.get('ADMINS', '')
if len(ADMINS_STR) == 0:
    logger.error('ADMINS is missing, exiting now')
    exit(1)
try:
    ADMINS = [int(admins) for admins in ADMINS_STR.split()]
except ValueError:
    logger.error('ADMINS must contain only integer IDs separated by space, exiting now')
    exit(1)

# CHANNELS & GROUPS
LOG_CHANNEL_STR = environ.get('LOG_CHANNEL', '')
if not LOG_CHANNEL_STR.lstrip('-').isdigit():
    logger.error('LOG_CHANNEL is missing or invalid, exiting now')
    exit(1)
LOG_CHANNEL = int(LOG_CHANNEL_STR)

SUPPORT_GROUP_STR = environ.get('SUPPORT_GROUP', '')
if not SUPPORT_GROUP_STR.lstrip('-').isdigit():
    logger.error('SUPPORT_GROUP is missing or invalid, exiting now')
    exit(1)
SUPPORT_GROUP = int(SUPPORT_GROUP_STR)

# Bin Channel (Stream Features के लिए ज़रूरी)
BIN_CHANNEL_STR = environ.get("BIN_CHANNEL", "")
if not BIN_CHANNEL_STR.lstrip('-').isdigit():
    logger.error('BIN_CHANNEL is missing or invalid, exiting now')
    exit(1)
BIN_CHANNEL = int(BIN_CHANNEL_STR)

# Server URL (Stream के लिए)
URL = environ.get("URL", "")
if len(URL) == 0:
    logger.error('URL is missing, exiting now')
    exit(1)
else:
    if URL.startswith(('https://', 'http://')):
        if not URL.endswith("/"):
            URL += '/'
    elif is_valid_ip(URL):
        URL = f'http://{URL}/'
    else:
        logger.error('URL is not valid, exiting now')
        exit(1)

# ==============================================================================
# OPTIONAL VARIABLES (वैकल्पिक वैरिएबल्स - Default values set)
# ==============================================================================

PORT = int(environ.get('PORT', '8080'))

# Databases
SECOND_FILES_DATABASE_URL = environ.get('SECOND_FILES_DATABASE_URL', "")
if len(SECOND_FILES_DATABASE_URL) == 0:
    logger.info('SECOND_FILES_DATABASE_URL is empty, using single DB')

DATABASE_NAME = environ.get('DATABASE_NAME', "Cluster0")
COLLECTION_NAME = environ.get('COLLECTION_NAME', 'Files')

# Channels
INDEX_CHANNELS = [int(ch) if ch.lstrip('-').isdigit() else ch for ch in environ.get('INDEX_CHANNELS', '').split()]
if len(INDEX_CHANNELS) == 0:
    logger.info('INDEX_CHANNELS is empty')

# Links
SUPPORT_LINK = environ.get('SUPPORT_LINK', 'https://t.me/YourXCloud')
UPDATES_LINK = environ.get('UPDATES_LINK', 'https://t.me/YourXFiles')
FILMS_LINK = environ.get('FILMS_LINK', 'https://t.me/YourX')
TUTORIAL = environ.get("TUTORIAL", "https://t.me/YourX")
VERIFY_TUTORIAL = environ.get("VERIFY_TUTORIAL", "https://t.me/YourX")

# Images
PICS = environ.get('PICS', 'https://i.postimg.cc/8C15CQ5y/1.png https://i.postimg.cc/gcNtrv0m/2.png').split()

# Settings
TIME_ZONE = environ.get('TIME_ZONE', 'Asia/Kolkata')
DELETE_TIME = int(environ.get('DELETE_TIME', 3600))
CACHE_TIME = int(environ.get('CACHE_TIME', 300))
MAX_BTN = int(environ.get('MAX_BTN', 8))
VERIFY_EXPIRE = int(environ.get('VERIFY_EXPIRE', 86400))
PM_FILE_DELETE_TIME = int(environ.get('PM_FILE_DELETE_TIME', '3600'))

# Shortlink
SHORTLINK_URL = environ.get("SHORTLINK_URL", "mdiskshortner.link")
SHORTLINK_API = environ.get("SHORTLINK_API", "your_api_key_here")

# Templates
IMDB_TEMPLATE = environ.get("IMDB_TEMPLATE", script.IMDB_TEMPLATE)
FILE_CAPTION = environ.get("FILE_CAPTION", script.FILE_CAPTION)
WELCOME_TEXT = environ.get("WELCOME_TEXT", script.WELCOME_TEXT)

# Booleans (Switches)
USE_CAPTION_FILTER = is_enabled('USE_CAPTION_FILTER', True)
IS_VERIFY = is_enabled('IS_VERIFY', True)
AUTO_DELETE = is_enabled('AUTO_DELETE', False)
WELCOME = is_enabled('WELCOME', False)
PROTECT_CONTENT = is_enabled('PROTECT_CONTENT', True)
LONG_IMDB_DESCRIPTION = is_enabled("LONG_IMDB_DESCRIPTION", False)
LINK_MODE = is_enabled("LINK_MODE", True)
IMDB = is_enabled('IMDB', False)
SPELL_CHECK = is_enabled("SPELL_CHECK", True)
SHORTLINK = is_enabled('SHORTLINK', True)
IS_STREAM = is_enabled('IS_STREAM', True)

# Languages & Quality
LANGUAGES = [lang.lower() for lang in environ.get('LANGUAGES', 'hindi english telugu tamil kannada malayalam marathi punjabi').split()]
QUALITY = [quality.lower() for quality in environ.get('QUALITY', '360p 480p 720p 1080p 1440p 2160p').split()]

# Stickers & Reactions
REACTIONS = [reactions for reactions in environ.get('REACTIONS', '🤝 😇 🤗 😍 👍 🎅 😐 🥰 🤩 😱 🤣 😘 👏 😛 😈 🎉 ⚡️ 🫡 🤓 😎 🏆 🔥 🤭 🌚 🆒 👻 😁').split()]
STICKERS = [sticker for sticker in environ.get('STICKERS', 'CAACAgIAAxkBAAEN4ctnu1NdZUe21tiqF1CjLCZW8rJ28QACmQwAAj9UAUrPkwx5a8EilDYE').split()]

# Premium
IS_PREMIUM = is_enabled('IS_PREMIUM', True)
PRE_DAY_AMOUNT = int(environ.get('PRE_DAY_AMOUNT', '10'))
UPI_ID = environ.get("UPI_ID", "YourX@SBI")
UPI_NAME = environ.get("UPI_NAME", "VIP")
RECEIPT_SEND_USERNAME = environ.get("RECEIPT_SEND_USERNAME", "@YourX")

if len(UPI_ID) == 0 or len(UPI_NAME) == 0:
    logger.info('IS_PREMIUM disabled due to empty UPI_ID or UPI_NAME')
    IS_PREMIUM = False
