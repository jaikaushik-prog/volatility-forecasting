"""Readable Sprint 1B findings; machine evidence remains in the audit manifest."""
from pathlib import Path


def audit_markdown(result):
    lines = ['# NEXUS Sprint 1B data quality audit', '',
             f"Audit `{result['audit_id']}`; executed {result['audited_at_utc']}.",
             f"Input ingestion run: `{result['input_run_id']}`.", '',
             '**PASS**: checks valid. **WARNING**: manual review required. **FAIL**: unsafe for research; excluded from canonical publication.', '',
             'No raw files or prices were altered. No forward-fill, interpolation, winsorization, mixed-currency series or cross-market calendar join is used.', '',
             '## Asset summary', '',
             '| Asset | Currency | First | Last | Observations | Usable returns | Suspicious returns | Status | Research readiness |',
             '|---|---|---|---|---:|---:|---:|---|---|']
    for item in result['assets']:
        s = item['summary']
        lines.append('| ' + ' | '.join(str(s.get(k, 'unavailable')) for k in (
            'asset', 'currency', 'earliest', 'latest', 'observation_count', 'usable_return_observations',
            'suspicious_return_count', 'validation_status', 'research_ready')) + ' |')
    lines += ['', '## Interpretation and research limits', '',
              'A WARNING is not unconditional research approval. Resolve or explicitly document acceptance of flagged observations and calendar limitations before out-of-sample work. No forecasting or backtest is included.', '',
              'Return usability means mathematically valid on the observed sequence, excluding invalid adjacent prices and confirmed missing sessions. It does not certify unverified historical intervals as single trading sessions. `calendar_interval_verified` records that distinction for every observation.', '',
              'Simple returns use P(t)/P(t-1)-1; log returns use ln(P(t)/P(t-1)). The audit verifies log1p identity and every cumulative prefix within each uninterrupted valid segment. First returns are null. Original stored return errors cause FAIL and are never repaired to pass tests.', '',
              'If a confirmed session is absent, the first subsequent daily return is null in the inspection artifact, with the original interval returns retained in `observed_*` columns and an explicit exclusion reason. This is a documented missing-session policy, not a replacement price. Failed assets are quarantined.', '',
              'All diagnostics, median/MAD flags and annualized volatility are retrospective full-sample descriptions. They must not be fed into out-of-sample forecasts. Annualization is sqrt(configured sessions) times sample log-return standard deviation (ddof=1). USD and INR statistics remain asset-specific.', '',
              'Yahoo adjusted prices are a current-vintage, same-provider reconstruction, not a point-in-time archive or an independent-vendor total-return certification. NSE gross TRI identity is verified against the stored official response field. Historical revisions may still occur.', '']
    if result.get('calendar_limitation'):
        lines += [result['calendar_limitation'], '']
    for item in result['assets']:
        s = item['summary']
        lines += [f"## {s['asset']} ({s['currency']})", '', f"Source: {s['source']}.", '']
        if s.get('failure'):
            lines += [f"**FAIL**: {s['failure']}", '']
            continue
        cal, source = item['calendar_audit'], item['source_audit']
        lines += [f"Convention: `{s['price_convention']}`. Session timezone: `{s['source_timezone']}`.", '',
                  f"Invalid prices: {s['invalid_price_count']}; invalid dates: {s['invalid_date_count']}; duplicate asset-date excess: {s['duplicate_asset_date_excess']}; exact duplicate-row excess: {s['duplicate_rows_excess']}; long gaps: {s['long_gap_count']}.", '',
                  f"Calendar coverage bounds: {cal['verified_start']} through {cal['verified_end']}. Explicit unverified dates inside these bounds: {cal.get('unverified_dates_in_coverage', [])}. Expected sessions in verified coverage, excluding those exceptions: {cal['expected_sessions_verified_period']}; missing: {s['missing_expected_sessions']}; unexpected observed sessions: {s['unexpected_sessions']}. Full-window expected count: {cal['expected_sessions_full_window']} (null means unavailable). Unverified absent weekdays: {s['unverified_absent_weekdays']}; these may be holidays and are not declared errors.", '']
        for url in cal['sources']:
            lines.append(f'- [{cal["calendar"]} calendar evidence]({url})')
        lines += ['', f"Return checks: **{s['return_checks']}**. Source total-return compatibility: **{s['total_return_compatible']}**. Adjustment/identity result: `{source.get('adjustment_check', 'unavailable')}`.", '']
        if 'matched_price_observations' in source:
            lines += [f"Yahoo Adj Close comparison: {source['matched_price_observations']}/{source['compared_price_observations']} prices matched. Distribution events checked: {source['dividend_events_checked']}; factor warnings: {source['dividend_factor_warnings']}; recorded split events: {source['split_events_available']}.", '']
        for limitation in source.get('limitations', []):
            lines.append(f'- {limitation}')
        lines += ['', f"Absolute-return flags: {s['absolute_extreme_return_count']}; all suspicious-return dates: {s['suspicious_return_count']}; stale-price observations: {s['stale_price_observations']}; longest equal-price run: {s['max_consecutive_equal_prices']} observations.", '',
                  '| Descriptive diagnostic | Value |', '|---|---:|']
        for key in ('mean_daily_simple_return', 'daily_log_return_std', 'annualized_historical_volatility',
                    'min_daily_simple_return', 'max_daily_simple_return'):
            value = s[key]
            lines.append(f"| {key} | {'unavailable' if value is None else format(value, '.8f')} |")
        lines += ['', 'Cleaning actions:', '']
        if not item['cleaning_actions']:
            lines.append('- None. Original prices, dates and returns retained exactly; audit annotations added.')
        for action in item['cleaning_actions']:
            lines.append(f"- `{action['code']}`: {action.get('message', action.get('action', ''))}")
        lines += ['', 'Validation notices:', '']
        for notice in item['issues']:
            lines.append(f"- {notice['severity'].upper()} `{notice['code']}`: {notice['message']}")
        if not item['issues']:
            lines.append('- None.')
        lines += ['', 'Visual inspection artifacts:', '']
        for path in item.get('figures', []):
            # Valid from both the top-level report and archived report using absolute local paths.
            lines.append(f'- [{Path(path).name}](<{Path(path).as_posix()}>)')
        lines.append('')
    lines += ['## Reproducibility and evidence', '',
              'The adjacent `data_quality_summary.csv` contains per-asset coverage and descriptive metrics. `suspicious_dates.csv` contains all flagged dates, including unverified calendar absences, reasons, severities and verification actions. Null prices on absent dates are not inserted into canonical time series.', '',
              f"Full audit trail: [audit_manifest.json](<{(Path(result['report_dir']) / 'audit_manifest.json').as_posix()}>). It records source file paths and SHA-256 hashes, original acquisition metadata/timestamps, adjustment-reference metadata, effective thresholds, calendar sources, code hashes, dependency versions and output hashes.", '',
              'Audit IDs depend on input bytes, implementation, configuration and package versions. Repeating the same audit verifies and reuses the same artifacts. No raw file is overwritten; raw hashes are checked before and after execution. Git commit identity is unavailable where the repository has no commit; implementation hashes are the code version.', '',
              'Synthetic pytest fixtures validate the software only; they are not research data and do not establish the quality of real observations. Real-data results above come from the selected saved ingestion run.', '',
              'Run from the repository root:', '', '```powershell',
              r'.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --audit', '```', '',
              'Sprint 1B ends here. No Sprint 1C models or portfolio calculations were implemented.', '']
    return '\n'.join(lines)
