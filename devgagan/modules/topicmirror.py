import asyncio
import time
from pyrogram import filters
from pyrogram.errors import FloodWait
from telethon.tl.functions.messages import CreateForumTopicRequest, GetForumTopicsRequest
from devgagan import app, sex
from devgagan.modules.main import initialize_userbot
from devgagan.core.get_func import get_msg, user_chat_ids

user_mirror_data = {}

async def create_topic(chat_id, title):
    if not sex or not sex.is_connected():
        raise Exception("Telethon ક્લાયન્ટ ચાલુ નથી.")
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
        ask = await app.ask(user_id, "🔗 સોર્સ ગ્રુપના કોઈપણ એક મેસેજની લિંક મોકલો:\n(દા.ત. `https://t.me/c/123456789/4/50`)")
        link = ask.text.strip()
        if "t.me/c/" not in link:
            return await app.send_message(user_id, "❌ ખોટી લિંક! પ્રાઇવેટ ગ્રુપની લિંક મોકલો.")
        
        parts = link.split("/")
        idx = parts.index("c")
        source_chat_id = int("-100" + parts[idx + 1])
        nums = [int(x.split("?")[0]) for x in parts[idx + 2:] if x.split("?")[0].isdigit()]
        if not nums:
            return await app.send_message(user_id, "❌ લિંકમાં મેસેજ ID મળ્યો નથી.")
        
        if len(nums) >= 2:
            extracted_topic_id, start_msg_id = int(nums[-2]), int(nums[-1])
        else:
            extracted_topic_id, start_msg_id = 1, int(nums[0])

        ask = await app.ask(user_id, "🎯 ટાર્ગેટ ગ્રુપ ID મોકલો (-100 થી શરૂ થતો):")
        target_chat_id = int(ask.text.strip())

        ask = await app.ask(user_id, "🔢 કેટલા મેસેજ સ્કેન કરવા છે? (દા.ત. 100):")
        limit = int(ask.text.strip())
        if limit < 1:
            return await app.send_message(user_id, "❌ સંખ્યા 1 થી વધુ હોવી જોઈએ.")
    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: `{e}`")

    status = await app.send_message(user_id, "⏳ યુઝરબોટ ચાલુ થઈ રહ્યો છે...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ ના થયો! પહેલા `/login` કરો.")

    try:
        await status.edit("🔍 જૂના ગ્રુપમાંથી સાચા નામો સાથે બધા ટોપિક્સ શોધાઈ રહ્યા છે...")
        topics = {}

        # 🌟 ૧. Userbot દ્વારા ડાયરેક્ટ Raw API થી સાચા નામો ખેંચવા 🌟
        try:
            peer = await userbot.resolve_peer(source_chat_id)
            from pyrogram.raw.functions.channels import GetForumTopics
            res = await userbot.invoke(GetForumTopics(
                channel=peer,
                offset_date=0,
                offset_id=0,
                offset_topic=0,
                limit=100
            ))
            for t in getattr(res, "topics", []):
                t_id = getattr(t, "id", None)
                t_title = getattr(t, "title", None)
                if t_id and t_title and int(t_id) != 1:
                    topics[int(t_id)] = t_title
        except Exception:
            pass

        # 🌟 ૨. જો સીધા ના મળે, તો જે મેસેજ સ્કેન થાય એના પહેલા ક્રિએશન મેસેજમાંથી સાચું નામ લેવું 🌟
        scan_topics = set()
        for mid in range(start_msg_id, start_msg_id + limit):
            try:
                msg = await userbot.get_messages(source_chat_id, mid)
                if not msg or getattr(msg, "empty", False):
                    continue
                th_id = getattr(msg, "message_thread_id", None) or extracted_topic_id
                if th_id and int(th_id) != 1:
                    scan_topics.add(int(th_id))
            except Exception:
                continue

        for t_id in scan_topics:
            if t_id not in topics:
                try:
                    # ટોપિક જે મેસેજથી બન્યો હોય તેનો ID એ જ ટોપિકનો ID હોય છે
                    t_init_msg = await userbot.get_messages(source_chat_id, t_id)
                    created = getattr(t_init_msg, "forum_topic_created", None)
                    if created and getattr(created, "title", None):
                        topics[t_id] = created.title
                    else:
                        topics[t_id] = f"Topic {t_id}"
                except Exception:
                    topics[t_id] = f"Topic {t_id}"

        if not topics:
            return await status.edit("❌ કોઈ ટોપિક મળ્યા નથી.")

        mapped = {}
        total_topics = len(topics)
        current_idx = 0
        summary_lines = ["📋 **ટોપિક લિસ્ટ:**"]
        progress_msg = await app.send_message(user_id, "🛠️ ટોપિક્સ બનાવવાનું ચાલુ છે...")

        for topic_id, title in topics.items():
            current_idx += 1
            if topic_id == 1:
                mapped[topic_id] = None
                continue
            try:
                new_id = await create_topic(target_chat_id, title)
                mapped[topic_id] = new_id
                summary_lines.append(f"`{topic_id}` ➔ `{title[:18]}`")
            except FloodWait as e:
                await asyncio.sleep(e.value + 2)
                try:
                    new_id = await create_topic(target_chat_id, title)
                    mapped[topic_id] = new_id
                    summary_lines.append(f"`{topic_id}` ➔ `{title[:18]}`")
                except Exception:
                    mapped[topic_id] = None
            except Exception:
                mapped[topic_id] = None

            if current_idx % 3 == 0 or current_idx == total_topics:
                text_to_show = "\n".join(summary_lines)
                try:
                    await progress_msg.edit(f"> {text_to_show}"[:4000])
                except Exception:
                    pass
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
            f"🎉 **બધા ટોપિક્સ બની ગયા!**\n"
            f"બનેલા ટોપિક્સ: `{created_count}` / `{total_topics}`\n\n"
            "👉 વિડીયો અપલોડ કરવા કમાન્ડ આપો:\n"
            "દા.ત. `/startmirror 1012` અથવા `/startmirror 1016`"
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

    args = message.text.strip().split()
    if len(args) < 2 or not args[1].isdigit():
        return await app.send_message(
            user_id, 
            "⚠️ **સાચો કમાન્ડ વાપરો:**\n\n"
            "જે ટોપિકના વિડીયો મોકલવા હોય તેનો ID લખો.\n"
            "દા.ત. `/startmirror 1012`"
        )

    selected_topic_id = int(args[1])
    target_topic_id = data["mapped_topics"].get(selected_topic_id)

    if not target_topic_id:
        return await app.send_message(user_id, f"❌ ટોપિક ID `{selected_topic_id}` નો મેળ ટાર્ગેટ ગ્રુપમાં મળ્યો નથી.")

    user_chat_ids[user_id] = f'{data["target_chat_id"]}/{target_topic_id}'

    status = await app.send_message(user_id, f"🚀 **Topic {selected_topic_id}** ના વિડીયો ટ્રાન્સફર થાય છે...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ નથી. પહેલા `/login` કરો.")

    success = 0
    failed = 0
    try:
        async for msg in userbot.get_chat_history(data["source_chat_id"]):
            if not msg or getattr(msg, "empty", False) or getattr(msg, "service", False):
                continue

            msg_topic = getattr(msg, "message_thread_id", None)
            
            if msg_topic and int(msg_topic) == selected_topic_id:
                temp = await app.send_message(user_id, f"🔄 પ્રોસેસિંગ મેસેજ `{msg.id}`...")
                fake_link = f'https://t.me/c/{str(data["source_chat_id"]).replace("-100", "")}/{msg.id}'
                
                try:
                    await get_msg(userbot, user_id, temp.id, fake_link, 0, message)
                    success += 1
                except FloodWait as e:
                    await asyncio.sleep(e.value + 2)
                except Exception:
                    failed += 1
                finally:
                    try:
                        await temp.delete()
                    except Exception:
                        pass

                await asyncio.sleep(3)

        await status.edit(
            f"🎉 **Topic {selected_topic_id} નું કામ પૂરું થયું!**\n\n"
            f"✅ સફળ: `{success}` | ❌ નિષ્ફળ: `{failed}`"
        )
    finally:
        user_chat_ids.pop(user_id, None)
        try:
            await userbot.stop()
        except Exception:
            pass
            
