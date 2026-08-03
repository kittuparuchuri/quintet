import numpy as np
import pandas as pd
from strategies import meanrev

vals = np.asarray([100.0 + (i % 3) * 0.1 for i in range(30)] + [96.0])
df = pd.DataFrame({
    "open": vals, "high": vals * 1.001, "low": vals * 0.999,
    "close": vals, "volume": np.full(len(vals), 1000.0),
}, index=pd.date_range("2026-01-01", periods=len(vals), freq="15min"))

print("any NaN in close?", df["close"].isna().any())
z = meanrev.zscore(df)
print("z-score:", z)
print("signal:", meanrev.evaluate(df, "SPY", in_position=False))