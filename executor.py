"""Turns approved OrderIntents into real Alpaca bracket orders. Duplicate-proof."""
from dotenv import load_dotenv; load_dotenv()
import os
from datetime import datetime, timezone
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, StopOrderRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
import store

client = TradingClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"), paper=True)

def _fingerprint(intent):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    return f"{intent.strategy}-{intent.symbol.replace('/','')}-{stamp}"

def _log_order(intent, order_id, status):
    with store._conn() as c:
        c.execute("INSERT INTO orders(ts, symbol, side, qty, order_id, status) VALUES (?,?,?,?,?,?)",
                  (datetime.now(timezone.utc).isoformat(), intent.symbol, intent.side,
                   intent.qty, str(order_id), str(status)))

def submit(intent):
    is_crypto = "/" in intent.symbol
    req = MarketOrderRequest(
        symbol=intent.symbol.replace("/", ""),
        qty=intent.qty,
        side=OrderSide.BUY if intent.side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.GTC if is_crypto else TimeInForce.DAY,
        order_class=None if is_crypto else OrderClass.BRACKET,
        stop_loss=None if is_crypto else StopLossRequest(stop_price=intent.stop_price),
        client_order_id=_fingerprint(intent),
    )
    order = client.submit_order(req)
    _log_order(intent, order.id, order.status)
    print(f"ORDER sent: {intent.side} {intent.qty} {intent.symbol} "
          f"stop={intent.stop_price} id={order.client_order_id}")
    if is_crypto:
        stop = client.submit_order(StopOrderRequest(
            symbol=intent.symbol.replace("/", ""), qty=intent.qty,
            side=OrderSide.SELL, time_in_force=TimeInForce.GTC,
            stop_price=intent.stop_price,
            client_order_id=_fingerprint(intent) + "-stop"))
        _log_order(intent, stop.id, f"stop:{stop.status}")
        print(f"  crypto stop placed at {intent.stop_price} - verify in dashboard")
    return order

def reconcile():
    positions = {p.symbol: float(p.qty) for p in client.get_all_positions()}
    print("Reconcile - broker says we hold:", positions or "nothing")
    return positions
