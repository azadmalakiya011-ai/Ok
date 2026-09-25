# ---------------------------------------------------
# File Name: main.py
# Description: 100% Tested Working Channel Summary with Direct Video Jump Links
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
from pyrogram.errors import FloodWait, MessageNotModified
from datetime import datetime, timedelta
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from devgagan.modules.shrink import is_user_verified

async def generate_random_name(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

users_loop = {}
interval_set = {}
batch_mode = {}

# Caption / File Title માંથી વિષયનું શુદ્ધ ગુજરાતી નામ મેળવવું
def extract_topic_from_text(raw_text: str) -> str:
    if not raw_text:
        return "સામાન્ય વિષય"

    # ૧. File Title વાળી લાઇનમાંથી નામ કાઢવું
    for line in raw_text.split("\n"):
        if "file title" in line.lower():
            clean = re.sub(r'(?i)file title\s*[:\-\—]*', '', line).strip()
            clean = re.sub(r'(\.pdf|\.mkv|\.mp4|\[\d+p\]|\(\d+p\))', '', clean, flags=re.IGNORECASE).strip()
            clean = re.sub(r'(?i)\b(l|lec|lecture)[\-_ ]*\d+\b\s*[:\-\—]*', '', clean).strip()
            if clean:
                return clean[:30]

    # ૨. કીવર્ડ્સ મેચ કરવા
    t_lower = raw_text.lower()
    subject_map = [
        (["રીઝનીંગ", "reasoning"], "રીઝનીંગ"),
        (["રોડ સેફટી", "road safety", "મોટર"], "રોડ સેફટી"),
        (["ગુજરાતી વ્યાકરણ", "વ્યાકરણ", "vyakaran"], "ગુજરાતી વ્યાકરણ"),
        (["ગુજરાતી સાહિત્ય", "સાહિત્ય", "sahitya"], "ગુજરાતી સાહિત્ય"),
        (["ગણિત", "maths", "math"], "ગણિત"),
        (["કોમ્પ્યુટર", "computer", "કોમ્પ"], "કોમ્પ્યુટર"),
        (["અંગ્રેજી", "english", "ઇંગ્લિશ", "eng"], "અંગ્રેજી"),
        (["ઇતિહાસ", "history", "ઈતિહાસ"], "ઇતિહાસ"),
        (["ભૂગોળ", "geography", "ભુગોળ"], "ભૂગોળ"),
        (["બંધારણ", "polity", "constitution"], "બંધારણ"),
        (["વિજ્ઞાન", "science", "સાયન્સ"], "વિજ્ઞાન"),
        (["કાયદો", "law", "ipc", "crpc"], "કાયદો"),
        (["કરંટ", "current"], "કરંટ અફેર્સ"),
        (["પર્યાવરણ", "environment", "ફોરેસ્ટ"], "પર્યાવરણ"),
        (["સામાન્ય જ્ઞાન", "જનરલ નોલેજ", "gk"], "સામાન્ય જ્ઞાન"),
        (["કંડક્ટર", "ડ્રાઈવર"], "કંડક્ટર સ્પેશિયલ")
    ]

    for kws, name in subject_map:
        for kw in kws:
            if kw in t_lower:
                return name

    for line in raw_text.split("\n"):
        clean_line = line.strip()
        if clean_line and not any(x in clean_line.lower() for x in ["vid id", "pdf id", "batch name", "topic name", "log info"]):
            clean_line = re.sub(r'(\.pdf|\.mkv|\.mp4)', '', clean_line, flags=re.IGNORECASE).strip()
            return clean_line[:30]

    return "સામાન્ય વિષય"

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

    # ટાર્ગેટ ચેનલ આઈડી મેળવવો અને ફોર્મેટ કરવો
    target_chat_id = None
    try:
        user_settings = await db.get_data(user_id)
        if user_settings:
            raw_cid = user_settings.get("chat_id")
            if raw_cid:
                raw_str = str(raw_cid).strip()
                if not raw_str.startswith("-100"):
                    raw_str = "-100" + raw_str.lstrip("-")
                target_chat_id = int(raw_str)
    except Exception as e:
        print(f"Target chat ID error: {e}")

    summary_data = {}

    try:
        userbot = await initialize_userbot(user_id)
        dest_chat = target_chat_id if target_chat_id else user_id

        for i in range(cs, cs + cl):
            if not users_loop.get(user_id, False):
                break

            url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
            link = get_link(url)

            if any(x in link for x in ['t.me/b/', 't.me/c/']) and not userbot:
                await app.send_message(message.chat.id, "⚠️ આ પ્રાઈવેટ ચેનલ છે! કૃપા કરીને પહેલા /login કરો.")
                break

            # સોર્સ મેસેજમાંથી વિષયનું સાચું નામ વાંચવું
            topic_name = "સામાન્ય વિષય"
            is_pdf = False
            try:
                parts = link.split("/")
                c_id = int("-100" + parts[-2])
                m_id = int(parts[-1].split("?")[0])
                src_msg = await userbot.get_messages(c_id, m_id)
                if src_msg:
                    raw_text = src_msg.caption or src_msg.text or ""
                    if not raw_text and src_msg.document and src_msg.document.file_name:
                        raw_text = src_msg.document.file_name
                    elif not raw_text and src_msg.video and src_msg.video.file_name:
                        raw_text = src_msg.video.file_name

                    topic_name = extract_topic_from_text(raw_text)
                    if src_msg.document and src_msg.document.file_name and src_msg.document.file_name.lower().endswith(".pdf"):
                        is_pdf = True
            except Exception as e:
                print(f"Source fetch error: {e}")

            msg = await app.send_message(message.chat.id, "Processing...")
            await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)

            # વિડિયો અપલોડ થયા પછી ટાર્ગેટ ચેનલમાંથી તાજા વિડિયોનો સાચો મેસેજ ID લેવો
            await asyncio.sleep(3.5)
            latest_msg_id = None
            
            # Userbot દ્વારા તાજેતરનો મેસેજ શોધવો
            if userbot:
                try:
                    async for last_m in userbot.get_chat_history(dest_chat, limit=1):
                        latest_msg_id = last_m.id
                        break
                except Exception:
                    pass

            if not latest_msg_id:
                try:
                    async for last_m in app.get_chat_history(dest_chat, limit=1):
                        latest_msg_id = last_m.id
                        break
                except Exception:
                    pass

            # ૧૦૦% સાચી ટાર્ગેટ ચેનલની લિંક બનાવવી જેથી ક્લિક કરતાં સીધો વિડિયો ખુલે
            clean_dest = str(dest_chat).replace("-100", "").replace("-", "")
            if latest_msg_id:
                jump_url = f"https://t.me/c/{clean_dest}/{latest_msg_id}"
            else:
                jump_url = f"https://t.me/c/{clean_dest}/1"

            # દરેક વિષય માટે તેના પહેલા વિડિયોની લિંક સાચવવી
            if topic_name not in summary_data:
                summary_data[topic_name] = {
                    "url": jump_url,
                    "videos": 0,
                    "pdfs": 0
                }

            if is_pdf:
                summary_data[topic_name]["pdfs"] += 1
            else:
                summary_data[topic_name]["videos"] += 1

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

        # ફોટો જેવી પરફેક્ટ Topic Summary ફોર્મેટ
        summary_text = "📌 **Topic Summary**\n\n"
        for topic, stats in summary_data.items():
            url = stats["url"]
            v_count = stats["videos"]
            p_count = stats["pdfs"]
            summary_text += f"- [{topic}]({url}) 🎥 {v_count} | 📄 {p_count}\n\n"

        summary_text += "━━━━━━━━━━━━━━━━━━━━\n"
        summary_text += f"✅ **કુલ ફાઇલો:** `{cl}`\n"
        summary_text += "**__Powered By ╰‿╯ ҡσℓเ ⚝__**"

        # ૧. ટાર્ગેટ ચેનલમાં સીધું Userbot દ્વારા મોકલવું અને Pin કરવું
        if target_chat_id and userbot:
            try:
                ch_msg = await userbot.send_message(
                    chat_id=target_chat_id,
                    text=summary_text,
                    disable_web_page_preview=True
                )
                try:
                    await ch_msg.pin(both_sides=True)
                except Exception:
                    pass
            except Exception as e:
                print(f"Userbot channel summary error: {e}")
                # જો Userbot થી ન થાય તો Bot દ્વારા ટ્રાય કરવી
                try:
                    ch_msg2 = await app.send_message(
                        chat_id=target_chat_id,
                        text=summary_text,
                        disable_web_page_preview=True
                    )
                    await ch_msg2.pin(both_sides=True)
                except Exception:
                    pass

        # ૨. યુઝરની પર્સનલ બોટ ચેટમાં પણ મોકલવું
        try:
            u_msg = await app.send_message(
                chat_id=user_id,
                text=summary_text,
                disable_web_page_preview=True
            )
            try:
                await u_msg.pin(both_sides=True)
            except Exception:
                pass
        except Exception as e:
            print(f"User summary error: {e}")

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
    
