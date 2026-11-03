# Frozen forecasting protocol — subsequent prospective evaluation

Protocol frozen with Stage 4B run `940447e060f8874e34b2724b` at 2026-11-03T16:08:58.989362+00:00. It was designed after exploratory 2024 analysis. It does not retroactively make 2024 independent.

## Scope and candidates

NIFTY NSE spot. Primary target: next-session complete 5-minute intraday realized variance. Secondary target: that RV plus adjacent valid overnight squared log return, scored separately. Candidates: RV-EWMA, standard HAR, Log-HAR M0, Log-HAR+VIX M1, Log-HAR+VIX-change M2, Ridge M3. Retain all six as the frozen comparison set; the original negative levels HAR+VIX is an archived unsuccessful diagnostic comparator, not a prospective candidate. No portfolio or trading study is authorized.

## Fixed model specification

Use the exact feature definitions, 500-position window, 126-pair minimum, 21-session refits, training-only zero-RV treatment, standardized Ridge objective and residual-smearing correction recorded in this run. Keep the additional full-session VIX lag. Freeze the selected penalties below; do not retune them on 2024 or the prospective evaluation. Maintain the native session grid and common regression training pairs. Retain all attempted predictions and common-date comparisons.

| target | alpha | selection_available_on | tuning_cutoff | score | criterion | grid_size |
| --- | --- | --- | --- | --- | --- | --- |
| intraday | 10 | 2023-12-29 | 2023-12-31 | -9.80058 | equal_fold_mean_qlike_then_larger_alpha_on_exact_tie | 4 |
| intraday_overnight | 100 | 2023-12-29 | 2023-12-31 | -9.16702 | equal_fold_mean_qlike_then_larger_alpha_on_exact_tie | 4 |

## Required provenance and quality gates

Before registration of the evaluation start, obtain source/export documentation identifying vendor/API, NSE spot instrument (not futures/TRI), original timezone, daylight/timestamp handling, start/end bar labels, OHLC construction and availability times. Independently reconcile sample prices/bars with exchange or documented vendor evidence; resolve quarantined/conflicting records and special-session calendars. Document licensing and data vintage. Numerical checks must pass session completeness, no cross-session intraday returns, RV reconciliation, adjacent overnight endpoints and causal VIX availability. An extra VIX lag does not certify source conventions.

A corrected source vintage may change RV/feature values. That requires a new development-only audit and a new protocol version frozen before future collection begins. Preserve this protocol and all old results; do not silently reinterpret provisional numbers as verified.

## Obtaining genuinely unseen data

Do not use 2025–2026 as a pristine holdout: earlier project research exposed some observations. This workflow has not read them. Instead, after provenance sign-off and timestamped protocol/hash registration, start at the first scheduled NSE session strictly after both events. Collect new data as it is released, with immutable retrieval and availability timestamps. Publish each forecast to an append-only local ledger before the target session opens. No future-period evaluation is run by Stage 4B.

Evaluate exactly the first 252 scheduled sessions after that start. Require at least 200 matched eligible dates for the primary conclusion; otherwise declare the result inconclusive. Never extend or stop the period based on forecast losses. Restrict interim monitoring to data integrity and operational failures, without model ranking or outcome-driven specification changes.

## Statistical and selection policy

Primary contrasts: M1−M0, M2−M0 and M3−M0. Secondary contrasts: M1−RV-EWMA and M2−M1. Apply the same five to the separate overnight-inclusive target; Holm-adjust all ten jointly. Use mean QLIKE as the primary loss, with MSE/MAE, bias, observed/predicted calibration, positivity, availability and computational cost as diagnostics. Use the saved gap-aware HAC and 10,000-draw stationary bootstrap, block length 10, seed 20261103. Report pointwise intervals and both adjusted p-values.

Retain M0 unless a challenger has lower primary mean QLIKE and both adjusted p-values below .05, no invalid positive-link predictions on otherwise eligible origins, and aggregate calibration at least as close to one in absolute log distance as M0. If multiple challengers satisfy these rules, prefer the smaller feature set; if still tied, prefer lower primary QLIKE. If none qualifies, report no established replacement. Secondary-target gains alone do not select the primary model. No risk-management or portfolio benefit may be inferred from this test.

## Failure handling and regime rules

No interpolation, artificial forecasts, winsorization, automatic crisis deletion or fallback model. Reject nonfinite/underflowed predictions and annualized volatility above the fixed 5.0 ceiling; record each failure and exclude only from matched scoring, while reporting its full failure rate. Any positive-link invalid prediction disqualifies promotion under this protocol. Standard HAR retains its flagged training-derived floor policy and its floor count must be reported. Insufficient history remains warm-up. Preserve missing session rows and their effect on feature windows. Origin-known IV regimes may be reported descriptively; no regime-based switching rule is introduced. Retrospective shock labels and quarter comparisons never become prospective selection rules.

The saved run registration, configuration, source snapshot and manifests identify this protocol. Any amendment requires a new timestamped version before unseen evaluation begins. No future evaluation or data acquisition is scheduled or executed by this command.
