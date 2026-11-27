# bf-scorekeeper-bot

A Telegram bot (@bf_scorekeeper_bot) that counts Good Boyfriend Points when someone sends a sticker from the pack in a chat the bot is in.

Stickers: https://t.me/addstickers/goodbfpoints (the images are in `stickers/`). The bot also counts the older copy of the pack, `bf_points_claudia`.

## Where it runs

It runs on a Linux server as a service called `bf-bot`: code in `/opt/bf-bot` (libraries in `/opt/bf-bot/lib`), token in `/etc/bf-bot.env`, scores in `/var/lib/bf-bot/points.db`, time zone America/New_York. It restarts by itself after a crash or a reboot.

Check that it's running:
```
gcloud compute ssh bf-bot --zone=us-east1-b --tunnel-through-iap --command="sudo journalctl -u bf-bot -n 20 -o cat"
```

Update the code after changing `bot.py`:
```
gcloud compute scp bot.py bf-bot: --zone=us-east1-b --tunnel-through-iap
gcloud compute ssh bf-bot --zone=us-east1-b --tunnel-through-iap --command="sudo cp bot.py /opt/bf-bot/ && sudo systemctl restart bf-bot"
```

## Run it on this PC instead

Only one copy can run at a time. Two copies with one token fail with "Conflict: terminated by other getUpdates request", so stop the server first (`sudo systemctl stop bf-bot`).

1. Copy the token from the BotFather chat, then run this. It reads the token from the clipboard and saves it in Windows Credential Manager as `bf-scorekeeper-bot-token`, not in a file:
   ```
   .venv\Scripts\python bot.py --set-token
   ```
2. Double-click `run.cmd`. It counts only while the PC is on and the window is open.

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
