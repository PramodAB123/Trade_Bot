"""Settings for the paper-trading bot. Change numbers here, not in the code.

This bot never places real orders and needs no API keys.
"""

import os

# Fake starting balance in USDT.
STARTING_BALANCE = 1000.0

# How much of the fake balance to use per simulated trade (USDT).
TRADE_SIZE = 200.0

# How often to check prices, in seconds.
POLL_SECONDS = 1.0

# Taker fees per exchange, as a fraction (0.001 = 0.10%).
# These are typical entry-level fees. Check your own account tier and edit if needed.
FEES = {
    "binance": 0.0010,
    "okx": 0.0010,
    "kraken": 0.0040,
    "coinbase": 0.0060,
}

# Extra gap required on top of both fees before we call it an "opportunity"
# (0.0005 = 0.05%).
SAFETY_MARGIN = 0.0005

# Simulated delay between spotting a gap and the orders filling, in seconds.
# The bot waits this long, re-reads prices, and fills at those new prices.
DELAY_MIN = 0.3
DELAY_MAX = 0.8

# Extra price slippage applied to each fill (0.0002 = 0.02%).
SLIPPAGE = 0.0002

# After a simulated trade on a pair of exchanges, wait this many seconds
# before trading that same pair again (stops one gap being counted many times).
COOLDOWN_SECONDS = 5.0

# Where the CSV logs go. On Railway this is the volume folder, so the logs
# survive restarts. On your PC it is the "logs" folder next to this file.
LOG_DIR = os.environ.get("LOG_DIR") or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") or "logs"

# On a server, print a status line every this many seconds (instead of every second).
STATUS_EVERY_SECONDS = 60

# On a server, print the full report into the logs every this many hours.
REPORT_EVERY_HOURS = 24
