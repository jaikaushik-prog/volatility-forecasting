# H4 registration — volatility-based risk monitoring

**Status: DRAFT FOR REVIEW — NOT FROZEN.** No prospective data collection or evaluation is authorized. Version 0.2.0-draft, drafted 2026-11-03.

Companion documents:
- `reports/h4_alert_specification.md` — alert levels, computation, report content and what each audience does.
- `reports/h4_prospective_evaluation_protocol.md` — how the system will be judged.
- `config/h4_monitoring.toml` — the machine-readable draft. It validates and refuses prospective start while in draft.
- `reports/h4_draft/` — development-only draft thresholds, event thresholds, alert-burden statistics and the model inventory.

This protocol is separate from the frozen forecasting protocol (`reports/frozen_forecasting_protocol.md`) and from every Stage 2–6 configuration. It amends none of them.

## 1. Objective and scope

Establish whether forecasts can detect elevated **next-session market risk** with useful accuracy, calibration, an acceptable false-positive rate and operational reliability. The use is advisory risk monitoring for NEXUS.

**H4 null hypothesis.** Alerts from the designated alert model detect large next-session market moves no better than the base rate or a simple trailing-volatility rule. Its volatility forecasts and large-move probabilities are not calibrated.

**Scope limits:**
- **Market risk, not portfolio risk.** Every estimate concerns a market index: NIFTY50_TRI primarily, with SPY and VT. It is **not** an estimate of the risk of WSC's combined stock portfolio. Portfolio risk depends on holdings, weights, concentration, sector and factor exposures, and liquidity, none of which H4 models.
- **Not directional.** High forecast volatility is not a bearish signal. It does not predict a crash or a negative return. A large-move probability counts moves in either direction.
- **Advisory only.** There is no automatic selling, position reduction, capital reallocation or trading. Discretionary trades remain with the analyst and CIO under existing approval rules.
- **Not measured by P&L.** H4 success is never measured by trading P&L, and no claim is made that alerts reduce fund losses.
- **One-session horizon.** The weekly summary is descriptive. A five-session horizon is reserved for a separate experiment with horizon-consistent models, targets and evaluation.

## 2. Risk definitions

| measure | definition | target | where defined |
| --- | --- | --- | --- |
| **Primary** | Next-session conditional market-return volatility, σ = √(252·*h*) where *h* is the one-session-ahead variance forecast | Next-session squared close-to-close log return, the **common target for every model** | Config `[risk]` |
| **Secondary** | Probability of an unusually large next-session absolute return: P(\|r\| > c) = P(\|z\| > c/√*h*) | Event indicator \|r\| > c, with *c* at the development 75th (ELEVATED) and 90th (CRITICAL) percentiles of \|r\| | Config `[events]`; method below |
| **Model reliability** | Calibration, historical forecast errors, forecast availability, data-quality issues and model disagreement | Reported in a separate block, never mixed into the risk level | Config `[alerts].reliability_fields` |

**Probability methods** must be fixed before prospective testing. The draft defines two:
1. **Normal:** 2·(1 − Φ(c/√*h*)).
2. **Filtered historical:** the share of development standardized returns *z* = *r*/√*h* with |*z*| > c/√*h*. This is the draft primary method (review decision R6).

Both use only quantities frozen from the development window.

**Draft event thresholds** use target dates 2012–2021. ELEVATED is the 75th percentile of absolute return and CRITICAL the 90th. Base rates are by construction about 25% and 10% in development.

| asset | ELEVATED event | CRITICAL event |
| --- | --- | --- |
| NIFTY50_TRI | absolute return ≥ 0.98% | ≥ 1.57% |
| SPY | ≥ 0.87% | ≥ 1.44% |
| VT | ≥ 0.89% | ≥ 1.47% |

## 3. Audience and governance

| role | access | obligation |
| --- | --- | --- |
| CIOs and co-CIOs | All reports and alerts | Review every CRITICAL alert: portfolio exposure, drivers, and whether to recommend a change under existing approval rules |
| Analysts (long-only equity positions or strategies) | Reports and alerts for their scope | Acknowledge every ELEVATED alert; review exposure and concentration; document whether action is warranted |
| Investment Committee | Read-only risk reports | Oversight; no acknowledgement duty |
| Research (system operator) | All ledgers | Publish reports, maintain data integrity, never alter logged records |

Acknowledgement and review deadlines in the config are placeholders pending agreement: ELEVATED before the next session opens, CRITICAL the same session day.

## 4. Models: production and provisional

All 32 previously researched models appear once, as you instructed. They are split by whether their data and provenance requirements are met. `reports/h4_draft/model_inventory.csv` lists each one with its grade, role and status. All forecast the **same close-to-close target**.

### Production-grade (12 models)

These use only audited daily close-to-close returns. They are eligible to influence production classifications.

| group | models |
| --- | --- |
| Sprint 2 | expanding, rolling_20, rolling_60, ewma_094, garch_normal, garch_t, egarch_normal, egarch_t, **gjr_normal (proposed alert model)**, gjr_t |
| Stage 3 | markov_switching_2, xgboost_v1 |

**Exactly one production model per asset drives the alert level.** The other 11 are logged every session. Their agreement and dispersion are shown in the reliability block as model disagreement; they do not change the level. Using many models as simultaneous alert sources would leave alert meaning and false-positive rates undefined.

**Proposed alert model: `gjr_normal`.** On development data only (target dates 2012–2021, never 2022–2024), it had the lowest QLIKE among normal-innovation models on NIFTY. On SPY and VT it was within 0.01 QLIKE of the best model. Its calibration ratios were 0.98, 0.95 and 0.91. Sprint 2 recommended dropping Student-t variants. **Known weakness:** the GJR asymmetry parameter was at zero in 50–70% of Sprint 2 refits. The simpler alternative is `ewma_094`: calibration 1.00 on all three assets, no estimation failures, a slightly worse QLIKE (review decision R1).

### Provisional (20 models)

These depend on unverified intraday RV, India VIX or vendor spot inputs. They are **separately flagged** and never contribute to production-grade classifications. The config enforces this, and validation rejects any setting that would let them in:
- They cannot be the alert model.
- They are excluded from the production consensus and dispersion.
- They cannot set thresholds.

They appear only in a labelled provisional panel.

| status | models |
| --- | --- |
| Existing close-to-close forecasts (Stage 4, NIFTY spot; development Oct 2022–Dec 2023) | previous, mean5, mean22, rv_ewma, har, har_overnight, har_vix, har_vix_overnight, log_har, spot_ewma, spot_garch, spot_egarch, spot_gjr |
| Requires horizon-1 close-to-close re-specification before freeze | log_har_vix_c2c_h1, log_har_vix_change_c2c_h1, ridge_log_har_vix_c2c_h1 (Stage 4B, native target intraday RV); har_daily_h1, log_har_daily_h1, log_har_vix_daily_h1 (Stage 5, native horizon 2) |
| Archived comparator | legacy_levels_har_vix. The frozen protocol excludes it as a prospective candidate, so it is logged only |

A provisional model can be promoted only by a new protocol version, registered **before** evaluation begins. That requires provenance sign-off under the frozen forecasting protocol's gates (vendor and export chain, timezone, bar labels, VIX availability) and a credible development history on the common target. Today the Stage 4 close-to-close forecasts cover 39–292 development sessions per model. That is too few for stable 90th-percentile thresholds.

## 5. Data, freshness and provenance

- A report is produced after each session only when the alert model's inputs include the just-closed session. Otherwise the level is DATA_STALE or DATA_UNAVAILABLE, never NORMAL, and no forecast is shown.
- Each report records the last return date, the retrieval timestamp, data-quality issues and the provenance status of every input.
- **Prerequisite not yet built:** a prospective daily acquisition path for NIFTY TRI, SPY and VT with immutable retrieval timestamps. For provisional models it must also capture intraday bars and VIX with availability times.
- No interpolation, no filled prices, no model substitution. Failures are logged as MODEL_FAILURE.

## 6. Ledgers

Five append-only, separately stored ledgers. Every record carries a sequence number, a timestamp and the hash of the previous record.

| ledger | written | contents | may it reference outcomes? |
| --- | --- | --- | --- |
| Forecast | After the close, before the next session opens | Every model's forecast, grade, fit status and inputs hash | No |
| Alert | With the forecast | Full alert record: risk block, reliability block and limitations | No |
| Acknowledgement | When a person acknowledges | Who, when, which alert, review notes | No |
| Decision | When a discretionary decision is recorded | Decision or recommendation and rationale, linked to an alert | No |
| Outcome | After the target session closes | Realized squared return, event flags, forecast error | Yes; never edits other ledgers |

Acknowledgements and decisions are logged for governance and audit. They are **not** evaluation inputs. Fund decisions do not change index-level volatility, so analyst responses cannot contaminate the evaluation target.

## 7. Draft alert thresholds (illustrative, for review)

The 75th (ELEVATED) and 90th (CRITICAL) percentiles of the alert model's walk-forward out-of-sample forecast volatility over 2012–2021. They were computed without reading any row dated after the window. They were not tuned and not compared with 2024 or later outcomes.

| asset | alert model | ELEVATED at | CRITICAL at | development forecasts |
| --- | --- | --- | --- | --- |
| NIFTY50_TRI | gjr_normal | 15.9% | 20.0% | 1,978 (2014–2021) |
| SPY | gjr_normal | 15.7% | 23.0% | 2,016 |
| VT | gjr_normal | 15.5% | 22.5% | 2,016 |

Values are annualized forecast volatility. Thresholds for all production and provisional models are in `reports/h4_draft/draft_alert_thresholds.csv`, with provisional rows labelled.

**Implied alert burden** on development data, with the 3-session de-escalation rule:

| asset | sessions NORMAL / ELEVATED / CRITICAL | ELEVATED entries per year | CRITICAL entries per year | mean CRITICAL episode |
| --- | --- | --- | --- | --- |
| NIFTY50_TRI | 70% / 18% / 12% | 7.0 | 2.3 | 13 sessions |
| SPY | 69% / 18% / 14% | 8.4 | 3.9 | 9 sessions |
| VT | 69% / 16% / 14% | 8.6 | 4.4 | 8 sessions |

Hysteresis holds levels longer, so occupancy exceeds the nominal 25% and 10%. The CIOs should check that roughly 2–4 critical episodes a year, each about two weeks long, is a workable review load. Any change must be made before freeze (review decision R2).

## 8. Freeze checklist

Every item must be complete, and the config set to `status = "FROZEN"`, before registration.

1. Review decisions R1–R8 resolved and recorded in the config.
2. Each provisional re-specification either implemented, unit-tested and development-checked, or removed from the inventory. Their grade stays PROVISIONAL either way.
3. Prospective acquisition, the five-ledger pipeline and report rendering implemented and tested on development data. A 2024 dry run is a pipeline check only and produces no evidence.
4. Final alert thresholds, event thresholds and the development standardized-return sample for the filtered-historical method recomputed from the agreed window, stored and hashed.
5. Config, code, thresholds and these documents hashed into a timestamped registration file. Evaluation starts at the first scheduled session strictly after registration.

## 9. Open review decisions

| id | decision | draft default |
| --- | --- | --- |
| R1 | Alert model | gjr_normal; alternative ewma_094 |
| R2 | Alert percentiles and acceptable CRITICAL burden | 75th / 90th (illustrative); about 2–4 critical episodes a year |
| R3 | De-escalation rule | Step down one level after 3 consecutive sessions below the lower threshold |
| R4 | Whether to complete the six provisional re-specifications before freeze | Complete them; they stay provisional and descriptive |
| R5 | Assets that issue alerts | NIFTY50_TRI primary; SPY and VT as secondary alert assets |
| R6 | Primary large-move probability method | Filtered historical; normal reported alongside |
| R7 | Acknowledgement and review deadlines | ELEVATED before next open; CRITICAL same day |
| R8 | Acceptance criteria and false-positive budget | See the evaluation protocol, §6 |
