"""Offline Sprint 1B audit of immutable Sprint 1A manifests and snapshots."""
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

import numpy as np
import pandas as pd

from volrisk.data.calendar_audit import audit_calendar
from volrisk.data.models import ASSETS, DataError, NormalizedData
from volrisk.data.outliers import detect_outliers
from volrisk.data.pipeline import _versions
from volrisk.data.return_audit import audit_returns
from volrisk.data.source_audit import audit_source
from volrisk.data.storage import sha256, write_json, write_parquet, write_text
from volrisk.data.validation import validate

EVENT_COLUMNS = ['Asset', 'Date', 'Price', 'Simple return', 'Log return',
                 'Reason flagged', 'Severity', 'Suggested verification action']
RANK = {'PASS': 0, 'WARNING': 1, 'FAIL': 2}
RETURN_FLAGS = {'absolute_return', 'median_MAD_outlier', 'zero_MAD_deviation',
                'large_two_observation_reversal', 'split_like_jump',
                'possible_split_adjustment_error', 'possible_missing_dividend_adjustment',
                'possible_double_dividend_adjustment', 'adjustment_reference_mismatch',
                'dividend_factor_inconsistency', 'return_identity_failure'}


def _number(value):
    return float(value) if pd.notna(value) and np.isfinite(value) else None


def inspect_asset(frame, entry, asset, settings, calendar_document):
    """Keep supplied values; only exclude returns spanning confirmed missing sessions."""
    frame = frame.copy().reset_index(drop=True)
    required = {'date', 'asset', 'price', 'currency', 'source', 'price_convention',
                'simple_return', 'log_return', 'daily_return'}
    if not required <= set(frame):
        raise DataError(f'Missing columns: {sorted(required - set(frame))}')
    if not pd.api.types.is_datetime64_any_dtype(frame['date']):
        raise DataError('Canonical dates must have datetime dtype')
    if frame['date'].dt.tz is not None or not frame['date'].dropna().eq(frame['date'].dropna().dt.normalize()).all():
        raise DataError('Stored session dates must be naive, exchange-local midnight labels')
    for col in ('price', 'daily_return', 'simple_return', 'log_return'):
        if not pd.api.types.is_numeric_dtype(frame[col]) or pd.api.types.is_bool_dtype(frame[col]):
            raise DataError(f'{col} must have a numeric, non-boolean dtype')
    events = {}

    def flag(position, reason, severity, action):
        if isinstance(position, (int, np.integer)):
            row = frame.iloc[position]
            stamp = row['date']
            key = stamp.strftime('%Y-%m-%d') if pd.notna(stamp) else f'invalid-row-{position}'
            values = [_number(row[c]) for c in ('price', 'simple_return', 'log_return')]
        else:
            key, values = str(position), [None, None, None]
        event = events.setdefault(key, {'Asset': asset.symbol, 'Date': key,
            'Price': values[0], 'Simple return': values[1], 'Log return': values[2],
            'reasons': set(), 'Severity': severity, 'actions': set()})
        event['reasons'].add(reason)
        event['actions'].add(action)
        if RANK[severity] > RANK[event['Severity']]:
            event['Severity'] = severity

    base = validate(NormalizedData(frame), asset, settings.start, settings.end, settings.validation)
    # Calendar-specific evidence below supersedes the ingestion weekday heuristic.
    issues = [i for i in base['issues'] if i['code'] != 'unobserved_weekdays']
    for item in issues:
        severity = 'FAIL' if item['severity'] == 'error' else 'WARNING'
        for observation in item.get('observations', []):
            flag(observation['row'], item['code'], severity, 'Inspect the archived source row; no price has been imputed.')
    original_returns = audit_returns(frame, settings.audit)
    for pos in original_returns['bad_rows']:
        flag(pos, 'return_identity_failure', 'FAIL', 'Reconcile stored returns with source prices. Audit does not repair values.')
    source = {'total_return_compatible': None, 'limitations': []}
    try:
        source = audit_source(frame, entry, asset, settings, flag)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        issues.append({'code': 'source_verification_failed', 'severity': 'error', 'message': str(exc)})
        source['limitations'].append(str(exc))
    if source.get('total_return_compatible') is not True:
        issues.append({'code': 'total_return_unverified', 'severity': 'warning',
                       'message': 'Total-return compatibility is not verified; review source identity/adjustments.'})
    calendar = audit_calendar(frame['date'], asset, settings.start, settings.end, calendar_document)
    gap_mask = calendar.pop('gap_mask')
    verified_interval = calendar.pop('verified_interval')
    unexplained_gaps = []
    for item in issues:
        if item['code'] == 'long_date_gap':
            for gap in item['gaps']:
                positions = np.flatnonzero(frame['date'].eq(pd.Timestamp(gap['date'])))
                explained = len(positions) == 1 and bool(verified_interval.iloc[positions[0]])
                if not explained:
                    unexplained_gaps.append(gap)
                    flag(int(positions[0]) if len(positions) else gap['date'], 'long_unexplained_gap', 'WARNING',
                         'Verify closures and source coverage across this interval.')
            item['gaps'] = unexplained_gaps
            item['count'] = len(unexplained_gaps)
    issues = [i for i in issues if i['code'] != 'long_date_gap' or i['count']]
    if not calendar['full_window_verified']:
        issues.append({'code': 'partial_calendar_authority', 'severity': 'warning',
                       'message': 'Historical calendar coverage is incomplete. Dates outside coverage or in explicit unverified-date exceptions remain unverified, not confirmed missing sessions.'})
    for day in calendar['unverified_absent_weekdays']:
        flag(day, 'unverified_weekday_absence', 'WARNING', 'Check an authoritative historical exchange calendar; this may be a holiday.')
    for day in calendar['missing_expected_sessions']:
        flag(day, 'missing_expected_session', 'FAIL', 'Verify the official calendar and obtain the missing original observation; never forward-fill.')
    for day in calendar['unexpected_sessions']:
        flag(day, 'unexpected_session', 'WARNING', 'Verify a special exchange session or incorrect date/timezone.')
    if calendar['missing_expected_sessions']:
        issues.append({'code': 'missing_expected_sessions', 'severity': 'error',
                       'message': 'Confirmed expected sessions are absent. Affected returns are explicitly excluded in the inspection artifact.'})
    canonical = frame.copy()
    canonical['source_timezone'] = asset.timezone
    canonical['calendar_interval_verified'] = verified_interval
    canonical['return_exclusion_reason'] = ''
    if len(canonical):
        canonical.loc[0, 'return_exclusion_reason'] = 'first_observation'
    price_valid = np.isfinite(canonical['price']) & canonical['price'].gt(0) & canonical['date'].notna()
    invalid_interval = ~(price_valid & price_valid.shift(1, fill_value=False))
    canonical.loc[invalid_interval & canonical.index.to_series().ne(0), 'return_exclusion_reason'] = 'invalid_or_missing_adjacent_price'
    cleaning = list(source.get('cleaning_actions', []))
    if gap_mask.any():
        for col in ('daily_return', 'simple_return', 'log_return'):
            canonical['observed_' + col] = canonical[col]
            canonical.loc[gap_mask, col] = np.nan
        canonical.loc[gap_mask, 'return_exclusion_reason'] = 'confirmed_missing_session'
        cleaning.append({'code': 'exclude_returns_across_confirmed_missing_sessions',
                         'dates': canonical.loc[gap_mask, 'date'].dt.strftime('%Y-%m-%d').tolist(),
                         'action': 'Preserve observed returns in observed_* columns; exclude these multi-session intervals from daily returns. Prices unchanged.'})
        for pos in np.flatnonzero(gap_mask):
            flag(pos, 'return_spans_missing_session', 'FAIL', 'Recover missing data before treating this interval as a daily return; observed return preserved separately.')
    numerical = audit_returns(canonical, settings.audit, gap_mask)
    # Bad input returns remain a failure even if a documented gap would mask them.
    if original_returns['status'] == 'FAIL' or numerical['status'] == 'FAIL':
        issues.append({'code': 'return_validation_failed', 'severity': 'error',
                       'message': 'One or more arithmetic, log, identity or cumulative reconciliation checks failed.'})
    outliers = detect_outliers(canonical, settings.audit, settings.validation, flag)
    status = 'FAIL' if any(i['severity'] == 'error' for i in issues) else 'PASS'
    if status != 'FAIL' and (any(i['severity'] == 'warning' for i in issues) or events):
        status = 'WARNING'
    if any(e['Severity'] == 'FAIL' for e in events.values()):
        status = 'FAIL'
    canonical['audit_status'] = status
    canonical['review_reasons'] = canonical['date'].map(
        lambda day: '; '.join(sorted(events.get(day.strftime('%Y-%m-%d'), {}).get('reasons', []))) if pd.notna(day) else 'invalid_date')
    canonical['return_usable'] = (np.isfinite(canonical['simple_return']) & np.isfinite(canonical['log_return'])
                                   & ~invalid_interval & ~gap_mask)
    canonical.loc[numerical['bad_rows'], 'return_usable'] = False
    returns = canonical.loc[canonical['return_usable'], 'simple_return']
    logs = canonical.loc[canonical['return_usable'], 'log_return']
    count_flag = lambda names: sum(bool(e['reasons'] & names) for e in events.values())
    duplicate_excess = int(frame.duplicated(['asset', 'date']).sum())
    summary = {
        'asset': asset.symbol, 'asset_name': asset.name, 'currency': asset.currency, 'source': asset.source,
        'price_convention': asset.price_convention, 'source_timezone': asset.timezone,
        'earliest': base['earliest'], 'latest': base['latest'], 'observation_count': len(frame),
        'expected_sessions_verified_period': calendar['expected_sessions_verified_period'],
        'expected_sessions_full_window': calendar['expected_sessions_full_window'],
        'calendar_verified_start': calendar['verified_start'], 'calendar_verified_end': calendar['verified_end'],
        'missing_expected_sessions': len(calendar['missing_expected_sessions']),
        'unverified_absent_weekdays': len(calendar['unverified_absent_weekdays']),
        'unexpected_sessions': len(calendar['unexpected_sessions']),
        'invalid_price_count': base['invalid_price_count'], 'invalid_date_count': base['invalid_date_count'],
        'duplicate_asset_date_excess': duplicate_excess, 'duplicate_rows_excess': int(frame.duplicated().sum()),
        'source_duplicate_rows_collapsed': entry.get('quality', {}).get('source_duplicate_rows_collapsed', 0),
        'dates_monotonic': bool(frame['date'].is_monotonic_increasing),
        'absolute_extreme_return_count': count_flag({'absolute_return'}),
        'suspicious_return_count': count_flag(RETURN_FLAGS),
        'max_consecutive_equal_prices': outliers['max_unchanged_price_run'],
        'max_consecutive_unchanged_transitions': max(0, outliers['max_unchanged_price_run'] - 1),
        'stale_price_observations': outliers['stale_price_observations'],
        'long_gap_count': base['long_gap_count'], 'unexplained_long_gap_count': len(unexplained_gaps),
        'usable_return_observations': int(canonical['return_usable'].sum()),
        'mean_daily_simple_return': _number(returns.mean()), 'daily_log_return_std': _number(logs.std(ddof=1)),
        'annualized_historical_volatility': _number(logs.std(ddof=1) * np.sqrt(settings.audit.annualization_sessions)),
        'annualization_sessions': settings.audit.annualization_sessions,
        'min_daily_simple_return': _number(returns.min()), 'max_daily_simple_return': _number(returns.max()),
        'return_checks': numerical['status'], 'total_return_compatible': source.get('total_return_compatible'),
        'validation_status': status,
        'research_ready': 'YES' if status == 'PASS' else ('NO' if status == 'FAIL' else 'MANUAL_REVIEW_REQUIRED'),
    }
    rows = []
    for key in sorted(events):
        e = events[key]
        rows.append({**{k: v for k, v in e.items() if k not in {'reasons', 'actions'}},
                     'Reason flagged': '; '.join(sorted(e['reasons'])),
                     'Suggested verification action': ' '.join(sorted(e['actions']))})
    detail = {'summary': summary, 'issues': issues, 'source_audit': source, 'calendar_audit': calendar,
              'original_return_audit': original_returns, 'canonical_return_audit': numerical,
              'outlier_diagnostics': outliers, 'cleaning_actions': cleaning}
    return canonical, detail, rows


def _publish(result, reports_dir):
    run = Path(result['report_dir'])
    for name in ('data_quality.md', 'data_quality_summary.csv', 'suspicious_dates.csv'):
        write_text((run / name).read_text(encoding='utf-8'), reports_dir / name)
    write_json({'audit_id': result['audit_id'], 'manifest': str(run / 'audit_manifest.json'),
                'canonical': result['canonical'], 'complete': result['complete']}, reports_dir / 'latest_audit.json')


def run_audit(settings, *, input_manifest=None, config_path=None, plots=True):
    """Content-addressed audit; identical inputs/code/config reuse verified artifacts."""
    if input_manifest is None:
        pointer = json.loads((settings.reports_dir / 'latest.json').read_text(encoding='utf-8'))
        input_manifest = Path(pointer['manifest'])
    input_manifest = Path(input_manifest).resolve()
    manifest = json.loads(input_manifest.read_text(encoding='utf-8'))
    paths = {input_manifest}
    for entry in manifest['assets']:
        paths.update(Path(r['path']).resolve() for r in entry.get('raw', []))
        if entry.get('quality', {}).get('processed'):
            paths.add(Path(entry['quality']['processed']['path']).resolve())
    for path in (config_path, settings.audit.calendar_file):
        if path:
            paths.add(Path(path).resolve())
    if settings.audit.evidence_dir and settings.audit.evidence_dir.is_dir():
        paths.update(p.resolve() for p in settings.audit.evidence_dir.iterdir() if p.is_file())
    calendar = {}
    calendar_limitation = None
    if settings.audit.calendar_file:
        if settings.audit.calendar_file.is_file():
            calendar = json.loads(settings.audit.calendar_file.read_text(encoding='utf-8'))
            from volrisk.data.calendar_audit import verify_calendar_evidence
            paths.update(verify_calendar_evidence(calendar, settings.audit.calendar_file))
        else:
            calendar_limitation = 'Configured calendar file missing; all calendar absences are unverified.'
    inputs = {str(p): sha256(p) if p.is_file() else None for p in sorted(paths)}
    package = Path(__file__).resolve().parents[1]
    code = {p.relative_to(package).as_posix(): sha256(p) for p in sorted(package.rglob('*.py'))}
    versions = {**_versions(), 'matplotlib': version('matplotlib')}
    identity = {'schema_version': 1, 'inputs_sha256': inputs, 'implementation_sha256': code,
                'configuration': settings.as_dict(), 'versions': versions, 'plots': plots}
    audit_id = hashlib.sha256(json.dumps(identity, sort_keys=True, default=str).encode()).hexdigest()[:24]
    report_dir = settings.reports_dir / 'audits' / audit_id
    audit_manifest = report_dir / 'audit_manifest.json'
    if audit_manifest.is_file():
        saved = json.loads(audit_manifest.read_text(encoding='utf-8'))
        for path, digest in saved['output_sha256'].items():
            if not Path(path).is_file() or sha256(Path(path)) != digest:
                raise DataError(f'Cached audit artifact changed or missing: {path}; restore it or use a new report directory.')
        _publish(saved, settings.reports_dir)
        return {**saved, 'cache_reused': True}
    summaries, details, events, canonicals, artifacts = [], [], [], {}, []
    entries = {e['symbol']: e for e in manifest['assets']}
    for configured in ASSETS:
        entry = entries.get(configured.symbol, {})
        asset = configured
        # The two explicit official NSE formats are allowed; other source labels fail validation.
        if configured.symbol == 'NIFTY50_TRI' and entry.get('source') == 'NSE Indices official JSON responses':
            asset = replace(configured, source=entry['source'])
        try:
            record = entry.get('quality', {}).get('processed')
            if not record:
                raise DataError('No processed dataset in the selected ingestion run; no fallback or substitution used.')
            path = Path(record['path'])
            if not path.is_file() or sha256(path) != record['sha256']:
                raise DataError('Processed file missing or hash differs from ingestion manifest')
            canonical, detail, rows = inspect_asset(pd.read_parquet(path), entry, asset, settings, calendar)
            summary = detail['summary']
            folder = 'canonical' if summary['validation_status'] != 'FAIL' else 'quarantine'
            target = settings.processed_dir.parent / folder / audit_id / f'{asset.symbol}.parquet'
            if target.exists():
                pd.testing.assert_frame_equal(pd.read_parquet(target), canonical)
                saved = {'path': str(target.resolve()), 'sha256': sha256(target), 'rows': len(canonical)}
            else:
                saved = write_parquet(canonical, target)
            detail['data_artifact'] = saved
            if folder == 'canonical':
                canonicals[asset.symbol] = saved['path']
            artifacts.append(target)
            events.extend(rows)
            if plots:
                from volrisk.data.audit_plots import make_plots
                plotted = make_plots(canonical, detail, rows, report_dir / 'figures', settings.audit.event_plot_limit)
                detail['figures'] = [str(p.resolve()) for p in plotted]
                artifacts.extend(plotted)
        except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
            summary = {'asset': asset.symbol, 'asset_name': asset.name, 'currency': asset.currency,
                       'source': asset.source, 'validation_status': 'FAIL', 'research_ready': 'NO',
                       'observation_count': None, 'failure': f'{type(exc).__name__}: {exc}'}
            detail = {'summary': summary, 'issues': [{'code': 'audit_input_failure', 'severity': 'error',
                                                      'message': summary['failure']}]}
            canonicals.pop(asset.symbol, None)
        summaries.append(summary)
        details.append(detail)
    from volrisk.data.audit_reporting import audit_markdown
    result = {**identity, 'audit_id': audit_id, 'audited_at_utc': datetime.now(timezone.utc).isoformat(),
              'input_manifest': str(input_manifest), 'input_run_id': manifest.get('run_id'),
              'calendar_limitation': calendar_limitation, 'report_dir': str(report_dir.resolve()),
              'assets': details, 'canonical': canonicals, 'cache_reused': False,
              'complete': all(s['validation_status'] != 'FAIL' for s in summaries)}
    for name, payload in (
        ('data_quality_summary.csv', pd.DataFrame(summaries).to_csv(index=False, lineterminator='\n')),
        ('suspicious_dates.csv', pd.DataFrame(events, columns=EVENT_COLUMNS).to_csv(index=False, lineterminator='\n')),
        ('data_quality.md', audit_markdown(result)),
    ):
        path = report_dir / name
        write_text(payload, path)
        artifacts.append(path)
    # Re-hash every original input after execution: a concurrent change invalidates publication.
    for name, digest in inputs.items():
        path = Path(name)
        if (sha256(path) if path.is_file() else None) != digest:
            raise DataError(f'Audit input changed during execution: {name}')
    result['raw_inputs_unchanged'] = True
    result['output_sha256'] = {str(p.resolve()): sha256(p) for p in artifacts}
    write_json(result, audit_manifest)
    _publish(result, settings.reports_dir)
    return result
