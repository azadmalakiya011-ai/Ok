import asyncio
from pyrogram import filters
from pyrogram.errors import FloodWait
from devgagan import app
from devgagan.modules.main import initialize_userbot
from devgagan.core.get_func import get_msg, user_chat_ids

mapped_topics = {}

@app.on_message(filters.command("topicmirror") & filters.private)
async def topic_mirror(client, message):
    user_id = message.chat.id
    
    try:
        source_ask = await app.ask(user_id, "🔗 **સ્ટેપ 1:** સોર્સ ગ્રુપની લિંક મોકલો.\n(દા.ત. `https://t.me/c/123456789/4/50`)")
        source_link = source_ask.text
        
        if 't.me/c/' in source_link or 't.me/b/' in source_link:
            parts = source_link.split('/')
            if 't.me/c/' in source_link:
                source_chat_id = int('-100' + parts[parts.index('c') + 1])
            else:
                source_chat_id = int(parts[parts.index('b') + 1])
                
            start_msg_id = int(parts[-1])
            
            if parts[-3] not in ['c', 'b'] and parts[-2].isdigit():
                extracted_topic_id = int(parts[-2])
            else:
                extracted_topic_id = 1
        else:
            return await app.send_message(user_id, "❌ ખોટી લિંક! પ્રાઇવેટ ગ્રુપની લિંક જ ચાલશે.")

        target_ask = await app.ask(user_id, "🎯 **સ્ટેપ 2:** નવા ટાર્ગેટ ગ્રુપ નો ID મોકલો.\n(ID -100 થી શરૂ થવો જોઈએ.)")
        target_chat_id = int(target_ask.text)
        
        limit_ask = await app.ask(user_id, "🔢 **સ્ટેપ 3:** કેટલા મેસેજ કોપી કરવા છે?\n(દા.ત. 1, 10, 50)")
        limit = int(limit_ask.text)
        
    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: {e}\nફરીથી /topicmirror કમાન્ડ આપો.")

    status_msg = await app.send_message(user_id, "⏳ Userbot ચાલુ થાય છે...")
    userbot = await initialize_userbot(user_id)
    
    if not userbot:
        return await status_msg.edit("❌ Userbot ચાલુ ના થયો! પહેલા `/login` કરો.")

    # ==========================================
    # Phase 1: Scanning Unique Topics
    # ==========================================
    await status_msg.edit("🔍 **Phase 1:** મેસેજ સ્કેન કરી રહ્યો છું...")
    unique_topics = set()
    
    for i in range(limit):
        msg_id = start_msg_id + i
        try:
            msg = await userbot.get_messages(source_chat_id, msg_id)
            if not msg or msg.empty or msg.service:
                continue
            
            source_topic_id = msg.message_thread_id or extracted_topic_id
            unique_topics.add(source_topic_id)
            await asyncio.sleep(0.5)
        except FloodWait as e:
            await asyncio.sleep(e.value + 3)
        except Exception:
            pass

    # ==========================================
    # Phase 2: Creating Topics
    # ==========================================
    await status_msg.edit(f"🛠️ **Phase 2:** સ્કેનિંગ પૂરું! ટોટલ {len(unique_topics)} ટોપિક મળ્યા. નવા ગ્રુપમાં ટોપિક્સ બનાવી રહ્યો છું...")
    
    for t_id in unique_topics:
        if t_id not in mapped_topics:
            if t_id == 1:
                mapped_topics[t_id] = None
            else:
                try:
                    t_name = f"Mirror Topic {t_id}"
                    new_topic = await app.create_forum_topic(chat_id=target_chat_id, title=t_name)
                    mapped_topics[t_id] = new_topic.message_thread_id
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"Topic Create Error: {e}")
                    mapped_topics[t_id] = None

    # ==========================================
    # Phase 3: Transferring Files
    # ==========================================
    await status_msg.edit("🚀 **Phase 3:** ટોપિક્સ બની ગયા! હવે ફાઈલો ડાઉનલોડ/અપલોડ ચાલુ...")
    success = 0
    
    for i in range(limit):
        msg_id = start_msg_id + i
        try:
            msg = await userbot.get_messages(source_chat_id, msg_id)
            if not msg or msg.empty or msg.service:
                continue
            
            source_topic_id = msg.message_thread_id or extracted_topic_id
            target_topic_id = mapped_topics.get(source_topic_id)
            
            if target_topic_id:
                user_chat_ids[user_id] = f"{target_chat_id}/{target_topic_id}"
            else:
                user_chat_ids[user_id] = str(target_chat_id)

            temp_msg = await app.send_message(user_id, f"🔄 પ્રોસેસિંગ મેસેજ ID: {msg_id}...")
            
            fake_link = f"https://t.me/c/{str(source_chat_id).replace('-100', '')}/{msg_id}"
            await get_msg(userbot, user_id, temp_msg.id, fake_link, 0, message)
            
            success += 1
            await asyncio.sleep(4)
            
        except FloodWait as e:
            await asyncio.sleep(e.value + 3)
        except Exception as e:
            print(f"Error on msg {msg_id}: {e}")
            
    user_chat_ids.pop(user_id, None)
    await app.send_message(user_id, f"🎉 **Topic Mirroring પૂરું થયું!**\n\n✅ સફળતાપૂર્વક {success} ફાઈલો/મેસેજ ટ્રાન્સફર થયા.")
    
