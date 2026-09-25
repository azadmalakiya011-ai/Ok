# ---------------------------------------------------
# File Name: main.py
# Description: Auto Channel Scanner & Multi-Part Topic Summary
# Author: Gagan | Custom Mod for: ╰‿╯ ҡσℓเ ⚝
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
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, MessageNotModified
from datetime import datetime, timedelta
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from devgagan.modules.shrink import is_user_verified

async def generate_random_name(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

users_loop = {}
interval_set = {}
batch_mode = {}

def extract_topic_from_text(raw_text: str) -> str:
    if not raw_text:
        return "અન્ય વિષય"

    # 1. Caption mathi 'Topic Name :' athva 'Topic :' vali line sodhvi
    topic_line_text = ""
    for line in raw_text.split("\n"):
        line_clean = line.strip()
        if re.search(r'(?i)\btopic(\s*name)?\s*[:\-\—]', line_clean):
            topic_line_text = re.sub(r'(?i)^.*?\btopic(\s*name)?\s*[:\-\—]\s*', '', line_clean).strip()
            break

    text_to_search = f"{topic_line_text} {raw_text}".lower()

    # 2. Mukhya vishayo nu list
    subject_map = [
        (["કોમ્પ્યુટર", "computer", "કોમ્પ", "comp"], "કોમ્પ્યુટર"),
        (["ગણિત", "maths", "math", "mathematics"], "ગણિત"),
        (["રીઝનીંગ", "reasoning", "માનસિક ક્ષમતા", "mental ability"], "રીઝનીંગ"),
        (["રોડ સેફટી", "road safety", "મોટર વ્હીકલ"], "રોડ સેફટી"),
        (["ગુજરાતી વ્યાકરણ", "gujarati vyakaran", "gujarati grammar"], "ગુજરાતી વ્યાકરણ"),
        (["ગુજરાતી સાહિત્ય", "gujarati sahitya", "sahitya"], "ગુજરાતી સાહિત્ય"),
        (["ગુજરાતનો ઇતિહાસ", "ગુજરાતનો ઈતિહાસ", "gujarat no itihas", "gujarat itihas", "gujarat history"], "ગુજરાતનો ઇતિહાસ"),
        (["ભારતનો ઇતિહાસ", "ભારતનો ઈતિહાસ", "bharat no itihas", "bharat itihas", "indian history"], "ભારતનો ઇતિહાસ"),
        (["ગુજરાતનો સાંસ્કૃતિક વારસો", "ગુજરાતનો વારસો", "gujarat no sanskrutik varso"], "ગુજરાતનો સાંસ્કૃતિક વારસો"),
        (["ભારતનો સાંસ્કૃતિક વારસો", "ભારતનો વારસો", "bharat no sanskrutik varso"], "ભારતનો સાંસ્કૃતિક વારસો"),
        (["ગુજરાતની ભૂગોળ", "ગુજરાત ભૂગોળ", "gujarati bhugol", "gujarat bhugol", "gujarat geography"], "ગુજરાતની ભૂગોળ"),
        (["ભારતની ભૂગોળ", "ભારત ભૂગોળ", "bharat ni bhugol", "bharat bhugol", "indian geography"], "ભારતની ભૂગોળ"),
        (["વિશ્વ ભૂગોળ", "વિશ્વની ભૂગોળ", "vishva bhugol", "world geography"], "વિશ્વની ભૂગોળ"),
        (["ભારતીય બંધારણ", "બંધારણ", "bhartiy bandharan", "bandharan", "polity", "constitution"], "ભારતીય બંધારણ"),
        (["પત્ર લેખન", "patra lekhan"], "પત્ર લેખન"),
        (["અહિરવાલ", "ahirwal"], "અહિરવાલ"),
        (["પર્યાવરણ", "paryavaran", "environment", "ફોરેસ્ટ", "વનરક્ષક"], "પર્યાવરણ"),
        (["ઇંગ્લિશ ગ્રામર", "અંગ્રેજી વ્યાકરણ", "english grammar"], "ઇંગ્લિશ ગ્રામર"),
        (["અંગ્રેજી", "ઇંગ્લિશ", "english", "eng"], "અંગ્રેજી"),
        (["ગુજરાતી", "gujarati"], "ગુજરાતી"),
        (["સામાન્ય વિજ્ઞાન", "વિજ્ઞાન", "science", "general science", "સાયન્સ"], "સામાન્ય વિજ્ઞાન"),
        (["વિજ્ઞાન અને ટેકનોલોજી", "science and tech"], "વિજ્ઞાન અને ટેકનોલોજી"),
        (["કાયદો", "law", "ipc", "crpc", "evidence act", "પોલીસ કાયદો"], "કાયદો"),
        (["પંચાયતી રાજ", "panchayati raj"], "પંચાયતી રાજ"),
        (["જાહેર વહીવટ", "public administration", "pub ad"], "જાહેર વહીવટ"),
        (["અર્થશાસ્ત્ર", "અર્થતંત્ર", "economics", "economy"], "અર્થશાસ્ત્ર"),
        (["કરંટ અફેર્સ", "વર્તમાન પ્રવાહો", "current affairs", "current"], "કરંટ અફેર્સ"),
        (["સામાન્ય જ્ઞાન", "જનરલ નોલેજ", "gk", "general knowledge"], "સામાન્ય જ્ઞાન"),
        (["કંડક્ટર", "ડ્રાઈવર", "conductor"], "કંડક્ટર સ્પેશિયલ"),
        (["નીતિશાસ્ત્ર", "ethics"], "નીતિશાસ્ત્ર"),
        (["આપત્તિ વ્યવસ્થાપન", "disaster management"], "આપત્તિ વ્યવસ્થાપન"),
        (["સરકારી યોજનાઓ", "યોજનાઓ", "yojana", "yojna"], "સરકારી યોજનાઓ")
    ]

    for kws, name in subject_map:
        for kw in kws:
            if kw in text_to_search:
                return name

    # 3. Jo teacher nu naam aave to te clean karvu
    if topic_line_text:
        clean_topic = re.sub(r'(?i)\b\w+\s+sir\b\s*[\-\—:]*\s*', '', topic_line_text).strip()
        if clean_topic:
            return clean_topic[:25]
        return topic_line_text[:25]

    # 4. Faltu lines jem ke Index, Numbers ane ID ne ignore karvi
    for line in raw_text.split("\n"):
        clean_line = line.strip()
        if not clean_line:
            continue
        if any(x in clean_line.lower() for x in ["index", "vid id", "pdf id", "batch name", "log info", "saved by", "user id", "file title"]):
            continue
        if re.match(r'^[\s\-_:0-9\(\)\[\]\.\/]+$', clean_line):
            continue
        clean_line = re.sub(r'(\.pdf|\.mkv|\.mp4)', '', clean_line, flags=re.IGNORECASE).strip()
        if len(clean_line) > 2:
            return clean_line[:25]

    return "અન્ય વિષય"

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

async def process_and_upload_link(userbot, user_id, msg_id, link, retry_count, message):
    try:
        await get_msg(userbot, user_id, msg_id, link, retry_count, message)
        await asyncio.sleep(4)
    except Exception as e:
        print(f"Error in upload: {e}")

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
            if 't.me/+' in link:
                await msg.edit_text(await userbot_join(userbot, link))
            elif any(sub in link for sub in ['t.me/c/', 't.me/b/', '/s/', 'tg://openmessage']):
                await process_and_upload_link(userbot, user_id, msg.id, link, 0, msg)
                await set_interval(user_id, interval_minutes=45)
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

    except Exception as e:
        await app.send_message(message.chat.id, f"Error: {e}")
    finally:
        users_loop.pop(user_id, None)
        if userbot:
            try:
                await userbot.stop()
            except Exception:
                pass

# ---------------------------------------------------
# Auto Scanner Command: /gen_summary (Subject Grouping Support)
# ---------------------------------------------------
@app.on_message(filters.command("gen_summary"))
async def generate_channel_summary_auto(client, message):
    user_id = message.chat.id
    target_chat_id = None

    args = message.text.split()
    if len(args) > 1:
        raw_arg = args[1].strip()
        if not raw_arg.startswith("-100"):
            raw_arg = "-100" + raw_arg.lstrip("-")
        try:
            target_chat_id = int(raw_arg)
        except Exception:
            pass

    if not target_chat_id:
        try:
            user_settings = await db.get_data(user_id)
            if user_settings:
                raw_cid = (
                    user_settings.get("chat_id")
                    or user_settings.get("channel_id")
                    or user_settings.get("dump_id")
                    or user_settings.get("target_chat")
                )
                if raw_cid:
                    raw_str = str(raw_cid).strip()
                    if not raw_str.startswith("-100"):
                        raw_str = "-100" + raw_str.lstrip("-")
                    target_chat_id = int(raw_str)
        except Exception as e:
            print(f"Error fetching channel: {e}")

    if not target_chat_id:
        return await message.reply(
            "⚠️ ચેનલ આઈડી મળ્યો નથી!\n\n"
            "કૃપા કરીને `/settings` માં જઈને **Set Chat ID** કરો,\n"
            "અથવા સીધું આ રીતે લખો:\n`/gen_summary -100XXXXXXXXXX`"
        )

    status_msg = await message.reply(f"🔍 ચેનલ `{target_chat_id}` માંથી વીડિયો સ્કેન થઈ રહ્યા છે...")
    userbot = await initialize_userbot(user_id)
    c = userbot if userbot else app

    summary_data = {}
    clean_dest = str(target_chat_id).replace("-100", "").replace("-", "")

    try:
        all_messages = []
        async for m in c.get_chat_history(target_chat_id):
            if m.video or m.document:
                all_messages.append(m)

        all_messages.reverse()

        for m in all_messages:
            raw_text = m.caption or m.text or ""
            if not raw_text and m.video and m.video.file_name:
                raw_text = m.video.file_name
            elif not raw_text and m.document and m.document.file_name:
                raw_text = m.document.file_name

            topic = extract_topic_from_text(raw_text)
            is_pdf = bool(m.document and (m.document.file_name.endswith('.pdf') if m.document.file_name else False))
            jump_url = f"https://t.me/c/{clean_dest}/{m.id}"

            if topic not in summary_data:
                summary_data[topic] = {
                    "url": jump_url,
                    "videos": 0,
                    "pdfs": 0
                }

            if is_pdf:
                summary_data[topic]["pdfs"] += 1
            else:
                summary_data[topic]["videos"] += 1

        if not summary_data:
            return await status_msg.edit_text(f"❌ ચેનલ `{target_chat_id}` માં કોઈ વીડિયો કે ફાઈલ મળી નથી.")

        total_files = 0
        topic_lines = []
        for topic, stats in summary_data.items():
            url = stats["url"]
            v = stats["videos"]
            p = stats["pdfs"]
            total_files += (v + p)
            # Vishay na naam par click karta direct pehlo video khulse
            topic_lines.append(f"- [{topic}]({url}) 🎥 {v} | 📄 {p}\n\n")

        parts = []
        curr_part = "📌 **Topic Summary**\n\n"
        for line in topic_lines:
            if len(curr_part) + len(line) > 3000:
                parts.append(curr_part)
                curr_part = "📌 **Topic Summary (Continued)**\n\n" + line
            else:
                curr_part += line

        curr_part += "━━━━━━━━━━━━━━━━━━━━\n"
        curr_part += f"✅ **Total Files:** `{total_files}`\n"
        curr_part += "**__Powered By ╰‿╯ ҡσℓเ ⚝__**"
        parts.append(curr_part)

        first_msg = None
        sender = userbot if userbot else app

        for idx, part_text in enumerate(parts):
            sent = None
            try:
                sent = await sender.send_message(target_chat_id, part_text, disable_web_page_preview=True)
            except Exception:
                sent = await app.send_message(target_chat_id, part_text, disable_web_page_preview=True)

            if idx == 0 and sent:
                first_msg = sent
                try:
                    await first_msg.pin(both_sides=True)
                except Exception:
                    pass
            await asyncio.sleep(1)

        await status_msg.edit_text(f"✅ ચેનલ `{target_chat_id}` માં સમરી મોકલાઈ ગઈ અને પિન થઈ ગઈ!")

    except Exception as e:
        await status_msg.edit_text(f"❌ Error આવી: {e}")
    finally:
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
                      
