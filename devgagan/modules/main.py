# ---------------------------------------------------
# File Name: main.py
# Description: Exact Topic Summary with Video/PDF count & Channel links
# Author: Gagan | Mod for: ╰‿╯ ҡσℓเ ⚝
# ---------------------------------------------------

import time
import random
import string
import asyncio
import re
from pyrogram import filters, Client
from devgagan import app
from config import API_ID, API_HASH, FREEMIUM_LIMIT, PREMIUM_LIMIT, OWNER_ID
from devgagan.core.get_func import get_msg
from devgagan.core.func import *
from devgagan.core.mongo import db
from pyrogram.errors import FloodWait, MessageNotModified
from datetime import datetime, timedelta
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from devgagan.modules.shrink import is_user_verified

async def generate_random_name(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

users_loop = {}
interval_set = {}
batch_mode = {}

# Caption/Text mathi Topic Name kadvu
def parse_topic_name(raw_text: str) -> str:
    if not raw_text:
        return "General Topic"
    
    # Batch Name athva Topic Name line shodho
    for line in raw_text.split("\n"):
        line_clean = line.strip()
        if "topic name" in line_clean.lower():
            t = re.sub(r'(?i)topic name\s*[:\-\—]*', '', line_clean).strip()
            if t and t.lower() != "topic":
                return t
        if "batch name" in line_clean.lower():
            b = re.sub(r'(?i)batch name\s*[:\-\—]*', '', line_clean).strip()
            b = re.sub(r'\(.*?\)', '', b).strip()
            if b:
                return b

    # Subject Keywords Check
    t_lower = raw_text.lower()
    subject_map = [
        (["રીઝનીંગ", "reasoning"], "રીઝનીંગ"),
        (["રોડ સેફટી", "road safety"], "રોડ સેફટી"),
        (["ગુજરાતી વ્યાકરણ", "vyakaran"], "ગુજરાતી વ્યાકરણ"),
        (["ગુજરાતી સાહિત્ય", "sahitya"], "ગુજરાતી સાહિત્ય"),
        (["ગણિત", "maths", "math"], "ગણિત"),
        (["કોમ્પ્યુટર", "computer"], "કોમ્પ્યુટર"),
        (["અંગ્રેજી", "english"], "અંગ્રેજી"),
        (["ઇતિહાસ", "history"], "ઇતિહાસ"),
        (["ભૂગોળ", "geography"], "ભૂગોળ"),
        (["બંધારણ", "polity"], "બંધારણ"),
        (["વિજ્ઞાન", "science"], "વિજ્ઞાન"),
        (["કાયદો", "law"], "કાયદો"),
        (["સામાન્ય જ્ઞાન", "gk"], "સામાન્ય જ્ઞાન"),
        (["કંડક્ટર", "ડ્રાઈવર"], "કંડક્ટર સ્પેશિયલ")
    ]
    for kws, name in subject_map:
        for kw in kws:
            if kw in t_lower:
                return name

    # Default Clean Header
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    if lines:
        c = re.sub(r'https?://\S+|@\S+', '', lines[0])
        c = re.sub(r'(\.pdf|\.mkv|\.mp4)', '', c, flags=re.IGNORECASE).strip()
        return c[:35]
    return "General Topic"

# Channel mathi real message track karvu
async def track_channel_upload(summary_data, target_chat_id, user_id):
    try:
        dest_chat = target_chat_id if target_chat_id else user_id
        await asyncio.sleep(2)
        
        async for m in app.get_chat_history(dest_chat, limit=1):
            text = m.caption or m.text or ""
            topic = parse_topic_name(text)

            is_video = bool(m.video or (m.document and "video" in str(m.document.mime_type)))
            is_pdf = bool(m.document and (m.document.file_name.endswith('.pdf') if m.document.file_name else False))

            cid_str = str(dest_chat).replace("-100", "")
            jump_url = f"https://t.me/c/{cid_str}/{m.id}"

            if topic not in summary_data:
                summary_data[topic] = {
                    "url": jump_url,
                    "videos": 0,
                    "pdfs": 0,
                    "others": 0
                }
            
            if is_video:
                summary_data[topic]["videos"] += 1
            elif is_pdf:
                summary_data[topic]["pdfs"] += 1
            else:
                summary_data[topic]["others"] += 1
            break
    except Exception as e:
        print(f"Tracking error: {e}")

# Exact photo jevi summary mokalvi
async def send_pinned_topic_summary(client, user_id, summary_data, target_chat_id):
    if not summary_data:
        return

    summary_text = "📌 **Topic Summary**\n\n"
    
    for topic, stats in summary_data.items():
        url = stats["url"]
        v_count = stats["videos"]
        p_count = stats["pdfs"]
        
        # Link sathe Topic Name ane 🎥 / 📄 counts
        summary_text += f"- [{topic}]({url}) 🎥 {v_count} | 📄 {p_count}\n\n"

    summary_text += "━━━━━━━━━━━━━━━━━━━━\n"
    summary_text += "**__Powered By ╰‿╯ ҡσℓเ ⚝__**"

    # 1. Target Channel ma mokalvu ane pin karvu
    if target_chat_id:
        try:
            ch_msg = await client.send_message(target_chat_id, summary_text, disable_web_page_preview=True)
            try:
                await ch_msg.pin(both_sides=True)
            except Exception:
                pass
        except Exception as e:
            print(f"Error sending to channel: {e}")

    # 2. Bot ma user ne mokalvu
    try:
        user_msg = await client.send_message(user_id, summary_text, disable_web_page_preview=True)
        try:
            await user_msg.pin(both_sides=True)
        except Exception:
            pass
    except Exception as e:
        print(f"Error sending to user: {e}")

async def process_and_upload_link(userbot, user_id, msg_id, link, retry_count, message):
    try:
        await get_msg(userbot, user_id, msg_id, link, retry_count, message)
        await asyncio.sleep(4)
    except Exception as e:
        print(f"Error: {e}")

async def check_interval(user_id, freecheck):
    if freecheck != 1 or await is_user_verified(user_id):
        return True, None

    now = datetime.now()
    if user_id in interval_set:
        cooldown_end = interval_set[user_id]
        if now < cooldown_end:
            remaining_time = (cooldown_end - now).seconds
            return False, f"Please wait {remaining_time} seconds(s) before sending another link.\n\n> Hey 👋 You can use /token to use the bot free for 3 hours."
        else:
            del interval_set[user_id]

    return True, None

async def set_interval(user_id, interval_minutes=45):
    now = datetime.now()
    interval_set[user_id] = now + timedelta(seconds=interval_minutes)

@app.on_message(
    filters.regex(r'https?://(?:www\.)?t\.me/[^\s]+|tg://openmessage\?user_id=\w+&message_id=\d+')
    & filters.private
)
async def single_link(_, message):
    user_id = message.chat.id

    if await subscribe(_, message) == 1 or user_id in batch_mode:
        return

    if users_loop.get(user_id, False):
        await message.reply("You already have an ongoing process. Please wait or use /cancel.")
        return

    if await chk_user(message, user_id) == 1 and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID and not await is_user_verified(user_id):
        await message.reply("Freemium service is not available.")
        return

    can_proceed, response_message = await check_interval(user_id, await chk_user(message, user_id))
    if not can_proceed:
        await message.reply(response_message)
        return

    users_loop[user_id] = True
    link = message.text if "tg://openmessage" in message.text else get_link(message.text)
    msg = await message.reply("Processing...")
    userbot = await initialize_userbot(user_id)

    try:
        if await is_normal_tg_link(link):
            await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
            await set_interval(user_id, interval_minutes=45)
        else:
            await process_special_links(userbot, user_id, msg, link)
    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}")
    finally:
        users_loop[user_id] = False
        if userbot:
            try:
                await userbot.stop()
            except Exception:
                pass
        try:
            await msg.delete()
        except Exception:
            pass

async def initialize_userbot(user_id):
    data = await db.get_data(user_id)
    if data and data.get("session"):
        try:
            device = 'iPhone 16 Pro'
            ub = Client(
                "userbot",
                api_id=API_ID,
                api_hash=API_HASH,
                device_model=device,
                session_string=data.get("session")
            )
            await ub.start()
            return ub
        except Exception as e:
            print(f"Userbot error: {e}")
            return None
    return None

async def is_normal_tg_link(link: str) -> bool:
    return 't.me/' in link and not any(x in link for x in ['t.me/+', 't.me/c/', 't.me/b/', 'tg://openmessage'])
    
async def process_special_links(userbot, user_id, msg, link):
    if 't.me/+' in link:
        await msg.edit_text(await userbot_join(userbot, link))
    elif any(sub in link for sub in ['t.me/c/', 't.me/b/', '/s/', 'tg://openmessage']):
        await process_and_upload_link(userbot, user_id, msg.id, link, 0, msg)
        await set_interval(user_id, interval_minutes=45)

@app.on_message(filters.command("batch") & filters.private)
async def batch_link(_, message):
    if await subscribe(_, message) == 1:
        return
    user_id = message.chat.id

    if users_loop.get(user_id, False):
        return await app.send_message(message.chat.id, "Batch process already running.")

    freecheck = await chk_user(message, user_id)
    max_batch_size = PREMIUM_LIMIT if (freecheck != 1 or user_id in OWNER_ID) else (30 if await is_user_verified(user_id) else FREEMIUM_LIMIT)
        
    for _ in range(3):
        await app.send_photo(message.chat.id, photo="https://i.postimg.cc/BXkchVpY/image.jpg", caption="Just Copy Post Link And Send it To Me.\n\nજ્યાંથી શરૂ કરવું હોય તે પોસ્ટની લિંક મોકલો:")
        start = await app.ask(message.chat.id, "🎯 Send The Link For Where I Need To Start Process From \n\n> You Have Only 3 Tries")
        start_id = start.text.strip()
        if start_id.split("/")[-1].isdigit():
            cs = int(start_id.split("/")[-1])
            break
    else:
        return await app.send_message(message.chat.id, "Maximum attempts exceeded.")

    for _ in range(3):
        num_messages = await app.ask(message.chat.id, f"How many messages do you want to process? 🌝\n> Max limit {max_batch_size}")
        try:
            cl = int(num_messages.text.strip())
            if 1 <= cl <= max_batch_size:
                break
        except ValueError:
            pass
    else:
        return await app.send_message(message.chat.id, "Invalid number.")

    join_button = InlineKeyboardButton("Join Channel", url="https://t.me/SRC_PRO")
    keyboard = InlineKeyboardMarkup([[join_button]])
    
    pin_msg = await app.send_message(
        user_id,
        f"Batch process started ⚡\nProcessing: 0/{cl}\n\n**Powered By ╰‿╯ ҡσℓเ ⚝**",
        reply_markup=keyboard
    )
    try:
        await pin_msg.pin(both_sides=True)
    except Exception:
        pass
    users_loop[user_id] = True

    # Chat ID fetch karo
    target_chat_id = None
    try:
        user_settings = await db.get_data(user_id)
        if user_settings:
            raw_cid = user_settings.get("chat_id")
            if raw_cid:
                target_chat_id = int(str(raw_cid).strip())
    except Exception as e:
        print(f"Target fetch error: {e}")

    summary_data = {}

    try:
        userbot = await initialize_userbot(user_id)

        for i in range(cs, cs + cl):
            if not users_loop.get(user_id, False):
                break

            url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
            link = get_link(url)

            if any(x in link for x in ['t.me/b/', 't.me/c/']) and not userbot:
                await app.send_message(message.chat.id, "⚠️ આ પ્રાઈવેટ ચેનલ છે! કૃપા કરીને પહેલા /login કરો.")
                break

            msg = await app.send_message(message.chat.id, "Processing...")
            await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
            
            # Channel ma upload thaya pachhi exact track karo
            await track_channel_upload(summary_data, target_chat_id, user_id)
            
            try:
                await pin_msg.edit_text(
                    f"Batch process started ⚡\nProcessing: {i - cs + 1}/{cl}\n\n**__Powered By ╰‿╯ ҡσℓเ ⚝__**",
                    reply_markup=keyboard
                )
            except Exception:
                pass

        await set_interval(user_id, interval_minutes=300)
        try:
            await pin_msg.edit_text(
                f"Batch completed successfully for {cl} messages 🎉\n\n**__Powered By ╰‿╯ ҡσℓเ ⚝__**",
                reply_markup=keyboard
            )
        except Exception:
            pass

        # Pinned Topic Summary format send karo
        await send_pinned_topic_summary(app, user_id, summary_data, target_chat_id)

    except Exception as e:
        await app.send_message(message.chat.id, f"Error: {e}")
    finally:
        users_loop.pop(user_id, None)
        if userbot:
            try:
                await userbot.stop()
            except Exception:
                pass

@app.on_message(filters.command("cancel"))
async def stop_batch(_, message):
    user_id = message.chat.id
    if user_id in users_loop and users_loop[user_id]:
        users_loop[user_id] = False
        await app.send_message(message.chat.id, "Batch processing has been stopped successfully.")
    else:
        await app.send_message(message.chat.id, "No active batch running.")
        
