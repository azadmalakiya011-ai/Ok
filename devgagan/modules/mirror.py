from pyrogram import filters, Client
from devgagan import app
from devgagan.core.mongo import save_topic_mirror, delete_topic_mirror

# કામચલાઉ ડેટા સાચવવા માટે (જ્યાં સુધી યુઝર લિંક ના કરે)
pending_mirrors = {}

@app.on_message(filters.command("topicmirror"))
async def set_topic_mirror(client, message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if not message.is_topic_message:
        await message.reply("❌ કૃપા કરીને આ કમાન્ડનો ઉપયોગ માત્ર કોઈ 'Forum Topic' ની અંદર જ કરો.")
        return
        
    thread_id = message.message_thread_id
    
    # સોર્સ ટોપિકને મેમરીમાં સેવ કરીએ
    pending_mirrors[user_id] = {"source_chat": chat_id, "source_thread": thread_id}
    
    await message.reply(
        f"✅ સોર્સ (Source) ટોપિક સિલેક્ટ થઈ ગયો!\n\n"
        f"👉 હવે જે ટોપિકમાં તમારે ડેટા મોકલવો છે (Target), ત્યાં જઈને `/topiclink` કમાન્ડ આપો."
    )

@app.on_message(filters.command("topiclink"))
async def link_topic(client, message):
    user_id = message.from_user.id
    target_chat = message.chat.id
    
    if not message.is_topic_message:
        await message.reply("❌ કૃપા કરીને આ કમાન્ડનો ઉપયોગ માત્ર કોઈ 'Forum Topic' ની અંદર જ કરો.")
        return
        
    if user_id not in pending_mirrors:
        await message.reply("❌ કોઈ સોર્સ ટોપિક મળ્યો નથી. પહેલા જૂના ટોપિકમાં જઈને `/topicmirror` આપો.")
        return
        
    target_thread = message.message_thread_id
    source_data = pending_mirrors[user_id]
    
    source_chat = source_data["source_chat"]
    source_thread = source_data["source_thread"]
    
    # ડેટાબેઝમાં સેવ કરીએ
    await save_topic_mirror(source_chat, source_thread, target_chat, target_thread)
    
    # મેમરીમાંથી કાઢી નાખીએ
    del pending_mirrors[user_id]
    
    await message.reply(
        f"🔗 એકદમ પરફેક્ટ! બંને ટોપિક સફળતાપૂર્વક લિંક થઈ ગયા છે અને ડેટાબેઝમાં સેવ થઈ ગયા છે!\n\n"
        f"હવેથી સોર્સમાં આવતો ડેટા અહીંયા ટ્રાન્સફર થશે."
    )
    
@app.on_message(filters.command("cancel_mirror"))
async def cancel_mirror(client, message):
    chat_id = message.chat.id
    if not message.is_topic_message:
        await message.reply("❌ આ કમાન્ડ માત્ર ફોરમ ટોપિકમાં કામ કરશે.")
        return
        
    thread_id = message.message_thread_id
    
    # ડેટાબેઝમાંથી લિંક ડિલીટ
    await delete_topic_mirror(chat_id, thread_id)
    await message.reply("🛑 આ ટોપિકનું મિરર કનેક્શન ડેટાબેઝમાંથી કેન્સલ (Delete) કરી દેવામાં આવ્યું છે.")
  
