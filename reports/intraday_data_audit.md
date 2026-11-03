# Intraday data audit

**PROVISIONAL — NOT CERTIFIED FOR FORECAST RESEARCH.** The user does not know the vendor or export conventions. Numerical consistency does not verify source identity. Asia/Kolkata and start-of-minute OHLC labels are explicit working assumptions. All supplied datasets retain `research_ready=False`. NIFTY/SENSEX are spot-index candidates; the minute NIFTY series is not treated as NIFTY TRI.

Content-addressed run: `892aa7cb55d7fd0249ea75a3`. Imported: 2026-11-03T12:31:20.314106+00:00. Original download times are unknown; filesystem modification time is recorded separately.

## Actual source files

| filename | rows | first_timestamp | last_timestamp | sorted_in_source | duplicate_timestamps |
| --- | --- | --- | --- | --- | --- |
| NIFTY 1min 2022-2025.csv | 296148 | 2022-10-25 09:15:00+05:30 | 2025-12-31 15:29:00+05:30 | False | 375 |
| NIFTY 1min YTD 2026.csv | 57290 | 2026-01-01 09:15:00+05:30 | 2026-08-12 15:39:00+05:30 | True | 0 |
| SENSEX 1min 2023-2026.csv | 362800 | 2023-01-02 09:09:00+05:30 | 2026-10-30 15:28:00+05:30 | True | 0 |
| INDIA VIX_minute (1).csv | 1048338 | 2015-01-09 09:15:00+05:30 | 2026-05-15 13:07:00+05:30 | True | 0 |

### NIFTY 1min 2022-2025.csv

OHLC schema: `Unnamed: 0: int64`, `time: object`, `open: float64`, `high: float64`, `low: float64`, `close: float64`, `volume: int64`.
Time column: `time`; original timezone: not encoded; unknown. Stock codes: not encoded; exchanges: not encoded. Invalid timestamps: 0. SHA-256: `b418b4c4edacd433f377a88665b6e9f3d7b287a8a77fa2e9caa27113d1c0ff97`.

### NIFTY 1min YTD 2026.csv

OHLC schema: `Unnamed: 0: int64`, `close: float64`, `datetime: object`, `exchange_code: object`, `high: float64`, `low: float64`, `open: float64`, `stock_code: object`, `volume: int64`.
Time column: `datetime`; original timezone: not encoded; unknown. Stock codes: ['NIFTY']; exchanges: ['NSE']. Invalid timestamps: 0. SHA-256: `a4f23d821708ed795c94a4cd80a0812b01296db0621021f52f08d671248e67ae`.

### SENSEX 1min 2023-2026.csv

OHLC schema: `Unnamed: 0: int64`, `close: float64`, `datetime: object`, `exchange_code: object`, `high: float64`, `low: float64`, `open: float64`, `stock_code: object`, `volume: int64`.
Time column: `datetime`; original timezone: not encoded; unknown. Stock codes: ['BSESEN']; exchanges: ['BSE']. Invalid timestamps: 0. SHA-256: `1e33878a8267613a80f9d78d9975ae4ad285ba1534175e8ef97c8b0aec823109`.

### INDIA VIX_minute (1).csv

OHLC schema: `date: object`, `open: float64`, `high: float64`, `low: float64`, `close: float64`, `volume: int64`.
Time column: `date`; original timezone: not encoded; unknown. Stock codes: not encoded; exchanges: not encoded. Invalid timestamps: 0. SHA-256: `bcf7345108926c09434776ff6b5aa1ff7e27d37cc1993e037bb5222bb9497030`.

The pickle is hashed as opaque bytes only and is never deserialized. Its contents and coverage are unknown. It can be omitted safely from this workflow because the CSV supplies the VIX observations used here. Zero volume fields are preserved; index volume is not interpreted as traded share volume.

## Canonicalization and flagged observations

Source files are never rewritten. Sorting is deterministic. Duplicate timestamps with identical market fields (ignoring export row indices) keep the first filename/row; removed copies are quarantined. All copies of conflicting timestamps are quarantined. Invalid prices and OHLC, off-grid timestamps and outside-session rows remain flagged in canonical data. No interpolation, forward-fill, extreme-return deletion or winsorization occurs. Whole-file MAD is retrospective QC only and never a forecasting feature or exclusion rule. A flag is not proof of error.

| asset | canonical_rows | duplicate_copies_removed | conflicting_timestamps | invalid_price | invalid_ohlc | off_minute_grid | identity_mismatch | outside_session | extreme_return | mad_outlier | large_reversal | stale_sequence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nifty | 353063 | 375 | 0 | 0 | 0 | 0 | 0 | 1317 | 0 | 88 | 0 | 22 |
| sensex | 362800 | 0 | 0 | 0 | 0 | 0 | 0 | 11715 | 11 | 99 | 2 | 23 |
| india_vix | 1048338 | 0 | 0 | 0 | 2547 | 10751 | 0 | 923 | 46 | 1665 | 39 | 439 |

Quality thresholds (log-return units):

```json
{
  "minimum_session_completeness": 1.0,
  "index_extreme_log_return": 0.01,
  "vix_extreme_log_return": 0.1,
  "mad_multiple": 15.0,
  "stale_run_minutes": 10,
  "vix_max_age_seconds": 90,
  "jump_min_intervals": 20
}
```

Exact flagged records and original row/file identifiers are in this run’s `audit/*_flagged_observations.parquet` and `audit/*_quarantined.parquet`. `intraday_session_quality.csv` lists every missing minute and candidate session.

## Exchange calendars and gaps

NSE dates reuse the existing hash-verified cash-market calendar. BSE dates use independently reviewed BSE-authored annual/amendment notices, with syndicated/mirrored originals where direct access failed. The source register below distinguishes indexed extracts from archived PDFs. It is not a claim that every new PDF was downloaded. Unverified exceptional times have no invented minute grid; unknown weekdays remain candidate sessions and interrupt overnight adjacency. NSE 2015–2022 Muhurat timing, the 2015 budget session and 2021-02-24 outage schedule remain unverified where present. BSE special-session times not explicitly verified in configuration, including the January 2024 amendments, remain unverified.

| asset | raw_rows | normalized_rows | first | last | observed_sessions | verified_scheduled_sessions | missing_verified_sessions | incomplete_verified_sessions | unverified_candidate_sessions | complete_numerical_sessions | research_ready |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NIFTY | 353438 | 353063 | 2022-10-25 09:15:00+05:30 | 2026-08-12 15:39:00+05:30 | 942 | 942 | 0 | 6 | 0 | 936 | False |
| SENSEX | 362800 | 362800 | 2023-01-02 09:09:00+05:30 | 2026-10-30 15:28:00+05:30 | 944 | 942 | 3 | 142 | 8 | 797 | False |
| INDIA_VIX | 1048338 | 1048338 | 2015-01-09 09:15:00+05:30 | 2026-05-15 13:07:00+05:30 | 2808 | 2800 | 2 | 149 | 10 | 2649 | False |

Complete numerical sessions still depend on unverified source conventions. FAIL in session CSV means unusable for complete-session RV; WARNING means numerically complete but provisional. Missing/unverified sessions are retained rather than dropped from feature windows. Missing-session counts are restricted to verified schedules.

### Exact missing and unverified sessions

| asset | session_date | session_kind | expected_minutes |
| --- | --- | --- | --- |
| SENSEX | 2023-06-22 00:00:00 | regular | 375 |
| SENSEX | 2024-05-09 00:00:00 | regular | 375 |
| SENSEX | 2024-05-18 00:00:00 | disaster_recovery | 105 |
| INDIA_VIX | 2015-01-16 00:00:00 | regular | 375 |
| INDIA_VIX | 2019-07-02 00:00:00 | regular | 375 |

Unverified schedules below are limitations, not established data errors:

| asset | session_date | session_kind | source_rows |
| --- | --- | --- | --- |
| SENSEX | 2023-11-12 00:00:00 | special_times_unverified | 66 |
| SENSEX | 2024-01-20 00:00:00 | special_times_unverified | 382 |
| SENSEX | 2024-01-22 00:00:00 | regular | 0 |
| SENSEX | 2024-03-02 00:00:00 | special_times_unverified | 186 |
| SENSEX | 2024-11-01 00:00:00 | special_times_unverified | 128 |
| SENSEX | 2025-02-01 00:00:00 | special_times_unverified | 0 |
| SENSEX | 2025-10-21 00:00:00 | special_times_unverified | 214 |
| SENSEX | 2026-02-01 00:00:00 | special_times_unverified | 0 |
| INDIA_VIX | 2015-02-28 00:00:00 | budget_times_unverified | 375 |
| INDIA_VIX | 2015-11-11 00:00:00 | special_times_unverified | 60 |
| INDIA_VIX | 2016-10-30 00:00:00 | special_times_unverified | 46 |
| INDIA_VIX | 2017-10-19 00:00:00 | special_times_unverified | 60 |
| INDIA_VIX | 2018-11-07 00:00:00 | special_times_unverified | 60 |
| INDIA_VIX | 2019-10-27 00:00:00 | special_times_unverified | 60 |
| INDIA_VIX | 2020-11-14 00:00:00 | special_times_unverified | 60 |
| INDIA_VIX | 2021-02-24 00:00:00 | exchange_outage_extended_session_unverified | 53 |
| INDIA_VIX | 2021-11-04 00:00:00 | special_times_unverified | 60 |
| INDIA_VIX | 2022-10-24 00:00:00 | special_times_unverified | 60 |

Incomplete NIFTY sessions (the full SENSEX/VIX lists are in their session-issues CSVs):

| session_date | missing_minutes | missing_minute_times |
| --- | --- | --- |
| 2023-06-05 00:00:00 | 1 | 13:36 |
| 2023-06-14 00:00:00 | 7 | 12:41;12:42;12:43;12:44;12:45;12:46;12:47 |
| 2023-07-12 00:00:00 | 1 | 14:57 |
| 2023-07-24 00:00:00 | 3 | 12:49;12:50;12:51 |
| 2023-08-07 00:00:00 | 1 | 15:23 |
| 2024-04-23 00:00:00 | 6 | 10:52;10:53;10:54;10:55;10:56;10:57 |

### File boundaries

- NIFTY: `NIFTY 1min 2022-2025.csv` ends 2025-12-31 15:29:00+05:30; `NIFTY 1min YTD 2026.csv` starts 2026-01-01 09:15:00+05:30. 0 verified sessions lie strictly between the files. 0 of those have no observations.

### Calendar and instrument-convention sources

- [nse_regular](https://www.nseindia.com/static/market-data/market-timings): Cash normal market 09:15-15:30; pre-open and closing sessions are separate.
- [bse_regular](https://www.bseindia.com/markets/MarketInfo/DownloadAttach.aspx?attachedId=cb125690-a0f8-452a-ba6b-86cab98004bc&id=20230630-19): BSE Equity master circular continuous trading 09:15-15:30; reviewed official indexed extract.
- [nse_2020_budget](https://nsearchives.nseindia.com/content/circulars/CMTR43290.pdf): Use existing archived nse_2020_budget.pdf evidence; normal cash-market session.
- [nse_2023_muhurat](https://nsearchives.nseindia.com/content/circulars/CMTR59124.pdf): 2023-11-12 cash normal session 18:15-19:15.
- [nse_2024_muhurat](https://nsearchives.nseindia.com/content/circulars/CMTR64628.pdf): 2024-11-01 cash normal session 18:00-19:00.
- [nse_2025_muhurat](https://nsearchives.nseindia.com/content/circulars/CMTR70319.pdf): 2025-10-21 cash normal session 13:45-14:45.
- [nse_2024_march](https://nsearchives.nseindia.com/content/circulars/MSD60677.pdf): 2024-03-02 cash segments 09:15-10:00 and 11:30-12:30; existing archived PDF reviewed.
- [nse_2024_may](https://nsearchives.nseindia.com/content/circulars/MSD61893.pdf): 2024-05-18 cash segments 09:15-10:00 and 11:30-12:30; existing archive reviewed.
- [nse_2025_budget](https://nsearchives.nseindia.com/content/circulars/CMTR65729.pdf): 2025-02-01 normal cash session 09:15-15:30; existing archive reviewed.
- [nse_2026_budget](https://nsearchives.nseindia.com/content/circulars/CMTR72349.pdf): 2026-02-01 normal cash session 09:15-15:30; existing archive reviewed.
- [bse_2023_annual](https://www.marketscreener.com/quote/stock/BSE-LIMITED-33930062/news/BSE-Trading-Holidays-for-the-Calendar-Year-2023-for-Equity-Equity-Derivatives-and-SLB-Segments-42505039/): BSE-authored notice 20221208-31 syndicated unaltered by Publicnow. Fifteen initial weekday holidays; June date amended separately.
- [bse_2023_june](https://archives.nseindia.com/corporate/WIPRO_27062023201740_PA_Signed_27062023.pdf): Issuer filing explicitly records BSE 20230627-2: June 28 working, June 29 holiday. Corroborating primary filing, not direct BSE archive.
- [bse_2024_annual](https://www.publicnow.com/view/763111B4C52D6A1053C38FA182DFE00F004F892F): BSE-authored 20231212-40: fourteen scheduled weekday entries including Muhurat November 1; full date table reviewed through indexed extract. Direct site access returned 403.
- [bse_2024_may_close](https://www.ricago.com/assets/front/base/file/file_management/1714.pdf): Mirrored BSE notice 20240408-25: equity market closed 2024-05-20.
- [bse_2024_nov_close](https://www.smifs.com/files/downloads/638669483305232188_Trading%20Holiday%20on%20account%20of%20Maharashtra%20Legislative%20Assembly%20General%20Election%20on%20November%2020%2C%202024.pdf): Mirrored BSE 20241108-19: equity market closed 2024-11-20.
- [bse_2024_may_open](https://www.bseindia.com/downloads/SPDJ_ANN/MediaReleasePDF/1472152_mediareleasespecialtradingsessionfors%26pbseindices20240510.pdf): Official BSE index release, indexed extract: indices calculated May 18, segments 09:15-10:00 and 11:30-12:30 IST.
- [bse_2025_annual](https://www.marketscreener.com/quote/stock/BSE-LIMITED-33930062/news/BSE-Trading-Holidays-for-the-Calendar-Year-2025-for-Equity-Equity-Derivatives-and-SLB-Segments-48588701/): BSE-authored 20241213-30 syndicated through Publicnow: fourteen weekday entries, October 21 Muhurat special.
- [bse_2026_annual](https://www.steelcitynettrade.com/Circulars/BSE-Trading%20Holidays%20for%20the%20Calendar%20Year%202026%20for%20Equity%20and%20Equity%20Derivatives%20Segments.pdf): Mirrored BSE-authored 20251212-8, fifteen weekday holidays; this integration stops October 30.
- [bse_2026_january](https://bigul.co/pdf/20260112-8%201.pdf): Mirrored BSE 20260112-8 and 20260112-46 establish January 15 election trading holiday.
- [bse_2026_budget](https://www.ricago.com/assets/front/base/file/file_management/5077.pdf): BSE 20260128-32 confirms February 1 live session and refers to 20260116-33; cash session times still unverified in this configuration.
- [india_vix](https://www.nseindia.com/static/products-services/indices-indiavix-index): India VIX is annualized percentage volatility implied by NIFTY option quotes for approximately the next 30 calendar days; not realized variance.

## Audit trail and rerun

Existing modules inspected/reused: `data/storage.py`, `data/calendar_audit.py`, `data/return_audit.py`, `data/returns.py`, the forecasting/evaluation packages, `config/calendars.json`, its archived evidence/amendments, existing audit/experiment manifests, `pyproject.toml`, README and the existing test suite. Intraday files live in a separate package; daily model and dataset outputs are not overwritten.

The immutable `manifest.json` records input/code/output SHA-256 hashes, package versions, import timestamps, source schemas, calendar evidence, cleaning actions and thresholds. `reports/latest_intraday.json` points to it. Identical inputs/code/configuration reuse the same verified outputs. Changed inputs create a separate run.

```powershell
.\.venv\Scripts\python.exe -m volrisk.intraday_cli --config config/intraday.toml
```
