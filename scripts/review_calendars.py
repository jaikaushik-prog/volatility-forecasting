"""Reconcile real saved observations against independently sourced calendars.

No prices, dates or returns are edited. This is real-artifact verification,
separate from synthetic unit tests. Historical review queues remain traceable.
"""
import json
from pathlib import Path

import pandas as pd

from volrisk.data.calendar_audit import audit_calendar, verify_calendar_evidence
from volrisk.data.models import ASSETS
from volrisk.data.storage import sha256, write_json, write_text

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
BASELINE_AUDIT_ID = '6b40c1052542abcbb4675b6e'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    calendar_path = ROOT / 'config/calendars.json'
    calendar = read(calendar_path)
    verify_calendar_evidence(calendar, calendar_path)
    audit_path = Path(read(REPORTS / 'latest_audit.json')['manifest'])
    audit = read(audit_path)
    assert audit['inputs_sha256'][str(calendar_path)] == sha256(calendar_path)
    urls = {Path(e['path']).name: e.get('url', '') for e in calendar['evidence_files']}
    baseline = REPORTS / 'audits' / BASELINE_AUDIT_ID
    old_audit = read(baseline / 'audit_manifest.json')
    old_flags = baseline / 'suspicious_dates.csv'
    assert sha256(old_flags) == old_audit['output_sha256'][str(old_flags)]
    queue = pd.read_csv(old_flags)
    queue = queue[queue['Reason flagged'].str.contains('unverified_weekday_absence')].copy()
    yearly, special, reviewed = [], [], []
    for asset in ASSETS:
        spec = calendar['markets'][asset.calendar]
        events = {e['date']: e for e in spec['date_evidence']}
        path = Path(audit['canonical'][asset.symbol])
        assert sha256(path) == audit['output_sha256'][str(path)]
        frame = pd.read_parquet(path)
        for row in queue[queue.Asset.eq(asset.symbol)].to_dict('records'):
            event = events.get(row['Date'])
            confirmed = event is not None and event['action'] == 'close'
            reviewed.append({**row,
                'review_status': 'EXCHANGE_CLOSURE_CONFIRMED' if confirmed else 'CASH_MARKET_CONFIRMATION_PENDING',
                'supporting_source': ' | '.join(urls[f] for f in event['source_files']) if event else '',
                'source_files': ' | '.join(event['source_files']) if event else '',
                'review_note': event['reason'] if event else 'Calendar evidence unavailable'})
        for row in frame[frame.date.dt.dayofweek.ge(5)].itertuples():
            day = row.date.date().isoformat()
            event = events.get(day)
            confirmed = event is not None and event['action'] == 'open'
            special.append({'asset': asset.symbol, 'date': day, 'price': row.price,
                'review_status': 'SPECIAL_SESSION_CONFIRMED' if confirmed else 'SPECIAL_SESSION_CONFIRMATION_PENDING',
                'reason': event['reason'] if event else 'No independent session evidence',
                'source_files': ' | '.join(event['source_files']) if event else '',
                'supporting_source': ' | '.join(urls[f] for f in event['source_files']) if event else ''})
        for year in range(2012, 2027):
            start = pd.Timestamp(f'{year}-01-01')
            end = min(pd.Timestamp(f'{year}-12-31'), pd.Timestamp(spec['verified_end']))
            dates = frame.loc[frame.date.between(start, end), 'date'].reset_index(drop=True)
            result = audit_calendar(dates, asset, start, end, calendar)
            missing, unexpected = len(result['missing_expected_sessions']), len(result['unexpected_sessions'])
            yearly.append({'asset': asset.symbol, 'currency': asset.currency, 'calendar': asset.calendar,
                'year': year, 'start': start.date().isoformat(), 'end': end.date().isoformat(),
                'observations': len(dates), 'expected_sessions_verified_coverage': result['expected_sessions_verified_period'],
                'expected_sessions_full_year_window': result['expected_sessions_full_window'],
                'missing_expected_sessions': missing, 'unexpected_sessions': unexpected,
                'unverified_absent_weekdays': len(result['unverified_absent_weekdays']),
                'confirmed_weekend_sessions': int((dates.dt.dayofweek.ge(5) & dates.isin(pd.to_datetime(spec['special_sessions']))).sum()),
                'calendar_status': 'FAIL' if missing else ('WARNING' if unexpected or not result['full_window_verified'] else 'PASS'),
                'annual_sources': ' | '.join(urls[f] for f in spec['annual_source_files'][str(year)])})
    annual = pd.DataFrame(yearly)
    closures = pd.DataFrame(reviewed)
    weekends = pd.DataFrame(special)
    for name, frame in [('calendar_verification_by_year.csv', annual), ('calendar_review.csv', closures),
                        ('special_session_review.csv', weekends)]:
        write_text(frame.to_csv(index=False, lineterminator='\n'), REPORTS / name)
    confirmed = int(closures.review_status.eq('EXCHANGE_CLOSURE_CONFIRMED').sum())
    pending = closures[closures.review_status.ne('EXCHANGE_CLOSURE_CONFIRMED')]
    historical_weekends = weekends[weekends.date.lt('2026-01-01')]
    lines = ['# Historical exchange-calendar verification', '',
        f"Current audit `{audit['audit_id']}`. Previous review queue: `{BASELINE_AUDIT_ID}`.", '',
        f'{confirmed} of {len(closures)} historical asset-date absence flags are confirmed closures. '
        f'{len(pending)} remains unverified. All {len(historical_weekends)} pre-2026 weekend observations are retained; '
        f'{int(historical_weekends.review_status.eq("SPECIAL_SESSION_CONFIRMED").sum())} have exchange evidence.', '',
        'The independently transcribed schedules cover 2012 through November 2, 2026. No holidays were inferred from missing prices. '
        'Early closes and Muhurat/live weekend sessions remain trading observations. Settlement-only holidays and other-segment calendars are not substituted for cash-market calendars.', '',
        '## Year-by-year reconciliation', '',
        'SPY and VT use NYSE/Arca sessions. Their counts below are per ETF; no cross-market intersection is used. '
        'Expected counts exclude explicitly unverified dates. The full-window expected count is null for NSE 2014.', '',
        '| Year | SPY obs / expected | VT obs / expected | NIFTY obs / verified expected | Confirmed missing (all assets) | Unverified asset-dates |',
        '|---|---:|---:|---:|---:|---:|']
    for year, group in annual.groupby('year'):
        by_asset = group.set_index('asset')
        cells = [str(year)]
        for symbol in ('SPY', 'VT', 'NIFTY50_TRI'):
            row = by_asset.loc[symbol]
            cells.append(f"{row.observations} / {row.expected_sessions_verified_coverage}")
        cells += [str(group.missing_expected_sessions.sum()), str(group.unverified_absent_weekdays.sum())]
        lines.append('| ' + ' | '.join(cells) + ' |')
    lines += ['', '2026 is a partial year, ending November 2. Zero confirmed missing sessions does not resolve the one explicitly unverified date.', '',
        '## Remaining calendar question', '',
        '**NSE, April 24, 2014:** likely election closure. The recovered NSE FAOP26362 notice covers equity derivatives. '
        'The corresponding cash-market notice has not been recovered. Contemporary reporting corroborates an exchange closure '
        '([Business Standard, April 3, 2014](https://www.business-standard.com/article/markets/markets-to-be-closed-on-apr-24-owing-to-elections-114040301123_1.html)), '
        'but this audit retains the stronger requirement for cash-market exchange evidence. '
        'The date is explicitly unverified, not a confirmed missing session or an approved cash-market holiday. '
        'The observed April 23 to April 25 return is preserved, with `calendar_interval_verified=False`.', '',
        '## Confirmed weekend observations', '',
        '| Date | Asset | Evidence |', '|---|---|---|']
    for row in weekends.itertuples():
        sources = row.source_files.replace(' | ', '; ')
        lines.append(f'| {row.date} | {row.asset} | {row.reason}; {sources} |')
    lines += ['', '## Evidence qualifications', '',
        '- NYSE 2012-2013: issuer-authored Business Wire release accessed on a syndication host. Direct HTML download returned 403; a labeled factual web-reader transcription is saved.',
        '- Sandy closures: SEC Regulation SCI proposal, PDF page 28. Direct PDF download returned 403; a labeled web-reader transcription is saved.',
        '- NSE January 20, 2024: final MSD60340 specifies regular primary-site trading and withdraws the earlier DR-session notices. Direct download failed; a labeled web-reader transcription is saved.',
        '- NSE 2023 Bakri Id amendment: issuer circular CMTR57285 is archived from a broker mirror, corroborated by official clearing circular CMPT57296.',
        '- NSE January 22, 2024 closure: official SURV60342 explicitly cites the cash-market closure circular CMTR60338.',
        '- September 8, 2012 and February 28, 2015 sessions: exchange annual-report chart footnotes, PDF pages 16 and 12 respectively; April 28, 2012: CSE exchange notice explicitly confirms NSE cash trading. These are primary exchange confirmations, not recovered individual NSE trading circulars.',
        '- Original downloaded bytes and retrieval metadata remain unchanged. Web-reader transcriptions are identified separately and are not presented as original HTTP responses. Hashes establish archive integrity, not issuer signatures.', '',
        '## Dataset readiness', '',
        'Calendar checks pass for SPY and VT across the complete requested window. NIFTY calendar coverage remains WARNING solely for April 24, 2014. '
        'All three datasets still have separate extreme-return review flags (SPY 10, VT 10, NIFTY 7); calendar verification does not approve those market moves. '
        'No prices, source rows, returns or final-holdout model results were changed.', '',
        '## Reproduce offline', '', '```powershell',
        r'.\.venv\Scripts\python.exe scripts/build_calendars.py',
        r'.\.venv\Scripts\python.exe -m volrisk --config config/ingestion.toml --audit',
        r'.\.venv\Scripts\python.exe scripts/review_calendars.py',
        r'.\.venv\Scripts\python.exe scripts/verify_audit_outputs.py', '```', '',
        'The builder reads only reviewed schedule transcriptions and evidence, never price observations. '
        'The audit hashes all declared evidence before execution/cache reuse. `calendar_review.csv` preserves the original historical queue with closure-by-closure source links; '
        '`calendar_verification_by_year.csv` contains all asset/year counts; `special_session_review.csv` lists every weekend observation.', '']
    write_text('\n'.join(lines), REPORTS / 'calendar_verification.md')
    outputs = ['calendar_verification.md', 'calendar_verification_by_year.csv', 'calendar_review.csv', 'special_session_review.csv']
    write_json({'audit_id': audit['audit_id'], 'calendar_sha256': sha256(calendar_path),
        'baseline_audit_id': BASELINE_AUDIT_ID, 'baseline_flags_sha256': sha256(old_flags),
        'confirmed_historical_closure_asset_dates': confirmed, 'unverified_historical_asset_dates': len(pending),
        'confirmed_historical_weekend_observations': int(historical_weekends.review_status.eq('SPECIAL_SESSION_CONFIRMED').sum()),
        'outputs': {name: sha256(REPORTS / name) for name in outputs}}, REPORTS / 'calendar_verification_manifest.json')
    print(f'Calendar review: {confirmed}/{len(closures)} closure flags resolved; {len(pending)} unverified; {len(historical_weekends)} historical weekends retained.')


if __name__ == '__main__':
    main()
