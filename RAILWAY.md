# Run the paper bot on Railway for 10 days

Fake money only. No API keys anywhere in this setup. Total cost: well under the $5 trial credit.

## Before you start

Your `L_bot` folder already has the updated files (`paper_bot.py`, `report.py`, `config.py`)
and the new ones (`requirements.txt`, `railway.json`, `.python-version`). Don't upload your `logs` folder.

## Step 1: put the files on GitHub (about 5 minutes)

1. Go to github.com, click **+** (top right), then **New repository**.
2. Name it `L_bot`, choose **Private**, click **Create repository**.
3. On the new page, click the link **uploading an existing file**.
4. Drag in these files from your L_bot folder: `paper_bot.py`, `report.py`, `config.py`,
   `requirements.txt`, `railway.json`, `.python-version`, `README.md`.
   (If Windows hides `.python-version`, skip it. It's optional.)
5. Click **Commit changes**.

## Step 2: create the Railway service

1. Make sure your Railway account is **connected to GitHub** (Railway needs this to verify you;
   without it you get a "limited trial" that blocks most internet access, and the bot can't read prices).
2. In Railway, click **New Project**, then **Deploy from GitHub repo**, and pick `L_bot`.
   If you don't see it, click **Configure GitHub App** and give Railway access to that repo.
3. Railway starts building. That's fine, we'll adjust two things next.

## Step 3: choose a Europe or Asia region

1. Click the `L_bot` service box, then the **Settings** tab.
2. Find **Regions** and choose **EU West (Amsterdam)** (or Southeast Asia, Singapore).
   Avoid the US regions: Binance blocks US servers.

## Step 4: add a volume so the logs survive restarts

1. On the project canvas, right-click an empty spot (or press **Ctrl+K**) and choose **Volume**.
2. Attach it to the `L_bot` service and set the **mount path** to `/data`.
3. That's all. The bot sees the volume automatically and writes its CSV logs there.
   (The trial gives 0.5 GB of volume space. The logs should stay far below that.)

Adding the volume redeploys the bot. Wait for the deployment to show **Active** (green).

## Step 5: check it's working

Click the service, then **Deployments**, then **View logs**. Within a minute you should see:

```
PAPER TRADING ONLY. No real orders are placed.
Mode: LIVE public prices
Balance: 1000.00 USDT | logs in /data/ | Ctrl+C to stop
Stops by itself at 2026-10-30 07:12 UTC (10 days after the first start).
07:12:00  binance:...  coinbase:...  kraken:...  okx:...  | opps 0  trades 0  P&L +0.00  bal 1000.00
```

- It prints one status line per minute, and a line for each simulated trade.
- Check that it says `logs in /data/`. If it says `logs/`, the volume isn't attached (redo Step 4).
- A `[warn] binance unavailable` line means that exchange is blocked from this region. The bot
  keeps going with the others, but try the other non-US region if you'd like Binance included.

Then check **Usage** (your account menu, top right) after a day or two. Expect a few cents per day.

## Step 6: read the results

You don't need to do anything special. **Every 24 hours the bot prints the full report into the
logs** (the same output as `python report.py`). After 10 days the bot stops by itself and
prints a **final report**. Then open **View logs**, search for
`PAPER TRADING REPORT`, and copy the latest one. Paste it to me and we'll go over it.

Optional, if you also want the raw CSV files: install the Railway CLI
(`npm i -g @railway/cli`), then in a terminal run `railway login`, `railway link` (pick L_bot),
and `railway ssh`. Inside, `python report.py` prints the report on demand and `ls /data` shows the CSVs.

## Step 7: delete the service when you're done

The bot stops by itself after 10 days and Railway won't restart it. Restarts or redeploys
before then don't reset the 10-day clock. To change the length, edit `RUN_DAYS` in `config.py`.

Once you have the final report, click the service, **Settings**, scroll down, and click **Delete service** in the danger zone (or delete the whole
project). Copy the final report out of the logs first, because deleting removes the logs too.

## If something goes wrong

- **Build failed**: check `requirements.txt` and `railway.json` were uploaded.
- **Service keeps restarting**: open the logs and send me the last 20 lines.
- **Changed a setting in `config.py`**: edit the file on GitHub (pencil icon) and commit.
  Railway redeploys by itself, and the bot carries on from the saved balance.
