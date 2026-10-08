import asyncio
import random
from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.raw.functions.channels import CreateForumTopic
from devgagan import app
from devgagan.modules.main import initialize_userbot
from devgagan.core.get_func import get_msg, user_chat_ids

user_mirror_data = {}

async def create_topic(chat_id, title):
    peer = await app.resolve_peer(chat_id)
    rnd_id = random.randint(1, 9223372036854775807)
    r = await app.invoke(CreateForumTopic(channel=peer, title=title, random_id=rnd_id))
    if hasattr(r, "updates"):
        for u in r.updates:
            if hasattr(u, "message") and hasattr(u.message, "id"):
                return u.message.id
            if hasattr(u, "id"):
                return u.id
    raise Exception("Topic ID મળ્યો નથી")

@app.on_message(filters.command("maketopics") & filters.private)
async def make_topics_command(client, message):
    user_id = message.chat.id
    try:
        source_ask = await app.ask(user_id, "🔗 **સ્ટેપ 1:** સોર્સ ગ્રુપની લિંક મોકલો.\n(દા.ત. `https://t.me/c/123456789/4/50`)")
        source_link = source_ask.text.strip()
        if "t.me/c/" not in source_link:
            return await app.send_message(user_id, "❌ ખોટી લિંક! `t.me/c/...` લિંક મોકલો.")
        parts = source_link.split("/")
        idx = parts.index("c")
        source_chat_id = int("-100" + parts[idx + 1])
        nums = parts[idx + 2:]
        if len(nums) == 1:
            extracted_topic_id = 1
            start_msg_id = int(nums[0])
        else:
            extracted_topic_id = int(nums[-2])
            start_msg_id = int(nums[-1])
        target_ask = await app.ask(user_id, "🎯 **સ્ટેપ 2:** નવા ટાર્ગેટ ગ્રુપનો ID મોકલો.\n(ID `-100` થી શરૂ થવો જોઈએ.)")
        target_chat_id = int(target_ask.text.strip())
        limit_ask = await app.ask(user_id, "🔢 **સ્ટેપ 3:** કેટલા મેસેજ સ્કેન કરવા છે?\n(દા.ત. 1, 10, 50)")
        limit = int(limit_ask.text.strip())
    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: `{e}`")

    status_msg = await app.send_message(user_id, "⏳ Userbot ચાલુ થાય છે...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status_msg.edit("❌ Userbot ચાલુ થયો નથી! પહેલા `/login` કરો.")

    await status_msg.edit("🔍 મેસેજ સ્કેન કરી રહ્યો છું...")
    unique_topics = set()

    for i in range(limit):
        msg_id = start_msg_id + i
        try:
            msg = await userbot.get_messages(source_chat_id, msg_id)
            if not msg or msg.empty or msg.service:
                continue
            topic_id = getattr(msg, "message_thread_id", None)
            if not topic_id or topic_id == 1:
                topic_id = extracted_topic_id
            unique_topics.add(topic_id)
            await asyncio.sleep(0.3)
        except FloodWait as e:
            await asyncio.sleep(e.value + 2)
        except Exception:
            pass

    mapped_topics = {}

    for t_id in unique_topics:
        if t_id == 1:
            mapped_topics[t_id] = None
            continue
        try:
            t_name = f"Mirror Topic {t_id}"
            new_topic_id = await create_topic(target_chat_id, t_name)
            mapped_topics[t_id] = new_topic_id
            await app.send_message(user_id, f"✅ Topic `{t_name}` બની ગયો!")
            await asyncio.sleep(2)
        except FloodWait as e:
            await asyncio.sleep(e.value + 2)
            try:
                new_topic_id = await create_topic(target_chat_id, f"Mirror Topic {t_id}")
                mapped_topics[t_id] = new_topic_id
            except Exception as ex:
                mapped_topics[t_id] = None
                await app.send_message(user_id, f"❌ Topic {t_id} ના બની શક્યો:\n`{ex}`")
        except Exception as e:
            mapped_topics[t_id] = None
            await app.send_message(user_id, f"⚠️ Topic {t_id} ના બની શક્યો!\n`{e}`")

    user_mirror_data[user_id] = {
        "source_chat_id": source_chat_id,
        "target_chat_id": target_chat_id,
        "start_msg_id": start_msg_id,
        "limit": limit,
        "extracted_topic_id": extracted_topic_id,
        "mapped_topics": mapped_topics
    }

    await status_msg.edit("🎉 **બધા ટોપિક્સ બની ગયા છે!**\n\nહવે:\n👉 `/startmirror`")

@app.on_message(filters.command("startmirror") & filters.private)
async def start_mirror_command(client, message):
    user_id = message.chat.id

    if user_id not in user_mirror_data:
        return await app.send_message(user_id, "❌ પહેલા `/maketopics` ચલાવો.")

    data = user_mirror_data[user_id]
    status_msg = await app.send_message(user_id, "🚀 **વિડીયો ટ્રાન્સફર ચાલુ છે...**")
    userbot = await initialize_userbot(user_id)

    if not userbot:
        return await status_msg.edit("❌ Userbot ચાલુ થયો નથી! પહેલા `/login` કરો.")

    success = 0
    failed = 0

    for i in range(data["limit"]):
        msg_id = data["start_msg_id"] + i
        try:
            msg = await userbot.get_messages(data["source_chat_id"], msg_id)
            if not msg or msg.empty or msg.service:
                continue

            source_topic_id = getattr(msg, "message_thread_id", None)
            if not source_topic_id or source_topic_id == 1:
                source_topic_id = data["extracted_topic_id"]

            target_topic_id = data["mapped_topics"].get(source_topic_id)

            if target_topic_id:
                user_chat_ids[user_id] = f"{data['target_chat_id']}/{target_topic_id}"
            else:
                user_chat_ids[user_id] = str(data["target_chat_id"])

            temp_msg = await app.send_message(user_id, f"🔄 Processing: `{msg_id}` | Topic: `{source_topic_id}`")

            fake_link = f"https://t.me/c/{str(data['source_chat_id']).replace('-100', '')}/{msg_id}"

            await get_msg(userbot, user_id, temp_msg.id, fake_link, 0, message)

            success += 1
            await asyncio.sleep(4)

        except FloodWait as e:
            await asyncio.sleep(e.value + 3)
        except Exception as e:
            failed += 1
            await app.send_message(user_id, f"⚠️ Message `{msg_id}` failed:\n`{e}`")

    user_chat_ids.pop(user_id, None)
    user_mirror_data.pop(user_id, None)

    await status_msg.edit(f"🎉 **Mirroring પૂરું થયું!**\n\n✅ સફળ: `{success}`\n❌ Failed: `{failed}`")
