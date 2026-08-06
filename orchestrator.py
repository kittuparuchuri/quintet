"""Multi-market orchestrator: per-symbol strategy, timeframe, and live/shadow mode."""
from dotenv import load_dotenv; load_dotenv()
import os
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
import store, bot_state, risk_engine, executor
from strategies import trend, meanrev, breakout
from models import Candle

# symbol, kind, tf_label, timeframe, strategy, mode ("live" or "shadow")
PLAN = [
    ("SPY",     "stock",  "15Min", TimeFrame(15, TimeFrameUnit.Minute), meanrev,  "live"),
    ("QQQ",     "stock",  "15Min", TimeFrame(15, TimeFrameUnit.Minute), meanrev,  "live"),
    ("BTC/USD", "crypto", "1Hour", TimeFrame(1,  TimeFrameUnit.Hour),   breakout, "shadow"),
    ("GLD",     "stock",  "4Hour", TimeFrame(4,  TimeFrameUnit.Hour),   trend,    "live"),
    ("USO",     "stock",  "4Hour", TimeFrame(4,  TimeFrameUnit.Hour),   trend,    "live"),
]

_stock = StockHistoricalDataClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"))
_crypto = CryptoHistoricalDataClient()

def log(msg):
    line = f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC | {msg}"
    print(line, flush=True)
    with open("orchestrator.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")

def refresh(symbol, kind, tf, tf_label):
    start = datetime.now(timezone.utc) - timedelta(days=10)
    if kind == "stock":
        df = _stock.get_stock_bars(StockBarsRequest(symbol_or_symbols=symbol, timeframe=tf, start=start)).df
    else:
        df = _crypto.get_crypto_bars(CryptoBarsRequest(symbol_or_symbols=symbol, timeframe=tf, start=start)).df
    rows = [Candle(sym, tf_label, ts.to_pydatetime(), r["open"], r["high"], r["low"], r["close"], r["volume"])
            for (sym, ts), r in df.iterrows()]
    store.save_candles(rows)

def account_snapshot():
    acct = executor.client.get_account()
    equity = float(acct.equity)
    last_equity = float(acct.last_equity)
    pnl = (equity - last_equity) / last_equity if last_equity else 0.0
    with store._conn() as c:
        c.execute("INSERT OR REPLACE INTO equity_snapshots VALUES (?,?)",
                  (datetime.now(timezone.utc).isoformat(), equity))
    return equity, pnl

def open_order_symbols():
    return {o.symbol.replace("USD", "/USD") if o.symbol == "BTCUSD" else o.symbol
            for o in executor.client.get_orders()}

def tick(group):
    if bot_state.get_state() != bot_state.RUNNING:
        log("tick skipped: bot HALTED"); return
    positions = executor.reconcile()
    pending = open_order_symbols()
    equity, pnl = account_snapshot()
    log(f"tick[{group}] | equity={equity:,.0f} todays_pnl={pnl:+.2%} positions={positions or 'none'}")
    for symbol, kind, tf_label, tf, strat, mode in PLAN:
        if group != "all" and tf_label != group:
            continue
        alp = symbol.replace("/", "")
        in_pos = alp in positions or symbol in pending or alp in pending
        try:
            refresh(symbol, kind, tf, tf_label)
        except Exception as e:
            log(f"{symbol}: refresh failed ({e}) - skipping"); continue
        df = store.load_df(symbol, tf_label)
        sig = strat.evaluate(df, symbol, in_pos)
        name = strat.__name__.split(".")[-1]
        if sig is None:
            log(f"{symbol} [{name}] no signal (in_pos={in_pos})"); continue
        with store._conn() as c:
            c.execute("INSERT INTO signals(ts,symbol,side,strategy,note) VALUES (?,?,?,?,?)",
                      (sig.ts.isoformat(), sig.symbol, sig.side, sig.strategy,
                       ("SHADOW " if mode == "shadow" else "") + sig.note))
        if mode == "shadow":
            log(f"{symbol} [{name}] SHADOW {sig.side} ({sig.note}) - logged only"); continue
        if sig.side == "sell" and in_pos:
            log(f"{symbol} [{name}] strategy exit - closing")
            try: executor.client.close_position(alp)
            except Exception as e: log(f"{symbol}: close failed ({e})")
            continue
        open_pos = {s: "4Hour" for s in positions}
        intent = risk_engine.evaluate(sig, equity, pnl, open_pos, tf_label)
        if intent:
            executor.submit(intent)
            log(f"{symbol} [{name}] ORDER {intent.side} {intent.qty} stop={intent.stop_price}")

def heartbeat():
    log(f"heartbeat | state={bot_state.get_state()}")
    url = os.getenv("HEALTHCHECK_URL")
    if url:
        try:
            import httpx; httpx.get(url, timeout=10)
        except Exception as e:
            log(f"healthcheck ping failed: {e}")

def morning_report():
    positions = executor.reconcile(); equity, pnl = account_snapshot()
    log(f"MORNING REPORT | equity={equity:,.0f} | positions={positions or 'none'} | state={bot_state.get_state()}")

def nightly_report():
    equity, pnl = account_snapshot()
    with store._conn() as c:
        v = c.execute("SELECT COUNT(*) FROM vetoes WHERE ts > date('now')").fetchone()[0]
        s = c.execute("SELECT COUNT(*) FROM signals WHERE ts > date('now')").fetchone()[0]
    log(f"NIGHTLY REPORT | equity={equity:,.0f} todays_pnl={pnl:+.2%} | signals_today={s} vetoes_today={v}")

if __name__ == "__main__":
    store.init_db()
    log("=== multi-market orchestrator starting ===")
    executor.reconcile()
    sched = BlockingScheduler(timezone="America/New_York")
    sched.add_job(lambda: tick("15Min"), CronTrigger(day_of_week="mon-fri", hour="10-15", minute="0,15,30,45"))
    sched.add_job(lambda: tick("15Min"), CronTrigger(day_of_week="mon-fri", hour=9, minute=45))
    sched.add_job(lambda: tick("1Hour"), CronTrigger(minute=2))
    sched.add_job(lambda: tick("4Hour"), CronTrigger(day_of_week="mon-fri", hour="10,14", minute=5))
    sched.add_job(lambda: tick("4Hour"), CronTrigger(day_of_week="mon-fri", hour=15, minute=55))
    sched.add_job(heartbeat, "interval", minutes=5)
    sched.add_job(morning_report, CronTrigger(day_of_week="mon-fri", hour=8, minute=30))
    sched.add_job(nightly_report, CronTrigger(day_of_week="mon-fri", hour=17, minute=0))
    log("armed: 15m SPY/QQQ (mkt hrs), 1h BTC (24/7), 4h GLD/USO, heartbeat 5m, reports 08:30/17:00 ET")
    tick("all")
    sched.start()
