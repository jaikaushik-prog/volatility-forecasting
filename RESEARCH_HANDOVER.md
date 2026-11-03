# Research handover — start here

**Project:** NEXUS Volatility Forecasting and Risk-Managed Position Sizing. **Point of contact:** Jai Kaushik. **Handover date:** 2026-11-04.

This document is for researchers continuing the project. It covers:
- what the original brief asked for, and what has been established against each item;
- the rules every future stage must follow;
- how to get running;
- the prioritized list of open work.

The original brief is in [`docs/project_brief.md`](docs/project_brief.md). The long [`README.md`](README.md) is the stage-by-stage technical reference, with every CLI and its conventions.

---

## 1. Where the project stands, in one paragraph

**Forecasting** (Stages 1–4B) is in good shape. Data pipelines are audited. Twelve daily models and twenty intraday or VIX-based models have been evaluated walk-forward on NIFTY 50 TRI, SPY and VT. Asymmetric GARCH models beat simple historical baselines, EWMA is the best-calibrated simple model, and none of the advanced challengers is statistically established as better.

**Position sizing** (Stage 5) produced a **negative result**. All five 12%-target inverse-volatility overlays underperformed buy-and-hold on net Sharpe in 2024.

**Diagnosis** (Stage 6) showed why. Exposure was cut after the June 2024 election shock and stayed low through the rebound; costs were secondary. One episode accounts for almost the entire shortfall.

**Current direction:** the project has pivoted to **H4, advisory volatility-based risk monitoring**. A draft protocol exists but is **not frozen**, and no prospective evaluation has started. Overlay ideas (exceptional-risk limits, momentum plus volatility) are deferred until broader verified data exist.

---

## 2. Original brief versus evidence

### Hypothesis

| brief claim | status | evidence |
| --- | --- | --- |
| Lagged EWMA/GARCH forecasts are better calibrated than a constant-volatility baseline | **Largely supported in development and validation (2012–2024)**. The final holdout is not yet evaluated | The expanding-window (constant) baseline ranks last on QLIKE for all three markets. Its calibration ratios are 1.05, 1.43 and 1.28, against EWMA's 1.00. Asymmetric GARCH beats GARCH(1,1) by 0.03–0.05 QLIKE. Only some contrasts survive Holm adjustment. `reports/research_findings.md`, `reports/model_comparison.md` |
| Bounded inverse-volatility sizing improves the downside profile at matched average exposure | **Not supported** (NIFTY 50 TRI, 2024, theoretical index) | Dynamic Sharpe 0.28–0.60 against 0.76 for buy-and-hold. Constants at the same exposure Sharpe ≈ 0.757. Drawdowns essentially unchanged. `reports/position_sizing_experiment.md`, `reports/stage6_failure_analysis.md` |

### Experiment design

| step | status | where |
| --- | --- | --- |
| 1. Historical SD, rolling 20/60, EWMA, GARCH(1,1), strictly lagged | **Done**, plus EGARCH, GJR, Student-t variants, Markov switching, XGBoost, HAR-RV family and India VIX models | Stages 1–4B |
| 2. Walk-forward one-step forecasts, calibration-first evaluation | **Done** for one step. Multi-day horizons have **not** been evaluated: Stage 5 used horizon-2 and horizon-3 *single-day* targets for execution timing | `reports/model_comparison.md`, `reports/advanced_model_comparison.md`, `reports/har_rv_findings.md` |
| 3. Exposure = target vol / forecast vol, 0–100% bounds | **Done** (Stage 5): targets of 10%, 12% and 15%, no leverage, next-close execution | `config/stage5.toml` |
| 4. Unscaled vs constant vs dynamic at comparable exposure, with costs | **Done for the NIFTY 50 TRI index only.** Development-matched and ex-post matched constants; 5, 10 and 20 bps costs. **Not done** on an existing NEXUS strategy's returns, which have never been supplied, nor on SPY or VT | `reports/position_sizing_experiment.md`, `reports/exposure_attribution.md` |
| 5. Stress tests: fast drawdowns, rebounds, model breaks, rebalance frequency | **Partly done.** Weekly rebalancing, bands, execution delay, forecast-failure injection and cash scenarios are covered. Event analysis is retrospective on four 2024 shocks only; no multi-crisis economic stress test exists | `reports/trading_cost_sensitivity.md`, `reports/stage6_failure_analysis.md` |

### Measures, failure modes and decision

- **Measures.** All are computed: QLIKE, MSE, calibration, realized portfolio volatility, worst drawdown, turnover, cash drag, matched-exposure returns, net Sharpe and ES95.
- **Failure modes from the brief.** All are guarded in code and tests:
  - No future volatility in sizing: same-close use is rejected by validation.
  - Matched-exposure benchmarks are mandatory.
  - Leverage is impossible by construction.
  - The sealed holdout and the "2024 already inspected" rule prevent optimization on the same crisis.
  - Warm-up minimums are enforced per model.
- **Go / no-go.** The **forecasting result is a GO** as a research result, which the brief explicitly accepts. The **overlay is a NO-GO** for deployment. See `reports/research_go_no_go.md`.
- **Second phase** (momentum plus volatility on NEXUS's previous live strategy) **has not started.** It needs that strategy's return series, which is not in this repository. As an idea it is H2, deferred.

---

## 3. Stage timeline

| stage | what was done | headline result | key report |
| --- | --- | --- | --- |
| 1A/1B Data | Ingestion of NIFTY 50 TRI (NSE official), SPY and VT (Yahoo); exchange-calendar verification; data-quality audit | All three assets WARNING (manual review documented). No silent repairs | `reports/data_quality.md`, `reports/calendar_verification.md`, `reports/dataset_manual_review.md` |
| 2 Baselines + GARCH | 10 models, walk-forward, refit every 21 sessions | Asymmetric GARCH best; Student-t adds nothing; historical baselines worst | `reports/research_findings.md` |
| 3 Advanced | Markov switching (filtered), XGBoost | XGBoost ranks first on point estimates; nothing significant after Holm. Markov over-forecasts | `reports/advanced_research_findings.md` |
| Intraday | Import and audit of NIFTY, SENSEX and India VIX minute data | **Provisional:** vendor, timezone and bar labels unverified | `reports/intraday_data_audit.md` |
| 4 HAR-RV | HAR, Log-HAR, HAR+VIX on 5-minute RV | Log-HAR best point estimate; levels HAR+VIX produced invalid forecasts | `reports/har_rv_findings.md`, `reports/vix_incremental_value.md` |
| 4B Positive VIX | Log-link VIX models, Ridge; **frozen forecasting protocol** | Log-HAR+VIX promising but driven by a few high-risk days; 0 of 10 contrasts pass | `reports/positive_vix_models.md`, `reports/frozen_forecasting_protocol.md` |
| 5 Economics | Inverse-volatility overlays, 221 registered paths, matched benchmarks, bootstrap | **Negative:** 5 of 5 overlays below buy-and-hold | `reports/position_sizing_experiment.md` |
| 6 Diagnosis | Read-only forensic attribution of Stage 5 | Rebound drag after 4 June 2024 explains 62–119% of the shortfall; costs secondary; accuracy ≠ allocation value | `reports/stage6_failure_analysis.md`, `reports/research_go_no_go.md` |
| H4 (draft) | Advisory risk-monitoring protocol, alert spec, evaluation plan, draft thresholds | **Not frozen**; awaiting review decisions R1–R8 | `reports/h4_registration_draft.md` |

---

## 4. Rules of the road (non-negotiable)

These rules are why the results can be trusted. Breaking one silently invalidates later work.

1. **The holdout (2025-01-01 to 2026-10-30) is sealed.**
   - Never evaluate on it, tune on it, or plot outcomes from it.
   - It is also not pristine. Earlier work incidentally exposed some observations, as disclosed in `experiments/stage5/registration.json`, so it cannot serve as primary independent confirmation.
   - Genuine confirmation needs **new sessions collected after a frozen registration**.
2. **2024 has been inspected repeatedly.** Use it for development checks and pipeline dry runs only. Never choose a model, threshold, frequency or rule because it worked in 2024.
3. **Never amend a frozen protocol.**
   - `reports/frozen_forecasting_protocol.md` and every `registration.json` stay as they are.
   - A change means a new, timestamped protocol version registered before new data are collected.
4. **Do not modify earlier artifacts.**
   - Stage 5 registers SHA-256 hashes of 1,047 protected files. Stage 6 and the verification scripts check them.
   - Add new files; never edit old reports, configs or run outputs.
5. **No model substitution, no imputation, no forward-filling.** A failed forecast is a recorded failure. Missing sessions stay in economic paths.
6. **Strict timing.** A forecast issued after close *t* can first affect the return ending *t+2* under next-close execution. Tests enforce this; keep it that way.
7. **Provisional data stay provisional.**
   - Intraday RV, India VIX and vendor spot data have unverified provenance (vendor, timezone, bar labels).
   - Models built on them are labelled PROVISIONAL. In H4 they must never feed production-grade classifications.
8. **No trading capability.** The repository contains no broker connection or execution code, and H4 is advisory only. Keep it that way unless a separately approved deployment project says otherwise.
9. **Report negative and inconclusive results** with the same care as positive ones.

---

## 5. Getting started

### Environment

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,ml]"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q
```

The full suite runs about 375 tests in roughly 10 minutes. `pyproject.toml` turns warnings into errors. Tests use synthetic fixtures. Integration checks that need local run archives skip themselves when those archives are absent.

### Data are not in this repository

Raw downloads, canonical datasets and experiment run archives (about 830 MB) are excluded by `.gitignore`. Some sources also have redistribution limits.

| data | how to obtain |
| --- | --- |
| SPY, VT daily | `python -m volrisk --config config/ingestion.toml --download-etfs` (Yahoo via yfinance; current-vintage adjusted prices) |
| NIFTY 50 TRI daily | NSE Indices total-return responses, replayed with `--nifty-json-dir` or `--nifty-csv-dir`; see README "Sources and raw preservation" |
| NIFTY, SENSEX, India VIX minute bars | **Not redistributable; vendor unknown.** Request the files privately from Jai Kaushik |
| NIFTYBEES ETF (Panel B) | `scripts/acquire_stage5_data.py`; not yet certified as an execution dataset |

After acquisition, rebuild in order:
1. Ingest, then audit (`--audit`).
2. Run the forecasting experiments (`volrisk.forecast_cli`).
3. Run the intraday import, then HAR and Stage 4B.
4. Run Stage 5, then Stage 6.

The exact commands are in the README section for each stage. Each CLI writes content-addressed runs under `experiments/<stage>/runs/` and a pointer `reports/latest_*.json`. Hashes verify reproduction.

### Repository map

| path | contents |
| --- | --- |
| `src/volrisk/data/` | Ingestion, normalization, calendars, audits, intraday pipeline |
| `src/volrisk/forecasting/` | Model interface, registry, historical, EWMA, GARCH family, Markov, XGBoost, HAR, positive-link HAR |
| `src/volrisk/evaluation/` | Walk-forward engines, metrics (QLIKE, DM/HAC, bootstrap, Holm), reporting |
| `src/volrisk/economics/` | Stage 5 accounting, alignment, metrics, attribution; Stage 6 `diagnosis.py` |
| `src/volrisk/monitoring/` | H4 draft: config validation, alert classification, evaluation statistics, development-only thresholds |
| `src/volrisk/*_cli.py` | One command line per stage |
| `config/` | One TOML per stage; `h4_monitoring.toml` is the H4 draft |
| `reports/` | All published findings, tables, figures and test reports |
| `experiments/` | Per-stage READMEs and registrations; run archives are local only |
| `tests/` | About 375 tests, one module per component or stage |
| `scripts/` | Data acquisition and independent output verification |
| `docs/` | This brief, plus `docs/history/` (earlier progress notes and a stage prompt) |

---

## 6. Open work, prioritized

Each item states the goal, why it matters and what "done" means.

### P0 — data foundations (everything economic is blocked on these)

1. **Prospective daily acquisition pipeline.** Daily NIFTY TRI, SPY and VT with immutable retrieval timestamps, appended without rewriting history. *Done when* a new session is ingested, audited and hashed automatically before the next open, with tests.
2. **Intraday and VIX provenance sign-off.** Identify vendor and export chain, original timezone, bar labels and VIX availability times. Reconcile samples against exchange data. The checklist is in `reports/frozen_forecasting_protocol.md`, "Required provenance and quality gates". *Done when* the gates are documented as passed, or the data are formally retired.
3. **Executable instrument data (Panel B).** Verified NIFTYBEES adjusted OHLC, the complete corporate-action record, closing-auction availability and a cost evidence base: spread, impact, fees. *Done when* an audit certifies it as an execution dataset. Until then, every economic result is a theoretical-index result.

### P1 — H4 risk monitoring (current primary path)

Read `reports/h4_registration_draft.md`, `reports/h4_alert_specification.md` and `reports/h4_prospective_evaluation_protocol.md`.

4. **Resolve review decisions R1–R8 with the CIOs.** They cover the alert model, percentiles and alert burden, de-escalation, re-specifications, asset scope, probability method, deadlines and acceptance criteria. Record them in `config/h4_monitoring.toml`.
5. **Implement the six horizon-1 close-to-close re-specifications** (Stage 4B VIX models, Stage 5 daily HAR), or remove them. They remain PROVISIONAL either way.
6. **Build the five append-only ledgers** (forecast, alert, acknowledgement, decision, outcome) and report rendering for the daily report and weekly summary. Use the record format in `src/volrisk/monitoring/alerts.py`. A 2024 dry run is a pipeline test only.
7. **Freeze and register**, following the checklist in `h4_registration_draft.md` §8, then collect 252 new sessions. `volrisk.monitoring_cli start` deliberately refuses to run until the config is FROZEN and a matching registration hash exists.

### P2 — research gaps from the original brief

8. **Multi-day horizons.** Five-session volatility forecasts with horizon-consistent targets and overlap-aware inference, run as a separate registered experiment (reserved in H4).
9. **Apply sizing to an actual NEXUS strategy's returns**, which the brief asked for. Obtain the return series, then design a matched-exposure study under a new registration, on data not used for design.
10. **Multi-market, multi-crisis economic evidence.** SPY, VT and longer verified NIFTY history covering crash-then-continuation, crash-then-rebound and slow grinds. This is needed before H1 (exceptional-risk limits with an exit rule) or H2 (momentum plus volatility, the brief's second phase) can be tested. Designs are in `reports/next_hypotheses.md`. They are **not backtested**, and must not be tuned on 2024.
11. **Lower-frequency adjustment (H3).** Only meaningful once measured costs exist (P0.3). Fix frequencies and bands from a conventional set before seeing outcomes.

### P3 — model housekeeping

12. GJR asymmetry parameter at its zero bound in 50–70% of refits: investigate stability or constraints. A change needs a new protocol version.
13. EGARCH-t degenerate fits on VT (ν at the 2.05 bound).
14. Unregistered model types (latent SV, Realized GARCH, Heston) stay stubs. Heston is impossible without options data.

---

## 7. Disclosures you must carry forward

- **Incidental later-period exposure.** A pre-existing review displayed some April 2025 rows, full-window audit aggregates and a search snippet. Data-quality reports also describe the full 2012–2026 window. None of this entered any model, but the holdout cannot be called pristine.
- **NIFTY 50 TRI is non-executable.** Stage 5 economics are index accounting: no ETF fees, tracking error, taxes or fill risk.
- **Intraday data are provisional.** Stage 4 and 4B results carry this label permanently.
- **Market risk is not portfolio risk.** H4 estimates index risk. It must never be presented as the risk of WSC's combined stock portfolio.
- **Volatility is not direction.** No result here supports treating high forecast volatility as a bearish or crash signal.

## 8. Literature

- **From the brief:** Moreira & Muir (2017), *Volatility-Managed Portfolios*; Barroso & Santa-Clara (2015), *Momentum has its moments*.
- **Sceptical follow-ups, worth reading before any new overlay work:**
  - Cederburg, O'Doherty, Wang & Yan (2020), *On the performance of volatility-managed portfolios*, JFE.
  - Liu, Tang & Zhou (2019), *Volatility-managed portfolio: does it really work?*, JPM.
  - Harvey et al. (2018), *The impact of volatility targeting*, JPM.
- **Forecasting methods used here:**
  - Corsi (2009), HAR-RV.
  - Glosten, Jagannathan & Runkle (1993), GJR-GARCH.
  - Nelson (1991), EGARCH.
  - Patton (2011), on QLIKE robustness.
- **For H4 evaluation:**
  - Kupiec (1995) and Christoffersen (1998), on interval and VaR backtests.
  - Brier (1950), and reliability diagrams for probability calibration.

Verify citations before quoting them in external documents.
