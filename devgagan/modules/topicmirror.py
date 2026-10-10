import asyncio
import time
import re
from pyrogram import filters
from pyrogram.errors import FloodWait
from telethon.tl.functions.messages import CreateForumTopicRequest
from devgagan import app, sex
from devgagan.modules.main import initialize_userbot
from devgagan.core.get_func import get_msg, user_chat_ids

BOT_OWNER_ID = 7899675722

user_mirror_data = {}
mirror_cancel_flags = {}
authorized_mirror_users = set()

def is_authorized(user_id: int) -> bool:
    uid = int(user_id)
    if uid == BOT_OWNER_ID or uid in authorized_mirror_users:
        return True
    return False

# ----------------- એક્સેસ કંટ્રોલ કમાન્ડ્સ -----------------

@app.on_message(filters.command("addmirror") & filters.private)
async def add_mirror_access(client, message):
    if not is_authorized(message.chat.id):
        return await message.reply_text("❌ આ કમાન્ડ વાપરવાની પરવાનગી માત્ર એડમિન પાસે છે.")
    args = message.text.strip().split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply_text("⚠️ સાચો કમાન્ડ વાપરો: `/addmirror <user_id>`")
    uid = int(args[1])
    authorized_mirror_users.add(uid)
    await message.reply_text(f"✅ યુઝર `{uid}` ને મિરર એક્સેસ આપી દીધો છે.")

@app.on_message(filters.command("delmirror") & filters.private)
async def del_mirror_access(client, message):
    if not is_authorized(message.chat.id):
        return await message.reply_text("❌ આ કમાન્ડ વાપરવાની પરવાનગી માત્ર એડમિન પાસે છે.")
    args = message.text.strip().split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply_text("⚠️ સાચો કમાન્ડ વાપરો: `/delmirror <user_id>`")
    uid = int(args[1])
    if uid in authorized_mirror_users:
        authorized_mirror_users.remove(uid)
        await message.reply_text(f"🚫 યુઝર `{uid}` પાસેથી મિરર એક્સેસ હટાવી દીધો છે.")
    else:
        await message.reply_text("⚠️ આ યુઝર પાસે પહેલેથી એક્સેસ નથી.")

# ----------------- હેલ્પર ફંક્શન્સ -----------------

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

# ----------------- મિરર કમાન્ડ્સ -----------------

# ૧. /topicmirror - બધા ટોપિક્સ સાચા નામ સાથે સિંક કરવા
@app.on_message(filters.command("topicmirror") & filters.private)
async def topic_mirror_full(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.")

    try:
        ask = await app.ask(user_id, "🔗 સોર્સ ગ્રુપના કોઈપણ એક મેસેજની લિંક મોકલો:")
        link = ask.text.strip()
        source_chat_id, _, _ = parse_tg_link(link)

        ask = await app.ask(user_id, "🎯 ટાર્ગેટ ગ્રુપ ID મોકલો (-100 થી શરૂ થતો):")
        target_chat_id = int(ask.text.strip())

    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: `{e}`")

    status = await app.send_message(user_id, "⏳ યુઝરબોટ ચાલુ થઈ રહ્યો છે...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ નથી. પહેલા `/login` કરો.")

    try:
        await status.edit("🔍 શરૂઆતના મેસેજમાંથી સાચા નામ સાથે બધા ટોપિક્સ શોધાઈ રહ્યા છે...")
        topics = {}

 # ૧. ટેલિથોન યુઝરબોટ દ્વારા બધા પેજના ટોપિક્સ (પૂરેપૂરા ૯૯+) લાવશે
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
                    
                    # જો ૧૦૦ કરતાં ઓછા ટોપિક્સ આવે તો લૂપ બંધ થશે
                    if len(raw_topics) < 100:
                        break
                    
                    # પછીના પેજના ટોપિક્સ મેળવવા માટે ઓફસેટ સેટ કરો
                    last_t = raw_topics[-1]
                    offset_topic = getattr(last_t, "id", 0)
                    offset_date = getattr(last_t, "date", 0)
                    offset_id = getattr(last_t, "top_message", 0)
                    await asyncio.sleep(0.3)
            except Exception:
                pass

        # ૨. જો API થી પૂરા ના મળે તો હિસ્ટ્રીમાંથી ડીપ સ્કેન
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
                        

        # ૨. જો API થી ના મળે તો જ Fallback હિસ્ટ્રી સ્કેન (કોઈ બ્રેક વગર)
        if not topics:
            async for msg in userbot.get_chat_history(source_chat_id, limit=8000):
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
            return await status.edit("❌ ગ્રુપમાંથી કોઈ ટોપિક્સ મળ્યા નહીં. ખાતરી કરો કે યુઝરબોટ એ ગ્રુપમાં છે.")

        mapped = {}
        total = len(topics)
        current = 0
        summary_lines = ["📋 **ટોપિક લિસ્ટ:**"]
        progress_msg = await app.send_message(user_id, f"🛠️ કુલ {total} ટોપિક મળ્યા! હવે નવા ગ્રુપમાં બની રહ્યા છે...")

        for t_id in sorted(topics.keys()):
            title = topics[t_id]
            current += 1
            try:
                new_id = await create_topic(target_chat_id, title)
                mapped[t_id] = new_id
                summary_lines.append(f"`{t_id}` ➔ `{title[:22]}`")
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try:
                    new_id = await create_topic(target_chat_id, title)
                    mapped[t_id] = new_id
                    summary_lines.append(f"`{t_id}` ➔ `{title[:22]}`")
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

# ૨. /topiclink - Game te Group ni Link to Link Transfer
@app.on_message(filters.command("topiclink") & filters.private)
async def topic_link_direct(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ Tamari pase aa command vaparvano access nathi.")

    try:
        ask = await app.ask(user_id, "🔗 Source topic na video/message ni link moklo:")
        s_link = ask.text.strip()
        s_chat_id, s_topic_id, s_msg_id = parse_tg_link(s_link)

        ask = await app.ask(user_id, "🔗 Target group na topic ni link moklo:")
        t_link = ask.text.strip()
        t_chat_id, t_topic_id, _ = parse_tg_link(t_link)
    except Exception as e:
        return await app.send_message(user_id, f"❌ Link vanchvama bhul thai: `{e}`")

    mirror_cancel_flags[user_id] = False
    user_chat_ids[user_id] = f"{t_chat_id}/{t_topic_id}"

    status = await app.send_message(
        user_id, 
        f"🚀 Video `{s_msg_id}` thi sharu kari ne target topic `{t_topic_id}` ma transfer thai rahya chhe...\n(Rokva mate `/cancel_mirror` moklo)"
    )
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ Userbot chalu nathi. Pahela `/login` karo.")

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

            temp = await app.send_message(user_id, f"🔄 Processing video `{msg.id}`...")
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

        await status.edit(f"🎉 **Transfer puru thayu!**\n✅ Safal files: `{success}`")
    finally:
        mirror_cancel_flags.pop(user_id, None)
        user_chat_ids.pop(user_id, None)
        try:
            await userbot.stop()
        except Exception:
            pass
            

# ૩. /scan_mirror - બંને ટોપિકમાં ફાઇલો સરખાવવી
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

# ૪. /sync_mirror - બાકી ફાઇલો સિંક કરવી
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

# ૫. /cancel_mirror - ચાલુ મિરરિંગ રોકવા માટે
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



# ૬. /mirror_all - જ્યાંથી બાકી હોય ત્યાંથી જ ઓટો-રીઝ્યૂમ અને કમ્પ્લીટ મેસેજ સાથે
@app.on_message(filters.command("mirror_all") & filters.private)
async def mirror_all_topics_handler(client, message):
    user_id = message.chat.id
    if not is_authorized(user_id):
        return await message.reply_text("❌ તમારી પાસે આ કમાન્ડ વાપરવાનો એક્સેસ નથી.")

    data = user_mirror_data.get(user_id)
    if not data or "mapped_topics" not in data or not data["mapped_topics"]:
        return await message.reply_text("❌ પહેલા `/topicmirror` રન કરો જેથી ટોપિક્સ મેપ થઈ જાય.")

    s_chat_id = data["source_chat_id"]
    t_chat_id = data["target_chat_id"]
    mapped = {int(k): int(v) for k, v in data["mapped_topics"].items() if v}

    mirror_cancel_flags[user_id] = False
    status = await app.send_message(user_id, f"🚀 **કુલ {len(mapped)} ટોપિક્સનું સ્માર્ટ મિરરિંગ શરૂ થઈ રહ્યું છે...**\n(વચ્ચે રોકવા માટે `/cancel_mirror` મોકલો)")

    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ નથી. પહેલા `/login` કરો.")

    total_synced_all = 0
    try:
        topic_items = sorted(mapped.items())
        for idx, (s_topic, t_topic) in enumerate(topic_items, 1):
            if mirror_cancel_flags.get(user_id, False):
                await app.send_message(user_id, "🛑 મિરરિંગ રોકી દેવામાં આવ્યું છે.")
                break

            user_chat_ids[user_id] = f"{t_chat_id}/{t_topic}"

            # ૧. ટાર્ગેટ ટોપિકમાં છેલ્લે ક્યાં સુધી ફાઇલ આવી તે ચેક કરો (Resume Logic)
            last_synced_src_id = 0
            is_already_done = False
            async for t_msg in userbot.get_chat_history(t_chat_id, limit=30):
                th_id = getattr(t_msg, "message_thread_id", None) or t_topic
                if int(th_id) == int(t_topic):
                    if t_msg.text and "તમામ ફાઇલો સફળતાપૂર્વક અપલોડ" in t_msg.text:
                        is_already_done = True
                        break
                    txt = t_msg.caption or t_msg.text or ""
                    m = re.search(rf"/c/{str(s_chat_id).replace('-100', '')}/(\d+)", txt)
                    if m:
                        last_synced_src_id = max(last_synced_src_id, int(m.group(1)))

            # જો ટોપિક પહેલેથી જ પૂરો થઈ ગયો હોય તો સ્કીપ કરો
            if is_already_done:
                continue

            await status.edit(f"⏳ **પ્રગતિ:** ટોપિક `{idx}/{len(mapped)}` (ID: `{s_topic}`) ના બાકી વિડિયો ટ્રાન્સફર થઈ રહ્યા છે...")

            topic_video_count = 0
            src_messages = []
            async for msg in userbot.get_chat_history(s_chat_id, limit=1000):
                th_id = getattr(msg, "message_thread_id", None) or s_topic
                if int(th_id) == int(s_topic) and msg.media:
                    if msg.id > last_synced_src_id:
                        src_messages.append(msg)

            src_messages.reverse()

            for msg in src_messages:
                if mirror_cancel_flags.get(user_id, False):
                    break

                temp = await app.send_message(user_id, f"🔄 પ્રોસેસિંગ ટોપિક `{s_topic}` - ફાઇલ `{msg.id}`...")
                fake_link = f'https://t.me/c/{str(s_chat_id).replace("-100", "")}/{msg.id}'
                try:
                    await get_msg(userbot, user_id, temp.id, fake_link, 0, message)
                    total_synced_all += 1
                    topic_video_count += 1
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

            # ટોપિક પૂરો થાય એટલે કમ્પ્લીટ મેસેજ મોકલવો
            if not mirror_cancel_flags.get(user_id, False):
                try:
                    await app.send_message(
                        chat_id=t_chat_id,
                        text=f"✅ **ટોપિક પૂર્ણ!**\nઆ ટોપિકની તમામ ફાઇલો સફળતાપૂર્વક અપલોડ થઈ ગઈ છે.",
                        message_thread_id=t_topic
                    )
                except Exception:
                    pass

            await asyncio.sleep(1)

        await status.edit(f"🎉 **બધા ટોપિક્સનું મિરરિંગ પૂરું થયું!**\n✅ કુલ નવી ટ્રાન્સફર થયેલી ફાઇલો: `{total_synced_all}`")
    finally:
        mirror_cancel_flags.pop(user_id, None)
        user_chat_ids.pop(user_id, None)
        try:
            await userbot.stop()
        except Exception:
            pass
                       
