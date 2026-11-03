"""Session checks with explicit, bounded calendar authority and no price imputation."""
from pathlib import Path

import pandas as pd

from volrisk.data.models import Asset, DataError
from volrisk.data.storage import sha256


def verify_calendar_evidence(document: dict, calendar_file: Path) -> set[Path]:
    """Check declared archive hashes before using or reusing a calendar audit.

    Paths are relative to the calendar file, including ../data/raw evidence.
    Legacy/synthetic calendars may have no attached evidence manifest.
    """
    paths = set()
    for record in document.get('evidence_files', []):
        path = (Path(calendar_file).parent / record['path']).resolve()
        if not path.is_file() or sha256(path) != record['sha256']:
            raise DataError(f'Calendar evidence missing or changed: {path}')
        paths.add(path)
    return paths


def audit_calendar(dates: pd.Series, asset: Asset, start, end, document: dict) -> dict:
    observed = pd.DatetimeIndex(dates.dropna().unique()).sort_values()
    spec = document.get('markets', {}).get(asset.calendar)
    expected = pd.DatetimeIndex([])
    covered_start = covered_end = None
    sources = []
    uncertain = pd.DatetimeIndex([])
    if spec:
        if spec.get('timezone') != asset.timezone or not spec.get('sources'):
            raise DataError(f'{asset.calendar}: timezone or calendar provenance invalid')
        covered_start = max(pd.Timestamp(start), pd.Timestamp(spec['verified_start']))
        covered_end = min(pd.Timestamp(end), pd.Timestamp(spec['verified_end']))
        sources = spec['sources']
        if covered_start <= covered_end:
            closed = pd.DatetimeIndex(pd.to_datetime(spec.get('holidays', [])))
            special = pd.DatetimeIndex(pd.to_datetime(spec.get('special_sessions', [])))
            uncertain = pd.DatetimeIndex(pd.to_datetime(spec.get('unverified_dates', [])))
            if len(closed.intersection(special)):
                raise DataError('Calendar declares a date both closed and open')
            if len(uncertain.intersection(closed.union(special))):
                raise DataError('Calendar declares a date both verified and unverified')
            uncertain = uncertain[(uncertain >= covered_start) & (uncertain <= covered_end)]
            expected = pd.bdate_range(covered_start, covered_end).difference(closed).union(special).difference(uncertain)
            expected = expected[(expected >= covered_start) & (expected <= covered_end)].sort_values()
        else:
            covered_start = covered_end = None
    known = observed[(observed >= covered_start) & (observed <= covered_end)] if covered_start is not None else pd.DatetimeIndex([])
    known = known.difference(uncertain)
    missing = expected.difference(observed)
    unexpected = known.difference(expected)
    weekdays = pd.bdate_range(start, end)
    unverified = weekdays if covered_start is None else weekdays[(weekdays < covered_start) | (weekdays > covered_end)]
    unverified = unverified.union(uncertain[uncertain.dayofweek < 5])
    unverified_absences = unverified.difference(observed)
    gap_mask = pd.Series(False, index=dates.index)
    verified_interval = pd.Series(False, index=dates.index)
    for i in range(1, len(dates)):
        previous, current = dates.iloc[i-1], dates.iloc[i]
        if pd.isna(previous) or pd.isna(current) or current <= previous:
            continue
        gap_mask.iloc[i] = bool(((missing > previous) & (missing < current)).any())
        if covered_start is not None:
            verified_interval.iloc[i] = (covered_start <= previous <= current <= covered_end
                                         and previous in expected and current in expected and not gap_mask.iloc[i]
                                         and not ((uncertain >= previous) & (uncertain <= current)).any())
    full = covered_start == pd.Timestamp(start) and covered_end == pd.Timestamp(end) and not len(uncertain)
    return {
        'calendar': asset.calendar, 'source_timezone': asset.timezone,
        'verified_start': covered_start.date().isoformat() if covered_start is not None else None,
        'verified_end': covered_end.date().isoformat() if covered_end is not None else None,
        'full_window_verified': full, 'sources': sources,
        'unverified_dates_in_coverage': uncertain.strftime('%Y-%m-%d').tolist(),
        'expected_sessions_verified_period': len(expected) if covered_start is not None else None,
        'expected_sessions_full_window': len(expected) if full else None,
        'missing_expected_sessions': missing.strftime('%Y-%m-%d').tolist(),
        'unexpected_sessions': unexpected.strftime('%Y-%m-%d').tolist(),
        'unverified_absent_weekdays': unverified_absences.strftime('%Y-%m-%d').tolist(),
        'gap_mask': gap_mask, 'verified_interval': verified_interval,
    }
