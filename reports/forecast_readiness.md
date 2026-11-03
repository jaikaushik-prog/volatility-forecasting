# Forecast readiness — PROVISIONAL

Numerical and temporal integrity gates passed on the loaded development/validation artifacts. This is not independent source certification. The user confirmed NIFTY as an NSE spot-index series (reported source: NSE); the original audit remains unchanged. Export documentation, original timezone and bar labels remain unverified. SENSEX retains its separate BSE calendar and source-identity limitation.

Run `d3094f857ec08cfaad204970`; source intraday run `892aa7cb55d7fd0249ea75a3`. Numerical values were loaded only through **2024-12-31**. No 2025–2026 forecasting or evaluation occurred.

## Gates and exclusions

- Verify input, calendar-evidence, intraday implementation and artifact hashes; never re-ingest or alter raw data.
- Reconcile saved 5/10/15-minute bars to daily RV, semivariances, bar availability and session boundaries.
- Require complete valid within-session minutes. Preserve verified special sessions at their actual duration; do not scale them to a normal day.
- Reconcile overnight and spot close-to-close returns to adjacent valid session endpoints. Never bridge absent/unverified sessions.
- Preserve missing/excluded session rows, so 5/22-session feature windows cannot compress gaps.
- Verify VIX EOD age, same-session availability and percent/decimal conversion; apply one additional FULL SESSION lag.
- The extra VIX lag reduces timing ambiguity but does not verify timezone, source identity or bar labels.
- Exclude incomplete/unverified sessions; identical duplicate copies were already quarantined by integration.
- Sensitivity additionally excludes sessions with absolute-return flags or at least ten unchanged-price minutes. These flags may represent genuine market moves; this is not a new raw-data cleaning rule.
- Whole-file MAD flags from integration are NOT used for model features or exclusions: their thresholds used the full source sample.

| asset | frequency | scenario | period | session_rows | complete_sessions | complete_special_duration_sessions | valid_overnight | valid_lagged_vix | all_har_origin_features | questionable_sessions | excluded_sessions | first_session | last_session | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NIFTY | 5 | eligible | development | 293 | 288 | 1 | 292 | 292 | 205 | 0 | 5 | 2022-10-25 00:00:00 | 2023-12-29 00:00:00 | PROVISIONAL |
| NIFTY | 5 | eligible | validation | 249 | 248 | 3 | 249 | 249 | 227 | 0 | 1 | 2024-01-01 00:00:00 | 2024-12-31 00:00:00 | PROVISIONAL |
| SENSEX | 5 | eligible | development | 246 | 126 | 0 | 237 | 0 | 70 | 0 | 120 | 2023-01-02 00:00:00 | 2023-12-29 00:00:00 | PROVISIONAL |
| SENSEX | 5 | eligible | validation | 250 | 239 | 0 | 237 | 0 | 123 | 0 | 11 | 2024-01-01 00:00:00 | 2024-12-31 00:00:00 | PROVISIONAL |

Complete sessions count usable measured RV, not supervised training pairs or evaluated forecasts. All-HAR-origin-feature counts include rolling-history/VIX constraints. `har_rv_sample_sizes.csv` covers every scenario/frequency; `har_rv_exclusions.csv` identifies each excluded session. `har_rv_model_comparison.csv` contains actual evaluated counts.

## Holdout protection

Development is 2022–2023 (actual NIFTY starts 2022-10-25); validation is 2024. Holdout remains 2025–2026, with the earlier project boundary preserved. Parquet predicate filters and a second walk-forward cutoff prevent holdout values from entering features, training, plots, losses or selection. File hashing examines bytes only. Earlier Stage 2 outputs and the descriptive integration audit had already exposed aspects of 2025–2026; the archive cannot be described as historically pristine. Future final confirmation needs a genuinely unseen, predeclared period.
