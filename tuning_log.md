
## Incident 2026-08-04: duplicate queued order
Restart between first autonomous order (21:55) and open-order patch created a 2nd queued GLD buy.
Caught by routine order check before any fill. Cancelled the newer order. Patch (in_pos includes
open orders) verified working on 22:00 restart. Zero cost. Lesson: reconcile must consider ORDERS,
not just positions.
