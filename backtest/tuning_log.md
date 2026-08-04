# Quintet Tuning Log

## Baseline — 2026-08-04 — params: ENTRY_Z=-2.0, VOL_MULT=1.5, EMA 20/50, fixed 1% stop
SPY  meanrev  in: 855 trades, -21.8%, DD -22.4%, win 61.5% | OUT: 588, -14.1%, DD -17.8%, win 61.6%
QQQ  meanrev  in: 921 trades, -25.6%, DD -25.5%, win 62.4% | OUT: 616, -10.1%, DD -14.7%, win 64.3%
BTC  breakout in: 262 trades, -79.1%, DD -79.5%, win 23.3% | OUT: 145, -73.1%, DD -72.8%, win 16.6%
GLD  trend    in:  25 trades, +34.1%, DD  -4.7%, win 40.0% | OUT:  20, +25.0%, DD  -7.6%, win 30.0%
USO  trend    in:  34 trades, -24.8%, DD -24.0%, win  5.9% | OUT:  22, -14.6%, DD -16.2%, win  4.5%

## Kill/keep criteria (set before results)
- PASS: OUT total > 0 after costs, avg >= 2x round-trip cost, maxDD > -20%, enough trades
- Iron rule: tune ONLY in-sample; OUT runs once per candidate.

## Experiment 1 — 2026-08-04 — ATR stop 2.0x (replaces fixed 1% stop). In-sample only.
Predictions (written before running):
- BTC win% jumps from 23% to well above 40%
- USO win% jumps from 6% dramatically
- meanrev avg improves toward/above zero (fewer noise stop-outs)
- GLD stays roughly as good (+34% area)
Results:
[PASTE FIVE IN-SAMPLE LINES HERE]

## Experiment 2 — 2026-08-04 — meanrev ENTRY_Z -2.5 (ATR stop kept). In-sample, SPY/QQQ only.
Predictions (before running):
- trade count drops sharply (roughly to 1/3 of Exp 1's ~1,200)
- avg per trade improves meaningfully vs Exp 1's -0.03%
- PASS bar: avg > +0.01% (2x round-trip costs) AND positive total. Below bar = meanrev retires.
Results:
Verdict: FALSIFIED. Trade count barely dropped (1168->850), avg worsened (-0.030 -> -0.035),
win% fell below 50%. Deeper entries found no additional edge.
DECISION: meanrev RETIRED for SPY and QQQ — edge thinner than costs at 15-min frequency,
confirmed across two stop regimes and two entry thresholds.

## Experiment 3 — 2026-08-04 — BTC breakout LOOKBACK 55 (was 20). ATR stop kept. In-sample only.
Predictions (before running):
- far fewer trades (maybe 60-100 vs 254)
- win% rises above 35%; winners much larger (real trends, not noise)
- PASS bar: positive total AND avg > +0.014% (2x BTC round-trip cost of 0.7%... i.e. avg > +1.4%).
  Below bar = BTC breakout retires; no further BTC experiments.
Results:
Verdict: FALSIFIED. Win% flat (25%), avg -0.59% vs required +1.4%. Two lookbacks (20, 55)
produced near-identical losses.
DECISION: BTC breakout RETIRED — no detectable edge at 1-hour frequency against 0.7%
round-trip costs. No further BTC experiments (anti-overfitting rule).

## STEP 6 — FINAL VERDICTS (2026-08-04)
| Strategy/Market | Verdict | Evidence |
|---|---|---|
| GLD trend 4h    | PROVISIONAL PASS | OUT +13.6%, maxDD -13.9%, 20 trades, avg 7x costs; consistent in ALL configs. Paper campaign = real trial. |
| USO trend 4h    | UNSTABLE — observation-only in paper | in-sample -24% vs OUT +29% on 21 trades, 19% win: 1-2 outlier trades, no consistent edge. |
| SPY meanrev 15m | RETIRED | Edge < costs across 2 stop regimes + 2 entry depths (exp 1-2). |
| QQQ meanrev 15m | RETIRED | Same. |
| BTC breakout 1h | RETIRED | ~-0.6%/trade vs +1.4% required, across lookback 20 and 55 (exp 3). |

Memorized numbers: GLD maxDD = -13.9% (OUT). If live GLD ever exceeds ~-15%, investigate before trusting further.
Params going forward: trend EMA 20/50, ATR stop 2.0x14, 4h candles.