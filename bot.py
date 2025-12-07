import logging
import os
import time
import asyncio
import uvloop
from hydrogram import types
from hydrogram import Client
from hydrogram.errors import FloodWait, MessageNotModified
from aiohttp import web
from typing import Union, Optional, AsyncGenerator
# 'web' फ़ोल्डर से web_app इम्पोर्ट करें
from web import web_app 
# सुनिश्चित करें कि ये वैरिएबल्स os.environ से आ रहे हैं (info.py में)
from info import (
    LOG_CHANNEL, API_ID, DATA_DATABASE_URL, 
    API_HASH, BOT_TOKEN, PORT, FILES_DATABASE_URL
) 
from utils import temp, check_premium
from database.users_chats_db import db
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# लॉगिंग सेटअप
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logging.getLogger('hydrogram').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

uvloop.install()

class Bot(Client):
    def __init__(self):
        super().__init__(
            name='Auto_Filter_Bot',
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"}
        )
        self.db_client = None # MongoDB client instance
        self.files_db_client = None

    async def start(self):
        await super().start()
        temp.START_TIME = time.time()
        
        # --- 1. MongoDB Connection Setup ---
        try:
            self.db_client = MongoClient(DATA_DATABASE_URL, server_api=ServerApi('1'))
            if FILES_DATABASE_URL and FILES_DATABASE_URL != DATA_DATABASE_URL:
                 self.files_db_client = MongoClient(FILES_DATABASE_URL, server_api=ServerApi('1'))
            
            self.db_client.admin.command('ping')
            if self.files_db_client:
                self.files_db_client.admin.command('ping')
            logger.info("MongoDB Connection Successful.")
        except Exception as e:
            logger.error(f"MongoDB Connection Error. Exiting now: {e}")
            exit()
            
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats

        # --- 2. Restart Message Handling ---
        if os.path.exists('restart.txt'):
            with open("restart.txt") as file:
                chat_id, msg_id = map(int, file)
            try:
                await self.edit_message_text(
                    chat_id=chat_id, 
                    message_id=msg_id, 
                    text='**✅ Successfully Restarted!**'
                )
            except (FloodWait, MessageNotModified) as e:
                logger.warning(f"Failed to edit restart message due to: {e}")
            except Exception:
                pass # अन्य त्रुटियों को नजरअंदाज करें
            os.remove('restart.txt')

        temp.BOT = self
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        
        # --- 3. Web Server & Background Tasks ---
        app_runner = web.AppRunner(web_app)
        await app_runner.setup()
        await web.TCPSite(app_runner, "0.0.0.0", PORT).start()

        asyncio.create_task(self.run_background_tasks())

        try:
            await self.send_message(
                chat_id=LOG_CHANNEL, 
                text=f"<b>{me.mention} Restarted! 🤖</b>"
            )
        except Exception as e:
            logger.error(f"Make sure bot admin in LOG_CHANNEL. Exiting now: {e}")
            exit()
            
        logger.info(f"@{me.username} is started now ✓")

    async def stop(self, *args):
        if self.db_client:
            self.db_client.close()
        if self.files_db_client:
             self.files_db_client.close()
        logger.info("MongoDB connection closed.")
        await super().stop()
        logger.info("Bot Stopped! Bye...")
        
    async def run_background_tasks(self):
        """सभी बैकग्राउंड कार्यों को चलाने के लिए सुरक्षित रैपर।"""
        try:
            await check_premium(self)
        except Exception as e:
            logger.error(f"Premium check task failed: {e}")

# --- कस्टम iter_messages को हटा दिया गया है ---

app = Bot()
app.run()
