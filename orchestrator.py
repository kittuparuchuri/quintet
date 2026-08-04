"""The heartbeat: runs the proven machine on a real clock. GLD live, USO shadow."""
from dotenv import load_dotenv; load_dotenv()
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
import os
import store, bot_state, risk_engine, executor
from strategies import trend
from models import Candle

LIVE = [("GLD", "4Hour")]
SHADOW = [("USO", "4Hour")]
_data = StockHistoricalDataClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"))

def log(msg):
    line = f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC | {msg}"
    print(line, flush=True)
    with open("orchestrator.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")

def refresh(symbol, tf_label):
    tf = TimeFrame(4, TimeFrameUnit.Hour)
    req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=tf,
                           start=datetime.now(timezone.utc) - timedelta(days=10))
    df = _data.get_stock_bars(req).df
    rows = [Candle(sym, tf_label, ts.to_pydatetime(), r["open"], r["high"],
                   r["low"], r["close"], r["volume"])
            for (sym, ts), r in df.iterrows()]
    store.save_candles(rows)

def account_snapshot():
    acct = executor.client.get_account()
    equity = float(acct.equity)
    last_equity = float(acct.last_equity)
    todays_pnl_pct = (equity - last_equity) / last_equity if last_equity else 0.0
    with store._conn() as c:
        c.execute("INSERT OR REPLACE INTO equity_snapshots VALUES (?,?)",
                  (datetime.now(timezone.utc).isoformat(), equity))
    return equity, todays_pnl_pct

def tick():
    if bot_state.get_state() != bot_state.RUNNING:
        log("tick skipped: bot HALTED"); return
    positions = executor.reconcile()
    equity, pnl = account_snapshot()
    log(f"tick | equity={equity:,.0f} todays_pnl={pnl:+.2%} positions={positions or 'none'}")
    for symbol, tf_label in LIVE + SHADOW:
        is_shadow = (symbol, tf_label) in SHADOW
        refresh(symbol, tf_label)
        df = store.load_df(symbol, tf_label)
        in_pos = symbol in positions or any(o.symbol == symbol for o in executor.client.get_orders())
        sig = trend.evaluate(df, symbol, in_pos)
        if sig is None:
            log(f"{symbol}: no signal (in_pos={in_pos})"); continue
        with store._conn() as c:
            c.execute("INSERT INTO signals(ts,symbol,side,strategy,note) VALUES (?,?,?,?,?)",
                      (sig.ts.isoformat(), sig.symbol, sig.side, sig.strategy,
                       ("SHADOW " if is_shadow else "") + sig.note))
        if is_shadow:
            log(f"{symbol}: SHADOW signal {sig.side} ({sig.note}) - logged, not traded")
            continue
        if sig.side == "sell" and in_pos:
            log(f"{symbol}: strategy exit - closing position")
            executor.client.close_position(symbol)
            continue
        open_pos = {s: "4Hour" for s in positions}
        intent = risk_engine.evaluate(sig, equity, pnl, open_pos, tf_label)
        if intent:
            executor.submit(intent)
            log(f"{symbol}: order sent {intent.side} {intent.qty} stop={intent.stop_price}")

def heartbeat():
    log(f"heartbeat | state={bot_state.get_state()}")

def morning_report():
    positions = executor.reconcile()
    equity, pnl = account_snapshot()
    log(f"MORNING REPORT | equity={equity:,.0f} | positions={positions or 'none'} | state={bot_state.get_state()}")

def nightly_report():
    equity, pnl = account_snapshot()
    with store._conn() as c:
        vetoes = c.execute("SELECT COUNT(*) FROM vetoes WHERE ts > date('now')").fetchone()[0]
        sigs = c.execute("SELECT COUNT(*) FROM signals WHERE ts > date('now')").fetchone()[0]
    log(f"NIGHTLY REPORT | equity={equity:,.0f} todays_pnl={pnl:+.2%} | signals_today={sigs} vetoes_today={vetoes}")

if __name__ == "__main__":
    log("=== orchestrator starting ===")
    executor.reconcile()
    sched = BlockingScheduler(timezone="America/New_York")
    sched.add_job(tick, CronTrigger(day_of_week="mon-fri", hour="10,14", minute=0))
    sched.add_job(tick, CronTrigger(day_of_week="mon-fri", hour=15, minute=55))
    sched.add_job(heartbeat, "interval", minutes=5)
    sched.add_job(morning_report, CronTrigger(day_of_week="mon-fri", hour=8, minute=30))
    sched.add_job(nightly_report, CronTrigger(day_of_week="mon-fri", hour=17, minute=0))
    log("scheduler armed: ticks 10:00/14:00/15:55 ET, heartbeat 5min, reports 08:30/17:00 ET")
    tick()
    sched.start()

