import sys
import glob
import importlib
import logging
import logging.config
import asyncio
import platform
from pathlib import Path
from time import time
from datetime import datetime, timezone
import pytz
from aiohttp import web
from hydrogram import Client, idle, __version__ as hydro_ver
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Local Imports
from info import API_ID, API_HASH, BOT_TOKEN, PORT, LOG_CHANNEL, TIME_ZONE, ADMINS
from utils import temp
from Script import script
from web import web_app
from database.users_chats_db import db

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("hydrogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="FastFinderBot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=10,
        )

    async def start(self):
        # Set Start Time
        temp.START_TIME = time()
        temp.BOT = self 
        
        # Load Banned Users/Chats
        try:
            b_users, b_chats = await db.get_banned()
            temp.BANNED_USERS = b_users
            temp.BANNED_CHATS = b_chats
        except Exception as e:
            logging.error(f"Error loading banned list: {e}")

        # Start Client
        await super().start()
        me = await self.get_me()
        
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        temp.B_ID = me.id
        
        # Start Web Server
        app = web.AppRunner(web_app)
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()
        logging.info(f"Web Server Started on Port {PORT}")
        logging.info(f"@{me.username} Started Successfully! 🚀")
        
        # Start Premium Expiry Checker Task
        self.loop.create_task(self.check_premium_expiry())

        # --- SMART STARTUP LOG ---
        try:
            tz = pytz.timezone(TIME_ZONE)
            now = datetime.now(tz)
            date_str = now.strftime("%d %b %Y")
            time_str = now.strftime("%I:%M %p")
        except:
            date_str = "Unknown"
            time_str = "Unknown"

        if LOG_CHANNEL:
            try:
                txt = (
                    f"<b>🚀 Bᴏᴛ Sᴛᴀʀᴛᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n\n"
                    f"<b>🤖 Bᴏᴛ:</b> @{me.username}\n"
                    f"<b>🐍 Pʏᴛʜᴏɴ:</b> <code>{platform.python_version()}</code>\n"
                    f"<b>📡 Hʏᴅʀᴏɢʀᴀᴍ:</b> <code>{hydro_ver}</code>\n"
                    f"<b>📅 Dᴀᴛᴇ:</b> <code>{date_str}</code>\n"
                    f"<b>⌚ Tɪᴍᴇ:</b> <code>{time_str}</code>"
                )
                await self.send_message(chat_id=LOG_CHANNEL, text=txt)
            except Exception as e:
                logging.error(f"Failed to send log: {e}")

        if ADMINS:
            for admin_id in ADMINS:
                try:
                    await self.send_message(
                        chat_id=admin_id,
                        text=f"<b>✅ {me.mention} is now Online!</b>\n📅 <code>{date_str} • {time_str}</code>"
                    )
                except:
                    pass

    async def stop(self, *args):
        await super().stop()
        logging.info("Bot Stopped. Bye!")

    # --- PREMIUM EXPIRY CHECKER TASK ---
    async def check_premium_expiry(self):
        logging.info("Premium Expiry Checker Started...")
        while True:
            try:
                async for user in await db.get_premium_users():
                    try:
                        user_id = user['id']
                        plan_status = user.get('status', {})
                        expiry_date = plan_status.get('expire')
                        
                        if not plan_status.get('premium') or not isinstance(expiry_date, datetime):
                            continue
                        
                        # Fix Timezone Offset
                        if expiry_date.tzinfo is None:
                            expiry_date = expiry_date.replace(tzinfo=timezone.utc)

                        now = datetime.now(timezone.utc)
                        delta = expiry_date - now
                        seconds = delta.total_seconds()
                        
                        # Readable Date
                        try:
                            tz = pytz.timezone(TIME_ZONE)
                            expiry_ist = expiry_date.astimezone(tz)
                            expiry_str = expiry_ist.strftime("%d %b %Y, %I:%M %p")
                        except:
                            expiry_str = expiry_date.strftime("%d %b %Y, %I:%M %p")
                        
                        btn = InlineKeyboardMarkup([[InlineKeyboardButton("💎 Aᴄᴛɪᴠᴇ Pʟᴀɴ Nᴏᴡ", callback_data="activate_plan")]])
                        msg_text = None
                        
                        # --- REMINDER LOGIC (With Dynamic Emojis) ---
                        
                        # 12 Hours Left
                        if 43200 <= seconds < 43260:
                            msg_text = f"<b>🕛 Pʀᴇᴍɪᴜᴍ Exᴘɪʀɪɴɢ Sᴏᴏɴ!</b>\n\nYour premium plan expires in <b>12 Hours</b>.\n📅 <b>Expiry:</b> <code>{expiry_str}</code>"
                        
                        # 6 Hours Left
                        elif 21600 <= seconds < 21660:
                            msg_text = f"<b>🕕 Pʀᴇᴍɪᴜᴍ Exᴘɪʀɪɴɢ Sᴏᴏɴ!</b>\n\nYour premium plan expires in <b>6 Hours</b>.\n📅 <b>Expiry:</b> <code>{expiry_str}</code>"
                            
                        # 3 Hours Left
                        elif 10800 <= seconds < 10860:
                            msg_text = f"<b>🕒 Pʀᴇᴍɪᴜᴍ Exᴘɪʀɪɴɢ Sᴏᴏɴ!</b>\n\nYour premium plan expires in <b>3 Hours</b>.\n📅 <b>Expiry:</b> <code>{expiry_str}</code>"
                            
                        # 1 Hour Left
                        elif 3600 <= seconds < 3660:
                            msg_text = f"<b>🕐 Pʀᴇᴍɪᴜᴍ Exᴘɪʀɪɴɢ Sᴏᴏɴ!</b>\n\nYour premium plan expires in <b>1 Hour</b>.\n📅 <b>Expiry:</b> <code>{expiry_str}</code>"
                            
                        # 10 Minutes Left
                        elif 600 <= seconds < 660:
                            msg_text = f"<b>⚠️ Hᴜʀʀʏ Uᴘ!</b>\n\nYour premium plan expires in just <b>10 Minutes</b>.\n📅 <b>Expiry:</b> <code>{expiry_str}</code>"
                            
                        # Expired (<= 0)
                        elif seconds <= 0:
                            msg_text = f"<b>🚫 Pʀᴇᴍɪᴜᴍ Exᴘɪʀᴇᴅ!</b>\n\nYour plan expired on <b>{expiry_str}</b>.\n<i>Renew now to continue enjoying exclusive features.</i>"
                            # Reset in DB
                            await db.update_plan(user_id, {'expire': '', 'trial': False, 'plan': '', 'premium': False})
                        
                        if msg_text:
                            # --- AUTO DELETE OLD REMINDER ---
                            old_msg_id = temp.PREMIUM_REMINDERS.get(user_id)
                            if old_msg_id:
                                try:
                                    await self.delete_messages(user_id, old_msg_id)
                                except Exception:
                                    pass 
                            
                            # --- SEND NEW REMINDER ---
                            try:
                                sent_msg = await self.send_message(chat_id=user_id, text=msg_text, reply_markup=btn)
                                temp.PREMIUM_REMINDERS[user_id] = sent_msg.id
                                
                                # Clear cache if expired
                                if seconds <= 0:
                                    temp.PREMIUM_REMINDERS.pop(user_id, None)
                                    
                            except Exception as e:
                                logging.error(f"Could not send reminder to {user_id}: {e}")
                                
                    except Exception as e:
                        logging.error(f"Error checking user {user.get('id')}: {e}")
                        
            except Exception as e:
                logging.error(f"Error in premium checker loop: {e}")
            
            await asyncio.sleep(60)

if __name__ == "__main__":
    # --- 🔥 UVLOOP INTEGRATION (Safe Mode) ---
    if platform.system() != "Windows":
        try:
            import uvloop
            uvloop.install()
            logging.info("⚡ uvloop initialized! Bot speed increased.")
        except ImportError:
            logging.warning("⚠️ uvloop not found in requirements. Running on default asyncio.")
        except Exception as e:
            logging.error(f"⚠️ Could not install uvloop: {e}")
            
    Bot().run()
