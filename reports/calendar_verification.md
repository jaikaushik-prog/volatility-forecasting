# Historical exchange-calendar verification

Current audit `572f825c852d8c0c540a207e`. Previous review queue: `6b40c1052542abcbb4675b6e`.

464 of 465 historical asset-date absence flags are confirmed closures. 1 remains unverified. All 17 pre-2026 weekend observations are retained; 17 have exchange evidence.

The independently transcribed schedules cover 2012 through November 2, 2026. No holidays were inferred from missing prices. Early closes and Muhurat/live weekend sessions remain trading observations. Settlement-only holidays and other-segment calendars are not substituted for cash-market calendars.

## Year-by-year reconciliation

SPY and VT use NYSE/Arca sessions. Their counts below are per ETF; no cross-market intersection is used. Expected counts exclude explicitly unverified dates. The full-window expected count is null for NSE 2014.

| Year | SPY obs / expected | VT obs / expected | NIFTY obs / verified expected | Confirmed missing (all assets) | Unverified asset-dates |
|---|---:|---:|---:|---:|---:|
| 2012 | 250 / 250 | 250 / 250 | 251 / 251 | 0 | 0 |
| 2013 | 252 / 252 | 252 / 252 | 250 / 250 | 0 | 0 |
| 2014 | 252 / 252 | 252 / 252 | 244 / 244 | 0 | 1 |
| 2015 | 252 / 252 | 252 / 252 | 248 / 248 | 0 | 0 |
| 2016 | 252 / 252 | 252 / 252 | 247 / 247 | 0 | 0 |
| 2017 | 251 / 251 | 251 / 251 | 248 / 248 | 0 | 0 |
| 2018 | 251 / 251 | 251 / 251 | 246 / 246 | 0 | 0 |
| 2019 | 252 / 252 | 252 / 252 | 245 / 245 | 0 | 0 |
| 2020 | 253 / 253 | 253 / 253 | 252 / 252 | 0 | 0 |
| 2021 | 252 / 252 | 252 / 252 | 248 / 248 | 0 | 0 |
| 2022 | 251 / 251 | 251 / 251 | 248 / 248 | 0 | 0 |
| 2023 | 250 / 250 | 250 / 250 | 246 / 246 | 0 | 0 |
| 2024 | 252 / 252 | 252 / 252 | 249 / 249 | 0 | 0 |
| 2025 | 250 / 250 | 250 / 250 | 249 / 249 | 0 | 0 |
| 2026 | 210 / 210 | 210 / 210 | 206 / 206 | 0 | 0 |

2026 is a partial year, ending November 2. Zero confirmed missing sessions does not resolve the one explicitly unverified date.

## Remaining calendar question

**NSE, April 24, 2014:** likely election closure. The recovered NSE FAOP26362 notice covers equity derivatives. The corresponding cash-market notice has not been recovered. Contemporary reporting corroborates an exchange closure ([Business Standard, April 3, 2014](https://www.business-standard.com/article/markets/markets-to-be-closed-on-apr-24-owing-to-elections-114040301123_1.html)), but this audit retains the stronger requirement for cash-market exchange evidence. The date is explicitly unverified, not a confirmed missing session or an approved cash-market holiday. The observed April 23 to April 25 return is preserved, with `calendar_interval_verified=False`.

## Confirmed weekend observations

| Date | Asset | Evidence |
|---|---|---|
| 2012-01-07 | NIFTY50_TRI | Special live trading session; nse_2012_january_special.pdf |
| 2012-03-03 | NIFTY50_TRI | Special live trading session; nse_2012_march_special.pdf |
| 2012-04-28 | NIFTY50_TRI | NSE cash-market live session confirmed by CSE exchange notice; nse_2012_april_special_confirmation.html |
| 2012-09-08 | NIFTY50_TRI | Special live session confirmed in NSE annual report 2012-13 PDF page 16, cash/derivatives chart note; nse_annual_report_2013.pdf |
| 2013-05-11 | NIFTY50_TRI | Special live trading session; nse_2013_may_special.pdf |
| 2013-11-03 | NIFTY50_TRI | Muhurat trading session; nse_2013_annual.pdf |
| 2014-03-22 | NIFTY50_TRI | Special live trading from BCP site; nse_2014_march_special.pdf |
| 2015-02-28 | NIFTY50_TRI | Special session confirmed in NSE annual report 2014-15 PDF page 12, cash/derivatives chart note; nse_annual_report_2015.pdf |
| 2016-10-30 | NIFTY50_TRI | Muhurat trading session; nse_2016_annual.pdf |
| 2019-10-27 | NIFTY50_TRI | Muhurat trading session; nse_2019_annual.pdf |
| 2020-02-01 | NIFTY50_TRI | Union Budget live session; nse_2020_budget.pdf |
| 2020-11-14 | NIFTY50_TRI | Muhurat trading session; nse_2020_annual.pdf |
| 2023-11-12 | NIFTY50_TRI | Muhurat trading session; nse_2023_annual.pdf |
| 2024-01-20 | NIFTY50_TRI | Regular live equity session at primary site; MSD60340 supersedes original DR-session notice MSD59999; nse_2024_january_web_verification.json |
| 2024-03-02 | NIFTY50_TRI | Special live session with DR-site switchover; nse_2024_march_special.pdf |
| 2024-05-18 | NIFTY50_TRI | Special live session with DR-site switchover; nse_2024_may_special.pdf |
| 2025-02-01 | NIFTY50_TRI | Union Budget live session; nse_2025_budget.pdf |
| 2026-02-01 | NIFTY50_TRI | Budget special session; nse_2026_holidays.pdf; nse_2026_election.pdf; nse_2026_budget.pdf |

## Evidence qualifications

- NYSE 2012-2013: issuer-authored Business Wire release accessed on a syndication host. Direct HTML download returned 403; a labeled factual web-reader transcription is saved.
- Sandy closures: SEC Regulation SCI proposal, PDF page 28. Direct PDF download returned 403; a labeled web-reader transcription is saved.
- NSE January 20, 2024: final MSD60340 specifies regular primary-site trading and withdraws the earlier DR-session notices. Direct download failed; a labeled web-reader transcription is saved.
- NSE 2023 Bakri Id amendment: issuer circular CMTR57285 is archived from a broker mirror, corroborated by official clearing circular CMPT57296.
- NSE January 22, 2024 closure: official SURV60342 explicitly cites the cash-market closure circular CMTR60338.
- September 8, 2012 and February 28, 2015 sessions: exchange annual-report chart footnotes, PDF pages 16 and 12 respectively; April 28, 2012: CSE exchange notice explicitly confirms NSE cash trading. These are primary exchange confirmations, not recovered individual NSE trading circulars.
- Original downloaded bytes and retrieval metadata remain unchanged. Web-reader transcriptions are identified separately and are not presented as original HTTP responses. Hashes establish archive integrity, not issuer signatures.

## Dataset readiness

Calendar checks pass for SPY and VT across the complete requested window. NIFTY calendar coverage remains WARNING solely for April 24, 2014. All three datasets still have separate extreme-return review flags (SPY 10, VT 10, NIFTY 7); calendar verification does not approve those market moves. No prices, source rows, returns or final-holdout model results were changed.

## Reproduce offline

```powershell
.\.venv\Scripts\python.exe scripts/build_calendars.py
.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --audit
.\.venv\Scripts\python.exe scripts/review_calendars.py
.\.venv\Scripts\python.exe scripts/verify_audit_outputs.py
```

The builder reads only reviewed schedule transcriptions and evidence, never price observations. The audit hashes all declared evidence before execution/cache reuse. `calendar_review.csv` preserves the original historical queue with closure-by-closure source links; `calendar_verification_by_year.csv` contains all asset/year counts; `special_session_review.csv` lists every weekend observation.
