
## Incident 2026-08-04: duplicate queued order
Restart between first autonomous order (21:55) and open-order patch created a 2nd queued GLD buy.
Caught by routine order check before any fill. Cancelled the newer order. Patch (in_pos includes
open orders) verified working on 22:00 restart. Zero cost. Lesson: reconcile must consider ORDERS,
not just positions.

## Step 9 test log 2026-08-05
E(a) restart-on-crash: PASSED on evidence of 8/5 missing-tables crash-loop (Docker auto-restarted
repeatedly: "exited with code 1 (restarting)"). Note: manual docker kill/stop intentionally does
NOT trigger restart: always - policy guards crashes, not operator actions.
E(b) dead-bot alert: bot killed ~23:05 UTC, healthchecks flipped red, alert email received at
kittuparuchuri@gmail.com. Resurrected via compose up; green restored.
E(c) 24h soak: begins from this restart.
