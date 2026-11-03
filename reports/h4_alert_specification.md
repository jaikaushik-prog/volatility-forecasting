# H4 alert specification

**Status: DRAFT FOR REVIEW — NOT FROZEN.**

This specification is advisory and non-directional. It defines no trading, selling, position-reduction or reallocation action. It measures **market-index risk**, not the risk of WSC's combined stock portfolio.

The rules are implemented and unit-tested in `src/volrisk/monitoring/alerts.py`, with tests in `tests/test_h4_monitoring.py`.

## 1. Levels

| level | meaning | who acts | required action |
| --- | --- | --- | --- |
| NORMAL | Forecast volatility below the ELEVATED threshold | None | Daily risk summary only |
| ELEVATED | Forecast volatility at or above the development 75th percentile | Analysts | Review exposure and concentration, acknowledge, and document whether action is warranted |
| CRITICAL | Forecast volatility at or above the development 90th percentile | CIOs and co-CIOs | Review portfolio exposure, investigate risk drivers, and decide whether to recommend a change under existing approval rules |

The 75th and 90th percentiles are illustrative and subject to review before freeze. They are fixed from development data and never optimized against 2024 or any result seen during research.

Operational states are reported as themselves. They are **never** reported as NORMAL.

| state | condition | displayed |
| --- | --- | --- |
| DATA_UNAVAILABLE | Required inputs for the just-closed session missing | No forecast; the last valid level and its date shown as context |
| DATA_STALE | Latest inputs do not include the just-closed session | No forecast; data age shown |
| MODEL_FAILURE | Alert model produced no valid forecast | No forecast; no substitute model is used |

## 2. Computation, each session after the close

1. Confirm the inputs include the just-closed session. Otherwise emit the operational state.
2. **Primary measure.** Compute the production alert model's one-session variance forecast *h* and the volatility σ = √(252·*h*).
3. Compare σ with that asset's frozen thresholds to get the raw level.
4. Apply hysteresis:
   - **Escalation is immediate.**
   - **De-escalation** steps down one level only after a pre-set number of consecutive sessions (draft: 3) below the current level's lower threshold.
   - Any session back at or above the threshold resets the count.
   - Operational states do not reset the count.
5. **Secondary measure.** Compute P(|r| > c) for the ELEVATED and CRITICAL event thresholds, with the registered method: filtered historical, and normal alongside.
6. **Reliability.** Assemble the reliability block, described below, separately from the level.
7. Record every production and provisional model's forecast. Write the forecast and alert ledgers before the next session opens.

The level depends only on the production alert model and the frozen thresholds. Nothing in the reliability block or the provisional panel can change it.

## 3. Report structure

Every report, including NORMAL and operational states, has three separate parts. Record validation rejects a report missing any required field, any required limitation, or the provisional label.

### A. Risk

| field | contents |
| --- | --- |
| Level | Current level and previous level |
| Primary measure | Annualized forecast volatility, daily variance, percentile within the development forecast distribution |
| Thresholds | ELEVATED and CRITICAL values used |
| Secondary measure | P(\|r\| > ELEVATED event), P(\|r\| > CRITICAL event), method name |
| Horizon | Target session date; horizon = 1 session |
| Reason | The rule triggered, in plain language. States when a level is held by the de-escalation rule |
| Model | Alert model name and version |

### B. Model reliability (shown separately from the level)

| field | contents |
| --- | --- |
| Calibration | "Not yet evaluated" until the prospective period produces results; then rolling realized-to-forecast ratio and probability calibration |
| Historical forecast errors | Recent forecast errors and QLIKE of the alert model |
| Availability | Status of today's forecast; prospective availability rate to date |
| Data freshness | Last return date, retrieval timestamp, freshness status |
| Data quality | Open data-quality issues affecting any input |
| Provenance | Audit status of each input (e.g. daily TRI audited; intraday RV unverified) |
| Model disagreement | Production models available, production models at CRITICAL, and max/min dispersion of production forecasts. **Production models only** |
| Provisional panel | Each provisional model's forecast and would-be level, every entry labelled PROVISIONAL |

### C. Limitations, shown on every report

- This is an estimate of market-index risk, not the risk of WSC's combined stock portfolio.
- High forecast volatility is not a bearish signal and does not predict a crash or a negative return.
- Advisory only: no position is changed by this system.
- One-session horizon. The weekly summary is descriptive and not a five-session forecast.
- Thresholds come from a fixed historical development window and may not reflect the current regime.
- Shocks that arrive within the forecast session cannot be anticipated by a close-to-close forecast.
- Provisional models use unverified intraday or VIX inputs and do not affect the alert level.

**Language rule.** Report text is non-directional and never recommends a trade. Validation rejects reasons containing words such as "sell", "buy", "reduce position", "rebalance", "crash", "bearish" or "will fall". Decisions belong to people and are logged in the decision ledger.

## 4. Example report

The values below are illustrative, not real forecasts. The probabilities apply the draft NIFTY development quantities to an illustrative variance.

```text
NIFTY50_TRI · market-index risk · report 2027-01-04 after close · for session 2027-01-05 (1 session)

RISK
  Level: CRITICAL (previous: ELEVATED)
  Forecast volatility 22.2% annualized (92nd development percentile)
  Thresholds: ELEVATED 15.9% · CRITICAL 20.0%
  P(|move| >= 0.98%) = 44% · P(|move| >= 1.57%) = 24%   (filtered historical; normal: 49% / 26%)
  Development base rates for comparison: 25% / 10%
  Reason: at or above the development 90th percentile (20.0% annualized).
  Model: gjr_normal v1.0.0

MODEL RELIABILITY
  Calibration: not yet evaluated · Recent errors: within normal range
  Availability: current · Data: last return 2027-01-04, retrieved 16:10 IST · Quality issues: none
  Provenance: daily TRI audited
  Disagreement: 9 of 12 production models at CRITICAL · dispersion 38%
  Provisional (unverified inputs, not used for the level): log_har 24.9% (would be CRITICAL), har 30.0% (CRITICAL), ...

LIMITATIONS
  Market-index risk, not WSC portfolio risk · not a bearish or crash signal · advisory only · ...
```

## 5. Acknowledgement and decision logging

- Each ELEVATED or CRITICAL alert opens an item in the acknowledgement ledger. It records the reviewer, the time and the review notes.
- A recommendation or decision, including an explicit "no action warranted", goes in the decision ledger and links to the alert. It does not change the alert.
- Missed deadlines are logged as governance exceptions. They are not model-evaluation failures.
- Outcomes are written only to the outcome ledger, after the target session closes.

## 6. Weekly summary (descriptive only)

Issued after the last session of each week. It contains:
- **Recent forecasts:** daily forecast volatility for the alert model, with the production-model range. Provisional models are shown separately and labelled.
- **Risk regime:** level changes during the week and session counts per level.
- **Errors and calibration:** realized-to-forecast ratio, QLIKE, and large-move probability against observed frequency, week to date and rolling.
- **Alerts:** issued, acknowledged and outstanding.
- **Model reliability:** availability, stale and unavailable sessions, model failures and data-quality issues.
- **Realized weekly risk:** the five-session sum of squared returns, labelled descriptive.

The weekly summary states on its face that it is not a validated five-session forecast. Rolling statistics in weekly summaries are operational information only. They never trigger a change to model, thresholds or rules during the evaluation.
