"""Assembles the plain facts for daily reports. Used by Cowork (via MCP) and as email backup."""
from dotenv import load_dotenv; load_dotenv()
import os
from datetime import datetime, timezone
import store, executor, bot_state

def market_conditions():
    """One line per market: latest price, trend direction, freshness."""
    from data_service import is_fresh, PLAN as DATA_PLAN
    lines = []
    for symbol, kind, tf, tf_label in DATA_PLAN:
        try:
            df = store.load_df(symbol, tf_label)
            last = df.iloc[-1]
            fresh = "fresh" if is_fresh(symbol, tf_label) else "STALE"
            lines.append(f"{symbol}: close={last['close']:.2f} ({fresh}, {tf_label})")
        except Exception as e:
            lines.append(f"{symbol}: no data ({e})")
    return lines

def positions_and_pnl():
    positions = executor.reconcile()
    acct = executor.client.get_account()
    equity = float(acct.equity)
    last_equity = float(acct.last_equity)
    pnl_pct = (equity - last_equity) / last_equity if last_equity else 0.0
    return {"positions": positions, "equity": equity, "todays_pnl_pct": pnl_pct}

def todays_orders():
    with store._conn() as c:
        rows = c.execute(
            "SELECT ts,symbol,side,qty,status FROM orders WHERE ts > date('now') ORDER BY ts"
        ).fetchall()
    return [{"ts": r[0], "symbol": r[1], "side": r[2], "qty": r[3], "status": r[4]} for r in rows]

def todays_vetoes():
    with store._conn() as c:
        rows = c.execute(
            "SELECT ts,symbol,strategy,reason FROM vetoes WHERE ts > date('now') ORDER BY ts"
        ).fetchall()
    return [{"ts": r[0], "symbol": r[1], "strategy": r[2], "reason": r[3]} for r in rows]

def morning_summary():
    pnl = positions_and_pnl()
    lines = [
        f"=== MORNING BRIEF — {datetime.now(timezone.utc):%Y-%m-%d} ===",
        f"Bot state: {bot_state.get_state()}",
        f"Equity: ${pnl['equity']:,.0f}",
        f"Open positions: {pnl['positions'] or 'none'}",
        "",
        "Market conditions:",
    ] + [f"  {l}" for l in market_conditions()]
    return "\n".join(lines)

def nightly_summary():
    pnl = positions_and_pnl()
    orders = todays_orders()
    vetoes = todays_vetoes()
    lines = [
        f"=== NIGHTLY REPORT — {datetime.now(timezone.utc):%Y-%m-%d} ===",
        f"Bot state: {bot_state.get_state()}",
        f"Equity: ${pnl['equity']:,.0f}  |  Today's P&L: {pnl['todays_pnl_pct']:+.2%}",
        f"Open positions: {pnl['positions'] or 'none'}",
        "",
        f"Orders today ({len(orders)}):",
    ] + [f"  {o['ts'][11:16]} {o['symbol']} {o['side']} {o['qty']} [{o['status']}]" for o in orders] + [
        "",
        f"Vetoes today ({len(vetoes)}):",
    ] + [f"  {v['ts'][11:16]} {v['symbol']} [{v['strategy']}] {v['reason']}" for v in vetoes]
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "nightly":
        print(nightly_summary())
    else:
        print(morning_summary())
