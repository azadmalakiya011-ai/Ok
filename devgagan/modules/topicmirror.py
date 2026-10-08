import asyncio
from pyrogram import filters
from pyrogram.errors import FloodWait
from devgagan import app
from devgagan.modules.main import initialize_userbot
from devgagan.core.get_func import get_msg, user_chat_ids

user_mirror_data = {}

async def create_topic(chat_id, title):
    result = await app.create_forum_topic(chat_id, title)
    topic_id = getattr(result, "message_thread_id", None) or getattr(result, "id", None)
    if not topic_id:
        raise Exception("Topic ID મળ્યો નથી")
    return topic_id

@app.on_message(filters.command("maketopics") & filters.private)
async def make_topics_command(client, message):
    user_id = message.chat.id
    try:
        source_ask = await app.ask(user_id, "🔗 **સ્ટેપ 1:** સોર્સ ગ્રુપની લિંક મોકલો.\nદા.ત. `https://t.me/c/123456789/4/50`")
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
        target_ask = await app.ask(user_id, "🎯 **સ્ટેપ 2:** ટાર્ગેટ forum group નો ID મોકલો.\nદા.ત. `-1001234567890`")
        target_chat_id = int(target_ask.text.strip())
        limit_ask = await app.ask(user_id, "🔢 **સ્ટેપ 3:** કેટલા મેસેજ સ્કેન કરવા છે?")
        limit = int(limit_ask.text.strip())
    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: `{e}`")

    status_msg = await app.send_message(user_id, "⏳ Userbot ચાલુ થાય છે...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status_msg.edit("❌ Userbot ચાલુ થયો નથી! પહેલા `/login` કરો.")

    try:
        await status_msg.edit("🔍 Source messages સ્કેન કરી રહ્યો છું...")
        unique_topics = set()
        topic_names = {}

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

                created = getattr(msg, "forum_topic_created", None)
                if created and getattr(created, "title", None):
                    topic_names[topic_id] = created.title

                await asyncio.sleep(0.2)
            except FloodWait as e:
                await asyncio.sleep(e.value + 2)
            except Exception:
                continue

        if not unique_topics:
            return await status_msg.edit("❌ કોઈ topic/message મળ્યો નથી.")

        mapped_topics = {}

        for topic_id in sorted(unique_topics):
            if topic_id == 1:
                mapped_topics[topic_id] = None
                continue

            title = topic_names.get(topic_id, f"Mirror Topic {topic_id}")

            for attempt in range(3):
                try:
                    new_topic_id = await create_topic(target_chat_id, title[:128])
                    mapped_topics[topic_id] = new_topic_id
                    await app.send_message(user_id, f"✅ `{title}` → Topic `{new_topic_id}`")
                    break
                except FloodWait as e:
                    await asyncio.sleep(e.value + 2)
                except Exception as e:
                    if attempt == 2:
                        mapped_topics[topic_id] = None
                        await app.send_message(user_id, f"❌ `{title}` બની શક્યો નથી:\n`{e}`")
                    else:
                        await asyncio.sleep(2)

        user_mirror_data[user_id] = {
            "source_chat_id": source_chat_id,
            "target_chat_id": target_chat_id,
            "start_msg_id": start_msg_id,
            "limit": limit,
            "extracted_topic_id": extracted_topic_id,
            "mapped_topics": mapped_topics
        }

        await status_msg.edit(
            "🎉 **Topics તૈયાર થઈ ગયા!**\n\n"
            f"📌 મળેલા Topics: `{len(unique_topics)}`\n"
            f"✅ બનાવેલા Topics: `{sum(1 for x in mapped_topics.values() if x)}`\n\n"
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

    if user_id not in user_mirror_data:
        return await app.send_message(user_id, "❌ પહેલા `/maketopics` ચલાવો.")

    data = user_mirror_data[user_id]
    status_msg = await app.send_message(user_id, "🚀 **Mirroring ચાલુ છે...**")
    userbot = await initialize_userbot(user_id)

    if not userbot:
        return await status_msg.edit("❌ Userbot ચાલુ થયો નથી! પહેલા `/login` કરો.")

    success = 0
    failed = 0

    try:
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

                temp_msg = await app.send_message(
                    user_id,
                    f"🔄 Processing `{msg_id}` | Topic `{source_topic_id}`"
                )

                fake_link = (
                    f"https://t.me/c/"
                    f"{str(data['source_chat_id']).replace('-100', '')}/"
                    f"{msg_id}"
                )

                await get_msg(
                    userbot,
                    user_id,
                    temp_msg.id,
                    fake_link,
                    0,
                    message
                )

                success += 1
                await asyncio.sleep(4)

            except FloodWait as e:
                await asyncio.sleep(e.value + 3)
                continue
            except Exception as e:
                failed += 1
                await app.send_message(
                    user_id,
                    f"⚠️ Message `{msg_id}` failed:\n`{e}`"
                )

        await status_msg.edit(
            "🎉 **Mirroring પૂરું થયું!**\n\n"
            f"✅ સફળ: `{success}`\n"
            f"❌ Failed: `{failed}`"
        )

    finally:
        user_chat_ids.pop(user_id, None)
        try:
            await userbot.stop()
        except Exception:
            pass
