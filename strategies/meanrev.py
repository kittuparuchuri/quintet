"""Mean reversion: price stretched far below its average tends to snap back."""
from datetime import datetime, timezone
from models import Signal

LOOKBACK = 20        # candles used for the average
ENTRY_Z = -2.5       # how stretched before we buy
EXIT_Z = -0.25       # snap-back point where we exit

def zscore(df):
    """How many standard deviations is the latest close from its recent average?"""
    closes = df["close"].tail(LOOKBACK + 1)
    mean = closes.iloc[:-1].mean()
    std = closes.iloc[:-1].std()
    if std == 0 or std != std:      # zero or NaN std -> no opinion
        return None
    return (closes.iloc[-1] - mean) / std

def evaluate(df, symbol: str, in_position: bool) -> Signal | None:
    """Look at the latest candle. Return a Signal or None (no opinion)."""
    if len(df) < LOOKBACK + 1:
        return None
    z = zscore(df)
    if z is None:
        return None
    now = datetime.now(timezone.utc)
    if not in_position and z < ENTRY_Z:
        return Signal(symbol, "buy", "meanrev", now, note=f"z={z:.2f}")
    if in_position and z > EXIT_Z:
        return Signal(symbol, "sell", "meanrev", now, note=f"z={z:.2f}")
    return None