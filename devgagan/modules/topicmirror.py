import asyncio
from pyrogram import filters
from pyrogram.errors import FloodWait
from devgagan import app
from devgagan.modules.main import initialize_userbot
from devgagan.core.get_func import get_msg, user_chat_ids

# બંને કમાન્ડ વચ્ચે ડેટા સાચવવા માટે
user_mirror_data = {}

# ==========================================
# કમાન્ડ 1: ખાલી ટોપિક્સ બનાવવા માટે
# ==========================================
@app.on_message(filters.command("maketopics") & filters.private)
async def make_topics_command(client, message):
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
        
        limit_ask = await app.ask(user_id, "🔢 **સ્ટેપ 3:** કેટલા મેસેજ સ્કેન કરવા છે?\n(દા.ત. 1, 10, 50)")
        limit = int(limit_ask.text)
        
    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: {e}")

    status_msg = await app.send_message(user_id, "⏳ Userbot ચાલુ થાય છે... થોડીવાર રાહ જુઓ.")
    userbot = await initialize_userbot(user_id)
    
    if not userbot:
        return await status_msg.edit("❌ Userbot ચાલુ ના થયો! પહેલા `/login` કરો.")

    await status_msg.edit("🔍 મેસેજ સ્કેન કરીને નવા ટોપિક્સ બનાવી રહ્યો છું...")
    
    unique_topics = set()
    mapped_topics = {}
    
    # સ્કેનિંગ
    for i in range(limit):
        msg_id = start_msg_id + i
        try:
            msg = await userbot.get_messages(source_chat_id, msg_id)
            if not msg or msg.empty or msg.service:
                continue
            
            source_topic_id = msg.message_thread_id
            if not source_topic_id or source_topic_id == 1:
                source_topic_id = extracted_topic_id
            
            unique_topics.add(source_topic_id)
            await asyncio.sleep(0.3)
        except Exception:
            pass

    # ટોપિક બનાવવા
    for t_id in unique_topics:
        if t_id == 1:
            mapped_topics[t_id] = None
        else:
            try:
                t_name = f"Mirror Topic {t_id}"
                new_topic = await app.create_forum_topic(chat_id=target_chat_id, title=t_name)
                mapped_topics[t_id] = new_topic.message_thread_id
                await app.send_message(user_id, f"✅ નવો ટોપિક '{t_name}' બની ગયો!")
                await asyncio.sleep(2)
            except Exception as e:
                await app.send_message(user_id, f"⚠️ ટોપિક {t_id} ના બની શક્યો! Error: {e}")
                mapped_topics[t_id] = None

    # આગળના કમાન્ડ માટે ડેટા સેવ કરો
    user_mirror_data[user_id] = {
        'source_chat_id': source_chat_id,
        'target_chat_id': target_chat_id,
        'start_msg_id': start_msg_id,
        'limit': limit,
        'extracted_topic_id': extracted_topic_id,
        'mapped_topics': mapped_topics
    }

    await status_msg.edit("🎉 **બધા ટોપિક્સ બની ગયા છે!**\n\nહવે વિડીયો ડાઉનલોડ/અપલોડ ચાલુ કરવા માટે નીચેનો કમાન્ડ આપો:\n👉 `/startmirror`")


# ==========================================
# કમાન્ડ 2: ફાઈલો ડાઉનલોડ/અપલોડ કરવા માટે
# ==========================================
@app.on_message(filters.command("startmirror") & filters.private)
async def start_mirror_command(client, message):
    user_id = message.chat.id
    
    if user_id not in user_mirror_data:
        return await app.send_message(user_id, "❌ કોઈ ડેટા મળ્યો નથી! પહેલા `/maketopics` કમાન્ડ વાપરો.")
        
    data = user_mirror_data[user_id]
    status_msg = await app.send_message(user_id, "🚀 **વિડીયો ટ્રાન્સફર ચાલુ થાય છે!**...")
    
    userbot = await initialize_userbot(user_id)
    if not userbot:
        return await status_msg.edit("❌ Userbot ચાલુ ના થયો! પહેલા `/login` કરો.")

    success = 0
    for i in range(data['limit']):
        msg_id = data['start_msg_id'] + i
        try:
            msg = await userbot.get_messages(data['source_chat_id'], msg_id)
            if not msg or msg.empty or msg.service:
                continue
            
            source_topic_id = msg.message_thread_id
            if not source_topic_id or source_topic_id == 1:
                source_topic_id = data['extracted_topic_id']
                
            target_topic_id = data['mapped_topics'].get(source_topic_id)
            
            if target_topic_id:
                user_chat_ids[user_id] = f"{data['target_chat_id']}/{target_topic_id}"
            else:
                user_chat_ids[user_id] = str(data['target_chat_id'])

            temp_msg = await app.send_message(user_id, f"🔄 પ્રોસેસિંગ મેસેજ ID: {msg_id} (Topic: {source_topic_id})...")
            
            fake_link = f"https://t.me/c/{str(data['source_chat_id']).replace('-100', '')}/{msg_id}"
            await get_msg(userbot, user_id, temp_msg.id, fake_link, 0, message)
            
            success += 1
            await asyncio.sleep(4)
            
        except FloodWait as e:
            await asyncio.sleep(e.value + 3)
        except Exception as e:
            pass
            
    user_chat_ids.pop(user_id, None)
    user_mirror_data.pop(user_id, None) # ક્લીનઅપ
    
    await app.send_message(user_id, f"🎉 **Topic Mirroring પૂરું થયું!**\n\n✅ સફળતાપૂર્વક {success} ફાઈલો/મેસેજ ટ્રાન્સફર થયા.")
    
