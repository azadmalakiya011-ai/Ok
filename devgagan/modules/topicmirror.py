import asyncio
import time
from pyrogram import filters
from pyrogram.errors import FloodWait
from telethon.tl.functions.messages import CreateForumTopicRequest, GetForumTopicsRequest
from devgagan import app, sex
from devgagan.modules.main import initialize_userbot
from devgagan.core.get_func import get_msg, user_chat_ids

# ઓનર ID અને ઓથોરાઈઝ્ડ યુઝર્સ
from config import OWNER_ID

user_mirror_data = {}
mirror_cancel_flags = {}
authorized_mirror_users = set()

# એક્સેસ ચેક કરવા માટેનું ફંક્શન
def is_authorized(user_id: int) -> bool:
    if user_id == OWNER_ID or user_id in authorized_mirror_users:
        return True
    return False

# ----------------- એક્સેસ કંટ્રોલ કમાન્ડ્સ (માત્ર ઓનર માટે) -----------------

@app.on_message(filters.command("addmirror") & filters.private)
async def add_mirror_access(client, message):
    if message.chat.id != OWNER_ID:
        return await message.reply_text("❌ આ કમાન્ડ વાપરવાની પરવાનગી માત્ર બોટ ઓનર પાસે છે.")
    
    args = message.text.strip().split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply_text("⚠️ સાચો કમાન્ડ વાપરો: `/addmirror <user_id>`")
    
    uid = int(args[1])
    authorized_mirror_users.add(uid)
    await message.reply_text(f"✅ યુઝર `{uid}` ને ટોપિક મિરર કમાન્ડ્સ વાપરવાનો એક્સેસ આપી દેવામાં આવ્યો છે.")

@app.on_message(filters.command("delmirror") & filters.private)
async def del_mirror_access(client, message):
    if message.chat.id != OWNER_ID:
        return await message.reply_text("❌ આ કમાન્ડ વાપરવાની પરવાનગી માત્ર બોટ ઓનર પાસે છે.")
    
    args = message.text.strip().split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply_text("⚠️ સાચો કમાન્ડ વાપરો: `/delmirror <user_id>`")
    
    uid = int(args[1])
    if uid in authorized_mirror_users:
        authorized_mirror_users.remove(uid)
        await message.reply_text(f"🚫 યુઝર `{uid}` પાસેથી મિરર એક્સેસ હટાવી દેવામાં આવ્યો છે.")
    else:
        await message.reply_text(f"⚠️ આ યુઝર પાસે પહેલેથી એક્સેસ નથી.")

# ----------------- મિરરિંગ ફંક્શન્સ -----------------

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

# ૧. /topicmirror
@app.on_message(filters.command("topicmirror") & filters.private)
async def topic_mirror_full(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી. એડમિનનો સંપર્ક કરો.")

    try:
        ask = await app.ask(user_id, "🔗 સોર્સ ગ્રુપના કોઈપણ એક મેસેજની લિંક મોકલો:")
        link = ask.text.strip()
        source_chat_id, extracted_topic_id, start_msg_id = parse_tg_link(link)

        ask = await app.ask(user_id, "🎯 ટાર્ગેટ ગ્રુપ ID મોકલો (-100 થી શરૂ થતો):")
        target_chat_id = int(ask.text.strip())

        ask = await app.ask(user_id, "🔢 કેટલા મેસેજ સ્કેન કરવા છે? (દા.ત. 100 અથવા 200):")
        limit = int(ask.text.strip())
    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: `{e}`")

    status = await app.send_message(user_id, "⏳ યુઝરબોટ ચાલુ થઈ રહ્યો છે...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ નથી. પહેલા `/login` કરો.")

    try:
        await status.edit("🔍 સાચા નામ સાથે બધા ટોપિક્સ શોધાઈ રહ્યા છે...")
        topics = {}

        if sex and sex.is_connected():
            try:
                src_entity = await sex.get_input_entity(source_chat_id)
                forum_res = await sex(GetForumTopicsRequest(
                    channel=src_entity,
                    offset_date=0,
                    offset_id=0,
                    offset_topic=0,
                    limit=100
                ))
                for t in getattr(forum_res, "topics", []):
                    t_id = getattr(t, "id", None)
                    t_title = getattr(t, "title", None)
                    if t_id and t_title and int(t_id) != 1:
                        topics[int(t_id)] = t_title
            except Exception:
                pass

        if not topics:
            for mid in range(start_msg_id, start_msg_id + limit):
                try:
                    msg = await userbot.get_messages(source_chat_id, mid)
                    if not msg or getattr(msg, "empty", False):
                        continue
                    th_id = getattr(msg, "message_thread_id", None) or extracted_topic_id
                    if th_id and int(th_id) != 1 and int(th_id) not in topics:
                        title = None
                        created = getattr(msg, "forum_topic_created", None)
                        if created and getattr(created, "title", None):
                            title = created.title
                        topics[int(th_id)] = title or f"Topic {th_id}"
                    await asyncio.sleep(0.02)
                except Exception:
                    continue

        if not topics:
            return await status.edit("❌ કોઈ ટોપિક મળ્યા નથી.")

        mapped = {}
        total = len(topics)
        current = 0
        summary_lines = ["📋 **ટોપિક લિસ્ટ:**"]
        progress_msg = await app.send_message(user_id, "🛠️ ટોપિક્સ બનાવવાનું ચાલુ છે...")

        for t_id, title in topics.items():
            current += 1
            try:
                new_id = await create_topic(target_chat_id, title)
                mapped[t_id] = new_id
                summary_lines.append(f"`{t_id}` ➔ `{title[:18]}`")
            except Exception:
                mapped[t_id] = None

            if current % 4 == 0 or current == total:
                try:
                    await progress_msg.edit("> " + "\n".join(summary_lines)[:4000])
                except Exception:
                    pass
            await asyncio.sleep(0.15)

        user_mirror_data[user_id] = {
            "source_chat_id": source_chat_id,
            "target_chat_id": target_chat_id,
            "mapped_topics": mapped
        }

        created_count = sum(1 for v in mapped.values() if v)
        await status.edit(
            f"🎉 **બધા ટોપિક્સ સિંક થઈ ગયા!**\n"
            f"બનેલા ટોપિક્સ: `{created_count}` / `{total}`\n\n"
            "👉 ચોક્કસ ટોપિક મિરર કરવા માટે: `/topiclink`\n"
            "👉 બાકી રહેલી ફાઈલો સિંક કરવા માટે: `/sync_mirror`"
        )
    finally:
        try:
            await userbot.stop()
        except Exception:
            pass

# ૨. /topiclink
@app.on_message(filters.command("topiclink") & filters.private)
async def topic_link_direct(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.")

    try:
        ask = await app.ask(user_id, "🔗 સોર્સ ટોપિકના કોઈપણ મેસેજની લિંક મોકલો:")
        s_link = ask.text.strip()
        s_chat_id, s_topic_id, _ = parse_tg_link(s_link)

        ask = await app.ask(user_id, "🔗 ટાર્ગેટ ટોપિકના કોઈપણ મેસેજની લિંક મોકલો:")
        t_link = ask.text.strip()
        t_chat_id, t_topic_id, _ = parse_tg_link(t_link)
    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: `{e}`")

    mirror_cancel_flags[user_id] = False
    user_chat_ids[user_id] = f"{t_chat_id}/{t_topic_id}"

    status = await app.send_message(user_id, f"🚀 ટોપિક `{s_topic_id}` ➔ `{t_topic_id}` માં ફાઇલ ટ્રાન્સફર ચાલુ છે...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ નથી.")

    success = 0
    try:
        async for msg in userbot.get_chat_history(s_chat_id):
            if mirror_cancel_flags.get(user_id, False):
                break
            if not msg or getattr(msg, "empty", False) or getattr(msg, "service", False):
                continue
            th_id = getattr(msg, "message_thread_id", None) or s_topic_id
            if int(th_id) == int(s_topic_id):
                temp = await app.send_message(user_id, f"🔄 પ્રોસેસિંગ `{msg.id}`...")
                fake_link = f'https://t.me/c/{str(s_chat_id).replace("-100", "")}/{msg.id}'
                try:
                    await get_msg(userbot, user_id, temp.id, fake_link, 0, message)
                    success += 1
                except Exception:
                    pass
                finally:
                    try:
                        await temp.delete()
                    except Exception:
                        pass
                await asyncio.sleep(2)
        await status.edit(f"🎉 **ટોપિક-ટુ-ટોપિક ટ્રાન્સફર પૂરું થયું!**\n✅ સફળ: `{success}`")
    finally:
        mirror_cancel_flags.pop(user_id, None)
        user_chat_ids.pop(user_id, None)
        try:
            await userbot.stop()
        except Exception:
            pass

# ૩. /scan_mirror
@app.on_message(filters.command("scan_mirror") & filters.private)
async def scan_mirror_compare(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.")

    try:
        ask = await app.ask(user_id, "🔗 સોર્સ ટોપિકની લિંક મોકલો:")
        s_link = ask.text.strip()
        s_chat_id, s_topic_id, _ = parse_tg_link(s_link)

        ask = await app.ask(user_id, "🔗 ટાર્ગેટ ટોપિકની લિંક મોકલો:")
        t_link = ask.text.strip()
        t_chat_id, t_topic_id, _ = parse_tg_link(t_link)
    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: `{e}`")

    status = await app.send_message(user_id, "🔍 મેસેજ અને મીડિયા ગણાઈ રહ્યા છે...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ નથી.")

    try:
        s_count = 0
        async for msg in userbot.get_chat_history(s_chat_id, limit=300):
            th_id = getattr(msg, "message_thread_id", None) or s_topic_id
            if int(th_id) == int(s_topic_id) and msg.media:
                s_count += 1

        t_count = 0
        async for msg in userbot.get_chat_history(t_chat_id, limit=300):
            th_id = getattr(msg, "message_thread_id", None) or t_topic_id
            if int(th_id) == int(t_topic_id) and msg.media:
                t_count += 1

        diff = max(0, s_count - t_count)
        await status.edit(
            "📊 **સ્કેન અને સરખામણીનું પરિણામ:**\n\n"
            f"📁 જૂના ટોપિકમાં મીડિયા: `{s_count}`\n"
            f"📁 નવા ટોપિકમાં મીડિયા: `{t_count}`\n"
            f"⚠️ બાકી રહેલી ફાઈલો: `{diff}`\n\n"
            "બાકી રહેલી ફાઈલો મોકલવા માટે `/sync_mirror` ચલાવો."
        )
    finally:
        try:
            await userbot.stop()
        except Exception:
            pass

# ૪. /sync_mirror
@app.on_message(filters.command("sync_mirror") & filters.private)
async def sync_mirror_missing(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.")

    try:
        ask = await app.ask(user_id, "🔗 સોર્સ ટોપિકની લિંક મોકલો:")
        s_link = ask.text.strip()
        s_chat_id, s_topic_id, _ = parse_tg_link(s_link)

        ask = await app.ask(user_id, "🔗 ટાર્ગેટ ટોપિકની લિંક મોકલો:")
        t_link = ask.text.strip()
        t_chat_id, t_topic_id, _ = parse_tg_link(t_link)
    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: `{e}`")

    mirror_cancel_flags[user_id] = False
    user_chat_ids[user_id] = f"{t_chat_id}/{t_topic_id}"
    status = await app.send_message(user_id, "🔄 બાકી રહેલી ફાઈલો સિંક થઈ રહી છે...")

    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ નથી.")

    try:
        target_files = set()
        async for t_msg in userbot.get_chat_history(t_chat_id, limit=200):
            th_id = getattr(t_msg, "message_thread_id", None) or t_topic_id
            if int(th_id) == int(t_topic_id) and t_msg.media:
                size = getattr(getattr(t_msg, t_msg.media.value, None), "file_size", None)
                if size:
                    target_files.add(size)

        synced = 0
        async for s_msg in userbot.get_chat_history(s_chat_id, limit=200):
            if mirror_cancel_flags.get(user_id, False):
                break
            th_id = getattr(s_msg, "message_thread_id", None) or s_topic_id
            if int(th_id) == int(s_topic_id) and s_msg.media:
                s_size = getattr(getattr(s_msg, s_msg.media.value, None), "file_size", None)
                if s_size and s_size not in target_files:
                    temp = await app.send_message(user_id, f"🔄 ફાઇલ સિંક થઈ રહી છે `{s_msg.id}`...")
                    fake_link = f'https://t.me/c/{str(s_chat_id).replace("-100", "")}/{s_msg.id}'
                    try:
                        await get_msg(userbot, user_id, temp.id, fake_link, 0, message)
                        synced += 1
                        target_files.add(s_size)
                    except Exception:
                        pass
                    finally:
                        try:
                            await temp.delete()
                        except Exception:
                            pass
                    await asyncio.sleep(2)

        await status.edit(f"🎉 **સિંકિંગ પૂરું થયું!**\n✅ બાકી ફાઈલો ટ્રાન્સફર થઈ: `{synced}`")
    finally:
        mirror_cancel_flags.pop(user_id, None)
        user_chat_ids.pop(user_id, None)
        try:
            await userbot.stop()
        except Exception:
            pass

# ૫. /cancel_mirror
@app.on_message(filters.command(["cancel_mirror", "stopmirror"]) & filters.private)
async def cancel_mirror_handler(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.")

    if user_id in mirror_cancel_flags:
        mirror_cancel_flags[user_id] = True
        await message.reply_text("🛑 **મિરરિંગ રોકવાની વિનંતી સ્વીકારી લીધી છે!** હાલની ફાઈલ પૂરી થતાં જ બંધ થઈ જશે.")
    else:
        await message.reply_text("⚠️ હાલમાં કોઈ મિરરિંગ પ્રોસેસ ચાલુ નથી.")
            
