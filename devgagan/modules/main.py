# ---------------------------------------------------
# File Name: main.py
# Description: Fully Dynamic Subject Auto-Grouping & Clickable Links
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

# ટાઇટલમાંથી વિષયનું નામ ઓટોમેટિક અલગ કાઢવું
def extract_clean_subject(text: str) -> str:
    if not text:
        return "અન્ય વિડિયો"
    
    first_line = text.strip().split("\n")[0]
    # બિનજરૂરી ચિહ્નો સાફ કરવા
    clean_line = re.sub(r'https?://\S+|www\.\S+|@\S+', '', first_line).strip()
    
    # વિષય અને ચેપ્ટરને અલગ પાડવા માટે વિભાજક (| , - , _ , :)
    delimiters = ['|', ':', '-', '—', '_', '•']
    for d in delimiters:
        if d in clean_line:
            part = clean_line.split(d)[0].strip()
            if len(part) >= 3:
                return part[:35]
                
    # જો કોઈ ચિહ્ન ન હોય તો શરૂઆતના થોડા શબ્દો વિષય બનશે
    words = clean_line.split()
    if len(words) > 4:
        return " ".join(words[:4])
    return clean_line[:35] if clean_line else "અન્ય વિડિયો"

# કોઈપણ નવો વિષય આવે તો તેને ઓટોમેટિક કેટેગરીમાં ઉમેરવું
async def classify_and_record_link(userbot, link, user_id, start_msg_id, summary_tracker):
    try:
        chat, msg_id = None, None
        clean_link = link.split("?single")[0]
        if 't.me/c/' in clean_link:
            parts = clean_link.split("/")
            chat = int('-100' + parts[parts.index('c') + 1])
            msg_id = int(parts[-1])
        elif 't.me/b/' in clean_link:
            parts = clean_link.split("/")
            chat = parts[-2]
            msg_id = int(parts[-1])
        elif 't.me/' in clean_link:
            parts = clean_link.split("t.me/")[1].split("/")
            chat = parts[0]
            msg_id = int(parts[1])

        raw_title = ""
        client_to_use = userbot if userbot else app
        msg = await client_to_use.get_messages(chat, msg_id)
        if msg:
            if msg.caption:
                raw_title = msg.caption
            elif msg.text:
                raw_title = msg.text
            elif msg.video and msg.video.file_name:
                raw_title = msg.video.file_name
            elif msg.document and msg.document.file_name:
                raw_title = msg.document.file_name

        # ઓટોમેટિક વિષય નક્કી થશે
        subject_name = extract_clean_subject(raw_title)
        target_jump_url = f"https://t.me/c/{str(user_id).replace('-100', '')}/{start_msg_id}"

        if subject_name not in summary_tracker:
            summary_tracker[subject_name] = []
        summary_tracker[subject_name].append(target_jump_url)
    except Exception:
        pass

# બેચ પૂરી થયે બધા જ અલગ-અલગ વિષયોનું ક્લિકેબલ લિસ્ટ
async def send_clickable_summary(client, user_id, summary_tracker, total_count):
    if not summary_tracker:
        await client.send_message(user_id, f"🎉 **બેચ સફળતાપૂર્વક પૂર્ણ થઈ ગઈ છે!** (કુલ: {total_count})")
        return

    text = "📊 **બેચ સમરી (Batch Summary)**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"

    # દરેક વિષય લિસ્ટમાં ઓટોમેટિક ગોઠવાઈ જશે
    for subject, links in summary_tracker.items():
        if links:
            count = len(links)
            first_url = links[0]
            text += f"🔹 [{subject} ({count} વિડિયો)]({first_url}) 👈 અહીં દબાવો\n"

    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += f"✅ **કુલ અપલોડ થયેલ વિડિયો:** `{total_count}`\n"
    text += "💡 *જે વિષય પર જવું હોય તેના બ્લુ અક્ષર પર ક્લિક કરો.*"

    await client.send_message(user_id, text, disable_web_page_preview=True)

async def process_and_upload_link(userbot, user_id, msg_id, link, retry_count, message):
    try:
        await get_msg(userbot, user_id, msg_id, link, retry_count, message)
        await asyncio.sleep(15)
    finally:
        pass

async def check_interval(user_id, freecheck):
    if freecheck != 1 or await is_user_verified(user_id):
        return True, None

    now = datetime.now()
    if user_id in interval_set:
        cooldown_end = interval_set[user_id]
        if now < cooldown_end:
            remaining_time = (cooldown_end - now).seconds
            return False, f"Please wait {remaining_time} seconds(s) before sending another link. Alternatively, purchase premium for instant access.\n\n> Hey 👋 You can use /token to use the bot free for 3 hours without any time limit."
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
        await message.reply(
            "You already have an ongoing process. Please wait for it to finish or cancel it with /cancel."
        )
        return

    if await chk_user(message, user_id) == 1 and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID and not await is_user_verified(user_id):
        await message.reply("Freemium service is currently not available. Upgrade to premium for access.")
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
            
    except FloodWait as fw:
        await msg.edit_text(f'Try again after {fw.x} seconds due to floodwait from Telegram.')
    except Exception as e:
        await msg.edit_text(f"Link: `{link}`\n\n**Error:** {str(e)}")
    finally:
        users_loop[user_id] = False
        if userbot:
            await userbot.stop()
        try:
            await msg.delete()
        except Exception:
            pass

async def initialize_userbot(user_id):
    data = await db.get_data(user_id)
    if data and data.get("session"):
        try:
            device = 'iPhone 16 Pro'
            userbot = Client(
                "userbot",
                api_id=API_ID,
                api_hash=API_HASH,
                device_model=device,
                session_string=data.get("session")
            )
            await userbot.start()
            return userbot
        except Exception:
            return None
    return None

async def is_normal_tg_link(link: str) -> bool:
    special_identifiers = ['t.me/+', 't.me/c/', 't.me/b/', 'tg://openmessage']
    return 't.me/' in link and not any(x in link for x in special_identifiers)
    
async def process_special_links(userbot, user_id, msg, link):
    if 't.me/+' in link:
        result = await userbot_join(userbot, link)
        await msg.edit_text(result)
    elif any(sub in link for sub in ['t.me/c/', 't.me/b/', '/s/', 'tg://openmessage']):
        await process_and_upload_link(userbot, user_id, msg.id, link, 0, msg)
        await set_interval(user_id, interval_minutes=45)
    else:
        await msg.edit_text("Invalid link format.")

@app.on_message(filters.command("batch") & filters.private)
async def batch_link(_, message):
    join = await subscribe(_, message)
    if join == 1:
        return
    user_id = message.chat.id

    if users_loop.get(user_id, False):
        await app.send_message(
            message.chat.id,
            "You already have a batch process running. Please wait for it to complete."
        )
        return

    freecheck = await chk_user(message, user_id)
    if freecheck == 1 and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID and not await is_user_verified(user_id):
        await message.reply("Freemium service is currently not available. Upgrade to premium for access.")
        return

    max_batch_size = PREMIUM_LIMIT if (freecheck != 1 or user_id in OWNER_ID) else (30 if await is_user_verified(user_id) else FREEMIUM_LIMIT)
        
    for attempt in range(3):
        await app.send_photo(
            message.chat.id,
            photo="https://i.postimg.cc/BXkchVpY/image.jpg",
            caption="Just Copy Post Link And Send it To Me.\n\nજ્યાંથી શરૂ કરવું હોય તે પોસ્ટની લિંક મોકલો\n\nMake sure the link is correct!"
        )
        start = await app.ask(message.chat.id, "🎯 Send The Link For Where I Need To Start Process From \n\n> You Have Only 3 Tries")
        start_id = start.text.strip()
        s = start_id.split("/")[-1]
        if s.isdigit():
            cs = int(s)
            break
        await app.send_message(message.chat.id, "Invalid link. Please send again ...")
    else:
        await app.send_message(message.chat.id, "Maximum attempts exceeded. Try later.")
        return

    for attempt in range(3):
        num_messages = await app.ask(message.chat.id, f"How many messages do you want to process? 🌝\n> Max limit {max_batch_size}")
        try:
            cl = int(num_messages.text.strip())
            if 1 <= cl <= max_batch_size:
                break
            raise ValueError()
        except ValueError:
            await app.send_message(
                message.chat.id, 
                f"Invalid number. Please enter a number between 1 and {max_batch_size}."
            )
    else:
        await app.send_message(message.chat.id, "Maximum attempts exceeded. Try later.")
        return

    can_proceed, response_message = await check_interval(user_id, freecheck)
    if not can_proceed:
        await message.reply(response_message)
        return
        
    join_button = InlineKeyboardButton("Join Channel", url="https://t.me/SRC_PRO")
    keyboard = InlineKeyboardMarkup([[join_button]])
    pin_msg = await app.send_message(
        user_id,
        f"Batch process started ⚡\nProcessing: 0/{cl}\n\n**Powered By ╰‿╯ ҡσℓเ ⚝**",
        reply_markup=keyboard
    )
    await pin_msg.pin(both_sides=True)

    users_loop[user_id] = True

    # ઑટોમેટિક સમરી ટ્રેકર (બધા જ વિષયો માટે)
    summary_tracker = {}

    try:
        normal_links_handled = False
        userbot = await initialize_userbot(user_id)

        # Normal Links
        for i in range(cs, cs + cl):
            if user_id in users_loop and users_loop[user_id]:
                url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
                link = get_link(url)
                if 't.me/' in link and not any(x in link for x in ['t.me/b/', 't.me/c/', 'tg://openmessage']):
                    msg = await app.send_message(message.chat.id, f"Processing...")
                    await classify_and_record_link(userbot, link, user_id, msg.id, summary_tracker)
                    await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
                    try:
                        await pin_msg.edit_text(
                            f"Batch process started ⚡\nProcessing: {i - cs + 1}/{cl}\n\n**__Powered By ╰‿╯ ҡσℓเ ⚝__**",
                            reply_markup=keyboard
                        )
                    except MessageNotModified:
                        pass
                    except FloodWait as fw:
                        await asyncio.sleep(fw.value)
                    except Exception:
                        pass
                    normal_links_handled = True

        if normal_links_handled:
            await set_interval(user_id, interval_minutes=300)
            try:
                await pin_msg.edit_text(
                    f"Batch completed successfully for {cl} messages 🎉\n\n**__Powered By ╰‿╯ ҡσℓเ ⚝__**",
                    reply_markup=keyboard
                )
            except Exception:
                pass
            await send_clickable_summary(app, user_id, summary_tracker, cl)
            return
            
        # Special Links (t.me/c/ etc.)
        for i in range(cs, cs + cl):
            if not userbot:
                await app.send_message(message.chat.id, "Login in bot first ...")
                users_loop[user_id] = False
                return
            if user_id in users_loop and users_loop[user_id]:
                url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
                link = get_link(url)
                if any(x in link for x in ['t.me/b/', 't.me/c/']):
                    msg = await app.send_message(message.chat.id, f"Processing...")
                    await classify_and_record_link(userbot, link, user_id, msg.id, summary_tracker)
                    await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
                    try:
                        await pin_msg.edit_text(
                            f"Batch process started ⚡\nProcessing: {i - cs + 1}/{cl}\n\n**__Powered By ╰‿╯ ҡσℓเ ⚝__**",
                            reply_markup=keyboard
                        )
                    except MessageNotModified:
                        pass
                    except FloodWait as fw:
                        await asyncio.sleep(fw.value)
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

        # છેલ્લે દરેક વિષયની ક્લિકેબલ લિંક્સ સાથેનો સમરી મેસેજ
        await send_clickable_summary(app, user_id, summary_tracker, cl)

    except Exception as e:
        await app.send_message(message.chat.id, f"Error: {e}")
    finally:
        users_loop.pop(user_id, None)

@app.on_message(filters.command("cancel"))
async def stop_batch(_, message):
    user_id = message.chat.id

    if user_id in users_loop and users_loop[user_id]:
        users_loop[user_id] = False
        await app.send_message(
            message.chat.id, 
            "Batch processing has been stopped successfully. You can start a new batch now if you want."
        )
    elif user_id in users_loop and not users_loop[user_id]:
        await app.send_message(
            message.chat.id, 
            "The batch process was already stopped. No active batch to cancel."
        )
    else:
        await app.send_message(
            message.chat.id, 
            "No active batch processing is running to cancel."
    )
                    
