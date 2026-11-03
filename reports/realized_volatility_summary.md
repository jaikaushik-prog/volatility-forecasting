# Realized-volatility integration summary

**Descriptive, provisional results only. No forecasting models or strategies were run.**

## Definitions and availability

Bars are start-labelled, left-closed/right-open intervals anchored separately to each continuous exchange segment. A bar is available only at its end. Non-overlapping 1/5/10/15-minute bars require every constituent minute to be valid. A regular session has 375 minutes: 10-minute sampling therefore ends with a labelled 5-minute interval. No synthetic bars fill gaps. Each segment’s return path starts with its observed opening price, followed by bar closes. RV is the sum of squared log returns (decimal-return squared units); realized volatility is its square root. First-bar open-to-close returns are included. Scheduled-break reopening returns and overnight returns are separate. Full-session RV adds squared reopening returns; the full RV proxy adds overnight squared return. Overnight returns require consecutive known session endpoints, including across verified weekends/holidays, and never bridge an absent or unverified candidate session. Annualized volatility is sqrt(252 × daily variance). Short sessions are not extrapolated to full-day duration; regular-session frequency comparisons exclude them.

Strict completeness is 100% of valid expected minutes. Incomplete-session RV is missing, not zero. Observed endpoints may still support overnight/c2c returns even if a session’s interior is incomplete. Positive plus negative semivariance equals intraday RV. Five-minute finite-sample adjusted bipower variation uses adjacent absolute returns within each segment; max(RV−BPV,0) is a descriptive jump proxy, not a formal jump test. It requires at least the configured interval count and equal interval lengths within segments.

Daily lagged RV features shift by one expected/candidate session, then use full 5/22-session windows. Missing sessions break windows. Volatility of volatility is the sample standard deviation of sqrt(RV) over 22 past sessions. Current-day realized measures and VIX features are available at the recorded session close; lagged columns are explicitly named. Forecast targets must be shifted to the next session by a future modeling workflow.

## Frequency comparison on matched complete regular sessions

| asset | frequency_minutes | matched_regular_sessions | mean_rv | median_rv | p95_rv | max_rv | mean_annualized_vol_percent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| nifty | 1 | 928 | 3.81684e-05 | 2.65456e-05 | 9.43934e-05 | 0.00199005 | 9.00358 |
| nifty | 5 | 928 | 3.87091e-05 | 2.6319e-05 | 9.85098e-05 | 0.00175333 | 9.01666 |
| nifty | 10 | 928 | 3.86089e-05 | 2.58912e-05 | 9.79325e-05 | 0.00199587 | 8.91413 |
| nifty | 15 | 928 | 4.00707e-05 | 2.51529e-05 | 0.000104586 | 0.00279903 | 8.91568 |
| sensex | 1 | 797 | 4.4681e-05 | 2.92779e-05 | 0.000103876 | 0.00195767 | 9.54049 |
| sensex | 5 | 797 | 4.0806e-05 | 2.73746e-05 | 0.000102085 | 0.00174184 | 9.22535 |
| sensex | 10 | 797 | 4.08311e-05 | 2.68072e-05 | 0.00010179 | 0.00193291 | 9.12058 |
| sensex | 15 | 797 | 4.15434e-05 | 2.58857e-05 | 0.000107698 | 0.00273256 | 9.02237 |

- NIFTY: median paired RV(1m)/RV(5m) = 1.011; median overnight risk share = 15.38%; aggregate overnight share = 40.69% over 927 complete regular sessions with valid overnight endpoints.
- SENSEX: median paired RV(1m)/RV(5m) = 1.037; median overnight risk share = 14.80%; aggregate overnight share = 42.77% over 788 complete regular sessions with valid overnight endpoints.

Higher 1-minute RV can reflect sampling sensitivity, noise or genuine within-interval price variation. These data alone do not identify microstructure noise. The largest-RV sessions below and the saved plots show stress-period agreement/divergence without declaring one frequency the truth. No forecast stability or accuracy claim is made.

| session_date | rv_1min | rv_5min | rv_10min | rv_15min | overnight_squared_return | overnight_risk_share | asset |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-06-04 00:00:00 | 0.00199005 | 0.00175333 | 0.00199587 | 0.00279903 | 2.95982e-05 | 0.0166009 | nifty |
| 2024-06-05 00:00:00 | 0.00032654 | 0.000457147 | 0.000576561 | 0.00035157 | 3.57426e-05 | 0.0725166 | nifty |
| 2026-02-03 00:00:00 | 0.000395261 | 0.000358871 | 0.000356705 | 0.00038139 | 0.00213137 | 0.855889 | nifty |
| 2024-06-04 00:00:00 | 0.00195767 | 0.00174184 | 0.00193291 | 0.00273256 | 1.67989e-05 | 0.00955222 | sensex |
| 2026-03-02 00:00:00 | 0.000451331 | 0.000475294 | 0.000489101 | 0.000553406 | 0.00107848 | 0.694104 | sensex |
| 2024-06-05 00:00:00 | 0.00028211 | 0.000393385 | 0.000498094 | 0.000322454 | 1.29465e-05 | 0.0318619 | sensex |

## India VIX and shared coverage

VIX EOD is available on **880 / 942** NIFTY candidate sessions. Joint complete NIFTY RV / available VIX: **874** sessions. Complete NIFTY/SENSEX overlap: **753** sessions. These are coverage intersections for diagnostics; native datasets retain their full calendars.

VIX is a separate implied-volatility series. Its minute changes are never NIFTY RV. EOD uses only valid same-session observations available at or before the NIFTY close, within the configured 90-second age limit. Missing VIX is not carried forward. Levels in percentage points are divided by 100 for annualized decimal volatility. India VIX describes approximately 30 calendar days of forward implied volatility. The trailing comparison uses 22 sessions of full RV, annualized with 252. Both 30-calendar-day variance proxies multiply annualized variance by 30/365. This assumes linear variance accrual and 252 trading sessions/year; forward option-implied and backward realized horizons/measurement remain different. The difference is not identified as a volatility risk premium. Percentiles compare the current VIX only with strictly earlier observations in a 252-session window (minimum 60); missing observations reduce history and never get filled.

Detailed per-column availability, earliest/latest usable dates and missing counts: `intraday_feature_coverage.csv`.

## Research readiness and next experiments

All outputs are provisional until vendor, instrument identity, timezone and bar labels can be independently established. Review duplicate provenance, outside-session rows, invalid VIX OHLC, missing SENSEX minutes and unresolved special schedules. Do not certify a series merely because its prices or hours look plausible. The daily NIFTY TRI pipeline remains separate.

After those checks: predeclare sampling-frequency robustness comparisons, then evaluate a HAR-RV baseline, overnight/intraday decomposition, lagged VIX ablations and joint-market features using origin timestamps and time-series splits. This integration implements none of those forecast models. Descriptive inspection of 2025–2026 here does not create a new untouched holdout.

## Saved figures

- [figures/intraday/nifty_rv_frequencies.png](figures/intraday/nifty_rv_frequencies.png)
- [figures/intraday/nifty_overnight_signature.png](figures/intraday/nifty_overnight_signature.png)
- [figures/intraday/nifty_stress_diagnostics.png](figures/intraday/nifty_stress_diagnostics.png)
- [figures/intraday/sensex_rv_frequencies.png](figures/intraday/sensex_rv_frequencies.png)
- [figures/intraday/sensex_overnight_signature.png](figures/intraday/sensex_overnight_signature.png)
- [figures/intraday/sensex_stress_diagnostics.png](figures/intraday/sensex_stress_diagnostics.png)
- [figures/intraday/session_completeness.png](figures/intraday/session_completeness.png)
- [figures/intraday/nifty_vix_comparison.png](figures/intraday/nifty_vix_comparison.png)
- [figures/intraday/joint_coverage.png](figures/intraday/joint_coverage.png)
