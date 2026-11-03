# NEXUS Sprint 1B data quality audit

Audit `572f825c852d8c0c540a207e`; executed 2026-11-03T06:19:40.916541+00:00.
Input ingestion run: `20261103T045329099102Z_79120125`.

**PASS**: checks valid. **WARNING**: manual review required. **FAIL**: unsafe for research; excluded from canonical publication.

No raw files or prices were altered. No forward-fill, interpolation, winsorization, mixed-currency series or cross-market calendar join is used.

## Asset summary

| Asset | Currency | First | Last | Observations | Usable returns | Suspicious returns | Status | Research readiness |
|---|---|---|---|---:|---:|---:|---|---|
| SPY | USD | 2012-01-03 | 2026-11-02 | 3730 | 3729 | 10 | WARNING | MANUAL_REVIEW_REQUIRED |
| VT | USD | 2012-01-03 | 2026-11-02 | 3730 | 3729 | 10 | WARNING | MANUAL_REVIEW_REQUIRED |
| NIFTY50_TRI | INR | 2012-01-02 | 2026-11-02 | 3677 | 3676 | 7 | WARNING | MANUAL_REVIEW_REQUIRED |

## Interpretation and research limits

A WARNING is not unconditional research approval. Resolve or explicitly document acceptance of flagged observations and calendar limitations before out-of-sample work. No forecasting or backtest is included.

Return usability means mathematically valid on the observed sequence, excluding invalid adjacent prices and confirmed missing sessions. It does not certify unverified historical intervals as single trading sessions. `calendar_interval_verified` records that distinction for every observation.

Simple returns use P(t)/P(t-1)-1; log returns use ln(P(t)/P(t-1)). The audit verifies log1p identity and every cumulative prefix within each uninterrupted valid segment. First returns are null. Original stored return errors cause FAIL and are never repaired to pass tests.

If a confirmed session is absent, the first subsequent daily return is null in the inspection artifact, with the original interval returns retained in `observed_*` columns and an explicit exclusion reason. This is a documented missing-session policy, not a replacement price. Failed assets are quarantined.

All diagnostics, median/MAD flags and annualized volatility are retrospective full-sample descriptions. They must not be fed into out-of-sample forecasts. Annualization is sqrt(configured sessions) times sample log-return standard deviation (ddof=1). USD and INR statistics remain asset-specific.

Yahoo adjusted prices are a current-vintage, same-provider reconstruction, not a point-in-time archive or an independent-vendor total-return certification. NSE gross TRI identity is verified against the stored official response field. Historical revisions may still occur.

## SPY (USD)

Source: Yahoo Finance via yfinance.

Convention: `yfinance_auto_adjusted_close_dividends_and_splits`. Session timezone: `America/New_York`.

Invalid prices: 0; invalid dates: 0; duplicate asset-date excess: 0; exact duplicate-row excess: 0; long gaps: 0.

Calendar coverage bounds: 2012-01-01 through 2026-11-02. Explicit unverified dates inside these bounds: []. Expected sessions in verified coverage, excluding those exceptions: 3730; missing: 0; unexpected observed sessions: 0. Full-window expected count: 3730 (null means unavailable). Unverified absent weekdays: 0; these may be holidays and are not declared errors.

- [NYSE calendar evidence](https://hk.marketscreener.com/quote/stock/NYSE-EURONEXT-13866/news/NYSE-EURO-NYSE-Euronext-NYX-Announces-its-2012-and-2013-Holiday-Calendar-and-Early-Closings-for-13533281/)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/NYSE-Group-Announces-2022-2023-and-2024-Holiday-and-Early-Closings-Calendar-2021.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/NYSE-Group-Announces-2023-2024-and-2025-Holiday-and-Early-Closings-Calendar-2022.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of--IGCRS.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/archive/266fafb2-a85c-433a-8350-0760d895b49c.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/archive/313c9417-c6e3-46d3-b820-dbc7d9961ebd.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/archive/442a7c75-b606-4b5d-9853-2efa7d6634c3.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/archive/91a5230f-7233-4a93-b30a-79c9411ebdbe.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/archive/b97d77df-0ecb-4db0-9ced-75bdb9b218ba.pdf)
- [NYSE calendar evidence](https://www.nyse.com/trade/hours-calendars)
- [NYSE calendar evidence](https://www.sec.gov/files/rules/proposed/2013/34-69077.pdf)

Return checks: **PASS**. Source total-return compatibility: **True**. Adjustment/identity result: `VERIFIED_YAHOO_ADJUSTED_CLOSE`.

Yahoo Adj Close comparison: 3730/3730 prices matched. Distribution events checked: 59; factor warnings: 0; recorded split events: 0.

- Current-vintage Yahoo history is not a historical as-of database. The reference is from the same provider, not an independent vendor.

Absolute-return flags: 2; all suspicious-return dates: 10; stale-price observations: 0; longest equal-price run: 2 observations.

| Descriptive diagnostic | Value |
|---|---:|
| mean_daily_simple_return | 0.00059845 |
| daily_log_return_std | 0.01040161 |
| annualized_historical_volatility | 0.16512048 |
| min_daily_simple_return | -0.10942360 |
| max_daily_simple_return | 0.10501940 |

Cleaning actions:

- None. Original prices, dates and returns retained exactly; audit annotations added.

Validation notices:

- WARNING `extreme_return`: Large absolute simple returns retained for review.

Visual inspection artifacts:

- [SPY_normalized_price.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/SPY_normalized_price.png>)
- [SPY_daily_returns.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/SPY_daily_returns.png>)
- [SPY_log_return_distribution.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/SPY_log_return_distribution.png>)
- [SPY_session_gaps.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/SPY_session_gaps.png>)
- [SPY_extreme_events.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/SPY_extreme_events.png>)

## VT (USD)

Source: Yahoo Finance via yfinance.

Convention: `yfinance_auto_adjusted_close_dividends_and_splits`. Session timezone: `America/New_York`.

Invalid prices: 0; invalid dates: 0; duplicate asset-date excess: 0; exact duplicate-row excess: 0; long gaps: 0.

Calendar coverage bounds: 2012-01-01 through 2026-11-02. Explicit unverified dates inside these bounds: []. Expected sessions in verified coverage, excluding those exceptions: 3730; missing: 0; unexpected observed sessions: 0. Full-window expected count: 3730 (null means unavailable). Unverified absent weekdays: 0; these may be holidays and are not declared errors.

- [NYSE calendar evidence](https://hk.marketscreener.com/quote/stock/NYSE-EURONEXT-13866/news/NYSE-EURO-NYSE-Euronext-NYX-Announces-its-2012-and-2013-Holiday-Calendar-and-Early-Closings-for-13533281/)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/NYSE-Group-Announces-2022-2023-and-2024-Holiday-and-Early-Closings-Calendar-2021.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/NYSE-Group-Announces-2023-2024-and-2025-Holiday-and-Early-Closings-Calendar-2022.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of--IGCRS.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/archive/266fafb2-a85c-433a-8350-0760d895b49c.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/archive/313c9417-c6e3-46d3-b820-dbc7d9961ebd.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/archive/442a7c75-b606-4b5d-9853-2efa7d6634c3.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/archive/91a5230f-7233-4a93-b30a-79c9411ebdbe.pdf)
- [NYSE calendar evidence](https://s2.q4cdn.com/154085107/files/doc_news/archive/b97d77df-0ecb-4db0-9ced-75bdb9b218ba.pdf)
- [NYSE calendar evidence](https://www.nyse.com/trade/hours-calendars)
- [NYSE calendar evidence](https://www.sec.gov/files/rules/proposed/2013/34-69077.pdf)

Return checks: **PASS**. Source total-return compatibility: **True**. Adjustment/identity result: `VERIFIED_YAHOO_ADJUSTED_CLOSE`.

Yahoo Adj Close comparison: 3730/3730 prices matched. Distribution events checked: 57; factor warnings: 0; recorded split events: 0.

- Current-vintage Yahoo history is not a historical as-of database. The reference is from the same provider, not an independent vendor.

Absolute-return flags: 2; all suspicious-return dates: 10; stale-price observations: 0; longest equal-price run: 2 observations.

| Descriptive diagnostic | Value |
|---|---:|
| mean_daily_simple_return | 0.00047595 |
| daily_log_return_std | 0.01024897 |
| annualized_historical_volatility | 0.16269732 |
| min_daily_simple_return | -0.11641118 |
| max_daily_simple_return | 0.09140978 |

Cleaning actions:

- None. Original prices, dates and returns retained exactly; audit annotations added.

Validation notices:

- WARNING `extreme_return`: Large absolute simple returns retained for review.

Visual inspection artifacts:

- [VT_normalized_price.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/VT_normalized_price.png>)
- [VT_daily_returns.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/VT_daily_returns.png>)
- [VT_log_return_distribution.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/VT_log_return_distribution.png>)
- [VT_session_gaps.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/VT_session_gaps.png>)
- [VT_extreme_events.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/VT_extreme_events.png>)

## NIFTY50_TRI (INR)

Source: NSE Indices official JSON responses.

Convention: `official_gross_total_return_index_level`. Session timezone: `Asia/Kolkata`.

Invalid prices: 0; invalid dates: 0; duplicate asset-date excess: 0; exact duplicate-row excess: 0; long gaps: 0.

Calendar coverage bounds: 2012-01-01 through 2026-11-02. Explicit unverified dates inside these bounds: ['2014-04-24']. Expected sessions in verified coverage, excluding those exceptions: 3677; missing: 0; unexpected observed sessions: 0. Full-window expected count: None (null means unavailable). Unverified absent weekdays: 1; these may be holidays and are not declared errors.

- [NSE calendar evidence](https://geplcapital.com/fundamental-research/649a873a2dbe6.1687848762.CMTR57285.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMPT57296.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR19539.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR19734.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR20063.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR22317.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR23302.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR24977.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR25326.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR26045.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR27792.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR28337.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR31297.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR33746.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR36475.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR39612.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR40536.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR42877.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR43290.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR46623.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR50560.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR54757.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR59722.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR61518.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR64960.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR65587.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR65729.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR71775.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR72260.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/CMTR72349.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/FAOP26362.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/MSD42319.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/MSD60340.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/MSD60677.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/MSD61893.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/content/circulars/SURV60342.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/global/content/about_us/NSEIL_Annual_Report_2013.pdf)
- [NSE calendar evidence](https://nsearchives.nseindia.com/global/content/about_us/NSEIL_Annual_Report_2015.pdf)
- [NSE calendar evidence](https://www.cse-india.com/upload/CSE%20Notices%20%26%20Circulars/2012/Notice260412.htm)

Return checks: **PASS**. Source total-return compatibility: **True**. Adjustment/identity result: `Gross TotalReturnsIndex field selected; price index and NTR excluded.`.

- Original NSE HTTP-completion times were not recorded separately; response-save times are retained.

Absolute-return flags: 1; all suspicious-return dates: 7; stale-price observations: 0; longest equal-price run: 2 observations.

| Descriptive diagnostic | Value |
|---|---:|
| mean_daily_simple_return | 0.00054118 |
| daily_log_return_std | 0.01011486 |
| annualized_historical_volatility | 0.16056849 |
| min_daily_simple_return | -0.12914575 |
| max_daily_simple_return | 0.08762944 |

Cleaning actions:

- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.
- `source_non_monotonic`: Source dates were not ascending; normalized output is sorted.

Validation notices:

- WARNING `extreme_return`: Large absolute simple returns retained for review.
- WARNING `partial_calendar_authority`: Historical calendar coverage is incomplete. Dates outside coverage or in explicit unverified-date exceptions remain unverified, not confirmed missing sessions.

Visual inspection artifacts:

- [NIFTY50_TRI_normalized_price.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/NIFTY50_TRI_normalized_price.png>)
- [NIFTY50_TRI_daily_returns.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/NIFTY50_TRI_daily_returns.png>)
- [NIFTY50_TRI_log_return_distribution.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/NIFTY50_TRI_log_return_distribution.png>)
- [NIFTY50_TRI_session_gaps.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/NIFTY50_TRI_session_gaps.png>)
- [NIFTY50_TRI_extreme_events.png](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/figures/NIFTY50_TRI_extreme_events.png>)

## Reproducibility and evidence

The adjacent `data_quality_summary.csv` contains per-asset coverage and descriptive metrics. `suspicious_dates.csv` contains all flagged dates, including unverified calendar absences, reasons, severities and verification actions. Null prices on absent dates are not inserted into canonical time series.

Full audit trail: [audit_manifest.json](<C:/Users/DELL/Desktop/nexus-volatility-research/reports/audits/572f825c852d8c0c540a207e/audit_manifest.json>). It records source file paths and SHA-256 hashes, original acquisition metadata/timestamps, adjustment-reference metadata, effective thresholds, calendar sources, code hashes, dependency versions and output hashes.

Audit IDs depend on input bytes, implementation, configuration and package versions. Repeating the same audit verifies and reuses the same artifacts. No raw file is overwritten; raw hashes are checked before and after execution. Git commit identity is unavailable where the repository has no commit; implementation hashes are the code version.

Synthetic pytest fixtures validate the software only; they are not research data and do not establish the quality of real observations. Real-data results above come from the selected saved ingestion run.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --audit
```

Sprint 1B ends here. No Sprint 1C models or portfolio calculations were implemented.
