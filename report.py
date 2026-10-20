"""Step 2: an honest report on the paper-trading logs.

Run:   python report.py          (live logs)
       python report.py --demo   (demo logs)
"""

import argparse
import csv
import os
from collections import Counter
from datetime import datetime

import config


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    log_dir = os.path.join(config.LOG_DIR, "demo") if args.demo else config.LOG_DIR
    print_report(log_dir, args.demo)


def print_report(log_dir, demo=False):
    opps = load(os.path.join(log_dir, "opportunities.csv"))
    trades = load(os.path.join(log_dir, "trades.csv"))

    print("=" * 60)
    print("PAPER TRADING REPORT" + ("  (DEMO DATA - not real prices)" if demo else ""))
    print("=" * 60)

    if not opps and not trades:
        print("No data yet. Run paper_bot.py first and let it collect data.")
        return

    times = [datetime.fromisoformat(r["time"]) for r in opps + trades]
    span_h = (max(times) - min(times)).total_seconds() / 3600
    print(f"Period covered:            {min(times):%Y-%m-%d %H:%M} to {max(times):%Y-%m-%d %H:%M} UTC "
          f"({span_h:.1f} hours)")
    print(f"Opportunities logged:      {len(opps)}")
    print(f"Simulated trades:          {len(trades)}")

    if not trades:
        print("\nNo simulated trades yet, so there is nothing to judge.")
        return

    pnls = [float(t["pnl_usdt"]) for t in trades]
    wins = [p for p in pnls if p > 0]
    total = sum(pnls)
    fees = sum(float(t["fees_usdt"]) for t in trades)
    seen = [float(t["seen_gap_pct"]) for t in trades]
    filled = [float(t["fill_gap_pct"]) for t in trades]
    closed = sum(1 for t in trades if float(t["fill_gap_pct"]) <= 0)

    print(f"Trades that made money:    {len(wins)} of {len(trades)} ({len(wins) / len(trades):.0%}) after fees")
    print(f"Biggest single loss:       {min(pnls):+.4f} USDT")
    print(f"Biggest single win:        {max(pnls):+.4f} USDT")
    print(f"Total fees paid:           {fees:.4f} USDT")
    print(f"TOTAL RESULT:              {total:+.4f} USDT on a {config.STARTING_BALANCE:.0f} USDT balance "
          f"({total / config.STARTING_BALANCE:+.2%})")

    print("\nHow fast the gaps disappeared")
    print(f"  Average gap when spotted:     {sum(seen) / len(seen):.4f}%")
    print(f"  Average gap when 'filled':    {sum(filled) / len(filled):.4f}%")
    print(f"  Gap gone or reversed by fill: {closed} of {len(trades)} trades")

    pairs = Counter(f"{t['buy_ex']} -> {t['sell_ex']}" for t in trades)
    print("\nMost common routes")
    for route, n in pairs.most_common(5):
        route_pnl = sum(float(t["pnl_usdt"]) for t in trades if f"{t['buy_ex']} -> {t['sell_ex']}" == route)
        print(f"  {route:22s} {n:5d} trades  {route_pnl:+.4f} USDT")

    print("\nHonest verdict")
    if span_h < 24 * 7:
        print(f"  - Only {span_h:.1f} hours of data. The guide suggests 1-2 weeks before drawing conclusions.")
    if total <= 0:
        print("  - The simulation LOST money after fees and delay. Real trading would very likely do worse.")
    else:
        print("  - The simulation shows a profit, but treat it with suspicion:")
    print("  - Real fills are slower than this simulation for a home connection, and order book depth is")
    print("    ignored here (a big order would move the price more than the slippage setting assumes).")
    print("  - Buying on one exchange and selling on another needs money parked on both. Moving funds")
    print("    between them costs withdrawal fees and time, which this simulation does not count.")
    print("  - Professional firms with faster servers and lower fees usually take these gaps first.")
    print("  - Not financial advice.")


if __name__ == "__main__":
    main()
