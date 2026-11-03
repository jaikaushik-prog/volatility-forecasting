"""Lossless source audit and explicit deterministic canonicalization policies."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from volrisk.data.storage import sha256
from .calendar import TZ, local_time

PRICE_COLUMNS = ['open', 'high', 'low', 'close']


def read_source(path: Path, spec: dict):
    if path.suffix.lower() != '.csv':
        raise ValueError('Only CSV input is accepted; pickle files are never deserialized')
    raw = pd.read_csv(path)
    time_columns = [c for c in ('datetime', 'time', 'date', 'timestamp') if c in raw]
    if len(time_columns) != 1 or not set(PRICE_COLUMNS) <= set(raw):
        raise ValueError(f'{path.name}: expected one timestamp and OHLC columns')
    col = time_columns[0]
    parsed = pd.to_datetime(raw[col], format='mixed', errors='coerce')
    if not isinstance(parsed.dtype, pd.DatetimeTZDtype):
        parsed = parsed.dt.tz_localize(spec['timezone'], ambiguous='raise', nonexistent='raise')
    parsed = parsed.dt.tz_convert(TZ)
    digest = sha256(path)
    report = {'filename': path.name, 'path': str(path.resolve()), 'sha256': digest, 'bytes': path.stat().st_size,
        'rows': len(raw), 'columns': list(raw), 'dtypes': raw.dtypes.astype(str).to_dict(),
        'missing_values': raw.isna().sum().astype(int).to_dict(), 'timestamp_column': col,
        'first_timestamp': str(parsed.min()), 'last_timestamp': str(parsed.max()),
        'sorted_in_source': bool(parsed.is_monotonic_increasing), 'invalid_timestamps': int(parsed.isna().sum()),
        'duplicate_timestamps': int(parsed.duplicated().sum()), 'identical_raw_rows': int(raw.duplicated().sum()),
        'source_timezone': 'not encoded; unknown' if not raw[col].astype(str).str.contains(r'(?:Z|[+-]\d\d:\d\d)$').any() else 'explicit offset',
        'timezone_normalization': spec['timezone'], 'timezone_verified': spec['timezone_verified'],
        'bar_label': spec['bar_label'], 'bar_label_verified': spec['bar_label_verified'],
        'instrument': spec['instrument'], 'instrument_verified': spec['instrument_verified'],
        'stock_codes': sorted(raw.stock_code.dropna().astype(str).unique()) if 'stock_code' in raw else [],
        'exchanges': sorted(raw.exchange_code.dropna().astype(str).unique()) if 'exchange_code' in raw else [],
        'retrieved_at_utc': None, 'imported_at_utc': datetime.now(timezone.utc).isoformat(),
        'original_mtime_utc': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}
    out = pd.DataFrame({'timestamp': parsed, 'source_timestamp': raw[col].astype(str),
        'source_file': path.name, 'source_sha256': digest, 'source_row': np.arange(len(raw))+2})
    for c in PRICE_COLUMNS + ['volume']:
        out[c] = pd.to_numeric(raw[c], errors='coerce') if c in raw else np.nan
    out['identity_mismatch'] = False
    if 'exchange_code' in raw:
        out['identity_mismatch'] |= raw.exchange_code.ne(spec['exchange'])
    if 'stock_code' in raw and spec.get('expected_stock_codes'):
        out['identity_mismatch'] |= ~raw.stock_code.isin(spec['expected_stock_codes'])
    if spec['bar_label'] == 'end':
        out['timestamp'] -= pd.Timedelta(minutes=1)
    elif spec['bar_label'] != 'start':
        raise ValueError('bar_label must explicitly be start or end')
    return out, report


def normalize_frames(frames, spec, calendar, quality):
    frame = pd.concat(frames, ignore_index=True)
    frame['asset'] = spec['asset']
    frame['exchange'] = spec['exchange']
    frame['currency'] = spec['currency']
    frame['unit'] = spec['unit']
    frame['instrument'] = spec['instrument']
    frame['provenance_verified'] = all(spec[k] for k in ['timezone_verified','bar_label_verified','instrument_verified'])
    quarantine = []
    invalid_date = frame.timestamp.isna()
    if invalid_date.any():
        quarantine.append(frame.loc[invalid_date].assign(reason='invalid_timestamp'))
    frame = frame.loc[~invalid_date].sort_values(['timestamp','source_file','source_row'], kind='stable').copy()
    dup = frame.timestamp.duplicated(keep=False)
    comparison = PRICE_COLUMNS + ['volume','identity_mismatch']
    conflicting = frame.loc[dup].groupby('timestamp')[comparison].nunique(dropna=False).max(axis=1).gt(1)
    conflict_times = conflicting.index[conflicting]
    conflict = frame.timestamp.isin(conflict_times)
    if conflict.any():
        quarantine.append(frame.loc[conflict].assign(reason='conflicting_duplicate_all_copies_excluded'))
    frame = frame.loc[~conflict].copy()
    exact = frame.timestamp.duplicated(keep='first')
    if exact.any():
        quarantine.append(frame.loc[exact].assign(reason='identical_market_fields_duplicate_removed'))
    removed = int(exact.sum())
    frame = frame.loc[~exact].reset_index(drop=True)
    if frame.empty:
        raise ValueError(f'{spec["asset"]}: no canonical timestamps remain; source cannot be integrated')
    frame['available_at'] = frame.timestamp + pd.Timedelta(minutes=1)
    frame['session_date'] = frame.timestamp.dt.tz_localize(None).dt.normalize()
    prices = frame[PRICE_COLUMNS]
    frame['invalid_price'] = ~np.isfinite(prices).all(axis=1) | prices.le(0).any(axis=1)
    frame['invalid_ohlc'] = (frame.high < prices[['open','close','low']].max(axis=1)) | (frame.low > prices[['open','close','high']].min(axis=1))
    frame['off_minute_grid'] = frame.timestamp.ne(frame.timestamp.dt.floor('min'))
    frame['segment'] = -1
    frame['schedule_verified'] = False
    frame['session_kind'] = ''
    for date, idx in frame.groupby('session_date', sort=False).groups.items():
        info = calendar.describe(date)
        frame.loc[idx, 'schedule_verified'] = info['schedule_verified']
        frame.loc[idx, 'session_kind'] = info['session_kind']
        for segment,(a,b) in enumerate(info['segments']):
            within = (frame.loc[idx, 'timestamp'] >= local_time(date,a)) & (frame.loc[idx, 'available_at'] <= local_time(date,b))
            frame.loc[within.index[within], 'segment'] = segment
    frame['outside_session'] = frame.segment.lt(0)
    frame['valid_bar'] = ~(frame.invalid_price | frame.invalid_ohlc | frame.off_minute_grid | frame.identity_mismatch | frame.outside_session)
    # Returns for anomaly detection are only between adjacent, valid, same-segment observations.
    continuous = (frame.session_date.eq(frame.session_date.shift()) & frame.segment.eq(frame.segment.shift())
        & frame.timestamp.diff().eq(pd.Timedelta(minutes=1)) & frame.valid_bar & frame.valid_bar.shift(fill_value=False))
    with np.errstate(divide='ignore', invalid='ignore'):
        r = np.log(frame.close / frame.close.shift()).where(continuous)
    frame['intraday_log_return_adjacent'] = r
    threshold = quality['vix_extreme_log_return'] if spec['asset'] == 'INDIA_VIX' else quality['index_extreme_log_return']
    frame['extreme_return'] = r.abs().gt(threshold)
    # Whole-file MAD is retrospective QC only; never a forecasting feature or deletion rule.
    finite_returns = r.dropna()
    median = finite_returns.median() if len(finite_returns) else np.nan
    mad = (finite_returns-median).abs().median() if len(finite_returns) else np.nan
    frame['mad_outlier'] = (r-median).abs().gt(quality['mad_multiple']*1.4826*mad) if mad > 0 else False
    frame['large_reversal'] = (r.abs().gt(threshold/2) & r.shift().abs().gt(threshold/2)
                              & (r*r.shift()).lt(0) & (r+r.shift()).abs().lt(threshold/4))
    unchanged = continuous & frame.close.eq(frame.close.shift())
    group = (~unchanged).cumsum()
    runlength = unchanged.groupby(group).cumsum().astype(int)
    frame['unchanged_run_minutes'] = runlength
    frame['stale_sequence'] = runlength.ge(int(quality['stale_run_minutes']))
    flags = ['invalid_price','invalid_ohlc','off_minute_grid','identity_mismatch','outside_session',
             'extreme_return','mad_outlier','large_reversal','stale_sequence']
    frame['quality_flags'] = [';'.join(k for k,v in zip(flags,row) if v) for row in frame[flags].itertuples(index=False,name=None)]
    rejected = pd.concat(quarantine,ignore_index=True) if quarantine else pd.DataFrame(columns=list(frame.columns)+['reason'])
    actions = {'identical_duplicates_removed': removed, 'conflicting_timestamps': len(conflict_times),
               'invalid_timestamp_rows': int(invalid_date.sum()), 'normalized_rows': len(frame),
               'flag_counts': {c:int(frame[c].sum()) for c in flags},
               'mad_location': None if not np.isfinite(median) else float(median),
               'mad_scale': None if not np.isfinite(mad) else float(mad),
               'sorting': 'stable timestamp/source filename/row order; raw source unchanged',
               'duplicate_policy': 'identical market fields keep first; conflicting timestamps quarantine all copies',
               'price_policy': 'no interpolation, no forward fill, no winsorization, invalid rows retained and flagged'}
    return frame, rejected, actions
