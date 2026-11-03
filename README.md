# NEXUS: historical data ingestion and research audit

> **New to this project? Start with [`RESEARCH_HANDOVER.md`](RESEARCH_HANDOVER.md)**: brief-versus-evidence status, research rules, setup and the prioritized open work. The original brief is in [`docs/project_brief.md`](docs/project_brief.md). This README is the detailed stage-by-stage technical reference.

Research infrastructure for NEXUS. This stage imports or downloads source data, normalizes it, validates it and stores separate asset datasets. It does not construct a portfolio or forecast volatility.

Sprint 1B extends the existing Sprint 1A pipeline with an offline research audit. Run it with `--audit`; the [Sprint 1B instructions](#sprint-1b-research-audit) below explain readiness, output files and remaining limitations. Work stops at Sprint 1B.

The default interval is **2012-01-01 through 2026-11-02, inclusive**, matching the latest completed observations downloaded on 3 November 2026. The 2026 data is partial. Change the interval explicitly in `config/ingestion.toml` for another research window.

## Setup

Use Python 3.11 or newer. From the repository root on Windows:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Activation is optional. If the Windows launcher is unavailable, use the full path to a working Python executable. This workspace already has a working environment based on Anaconda. Its original offline setup was:

```powershell
& 'C:\Users\DELL\anaconda3\python.exe' -m venv --system-site-packages .venv
.\.venv\Scripts\python.exe -m pip install --no-index --no-build-isolation -e '.[dev]'
```

The fallback shares installed packages. Prefer the isolated setup above on a new machine with package-index access. On macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Runtime dependencies are pandas, numpy, yfinance, pyarrow and matplotlib. pytest is the development dependency. TOML parsing, the CLI, hashes and metadata use the standard library.

## Run the complete workflow

One command imports the archived real sources, normalizes all three assets, validates them, writes Parquet files and generates reports:

```powershell
.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml
```

The installed entry point is equivalent:

```text
volrisk-ingest --config config/ingestion.toml
```

The default run is offline. Its explicit inputs are the original source snapshots already archived in this workspace:

```text
data/raw/source_snapshots/20261103/
  yahoo/
    SPY_yfinance_raw.parquet
    SPY_metadata.json
    VT_yfinance_raw.parquet
    VT_metadata.json
  nifty/
    provenance.json
    source/
      tri_2012_response.json ... tri_2026_response.json
      tri_2012_request.json  ... tri_2025_request.json
```

These are original downloaded files, not the later Excel/CSV exports. This input archive is git-ignored: retain it with the research project and transfer its metadata too when reproducing a run on another machine. Missing or altered configured inputs cause visible failures; the pipeline never silently uses a previous processed output or switches to another source.

Useful execution options:

```powershell
# Download fresh SPY and VT history for the configured dates.
# The configured local NIFTY source is still imported.
.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --download-etfs

# Select another archive of original yfinance snapshots and metadata.
.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --etf-snapshot-dir C:\research\yahoo-snapshots

# Use official NIFTY CSVs instead of configured JSON responses.
.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --nifty-csv-dir C:\research\official-tri

# Select another NSE JSON archive with its provenance.json.
.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --nifty-json-dir C:\research\nifty-snapshots

# Return a failure status when warnings require review.
.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --fail-on-warning

# Process NIFTY only; ETFs are marked skipped and exit code is 1.
.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --skip-download
```

Exit codes: **0** means all assets published, allowing review warnings; **1** means a failed, missing or skipped asset, or warnings with `--fail-on-warning`; **2** means a configuration or run-level I/O error. Strict-warning runs still preserve data and reports for inspection.

TOML paths resolve relative to the parent of the `config/` directory. CLI directory overrides resolve relative to the current working directory. Empty or omitted `etf_snapshot_dir` selects live downloads; empty or omitted `nifty_json_dir` selects the configured CSV directory. Every manifest records effective settings, including overrides.

## Sources and raw preservation

| Asset | Currency | Normalized price | Source |
|---|---|---|---|
| SPY | USD | Dividend- and split-adjusted Close | Yahoo Finance via yfinance |
| VT | USD | Dividend- and split-adjusted Close | Yahoo Finance via yfinance |
| NIFTY50_TRI | INR | Official gross Total Returns Index level | NSE Indices JSON responses or official CSV |

Live ETF requests use `yfinance.download(auto_adjust=True, actions=True)`, daily bars, `keepna=True`, `repair=False`, `back_adjust=False`, `rounding=False`, and no pre/post-market bars. Start is inclusive and yfinance's end is exclusive: the current window sends `start="2012-01-01", end="2026-11-03"`. Empty results and exceptions receive bounded retries. See the [yfinance download documentation](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html).

`Close` is already adjusted. Do not add dividends again when computing returns from it. Source actions are retained separately; missing action columns are flagged rather than filled with zero. Yahoo can revise adjusted history, so a fresh download can differ from a saved snapshot.

For live ETF downloads, the unmodified returned DataFrame, including its original index and columns, is serialized to raw Parquet before normalization. This preserves yfinance's returned data, not upstream HTTP bytes or unadjusted OHLC. In snapshot mode, the saved Parquet and metadata are copied **byte-for-byte**, and the recorded SHA-256 and price convention are checked.

NIFTY replay copies the original JSON responses, provenance and available request metadata **byte-for-byte**. Response hashes, index identity and declared observation counts are checked. It selects `TotalReturnsIndex`, rejecting price-index and net-return substitutes. Normalized rows retain the original filename and 1-based JSON-array position. Raw JSON remains in its original order.

Yahoo metadata contains retrieval-completion timestamps. The earlier NSE downloader recorded response-file save times, retained separately as `response_saved_at_utc` and, where available, the original `recorded_retrieval_at_utc`. Exact NSE HTTP-completion timestamps were not measured separately and remain null. Import times describe replay, not a new retrieval. Hashes detect changes to archived bytes; they are not provider signatures.

### Official NIFTY CSV alternative

1. Open [NSE Indices Historical Data](https://www.niftyindices.com/reports/historical-data).
2. Select **Total returns Index Values**, **NIFTY 50**, and successive date windows. Download the gross **Total Returns Index**.
3. Keep original exports unchanged in `data/raw/nifty50_tri/` or another directory.
4. Run the CLI with `--nifty-csv-dir` to select that directory.

The importer supports UTF-8/BOM, UTF-16 and CP1252; comma, semicolon or tab delimiters; explicit Date/TRI headers; named-month/ISO dates; and Indian day-first numeric dates. `01/02/2024` means 1 February by default. Set `nifty_date_format = "%m/%d/%Y"` for explicitly month-first files. Generic `Close`, `Price`, net-return-only data and other index identities are rejected. If the export lacks an index-name column, the report says selection must be verified by the importer. Unknown manual download times are not inferred from filesystem modification times.

## Standardized Parquet schema

Every asset's Parquet starts with these same seven columns:

| Column | Definition |
|---|---|
| `date` | Exchange-local daily date, stored as a timezone-naive timestamp |
| `asset` | `SPY`, `VT` or `NIFTY50_TRI` |
| `price` | Auto-adjusted ETF Close or official gross TRI level |
| `daily_return` | Simple return: `price / price.shift(1) - 1` |
| `currency` | `USD` or `INR` |
| `source` | Provider and source-format label |
| `price_convention` | Explicit adjusted-Close or gross-TRI convention |

Returns are decimals: `0.01` means 1%. The first in-window return is null because no pre-window price is used. Missing, invalid or nonpositive prices make that row's return and the following return null. Prices are never forward-filled or interpolated.

Existing supplementary fields remain available: `simple_return` equals `daily_return`, `log_return` is `log(price / previous_price)`, and `return_interval_days` records elapsed calendar days. Source actions and NIFTY row references remain where supplied. `daily_return` is always the requested simple-return series.

Assets remain separate on their own observed calendars. There is no calendar expansion, common-date intersection, FX conversion or mixed-currency portfolio. NIFTY is an INR-based index level, not a tradable security price. If a source omits an entire session, the next return spans consecutive available observations; date-gap diagnostics expose this limitation.

## Validation and outputs

Checks cover source and processed date order, duplicates, invalid dates, missing/nonnumeric/nonfinite prices, zero or negative prices, return consistency, large daily returns, date gaps, unchanged-price runs, date-window coverage and observation counts. Boolean prices are invalid, not interpreted as 0 or 1.

Identical overlaps are explicitly flagged and collapsed only in processed data; original files remain untouched. Conflicting duplicates fail the asset. Structural errors block that asset's processed output while the others continue. Raw evidence and failure details are retained.

Configured review thresholds:

- Absolute simple return greater than 10%.
- Consecutive dates more than 7 calendar days apart.
- At least 3 consecutive observations with an exactly unchanged positive price.
- Fewer than 200 unique observation dates.
- Boundary coverage more than 7 calendar days short of the requested window.

Warnings require inspection, not automatic corrections. Crisis returns are never deleted, clipped or winsorized. Sprint 1A uses a weekday heuristic and does not classify those absences as confirmed missing trading days. Sprint 1B adds bounded official calendar coverage, described below. Special weekend observations are retained.

Each run creates immutable paths:

```text
data/raw/runs/<run_id>/                  Source snapshots and metadata
data/processed/<run_id>/SPY.parquet
data/processed/<run_id>/VT.parquet
data/processed/<run_id>/NIFTY50_TRI.parquet
reports/runs/<run_id>/manifest.json
reports/runs/<run_id>/data_quality.json
reports/runs/<run_id>/data_quality.md
reports/latest.json
```

The Markdown report lists asset name, currency, source, first/last date, observation count, invalid-price count, extreme-return count and status, followed by flagged dates and returns. JSON includes every flagged observation and gap candidate. The manifest records effective configuration, config hash, Python/package versions, implementation-file hashes, source details, retrieval/import times, request parameters, return conventions and raw/processed file hashes.

`reports/latest.json` points to the latest attempt even when it fails. Read only processed paths listed there, or select an older successful run deliberately:

```python
import json
from pathlib import Path
import pandas as pd

run = json.loads(Path("reports/latest.json").read_text(encoding="utf-8"))
if "SPY" in run["processed"]:
    spy = pd.read_parquet(run["processed"]["SPY"])
    print(spy[["date", "asset", "price", "daily_return", "currency"]].tail())
```

## Tests and executed verification

Run the synthetic-data test suite:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-results.xml
```

The environment setting prevents unrelated installed pytest plugins from loading. On macOS/Linux:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q --junitxml=reports/pytest-results.xml
```

Fixtures are small synthetic datasets inside pytest temporary directories. Tests never use the network or place synthetic data in research outputs. Coverage includes formulas, no-fill behavior, independent calendars/currencies, invalid prices, source order, duplicate conflicts, crisis-return retention, gaps/staleness/coverage, raw-byte preservation, hash/identity checks, replay repeatability, CLI exit codes and failure-safe output selection.

The original Sprint 1A suite passed **73 tests**. Its real-data ingestion run succeeded:

| Asset | Currency | First | Last | Observations | Invalid prices | Extreme-return flags |
|---|---|---|---|---:|---:|---:|
| SPY | USD | 2012-01-03 | 2026-11-02 | 3,730 | 0 | 2 |
| VT | USD | 2012-01-03 | 2026-11-02 | 3,730 | 0 | 2 |
| NIFTY50_TRI | INR | 2012-01-02 | 2026-11-02 | 3,677 | 0 | 1 |

All three have review-warning status because of retained large daily moves. NSE's 15 annual source batches also have descending-date warnings; processed dates are ascending and raw order is unchanged. No source trading observation was removed in this run. See `reports/verification.json`, `reports/pytest-results.xml`, and the run referenced by `reports/latest.json`.

The entry point is `src/volrisk/cli.py`. Acquisition, snapshot replay, normalization, validation, reporting and storage are separate modules under `src/volrisk/data/`; automated tests are under `tests/`.

## Sprint 1B research audit

One command audits the selected saved ingestion run, generates per-asset canonical Parquet files, validates source/return/calendar conventions, and writes all reports and 15 figures. It is offline and does not rerun acquisition:

```powershell
.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --audit
```

The default input is the manifest referenced by `reports/latest.json`. Pin the original real-data run explicitly when required:

```powershell
.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --audit --input-manifest reports/runs/20261103T045329099102Z_79120125/manifest.json
```

On a new checkout, install the dependencies above, restore the original source archives and audit evidence, run ingestion once, then run the audit. Saved manifests contain absolute paths: on another machine, replay the source archives to generate a local manifest. Do not hand-edit recorded hashes to force validation. Missing or unverifiable data is reported explicitly; synthetic fixtures are never substituted.

```powershell
# Software checks: all fixtures are synthetic and remain in temporary directories.
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-sprint1b.xml

# Separate real-artifact checks for the current run, including source hashes and
# exact preservation of every existing processed column.
.\.venv\Scripts\python.exe scripts/verify_audit_outputs.py

# Optional: make any review warning fail a CI gate (exit code 1 is expected today).
.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --audit --fail-on-warning
```

Normal audit exit codes: 0 = no FAIL assets (WARNING may remain); 1 = an asset failed, or a warning with `--fail-on-warning`; 2 = invalid/unavailable workflow inputs. A zero exit code does **not** mean unconditional research readiness. Read `research_ready` and `validation_status`.

### Artifacts and idempotence

```text
data/canonical/<audit_id>/{SPY,VT,NIFTY50_TRI}.parquet
data/quarantine/<audit_id>/<failed_asset>.parquet  # when input is inspectable but fails
reports/data_quality.md
reports/data_quality_summary.csv
reports/suspicious_dates.csv
reports/latest_audit.json
reports/audits/<audit_id>/audit_manifest.json
reports/audits/<audit_id>/data_quality.md
reports/audits/<audit_id>/data_quality_summary.csv
reports/audits/<audit_id>/suspicious_dates.csv
reports/audits/<audit_id>/figures/<asset>_<figure>.png
reports/pytest-sprint1b.xml
reports/sprint1b_verification.json
```

The five figure types are normalized price (first valid observation = 100), simple/log return time series, log-return histogram, session-gap summary, and extreme-event windows. Each asset uses its own dates. Event panels show up to the configured limit of the largest flagged moves; the CSV includes every flag.

Audit IDs hash input files, code, effective configuration and installed package versions. An identical rerun verifies and reuses the same artifacts and initial audit timestamp. Changed/missing input bytes cannot reuse an earlier success. Changed cached outputs fail visibly. Reports are published atomically; raw files are read-only. SHA-256 hashes provide integrity relative to the captured files, not cryptographic authentication of a data vendor. Raw evidence and generated datasets/figure archives are git-ignored and must be retained separately.

Existing columns are retained: `date`, `asset`, `price`, `daily_return`, `currency`, `source`, `price_convention`, `simple_return`, `log_return`, `return_interval_days`, plus source-row/action fields. `daily_return` remains an exact alias of `simple_return`. New annotations are `source_timezone`, `calendar_interval_verified`, `return_exclusion_reason`, `audit_status`, `review_reasons`, and `return_usable`.

No price is filled, interpolated, trimmed or winsorized. Source sorting and identical-overlap collapse from ingestion are listed as cleaning actions. Conflicting duplicates fail. The current real-data audit preserves all existing prices, dates and returns exactly. A confirmed missing trading session would exclude the subsequent multi-session interval from canonical daily returns, preserving original values in `observed_daily_return`, `observed_simple_return` and `observed_log_return`. That asset is quarantined until reviewed. Unverified calendar absences do not trigger such exclusions. Incorrect original return values always fail; they are not recomputed to make checks pass.

`return_usable` describes arithmetic validity on the observed sequence, not full historical calendar certification. Calendar uncertainty is separately visible in `calendar_interval_verified`. Currency is preserved per asset; no INR/USD portfolio or calendar inner join is created.

### Numerical and review rules

All rules are configurable in `[validation]` and `[audit]` of `config/ingestion.toml`:

| Check | Current rule |
|---|---|
| Formula, log1p and cumulative reconciliation | Relative tolerance 1e-10; absolute tolerance 1e-12 |
| Absolute extreme simple return | Absolute value greater than 10% |
| Robust log-return outlier | 0.67448975 × absolute deviation / MAD > 8, and absolute simple return >= 3%; at least 30 finite observations |
| Zero MAD | Nonzero median deviation above the same 3% simple-return floor is flagged |
| Reversal | Adjacent opposing moves each >= 8%; absolute sum of their log returns <= 0.02 |
| Stale price | At least 3 consecutive identical positive price observations |
| Split-like discontinuity | Move >= 30%; absolute log move within 0.03 of log(2, 3, 4, 5 or 10), plus recorded split-ratio checks |
| Yahoo adjustment reference | Relative price tolerance 1e-5 and absolute 1e-6; distribution-factor tolerance 1e-4 |
| Long gap | More than 7 calendar days; reliable holiday closures are distinguished from unexplained intervals |
| Historical volatility | Sample log-return standard deviation × sqrt(252) |
| Event plots | Up to 8 largest flagged return dates per asset |

Every cumulative prefix is checked against its price ratio, separately across valid continuous segments. First returns are null. Invalid/missing observations break return calculation; infinity and undocumented missing returns fail. The checks do not change supplied return values.

MAD and descriptive mean, standard deviation, annualized volatility and extrema use the full historical sample solely for audit diagnostics. They must not become future-informed forecast features. A large move or reversal is a review flag, not a declared market-data error.

### Source and calendar evidence

NIFTY identity is verified by parsing the original official JSON `Index Name` and gross `TotalReturnsIndex` fields; `NTR_Value` and the standard price index are not used. The 15 source batches were supplied in descending order; normalized data is ascending and every original response is preserved. NSE response-save times are available, but original HTTP-completion timestamps were not recorded separately.

The existing ETF acquisition uses `yfinance.download(auto_adjust=True, actions=True, back_adjust=False, repair=False, keepna=True)`. The installed `yfinance.utils.auto_adjust` implementation uses the provider's `Adj Close` as adjusted `Close`; normalization and the audit apply no second adjustment. A separate `auto_adjust=False, actions=True` capture contains both `Close` and `Adj Close` plus distributions and splits. This is a current-vintage, same-provider comparison, not independent vendor corroboration or a historical as-of database.

Evidence is preserved in `data/raw/audit_evidence/20261103/`: the two reference Parquet files and retrieval metadata, the inspected yfinance function text, NYSE HTML, three NSE circular PDFs and `calendar_sources.json` with hashes/source URLs and archive times. The one-off evidence capture script is pinned to this date window; it is not part of the offline audit:

```powershell
.\.venv\Scripts\python.exe scripts/collect_audit_evidence.py
```

For a new evidence vintage, explicitly choose a new archive directory/date window and update the configuration. Never overwrite prior research evidence.

The reviewed calendar now covers **2012-01-01 through 2026-11-02**, with one explicit unverified date: **NSE 2014-04-24**. SPY and VT use NYSE/Arca schedules; NIFTY uses NSE cash-market schedules, including later holiday amendments, Muhurat sessions, Budget sessions and special live weekend trading. Early closes remain sessions. Session dates remain exchange-local: America/New_York for ETFs and Asia/Kolkata for NIFTY.

See [the year-by-year calendar report](reports/calendar_verification.md), [asset/year counts](reports/calendar_verification_by_year.csv), [historical absence resolutions](reports/calendar_review.csv), and [weekend-session evidence](reports/special_session_review.csv). The historical review resolved **464 of 465** asset-date absence flags and confirmed all **17** pre-2026 weekend observations. There are zero confirmed missing sessions. NSE April 24, 2014 is likely an election closure, but the recovered circular covers derivatives; cash-market exchange confirmation is still pending. It remains unverified and does not cause a return exclusion. Its surrounding return is not marked `calendar_interval_verified`.

The calendar is compiled from reviewed source transcriptions, never inferred from prices. Downloaded notices and retrieval metadata are preserved under `data/raw/calendar_evidence/20261103/`. Three explicitly labeled web-reader factual transcriptions are used where direct file downloads failed (NYSE 2012-2013, SEC Sandy evidence, NSE MSD60340). A mirrored NSE 2023 circular is corroborated by official clearing evidence. The report describes these qualifications and the exchange annual-report/session confirmations. Original HTTP bytes are not claimed for web-reader transcriptions.

Rebuild and rerun entirely offline:

```powershell
.\.venv\Scripts\python.exe scripts/build_calendars.py
.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --audit
.\.venv\Scripts\python.exe scripts/review_dataset_flags.py
.\.venv\Scripts\python.exe scripts/verify_audit_outputs.py
```

`review_dataset_flags.py` also generates the calendar reports. To regenerate only those reports, run `scripts/review_calendars.py`. The historical review queue is pinned to audit `6b40c1052542abcbb4675b6e`; retain that audit's manifest and suspicious-dates CSV to reproduce its resolution history. The current audit itself does not depend on the previous audit. All calendar evidence paths/hashes are included in the current audit identity and checked before cache reuse. Changed or missing declared evidence fails visibly. The full-window expected-session count remains null if any date in that window is unverified.

Optional public-source acquisition/extraction (not required for offline replay):

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[calendar]"
.\.venv\Scripts\python.exe scripts/collect_calendar_evidence.py config/calendar_sources.json
```

The collector preserves existing source bytes and verifies stored hashes. `config/calendar_sources.json` lists acquired sources used by this review; failed or irrelevant discovery attempts remain in `reports/calendar_source_discovery.json` and the retrieval log. Web-reader factual transcriptions are separate reviewed inputs, not downloads reproduced by this utility. Keep both raw evidence directories and the versioned JSON transcriptions when transferring the project.

### Executed real-data findings and remaining review

The original Sprint 1B suite passed 119 tests. After the historical calendar update, **127 synthetic tests pass** (`reports/pytest-calendar-review.xml`). New checks cover date-specific calendar uncertainty, unaffected windows, genuine missing-session detection, evidence tampering and verification before cache reuse. Separate real-artifact verification checks **143 input hashes**, **21 output hashes**, and exact preservation of every original processed column. Calendar-report reproduction is independent of the software tests.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-calendar-review.xml
```

| Asset | Currency | Coverage | Observations | Usable observed returns | Return-review dates | Verified expected sessions / missing |
|---|---|---|---:|---:|---:|---|
| SPY | USD | 2012-01-03–2026-11-02 | 3,730 | 3,729 | 10 | 3,730 / 0 |
| VT | USD | 2012-01-03–2026-11-02 | 3,730 | 3,729 | 10 | 3,730 / 0 |
| NIFTY50_TRI | INR | 2012-01-02–2026-11-02 | 3,677 | 3,676 | 7 | 3,677 / 0; one unverified date |

All three pass price integrity and arithmetic/log/cumulative return checks, with zero duplicate observations, invalid prices, unexplained long gaps or stale runs at the configured threshold. Both ETFs match the separately captured Yahoo adjusted closes within tolerance at all 3,730 dates. Distribution-factor checks pass for 59 SPY and 57 VT events. Neither ETF has recorded splits in this sample, so actual split-event behavior cannot be empirically verified here. Synthetic tests exercise omitted/double dividend adjustments and split discontinuities.

The strongest absolute-return flags are SPY 2020-03-16 (-10.9424%) and 2025-04-09 (+10.5019%); VT 2020-03-12 (-10.2275%) and 2020-03-16 (-11.6411%); NIFTY 2020-03-23 (-12.9146%). No flagged return has been deleted or corrected. The current `reports/suspicious_dates.csv` contains 27 return-review observations and the one remaining unverified NSE date. The original 465 historical absence flags remain traceable in `reports/calendar_review.csv`, with 464 resolved.

**All three remain WARNING / MANUAL_REVIEW_REQUIRED**, not unconditional research-ready datasets. Remaining work is cash-market evidence for NSE April 24, 2014 and review/acceptance of the 27 flagged market moves. Yahoo vintage revisions and unavailable original NSE HTTP-completion times remain provenance limitations. The 2026 sample ends November 2, not year-end. No Sprint 1C work is included.

### Implementation inventory

Inspected before development: `README.md`, `pyproject.toml`, `.gitignore`, `config/ingestion.toml`, `src/volrisk/config.py`, `src/volrisk/cli.py`, all existing `src/volrisk/data/` modules (acquisition, models, normalization, CSV/JSON parsers, snapshots, storage, validation, reporting and pipeline), existing tests/fixtures, `reports/latest.json`, its ingestion manifest/quality report, original raw metadata/responses, and all three processed Parquet schemas/values.

Added: `src/volrisk/data/{audit,audit_reporting,audit_plots,calendar_audit,return_audit,outliers,source_audit}.py`, `config/calendars.json`, `tests/test_research_audit.py`, `scripts/collect_audit_evidence.py`, and `scripts/verify_audit_outputs.py`.

Modified: `src/volrisk/{__init__,cli,config}.py`, `src/volrisk/data/{models,normalization}.py`, `tests/test_normalization.py` (exchange-local timezone fixture), `config/ingestion.toml`, `pyproject.toml`, `.gitignore`, and this README. The working acquisition, snapshot, parser and ingestion orchestration modules were reused.

### Historical calendar update inventory

Added: `scripts/{build_calendars,collect_calendar_evidence,review_calendars}.py`, reviewed annual/transcription/amendment JSON files under `config/`, historical source archives and the year-by-year reports. Updated the existing calendar/audit/reporting modules to support explicitly unverified dates and hash every declared evidence file. Updated `tests/test_research_audit.py`, the existing review worksheet script, and this README. Original ingestion modules, source prices and return calculations were reused without changes. No forecasting models or portfolio work was added by the calendar review.

## Sprint 2: volatility forecasting research (Stages 1 and 2)

Sprint 2 adds a modular forecasting engine, the historical and GARCH-family model suites, a walk-forward
evaluation engine, statistical model comparison, diagnostics and reports. Portfolio position sizing,
trading strategies and optimization are **not** part of this sprint. Stage 3 (Markov-switching, XGBoost)
was subsequently implemented in Stage 3 below. Stage 4 (stochastic volatility, Heston, HAR-RV,
Realized GARCH) remains documented interfaces only; see `experiments/advanced/README.md`.

### Forecast quantity and conventions

Every model forecasts the **next-session conditional variance of the daily log return in decimal units**
(1% = 0.01, variance 1e-4) at a one-session horizon. Annualized volatility = `sqrt(variance_daily * 252)`;
both values are stored. Models are estimated on `log_return` from the canonical datasets referenced by
`reports/latest_audit.json`; `simple_return` is carried separately for later portfolio work and never
mixed into the variance evaluation. Only rows with `return_usable = True` are used; nothing is filled.
GARCH models use a zero conditional mean, returns scaled by 100 for optimization (forecasts converted
back to decimal units), a rolling 1000-session window (minimum 500), and re-estimation every 21 sessions
with the variance state advanced by the model's own recursion between refits.

### Layout

```text
src/volrisk/forecasting/      base.py (interface, FitReport, record schema), registry.py, historical.py,
                              ewma.py, garch.py, regime_switching.py, stochastic_volatility.py,
                              realized_volatility.py, ml.py
src/volrisk/evaluation/       walk_forward.py, metrics.py, diagnostics.py, reporting.py, experiment.py
src/volrisk/data/returns.py   canonical dataset -> estimation (log) and portfolio (simple) return series
src/volrisk/forecast_cli.py   `volrisk-forecast` / `python -m volrisk.forecast_cli`
config/forecasting.toml       data, splits, walk-forward, evaluation, model and experiment definitions
experiments/{baseline,econometric,advanced}/   READMEs; runs/<run_id>/ outputs (git-ignored)
reports/model_comparison.md, model_metrics.csv, statistical_tests.csv, regime_metrics.csv,
reports/parameter_stability.csv, pairwise_dm.csv, figures/<asset>_*.png, research_findings.md
```

### Walk-forward protocol

At origin session t the model receives returns through t, is re-estimated if a refit is due (otherwise
its state is updated with r_t), forecasts the variance of session t+1, and the forecast is persisted
with asset, model, version, origin and target dates, parameters, training window, fit status and
runtime before r_{t+1} is read. Failed estimations are recorded as missing forecasts and retried at the
next session; no other model is substituted. Splits are assigned by target date: development 2012–2021,
validation 2022–2024, final holdout 2025-01-01..2026-10-30. The holdout is **sealed** by default
(observations excluded before fitting, forecasting and diagnostics); `--include-holdout` explicitly
unseals it. This enforcement was corrected in Stage 3; see the earlier-exposure limitation below. Metrics
are reported for all available forecasts and for common dates on which every model has a valid
forecast. The first forecasts appear after 252 valid returns (benchmarks) and 500 (GARCH family).

### Commands

```powershell
# Stage 1 benchmarks
.\.venv\Scripts\python.exe -m volrisk.forecast_cli --config config/forecasting.toml run --experiment baseline --workers 4
# Stage 2 full comparison (publishes tables and figures to reports/)
.\.venv\Scripts\python.exe -m volrisk.forecast_cli --config config/forecasting.toml run --experiment econometric --workers 4
# Registry and Stage 4 data gates
.\.venv\Scripts\python.exe -m volrisk.forecast_cli list-models
.\.venv\Scripts\python.exe -m volrisk.forecast_cli data-check
# Tests (synthetic data only)
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-forecasting.xml
```

Runtime dependencies added: `scipy` and `arch`. `xgboost`/`scikit-learn` are an optional `[ml]` extra for
Stage 3. Each run manifest records the configuration hash, model metadata, data provenance (audit id,
Parquet hashes), package versions, seed and output hashes.

### Evaluation

QLIKE = log(h) + r²/h (lower is better; only for strictly positive finite h), variance MSE and MAE,
calibration ratio (mean r² / mean h), bias, estimation failure and non-convergence rates, forecast
stability (mean |Δ log h|) and runtime, per asset, period and sample. Squared daily returns are a noisy
proxy of the latent variance, so models are compared on identical dates with HAC Diebold–Mariano tests
and a stationary block bootstrap, Holm-adjusted for the number of comparisons against the benchmark.
Ex-ante volatility regimes (terciles of trailing 60-session variance relative to its own past) are
distinguished from retrospective labels (shock sessions, post-shock recovery, named event windows).
Results and commentary: `reports/model_comparison.md` and `reports/research_findings.md`.

## Stage 3: filtered Markov switching and XGBoost

Stage 3 adds two forecasters to the existing registry and reuses the walk-forward, failure-recording,
evaluation and plotting architecture. All ten Stage 1/2 comparators are rerun on the same eligible
data and all twelve models are compared on identical observed target sessions within each asset.
The outputs are separate from the archived Stage 2 reports.

### Setup and execution

Run from the repository root. Existing installations can use the final install command directly.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev,ml]"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-advanced.xml
.\.venv\Scripts\python.exe -m volrisk.forecast_cli --config config/forecasting.toml run --experiment advanced --workers 4
.\.venv\Scripts\python.exe scripts/verify_advanced_outputs.py
```

This uses existing audited local data; it does not redownload or change prices. Install the optional
`[ml]` dependencies for XGBoost, or disable it independently in the TOML model/experiment list.
`--max-origins 65 --bootstrap-draws 20 --no-figures --no-publish` provides a smoke run, not research evidence.
The final holdout is excluded by default. Do not use `--include-holdout` during model development.

### Model definitions

- **Markov switching:** two Gaussian zero-mean variance states, past-only maximum likelihood through
  statsmodels, two deterministic initializations, minimum 500 observations, a rolling 1000-observation
  window and refits every 21 sessions. States and transitions are reordered by ascending variance.
  Forecast = `filtered_probabilities @ transition_matrix @ state_variances`, with transition rows
  representing the current state. Between refits, the log-space Hamilton filter incorporates each
  new return. No smoothed state enters a forecast; EM can smooth inside the past-only fitting window.
  Convergence, weak separation/occupancy, transition boundaries and variance changes are recorded.
- **XGBoost:** predicts the conditional mean of next-session squared decimal log return with Tweedie
  regression (power 1.5, log link). Targets are scaled by 10,000 then converted back. Zero targets are
  supported; all-zero training samples fail. A configurable positive variance floor is recorded per
  prediction, while invalid predictions fail. This avoids naive exponentiation of a log-target model.
  Thirteen causal daily-return features include historical variance, EWMA, absolute/squared returns,
  negative-return indicators, variance differences and log drawdown. These are not intraday RV.
  At origin t, the last training pair is features at t-1 and the observed label r_t squared. A rolling
  window holds up to 1500 labelled pairs; model weights refit every 21 sessions. Three prespecified
  depth/tree-count candidates use two chronological 60-session folds, with retuning no more often
  than every 252 sessions and only through development end. Selected settings freeze for validation.
  Each asset has its own estimator and tuning history; CPU trees use one thread and seed 20261103.

Dynamic filter probabilities/features/clipping are saved in `model_state`; fitted parameters and
configuration remain separate. Split gain is reported per fitted booster and averaged across refits;
it is training-set importance, not a causal claim. Parameter/weight updates during validation use
only information already available at each origin, with no validation-driven hyperparameter tuning.

### Protocol corrections and limitations

The old Stage 2 code excluded holdout rows from summary metrics only: it generated holdout forecasts
and losses and published fit diagnostics, and its research narrative discussed those failures.
Stage 3 now enforces the cutoff in the canonical loader before models and diagnostics see returns.
This prevents new exposure but cannot undo prior exposure. The original holdout is therefore **not
historically pristine**; final confirmation needs subsequently unseen data or a new predeclared holdout.

The loader verifies canonical hashes against the audit manifest, numerical return checks and source
conventions. All three archived datasets retain extreme-return review warnings. NIFTY's 2014-04-25
return crosses an interval with unresolved calendar verification; Stage 3 excludes that interval
and resets training after the gap without changing source/canonical files or inventing prices.
It also resets all models after any invalid/missing return. Baselines are rerun under this policy;
the NIFTY sample is not directly interchangeable with the previous Stage 2 table. Native calendars
and INR/USD identities remain separate. Current-vintage adjusted prices are not point-in-time snapshots.

Validation 2022-2024 is the main model-selection comparison. Development results include tuning and
are exploratory. Squared log returns are noisy variance proxies under the zero-mean convention.
QLIKE, MSE, MAE, calibration, bias, stability, runtime and failures are reported per asset. Matched-date
loss tables retain failure counts/runtime from all attempted origins in the period, preventing
failed fits from disappearing with the comparison-date filter. Tests against GARCH-normal use HAC
DM and stationary block-bootstrap uncertainty with Holm adjustment; intervals are pointwise and
do not account for every possible research choice. All-pair DM p-values have their own Holm family.

### Outputs and provenance

Requested reports: `reports/advanced_model_comparison.md`, `advanced_model_metrics.csv`,
`regime_analysis.md`, `xgboost_features.md`. Supporting reports contain paired tests, regime metrics,
refit stability, shock responses, filtered states, feature gain and chronological tuning boundaries.
Figures are published under `reports/figures/advanced/`. `reports/latest_advanced.json` points to the
immutable run in `experiments/advanced/runs/`, with all forecasts, fits, all/common-date indicators,
effective settings, seeds, package versions, data/config/code/output hashes and retrieval provenance
via the referenced source audit. Runtime is measured, so reruns need not be byte-identical; numerical
forecasts and model choices are reproducible in the same environment. Synthetic fixtures are only tests.

At Stage 3 completion, Stage 4 interfaces remained pending. No portfolio sizing, strategies,
optimization, Heston, HAR-RV, LSTM or Transformer was implemented or run by Stage 3.

The run-specific interpretation is in `reports/advanced_research_findings.md`. Additional raw
NIFTY/SENSEX minute-price and India VIX files are present but not audited or used in Stage 3.
The older filename-only `data-check` does not verify schemas (it can misidentify VIX as an options
surface or miss `1min` filenames); do not use its boolean availability flag as a data certification.

## High-frequency data integration

The separate intraday pipeline audits the supplied NIFTY, SENSEX and India VIX CSVs,
preserves raw bytes and publishes Parquet bars and daily realized-volatility features.
The source vendor, instrument identity, original timezone and bar labels are unknown.
**Outputs are provisional, with `research_ready=False`; they are not certified inputs
for forecasting experiments.** Asia/Kolkata and start-labelled OHLC bars are working
assumptions. Minute NIFTY is a spot-index candidate, never substituted for daily NIFTY TRI.
The pickle is never deserialized. The daily ingestion/forecasting modules are unchanged.

From the repository root, setup (if not already installed) and execution:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-intraday.xml
.\.venv\Scripts\python.exe -m volrisk.intraday_cli --config config/intraday.toml
.\.venv\Scripts\python.exe scripts/verify_intraday_outputs.py
```

The CLI also installs as `volrisk-intraday`. `--no-figures` produces a distinct run
without plots. It never downloads or substitutes missing source files. Configuration
is in `config/intraday.toml`; bounded NSE/BSE schedules and cited evidence are in
`config/intraday_calendar.json`, with the existing NSE calendar evidence reused.

Published datasets:

- `data/processed/intraday/{nifty,sensex,india_vix}.parquet`: sorted, unique minute
  observations with source row/hash, timezone-aware timestamps, availability times,
  price/session validity and anomaly flags. Original prices remain visible.
- `data/processed/intraday/{nifty,sensex}_{5,10,15}min.parquet`: non-overlapping
  OHLC bars with duration, completeness and availability; incomplete bars are missing.
- `data/processed/features/{nifty,sensex}_realized_vol_daily.parquet`: daily measures,
  missing-session rows, coverage, provenance and causal RV features.
- `data/processed/features/nifty_vix_features_daily.parquet`: end-of-day available
  VIX, lag/change/rolling/percentile features and explicitly scaled RV comparisons.

Reports: `reports/intraday_data_audit.md`, `realized_volatility_summary.md`,
`intraday_session_quality.csv`, `intraday_feature_coverage.csv`, per-asset session issues,
frequency/stress statistics and `reports/figures/intraday/`. Exact flagged/quarantined
rows are in the immutable run's `audit/` folder. `reports/latest_intraday.json` identifies
the run in `data/processed/intraday_runs/`, including input/code/output hashes, versions,
import timestamps, schemas, assumptions and cleaning actions. Identical runs verify and
republish the same artifacts. Changed inputs/config/code create a new run; incomplete
runs are never published or silently overwritten.

### Intraday measurement and feature contract

Raw duplicate timestamps with identical market fields retain one deterministic copy;
all conflicting copies are quarantined. Invalid OHLC/prices, off-minute timestamps,
outside-session observations and suspicious returns are flagged. Extreme returns are
not deleted or winsorized. Whole-sample MAD is retrospective QC, never a model feature
or a deletion rule. No price interpolation, timestamp rounding or forward filling occurs.

Bars start at each continuous-session segment's opening time and become observable at
their end. A regular session is 375 minutes; 10-minute aggregation retains a labelled
5-minute final interval. No interval spans an exchange break. Each segment's price path
starts with its first observed open and continues through sampled closes. Thus the first
open-to-close return contributes to intraday RV. Complete-session RV requires **100%**
valid expected minutes; incomplete and unverified sessions have missing RV, not zero.
Short special sessions are retained with their actual duration, not scaled to full days.

`rv_{1,5,10,15}min` is sum of squared intraday **log** returns in decimal-return squared
units. `realized_vol_*` is its square root; annualized volatility is `sqrt(252 * RV)`.
Scheduled-break reopening returns are separate; `full_session_rv_*` adds their squares.
`full_rv_proxy_*` adds overnight squared return. Overnight/c2c returns require adjacent
known session endpoints; they may cross a verified holiday/weekend but never an absent
or unverified candidate session. Valid endpoints can support overnight returns even when
the interior of the prior day is incomplete. Semivariances split RV by return sign.
Five-minute bipower variation and `max(RV-BPV, 0)` are descriptive jump proxies, not
formal jump tests. Minimum interval count and equal spacing within segments are enforced.

Expected/candidate session rows are retained so missing days break lagged 5/22-session
windows. RV features suffixed `_lag1` use only earlier sessions. Current realized measures
and VIX features are available at `feature_origin_timestamp` (the session close). A future
forecaster must predict the following session; it must not use current RV to predict itself.
Volatility of volatility is the 22-session sample standard deviation of lagged `sqrt(RV)`.
Both observed and lagged overnight/intraday risk shares are explicit columns.

VIX is separate implied volatility, never NIFTY RV. A VIX bar must be available at/before
the NIFTY close, on the same session, no older than 90 seconds, and pass OHLC/session
checks. Missing observations stay missing. VIX percentage points / 100 produce annualized
decimal volatility. India VIX concerns about 30 calendar days forward; trailing full RV
uses 22 trading sessions. For a comparable-unit diagnostic, annualized variance × 30/365
is recorded for each, assuming 252 sessions/year and linear variance accrual. Horizons
and forward/backward information still differ; this is not an identified risk premium.
VIX percentiles use strictly earlier observations (252-session window, minimum 60 valid).

Numerical completeness is separate from verified provenance. Review the audit's remaining
special-session calendar gaps and questionable observations before research use. Historical
2025–2026 inspection here is descriptive and does not restore an untouched forecast holdout.
No HAR-RV, XGBoost, volatility forecasting, position sizing or trading is run by integration.

## Stage 4 — provisional HAR-RV and India VIX forecasting

Stage 4 reuses the completed intraday artifacts; **do not rerun ingestion to run forecasts**.
The user confirmed NIFTY as an NSE spot-index series (reported source: NSE). Export documentation,
timezone and bar labels remain unconfirmed. All real-data results are **PROVISIONAL**; numerical
checks do not certify provenance. The source audit and raw files remain immutable.

```powershell
# Existing environment already has all required numerical packages.
# Fresh setup, if needed: .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-har-rv.xml
.\.venv\Scripts\python.exe -m volrisk.har_cli --config config/har_rv.toml check
.\.venv\Scripts\python.exe -m volrisk.har_cli --config config/har_rv.toml run
.\.venv\Scripts\python.exe scripts/verify_har_outputs.py
.\.venv\Scripts\python.exe scripts/summarize_har_results.py
```

The installed CLI is `volrisk-har`. `--no-figures` omits plots and creates a separate run.
There is no holdout-unsealing option. `check` only publishes readiness/coverage information;
it never estimates a model. Critical hash, schema, numerical or temporal failures produce
blocker reports and no empirical comparisons. Provisional source conventions are allowed
only because `allow_provisional=true` explicitly records the authorized research protocol.

### Targets, models and timing

The primary target is next-session NIFTY 5-minute **intraday realized variance**, in decimal
log-return squared units. The secondary target adds the next session's squared overnight
log return. It excludes scheduled-break reopening squares, so it intentionally differs from
the integration module's `full_rv_proxy_*` on split sessions. Neither target is squared
close-to-close return. Targets, assets, sampling frequencies and exclusion scenarios retain
separate rankings. Annualized forecast volatility is `sqrt(252 * forecast_variance)`.

Five fixed HAR specifications are implemented in `src/volrisk/forecasting/har.py`:

| Name | Specification |
| --- | --- |
| `har` | Levels OLS: RV at origin, arithmetic 5-session mean, arithmetic 22-session mean |
| `log_har` | Log target and logs of the same arithmetic RV averages; training-residual smearing |
| `har_overnight` | Levels HAR plus overnight square and its 5/22-session arithmetic means |
| `har_vix` | Levels HAR plus prior-session annualized India VIX implied variance |
| `har_vix_overnight` | Levels HAR plus both predictor groups |

VIX feature at origin t is `(VIX_EOD_(t-1) / 100)^2`: an **additional full-session lag**
because EOD timing conventions remain unconfirmed. The lag does not resolve timezone or
source uncertainty. Original observations must pass same-session timestamp/age checks.
Missing VIX remains missing; the VIX experiment cannot extend beyond source availability.
Annualized implied variance describes approximately 30 calendar days, and its regression
coefficient is estimated. It is not directly equated with one-day RV. Overnight predictors
use only already-observed overnight returns through the forecast origin.

Default HAR fits use a 500-session-position rolling window, at least 126 completed
supervised pairs and refits every 21 sessions. All variants share identical training rows
within each asset/target/frequency/scenario, using the union of required predictor availability.
Between refits, only the observable origin features change. Missing rows remain in the calendar
and break rolling windows; they are not compressed out. OLS standardization is learned in the
training sample. Rank, condition number, coefficients and training target dates are retained.

The transformation/prediction floor is `1e-6 * median(positive training targets)`, learned at
each refit. Zero observed variances remain zero in evaluation. Log-HAR uses the training-only
smearing factor `mean(exp(training log residuals))`; its constant residual-distribution assumption
is a limitation. Raw predictions and every floor application are stored. Nonfinite/explosive
forecasts and failed fits remain missing; no other model substitutes for them.

Realized benchmarks use the previous observed target, its 5/22-session mean, and EWMA of
observed variance with lambda .94 and initialization at the first 22-session mean. They do
not calculate the variance of the RV series. A separate 5-minute-feature comparison fits
HAR to **spot close-to-close squared returns** and reuses daily-return EWMA, GARCH, EGARCH
and GJR-GARCH on that same outcome. These use the same minute-derived spot closes, not NIFTY
TRI. GARCH has a 252-return minimum, 500-session window, 21-session refits, zero mean and
100× scaling converted back to decimal variance. Nonconverged fits are explicitly rejected.
Missing daily returns reset filtering; insufficient contiguous history can leave a panel empty.

### Eligibility, evaluation and robustness

Only complete, valid, verified-schedule intraday sessions supply RV. Complete special sessions
retain their native duration; they are not extrapolated to full days. The basic HAR has no
duration regressor, a stated specification limitation. Overnight returns need adjacent valid
endpoints. A separate exclusion sensitivity removes sessions with absolute-return flags or at
least ten unchanged-price minutes, without changing source data. These flags can reflect real
crises. Whole-file MAD flags are not used because their thresholds used the full source sample.

Development is 2022–2023, validation 2024, and the existing 2025–2026 holdout stays sealed.
Only data through validation end are loaded numerically, with a second cutoff inside the engine.
No hyperparameter search occurs. Earlier project outputs had exposed parts of the historical
holdout; sealing this workflow cannot make it historically pristine. Final confirmation needs
a genuinely unseen predeclared period.

Metrics retain all attempted forecasts and a separately identified common-date sample.
Only common-date metrics receive QLIKE/calibration rankings. Calibration is mean observed /
mean predicted variance. Forecast stability uses adjacent valid origins; estimation failures,
prediction failures, warm-up and floored outputs are separate. Paired HAC loss tests respect
native session-position spacing; stationary bootstrap blocks restart at missing-session gaps.
Holm adjustment covers all predeclared validation comparisons, including robustness panels.
Intervals are approximate and pointwise; nested models and small samples limit inference.

Sensitivity repeats 1/5/10/15-minute targets separately and compares frequencies on common
dates without pooling their loss scales. Exclusion scenarios are also compared on their date
intersection. SENSEX is a secondary sample using HAR, log-HAR and HAR+overnight; NIFTY-based
India VIX is not silently treated as SENSEX implied volatility. Origin-known regimes are kept
separate from retrospective shock/recovery labels and diagnostic risk buckets.

### Stage 4 artifacts

`reports/latest_har_rv.json` points to `experiments/har_rv/runs/<content_hash>/`.
The run contains source/config/code/version provenance, the predeclared protocol,
prepared pre-holdout panels, all/common forecasts, fit diagnostics, and an issuance JSONL
written before each target outcome is attached. Issuance timestamps are a historical-simulation
convention (origin close plus one microsecond), not actual historical publication evidence.
Repeated identical runs verify and reuse artifacts; changed inputs/config/code create a new run.

Published reports: `har_rv_research.md`, `har_rv_model_comparison.csv`,
`vix_incremental_value.md`, `overnight_risk_analysis.md`, `forecast_readiness.md`,
`har_rv_sample_sizes.csv`, `har_rv_exclusions.csv`, `har_rv_statistical_tests.csv`,
`har_rv_regime_metrics.csv`, `har_rv_parameter_stability.csv`, `har_rv_sensitivity.csv`,
`har_rv_frequency_sensitivity.csv`, and `figures/har_rv/`.

The supplementary `har_rv_findings.md` interprets the saved validation results, including
negative raw VIX-model predictions, forecast availability and event concentration.
`har_rv_floor_events.csv` lists floored predictions. `NIFTY_core_qlike_detail.png` displays
the non-VIX subset relative to HAR; the original all-model plot retains the full loss scale.
`scripts/summarize_har_results.py` generates these without fitting models or reading holdout
data and records separate output hashes in `har_rv_findings_manifest.json`.

No portfolio position sizing, trading, execution, Heston, LSTM or Realized GARCH is added.

## Stage 4B — exploratory positive-link VIX research

Stage 4B preserves historical Stage 4 results and uses only its saved NIFTY 5-minute
panel through 2024. Do not rerun ingestion or the old Stage 4 publication command for
this follow-up. The original implementation is preserved in
`experiments/stage4b/stage4_code_snapshot/`; the new run checks historical artifact hashes.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-stage4b.xml
.\.venv\Scripts\python.exe -m volrisk.stage4b_cli --config config/stage4b.toml
.\.venv\Scripts\python.exe scripts/verify_stage4b_outputs.py
```

The installed entry point is `volrisk-stage4b`. There is no holdout evaluation option.
Repeated identical runs verify and reuse their immutable artifacts. Changed code,
configuration, dependencies or source hashes create a different run ID.

`forecasting/positive_har.py` adds Log-HAR+VIX, Log-HAR+VIX change and Ridge Log-HAR+VIX
alongside the existing Log-HAR, standard HAR and RV-EWMA benchmarks. VIX remains a
full native session behind the forecast origin; the change is the signed difference
between two adjacent lagged log implied variances. Missing values break that feature.
Every regression uses the same completed training pairs and the existing 21-session
refit schedule. A 500-position window and minimum 126 pairs are retained.

New log models use an exponential link and training-residual smearing, with no prediction
floor. Exactly zero RV values use a training-derived replacement only inside log
transformations. Positive small values are not clipped. Invalid IV, underflow, overflow
and excessive variance forecasts are recorded as failures, not silently replaced.
The original unsuccessful levels HAR+VIX forecasts remain an archived comparator.

Ridge minimizes standardized-predictor SSE plus `alpha * sum(slopes**2)` with an
unpenalized intercept. The four fixed strengths `[0.1, 1, 10, 100]` are selected separately
for each target using chronological September–October and November–December 2023 blocks. Scaling, zero handling
and smearing use each origin's training sample only. Selection uses equal fold-mean
QLIKE, at least 30 common observations per fold, no unexpected failures, and a larger
alpha only for an exact tie. No 2024 losses enter alpha selection. Initialization before
the evaluation boundary creates no saved final-model forecasts; configuration-availability
dates prevent retrospective claims of issuance before hyperparameter selection.

The initial Q3/Q4 split failed the fixed 30-per-fold gate (15/61 usable observations).
That aborted registration is preserved. Before any new 2024 results, the boundaries were
amended using coverage only, yielding 35/41 observations; the grid and minimum stayed fixed.
This small development sample makes Ridge selection uncertain. Both fold designs and the
four aborted primary-target grid runs are disclosed in the configuration and reports.

`data/stage4b_dataset.py` verifies the saved panel and VIX availability. New evaluation
modules `stage4b.py`, `stage4b_experiment.py`, `stage4b_reporting.py` and `vix_diagnostics.py`
reuse the existing model interface, walk-forward engine, metrics, HAC and bootstrap tools.
The engine's optional feature-builder/emission hooks preserve the original default behavior.
No daily-return or intraday ingestion implementation was changed.

Outputs include `vix_model_diagnostics.md`, `positive_vix_models.md`,
`stage4b_comparison.csv`, `frozen_forecasting_protocol.md`, plus separate tuning,
coefficient, feature-correlation, extrapolation, floor-sensitivity, sample-alignment,
regime/quarter and paired-test CSVs. Forecasts, coefficients, training dates and an
issuance-before-outcome ledger are saved under `experiments/stage4b/runs/` with a code
snapshot and manifests. `reports/latest_stage4b.json` points to the completed run.

The registered family has 18 distinct model/target configurations (including eight
development Ridge candidates), 12 final comparison cells, ten formal paired contrasts,
and five diagnostic legacy-floor counterfactuals. Quarter and regime slices are descriptive.
Holm adjustment covers the ten loss comparisons across both targets; a statistical flag
requires both HAC and gap-aware bootstrap checks. This does not account away the earlier
research-driven choice of specifications.

All results are **PROVISIONAL / EXPLORATORY**. The same 2024 sample influenced this work;
it cannot provide independent confirmation. Vendor/export, original timezone and bar
conventions remain unverified. Earlier project work exposed some 2025–2026 observations,
so those dates are not a pristine holdout. The frozen protocol specifies a new prospective
collection period after verification and registration; it is not executed here.

## Stage 5 — exploratory economic value

The separate `volrisk.economics` package adds forecast-to-holding-period alignment,
event accounting, bounded long-only inverse-volatility policies, development-only
matched exposure/risk benchmarks, costs/cash scenarios, economic metrics, paired
stationary-bootstrap uncertainty and reconciled P&L attribution. The frozen
prospective forecasting protocol and historical experiment artifacts are preserved.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-stage5.xml
.\.venv\Scripts\python.exe -m volrisk.stage5_cli --config config/stage5.toml register
.\.venv\Scripts\python.exe -m volrisk.stage5_cli --config config/stage5.toml run
```

No new dependencies are required beyond the existing environment. For a fresh
environment, use the setup commands above (`python -m pip install -e ".[dev]"`).
The module CLI also works without reinstalling the new `volrisk-stage5` entry point.

The empirical Panel A is **PROVISIONAL / EXPLORATORY / NON-EXECUTABLE NIFTY TRI**.
It is not an ETF result or realized profit. NIFTYBEES source checks found omitted
special sessions and incomplete corporate-action metadata. The bounded raw files
and eight official exchange checks are preserved, but they are not silently patched
into an executable backtest. Panel B remains blocked pending verified adjusted OHLC,
actions, availability and instrument-risk alignment.

Primary timing is after-close signal t, execution at t+1 close, first holding return
ending t+2. Thus the forecast is for that future **daily** interval (horizon2), not
the sum of two daily variances. Delay sensitivity uses horizon3. Daily-target HAR,
Log-HAR and Log-HAR+VIX are new economic-study specifications, not unchanged Stage4B
intraday candidates. Cash0% and costs5/10/20bps are scenarios. No leverage, shorts,
live trading or changes to fund holdings are implemented.

Only numerical observations through2024 enter the run. A disclosed initial report
inspection exposed some later-period rows; see the immutable Stage5 registration.
They do not enter the experiment. 2024 is repeatedly inspected and all economic
findings are exploratory. No2025–2026 evaluation is performed.

Outputs are `reports/position_sizing_experiment.md`, `economic_model_comparison.csv`,
`exposure_attribution.md`, `trading_cost_sensitivity.md`, `forecast_vs_economic_value.md`
and `reports/figures/stage5/`. `reports/latest_stage5.json` identifies the immutable
completed run under `experiments/stage5/runs/`, including entry events, every net and
zero-cost shadow ledger, forecasts, sources/config/package hashes and statistical
comparisons. Identical completed runs are verified and reused; interrupted runs are
retained and never reported as complete. See `experiments/stage5/README.md`.

## Stage 6 — economic failure diagnosis (read-only)

Stage 6 explains why the Stage 5 volatility-targeting overlays underperformed buy-and-hold in 2024. It reads only the
saved Stage 5 run (hash-verified before and after), simulates no new allocation rule, refits no model, executes no
trade and reads no observation after 2024-12-31. The terminal-wealth decomposition reconciles exactly to Stage 5.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q tests/test_stage6_diagnosis.py --junitxml=reports/pytest-stage6.xml
$env:PYTHONPATH = 'src'; .\.venv\Scripts\python.exe -m volrisk.stage6_cli run
```

Outputs: `experiments/stage6/runs/<id>/` (tables, figures, manifest), `reports/latest_stage6.json`,
`reports/figures/stage6/`, and the reports `stage6_failure_analysis.md`, `stage6_research_inferences.md`,
`next_hypotheses.md` and `research_go_no_go.md`. The hypotheses are designs only; none has been backtested.

## H4 — advisory volatility risk monitoring (DRAFT, not frozen)

Draft registration, alert specification and prospective evaluation protocol for an advisory risk-alert system
(NORMAL / ELEVATED / CRITICAL). No trading, position reduction or reallocation capability exists. Prospective
collection is refused until the protocol is frozen and registered.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m volrisk.monitoring_cli validate
.\.venv\Scripts\python.exe -m volrisk.monitoring_cli draft-thresholds   # development-only data
```

Documents: `reports/h4_registration_draft.md`, `reports/h4_alert_specification.md`,
`reports/h4_prospective_evaluation_protocol.md`; config: `config/h4_monitoring.toml`; draft outputs: `reports/h4_draft/`.
