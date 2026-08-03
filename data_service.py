"""The bot's eyes: download history (backfill) and listen live (stream)."""
from dotenv import load_dotenv; load_dotenv()
import os, sys, threading
from datetime import datetime, timedelta, timezone

from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.live import StockDataStream, CryptoDataStream

from models import Candle
import store

KEY, SEC = os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY")

# The five markets and their timeframes — the heart of the config
PLAN = [
    ("SPY",     "stock",  TimeFrame(15, TimeFrameUnit.Minute), "15Min"),
    ("QQQ",     "stock",  TimeFrame(15, TimeFrameUnit.Minute), "15Min"),
    ("BTC/USD", "crypto", TimeFrame(1,  TimeFrameUnit.Hour),   "1Hour"),
    ("GLD",     "stock",  TimeFrame(4,  TimeFrameUnit.Hour),   "4Hour"),
    ("USO",     "stock",  TimeFrame(4,  TimeFrameUnit.Hour),   "4Hour"),
]
TF_MINUTES = {"15Min": 15, "1Hour": 60, "4Hour": 240}

def _rows_to_candles(df, symbol, tf_label):
    out = []
    for (sym, ts), r in df.iterrows():
        out.append(Candle(symbol=sym, timeframe=tf_label, ts=ts.to_pydatetime(),
                          open=r["open"], high=r["high"], low=r["low"],
                          close=r["close"], volume=r["volume"]))
    return out

def backfill(years: int = 4):
    store.init_db()
    stocks = StockHistoricalDataClient(KEY, SEC)
    crypto = CryptoHistoricalDataClient()          # crypto data needs no keys
    start = datetime.now(timezone.utc) - timedelta(days=365 * years)

    for symbol, kind, tf, tf_label in PLAN:
        print(f"Backfilling {symbol} {tf_label} ...", flush=True)
        if kind == "stock":
            req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=tf, start=start)
            df = stocks.get_stock_bars(req).df
        else:
            req = CryptoBarsRequest(symbol_or_symbols=symbol, timeframe=tf, start=start)
            df = crypto.get_crypto_bars(req).df
        candles = _rows_to_candles(df, symbol, tf_label)
        store.save_candles(candles)
        print(f"  saved {len(candles):,} candles "
              f"({candles[0].ts:%Y-%m-%d} -> {candles[-1].ts:%Y-%m-%d})")

def is_fresh(symbol: str, tf_label: str) -> bool:
    """Data is 'fresh' if the newest candle is younger than 2x its timeframe."""
    last = store.last_candle_ts(symbol, tf_label)
    if last is None:
        return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    age_min = (datetime.now(timezone.utc) - last).total_seconds() / 60
    return age_min <= 2 * TF_MINUTES[tf_label]

def stream():
    """Listen live. Stocks and crypto use separate feeds, so: two threads."""
    store.init_db()
    tf_for = {"SPY": "15Min", "QQQ": "15Min", "GLD": "4Hour", "USO": "4Hour"}

    async def on_stock_bar(bar):   # called for every closed 1-min bar
        c = Candle(bar.symbol, "1Min", bar.timestamp, bar.open, bar.high,
                   bar.low, bar.close, bar.volume)
        store.save_candles([c])
        print(f"[stock] {bar.symbol} {bar.timestamp:%H:%M} close={bar.close}")

    async def on_crypto_bar(bar):
        c = Candle(bar.symbol, "1Min", bar.timestamp, bar.open, bar.high,
                   bar.low, bar.close, bar.volume)
        store.save_candles([c])
        print(f"[crypto] {bar.symbol} {bar.timestamp:%H:%M} close={bar.close}")

    s_stream = StockDataStream(KEY, SEC)
    s_stream.subscribe_bars(on_stock_bar, "SPY", "QQQ", "GLD", "USO")
    c_stream = CryptoDataStream(KEY, SEC)
    c_stream.subscribe_bars(on_crypto_bar, "BTC/USD")

    threading.Thread(target=s_stream.run, daemon=True).start()
    print("Streaming... Ctrl+C to stop.")
    c_stream.run()   # blocks; keeps the program alive

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "backfill"
    if cmd == "backfill":
        backfill()
    elif cmd == "stream":
        stream()
    elif cmd == "fresh":
        for sym, _, _, tf in PLAN:
            print(sym, tf, "fresh" if is_fresh(sym, tf) else "STALE")