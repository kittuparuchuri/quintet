"""The gatekeeper: every Signal passes through here. APPROVED or VETO, always logged."""
from dotenv import load_dotenv; load_dotenv()
import os
from dataclasses import dataclass
from datetime import datetime, timezone
import numpy as np
import store
import bot_state
from data_service import is_fresh

RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.005"))
MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "0.02"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "4"))
ATR_MULT, ATR_LEN = 2.0, 14
CORR_LIMIT = 0.8

@dataclass
class OrderIntent:
    symbol: str
    side: str
    qty: float
    stop_price: float
    strategy: str

def _log_veto(symbol, strategy, reason):
    with store._conn() as c:
        c.execute("INSERT INTO vetoes(ts, symbol, strategy, reason) VALUES (?,?,?,?)",
                  (datetime.now(timezone.utc).isoformat(), symbol, strategy, reason))
    print(f"VETO {symbol} [{strategy}]: {reason}")

def _atr(df, n=ATR_LEN):
    hi, lo, cl = df["high"], df["low"], df["close"]
    tr = np.maximum(hi - lo, np.maximum(abs(hi - cl.shift()), abs(lo - cl.shift())))
    return tr.rolling(n).mean().iloc[-1]

def _correlation(sym_a, tf_a, sym_b, tf_b, days=60):
    a = store.load_df(sym_a, tf_a)["close"].resample("1D").last().dropna().pct_change().tail(days)
    b = store.load_df(sym_b, tf_b)["close"].resample("1D").last().dropna().pct_change().tail(days)
    joined = a.to_frame("a").join(b.to_frame("b"), how="inner").dropna()
    if len(joined) < 20:
        return 0.0
    return float(joined["a"].corr(joined["b"]))

def evaluate(signal, equity, todays_pnl_pct, open_positions, tf_label):
    if bot_state.get_state() != bot_state.RUNNING:
        _log_veto(signal.symbol, signal.strategy, "bot HALTED"); return None
    if not is_fresh(signal.symbol, tf_label):
        _log_veto(signal.symbol, signal.strategy, "stale data"); return None
    if todays_pnl_pct <= -MAX_DAILY_LOSS:
        bot_state.set_state(bot_state.HALTED)
        _log_veto(signal.symbol, signal.strategy,
                  f"daily loss cap hit ({todays_pnl_pct:.2%}) -> HALTED"); return None
    if len(open_positions) >= MAX_OPEN_POSITIONS:
        _log_veto(signal.symbol, signal.strategy, "max open positions"); return None
    for held, held_tf in open_positions.items():
        rho = _correlation(signal.symbol, tf_label, held, held_tf)
        if rho > CORR_LIMIT:
            _log_veto(signal.symbol, signal.strategy,
                      f"corr filter: {held} open (rho {rho:.2f})"); return None
    df = store.load_df(signal.symbol, tf_label)
    a = _atr(df)
    if not a or a != a:
        _log_veto(signal.symbol, signal.strategy, "ATR unavailable"); return None
    entry_est = float(df["close"].iloc[-1])
    qty = np.floor((equity * RISK_PER_TRADE) / (ATR_MULT * a))
    max_qty = np.floor((equity * 0.20) / entry_est)
    qty = float(min(qty, max_qty))
    if qty < 1:
        _log_veto(signal.symbol, signal.strategy, "qty rounds to zero"); return None
    stop_price = round(float(entry_est - ATR_MULT * a), 2)
    return OrderIntent(signal.symbol, signal.side, qty, stop_price, signal.strategy)

