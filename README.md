# bf-scorekeeper-bot

A Telegram bot (@bf_scorekeeper_bot) that counts Good Boyfriend Points when someone sends a sticker from the pack in a chat the bot is in.

## Run it on this PC

It counts only while the PC is on and the window is open.

1. Copy the token from the BotFather chat, then run this. It reads the token from the clipboard and saves it in Windows Credential Manager as `bf-scorekeeper-bot-token`, not in a file:
   ```
   .venv\Scripts\python bot.py --set-token
   ```
2. Double-click `run.cmd`.

## Run it all the time on Railway

1. Push this folder to a private GitHub repo.
2. On railway.com: New Project, Deploy from GitHub repo, pick the repo.
3. Variables: `BOT_TOKEN`, `STICKER_SET` is optional (the pack, bf_points_claudia, is already set in `bot.py`), `DB_PATH=/data/points.db`, and `TZ` (for example `America/New_York`) so `/history` shows local time.
4. Add a Volume mounted at `/data`, or the score resets on every redeploy.

Stop the copy on the PC first. Two copies with one token fail with "Conflict: terminated by other getUpdates request".

## Points

The value of a sticker is its place in the pack, which must be in this order: +1, +10, +50, +100, -1, -10, -50, -100. If the pack is in a different order, change `PACK_ORDER` in `bot.py`.

Each chat keeps its own score. Ranks: 💀 sleeping on the couch (below -200), 😠 in trouble, 😒 on thin ice, ⭐ good boyfriend (0 and up), 💙 very good (50+), 🏆 boyfriend of the year (200+), 👑 legendary (500+).

| Command | What it does |
|---|---|
| `/score` | Current total and rank |
| `/history` | Last 10 points and who gave them |
| `/week` | Points gained and lost in the last 7 days |
| `/undo` | Removes the last sticker's points |
| `/reset confirm` | Sets the score back to 0 |

## If something's off

- The bot ignores stickers in a group: privacy mode is on. The bot says so in its log at startup. In @BotFather send `/setprivacy`, pick the bot, choose Disable, then remove the bot from the group and add it back.
- You don't know the pack's short name: start the bot without `STICKER_SET` and send it any sticker from the pack. It replies with the name.
- "Sticker pack not found" at startup: `STICKER_SET` is wrong. Use the short name or the full `t.me/addstickers/` link.
- Wrong point values: the pack order doesn't match `PACK_ORDER`.
