import asyncio
from pyrogram import filters
from pyrogram.errors import FloodWait
from devgagan import app
from devgagan.modules.main import initialize_userbot
from devgagan.core.get_func import copy_message_with_chat_id, user_chat_ids

# આ ડિક્શનરી યાદ રાખશે કે કયા જૂના ટોપિક સામે કયો નવો ટોપિક બનાવ્યો છે
mapped_topics = {}

@app.on_message(filters.command("topicmirror") & filters.private)
async def topic_mirror(client, message):
    user_id = message.chat.id
    
    try:
        # 1. Source Link માંગવી
        source_ask = await app.ask(user_id, "🔗 **સ્ટેપ 1:** સોર્સ ગ્રુપ (જ્યાંથી ડેટા લેવાનો છે) ના કોઈ પણ એક મેસેજની લિંક મોકલો.\n\n(દા.ત. `https://t.me/c/123456789/50`)")
        source_link = source_ask.text
        
        if 't.me/c/' in source_link or 't.me/b/' in source_link:
            parts = source_link.split('/')
            source_chat_id = int('-100' + parts[-2]) if 't.me/c/' in source_link else int(parts[-2])
            start_msg_id = int(parts[-1])
        else:
            return await app.send_message(user_id, "❌ ખોટી લિંક! પ્રાઇવેટ ગ્રુપની લિંક જ ચાલશે.")

        # 2. Target Group માંગવું
        target_ask = await app.ask(user_id, "🎯 **સ્ટેપ 2:** નવા ટાર્ગેટ ગ્રુપ (જ્યાં ડેટા નાખવાનો છે) નો ID મોકલો.\n\n(ID -100 થી શરૂ થવો જોઈએ. નોંધ: બોટ એ ગ્રુપમાં Admin હોવો જોઈએ અને તેમાં Topics ON હોવા જોઈએ.)")
        target_chat_id = int(target_ask.text)
        
        # 3. Message Count માંગવું
        limit_ask = await app.ask(user_id, "🔢 **સ્ટેપ 3:** કેટલા મેસેજ કોપી કરવા છે?\n\n(દા.ત. 10, 50, 100 લખીને મોકલો)")
        limit = int(limit_ask.text)
        
    except Exception as e:
        return await app.send_message(user_id, f"❌ ભૂલ થઈ: {e}\nફરીથી /topicmirror કમાન્ડ આપો.")

    status_msg = await app.send_message(user_id, "⏳ Userbot ચાલુ થાય છે... થોડીવાર રાહ જુઓ.")
    userbot = await initialize_userbot(user_id)
    
    if not userbot:
        return await status_msg.edit("❌ Userbot ચાલુ ના થયો! પહેલા `/login` કમાન્ડથી લોગીન કરો.")

    await status_msg.edit(f"🚀 **Topic Mirroring ચાલુ થઈ ગયું છે!**\n\nસ્કેનિંગ મેસેજ ID: {start_msg_id} થી {start_msg_id + limit}")
    
    success = 0
    for msg_id in range(start_msg_id, start_msg_id + limit):
        try:
            # યુઝરબોટથી મેસેજ ચેક કરો
            msg = await userbot.get_messages(source_chat_id, msg_id)
            if not msg or msg.empty or msg.service:
                continue
            
            # ટોપિક ID કાઢો (જો ટોપિક ના હોય તો 1 એટલે કે General ગણાશે)
            source_topic_id = msg.message_thread_id or 1
            
            # જો આ ટોપિક નવા ગ્રુપમાં ના બનાવ્યો હોય, તો નવો બનાવો
            if source_topic_id not in mapped_topics:
                if source_topic_id == 1:
                    mapped_topics[source_topic_id] = None
                else:
                    try:
                        t_name = f"Mirror Topic {source_topic_id}"
                        new_topic = await app.create_forum_topic(chat_id=target_chat_id, title=t_name)
                        mapped_topics[source_topic_id] = new_topic.message_thread_id
                        await asyncio.sleep(2)
                    except Exception as e:
                        print(f"Topic Error: {e}")
                        mapped_topics[source_topic_id] = None
                        
            target_topic_id = mapped_topics[source_topic_id]
            
            # જુના get_func.py ના લોજિક પ્રમાણે user_chat_ids માં ટોપિક આઈડી સેટ કરો (દા.ત. -100xxx/5)
            if target_topic_id:
                user_chat_ids[user_id] = f"{target_chat_id}/{target_topic_id}"
            else:
                user_chat_ids[user_id] = str(target_chat_id)

            # તમારા જુના ડાઉનલોડ/અપલોડ કોડનો જ સીધો ઉપયોગ કરો (જેથી બધી સાઈઝની ફાઈલો ટ્રાન્સફર થાય)
            await copy_message_with_chat_id(app, userbot, user_id, source_chat_id, msg_id, status_msg)
            
            success += 1
            await asyncio.sleep(4) # ટેલિગ્રામ સ્પામ (FloodWait) એરરથી બચવા માટે
            
        except FloodWait as e:
            await asyncio.sleep(e.value + 3)
        except Exception as e:
            print(f"Error on msg {msg_id}: {e}")
            
    # પ્રોસેસ પૂરી થયા પછી જૂનું સેટિંગ પાછું લાવી દો
    user_chat_ids.pop(user_id, None)
    await app.send_message(user_id, f"🎉 **Topic Mirroring પૂરું થયું!**\n\n✅ સફળતાપૂર્વક {success} ફાઈલો/મેસેજ યોગ્ય ટોપિકમાં ટ્રાન્સફર થયા.")
    await userbot.stop()
          
