import asyncio
import time
from pyrogram import filters
from pyrogram.errors import FloodWait
from telethon.tl.functions.messages import CreateForumTopicRequest
from devgagan import app, sex
from devgagan.modules.main import initialize_userbot
from devgagan.core.get_func import get_msg, user_chat_ids

user_mirror_data = {}
mirror_cancel_flags = {}

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

    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: `{e}`")

    status = await app.send_message(user_id, "⚡ **યુઝરબોટથી ટોપિક્સ લિસ્ટ ફેચ થઈ રહ્યું છે...**")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ ના થયો! પહેલા `/login` કરો.")

    try:
        topics = {}

        # ડાયરેક્ટ Raw API થી ૧ જ સેકન્ડમાં આખું લિસ્ટ લાવવું
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
        except Exception as e:
            print(f"API Error: {e}")

        if not topics:
            return await status.edit("❌ ગ્રુપમાંથી ટોપિક્સ મળ્યા નહીં. ખાતરી કરો કે યુઝરબોટ એ ગ્રુપમાં જોડાયેલો છે.")

        await status.edit(f"🚀 **કુલ {len(topics)} ટોપિક મળ્યા! હવે નવા ગ્રુપમાં ફટાફટ બની રહ્યા છે...**")

        mapped = {}
        summary_lines = ["📋 **ટોપિક લિસ્ટ:**"]

        for topic_id, title in topics.items():
            if topic_id == 1:
                mapped[topic_id] = None
                continue
            try:
                new_id = await create_topic(target_chat_id, title)
                mapped[topic_id] = new_id
                summary_lines.append(f"`{topic_id}` ➔ `{title[:18]}`")
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try:
                    new_id = await create_topic(target_chat_id, title)
                    mapped[topic_id] = new_id
                    summary_lines.append(f"`{topic_id}` ➔ `{title[:18]}`")
                except Exception:
                    mapped[topic_id] = None
            except Exception:
                mapped[topic_id] = None

            await asyncio.sleep(0.1)

        user_mirror_data[user_id] = {
            "source_chat_id": source_chat_id,
            "target_chat_id": target_chat_id,
            "start_msg_id": start_msg_id,
            "extracted_topic_id": extracted_topic_id,
            "mapped_topics": mapped
        }
        
        created_count = sum(1 for v in mapped.values() if v)
        
        list_text = "\n".join(summary_lines)
        await app.send_message(user_id, f"> {list_text}"[:4000])

        await status.edit(
            f"🎉 **બધા ટોપિક્સ બની ગયા!**\n"
            f"બનેલા ટોપિક્સ: `{created_count}` / `{len(topics)}`\n\n"
            "👉 વિડીયો અપલોડ કરવા કમાન્ડ આપો:\n"
            f"દા.ત. `/startmirror {list(mapped.keys())[0]}`"
        )
    finally:
        try:
            await userbot.stop()
        except Exception:
            pass

@app.on_message(filters.command(["stopmirror", "cancelmirror"]) & filters.private)
async def stop_mirror_command(client, message):
    user_id = message.chat.id
    if user_id in mirror_cancel_flags:
        mirror_cancel_flags[user_id] = True
        await message.reply_text("🛑 **મિરરિંગ રોકવાની વિનંતી સ્વીકારી લીધી છે!**\nહાલની ફાઈલ પૂરી થતાં જ પ્રોસેસ તરત બંધ થઈ જશે.")
    else:
        await message.reply_text("⚠️ હાલમાં કોઈ મિરરિંગ પ્રોસેસ ચાલુ નથી.")

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
            "દા.ત. `/startmirror 2`"
        )

    selected_topic_id = int(args[1])
    target_topic_id = data["mapped_topics"].get(selected_topic_id)

    if not target_topic_id:
        return await app.send_message(user_id, f"❌ ટોપિક ID `{selected_topic_id}` ટાર્ગેટ ગ્રુપમાં મળ્યો નથી.")

    mirror_cancel_flags[user_id] = False
    user_chat_ids[user_id] = f'{data["target_chat_id"]}/{target_topic_id}'

    status = await app.send_message(user_id, f"🚀 **Topic {selected_topic_id}** ના વિડીયો ટ્રાન્સફર ચાલુ છે...\n(રોકવા માટે `/stopmirror` મોકલો)")
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status.edit("❌ યુઝરબોટ ચાલુ નથી. પહેલા `/login` કરો.")

    success = 0
    failed = 0
    was_cancelled = False
    try:
        async for msg in userbot.get_chat_history(data["source_chat_id"]):
            if mirror_cancel_flags.get(user_id, False):
                was_cancelled = True
                break

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

                await asyncio.sleep(2)

        if was_cancelled:
            await status.edit(
                f"🛑 **Topic {selected_topic_id} નું ટ્રાન્સફર રોકી દેવામાં આવ્યું છે!**\n\n"
                f"✅ સફળ: `{success}` | ❌ નિષ્ફળ: `{failed}`"
            )
        else:
            await status.edit(
                f"🎉 **Topic {selected_topic_id} નું કામ પૂરું થયું!**\n\n"
                f"✅ સફળ: `{success}` | ❌ નિષ્ફળ: `{failed}`\n\n"
                "👉 હવે પછીના ટોપિક માટે કમાન્ડ આપો."
            )
    finally:
        mirror_cancel_flags.pop(user_id, None)
        user_chat_ids.pop(user_id, None)
        try:
            await userbot.stop()
        except Exception:
            pass
                
