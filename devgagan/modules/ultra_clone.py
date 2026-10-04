import asyncio
from pyrogram import filters, Client
from pyrogram.errors import FloodWait
from devgagan import app
from config import API_ID, API_HASH
from devgagan.core.mongo.db import get_session

# મેમરીમાં ટોપિકનો રસ્તો યાદ રાખવા માટે
TOPIC_MAP = {}

@app.on_message(filters.command("maketopics"))
async def ultra_clone_topics(client, message):
    args = message.text.split()
    if len(args) != 3:
        return await message.reply("❌ સાચો કમાન્ડ: `/maketopics [સોર્સ_ગ્રુપ_ID] [ટાર્ગેટ_ગ્રુપ_ID]`")
        
    source_chat = int(args[1])
    target_chat = int(args[2])
    user_id = message.from_user.id
    
    # devgagan ના ડેટાબેઝમાંથી તમારું સેશન ખેંચશે
    session = await get_session(user_id)
    if not session:
        return await message.reply("❌ સેશન નથી મળતું! પહેલા `/login` કમાન્ડ આપીને તમારો નંબર નાખીને લોગીન કરો.")
        
    m = await message.reply("⏳ સિસ્ટમ સ્ટાર્ટ થાય છે... જૂના ગ્રુપના ટોપિક્સ ફેચ (Fetch) કરી રહ્યો છું.")
    
    # Userbot ચાલુ કરીએ (જેથી બીજાના ગ્રુપમાંથી ડેટા વાંચી શકાય)
    try:
        userbot = Client(f"ubot_{user_id}", api_id=API_ID, api_hash=API_HASH, session_string=session)
        await userbot.start()
    except Exception as e:
        return await m.edit(f"❌ લોગીન સ્ટાર્ટ કરવામાં એરર (ફરી લોગીન કરો): {e}")

    index_text = "📁 **All Topics Index:**\n\n"
    TOPIC_MAP[source_chat] = {}
    
    try:
        # Userbot જૂના ગ્રુપના બધા ટોપિક સ્કેન કરશે
        async for topic in userbot.get_forum_topics(source_chat):
            if topic.title:
                # બોટ તમારા નવા ગ્રુપમાં સેમ નામના ટોપિક બનાવશે
                new_topic = await client.create_forum_topic(target_chat, topic.title)
                TOPIC_MAP[source_chat][topic.id] = new_topic.id
                
                # ઇન્ડેક્સ માટે લિંક જનરેટ
                clean_target_id = str(target_chat).replace("-100", "")
                topic_link = f"https://t.me/c/{clean_target_id}/{new_topic.id}"
                index_text += f"🔹 [{topic.title}]({topic_link})\n"
                
                await asyncio.sleep(1.5) # Telegram બેન ના કરે એટલે બ્રેક
                
        # છેલ્લે Index ટોપિક બનાવીને તેમાં લિસ્ટ મોકલશે
        index_topic = await client.create_forum_topic(target_chat, "📑 All Topics Index")
        await client.send_message(target_chat, index_text, message_thread_id=index_topic.id, disable_web_page_preview=True)
        
        await m.edit("✅ એકદમ પરફેક્ટ! બધા ટોપિક્સ અને ઇન્ડેક્સ બની ગયા છે.\n\n👉 હવે ડેટા ખેંચવા માટે કમાન્ડ આપો:\n`/startcopy સોર્સ_ID ટાર્ગેટ_ID`")
    except Exception as e:
        await m.edit(f"❌ ટોપિક બનાવવામાં એરર: {e}")
    finally:
        await userbot.stop()


@app.on_message(filters.command("startcopy"))
async def ultra_start_copy(client, message):
    args = message.text.split()
    if len(args) != 3:
        return await message.reply("❌ સાચો કમાન્ડ: `/startcopy [સોર્સ_ગ્રુપ_ID] [ટાર્ગેટ_ગ્રુપ_ID]`")
        
    source_chat = int(args[1])
    target_chat = int(args[2])
    user_id = message.from_user.id
    
    if source_chat not in TOPIC_MAP:
        return await message.reply("❌ કોઈ ટોપિક લિસ્ટ મળ્યું નથી! પહેલા `/maketopics` કમાન્ડ ચલાવો.")
        
    session = await get_session(user_id)
    if not session:
        return await message.reply("❌ પહેલા `/login` કરો!")
        
    m = await message.reply("🚀 ફાઈલો અને વિડીયો કોપી કરવાનું એન્જિન ચાલુ થઈ ગયું છે... આમાં સમય લાગશે.")
    
    try:
        userbot = Client(f"ubot_copy_{user_id}", api_id=API_ID, api_hash=API_HASH, session_string=session)
        await userbot.start()
    except Exception as e:
        return await m.edit(f"❌ યુઝરબોટ સ્ટાર્ટ પ્રોબ્લેમ: {e}")
        
    copied_count = 0
    failed_count = 0
    
    try:
        # જૂના ગ્રુપની પૂરી ચેટ હિસ્ટ્રી ફેચ કરશે
        async for msg in userbot.get_chat_history(source_chat):
            if getattr(msg, "message_thread_id", None):
                old_thread_id = msg.message_thread_id
                
                if old_thread_id in TOPIC_MAP[source_chat]:
                    new_thread_id = TOPIC_MAP[source_chat][old_thread_id]
                    
                    try:
                        # Userbot જાતે જ મેસેજ ટાર્ગેટ ગ્રુપના સાચા ટોપિકમાં કોપી કરશે
                        await msg.copy(chat_id=target_chat, reply_to_message_id=new_thread_id)
                        copied_count += 1
                        
                        # દર 20 મેસેજ પછી લાઈવ પ્રોગ્રેસ અપડેટ કરશે
                        if copied_count % 20 == 0:
                            await m.edit(f"⏳ **લાઈવ પ્રોગ્રેસ:**\n\n✅ ટ્રાન્સફર થયા: {copied_count}\n❌ સ્કીપ/ફેલ: {failed_count}\n\nપ્લીઝ રાહ જુઓ...")
                            
                        await asyncio.sleep(2) # FloodWait પ્રોટેક્શન
                        
                    except FloodWait as fw:
                        # જો Telegram સ્પીડ લિમિટ લગાવે તો જાતે જ ઉભો રહી જશે અને પાછો ચાલુ થશે
                        await asyncio.sleep(fw.value + 2)
                        await msg.copy(chat_id=target_chat, reply_to_message_id=new_thread_id)
                        copied_count += 1
                    except Exception:
                        failed_count += 1
                        
        await m.edit(f"🎉 **મિશન કમ્પ્લીટ! આખું ગ્રુપ ક્લોન થઈ ગયું છે.**\n\n✅ ટોટલ ટ્રાન્સફર: {copied_count}\n❌ ડિલીટ/ફેલ: {failed_count}")
    except Exception as e:
        await m.edit(f"❌ ડેટા કોપીમાં એરર: {e}")
    finally:
        await userbot.stop()
  
