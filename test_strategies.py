"""Unit tests: feed each strategy fake data where WE know the answer."""
import pandas as pd
import numpy as np
from strategies import meanrev, breakout, trend

def make_df(closes, volumes=None):
    n = len(closes)
    closes = np.asarray(closes, dtype=float)          # plain array: no label trap
    vols = np.asarray(volumes if volumes is not None else [1000.0] * n, dtype=float)
    return pd.DataFrame({
        "open": closes, "high": closes * 1.001, "low": closes * 0.999,
        "close": closes, "volume": vols,
    }, index=pd.date_range("2026-01-01", periods=n, freq="15min"))

# --- meanrev: flat at 100, then a sudden plunge -> must fire BUY
df = make_df([100.0 + (i % 3) * 0.1 for i in range(30)] + [96.0])
sig = meanrev.evaluate(df, "SPY", in_position=False)
assert sig and sig.side == "buy", "meanrev should buy the plunge"
# ...and stay quiet on calm data
df_calm = make_df([100.0 + (i % 3) * 0.1 for i in range(31)])
assert meanrev.evaluate(df_calm, "SPY", False) is None, "meanrev must not fire on calm data"

# --- breakout: new high on huge volume -> BUY; same high on weak volume -> silent
base = [100 + np.sin(i / 3) for i in range(25)]
df_break = make_df(base + [103.0], volumes=[1000.0] * 25 + [2500.0])
sig = breakout.evaluate(df_break, "BTC/USD", False)
assert sig and sig.side == "buy", "breakout should buy a high-volume break"
df_weak = make_df(base + [103.0], volumes=[1000.0] * 25 + [1100.0])
assert breakout.evaluate(df_weak, "BTC/USD", False) is None, "no volume, no trade"

# --- trend: long decline then strong recovery -> a BUY appears at the crossover
prices = list(np.linspace(120, 100, 60)) + list(np.linspace(100, 118, 30))
fired = 0
for i in range(55, 90):
    s = trend.evaluate(make_df(prices[:i + 1]), "GLD", in_position=False)
    if s and s.side == "buy":
        fired += 1
assert fired == 1, f"trend should fire exactly once at the crossover, got {fired}"

print("ALL TESTS PASSED")