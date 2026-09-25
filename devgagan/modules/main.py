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

def get_tag(text, is_ch=False):
    t = (text or "").lower()
    ch_kws = [("સાદું વ્યાજ", ["સાદું વ્યાજ", "simple interest"]), ("નફો ખોટ", ["નફો", "profit"]), ("ટકાવારી", ["ટકાવારી", "percent"]), ("ગુણોત્તર", ["ગુણોત્તર", "ratio"]), ("સરેરાશ", ["સરેરાશ", "average"]), ("કામ સમય", ["કામ", "work"]), ("ઝડપ અંતર", ["ઝડપ", "speed", "ટ્રેન"]), ("ક્ષેત્રફળ", ["ક્ષેત્રફળ", "area"])]
    sub_kws = [("ગણિત", ["ગણિત", "math"]), ("રીઝનીંગ", ["રીઝનીંગ", "reasoning"]), ("બંધારણ", ["બંધારણ", "polity"]), ("ઇતિહાસ", ["ઇતિહાસ", "history"]), ("ભૂગોળ", ["ભૂગોળ", "geography"]), ("ગુજરાતી", ["ગુજરાતી", "gujarati"]), ("અંગ્રેજી", ["અંગ્રેજી", "english"]), ("વિજ્ઞાન", ["વિજ્ઞાન", "science"]), ("કોમ્પ્યુટર", ["કોમ્પ્યુટર", "comp"]), ("કાયદો", ["કાયદો", "law"])]
    for name, kws in (ch_kws if is_ch else sub_kws):
        if any(k in t for k in kws): return name
    for line in (text or "").split("\n"):
        c = re.sub(r'(?i)^.*?(topic|chapter)\s*[:\-\—]\s*', '', line).strip()
        if len(c) > 2 and not any(x in c.lower() for x in ["index", "vid", "http", "batch"]): return c[:20]
    return "અન્ય"

async def check_interval(u_id, freecheck):
    if freecheck != 1 or await is_user_verified(u_id): return True, None
    now = datetime.now()
    if u_id in interval_set and now < interval_set[u_id]:
        return False, f"Please wait {(interval_set[u_id] - now).seconds}s before next link."
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
    if not target: return await message.reply("⚠️ Target ID lakho: `/gen_summary ID` ke `/chapter_summary ID`")

    st = await message.reply("⚡ Scanning fast...")
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
        return await st.edit_text("❌ Koi file mali nathi.")

    msgs.reverse()
    clean = str(target).replace("-100", "").replace("-", "")
    data = {}

    for m in msgs:
        txt = m.caption or m.text or (m.video.file_name if m.video else "") or (m.document.file_name if m.document else "")
        tag = get_tag(txt, is_ch)
        is_pdf = bool(m.document and m.document.file_name and m.document.file_name.endswith('.pdf'))
        url = f"https://t.me/c/{clean}/{topic_id}/{m.id}" if topic_id else f"https://t.me/c/{clean}/{m.id}"
        data.setdefault(tag, []).append((url, is_pdf))

    txt_lines = []
    if is_ch:
        for ch, items in data.items():
            vl, pl = [], []
            for u, pdf in items:
                if pdf: pl.append(f"[PDF {len(pl)+1}]({u})")
                else: vl.append(f"[Part {len(vl)+1}]({u})")
            b = f"📂 **{ch}**\n"
            if vl: b += "🎥 " + " | ".join(vl) + "\n"
            if pl: b += "📄 " + " | ".join(pl) + "\n"
            txt_lines.append(b + "\n")
    else:
        for sub, items in data.items():
            v, p = sum(1 for _, x in items if not x), sum(1 for _, x in items if x)
            txt_lines.append(f"- [{sub}]({items[0][0]}) 🎥 {v} | 📄 {p}\n\n")

    parts, cur = [], ("📚 **Chapter Index**\n\n" if is_ch else "📌 **Topic Summary**\n\n")
    for l in txt_lines:
        if len(cur) + len(l) > 3000: parts.append(cur); cur = l
        else: cur += l
    cur += f"━━━━━━━━━━━━━━━━━━━━\n✅ Total Files: `{len(msgs)}`\n**__Powered By ╰‿╯ ҡσℓเ ⚝__**"
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
    await st.edit_text("✅ Summary moklai gai ane PIN thai gai!")

@app.on_message(filters.regex(r'https?://(?:www\.)?t\.me/[^\s]+|tg://openmessage\?user_id=\w+&message_id=\d+') & filters.private)
async def single_link(_, m):
    u_id = m.chat.id
    if await subscribe(_, m) == 1 or u_id in batch_mode or users_loop.get(u_id, False): return
    chk = await chk_user(m, u_id)
    if chk == 1 and FREEMIUM_LIMIT == 0 and u_id not in OWNER_ID and not await is_user_verified(u_id):
        return await m.reply("Freemium not available.")
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
        st = await app.ask(u_id, "🎯 Start Link moklo:")
        if st.text.strip().split("/")[-1].isdigit():
            cs = int(st.text.strip().split("/")[-1])
            start_url = st.text.strip()
            break
    else: return await m.reply("Max limit reached.")

    for _ in range(3):
        nm = await app.ask(u_id, f"Ketla messages karva chhe? (Max {mx}):")
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
            
