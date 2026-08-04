"""Momentum breakout: price punching a recent high on heavy volume is real."""
from datetime import datetime, timezone
from models import Signal

LOOKBACK = 55
VOL_MULT = 1.5       # volume must be 1.5x its average — the fakeout filter
STOP_EXIT = 0.985    # simple exit: close 1.5% below the recent high -> leave

def evaluate(df, symbol: str, in_position: bool) -> Signal | None:
    if len(df) < LOOKBACK + 1:
        return None
    window = df.iloc[-(LOOKBACK + 1):-1]          # the 20 candles BEFORE now
    prev_high = window["high"].max()
    avg_vol = window["volume"].mean()
    last = df.iloc[-1]
    now = datetime.now(timezone.utc)
    if not in_position and last["close"] > prev_high and last["volume"] > VOL_MULT * avg_vol:
        return Signal(symbol, "buy", "breakout", now,
                      note=f"broke {prev_high:.0f}, vol {last['volume']/avg_vol:.1f}x")
    if in_position and last["close"] < prev_high * STOP_EXIT:
        return Signal(symbol, "sell", "breakout", now, note="momentum faded")
    return None