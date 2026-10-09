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
        raise Exception("Telethon client connect nathi.")
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
    raise Exception("Topic ID generate na thayo.")

@app.on_message(filters.command("maketopics") & filters.private)
async def make_topics_command(client, message):
    user_id = message.chat.id
    try:
        ask = await app.ask(user_id, "🔗 Source group message link moklo:\n(Example: `https://t.me/c/123456789/4/50`)")
        link = ask.text.strip()
        if "t.me/c/" not in link:
            return await app.send_message(user_id, "❌ Khoti link! Private group ni link j chalse.")
        
        parts = link.split("/")
        idx = parts.index("c")
        source_chat_id = int("-100" + parts[idx + 1])
        nums = [int(x.split("?")[0]) for x in parts[idx + 2:] if x.split("?")[0].isdigit()]
        if not nums:
            return await app.send_message(user_id, "❌ Link ma message ID na malyo.")
        
        if len(nums) >= 2:
            extracted_topic_id, start_msg_id = int(nums[-2]), int(nums[-1])
        else:
            extracted_topic_id, start_msg_id = 1, int(nums[0])

        ask = await app.ask(user_id, "🎯 Target Group ID moklo (-100 thi start thavu joie):")
        target_chat_id = int(ask.text.strip())

        ask = await app.ask(user_id, "🔢 Ketla messages scan karva chhe? (e.g. 100):")
        limit = int(ask.text.strip())
        if limit < 1:
            return await app.send_message(user_id, "❌ Limit 1 thi vadhu hovi joie.")
    except Exception as e:
        return await app.send_message(user_id, f"❌ Bhul thai: `{e}`")

    status = await app.send_message(user_id, "⏳ Userbot start thay chhe...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ Userbot chalu na thayo! Pehla `/login` karo.")

    try:
        await status.edit("🔍 Saacha naam sathe badha topics shodhai rahya chhe...")
        topics = {}

        # 1. Sharuat na message ID 1 thi scan karo jethi badha topic creation messages mali jaay
        scan_max = max(start_msg_id + limit, 150)
        for mid in range(1, scan_max):
            try:
                msg = await userbot.get_messages(source_chat_id, mid)
                if not msg or getattr(msg, "empty", False):
                    continue

                created = getattr(msg, "forum_topic_created", None)
                if created and getattr(created, "title", None):
                    topics[int(mid)] = created.title

                th_id = getattr(msg, "message_thread_id", None)
                if th_id and int(th_id) != 1 and int(th_id) not in topics:
                    topics[int(th_id)] = None

                await asyncio.sleep(0.02)
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception:
                continue

        # 2. Jo koi topic nu title baaki rahi gayu hoy to direct topic message thi title lavo
        for t_id in list(topics.keys()):
            if not topics[t_id]:
                try:
                    init_m = await userbot.get_messages(source_chat_id, t_id)
                    created = getattr(init_m, "forum_topic_created", None)
                    if created and getattr(created, "title", None):
                        topics[t_id] = created.title
                    else:
                        topics[t_id] = f"Topic {t_id}"
                except Exception:
                    topics[t_id] = f"Topic {t_id}"

        if not topics:
            return await status.edit("❌ Koyi topics na malya.")

        mapped = {}
        total_topics = len(topics)
        current_idx = 0
        summary_lines = ["📋 **Topic List:**"]
        progress_msg = await app.send_message(user_id, "🛠️ Topics banavanu chalu chhe...")

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

            if current_idx % 2 == 0 or current_idx == total_topics:
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
            f"🎉 **Badha Topics Bani Gaya!**\n"
            f"Baneela Topics: `{created_count}` / `{total_topics}`\n\n"
            "👉 Videos upload karva command aapo:\n"
            f"Example: `/startmirror {list(mapped.keys())[0]}`"
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
        return await app.send_message(user_id, "❌ Pehla `/maketopics` chalavo.")

    args = message.text.strip().split()
    if len(args) < 2 or not args[1].isdigit():
        return await app.send_message(
            user_id, 
            "⚠️ **Sacho command vapro:**\n\n"
            "Je topic na video mokalva hoy teno ID lakho.\n"
            "Example: `/startmirror 2`"
        )

    selected_topic_id = int(args[1])
    target_topic_id = data["mapped_topics"].get(selected_topic_id)

    if not target_topic_id:
        return await app.send_message(user_id, f"❌ Topic ID `{selected_topic_id}` target group ma match na thayo.")

    user_chat_ids[user_id] = f'{data["target_chat_id"]}/{target_topic_id}'

    status = await app.send_message(user_id, f"🚀 **Topic {selected_topic_id}** na videos transfer thay chhe...")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ Userbot chalu nathi. Pehla `/login` karo.")

    success = 0
    failed = 0
    try:
        async for msg in userbot.get_chat_history(data["source_chat_id"]):
            if not msg or getattr(msg, "empty", False) or getattr(msg, "service", False):
                continue

            msg_topic = getattr(msg, "message_thread_id", None)
            
            if msg_topic and int(msg_topic) == selected_topic_id:
                temp = await app.send_message(user_id, f"🔄 Processing Message `{msg.id}`...")
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
            f"🎉 **Topic {selected_topic_id} nu kaam puru thayu!**\n\n"
            f"✅ Safal: `{success}` | ❌ Nishfal: `{failed}`"
        )
    finally:
        user_chat_ids.pop(user_id, None)
        try:
            await userbot.stop()
        except Exception:
            pass
                        
