# H4 prospective evaluation protocol

**Status: DRAFT FOR REVIEW — NOT FROZEN. No evaluation has started.**

The statistics are implemented in `src/volrisk/monitoring/evaluation.py` and unit-tested on synthetic data only. H4 is evaluated as **market-index risk monitoring**. Nothing here measures the risk or performance of WSC's stock portfolio, and nothing is measured by P&L.

## 1. Sample

- **Start:** the first scheduled exchange session strictly after both the protocol freeze and its timestamped registration.
- **Length:** exactly 252 scheduled sessions per asset (NIFTY50_TRI, SPY, VT). There is no early stopping and no extension.
- **Minimum:** at least 200 eligible sessions are required for a primary conclusion; otherwise that asset's result is **INCONCLUSIVE**. An eligible session has a valid production alert-model forecast and an observed close-to-close return.
- **Not used as evidence:** 2025–2026, because earlier research exposed some observations, and 2024, which is a pipeline dry run only.

## 2. What is evaluated

| question | evaluated quantity | target |
| --- | --- | --- |
| Do alerts catch large moves? | ELEVATED and CRITICAL alert levels | Event \|r\| above the development 75th and 90th percentile |
| Is volatility calibrated? | Forecast variance *h* | Squared close-to-close log return |
| Are large-move probabilities calibrated? | P(\|r\| > c) | Event indicator |
| Is the system reliable? | Report status and timeliness | Scheduled sessions |

Event thresholds are frozen from development data: NIFTY50_TRI 0.98% and 1.57%, SPY 0.87% and 1.44%, VT 0.89% and 1.47%. ELEVATED alerts are scored against ELEVATED events and CRITICAL alerts against CRITICAL events. An alert counts as positive when the level is at or above the one being scored. The direction of the move is ignored.

## 3. Metrics

| area | metric | function |
| --- | --- | --- |
| Alerts | **Precision, recall, false-positive rate, missed-event rate**, with Wilson intervals; lift over base rate; false-discovery rate | `detection` |
| Volatility calibration | **Realized-to-forecast variance ratio; Mincer–Zarnowitz intercept and slope; QLIKE** | `calibration_ratio`, `mincer_zarnowitz`, `qlike` |
| Probability calibration | **Brier score; Brier skill against the frozen development base rate; reliability bins** | `brier_skill`, `reliability_bins` |
| Alert burden | Sessions per level; entries and mean episode length per level | `burden` |
| Operations | Share of scheduled sessions with a timely, valid report; counts of stale, unavailable and failed sessions; publication lag; data-quality incidents | `operational` |

Paired contrasts use the stationary bootstrap: 10,000 draws, mean block length 10, seed 20261103. QLIKE contrasts use the existing gap-aware HAC test.

## 4. Benchmarks

1. **rolling_20 percentile rule.** The same percentile thresholds, frozen from the same development window, applied to 20-session trailing volatility.
2. **Unconditional base-rate rule.** A constant development base rate for probabilities, and alerts at the development alert rate independent of conditions.

All 11 other production models are scored the same way as descriptive context. Provisional models are scored in a **separate, labelled descriptive table only**. Neither set can change the alert model or any classification during the evaluation.

## 5. Primary contrasts and multiplicity

For each asset, five contrasts form one Holm family of 15 tests:

| id | contrast | supports H4 if |
| --- | --- | --- |
| C1 | CRITICAL-alert precision against the CRITICAL event base rate (lift) | Lift > 1, adjusted p < 0.05 |
| C2 | ELEVATED-alert precision against the ELEVATED event base rate (lift) | Lift > 1, adjusted p < 0.05 |
| C3 | CRITICAL large-move probability: Brier skill against the base rate | Skill > 0, adjusted p < 0.05 |
| C4 | Alert-model QLIKE minus rolling_20 QLIKE | Negative, adjusted p < 0.05 |
| C5 | CRITICAL recall, alert model minus rolling_20 rule, at their own frozen thresholds | Positive, adjusted p < 0.05 |

C1–C3 test whether the system is useful. C4–C5 test whether the alert model adds value over a trivial trailing rule. **If C1–C3 pass but C4–C5 fail, the alerts are informative but a simpler rule would do,** and the result must be reported that way.

## 6. Acceptance criteria (proposed, review decision R8)

H4 is **supported** for an asset only if all of the following hold:

1. **Detection.** C1, C2 and C3 pass.
2. **Volatility calibration.** Aggregate realized-to-forecast ratio within 0.80–1.25. Mincer–Zarnowitz slope interval includes 1.
3. **Probability calibration.** Observed frequencies fall within their Wilson intervals in every reliability bin with at least 20 sessions.
4. **Acceptable false positives.** The CRITICAL false-positive rate, missed-event rate and episodes per year are within the budget the CIOs pre-declare at freeze. The draft budget is at most 6 CRITICAL episodes a year, a CRITICAL precision of at least twice the base rate, and a missed-event rate reported with its interval.
5. **Operational reliability.** At least 98% of scheduled sessions have a timely, valid alert-model report.

**Outcome labels:**
- **SUPPORTED:** all five criteria pass.
- **PARTIALLY SUPPORTED:** detection passes but a calibration, false-positive or operational criterion fails, each reported.
- **NOT SUPPORTED:** detection fails with at least 200 eligible sessions.
- **INCONCLUSIVE:** fewer than 200 eligible sessions.

**Power note.** With a 10% CRITICAL base rate, 252 sessions yield about 25 events. A recall estimate then has a 95% interval roughly ±0.2 wide. Single-session absolute returns are noisy, so even a well-calibrated forecast has modest recall. A NOT SUPPORTED result must be read alongside the intervals, and a SUPPORTED result is one year of evidence on three related markets.

## 7. Conduct rules during evaluation

- Interim monitoring is limited to data integrity and operational failures. There is no interim model ranking and no change to specification, thresholds, probability method or rules.
- Missing or stale sessions remain in the sample as operational failures. They are excluded only from matched-forecast scoring.
- No interpolation, filled data or model substitution.
- P&L, position changes, acknowledgements and analyst decisions are never evaluation inputs.
- Provisional models cannot be promoted during the evaluation. Promotion requires provenance sign-off and a new protocol version registered before a **new** evaluation period.
- Any amendment requires a new, timestamped protocol version **before** evaluation begins. After it begins, the only permitted change is to stop the study on governance grounds, with results reported as incomplete.

## 8. What a result can and cannot claim

| can claim, if supported | cannot claim |
| --- | --- |
| The alert model identified sessions with unusually large NIFTY, SPY or VT moves more often than chance, with calibrated volatility and probabilities | That alerts predict crashes or negative returns |
| The system was operationally reliable at the stated rate | That alerts reduce fund losses, or anything about P&L |
| Whether the model beat a simple trailing-volatility rule | Anything about the risk of WSC's combined stock portfolio |

## 9. Reserved future experiment — five-session horizon

A five-session risk forecast needs its own models estimated at that horizon, a horizon-consistent target (the five-session sum of squared returns), its own thresholds and events, overlap-aware inference and a separate registration. The ledger schema already carries a `horizon_sessions` field so the architecture supports it. No five-session claim may draw on the one-session evaluation.
