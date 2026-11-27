# bf-scorekeeper-bot

A Telegram bot (@bf_scorekeeper_bot) that counts Good Boyfriend Points when someone sends a sticker from the pack in a chat the bot is in.

Stickers: https://t.me/addstickers/goodbfpoints (the images are in `stickers/`). The bot also counts the older copy of the pack, `bf_points_claudia`.

## Use it

Add the stickers, add @bf_scorekeeper_bot to a group (or open a private chat with it) and send a sticker. It replies with the new total and a rank.

## Run your own copy

1. Make a bot in @BotFather and copy its token. Turn privacy mode off there (`/setprivacy`, Disable) so the bot sees stickers in groups.
2. Make your own sticker pack in @Stickers from the images in `stickers/`, in the same order, or use any pack of 8 stickers.
3. Install and start it (Python 3.10 or newer):
   ```
   pip install -r requirements.txt
   BOT_TOKEN=your-token STICKER_SET=your_pack_name python bot.py
   ```
   Scores go to `points.db` next to `bot.py`. Set `DB_PATH` to keep them somewhere else, and `TZ` for the times in `/history`.

On Windows, `python bot.py --set-token` saves the token from the clipboard to Credential Manager, and `run.cmd` starts the bot.

Only one copy can run per token. A second copy fails with "Conflict: terminated by other getUpdates request".

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
