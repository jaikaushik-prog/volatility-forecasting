"""Verify source identity and provider adjustment conventions without readjusting prices."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from volrisk.data.models import DataError
from volrisk.data.normalization import normalize_nifty, normalize_yfinance
from volrisk.data.storage import sha256


def audit_source(frame, entry, asset, settings, flag):
    for field, expected in (('symbol', asset.symbol), ('currency', asset.currency),
                            ('source', asset.source), ('price_convention', asset.price_convention)):
        if field in entry and entry[field] != expected:
            raise DataError(f'Source manifest has invalid {field}: expected {expected}')
    records = entry.get('raw', [])
    if not records:
        raise DataError('No original source snapshots are recorded')
    for record in records:
        path = Path(record['path'])
        if not path.is_file() or sha256(path) != record['sha256']:
            raise DataError(f'Original raw source missing or hash mismatch: {path}')
    acquisition = entry.get('acquisition', {})
    if asset.symbol == 'NIFTY50_TRI':
        paths = [Path(r['path']) for r in records if r['path'].endswith('_response.json') or Path(r['path']).suffix.lower() == '.csv']
        original = normalize_nifty(paths, asset, settings.start, settings.end, settings.nifty_date_format)
        uncertain = any(i['code'] == 'index_identity_from_manual_selection' for i in original.issues)
        identity = 'UNCERTAIN' if uncertain else 'VERIFIED_NIFTY50_GROSS_TRI_FIELD'
        result = {'identity': identity, 'total_return_compatible': not uncertain,
                  'adjustment_check': 'Gross TotalReturnsIndex field selected; price index and NTR excluded.',
                  'limitations': ['Original NSE HTTP-completion times were not recorded separately; response-save times are retained.']}
    else:
        request = acquisition.get('request', {})
        if request.get('auto_adjust') is not True or request.get('actions') is not True or request.get('tickers') != asset.symbol:
            raise DataError('ETF retrieval convention is not verified auto_adjust=True, actions=True for this asset')
        if request.get('interval') != '1d' or request.get('back_adjust') is not False:
            raise DataError('ETF daily adjustment convention is invalid')
        path = next((Path(r['path']) for r in records if Path(r['path']).suffix == '.parquet'), None)
        if path is None:
            raise DataError('Original ETF Parquet snapshot unavailable')
        original = normalize_yfinance(pd.read_parquet(path), asset, settings.start, settings.end)
        result = _audit_adjustments(frame, asset, settings, flag)
    if frame['date'].tolist() != original.frame['date'].tolist():
        raise DataError('Processed dates differ from the original source calendar')
    actual = pd.to_numeric(frame['price'], errors='coerce').to_numpy(dtype=float)
    expected = original.frame['price'].to_numpy(dtype=float)
    if not np.array_equal(actual, expected, equal_nan=True):
        raise DataError('Processed prices differ from original source values; possible repeated adjustment')
    for col in ('dividends', 'stock_splits', 'capital_gains'):
        if col in original.frame:
            if col not in frame or not np.array_equal(frame[col], original.frame[col], equal_nan=True):
                raise DataError(f'{col} differs from the recorded source actions')
    result.update(raw_hashes_verified=True, stored_prices_equal_source=True,
                  source_timezone=asset.timezone,
                  timestamp_policy='Naive daily labels are exchange-local; aware timestamps convert to source timezone.',
                  acquisition=acquisition,
                  cleaning_actions=[i for i in original.issues if i['code'] in {'source_non_monotonic', 'identical_duplicates_collapsed'}])
    return result


def _audit_adjustments(frame, asset, settings, flag):
    result = {'identity': 'VERIFIED_ETF_REQUEST', 'total_return_compatible': None,
              'adjustment_check': 'UNVERIFIED_REFERENCE_UNAVAILABLE',
              'limitations': ['Current-vintage Yahoo history is not a historical as-of database. The reference is from the same provider, not an independent vendor.']}
    directory = settings.audit.evidence_dir
    meta_path = directory / f'{asset.symbol}_adjustment_reference.json' if directory else None
    if meta_path is None or not meta_path.is_file():
        result['limitations'].append('Unadjusted Close / Adj Close reference unavailable; metadata alone is not independent adjustment verification.')
        return result
    metadata = json.loads(meta_path.read_text(encoding='utf-8'))
    path = (directory / metadata['file']).resolve()
    if not path.is_relative_to(directory.resolve()) or not path.is_file() or sha256(path) != metadata.get('sha256'):
        raise DataError('Adjustment reference path or hash invalid')
    req = metadata.get('request', {})
    if (metadata.get('symbol') != asset.symbol or metadata.get('currency') != asset.currency
            or req.get('auto_adjust') is not False or req.get('actions') is not True or req.get('tickers') != asset.symbol):
        raise DataError('Adjustment reference metadata convention invalid')
    reference = pd.read_parquet(path)
    if not reference.index.is_unique or not {'Adj Close', 'Close', 'Dividends', 'Stock Splits'} <= set(reference):
        raise DataError('Adjustment reference lacks unique dates or required fields')
    aligned = reference.reindex(pd.DatetimeIndex(frame['date']))
    ref_adj = aligned['Adj Close'].to_numpy(dtype=float)
    raw_close = aligned['Close'].to_numpy(dtype=float)
    prices = frame['price'].to_numpy(dtype=float)
    reference_valid = np.isfinite(ref_adj) & (ref_adj > 0) & np.isfinite(raw_close) & (raw_close > 0)
    for col in ('Dividends', 'Stock Splits', 'Capital Gains'):
        if col in aligned:
            values = aligned[col].to_numpy(dtype=float)
            reference_valid &= np.isfinite(values) & (values >= 0)
    match = reference_valid & np.isclose(prices, ref_adj, rtol=settings.audit.adjustment_rtol, atol=1e-6)
    for i in np.flatnonzero(~match):
        flag(i, 'adjustment_reference_mismatch', 'WARNING', 'Compare source vintages and adjustment factors; original prices were retained.')
    with np.errstate(divide='ignore', invalid='ignore'):
        factor = ref_adj / raw_close
    cash = aligned['Dividends'].to_numpy(dtype=float)
    if 'Capital Gains' in aligned:
        cash = cash + aligned['Capital Gains'].to_numpy(dtype=float)
    dividend_dates = np.flatnonzero(np.isfinite(cash) & (cash != 0))
    factor_failures = 0
    with np.errstate(invalid='ignore', divide='ignore'):
        unadj_returns = np.r_[np.nan, raw_close[1:]/raw_close[:-1]-1]
        adj_returns = np.r_[np.nan, ref_adj[1:]/ref_adj[:-1]-1]
    for i in dividend_dates:
        if i == 0:
            continue
        if not (reference_valid[i-1] and reference_valid[i]):
            factor_failures += 1
            flag(i, 'dividend_factor_inconsistency', 'WARNING', 'Distribution factor cannot be checked across invalid or absent reference prices/actions.')
            continue
        observed_factor = factor[i-1] / factor[i]
        expected_factor = 1 - cash[i] / raw_close[i-1]
        if not np.isfinite(observed_factor) or abs(observed_factor-expected_factor) > settings.audit.adjustment_factor_atol:
            factor_failures += 1
            flag(i, 'dividend_factor_inconsistency', 'WARNING', 'Verify dividend/capital-gain amount and Yahoo adjustment factors, including any source revisions.')
        actual_return = frame['simple_return'].iloc[i]
        cash_yield = cash[i] / raw_close[i-1]
        if not (match[i] and match[i-1]) and np.isfinite(actual_return) and cash_yield > 1e-4:
            if abs(actual_return-unadj_returns[i]) < settings.audit.adjustment_factor_atol:
                flag(i, 'possible_missing_dividend_adjustment', 'WARNING', 'Stored returns resemble raw Close returns on an ex-distribution date.')
            if abs(actual_return-adj_returns[i]-cash_yield) < settings.audit.adjustment_factor_atol:
                flag(i, 'possible_double_dividend_adjustment', 'WARNING', 'Check whether distributions were added again to adjusted-price returns.')
    verified = bool(match.all() and factor_failures == 0)
    result.update(total_return_compatible=verified,
                  adjustment_check='VERIFIED_YAHOO_ADJUSTED_CLOSE' if verified else 'REVIEW_REQUIRED',
                  reference_metadata=metadata, reference_sha256=sha256(path),
                  matched_price_observations=int(match.sum()), compared_price_observations=len(frame),
                  dividend_events_checked=int((dividend_dates > 0).sum()), dividend_factor_warnings=factor_failures,
                  split_events_available=int(aligned['Stock Splits'].fillna(0).ne(0).sum()),
                  note='No adjustments applied during audit. Split behavior cannot be empirically checked when no split events exist.')
    return result
