"""Step 7 rehearsal: one forced signal through the full chain, then the kill switch."""
from models import Signal
from datetime import datetime, timezone
import risk_engine, executor, bot_state

bot_state.set_state(bot_state.RUNNING)
positions = executor.reconcile()

# Act 1: a forced GLD buy through the risk engine
sig = Signal("GLD", "buy", "trend", datetime.now(timezone.utc), note="rehearsal")
intent = risk_engine.evaluate(sig, equity=100_000, todays_pnl_pct=0.0,
                              open_positions={}, tf_label="4Hour")
print("Risk engine says:", intent)
if intent:
    executor.submit(intent)

# Act 2: a signal that MUST be vetoed (bot halted)
bot_state.set_state(bot_state.HALTED)
sig2 = Signal("GLD", "buy", "trend", datetime.now(timezone.utc), note="should veto")
risk_engine.evaluate(sig2, 100_000, 0.0, {}, "4Hour")
bot_state.set_state(bot_state.RUNNING)
