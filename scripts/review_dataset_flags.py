"""Explain the saved audit's review queue using actual archived source observations.

This produces a review worksheet, not a new approval or a replacement data audit.
It never modifies a source dataset or removes a flagged market move.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from volrisk.data.storage import sha256, write_json, write_text
from review_calendars import main as review_calendars

review_calendars()

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
pointer = json.loads((REPORTS / 'latest_audit.json').read_text(encoding='utf-8'))
audit_path = Path(pointer['manifest'])
audit = json.loads(audit_path.read_text(encoding='utf-8'))
ingestion = json.loads(Path(audit['input_manifest']).read_text(encoding='utf-8'))
entries = {e['symbol']: e for e in ingestion['assets']}
flags_path = Path(audit['report_dir']) / 'suspicious_dates.csv'
assert sha256(flags_path) == audit['output_sha256'][str(flags_path)]
flags = pd.read_csv(flags_path)
returns, weekends, datasets = [], [], []
checked_hashes = {}

for detail in audit['assets']:
    symbol = detail['summary']['asset']
    entry = entries[symbol]
    path = Path(audit['canonical'][symbol])
    assert sha256(path) == detail['data_artifact']['sha256'], path
    frame = pd.read_parquet(path)
    raw_paths = {}
    for record in entry['raw']:
        source = Path(record['path'])
        assert sha256(source) == record['sha256'], source
        checked_hashes[str(source)] = record['sha256']
        raw_paths[source.name] = source
    raw_etf = None
    if symbol != 'NIFTY50_TRI':
        raw_etf = pd.read_parquet(next(p for p in raw_paths.values() if p.suffix == '.parquet'))
    selected = flags[(flags.Asset == symbol) & flags['Simple return'].notna()]
    for event in selected.to_dict('records'):
        pos = int(np.flatnonzero(frame.date.eq(pd.Timestamp(event['Date'])))[0])
        assert pos > 0
        current, previous = frame.iloc[pos], frame.iloc[pos-1]
        source_prices = []
        source_ids = []
        for row in (previous, current):
            if raw_etf is not None:
                source_prices.append(float(raw_etf.loc[row.date, 'Close']))
                source_ids.append(f'{symbol} raw yfinance frame / {row.date.date()} / Close')
            else:
                source_path = raw_paths[row.source_file]
                original_row = json.loads(source_path.read_text(encoding='utf-8-sig'))[int(row.source_row)-1]
                source_prices.append(float(str(original_row['TotalReturnsIndex']).replace(',', '')))
                source_ids.append(f'{row.source_file} / JSON row {int(row.source_row)} / TotalReturnsIndex')
        computed = source_prices[1] / source_prices[0] - 1
        matched = source_prices == [previous.price, current.price]
        correct = bool(np.isclose(computed, current.simple_return, rtol=1e-10, atol=1e-12))
        assert matched and correct
        returns.append({'asset': symbol, 'date': event['Date'],
            'previous_date': previous.date.date().isoformat(), 'previous_price': previous.price,
            'price': current.price, 'simple_return': current.simple_return, 'log_return': current.log_return,
            'reason_flagged': event['Reason flagged'], 'prices_equal_archived_source': matched,
            'return_matches_source_ratio': correct, 'previous_source_identifier': source_ids[0],
            'current_source_identifier': source_ids[1],
            'recorded_dividend_on_date': current.get('dividends', np.nan),
            'recorded_split_on_date': current.get('stock_splits', np.nan),
            'review_status': 'SOURCE_AND_ARITHMETIC_CONFIRMED; INDEPENDENT_EVENT_PRICE_CHECK_PENDING'})
    datasets.append({'asset': symbol, **{key: detail['summary'][key] for key in (
        'currency', 'observation_count', 'invalid_price_count', 'duplicate_asset_date_excess',
        'suspicious_return_count', 'unverified_absent_weekdays', 'return_checks', 'validation_status')}})

calendar = pd.read_csv(REPORTS / 'calendar_review.csv')
weekend_frame = pd.read_csv(REPORTS / 'special_session_review.csv')
calendar_review = json.loads((REPORTS / 'calendar_verification_manifest.json').read_text(encoding='utf-8'))
assert calendar_review['audit_id'] == audit['audit_id']
return_frame = pd.DataFrame(returns).sort_values(['date', 'asset'])
write_text(return_frame.to_csv(index=False, lineterminator='\n'), REPORTS / 'return_review.csv')

lines = ['# Dataset manual-review worksheet', '',
    f"Based on audit `{audit['audit_id']}`. Original source datasets remain unchanged.", '',
    'No confirmed price, duplicate-date or return-formula errors were found by the saved audit. WARNING status reflects statistical return flags and the one remaining NSE calendar question. Flags do not establish that observations are incorrect.', '',
    '| Asset | Currency | Observations | Invalid prices | Duplicate excess | Return-review dates | Unverified weekday absences |',
    '|---|---|---:|---:|---:|---:|---:|']
for s in datasets:
    lines.append('| ' + ' | '.join(str(s[k]) for k in ('asset', 'currency', 'observation_count',
        'invalid_price_count', 'duplicate_asset_date_excess', 'suspicious_return_count', 'unverified_absent_weekdays')) + ' |')
lines += ['', '## Every flagged return date', '',
    f'All {len(returns)} flagged asset-date returns were recomputed from the two original source prices. Every value reconciles. This confirms archive/normalization/arithmetic consistency, not independent-vendor accuracy. ETF adjusted closes were also compared with a second Yahoo retrieval; both captures use the same vendor.', '',
    'The full-period median/MAD rule identifies unusually large moves. The absolute threshold is 10%. These are descriptive flags only. No returns are removed or winsorized.', '',
    '| Date | SPY simple return | VT simple return | NIFTY TRI simple return |', '|---|---:|---:|---:|']
pivot = return_frame.pivot(index='date', columns='asset', values='simple_return')
for day, row in pivot.iterrows():
    cells = [f'{row.get(a):+.4%}' if pd.notna(row.get(a)) else '-' for a in ('SPY', 'VT', 'NIFTY50_TRI')]
    lines.append('| ' + ' | '.join([day] + cells) + ' |')
lines += ['', 'A dash means the asset/date was not flagged, not that its observation is missing. `return_review.csv` records both prices, source row identifiers and corporate actions.', '',
    '## Calendar review', '',
    f"The historical review resolves {calendar_review['confirmed_historical_closure_asset_dates']} of {len(calendar)} original asset-date closure flags. "
    f"All {calendar_review['confirmed_historical_weekend_observations']} pre-2026 weekend observations have exchange evidence and remain in the dataset. "
    'SPY and VT calendar checks pass for 2012 through November 2, 2026. NSE has one explicit uncertainty: April 24, 2014, likely an election closure but still awaiting cash-market exchange evidence. Zero confirmed missing sessions were found.', '',
    'See [calendar_verification.md](calendar_verification.md) for each year, individual source references and evidence qualifications. `calendar_review.csv` preserves the original historical absence queue with current resolution status; `special_session_review.csv` records every weekend observation.', '',
    '## Remaining manual review', '',
    '1. Obtain cash-market exchange confirmation of the NSE closure on April 24, 2014. Its surrounding observed return is preserved but is not marked calendar-verified.',
    f'2. Independently corroborate or document acceptance of the {len(returns)} flagged market moves. Current source prices and arithmetic agree, but that does not provide independent-vendor verification.',
    '3. Preserve the provenance limitations: current-vintage Yahoo adjustments; no observed ETF splits in this sample; original NSE HTTP-completion timestamps were not separately recorded.', '',
    'All three datasets remain WARNING / MANUAL_REVIEW_REQUIRED. No forecasting experiments or final-holdout scoring were performed by this review.', '',
    'Reproduce:', '', '```powershell', r'.\.venv\Scripts\python.exe scripts/review_dataset_flags.py', '```', '']
write_text('\n'.join(lines), REPORTS / 'dataset_manual_review.md')
assert all(sha256(Path(p)) == digest for p, digest in checked_hashes.items())
write_json({'audit_id': audit['audit_id'], 'audit_manifest_sha256': sha256(audit_path),
    'original_raw_file_hashes_verified': checked_hashes, 'flagged_returns_recomputed': len(returns),
    'all_flagged_returns_match_original_source_ratios': True,
    'calendar_entries': len(calendar),
    'primary_source_confirmed_closure_asset_dates': calendar_review['confirmed_historical_closure_asset_dates'],
    'unverified_calendar_asset_dates': calendar_review['unverified_historical_asset_dates'],
    'unverified_special_sessions': int(weekend_frame.review_status.ne('SPECIAL_SESSION_CONFIRMED').sum()),
    'original_audit_status_unchanged': True,
    'outputs': {name: sha256(REPORTS / name) for name in ('return_review.csv', 'calendar_review.csv',
        'special_session_review.csv', 'dataset_manual_review.md')}}, REPORTS / 'dataset_manual_review_manifest.json')
print(f'Reviewed {len(returns)} source returns. Original data and audit preserved.')
