# ============ batch.py ============
# Rename ka poora engine: session, numbering (single/batch/range), download + upload.

import os
import re
import asyncio
import html
import mimetypes
from dataclasses import dataclass, field

from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

import config


@dataclass
class Session:
    title: str = config.DEFAULT_TITLE
    artist: str = config.DEFAULT_ARTIST
    quality: str = config.DEFAULT_QUALITY
    name_tpl: str = config.DEFAULT_NAME_TPL
    cap_tpl: str = config.DEFAULT_CAP_TPL
    target: int = config.TARGET_CHAT
    next_ep: int = 1      # agli file ka starting episode
    step: int = 1         # gap: 1 = single episode, 10 = 1-10, 11-20 ...
    stop_at: int = 0      # 0 = limit nahi, warna is episode ke baad ruk jao
    pad: int = 2          # 01, 02 ... (0 = padding nahi)
    done: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def take_range(self):
        """Agli file ke liye (start, end) nikalo aur counter aage badhao."""
        if self.stop_at and self.next_ep > self.stop_at:
            return None
        s = self.next_ep
        e = s + max(self.step, 1) - 1
        if self.stop_at and e > self.stop_at:
            e = self.stop_at
        self.next_ep = e + 1
        return s, e


_sessions = {}


def get_session(uid: int) -> Session:
    if uid not in _sessions:
        _sessions[uid] = Session()
    return _sessions[uid]


def reset_session(uid: int) -> Session:
    _sessions[uid] = Session()
    return _sessions[uid]


def fmt_ep(sess: Session, s: int, e: int) -> str:
    if s == e:
        return str(s).zfill(sess.pad)
    return f"{str(s).zfill(sess.pad)}-{str(e).zfill(sess.pad)}"


def clean_name(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    return re.sub(r"\s+", " ", name).strip()


def _values(sess: Session, ep: str, raw: bool):
    f = (lambda x: x) if raw else html.escape
    return dict(
        title=f(sess.title), ep=ep, quality=f(sess.quality), artist=f(sess.artist)
    )


def build_name(sess: Session, ep: str, ext: str) -> str:
    try:
        base = sess.name_tpl.format(**_values(sess, ep, raw=True))
    except (KeyError, IndexError, ValueError):
        base = f"{sess.title} - Episode {ep}"
    return clean_name(base) + ext


def build_caption(sess: Session, ep: str) -> str:
    try:
        return sess.cap_tpl.format(**_values(sess, ep, raw=False))
    except (KeyError, IndexError, ValueError):
        return f"<b>{html.escape(sess.title)} - Episode {ep}</b>\n\n🎨 Artist: {html.escape(sess.artist)}"


def get_media(msg):
    return msg.document or msg.video or msg.audio


def get_ext(msg) -> str:
    media = get_media(msg)
    name = getattr(media, "file_name", None) or ""
    ext = os.path.splitext(name)[1]
    if ext:
        return ext
    mime = getattr(media, "mime_type", None)
    guessed = mimetypes.guess_extension(mime) if mime else None
    if guessed:
        return guessed
    return ".mkv" if msg.video else ".mp3" if msg.audio else ""


async def _retry(coro_fn):
    for _ in range(3):
        try:
            return await coro_fn()
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
    return await coro_fn()


async def _download_and_send(client, msg, sess, new_name, caption):
    media = get_media(msg)
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    uid = f"{msg.chat.id}_{msg.id}"
    path = os.path.join(config.DOWNLOAD_DIR, uid + get_ext(msg))
    thumb = None
    chat_id = sess.target or msg.chat.id

    try:
        path = await _retry(lambda: client.download_media(msg, file_name=path))
        if getattr(media, "thumbs", None):
            try:
                thumb = await client.download_media(
                    media.thumbs[0].file_id,
                    file_name=os.path.join(config.DOWNLOAD_DIR, uid + "_thumb.jpg"),
                )
            except Exception:
                thumb = None

        kw = dict(chat_id=chat_id, caption=caption, parse_mode=ParseMode.HTML)

        if msg.video and not config.FORCE_DOCUMENT:
            await _retry(lambda: client.send_video(
                video=path, file_name=new_name, thumb=thumb,
                duration=media.duration, width=media.width, height=media.height,
                supports_streaming=True, **kw))
        elif msg.audio and not config.FORCE_DOCUMENT:
            await _retry(lambda: client.send_audio(
                audio=path, file_name=new_name, thumb=thumb,
                duration=media.duration, performer=media.performer,
                title=media.title, **kw))
        else:
            await _retry(lambda: client.send_document(
                document=path, file_name=new_name, thumb=thumb,
                force_document=True, **kw))
    finally:
        for p in (path, thumb):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


async def process_file(client, msg, sess: Session, rng, status):
    """Auto numbering wali file (single / batch / range sab isi se)."""
    s, e = rng
    ep = fmt_ep(sess, s, e)
    new_name = build_name(sess, ep, get_ext(msg))
    caption = build_caption(sess, ep)

    async with sess.lock:          # ek ke baad ek, order same rahega
        try:
            await status.edit_text(f"⏳ Processing: <code>{html.escape(new_name)}</code>",
                                   parse_mode=ParseMode.HTML)
            await _download_and_send(client, msg, sess, new_name, caption)
            sess.done += 1
            await status.edit_text(f"✅ Done: <code>{html.escape(new_name)}</code>",
                                   parse_mode=ParseMode.HTML)
        except Exception as ex:
            await status.edit_text(f"❌ Failed (Ep {ep}): {html.escape(str(ex))[:200]}")


async def rename_manual(client, msg, sess: Session, custom_name: str, status):
    """Single file: apne hisaab ka naam (/rename reply)."""
    ext = get_ext(msg)
    stem, given_ext = os.path.splitext(custom_name)
    if given_ext and len(given_ext) <= 5:
        new_name = clean_name(stem) + given_ext
        stem = clean_name(stem)
    else:
        stem = clean_name(custom_name)
        new_name = stem + ext
    caption = f"<b>{html.escape(stem)}</b>\n\n🎨 Artist: {html.escape(sess.artist)}"

    async with sess.lock:
        try:
            await status.edit_text("⏳ Renaming...")
            await _download_and_send(client, msg, sess, new_name, caption)
            await status.edit_text(f"✅ Done: <code>{html.escape(new_name)}</code>",
                                   parse_mode=ParseMode.HTML)
        except Exception as ex:
            await status.edit_text(f"❌ Failed: {html.escape(str(ex))[:200]}")
