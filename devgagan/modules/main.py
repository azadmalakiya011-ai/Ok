# ---------------------------------------------------
# File Name: main.py
# Description: Fixed Channel Summary with Subject & Direct Channel Link
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

# વિષયનું શુદ્ધ ગુજરાતી નામ શોધવું
def extract_clean_subject(text: str) -> str:
    if not text:
        return "અન્ય"

    t = text.lower()
    subject_map = [
        (["કોમ્પ્યુટર", "computer", "કોમ્પ"], "કોમ્પ્યુટર"),
        (["ગણિત", "maths", "math"], "ગણિત"),
        (["રીઝનીંગ", "reasoning"], "રીઝનીંગ"),
        (["રોડ સેફટી", "road safety", "મોટર વ્હીકલ"], "રોડ સેફટી"),
        (["ગુજરાતી વ્યાકરણ", "વ્યાકરણ", "vyakaran"], "ગુજરાતી વ્યાકરણ"),
        (["ગુજરાતી સાહિત્ય", "સાહિત્ય", "sahitya"], "ગુજરાતી સાહિત્ય"),
        (["અંગ્રેજી", "english", "ઇંગ્લિશ", "eng"], "અંગ્રેજી"),
        (["ઇતિહાસ", "history", "ઈતિહાસ"], "ઇતિહાસ"),
        (["ભૂગોળ", "geography", "ભુગોળ"], "ભૂગોળ"),
        (["બંધારણ", "polity", "constitution"], "બંધારણ"),
        (["વિજ્ઞાન", "science", "સાયન્સ"], "વિજ્ઞાન"),
        (["કાયદો", "law", "ipc", "crpc"], "કાયદો"),
        (["કરંટ", "current"], "કરંટ અફેર્સ"),
        (["પર્યાવરણ", "environment", "ફોરેસ્ટ"], "પર્યાવરણ"),
        (["સામાન્ય જ્ઞાન", "જનરલ નોલેજ", "gk", "general knowledge"], "સામાન્ય જ્ઞાન"),
        (["કંડક્ટર", "ડ્રાઈવર"], "કંડક્ટર સ્પેશિયલ")
    ]

    for keywords, name in subject_map:
        for kw in keywords:
            if kw in t:
                return name

    lines = text.strip().split("\n")
    target_line = ""
    for line in lines:
        if not any(x in line.lower() for x in ["vid id", "pdf id", "batch name", "topic name"]):
            if line.strip():
                target_line = line.strip()
                break

    if not target_line:
        target_line = lines[0].strip()

    clean = re.sub(r'https?://\S+|www\.\S+|@\S+', '', target_line)
    clean = re.sub(r'(\.pdf|\.mkv|\.mp4|\[\d+p\]|\(\d+p\))', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'(?i)\b(l|lec|lecture|class|file title|topic name|batch name)[\-_ ]*\d*\b\s*[:\-\—]*', '', clean).strip()

    for d in ['|', ':', '-', '—', '_', '•']:
        if d in clean:
            part = clean.split(d)[0].strip()
            if len(part) >= 2:
                clean = part
                break

    words = clean.split()
    if len(words) >= 2:
        return f"{words[0]} {words[1]}"
    elif len(words) == 1:
        return words[0]
    return "અન્ય"

# તમારી જ ચેનલમાંથી છેલ્લો અપલોડ થયેલો મેસેજ અને લિંક મેળવવી
async def record_own_channel_link(summary_tracker, target_chat_id, user_id):
    try:
        effective_chat = target_chat_id if target_chat_id else user_id
        await asyncio.sleep(2)  # અપલોડ પ્રોસેસ પૂરી થવા માટે ૨ સેકન્ડ થોભવું

        async for last_msg in app.get_chat_history(effective_chat, limit=1):
            raw_text = last_msg.caption or last_msg.text or ""
            if not raw_text and last_msg.video and last_msg.video.file_name:
                raw_text = last_msg.video.file_name
            elif not raw_text and last_msg.document and last_msg.document.file_name:
                raw_text = last_msg.document.file_name

            subject_name = extract_clean_subject(raw_text)

            clean_cid = str(effective_chat).replace("-100", "")
            target_jump_url = f"https://t.me/c/{clean_cid}/{last_msg.id}"

            if subject_name not in summary_tracker:
                summary_tracker[subject_name] = []
            summary_tracker[subject_name].append(target_jump_url)
            break
    except Exception as e:
        print(f"Error in tracking: {e}")

# સમરી યુઝર અને ચેનલ બંનેમાં મોકલવી
async def send_clickable_summary(client, user_id, summary_tracker, total_count, target_chat_id):
    text = "📊 **બેચ સમરી (Batch Summary)**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"

    if summary_tracker:
        for subject, links in summary_tracker.items():
            count = len(links)
            first_url = links[0]
            text += f"🔹 [{subject} ({count} ફાઇલો)]({first_url}) 👈 અહીં દબાવો\n"
    else:
        text += "🔹 [બધા વિડિયો જોવા માટે અહીં દબાવો](https://t.me) 👈\n"

    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += f"✅ **કુલ અપલોડ થયેલ ફાઇલો:** `{total_count}`\n"
    text += "💡 *જે વિષય પર જવું હોય તેના બ્લુ અક્ષર પર ક્લિક કરો.*\n\n"
    text += "**__Powered By ╰‿╯ ҡσℓเ ⚝__**"

    # ૧. ચેનલમાં સમરી મોકલવી
    if target_chat_id:
        try:
            await client.send_message(target_chat_id, text, disable_web_page_preview=True)
        except Exception as e:
            print(f"Channel Summary Send Error: {e}")

    # ૨. બોટમાં યુઝરને સમરી મોકલવી
    await client.send_message(user_id, text, disable_web_page_preview=True)

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
    await pin_msg.pin(both_sides=True)
    users_loop[user_id] = True

    # ટાર્ગેટ ચેનલ આઈડી ચોક્કસ રીતે શોધીને ઇન્ટિજરમાં ફેરવવો
    user_settings = await db.get_data(user_id)
    target_chat_id = None
    if user_settings:
        raw_cid = user_settings.get("chat_id")
        if raw_cid:
            try:
                target_chat_id = int(str(raw_cid).strip())
            except Exception:
                target_chat_id = raw_cid
    
    summary_tracker = {}

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
            
            # અપલોડ થઈ ગયેલા વિડિયોને તમારી ચેનલમાંથી જ સીધો ટ્રેક કરવો
            await record_own_channel_link(summary_tracker, target_chat_id, user_id)
            
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

        # સમરી ચેનલ અને બોટ બંનેમાં મોકલવી
        await send_clickable_summary(app, user_id, summary_tracker, cl, target_chat_id)

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
        
