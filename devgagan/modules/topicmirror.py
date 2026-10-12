import asyncio
import time
import re
from pyrogram import filters
from pyrogram.errors import FloodWait
from telethon.tl.functions.messages import CreateForumTopicRequest
from devgagan import app, sex
from devgagan.modules.main import initialize_userbot
from devgagan.core.get_func import get_msg, user_chat_ids

BOT_OWNER_ID = 8326187435

user_mirror_data = {}
mirror_cancel_flags = {}
# user_id: expiry_timestamp (0 એટલે લાઈફટાઈમ)
authorized_mirror_users = {}

def parse_duration(time_str: str) -> int:
    unit = time_str[-1].lower()
    val = int(time_str[:-1])
    if unit == 's':
        return val
    elif unit == 'm':
        return val * 60
    elif unit == 'h':
        return val * 3600
    elif unit == 'd':
        return val * 86400
    elif unit == 'y':
        return val * 86400 * 365
    return 0

def is_authorized(user_id: int) -> bool:
    uid = int(user_id)
    if uid == BOT_OWNER_ID:
        return True
    if uid in authorized_mirror_users:
        expiry = authorized_mirror_users[uid]
        if expiry == 0 or time.time() < expiry:
            return True
        else:
            authorized_mirror_users.pop(uid, None)
            return False
    return False

# ----------------- 🔐 એક્સેસ કંટ્રોલ કમાન્ડ્સ -----------------

@app.on_message(filters.command("addmirror") & filters.private)
async def add_mirror_access(client, message):
    if message.chat.id != BOT_OWNER_ID:
        return await message.reply_text("❌ **આ કમાન્ડ માત્ર બોટ ઓનર વાપરી શકે છે.**")
    
    args = message.text.strip().split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply_text(
            "⚠️ **વાપરવાની રીત:**\n"
            "`/addmirror <user_id> <time>`\n\n"
            "**ઉદાહરણ:**\n"
            "• ૧ કલાક: `/addmirror 123456789 1h`\n"
            "• ૧ દિવસ: `/addmirror 123456789 1d`\n"
            "• ૨ દિવસ: `/addmirror 123456789 2d`\n"
            "• ૧ વર્ષ: `/addmirror 123456789 1y`\n"
            "• કાયમી: `/addmirror 123456789`"
        )
    
    uid = int(args[1])
    duration_str = args[2] if len(args) >= 3 else None

    if duration_str:
        try:
            seconds = parse_duration(duration_str)
            if seconds <= 0:
                return await message.reply_text("❌ **ખોટો સમય ફોર્મેટ!** (ઉદાહરણ: 1h, 2d, 1y વાપરો)")
            expiry_time = time.time() + seconds
            authorized_mirror_users[uid] = expiry_time
            await message.reply_text(f"✨ **સફળ!** યુઝર `{uid}` ને `{duration_str}` માટે મિરર એક્સેસ આપવામાં આવ્યો છે. 🔓")
        except Exception:
            return await message.reply_text("❌ **સમય ગણતરીમાં ભૂલ થઈ.** સાચો ફોર્મેટ લખો (દા.ત. 1d, 2d, 1h).")
    else:
        authorized_mirror_users[uid] = 0
        await message.reply_text(f"✨ **સફળ!** યુઝર `{uid}` ને કાયમી (Lifetime) મિરર એક્સેસ આપવામાં આવ્યો છે. 👑")

@app.on_message(filters.command("delmirror") & filters.private)
async def del_mirror_access(client, message):
    if message.chat.id != BOT_OWNER_ID:
        return await message.reply_text("❌ **આ કમાન્ડ માત્ર બોટ ઓનર વાપરી શકે છે.**")
    
    args = message.text.strip().split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply_text("⚠️ **સાચો કમાન્ડ વાપરો:** `/delmirror <user_id>`")
    
    uid = int(args[1])
    if uid in authorized_mirror_users:
        authorized_mirror_users.pop(uid, None)
        await message.reply_text(f"🚫 **યુઝર `{uid}` પાસેથી મિરર એક્સેસ હટાવી દીધો છે.** 🔒")
    else:
        await message.reply_text("⚠️ **આ યુઝર પાસે પહેલેથી એક્સેસ નથી.**")


# ----------------- 🛠️ હેલ્પર ફંક્શન્સ -----------------

async def create_topic(chat_id, title):
    if not sex or not sex.is_connected():
        raise Exception("Telethon ક્લાયન્ટ કનેક્ટ નથી.")
    entity = await sex.get_input_entity(chat_id)
    result = await sex(CreateForumTopicRequest(
        peer=entity,
        title=title[:128],
        random_id=int(time.time() * 1000)
    ))
    for update in getattr(result, "updates", []):
        msg = getattr(update, "message", None)
        if msg:
            return msg.id
    raise Exception("Topic ID બન્યો નથી.")

def parse_tg_link(link: str):
    parts = link.strip().split("/")
    idx = parts.index("c")
    chat_id = int("-100" + parts[idx + 1])
    nums = [int(x.split("?")[0]) for x in parts[idx + 2:] if x.split("?")[0].isdigit()]
    topic_id = nums[-2] if len(nums) >= 2 else 1
    msg_id = nums[-1] if nums else 1
    return chat_id, topic_id, msg_id


# ----------------- 🚀 મિરર કમાન્ડ્સ -----------------

# ૧. /topicmirror - બધા ટોપિક્સ સાચા નામ સાથે સિંક કરવા
@app.on_message(filters.command("topicmirror") & filters.private)
async def topic_mirror_full(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ **તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.**")

    try:
        ask = await app.ask(user_id, "🔗 **સોર્સ ગ્રુપના કોઈપણ એક મેસેજની લિંક મોકલો:**")
        link = ask.text.strip()
        source_chat_id, _, _ = parse_tg_link(link)

        ask = await app.ask(user_id, "🎯 **ટાર્ગેટ ગ્રુપ ID મોકલો (-100 થી શરૂ થતો):**")
        target_chat_id = int(ask.text.strip())
    except Exception as e:
        return await app.send_message(user_id, f"❌ **ભૂલ થઈ:** `{e}`")

    status = await app.send_message(user_id, "⏳ **યુઝરબોટ ચકાસી રહ્યા છીએ...**")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ **યુઝરબોટ ચાલુ નથી. પહેલા `/login` કરો.**")

    try:
        await status.edit("🔍 **બધા ટોપિક્સ સાચા નામ સાથે સ્કેન થઈ રહ્યા છે...** 📂")
        topics = {}

        if sex and sex.is_connected():
            try:
                from telethon.tl.functions.channels import GetForumTopicsRequest
                src_entity = await sex.get_input_entity(source_chat_id)
                offset_date = 0
                offset_id = 0
                offset_topic = 0
                
                while True:
                    forum_res = await sex(GetForumTopicsRequest(
                        channel=src_entity,
                        offset_date=offset_date,
                        offset_id=offset_id,
                        offset_topic=offset_topic,
                        limit=100
                    ))
                    raw_topics = getattr(forum_res, "topics", [])
                    if not raw_topics:
                        break
                    
                    for t in raw_topics:
                        t_id = getattr(t, "id", None)
                        t_title = getattr(t, "title", None)
                        if t_id and t_title and int(t_id) != 1:
                            topics[int(t_id)] = t_title
                    
                    if len(raw_topics) < 100:
                        break
                    
                    last_t = raw_topics[-1]
                    offset_topic = getattr(last_t, "id", 0)
                    offset_date = getattr(last_t, "date", 0)
                    offset_id = getattr(last_t, "top_message", 0)
                    await asyncio.sleep(0.3)
            except Exception:
                pass

        if len(topics) < 50:
            async for msg in userbot.get_chat_history(source_chat_id, limit=25000):
                if not msg or getattr(msg, "empty", False):
                    continue
                th_id = getattr(msg, "message_thread_id", None)
                created = getattr(msg, "forum_topic_created", None)
                if created and getattr(created, "title", None):
                    topics[msg.id] = created.title
                elif th_id and int(th_id) != 1 and int(th_id) not in topics:
                    topics[int(th_id)] = None

            for t_id, name in list(topics.items()):
                if not name:
                    try:
                        t_msg = await userbot.get_messages(source_chat_id, int(t_id))
                        if t_msg and getattr(t_msg, "forum_topic_created", None):
                            topics[t_id] = t_msg.forum_topic_created.title
                        else:
                            topics[t_id] = f"Topic {t_id}"
                    except Exception:
                        topics[t_id] = f"Topic {t_id}"

        if not topics:
            return await status.edit("❌ **ગ્રુપમાંથી કોઈ ટોપિક્સ મળ્યા નહીં.** ખાતરી કરો કે તમારું એકાઉન્ટ તે ગ્રુપમાં હાજર છે.")

        mapped = {}
        total = len(topics)
        current = 0
        summary_lines = ["📋 **નવા બનેલા ટોપિક્સનું લિસ્ટ:**"]
        progress_msg = await app.send_message(user_id, f"🛠️ **કુલ `{total}` ટોપિક મળ્યા!** નવા ગ્રુપમાં બની રહ્યા છે...")

        for t_id in sorted(topics.keys()):
            title = topics[t_id]
            current += 1
            try:
                new_id = await create_topic(target_chat_id, title)
                mapped[t_id] = new_id
                summary_lines.append(f"📁 `{title[:22]}` ➔ `#{new_id}`")
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try:
                    new_id = await create_topic(target_chat_id, title)
                    mapped[t_id] = new_id
                    summary_lines.append(f"📁 `{title[:22]}` ➔ `#{new_id}`")
                except Exception:
                    mapped[t_id] = None
            except Exception:
                mapped[t_id] = None

            if current % 4 == 0 or current == total:
                try:
                    await progress_msg.edit("> " + "\n".join(summary_lines)[:4000])
                except Exception:
                    pass
            await asyncio.sleep(0.2)

        user_mirror_data[user_id] = {
            "source_chat_id": source_chat_id,
            "target_chat_id": target_chat_id,
            "mapped_topics": mapped
        }

        created_count = sum(1 for v in mapped.values() if v)
        finish_text = (
            "✅ 𝗖ꪮ𝗺𝗽𝗹𝗲𝘁𝗲 𝗛ꪮ 𝗚𝗮𝘆𝗮 𝗕ꪮ$$ 😎\n\n"
            f"🎉 **બધા ટોપિક્સ સફળતાપૂર્વક બની ગયા છે!**\n"
            f"📊 કુલ બનેલા ટોપિક્સ: `{created_count}` / `{total}` 📁\n\n"
            "👉 એક ટોપિક માટે: `/topiclink`\n"
            "👉 બધા ટોપિક્સ ઓટો-મિરર કરવા માટે: `/mirror_all`"
        )
        await status.edit(finish_text)
    except Exception as e:
        await status.edit(f"❌ **ટોપિક બનાવવામાં ભૂલ આવી:** `{e}`")


# ૨. /topiclink - Game te Group ni Link to Link Transfer
@app.on_message(filters.command("topiclink") & filters.private)
async def topic_link_direct(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ **તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.**")

    try:
        ask = await app.ask(user_id, "🔗 **Source topic ના video/message ની લિંક મોકલો:**")
        s_link = ask.text.strip()
        s_chat_id, s_topic_id, s_msg_id = parse_tg_link(s_link)

        ask = await app.ask(user_id, "🔗 **Target group ના topic ની લિંક મોકલો:**")
        t_link = ask.text.strip()
        t_chat_id, t_topic_id, _ = parse_tg_link(t_link)
    except Exception as e:
        return await app.send_message(user_id, f"❌ **લિંક વાંચવામાં ભૂલ થઈ:** `{e}`")

    start_time = time.time()
    mirror_cancel_flags[user_id] = False
    user_chat_ids[user_id] = f"{t_chat_id}/{t_topic_id}"

    status = await app.send_message(
        user_id, 
        f"🚀 **વિડિયો `{s_msg_id}` થી ટ્રાન્સફર શરૂ થઈ રહ્યું છે...**\n🎯 ટાર્ગેટ ટોપિક: `{t_topic_id}`\n\n🛑 રોકવા માટે `/cancel_mirror` મોકલો."
    )
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ **યુઝરબોટ ચાલુ નથી. પહેલા `/login` કરો.**")

    success = 0
    try:
        target_msgs = []
        async for msg in userbot.get_chat_history(s_chat_id, limit=2000):
            if not msg or getattr(msg, "empty", False) or getattr(msg, "service", False):
                continue
            
            th_id = getattr(msg, "message_thread_id", None) or s_topic_id
            if int(th_id) == int(s_topic_id) and msg.media:
                if msg.id >= s_msg_id:
                    target_msgs.append(msg)

        target_msgs.reverse()

        for msg in target_msgs:
            if mirror_cancel_flags.get(user_id, False):
                break

            temp = await app.send_message(user_id, f"🔄 **પ્રોસેસિંગ ફાઇલ:** `{msg.id}`...")
            fake_link = f'https://t.me/c/{str(s_chat_id).replace("-100", "")}/{msg.id}'
            
            try:
                await get_msg(userbot, user_id, temp.id, fake_link, 0, message)
                success += 1
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception:
                pass
            finally:
                try:
                    await temp.delete()
                except Exception:
                    pass
            await asyncio.sleep(2)

        elapsed = time.time() - start_time
        mins, secs = int(elapsed // 60), int(elapsed % 60)

        done_msg = (
            "✅ 𝗖ꪮ𝗺𝗽𝗹𝗲𝘁𝗲 𝗛ꪮ 𝗚𝗮𝘆𝗮 𝗕ꪮ$$ 😎\n\n"
            f"📁 **સફળ ફાઇલો ટ્રાન્સફર:** `{success}` ફાઇલ્સ\n"
            f"🎯 **ટાર્ગેટ ટોપિક ID:** `{t_topic_id}`\n"
            f"⏱ **લાગેલો સમય:** `{mins}m, {secs}s` ⚡"
        )
        await status.edit(done_msg)
    finally:
        mirror_cancel_flags.pop(user_id, None)
        user_chat_ids.pop(user_id, None)


# ૩. /scan_mirror - Perfect Scan અને સરખામણી
@app.on_message(filters.command("scan_mirror") & filters.private)
async def scan_mirror_compare(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ **તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.**")

    try:
        ask = await app.ask(user_id, "🔗 **Source topic ની લિંક મોકલો:**")
        s_link = ask.text.strip()
        s_chat_id, s_topic_id, _ = parse_tg_link(s_link)

        ask = await app.ask(user_id, "🔗 **Target topic ની લિંક મોકલો:**")
        t_link = ask.text.strip()
        t_chat_id, t_topic_id, _ = parse_tg_link(t_link)
    except Exception as e:
        return await app.send_message(user_id, f"❌ **લિંક વાંચવામાં ભૂલ થઈ:** `{e}`")

    status = await app.send_message(user_id, "🔍 **બંને ટોપિક્સ સ્કેન અને કમ્પેર થઈ રહ્યા છે...** ⏳")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ **યુઝરબોટ ચાલુ નથી. પહેલા `/login` કરો.**")

    try:
        target_files = set()
        t_count = 0
        async for t_msg in userbot.get_chat_history(t_chat_id, limit=2000):
            if not t_msg or getattr(t_msg, "empty", False) or getattr(t_msg, "service", False):
                continue
            
            th_id = getattr(t_msg, "message_thread_id", None)
            if (th_id and int(th_id) == int(t_topic_id)) or (not th_id and int(t_topic_id) == 1):
                if t_msg.media:
                    t_count += 1
                    media_obj = getattr(t_msg, t_msg.media.value, None)
                    if media_obj:
                        f_id = getattr(media_obj, "file_unique_id", None) or getattr(media_obj, "file_size", None)
                        if f_id:
                            target_files.add(str(f_id))

        s_count = 0
        missing_count = 0
        async for s_msg in userbot.get_chat_history(s_chat_id, limit=2000):
            if not s_msg or getattr(s_msg, "empty", False) or getattr(s_msg, "service", False):
                continue

            th_id = getattr(s_msg, "message_thread_id", None)
            if (th_id and int(th_id) == int(s_topic_id)) or (not th_id and int(s_topic_id) == 1):
                if s_msg.media:
                    s_count += 1
                    media_obj = getattr(s_msg, s_msg.media.value, None)
                    if media_obj:
                        f_id = getattr(media_obj, "file_unique_id", None) or getattr(media_obj, "file_size", None)
                        if str(f_id) not in target_files:
                            missing_count += 1

        res_text = (
            "📊 **સ્કેન અને સરખામણી રિપોર્ટ:**\n\n"
            f"📁 જૂના (Source) ટોપિકમાં ફાઇલો: `{s_count}`\n"
            f"📁 નવા (Target) ટોપિકમાં ફાઇલો: `{t_count}`\n"
            f"⚠️ **હજુ બાકી રહેલી ફાઇલો:** `{missing_count}`\n\n"
            "👉 ખૂટતી ફાઈલો ભરવા માટે `/sync_mirror` કમાન્ડ વાપરો."
        )
        await status.edit(res_text)
    except Exception as e:
        await status.edit(f"❌ **સ્કેન કરવામાં ભૂલ થઈ:** `{e}`")


# ૪. /sync_mirror - બાકી રહેલી ફાઇલો સિંક કરવી
@app.on_message(filters.command("sync_mirror") & filters.private)
async def sync_mirror_missing(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ **તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.**")

    try:
        ask = await app.ask(user_id, "🔗 **Source topic ની લિંક મોકલો:**")
        s_link = ask.text.strip()
        s_chat_id, s_topic_id, _ = parse_tg_link(s_link)

        ask = await app.ask(user_id, "🔗 **Target topic ની લિંક મોકલો:**")
        t_link = ask.text.strip()
        t_chat_id, t_topic_id, _ = parse_tg_link(t_link)
    except Exception as e:
        return await app.send_message(user_id, f"❌ **ભૂલ થઈ:** `{e}`")

    start_time = time.time()
    mirror_cancel_flags[user_id] = False
    user_chat_ids[user_id] = f"{t_chat_id}/{t_topic_id}"
    status = await app.send_message(user_id, "🔄 **બાકી રહેલી ફાઈલો સ્કેન અને સિંક થઈ રહી છે...** ⏳")

    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ **યુઝરબોટ ચાલુ નથી. પહેલા `/login` કરો.**")

    try:
        target_file_ids = set()
        async for t_msg in userbot.get_chat_history(t_chat_id, limit=600):
            th_id = getattr(t_msg, "message_thread_id", None) or t_topic_id
            if int(th_id) == int(t_topic_id) and t_msg.media:
                media_obj = getattr(t_msg, t_msg.media.value, None)
                if media_obj:
                    f_id = getattr(media_obj, "file_unique_id", None) or getattr(media_obj, "file_size", None)
                    if f_id:
                        target_file_ids.add(str(f_id))

        missing_msgs = []
        async for s_msg in userbot.get_chat_history(s_chat_id, limit=600):
            th_id = getattr(s_msg, "message_thread_id", None) or s_topic_id
            if int(th_id) == int(s_topic_id) and s_msg.media:
                media_obj = getattr(s_msg, s_msg.media.value, None)
                if media_obj:
                    f_id = getattr(media_obj, "file_unique_id", None) or getattr(media_obj, "file_size", None)
                    if str(f_id) not in target_file_ids:
                        missing_msgs.append(s_msg)

        missing_msgs.reverse()

        if not missing_msgs:
            return await status.edit("✅ **બધી ફાઈલો પહેલેથી સિંક છે.** કોઈ ફાઈલ બાકી નથી! 😎")

        synced = 0
        for s_msg in missing_msgs:
            if mirror_cancel_flags.get(user_id, False):
                break

            temp = await app.send_message(user_id, f"🔄 **ટ્રાન્સફર થઈ રહ્યો છે:** `{s_msg.id}`...")
            uploaded = False

            try:
                await userbot.copy_message(
                    chat_id=t_chat_id,
                    from_chat_id=s_chat_id,
                    message_id=s_msg.id,
                    message_thread_id=t_topic_id
                )
                uploaded = True
                synced += 1
            except Exception:
                pass

            if not uploaded:
                fake_link = f'https://t.me/c/{str(s_chat_id).replace("-100", "")}/{s_msg.id}'
                try:
                    await get_msg(userbot, user_id, temp.id, fake_link, 0, message)
                    synced += 1
                except FloodWait as e:
                    await asyncio.sleep(e.value + 1)
                except Exception:
                    pass

            try:
                await temp.delete()
      
