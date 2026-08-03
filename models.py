"""Shared data shapes every module passes around."""
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Candle:
    symbol: str        # "SPY", "BTC/USD", ...
    timeframe: str     # "15Min", "1Hour", "4Hour"
    ts: datetime       # when this candle closed (UTC)
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class Signal:
    symbol: str
    side: str          # "buy" or "sell"
    strategy: str      # "meanrev", "breakout", "trend"
    ts: datetime
    note: str = ""     # optional context, e.g. "z=-2.3"