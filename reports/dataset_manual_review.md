# Dataset manual-review worksheet

Based on audit `572f825c852d8c0c540a207e`. Original source datasets remain unchanged.

No confirmed price, duplicate-date or return-formula errors were found by the saved audit. WARNING status reflects statistical return flags and the one remaining NSE calendar question. Flags do not establish that observations are incorrect.

| Asset | Currency | Observations | Invalid prices | Duplicate excess | Return-review dates | Unverified weekday absences |
|---|---|---:|---:|---:|---:|---:|
| SPY | USD | 3730 | 0 | 0 | 10 | 0 |
| VT | USD | 3730 | 0 | 0 | 10 | 0 |
| NIFTY50_TRI | INR | 3677 | 0 | 0 | 7 | 1 |

## Every flagged return date

All 27 flagged asset-date returns were recomputed from the two original source prices. Every value reconciles. This confirms archive/normalization/arithmetic consistency, not independent-vendor accuracy. ETF adjusted closes were also compared with a second Yahoo retrieval; both captures use the same vendor.

The full-period median/MAD rule identifies unusually large moves. The absolute threshold is 10%. These are descriptive flags only. No returns are removed or winsorized.

| Date | SPY simple return | VT simple return | NIFTY TRI simple return |
|---|---:|---:|---:|
| 2015-08-24 | - | - | -5.9149% |
| 2020-03-09 | -7.8094% | -7.8912% | - |
| 2020-03-12 | -9.5677% | -10.2275% | -8.3021% |
| 2020-03-13 | +8.5486% | +7.9649% | - |
| 2020-03-16 | -10.9424% | -11.6411% | -7.5721% |
| 2020-03-18 | - | -6.3690% | - |
| 2020-03-23 | - | - | -12.9146% |
| 2020-03-24 | +9.0603% | +9.1410% | - |
| 2020-03-25 | - | - | +6.6243% |
| 2020-03-26 | +5.8390% | - | - |
| 2020-04-06 | +6.7166% | +6.1306% | - |
| 2020-04-07 | - | - | +8.7629% |
| 2020-06-11 | -5.7649% | -5.6991% | - |
| 2024-06-04 | - | - | -5.8647% |
| 2025-04-04 | -5.8543% | -5.9609% | - |
| 2025-04-09 | +10.5019% | +8.5498% | - |

A dash means the asset/date was not flagged, not that its observation is missing. `return_review.csv` records both prices, source row identifiers and corporate actions.

## Calendar review

The historical review resolves 464 of 465 original asset-date closure flags. All 17 pre-2026 weekend observations have exchange evidence and remain in the dataset. SPY and VT calendar checks pass for 2012 through November 2, 2026. NSE has one explicit uncertainty: April 24, 2014, likely an election closure but still awaiting cash-market exchange evidence. Zero confirmed missing sessions were found.

See [calendar_verification.md](calendar_verification.md) for each year, individual source references and evidence qualifications. `calendar_review.csv` preserves the original historical absence queue with current resolution status; `special_session_review.csv` records every weekend observation.

## Remaining manual review

1. Obtain cash-market exchange confirmation of the NSE closure on April 24, 2014. Its surrounding observed return is preserved but is not marked calendar-verified.
2. Independently corroborate or document acceptance of the 27 flagged market moves. Current source prices and arithmetic agree, but that does not provide independent-vendor verification.
3. Preserve the provenance limitations: current-vintage Yahoo adjustments; no observed ETF splits in this sample; original NSE HTTP-completion timestamps were not separately recorded.

All three datasets remain WARNING / MANUAL_REVIEW_REQUIRED. No forecasting experiments or final-holdout scoring were performed by this review.

Reproduce:

```powershell
.\.venv\Scripts\python.exe scripts/review_dataset_flags.py
```
