"""Trend following: ride the wave while the fast average is above the slow one."""
from datetime import datetime, timezone
from models import Signal

FAST, SLOW = 20, 50

def evaluate(df, symbol: str, in_position: bool) -> Signal | None:
    if len(df) < SLOW + 2:
        return None
    fast = df["close"].ewm(span=FAST, adjust=False).mean()
    slow = df["close"].ewm(span=SLOW, adjust=False).mean()
    now = datetime.now(timezone.utc)
    above_now = fast.iloc[-1] > slow.iloc[-1]
    above_before = fast.iloc[-2] > slow.iloc[-2]
    if not in_position and above_now and not above_before:      # fresh crossover up
        return Signal(symbol, "buy", "trend", now, note="EMA20 crossed above EMA50")
    if in_position and not above_now and above_before:          # crossover down
        return Signal(symbol, "sell", "trend", now, note="EMA20 crossed below EMA50")
    return None