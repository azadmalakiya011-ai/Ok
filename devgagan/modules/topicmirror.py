import asyncio
import time
from pyrogram import filters
from pyrogram.errors import FloodWait
from telethon.tl.functions.messages import CreateForumTopicRequest
from devgagan import app, sex
from devgagan.modules.main import initialize_userbot
from devgagan.core.get_func import get_msg, user_chat_ids

user_mirror_data = {}

async def create_topic(chat_id, title):
    if not sex or not sex.is_connected():
        raise Exception("Telethon client ચાલુ નથી.")
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
    raise Exception("Topic ID મળ્યો નથી.")

@app.on_message(filters.command("maketopics") & filters.private)
async def make_topics_command(client, message):
    user_id = message.chat.id
    try:
        ask = await app.ask(user_id, "🔗 Source group message link મોકલો.\nઉદાહરણ: `https://t.me/c/123456789/456` અથવા `https://t.me/c/123456789/10/456`")
        link = ask.text.strip()
        if "t.me/c/" not in link:
            return await app.send_message(user_id, "❌ ખોટી link.")
        parts = link.split("/")
        idx = parts.index("c")
        source_chat_id = int("-100" + parts[idx + 1])
        nums = [int(x.split("?")[0]) for x in parts[idx + 2:] if x.split("?")[0].isdigit()]
        if not nums:
            return await app.send_message(user_id, "❌ Link માં message ID મળ્યો નથી.")
        if len(nums) >= 2:
            extracted_topic_id, start_msg_id = nums[-2], nums[-1]
        else:
            extracted_topic_id, start_msg_id = 1, nums[0]
        ask = await app.ask(user_id, "🎯 Target Forum Group નો ID મોકલો.")
        target_chat_id = int(ask.text.strip())
        ask = await app.ask(user_id, "🔢 કેટલા messages scan કરવા છે?")
        limit = int(ask.text.strip())
        if limit < 1:
            return await app.send_message(user_id, "❌ Message count 1 કરતાં મોટો હોવો જોઈએ.")
    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ: `{e}`")

    status = await app.send_message(user_id, "⏳ Userbot ચાલુ થઈ રહ્યો છે...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ Userbot ચાલુ નથી. પહેલા `/login` કરો.")

    try:
        await status.edit("🔍 Messages scan થઈ રહ્યા છે...")
        topics = {}
        for i in range(limit):
            msg_id = start_msg_id + i
            try:
                msg = await userbot.get_messages(source_chat_id, msg_id)
                if not msg or getattr(msg, "empty", False) or getattr(msg, "service", False):
                    continue
                topic_id = getattr(msg, "message_thread_id", None) or extracted_topic_id
                if topic_id not in topics:
                    title = None
                    created = getattr(msg, "forum_topic_created", None)
                    if created:
                        title = getattr(created, "title", None)
                    topics[topic_id] = title or f"Mirror Topic {topic_id}"
                await asyncio.sleep(0.2)
            except FloodWait as e:
                await asyncio.sleep(e.value + 2)
            except Exception:
                continue

        if not topics:
            return await status.edit("❌ કોઈ messages અથવા topics મળ્યા નથી.")

        mapped = {}
        for topic_id, title in topics.items():
            if topic_id == 1:
                mapped[topic_id] = None
                continue
            try:
                new_id = await create_topic(target_chat_id, title)
                mapped[topic_id] = new_id
                await app.send_message(user_id, f"✅ `{title}` → Topic ID `{new_id}`")
            except FloodWait as e:
                await asyncio.sleep(e.value + 2)
                try:
                    new_id = await create_topic(target_chat_id, title)
                    mapped[topic_id] = new_id
                except Exception as err:
                    mapped[topic_id] = None
                    await app.send_message(user_id, f"❌ `{title}`: `{err}`")
            except Exception as e:
                mapped[topic_id] = None
                await app.send_message(user_id, f"❌ `{title}`: `{e}`")
            await asyncio.sleep(1)

        user_mirror_data[user_id] = {
            "source_chat_id": source_chat_id,
            "target_chat_id": target_chat_id,
            "start_msg_id": start_msg_id,
            "limit": limit,
            "extracted_topic_id": extracted_topic_id,
            "mapped_topics": mapped
        }
        created_count = sum(1 for v in mapped.values() if v)
        await status.edit(
            "🎉 **Topic scan પૂરું થયું!**\n"
            f"📌 મળેલા topics: `{len(topics)}`\n"
            f"✅ બનાવેલા topics: `{created_count}`\n\n"
            "હવે `/startmirror` મોકલો."
        )
    finally:
        try:
            await userbot.stop()
        except Exception:
            pass

@app.on_message(filters.command("startmirror") & filters.private)
async def start_mirror_command(client, message):
    user_id = message.chat.id
    data = user_mirror_data.get(user_id)
    if not data:
        return await app.send_message(user_id, "❌ પહેલા `/maketopics` ચલાવો.")

    status = await app.send_message(user_id, "🚀 Mirroring ચાલુ છે...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ Userbot ચાલુ નથી. પહેલા `/login` કરો.")

    success = 0
    failed = 0
    try:
        for i in range(data["limit"]):
            msg_id = data["start_msg_id"] + i
            try:
                msg = await userbot.get_messages(data["source_chat_id"], msg_id)
                if not msg or getattr(msg, "empty", False) or getattr(msg, "service", False):
                    continue

                source_topic_id = getattr(msg, "message_thread_id", None) or data["extracted_topic_id"]
                target_topic_id = data["mapped_topics"].get(source_topic_id)

                if target_topic_id:
                    user_chat_ids[user_id] = f'{data["target_chat_id"]}/{target_topic_id}'
                else:
                    user_chat_ids[user_id] = str(data["target_chat_id"])

                temp = await app.send_message(user_id, f"🔄 Message `{msg_id}` process થઈ રહ્યો છે...")
                fake_link = f'https://t.me/c/{str(data["source_chat_id"]).replace("-100", "")}/{msg_id}'
                await get_msg(userbot, user_id, temp.id, fake_link, 0, message)
                success += 1
                await asyncio.sleep(4)
            except FloodWait as e:
                await asyncio.sleep(e.value + 3)
            except Exception as e:
                failed += 1
                await app.send_message(user_id, f"⚠️ Message `{msg_id}` નિષ્ફળ: `{e}`")

        await status.edit(
            "🎉 **Mirroring પૂરું થયું!**\n\n"
            f"✅ સફળ: `{success}`\n"
            f"❌ નિષ્ફળ: `{failed}`"
        )
    finally:
        user_chat_ids.pop(user_id, None)
        try:
            await userbot.stop()
        except Exception:
            pass
