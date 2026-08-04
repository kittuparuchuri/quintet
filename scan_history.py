"""Run each strategy across the whole database and count its signals."""
import store
from strategies import meanrev, breakout, trend

PLAN = [("SPY", "15Min", meanrev), ("QQQ", "15Min", meanrev),
        ("BTC/USD", "1Hour", breakout), ("GLD", "4Hour", trend), ("USO", "4Hour", trend)]

for symbol, tf, strat in PLAN:
    df = store.load_df(symbol, tf)
    in_pos, entries, exits = False, 0, 0
    for i in range(60, len(df)):
        sig = strat.evaluate(df.iloc[:i + 1], symbol, in_pos)
        if sig and sig.side == "buy" and not in_pos:
            entries += 1; in_pos = True
        elif sig and sig.side == "sell" and in_pos:
            exits += 1; in_pos = False
    print(f"{symbol:8} {tf:6} {strat.__name__.split('.')[-1]:9} "
          f"entries={entries:5}  exits={exits:5}  candles={len(df):,}", flush=True)