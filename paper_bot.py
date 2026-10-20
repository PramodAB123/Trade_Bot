"""Paper-trading bot: watches BTC/USDT on several exchanges and simulates
trades on price gaps using FAKE money.

It never places real orders. It only reads public price data, so it needs
no account and no API keys.

Run:            python paper_bot.py
Offline demo:   python paper_bot.py --demo
Stop:           Ctrl+C
"""

import argparse
import csv
import json
import os
import random
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import config
import report

USER_AGENT = "L_bot-paper-trader/1.0"


# ---------------------------------------------------------------------------
# Part 1: reading prices
# Each exchange returns the best "bid" (highest price someone will pay you)
# and "ask" (lowest price someone will sell to you). You buy at the ask and
# sell at the bid, so we always use those, not the "last traded" price.
# ---------------------------------------------------------------------------

def _get_json(url, timeout=3):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def fetch_binance():
    # Binance's public market-data host. No account needed.
    for host in ("https://data-api.binance.vision", "https://api.binance.com"):
        try:
            d = _get_json(f"{host}/api/v3/ticker/bookTicker?symbol=BTCUSDT")
            return float(d["bidPrice"]), float(d["askPrice"])
        except Exception:
            continue
    raise RuntimeError("Binance unreachable")


def fetch_okx():
    d = _get_json("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
    t = d["data"][0]
    return float(t["bidPx"]), float(t["askPx"])


def fetch_kraken():
    d = _get_json("https://api.kraken.com/0/public/Ticker?pair=XBTUSDT")
    if d.get("error"):
        raise RuntimeError(str(d["error"]))
    t = next(iter(d["result"].values()))
    return float(t["b"][0]), float(t["a"][0])


def fetch_coinbase():
    d = _get_json("https://api.exchange.coinbase.com/products/BTC-USDT/ticker")
    return float(d["bid"]), float(d["ask"])


FETCHERS = {
    "binance": fetch_binance,
    "okx": fetch_okx,
    "kraken": fetch_kraken,
    "coinbase": fetch_coinbase,
}


class DemoPrices:
    """Fake prices for testing without internet. Gaps are random, not real."""

    def __init__(self):
        self.mid = 100000.0

    def fetch_all(self):
        self.mid *= 1 + random.gauss(0, 0.0003)
        out = {}
        for name in FETCHERS:
            m = self.mid * (1 + random.gauss(0, 0.002))
            spread = m * 0.0001
            out[name] = (m - spread / 2, m + spread / 2)
        return out


_pool = ThreadPoolExecutor(max_workers=len(FETCHERS))
_warned = set()


def fetch_all_live():
    """Ask every exchange at the same time. Skip any that fail this round."""
    futures = {name: _pool.submit(fn) for name, fn in FETCHERS.items()}
    prices = {}
    for name, fut in futures.items():
        try:
            prices[name] = fut.result(timeout=5)
            _warned.discard(name)
        except Exception as e:
            if name not in _warned:
                print(f"  [warn] {name} unavailable: {e}")
                _warned.add(name)
    return prices


# ---------------------------------------------------------------------------
# Part 2: spotting an opportunity
# For every pair of exchanges, check: if I buy on A (at A's ask) and sell on
# B (at B's bid), is the gap bigger than both fees plus a safety margin?
# ---------------------------------------------------------------------------

def find_opportunities(prices):
    opps = []
    for buy_ex, (_, ask) in prices.items():
        for sell_ex, (bid, _) in prices.items():
            if buy_ex == sell_ex:
                continue
            gap = (bid - ask) / ask
            needed = config.FEES[buy_ex] + config.FEES[sell_ex] + config.SAFETY_MARGIN
            if gap > needed:
                opps.append({
                    "buy_ex": buy_ex, "sell_ex": sell_ex,
                    "buy_price": ask, "sell_price": bid,
                    "gap_pct": gap * 100, "needed_pct": needed * 100,
                })
    return sorted(opps, key=lambda o: o["gap_pct"] - o["needed_pct"], reverse=True)


# ---------------------------------------------------------------------------
# Part 3: simulating the trade
# Real orders take time to reach the exchange, and the price moves meanwhile.
# So we wait a short random delay, re-read the prices, add slippage, take
# fees off both sides, and see what we would really have made.
# ---------------------------------------------------------------------------

def simulate_trade(opp, balance, fetch_all):
    size = min(config.TRADE_SIZE, balance)
    if size <= 0:
        return None

    delay = random.uniform(config.DELAY_MIN, config.DELAY_MAX)
    time.sleep(delay)
    later = fetch_all()
    if opp["buy_ex"] not in later or opp["sell_ex"] not in later:
        return None  # an exchange dropped out; skip rather than guess

    buy_fill = later[opp["buy_ex"]][1] * (1 + config.SLIPPAGE)
    sell_fill = later[opp["sell_ex"]][0] * (1 - config.SLIPPAGE)

    btc = size / buy_fill
    buy_fee = size * config.FEES[opp["buy_ex"]]
    proceeds = btc * sell_fill
    sell_fee = proceeds * config.FEES[opp["sell_ex"]]
    pnl = proceeds - size - buy_fee - sell_fee

    return {
        "buy_ex": opp["buy_ex"], "sell_ex": opp["sell_ex"],
        "size_usdt": round(size, 2), "delay_s": round(delay, 3),
        "seen_buy": round(opp["buy_price"], 2), "seen_sell": round(opp["sell_price"], 2),
        "fill_buy": round(buy_fill, 2), "fill_sell": round(sell_fill, 2),
        "seen_gap_pct": round(opp["gap_pct"], 4),
        "fill_gap_pct": round((sell_fill - buy_fill) / buy_fill * 100, 4),
        "fees_usdt": round(buy_fee + sell_fee, 4),
        "pnl_usdt": round(pnl, 4),
    }


# ---------------------------------------------------------------------------
# Part 4: saving to CSV
# ---------------------------------------------------------------------------

OPP_FIELDS = ["time", "buy_ex", "sell_ex", "buy_price", "sell_price", "gap_pct", "needed_pct", "traded"]
TRADE_FIELDS = ["time", "buy_ex", "sell_ex", "size_usdt", "delay_s", "seen_buy", "seen_sell",
                "fill_buy", "fill_sell", "seen_gap_pct", "fill_gap_pct", "fees_usdt",
                "pnl_usdt", "balance_after", "total_pnl"]


def open_log(path, fields):
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    f = open(path, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=fields)
    if new:
        w.writeheader()
    return f, w


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def last_balance(path):
    """Continue from the last balance if the bot is restarted."""
    if not os.path.exists(path):
        return config.STARTING_BALANCE
    last = None
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            last = row
    return float(last["balance_after"]) if last else config.STARTING_BALANCE


# ---------------------------------------------------------------------------
# Part 5: the main loop
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="BTC paper-trading bot (fake money only)")
    ap.add_argument("--demo", action="store_true", help="use fake offline prices (for testing)")
    ap.add_argument("--minutes", type=float, default=0, help="stop after N minutes (0 = run until Ctrl+C)")
    args = ap.parse_args()

    log_dir = os.path.join(config.LOG_DIR, "demo") if args.demo else config.LOG_DIR
    os.makedirs(log_dir, exist_ok=True)
    opp_path = os.path.join(log_dir, "opportunities.csv")
    trade_path = os.path.join(log_dir, "trades.csv")

    fetch_all = DemoPrices().fetch_all if args.demo else fetch_all_live
    balance = last_balance(trade_path)
    total_pnl = balance - config.STARTING_BALANCE
    last_trade_at = {}
    n_opps = n_trades = 0
    end_at = time.time() + args.minutes * 60 if args.minutes else None
    # On a server (Railway) there is no live screen, so print full lines less often.
    server = not sys.stdout.isatty()
    last_status = 0
    next_report = time.time() + config.REPORT_EVERY_HOURS * 3600

    opp_f, opp_w = open_log(opp_path, OPP_FIELDS)
    trade_f, trade_w = open_log(trade_path, TRADE_FIELDS)

    print("PAPER TRADING ONLY. No real orders are placed.")
    print(f"Mode: {'DEMO (fake prices)' if args.demo else 'LIVE public prices'}")
    print(f"Balance: {balance:.2f} USDT | logs in {log_dir}/ | Ctrl+C to stop\n")

    try:
        while end_at is None or time.time() < end_at:
            tick = time.time()
            prices = fetch_all()

            if len(prices) >= 2:
                for opp in find_opportunities(prices):
                    pair = (opp["buy_ex"], opp["sell_ex"])
                    cooling = tick - last_trade_at.get(pair, 0) < config.COOLDOWN_SECONDS
                    trade = None if cooling else simulate_trade(opp, balance, fetch_all)

                    n_opps += 1
                    opp_w.writerow({"time": now(), **{k: opp[k] for k in OPP_FIELDS[1:7]},
                                    "traded": trade is not None})
                    if trade:
                        last_trade_at[pair] = tick
                        balance += trade["pnl_usdt"]
                        total_pnl += trade["pnl_usdt"]
                        n_trades += 1
                        trade_w.writerow({"time": now(), **trade,
                                          "balance_after": round(balance, 4),
                                          "total_pnl": round(total_pnl, 4)})
                        trade_f.flush()
                        print(f"  TRADE buy {trade['buy_ex']} @ {trade['fill_buy']:.2f} -> "
                              f"sell {trade['sell_ex']} @ {trade['fill_sell']:.2f} | "
                              f"pnl {trade['pnl_usdt']:+.4f} USDT", flush=True)
                opp_f.flush()

            quotes = "  ".join(f"{k}:{(b + a) / 2:,.1f}" for k, (b, a) in sorted(prices.items()))
            if len(prices) < 2:
                quotes = f"waiting: only {len(prices)} exchange(s) responding"
            status = (f"{datetime.now():%H:%M:%S}  {quotes}  | opps {n_opps}  trades {n_trades}  "
                      f"P&L {total_pnl:+.2f}  bal {balance:.2f}")
            if not server:
                print(f"\r{status}   ", end="", flush=True)
            elif tick - last_status >= config.STATUS_EVERY_SECONDS:
                print(status, flush=True)
                last_status = tick

            if server and tick >= next_report:
                print(flush=True)
                report.print_report(log_dir, args.demo)
                print(flush=True)
                next_report = tick + config.REPORT_EVERY_HOURS * 3600

            time.sleep(max(0, config.POLL_SECONDS - (time.time() - tick)))
    except KeyboardInterrupt:
        pass
    finally:
        opp_f.close()
        trade_f.close()
        print(f"\n\nStopped. Opportunities: {n_opps}, simulated trades: {n_trades}, "
              f"total P&L: {total_pnl:+.2f} USDT, balance: {balance:.2f} USDT")
        print(f"Run 'python report.py{' --demo' if args.demo else ''}' for the full report.")


if __name__ == "__main__":
    sys.exit(main())
