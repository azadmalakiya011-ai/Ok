import time, random, string, asyncio, re
from pyrogram import filters, Client, enums
from devgagan import app
from config import API_ID, API_HASH, FREEMIUM_LIMIT, PREMIUM_LIMIT, OWNER_ID
from devgagan.core.get_func import get_msg
from devgagan.core.func import *
from devgagan.core.mongo import db
from datetime import datetime, timedelta
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from devgagan.modules.shrink import is_user_verified

users_loop, interval_set, batch_mode = {}, {}, {}

def get_clean_name(text, is_ch=False):
    t = (text or "").lower()

    ch_kws = [
        ("સાદું વ્યાજ", ["સાદું વ્યાજ", "sadu vyaj", "simple interest"]),
        ("ચક્રવૃદ્ધિ વ્યાજ", ["ચક્રવૃદ્ધિ વ્યાજ", "compound interest"]),
        ("નફો-ખોટ", ["નફો ખોટ", "નફો અને ખોટ", "nafo khot", "profit"]),
        ("ટકાવારી", ["ટકાવારી", "takavari", "percent"]),
        ("ગુણોત્તર-પ્રમાણ", ["ગુણોત્તર", "gunottar", "ratio"]),
        ("સરેરાશ", ["સરેરાશ", "sarerash", "average"]),
        ("કામ-સમય", ["કામ સમય", "મહેનતાણું", "kam samay", "work"]),
        ("નળ-ટાંકી", ["નળ અને ટાંકી", "tanki", "pipe"]),
        ("ઝડપ-અંતર", ["ઝડપ અને અંતર", "અંતર અને સમય", "speed", "distance"]),
        ("ટ્રેન", ["ટ્રેન", "train"]),
        ("હોડી-પ્રવાહ", ["હોડી", "boat"]),
        ("ભાગીદારી", ["ભાગીદારી", "partnership"]),
        ("ઉંમર સંબંધિત", ["ઉંમર", "ages", "umar"]),
        ("ક્ષેત્રફળ-પરિમિતિ", ["ક્ષેત્રફળ", "પરિમિતિ", "area"]),
        ("સાદુરૂપ", ["સાદુરૂપ", "simplification"])
    ]

    sub_kws = [
        ("ગણિત", ["ગણિત", "maths", "math"]),
        ("રીઝનીંગ", ["રીઝનીંગ", "reasoning"]),
        ("વિજ્ઞાન", ["વિજ્ઞાન", "science", "સાયન્સ"]),
        ("બંધારણ", ["બંધારણ", "polity", "constitution"]),
        ("ગુજરાત ઇતિહાસ", ["ગુજરાતનો ઇતિહાસ", "gujarat history", "gujarat itihas"]),
        ("ભારત ઇતિહાસ", ["ભારતનો ઇતિહાસ", "indian history", "bharat itihas"]),
        ("ગુજરાત ભૂગોળ", ["ગુજરાત ભૂગોળ", "gujarat geography"]),
        ("ભારત ભૂગોળ", ["ભારત ભૂગોળ", "indian geography"]),
        ("ગુજરાતી વ્યાકરણ", ["ગુજરાતી વ્યાકરણ", "gujarati grammar", "vyakaran"]),
        ("ગુજરાતી સાહિત્ય", ["સાહિત્ય", "sahitya"]),
        ("અંગ્રેજી વ્યાકરણ", ["અંગ્રેજી", "english grammar", "english"]),
        ("કોમ્પ્યુટર", ["કોમ્પ્યુટર", "computer", "comp"]),
        ("કાયદો", ["કાયદો", "law", "ipc", "crpc"]),
        ("પંચાયતી રાજ", ["પંચાયતી રાજ", "panchayati raj"]),
        ("કરંટ અફેર્સ", ["કરંટ અફેર્સ", "current affairs", "current"])
    ]

    target_list = ch_kws if is_ch else sub_kws
    for name, kws in target_list:
        if any(k in t for k in kws):
            return name

    for line in (text or "").split("\n"):
        c = line.strip()
        c = re.sub(r'(?i)^.*?(file\s*title|topic|chapter|ch|sub)\s*[:\-\—\.]*\s*', '', c).strip()
        c = re.sub(r'^\d+[\.\-\s_:]+', '', c).strip()
        c = re.sub(r'(\.pdf|\.mkv|\.mp4|\[\d+p\])', '', c, flags=re.IGNORECASE).strip()
        c = re.sub(r'(?i)\b(part|lec|lecture|\d+|video)\b.*', '', c).strip()

        if len(c) >= 4 and not re.match(r'^[A-Za-z]{1,3}$', c):
            if not any(x in c.lower() for x in ["vid id", "pdf id", "batch", "http", "saved by", "uploaded by"]):
                return c[:20]

    return "અન્ય ચેપ્ટર" if is_ch else "અન્ય વિષય"

# વિડિયોનું શોર્ટ નામ (લિંક બનાવવા માટે)
def get_short_title(text, default_name):
    if not text: return default_name
    first_line = text.strip().split("\n")[0]
    c = re.sub(r'(?i)^.*?(file\s*title|topic|chapter)\s*[:\-\—\.]*\s*', '', first_line).strip()
    c = re.sub(r'(\.pdf|\.mkv|\.mp4)', '', c, flags=re.IGNORECASE).strip()
    if len(c) > 25: c = c[:25] + ".."
    return c if len(c) > 2 else default_name

async def check_interval(u_id, freecheck):
    if freecheck != 1 or await is_user_verified(u_id): return True, None
    now = datetime.now()
    if u_id in interval_set and now < interval_set[u_id]:
        return False, f"રાહ જુઓ: {(interval_set[u_id] - now).seconds}s."
    return True, None

async def initialize_userbot(u_id):
    data = await db.get_data(u_id)
    if data and data.get("session"):
        try:
            ub = Client("userbot", api_id=API_ID, api_hash=API_HASH, device_model='iPhone 16 Pro', session_string=data.get("session"))
            await ub.start()
            return ub
        except Exception: pass
    return None

async def run_fast_summary(message, is_ch=False):
    u_id, target, topic_id = message.chat.id, None, None
    args = message.text.split()
    if len(args) > 1:
        raw = args[1].strip()
        p = raw.split("/") if "/" in raw else [raw, None]
        target = int("-100" + p[0].replace("-100", "").lstrip("-"))
        if p[1] and p[1].isdigit(): topic_id = int(p[1])
    if not target:
        ud = await db.get_data(u_id) or {}
        raw = str(ud.get("chat_id") or ud.get("dump_id") or "")
        if raw:
            p = raw.split("/") if "/" in raw else [raw, None]
            target = int("-100" + p[0].replace("-100", "").lstrip("-"))
            if p[1] and p[1].isdigit(): topic_id = int(p[1])
    if not target: return await message.reply("⚠️ Target ID લખો: `/gen_summary ID` કે `/chapter_summary ID`")

    st = await message.reply("⚡ સ્કેનિંગ શરૂ...")
    ub = await initialize_userbot(u_id)
    c = ub if ub else app
    msgs, seen = [], set()

    for flt in [enums.MessagesFilter.VIDEO, enums.MessagesFilter.DOCUMENT]:
        try:
            kw = {"chat_id": target, "filter": flt, "limit": 1500}
            if topic_id: kw["message_thread_id"] = topic_id
            async for m in c.search_messages(**kw):
                if m.id not in seen: seen.add(m.id); msgs.append(m)
        except Exception: pass

    if not msgs:
        async for m in c.get_chat_history(target, limit=2000):
            if topic_id:
                mt = getattr(m, "message_thread_id", None) or (m.reply_to_message_id if m.reply_to_message else None)
                if mt != topic_id and m.id != topic_id: continue
            if (m.video or m.document) and m.id not in seen:
                seen.add(m.id); msgs.append(m)

    if not msgs:
        if ub: await ub.stop()
        return await st.edit_text("❌ કોઈ ફાઈલ મળી નથી.")

    msgs.reverse()
    clean = str(target).replace("-100", "").replace("-", "")
    data = {}

    for idx, m in enumerate(msgs, 1):
        txt = m.caption or m.text or (m.video.file_name if m.video else "") or (m.document.file_name if m.document else "")
        tag = get_clean_name(txt, is_ch)
        is_pdf = bool(m.document and m.document.file_name and m.document.file_name.endswith('.pdf'))
        url = f"https://t.me/c/{clean}/{topic_id}/{m.id}" if topic_id else f"https://t.me/c/{clean}/{m.id}"
        
        # વિડિયોના નામને જ ક્લિકેબલ લિંક બનાવવી
        short_title = get_short_title(txt, f"Part {idx}" if not is_pdf else f"PDF {idx}")
        data.setdefault(tag, []).append((short_title, url, is_pdf))

    txt_lines = []
    if is_ch:
        # અતિ કોમ્પેક્ટ ફોર્મેટ: વિડિયોના નામ પર જ લિંક
        for ch, items in data.items():
            txt_lines.append(f"📁 **{ch}**\n")
            links_str = []
            for name, u, pdf in items:
                prefix = "📄" if pdf else "🎬"
                links_str.append(f"{prefix} [{name}]({u})")
            # એક જ બ્લોકમાં લિંક્સ
            txt_lines.append(" • " + "\n • ".join(links_str) + "\n\n")
    else:
        for sub, items in data.items():
            v = sum(1 for _, _, x in items if not x)
            p = sum(1 for _, _, x in items if x)
            txt_lines.append(f"🔹 [{sub}]({items[0][1]}) 🎥`{v}` 📄`{p}`\n")

    parts, cur = [], ("📚 **પ્રકરણ ઇન્ડેક્સ**\n\n" if is_ch else "📌 **વિષય સમરી**\n\n")
    for l in txt_lines:
        if len(cur) + len(l) > 3500: parts.append(cur); cur = l
        else: cur += l
    cur += f"───────────────\n✅ કુલ ફાઈલ: `{len(msgs)}`\n**__╰‿╯ ҡσℓเ ⚝__**"
    parts.append(cur)

    sender = ub if ub else app
    for i, p in enumerate(parts):
        try:
            s = await sender.send_message(target, p, reply_to_message_id=topic_id, disable_web_page_preview=True) if topic_id else await sender.send_message(target, p, disable_web_page_preview=True)
        except Exception:
            s = await app.send_message(target, p, reply_to_message_id=topic_id, disable_web_page_preview=True) if topic_id else await app.send_message(target, p, disable_web_page_preview=True)
        if i == 0 and s:
            try: await s.pin(both_sides=True)
            except Exception: pass
        await asyncio.sleep(1)

    if ub: await ub.stop()
    await st.edit_text("✅ સમરી મોકલાઈ ગઈ અને PIN થઈ ગઈ!")

@app.on_message(filters.regex(r'https?://(?:www\.)?t\.me/[^\s]+|tg://openmessage\?user_id=\w+&message_id=\d+') & filters.private)
async def single_link(_, m):
    u_id = m.chat.id
    if await subscribe(_, m) == 1 or u_id in batch_mode or users_loop.get(u_id, False): return
    chk = await chk_user(m, u_id)
    if chk == 1 and FREEMIUM_LIMIT == 0 and u_id not in OWNER_ID and not await is_user_verified(u_id): return await m.reply("Freemium not available.")
    can, res = await check_interval(u_id, chk)
    if not can: return await m.reply(res)

    users_loop[u_id] = True
    lnk = m.text if "tg://openmessage" in m.text else get_link(m.text)
    msg = await m.reply("Processing...")
    ub = await initialize_userbot(u_id)
    try:
        if 't.me/' in lnk and not any(x in lnk for x in ['t.me/+', 't.me/c/', 't.me/b/', 'tg://openmessage']):
            await get_msg(ub, u_id, msg.id, lnk, 0, m)
            interval_set[u_id] = datetime.now() + timedelta(seconds=45)
        elif 't.me/+' in lnk:
            await msg.edit_text(await userbot_join(ub, lnk))
        elif any(sub in lnk for sub in ['t.me/c/', 't.me/b/', '/s/', 'tg://openmessage']):
            await get_msg(ub, u_id, msg.id, lnk, 0, msg)
            interval_set[u_id] = datetime.now() + timedelta(seconds=45)
    except Exception as e: await msg.edit_text(f"Error: {e}")
    finally:
        users_loop[u_id] = False
        if ub: await ub.stop()
        try: await msg.delete()
        except Exception: pass

@app.on_message(filters.command("batch") & filters.private)
async def batch_link(_, m):
    if await subscribe(_, m) == 1 or users_loop.get(m.chat.id, False): return
    u_id = m.chat.id
    free = await chk_user(m, u_id)
    mx = PREMIUM_LIMIT if (free != 1 or u_id in OWNER_ID) else (30 if await is_user_verified(u_id) else FREEMIUM_LIMIT)

    for _ in range(3):
        st = await app.ask(u_id, "🎯 Start Link મોકલો:")
        if st.text.strip().split("/")[-1].isdigit():
            cs = int(st.text.strip().split("/")[-1])
            start_url = st.text.strip()
            break
    else: return await m.reply("Max limit reached.")

    for _ in range(3):
        nm = await app.ask(u_id, f"કેટલા મેસેજ કરવા છે? (Max {mx}):")
        if nm.text.strip().isdigit() and 1 <= int(nm.text.strip()) <= mx:
            cl = int(nm.text.strip())
            break
    else: return await m.reply("Invalid number.")

    p_msg = await m.reply(f"Batch started ⚡ (0/{cl})")
    users_loop[u_id] = True
    ub = await initialize_userbot(u_id)
    try:
        for i in range(cs, cs + cl):
            if not users_loop.get(u_id, False): break
            url = f"{'/'.join(start_url.split('/')[:-1])}/{i}"
            lnk = get_link(url)
            msg = await m.reply("Processing...")
            await get_msg(ub, u_id, msg.id, lnk, 0, m)
            try: await p_msg.edit_text(f"Processing: {i - cs + 1}/{cl}")
            except Exception: pass
            await asyncio.sleep(3)
        await p_msg.edit_text("Batch Completed 🎉")
    finally:
        users_loop.pop(u_id, None)
        if ub: await ub.stop()

@app.on_message(filters.command("gen_summary"))
async def cmd_gen_sum(_, m): await run_fast_summary(m, False)

@app.on_message(filters.command("chapter_summary"))
async def cmd_ch_sum(_, m): await run_fast_summary(m, True)

@app.on_message(filters.command("cancel"))
async def stop_batch(_, m):
    if users_loop.get(m.chat.id, False):
        users_loop[m.chat.id] = False
        await m.reply("Stopped successfully.")
    else:
        await m.reply("No active batch.")
        
