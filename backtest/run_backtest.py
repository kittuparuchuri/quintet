"""Honest backtest v2: ATR-based stop (2x ATR) instead of fixed 1% price stop."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np
import store
from strategies import meanrev, breakout, trend

ATR_MULT = 2.0       # stop sits 2 ATRs below entry — outside normal noise
ATR_LEN = 14
COSTS = {            # fee + slippage per SIDE (entry and exit each pay this)
    "SPY": 0.0002, "QQQ": 0.0002,        # 0.02%
    "GLD": 0.0005, "USO": 0.0005,        # 0.05%
    "BTC/USD": 0.0035,                    # 0.25% fee + 0.10% slippage
}
PLAN = [
        # ("SPY", "15Min", meanrev),      # retired, exp 2
        # ("QQQ", "15Min", meanrev),      # retired, exp 2
        # ("BTC/USD", "1Hour", breakout), # retired, exp 3
        ("GLD", "4Hour", trend),
        ("USO", "4Hour", trend),
        ]

SPLIT = "2025-01-01"     # tune BEFORE this date; judge AFTER (sealed exam)

def atr(df, n=ATR_LEN):
    """Average True Range: the market's typical candle-to-candle wiggle."""
    hi, lo, cl = df["high"], df["low"], df["close"]
    tr = np.maximum(hi - lo, np.maximum(abs(hi - cl.shift()), abs(lo - cl.shift())))
    return tr.rolling(n).mean()

def run(symbol, tf, strat, df):
    cost = COSTS[symbol]
    a = atr(df)                       # pre-compute volatility for every candle
    in_pos, entry_px, stop_px = False, 0.0, 0.0
    trades = []                       # each trade: net return fraction
    for i in range(60, len(df) - 1):
        window = df.iloc[:i + 1]
        last_close = window["close"].iloc[-1]
        if in_pos:
            # 1) volatility-sized stop first
            if df["low"].iloc[i] <= stop_px:
                trades.append((stop_px / entry_px) - 1 - 2 * cost)
                in_pos = False
                continue
            # 2) strategy exit?
            sig = strat.evaluate(window, symbol, True)
            if sig and sig.side == "sell":
                trades.append((last_close / entry_px) - 1 - 2 * cost)
                in_pos = False
        else:
            sig = strat.evaluate(window, symbol, False)
            if sig and sig.side == "buy":
                entry_px = df["open"].iloc[i + 1]                 # next candle's open
                stop_px = entry_px - ATR_MULT * a.iloc[i]         # 2 ATRs below entry
                in_pos = True
    return trades

def report(label, trades):
    if not trades:
        print(f"  {label}: no trades", flush=True); return
    r = np.array(trades)
    equity = np.cumprod(1 + r)
    peak = np.maximum.accumulate(equity)
    max_dd = ((equity - peak) / peak).min()
    wins = (r > 0).mean()
    print(f"  {label:12} trades={len(r):5}  total={equity[-1]-1:+8.1%}  "
          f"maxDD={max_dd:7.1%}  win%={wins:5.1%}  avg={r.mean():+7.4%}", flush=True)

for symbol, tf, strat in PLAN:
    df = store.load_df(symbol, tf)
    df_in = df[df.index < SPLIT]
    df_out = df[df.index >= SPLIT]
    print(f"\n{symbol} {tf} [{strat.__name__.split('.')[-1]}]", flush=True)
    report("in-sample", run(symbol, tf, strat, df_in))
    report("OUT-sample", run(symbol, tf, strat, df_out))   # SEALED while tuning