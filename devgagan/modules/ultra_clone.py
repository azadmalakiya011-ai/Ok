import asyncio
from pyrogram import filters, Client
from pyrogram.errors import FloodWait
from devgagan import app
from config import API_ID, API_HASH
from devgagan.core.mongo.db import get_data

TOPIC_MAP = {}

@app.on_message(filters.command("startcopy"))
async def ultra_start_copy(client, message):
    args = message.text.split()
    if len(args) != 3:
        return await message.reply("❌ સાચો કમાન્ડ: `/startcopy [સોર્સ_ગ્રુપ_ID] [ટાર્ગેટ_ગ્રુપ_ID]`")
        
    source_chat = int(args[1])
    target_chat = int(args[2])
    user_id = message.from_user.id
    
    user_data = await get_data(user_id)
    session = user_data.get("session") if user_data else None
    
    if not session:
        return await message.reply("❌ સેશન નથી મળતું! પહેલા `/login` કરો.")
        
    m = await message.reply("🚀 કોપી કરવાનું ચાલુ થઈ ગયું છે...\n\n(હવે ટોપિક્સ જાતે જ બની જશે, `/maketopics` ની જરૂર નથી!)")
    
    try:
        userbot = Client(f"ubot_copy_{user_id}", api_id=API_ID, api_hash=API_HASH, session_string=session)
        await userbot.start()
    except Exception as e:
        return await m.edit(f"❌ લોગીન પ્રોબ્લેમ: {e}")
        
    copied_count = 0
    failed_count = 0
    
    if source_chat not in TOPIC_MAP:
        TOPIC_MAP[source_chat] = {}
        
    try:
        async for msg in userbot.get_chat_history(source_chat):
            if getattr(msg, "message_thread_id", None):
                old_thread_id = msg.message_thread_id
                
                # જો ટોપિક હજુ ના બનાવ્યો હોય તો બોટ જાતે બનાવશે
                if old_thread_id not in TOPIC_MAP[source_chat]:
                    try:
                        # જૂના ગ્રુપમાંથી ટોપિકનું નામ શોધવું
                        t_msg = await userbot.get_messages(source_chat, old_thread_id)
                        title = t_msg.forum_topic_created.title if (t_msg and t_msg.forum_topic_created) else f"Folder {old_thread_id}"
                        
                        # નવા ગ્રુપમાં સેમ ટોપિક બનાવવો
                        new_topic = await client.create_forum_topic(target_chat, title)
                        TOPIC_MAP[source_chat][old_thread_id] = new_topic.id
                        await asyncio.sleep(2)
                    except Exception:
                        continue # કોઈ એરર આવે તો ટોપિક સ્કીપ કરો
                        
                new_thread_id = TOPIC_MAP[source_chat][old_thread_id]
                
                try:
                    await msg.copy(chat_id=target_chat, reply_to_message_id=new_thread_id)
                    copied_count += 1
                    
                    if copied_count % 20 == 0:
                        await m.edit(f"⏳ **લાઈવ પ્રોગ્રેસ:**\n✅ કોપી થયા: {copied_count}\n❌ ફેલ: {failed_count}")
                        
                    await asyncio.sleep(2)
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 2)
                    await msg.copy(chat_id=target_chat, reply_to_message_id=new_thread_id)
                    copied_count += 1
                except Exception:
                    failed_count += 1
                    
        await m.edit(f"🎉 **ક્લોન કમ્પ્લીટ!**\n✅ ટોટલ કોપી: {copied_count}\n❌ ફેલ: {failed_count}")
    except Exception as e:
        await m.edit(f"❌ એરર આવી: {e}")
    finally:
        await userbot.stop()
        
