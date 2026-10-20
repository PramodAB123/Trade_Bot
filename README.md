# L_bot: BTC paper-trading bot

**Fake money only.** This bot never places real orders and needs no account or API keys.
It reads public BTC/USDT prices from Binance, OKX, Kraken and Coinbase, looks for price gaps
bigger than the fees, and simulates trading them with a fake 1,000 USDT balance.

## What you need

- Python 3.10 or newer (python.org). Nothing else to install: it only uses Python's built-in libraries.

## Step 1: run the bot

Open a terminal in this folder (in File Explorer, click the address bar, type `cmd`, press Enter), then:

```
python paper_bot.py
```

Leave the window open. It prints prices every second plus a running P&L. Press **Ctrl+C** to stop.
If you restart it later, it carries on from the last fake balance.

To check everything works without internet, run `python paper_bot.py --demo` (made-up prices,
logged separately in `logs/demo/`).

If one exchange isn't reachable from your country or network, the bot prints a warning and keeps
going with the others. It needs at least two.

## Step 2: check the results after 1-2 weeks

```
python report.py
```

This prints how many opportunities it found, how many simulated trades made money after fees,
the biggest loss, the total result, how fast the gaps vanished, and a plain verdict.

## Running it in the cloud

See `RAILWAY.md` for running it on Railway for 2 weeks, so your PC doesn't need to stay on.

## How it works, in plain words

1. **Prices** (`fetch_*` in `paper_bot.py`): every second it asks each exchange for its best
   *bid* (what a buyer pays you) and *ask* (what a seller charges you). You buy at the ask and
   sell at the bid, so those are used instead of the "last price".
2. **Opportunities** (`find_opportunities`): for every pair of exchanges it checks whether
   buying on one and selling on the other beats both fees plus a safety margin. If so, it logs it.
3. **Simulated trade** (`simulate_trade`): it waits a random 0.3-0.8 seconds (the time a real
   order takes), re-reads prices, adds a little slippage, takes fees off both sides, and records
   what you would really have made or lost.
4. **Logs** (`logs/opportunities.csv`, `logs/trades.csv`): every opportunity and every simulated
   trade, with the running balance. Open them in Excel if you like.
5. **Cooldown**: after trading a pair it waits 5 seconds before trading that same pair again,
   so one gap isn't counted over and over.

All the numbers (fees, trade size, delay, slippage, safety margin) are in `config.py`.
The fees are typical starter-tier taker fees; edit them to match your real account tier.

## What the simulation does NOT count

- Moving money between exchanges (withdrawal fees and waiting time). Real cross-exchange
  trading needs funds already sitting on both sides.
- Order book depth: a larger order moves the price more than the slippage setting assumes.
- Your real connection speed, which is usually slower than professional firms'.

So a paper profit is the *best case*, not a promise. Not financial advice.
