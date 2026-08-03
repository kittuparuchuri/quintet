"""SQLite persistence. The whole database is one file: quintet.db."""
import sqlite3
from datetime import datetime, timezone
from models import Candle

DB_PATH = "quintet.db"

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("PRAGMA journal_mode=WAL;")   # safer concurrent reads/writes
    return c

def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS candles(
            symbol TEXT, timeframe TEXT, ts TEXT,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            PRIMARY KEY(symbol, timeframe, ts));
        CREATE TABLE IF NOT EXISTS signals(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, symbol TEXT,
            side TEXT, strategy TEXT, note TEXT);
        CREATE TABLE IF NOT EXISTS vetoes(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, symbol TEXT,
            strategy TEXT, reason TEXT);
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, symbol TEXT,
            side TEXT, qty REAL, order_id TEXT, status TEXT);
        CREATE TABLE IF NOT EXISTS equity_snapshots(
            ts TEXT PRIMARY KEY, equity REAL);
        """)

def save_candles(rows: list[Candle]):
    with _conn() as c:
        c.executemany(
            "INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)",
            [(r.symbol, r.timeframe, r.ts.isoformat(),
              r.open, r.high, r.low, r.close, r.volume) for r in rows])

def last_candle_ts(symbol: str, timeframe: str):
    with _conn() as c:
        row = c.execute(
            "SELECT MAX(ts) FROM candles WHERE symbol=? AND timeframe=?",
            (symbol, timeframe)).fetchone()
    return datetime.fromisoformat(row[0]) if row and row[0] else None

def count_candles(symbol: str, timeframe: str) -> int:
    with _conn() as c:
        return c.execute(
            "SELECT COUNT(*) FROM candles WHERE symbol=? AND timeframe=?",
            (symbol, timeframe)).fetchone()[0]