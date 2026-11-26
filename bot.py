"""Good Boyfriend Points bot (@bf_scorekeeper_bot).

Counts points when someone sends a sticker from the pack in a chat the bot is in.

Settings (environment variables):
  BOT_TOKEN    token from @BotFather. On Windows it can live in Credential
               Manager instead: run "python bot.py --set-token" once.
  STICKER_SET  short name of the pack, the part after t.me/addstickers/
               (a full link works too). While it's empty, the bot answers
               any sticker with the name of its pack.
  DB_PATH      score database, defaults to points.db next to this file.

Each sticker's value comes from its position in the pack, so the pack must be
in this order: +1, +10, +50, +100, -1, -10, -50, -100.
"""
import asyncio
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path

from telegram import Update
from telegram.error import BadRequest, NetworkError
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

PACK_ORDER = [1, 10, 50, 100, -1, -10, -50, -100]
DEFAULT_STICKER_SET = "bf_points_claudia"  # STICKER_SET overrides it
TOKEN_NAME = "bf-scorekeeper-bot-token"  # Windows Credential Manager entry
TOKEN_USER = "claudia"


def pack_name(value: str) -> str:
    """'https://t.me/addstickers/Name' or 'Name' -> 'Name'."""
    return value.strip().rstrip("/").rsplit("/", 1)[-1]


STICKER_SET = pack_name(os.environ.get("STICKER_SET") or DEFAULT_STICKER_SET)
DB_PATH = os.environ.get("DB_PATH") or str(Path(__file__).with_name("points.db"))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
# httpx logs every request URL at INFO, and the URL contains the token.
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("bfpoints")

# file_unique_id -> point value, filled at startup from the sticker set
STICKER_VALUES: dict[str, int] = {}
DB = None  # sqlite3.Connection, opened in open_db()


# ---------- token ----------
def get_token() -> str:
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        try:
            import keyring
            token = keyring.get_password(TOKEN_NAME, TOKEN_USER) or ""
        except Exception:
            token = ""
    if not token:
        sys.exit("No bot token. Set BOT_TOKEN, or on Windows run: python bot.py --set-token")
    return token


def set_token():
    """Copy the token from the BotFather chat, then run: python bot.py --set-token"""
    import re
    import subprocess
    import keyring
    token = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                           capture_output=True, text=True).stdout.strip()
    if not re.fullmatch(r"\d+:[\w-]{30,}", token):
        sys.exit("The clipboard doesn't hold a bot token. Copy the token from the "
                 "BotFather chat (only the token, like 123456:ABC...) and run this again.")
    keyring.set_password(TOKEN_NAME, TOKEN_USER, token)
    print(f"Saved in Windows Credential Manager as {TOKEN_NAME}.")


# ---------- storage ----------
def open_db(path: str = DB_PATH):
    global DB
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    DB = sqlite3.connect(path, isolation_level=None)  # autocommit
    DB.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        given_by TEXT,
        delta INTEGER NOT NULL,
        ts INTEGER NOT NULL)""")
    return DB


def total(chat_id: int) -> int:
    (t,) = DB.execute("SELECT COALESCE(SUM(delta), 0) FROM events WHERE chat_id=?",
                      (chat_id,)).fetchone()
    return t


def add_points(chat_id: int, given_by: str, delta: int) -> int:
    DB.execute("INSERT INTO events(chat_id, given_by, delta, ts) VALUES (?,?,?,?)",
               (chat_id, given_by, delta, int(time.time())))
    return total(chat_id)


def undo_last(chat_id: int):
    row = DB.execute("SELECT id, delta FROM events WHERE chat_id=? ORDER BY id DESC LIMIT 1",
                     (chat_id,)).fetchone()
    if row is None:
        return None, total(chat_id)
    DB.execute("DELETE FROM events WHERE id=?", (row[0],))
    return row[1], total(chat_id)


def history(chat_id: int, n: int = 10):
    return DB.execute(
        "SELECT delta, given_by, ts FROM events WHERE chat_id=? ORDER BY id DESC LIMIT ?",
        (chat_id, n)).fetchall()


def week(chat_id: int):
    return DB.execute(
        """SELECT COALESCE(SUM(CASE WHEN delta>0 THEN delta END), 0),
                  COALESCE(SUM(CASE WHEN delta<0 THEN delta END), 0),
                  COUNT(*)
           FROM events WHERE chat_id=? AND ts >= ?""",
        (chat_id, int(time.time()) - 7 * 86400)).fetchone()


def reset(chat_id: int):
    DB.execute("DELETE FROM events WHERE chat_id=?", (chat_id,))


# ---------- presentation ----------
def mood(t: int) -> str:
    if t >= 500: return "👑 legendary boyfriend"
    if t >= 200: return "🏆 boyfriend of the year"
    if t >= 50:  return "💙 very good boyfriend"
    if t >= 0:   return "⭐ good boyfriend"
    if t >= -50: return "😒 on thin ice"
    if t >= -200: return "😠 in trouble"
    return "💀 sleeping on the couch"


def fmt(n: int) -> str:
    return f"+{n}" if n > 0 else str(n)


async def reply(msg, text: str):
    """Reply, retrying a few times if the network hiccups."""
    for attempt in range(4):
        try:
            return await msg.reply_text(text)
        except NetworkError as e:  # includes TimedOut
            if attempt == 3:
                raise
            log.warning("Reply failed (%s), retrying", e)
            await asyncio.sleep(3 * (attempt + 1))


def points(n: int) -> str:
    return f"{n} point" if abs(n) == 1 else f"{n} points"


# ---------- handlers ----------
async def on_sticker(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    st = msg.sticker
    if not st or not st.set_name:
        return
    if not STICKER_SET:  # setup mode: tell people which pack this is
        await reply(msg, f"This sticker is from the pack {st.set_name}\n"
                             f"Set STICKER_SET={st.set_name} and restart me.")
        return
    if st.set_name.lower() != STICKER_SET.lower():
        return
    delta = STICKER_VALUES.get(st.file_unique_id)
    if delta is None:  # pack was edited after startup, reload once
        await load_pack(ctx.application)
        delta = STICKER_VALUES.get(st.file_unique_id)
        if delta is None:
            return
    who = msg.from_user.first_name if msg.from_user else "someone"
    t = add_points(msg.chat_id, who, delta)
    await reply(msg, f"{fmt(delta)} → total: {points(t)}\n{mood(t)}")


async def cmd_score(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = total(update.effective_chat.id)
    await reply(update.effective_message, f"Total: {points(t)}\n{mood(t)}")


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = history(update.effective_chat.id)
    if not rows:
        await reply(update.effective_message, "No points yet.")
        return
    lines = [f"{fmt(d)}  by {by}  ({time.strftime('%b %d %H:%M', time.localtime(ts))})"
             for d, by, ts in rows]
    await reply(update.effective_message, "Last points:\n" + "\n".join(lines))


async def cmd_week(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    plus, minus, n = week(update.effective_chat.id)
    await reply(update.effective_message, 
        f"Last 7 days: {n} stickers\nEarned: +{plus}\nLost: {minus}\nNet: {fmt(plus + minus)}")


async def cmd_undo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d, t = undo_last(update.effective_chat.id)
    text = "Nothing to undo." if d is None else f"Undid {fmt(d)}. Total: {t}"
    await reply(update.effective_message, text)


async def cmd_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if ctx.args != ["confirm"]:
        await reply(update.effective_message, "This wipes the score. Send /reset confirm to do it.")
        return
    reset(update.effective_chat.id)
    await reply(update.effective_message, "Score reset to 0. Fresh start 🌱")


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await reply(update.effective_message, 
        "Send a Good Boyfriend Points sticker and I'll count it.\n\n"
        "/score – current total\n/history – last 10\n/week – last 7 days\n"
        "/undo – remove the last one\n/reset confirm – start over")


# ---------- startup ----------
async def load_pack(app: Application):
    s = await app.bot.get_sticker_set(STICKER_SET)
    STICKER_VALUES.clear()
    for st, val in zip(s.stickers, PACK_ORDER):
        STICKER_VALUES[st.file_unique_id] = val
    log.info("Loaded %d stickers from %s", len(STICKER_VALUES), STICKER_SET)
    if len(s.stickers) != len(PACK_ORDER):
        log.warning("Pack has %d stickers, expected %d", len(s.stickers), len(PACK_ORDER))


async def on_startup(app: Application):
    me = await app.bot.get_me()
    log.info("Running as @%s", me.username)
    if not me.can_read_all_group_messages:
        log.warning("Privacy mode is on, so in groups I only see commands, not stickers. "
                    "In @BotFather send /setprivacy, pick the bot, choose Disable, "
                    "then remove me from the group and add me back.")
    if not STICKER_SET:
        log.warning("STICKER_SET is empty. Send me any sticker from your pack "
                    "and I'll reply with the pack's name.")
        return
    try:
        await load_pack(app)
    except BadRequest as e:
        raise RuntimeError(f"Sticker pack {STICKER_SET!r} not found ({e.message}). "
                           "Use the short name, the part after t.me/addstickers/.") from e


def build_app(token: str) -> Application:
    app = Application.builder().token(token).post_init(on_startup).build()
    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(CommandHandler("score", cmd_score))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("week", cmd_week))
    app.add_handler(CommandHandler("undo", cmd_undo))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.Sticker.ALL, on_sticker))
    return app


def main():
    if "--set-token" in sys.argv:
        set_token()
        return
    open_db()
    # ALL_TYPES includes business_message: chats connected through Telegram Business
    build_app(get_token()).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
