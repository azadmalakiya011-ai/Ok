# ---------------------------------------------------
# File Name: main.py
# Description: Fully Restored Original Bot with Dynamic Chapter Summary & 5h Redeem
# Powered By: ╰‿╯ ҡσℓเ ⚝
# ---------------------------------------------------

import time
import random
import string
import asyncio
import re
import secrets
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

def extract_clean_subject_and_chapter(text: str) -> str:
    if not text:
        return "અન્ય ફાઇલો"
    
    lines = text.strip().split("\n")
    target_line = ""

    for line in lines:
        if "file title" in line.lower():
            target_line = re.sub(r'(?i)file\s*title\s*[:\-\—]*', '', line).strip()
            break
        elif "topic name" in line.lower() and "topic name: topic" not in line.lower():
            target_line = re.sub(r'(?i)topic\s*name\s*[:\-\—]*', '', line).strip()
            break
        elif "batch name" in line.lower():
            target_line = re.sub(r'(?i)batch\s*name\s*[:\-\—]*', '', line).strip()
            break

    if not target_line:
        for line in lines:
            if not any(x in line.lower() for x in ["pdf id", "vid id", "id :", "id:"]):
                if line.strip():
                    target_line = line.strip()
                    break

    if not target_line:
        target_line = lines[0].strip()

    clean = re.sub(r'https?://\S+|www\.\S+|@\S+', '', target_line)
    clean = re.sub(r'(\.pdf|\.mkv|\.mp4|\[\d+p\]|\(\d+p\))', '', clean, flags=re.IGNORECASE)

    delimiters = ['|', '—', '•']
    for d in delimiters:
        if d in clean:
            part = clean.split(d)[0].strip()
            if len(part) >= 3:
                clean = part
                break

    words = clean.split()
    if len(words) > 6:
        clean = " ".join(words[:6])

    return clean[:40].strip() if clean else "સામાન્ય વિષય"

async def classify_and_record_link(userbot, link, user_id, summary_tracker, target_chat_id):
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

        subject_chapter = extract_clean_subject_and_chapter(raw_title)

        effective_chat = target_chat_id if target_chat_id else user_id
        clean_cid = str(effective_chat).replace("-100", "")

        target_jump_url = None
        try:
            async for last_msg in app.get_chat_history(effective_chat, limit=1):
                target_jump_url = f"https://t.me/c/{clean_cid}/{last_msg.id}"
        except Exception:
            pass

        if subject_chapter not in summary_tracker:
            summary_tracker[subject_chapter] = []
        if target_jump_url:
            summary_tracker[subject_chapter].append(target_jump_url)
    except Exception:
        pass

async def send_clickable_summary(client, user_id, summary_tracker, total_count, target_chat_id):
    if not summary_tracker:
        await client.send_message(
            user_id, 
            f"🎉 **Batch completed successfully for {total_count} messages**\n\n**__Powered By ╰‿╯ ҡσℓเ ⚝__**"
        )
        return

    text = "📊 **બેચ સમરી (Batch Summary)**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"

    for chapter, links in summary_tracker.items():
        if links:
            count = len(links)
            first_url = links[0]
            text += f"🔹 [{chapter} ({count} ફાઇલો)]({first_url}) 👈 અહીં દબાવો\n"

    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += f"✅ **કુલ અપલોડ થયેલ ફાઇલો:** `{total_count}`\n"
    text += f"⚡ **__Powered By ╰‿╯ ҡσℓเ ⚝__**\n"
    text += "💡 *જે વિષય/ચેપ્ટર પર જવું હોય તેના બ્લુ અક્ષર પર ક્લિક કરો.*"

    if target_chat_id:
        try:
            await client.send_message(target_chat_id, text, disable_web_page_preview=True)
        except Exception:
            pass

    await client.send_message(user_id, text, disable_web_page_preview=True)

async def process_and_upload_link(userbot, user_id, msg_id, link, retry_count, message):
    try:
        await get_msg(userbot, user_id, msg_id, link, retry_count, message)
        await asyncio.sleep(5)
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

    user_settings = await db.get_data(user_id)
    target_chat_id = user_settings.get("chat_id") if user_settings else None

    summary_tracker = {}

    try:
        normal_links_handled = False
        userbot = await initialize_userbot(user_id)

        for i in range(cs, cs + cl):
            if user_id in users_loop and users_loop[user_id]:
                url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
                link = get_link(url)
                if 't.me/' in link and not any(x in link for x in ['t.me/b/', 't.me/c/', 'tg://openmessage']):
                    msg = await app.send_message(message.chat.id, f"Processing...")
                    await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
                    await classify_and_record_link(userbot, link, user_id, summary_tracker, target_chat_id)
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
            await app.send_message(message.chat.id, "😘 Complete Ho Gaya Boss 😎")
            await send_clickable_summary(app, user_id, summary_tracker, cl, target_chat_id)
            return
            
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
                    await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
                    await classify_and_record_link(userbot, link, user_id, summary_tracker, target_chat_id)
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

        await app.send_message(message.chat.id, "😘 Complete Ho Gaya Boss 😎")
        await send_clickable_summary(app, user_id, summary_tracker, cl, target_chat_id)

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

@app.on_message(filters.command("gen_code") & filters.private)
async def generate_code_handler(client, message):
    user_id = message.chat.id
    
    owner_list = OWNER_ID if isinstance(OWNER_ID, list) else [int(OWNER_ID)]
    if user_id not in owner_list:
        return await message.reply(f"⚠️ તમારી પાસે પરવાનગી નથી! User ID: `{user_id}`")
    
    args = message.text.split()
    count = 1
    if len(args) > 1 and args[1].isdigit():
        count = int(args[1])
        if count > 20:
            count = 20

    try:
        from devgagan.core.mongo.db import create_redeem_code
        generated_codes = []

        for _ in range(count):
            code = f"SRC-{secrets.token_hex(3).upper()}"
            await create_redeem_code(code, hours=5)
            generated_codes.append(f"`{code}`")

        if count == 1:
            text = (
                f"🎉 **૫ કલાકનો નવો રીડીમ કોડ!**\n\n"
                f"🔑 **કોડ:** {generated_codes[0]}\n"
                f"⏳ **સમયગાળો:** ૫ કલાક\n\n"
                f"👉 વાપરવા માટે: `/redeem {generated_codes[0]}`\n\n"
                f"**__Powered By ╰‿╯ ҡσℓเ ⚝__**"
            )
        else:
            codes_list = "\n".join([f"• {c}" for c in generated_codes])
            text = (
                f"🎉 **કુલ {count} રીડીમ કોડ બની ગયા!** (દરેક ૫ કલાક)\n\n"
                f"{codes_list}\n\n"
                f"👉 મેમ્બરને `/redeem CODE` મોકલવા કહો.\n\n"
                f"**__Powered By ╰‿╯ ҡσℓเ ⚝__**"
            )

        await message.reply(text)
    except Exception as e:
        await message.reply(f"❌ એરર આવી: `{e}`")

@app.on_message(filters.command("redeem") & filters.private)
async def redeem_code_handler(client, message):
    user_id = message.chat.id
    args = message.text.split()
    
    if len(args) < 2:
        return await message.reply("⚠️ કોડ લખવો જરૂરી છે!\n\nઆ રીતે લખો: `/redeem SRC-XXXXXX`")
    
    code = args[1].strip()
    try:
        from devgagan.core.mongo.db import use_redeem_code
        success, res_msg = await use_redeem_code(code, user_id)
        await message.reply(res_msg)
    except Exception as e:
        await message.reply(f"❌ એરર આવી: `{e}`")



# ==================== ULTRA PRO GUJARAT EXAM SUMMARY SYSTEM ====================

def detect_real_exam_subject(text: str) -> str:
    if not text:
        return "સામાન્ય વિષય"

    t = text.lower()

    # સ્પર્ધાત્મક પરીક્ષાના ૧૦૦% સાચા અને શુદ્ધ નામો
    exam_catalog = [
        (["રીઝનીંગ", "reasoning", "તાર્કિક"], "રીઝનીંગ"),
        (["ગણિત", "maths", "math", "numerical", "સંખ્યાત્મક"], "ગણિત"),
        (["ગુજરાતી વ્યાકરણ", "vyakaran", "વ્યાકરણ"], "ગુજરાતી વ્યાકરણ"),
        (["ગુજરાતી સાહિત્ય", "sahitya", "સાહિત્ય"], "ગુજરાતી સાહિત્ય"),
        (["અંગ્રેજી વ્યાકરણ", "english grammar", "english", "ઇંગ્લિશ", "eng grammar"], "અંગ્રેજી વ્યાકરણ"),
        (["ગુજરાતી ભાષા", "માતૃભાષા"], "ગુજરાતી ભાષા"),
        (["બંધારણ", "polity", "constitution", "રાજ્યવ્યવસ્થા"], "ભારતનું બંધારણ"),
        (["ઇતિહાસ", "history", "ઈતિહાસ", "aitihas"], "ઇતિહાસ"),
        (["ભૂગોળ", "geography", "ભુગોળ", "bhugol"], "ભૂગોળ"),
        (["વિજ્ઞાન", "science", "સાયન્સ", "સામાન્ય વિજ્ઞાન", "ટેકનોલોજી"], "સામાન્ય વિજ્ઞાન"),
        (["અર્થતંત્ર", "અર્થશાસ્ત્ર", "economy", "economics", "banking"], "ભારતીય અર્થતંત્ર"),
        (["સાંસ્કૃતિક વારસો", "વારસો", "culture", "heritage"], "સાંસ્કૃતિક વારસો"),
        (["કરંટ અફેર્સ", "current affairs", "કરંટ", "વર્તમાન પ્રવાહો"], "વર્તમાન પ્રવાહો"),
        (["પર્યાવરણ", "environment", "ફોરેસ્ટ", "વન્યજીવ"], "પર્યાવરણ"),
        (["કોમ્પ્યુટર", "computer", "કોમ્પ", "ict"], "કોમ્પ્યુટર"),
        (["પંચાયતી રાજ", "panchayati raj"], "પંચાયતી રાજ"),
        (["જાહેર વહીવટ", "public administration"], "જાહેર વહીવટ"),
        (["કાયદો", "law", "ipc", "crpc", "પુરાવા", "evidence"], "કાયદો"),
        (["કંડક્ટર", "ડ્રાઈવર", "મોટર વ્હીકલ", "રોડ સેફટી", "road safety", "first aid"], "કંડક્ટર અને રોડ સેફટી"),
        (["મનોવિજ્ઞાન", "psychology", "બાળ વિકાસ", "pedagogy", "tet", "tat"], "શિક્ષણ અને મનોવિજ્ઞાન"),
        (["સામાન્ય જ્ઞાન", "જનરલ નોલેજ", "gk", "general knowledge"], "સામાન્ય જ્ઞાન")
    ]

    for keywords, official_name in exam_catalog:
        for kw in keywords:
            if kw in t:
                return official_name

    # જો ઉપરનામાંથી ન મળે તો માત્ર ચોખ્ખો વિષય જ લેવો (ફાઇલનું નામ કે એક્સટેન્શન નહીં)
    for line in text.split("\n"):
        clean_line = line.strip()
        if "topic name" in clean_line.lower():
            clean = re.sub(r'(?i)topic name\s*[:\-\—]*', '', clean_line).strip()
            if clean and clean.lower() != "topic":
                return clean[:25]
        if "topic:" in clean_line.lower() or "વિષય:" in clean_line.lower():
            clean = re.sub(r'(?i)(topic|વિષય)\s*[:\-\—]*', '', clean_line).strip()
            if clean:
                return clean[:25]

    return "અન્ય વિષય"

@app.on_message(filters.command("gen_summary") & filters.private)
async def generate_channel_summary_cmd(client, message: Message):
    user_id = message.chat.id
    target_chat_id = None

    if len(message.command) > 1:
        raw_cid = message.command[1].strip()
        try:
            target_chat_id = int(raw_cid)
        except ValueError:
            target_chat_id = raw_cid
    else:
        user_settings = await db.get_data(user_id)
        if user_settings and user_settings.get("chat_id"):
            try:
                target_chat_id = int(str(user_settings.get("chat_id")).strip())
            except Exception:
                target_chat_id = user_settings.get("chat_id")

    if not target_chat_id:
        return await message.reply("⚠️ ચેનલ ID મળ્યો નથી!\nવાપરો: `/gen_summary -100xxxxxxxxxx` અથવા `/settings` માં ચેનલ સેટ કરો.")

    status_msg = await message.reply("⚡ **સમરી બની રહી છે...** કૃપા કરીને થોડીવાર રાહ જુઓ.")

    summary_dict = {}
    total_files = 0

    try:
        clean_cid = str(target_chat_id).replace("-100", "")

        # ચેનલના છેલ્લા 1000 મેસેજ સ્કેન કરવા
        collected_messages = []
        async for msg in client.get_chat_history(target_chat_id, limit=1000):
            if msg.video or msg.document:
                collected_messages.append(msg)

        if not collected_messages:
            return await status_msg.edit_text("❌ ચેનલમાં કોઈ વિડિયો કે PDF મળ્યા નથી.")

        # સૌથી જૂના (પહેલા અપલોડ થયેલા) મેસેજથી ગણતરી કરવી
        # જેથી લિંક હંમેશા પેલા (Lec-1) વિડિયોની જ બને!
        collected_messages.reverse()

        for msg in collected_messages:
            total_files += 1
            raw_text = msg.caption or msg.text or ""
            if not raw_text:
                if msg.video and msg.video.file_name:
                    raw_text = msg.video.file_name
                elif msg.document and msg.document.file_name:
                    raw_text = msg.document.file_name

            subject_name = detect_real_exam_subject(raw_text)

            is_pdf = bool(msg.document and (msg.document.file_name.lower().endswith('.pdf') if msg.document.file_name else False))
            is_video = bool(msg.video or (msg.document and "video" in str(msg.document.mime_type)))

            # ગ્રૂપ ફોરમ ટોપિક કે ચેનલ લિંક
            if msg.topic_manually_assigned or (hasattr(msg, 'message_thread_id') and msg.message_thread_id):
                thread_id = msg.message_thread_id
                jump_url = f"https://t.me/c/{clean_cid}/{thread_id}/{msg.id}"
            else:
                jump_url = f"https://t.me/c/{clean_cid}/{msg.id}"

            # જો વિષય પહેલી વાર આવ્યો હોય તો જ તેની લિંક સેવ થશે (એટલે કે પહેલો વિડિયો)
            if subject_name not in summary_dict:
                summary_dict[subject_name] = {
                    "first_url": jump_url,
                    "videos": 0,
                    "pdfs": 0
                }

            if is_video:
                summary_dict[subject_name]["videos"] += 1
            elif is_pdf:
                summary_dict[subject_name]["pdfs"] += 1

        # ક્લીન અને કોમ્પેક્ટ ફોર્મેટ (જૂનું કશું જ નહીં આવે)
        summary_text = "📌 **Topic Summary**\n"
        summary_text += "━━━━━━━━━━━━━━━━━━━━\n\n"

        for subject, stats in summary_dict.items():
            first_url = stats["first_url"]
            v = stats["videos"]
            p = stats["pdfs"]
            # નામ પર દબાવતાં જ તે વિષયના પહેલા વિડિયો પર પહોંચી જશે
            summary_text += f"- [{subject}]({first_url}) 🎥 {v} | 📄 {p}\n\n"

        summary_text += "━━━━━━━━━━━━━━━━━━━━\n"
        summary_text += f"✅ **કુલ અપલોડ થયેલ ફાઇલો:** `{total_files}`\n"
        summary_text += "💡 *જે વિષય પર જવું હોય તેના બ્લુ નામ પર ક્લિક કરો.*\n\n"
        summary_text += "**__Powered By ╰‿╯ ҡσℓเ ⚝__**"

        # ૧. ચેનલમાં મોકલવું અને Pin કરવું
        try:
            ch_post = await client.send_message(target_chat_id, summary_text, disable_web_page_preview=True)
            try:
                await ch_post.pin(both_sides=True)
            except Exception:
                pass
        except Exception as e:
            print(f"Error posting in target channel: {e}")

        # ૨. પર્સનલ બોટમાં મોકલવું
        await client.send_message(user_id, summary_text, disable_web_page_preview=True)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ એરર આવી: {e}\nખાતરી કરો કે બોટ ચેનલમાં એડમિન છે.")
                           
        
