from dotenv import load_dotenv; load_dotenv()
import os
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from datetime import datetime, timedelta

key = os.getenv("ALPACA_API_KEY")
sec = os.getenv("ALPACA_SECRET_KEY")

trading = TradingClient(key, sec, paper=True)
acct = trading.get_account()
print("Account status:", acct.status, "| Fake equity:", acct.equity)

data = StockHistoricalDataClient(key, sec)
req = StockBarsRequest(
    symbol_or_symbols="SPY",
    timeframe=TimeFrame(15, TimeFrameUnit.Minute),
    start=datetime.utcnow() - timedelta(days=5),
)
bars = data.get_stock_bars(req).df
print(bars.tail())