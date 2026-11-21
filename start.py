# ============ start.py ============
# Bot start + saari commands. Chalane ke liye:  python start.py

import asyncio
import html
import logging

from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.enums import ParseMode

import config
from batch import (
    get_session, reset_session, fmt_ep, process_file, rename_manual,
)

logging.basicConfig(level=logging.INFO)

app = Client(
    "rename_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    in_memory=True,
)


async def _auth(_, __, m):
    if not config.AUTH_USERS:
        return True
    return bool(m.from_user and m.from_user.id in config.AUTH_USERS)

auth = filters.create(_auth)
HTML = ParseMode.HTML


def arg(m) -> str:
    parts = m.text.split(None, 1)
    return parts[1].strip() if len(parts) > 1 else ""


def settings_text(uid: int) -> str:
    s = get_session(uid)
    nxt = fmt_ep(s, s.next_ep, min(s.next_ep + s.step - 1, s.stop_at) if s.stop_at else s.next_ep + s.step - 1)
    stop = s.stop_at if s.stop_at else "No limit"
    return (
        "⚙️ <b>Current Settings</b>\n\n"
        f"📖 Title: <code>{html.escape(s.title)}</code>\n"
        f"🎨 Artist: <code>{html.escape(s.artist)}</code>\n"
        f"📺 Quality: <code>{html.escape(s.quality)}</code>\n"
        f"🔢 Next file Episode: <code>{nxt}</code>\n"
        f"↔️ Gap (step): <code>{s.step}</code>\n"
        f"🛑 Stop at: <code>{stop}</code>\n"
        f"0️⃣ Padding: <code>{s.pad}</code>\n"
        f"🎯 Target chat: <code>{s.target or 'Same chat'}</code>\n"
        f"✅ Done files: <code>{s.done}</code>\n\n"
        f"📝 Name format:\n<code>{html.escape(s.name_tpl)}</code>\n\n"
        f"💬 Caption format:\n<code>{html.escape(s.cap_tpl)}</code>"
    )


HELP = (
    "🤖 <b>File Rename Bot</b>\n\n"
    "<b>Auto rename:</b> bas file bhejte jao (single ya bahut saari). "
    "Har file ko agla episode number / range milta rahega.\n\n"
    "<b>Setup commands</b>\n"
    "/title <code>naam</code> - story/title ka naam\n"
    "/artist <code>naam</code> - file ke neeche artist name\n"
    "/quality <code>720p</code> - quality text\n"
    "/ep <code>5</code> - agli file kis episode se shuru ho\n"
    "/step <code>10</code> - har file me kitne episode (gap)\n"
    "/range <code>1 10</code> - Episode 1-10 se shuru, gap khud 10 ban jayega, "
    "agli file 11-20, phir 21-30...\n"
    "/stop <code>100</code> - is episode ke baad ruk jao (0 = limit hata do)\n"
    "/pad <code>2</code> - 01, 02 wala zero padding (0 = band)\n"
    "/format <code>template</code> - file ka naam format\n"
    "/caption <code>template</code> - caption format\n"
    "/target <code>-100xxxx</code> - kis channel/chat me bheje (0 = usi chat me)\n"
    "/settings - sab settings dekho\n"
    "/reset - sab default par\n\n"
    "<b>Single file, apna naam:</b>\n"
    "File par reply karke: /rename <code>Naya Naam</code>\n\n"
    "<b>Placeholders:</b> <code>{title} {ep} {quality} {artist}</code>\n\n"
    "<b>Example:</b>\n"
    "/title Pocket FM Story\n"
    "/artist Rahul\n"
    "/range 1 10\n"
    "/stop 50\n"
    "Ab files bhejo: 1-10, 11-20, 21-30, 31-40, 41-50, phir bot ruk jayega."
)


@app.on_message(filters.command(["start", "help"]) & filters.private & auth)
async def start_cmd(c, m):
    await m.reply_text(HELP, parse_mode=HTML)


@app.on_message(filters.command("settings") & filters.private & auth)
async def settings_cmd(c, m):
    await m.reply_text(settings_text(m.from_user.id), parse_mode=HTML)


@app.on_message(filters.command("title") & filters.private & auth)
async def title_cmd(c, m):
    v = arg(m)
    if not v:
        return await m.reply_text("Use: /title My Story Name")
    get_session(m.from_user.id).title = v
    await m.reply_text(f"✅ Title set: <code>{html.escape(v)}</code>", parse_mode=HTML)


@app.on_message(filters.command("artist") & filters.private & auth)
async def artist_cmd(c, m):
    v = arg(m)
    if not v:
        return await m.reply_text("Use: /artist Artist Name")
    get_session(m.from_user.id).artist = v
    await m.reply_text(f"✅ Artist set: <code>{html.escape(v)}</code>", parse_mode=HTML)


@app.on_message(filters.command("quality") & filters.private & auth)
async def quality_cmd(c, m):
    v = arg(m)
    if not v:
        return await m.reply_text("Use: /quality 720p")
    get_session(m.from_user.id).quality = v
    await m.reply_text(f"✅ Quality set: <code>{html.escape(v)}</code>", parse_mode=HTML)


@app.on_message(filters.command("ep") & filters.private & auth)
async def ep_cmd(c, m):
    v = arg(m)
    if not v.isdigit() or int(v) < 0:
        return await m.reply_text("Use: /ep 5")
    s = get_session(m.from_user.id)
    s.next_ep = int(v)
    await m.reply_text(f"✅ Agli file Episode {v} se shuru hogi (gap {s.step}).")


@app.on_message(filters.command("step") & filters.private & auth)
async def step_cmd(c, m):
    v = arg(m)
    if not v.isdigit() or int(v) < 1:
        return await m.reply_text("Use: /step 10")
    s = get_session(m.from_user.id)
    s.step = int(v)
    await m.reply_text(f"✅ Gap set: har file me {v} episode.")


@app.on_message(filters.command("range") & filters.private & auth)
async def range_cmd(c, m):
    p = arg(m).replace("-", " ").replace(",", " ").split()
    if len(p) != 2 or not all(x.isdigit() for x in p) or int(p[1]) < int(p[0]):
        return await m.reply_text("Use: /range 1 10")
    a, b = int(p[0]), int(p[1])
    s = get_session(m.from_user.id)
    s.next_ep = a
    s.step = b - a + 1
    await m.reply_text(
        f"✅ Range set: {a}-{b}\nGap: {s.step}\n"
        f"Agli files: {b + 1}-{b + s.step}, {b + s.step + 1}-{b + 2 * s.step} ..."
    )


@app.on_message(filters.command("stop") & filters.private & auth)
async def stop_cmd(c, m):
    v = arg(m)
    if not v.isdigit():
        return await m.reply_text("Use: /stop 100  (0 = limit hata do)")
    get_session(m.from_user.id).stop_at = int(v)
    await m.reply_text("✅ Limit hata di." if int(v) == 0 else f"✅ Episode {v} ke baad bot ruk jayega.")


@app.on_message(filters.command("pad") & filters.private & auth)
async def pad_cmd(c, m):
    v = arg(m)
    if not v.isdigit() or int(v) > 6:
        return await m.reply_text("Use: /pad 2")
    get_session(m.from_user.id).pad = int(v)
    await m.reply_text(f"✅ Padding set: {v}")


@app.on_message(filters.command("format") & filters.private & auth)
async def format_cmd(c, m):
    v = arg(m)
    if not v:
        return await m.reply_text(
            "Use: /format {title} - Episode {ep} [{quality}]\n"
            "Placeholders: {title} {ep} {quality} {artist}")
    get_session(m.from_user.id).name_tpl = v
    await m.reply_text(f"✅ Name format set:\n<code>{html.escape(v)}</code>", parse_mode=HTML)


@app.on_message(filters.command("caption") & filters.private & auth)
async def caption_cmd(c, m):
    v = arg(m)
    if not v:
        return await m.reply_text(
            "Use: /caption <b>{title} - Ep {ep}</b>\\n\\nArtist: {artist}\n"
            "(Naye line ke liye message me hi Enter dabao)\n"
            "Placeholders: {title} {ep} {quality} {artist}", parse_mode=HTML)
    get_session(m.from_user.id).cap_tpl = v
    await m.reply_text("✅ Caption format set.")


@app.on_message(filters.command("target") & filters.private & auth)
async def target_cmd(c, m):
    v = arg(m)
    try:
        t = int(v)
    except ValueError:
        return await m.reply_text("Use: /target -1001234567890  (0 = usi chat me)")
    get_session(m.from_user.id).target = t
    await m.reply_text("✅ Target set. (Bot us channel me admin hona chahiye)")


@app.on_message(filters.command("reset") & filters.private & auth)
async def reset_cmd(c, m):
    reset_session(m.from_user.id)
    await m.reply_text("♻️ Sab settings default par aa gayi.")


@app.on_message(filters.command("rename") & filters.private & auth)
async def rename_cmd(c, m):
    r = m.reply_to_message
    if not r or not (r.document or r.video or r.audio):
        return await m.reply_text("File par reply karke likho: /rename Naya Naam")
    name = arg(m)
    if not name:
        return await m.reply_text("Naam bhi likho: /rename Naya Naam")
    st = await m.reply_text("📥 Queued...", quote=True)
    await rename_manual(c, r, get_session(m.from_user.id), name, st)


@app.on_message(
    filters.private & (filters.document | filters.video | filters.audio) & auth
)
async def on_file(c, m):
    s = get_session(m.from_user.id)
    rng = s.take_range()          # numbering yahin ho jati hai, isliye order sahi rehta hai
    if rng is None:
        return await m.reply_text(
            f"🛑 Stop limit ({s.stop_at}) poori ho gayi.\n"
            "Naya set karne ke liye /stop ya /range use karo.")
    st = await m.reply_text(f"📥 Queued: Episode {fmt_ep(s, *rng)}", quote=True)
    await process_file(c, m, s, rng, st)


# ---------- chhota web server (Render ke liye) ----------
async def start_web():
    async def hello(_):
        return web.Response(text="Rename bot is running")
    web_app = web.Application()
    web_app.router.add_get("/", hello)
    runner = web.AppRunner(web_app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", config.PORT).start()


async def main():
    if config.WEB_SERVER:
        await start_web()
    await app.start()
    me = await app.get_me()
    print(f"Bot started: @{me.username}")
    await idle()
    await app.stop()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
