"""Compile reviewed exchange schedules. Never reads market observations.

Run from any working directory: python scripts/build_calendars.py
Manual transcriptions are research inputs, not inferred holiday rules.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config'
RAW = ROOT / 'data/raw/calendar_evidence/20261103'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    original = read(CONFIG / 'calendar_2026_transcription.json')
    amendments = read(CONFIG / 'calendar_amendments.json')
    old_sources = {s['file']: s for s in read(ROOT / 'data/raw/audit_evidence/20261103/calendar_sources.json')}
    evidence = {}

    def register(name):
        path = RAW / name
        if name in old_sources:
            path = ROOT / 'data/raw/audit_evidence/20261103' / name
            meta = old_sources[name]
        elif path.suffix == '.json':
            meta = read(path)
            if meta.get('artifact_kind') != 'researcher_transcription_from_web_reader':
                raise ValueError(f'Unknown evidence type: {name}')
        else:
            meta_path = path.with_suffix(path.suffix + '.json')
            meta = read(meta_path)
            evidence[meta_path] = {'kind': 'retrieval_metadata'}
        if 'sha256' in meta and digest(path) != meta['sha256']:
            raise ValueError(f'Archived source changed: {path}')
        evidence[path] = {'kind': meta.get('artifact_kind', 'original_source_bytes'), 'url': meta['url']}
        return meta['url']

    result = {'as_of': original['as_of'], 'schema_version': 2,
        'scope_note': 'Reviewed 2012-2025 annual schedules plus amendments and existing 2026 schedule through November 2. Explicit unverified dates are holes in coverage. No holidays inferred from price data.',
        'markets': {}, 'evidence_files': []}
    for market, name in [('NYSE', 'nyse'), ('NSE', 'nse')]:
        years = read(CONFIG / f'calendar_{name}_transcription.json')
        spec26 = original['markets'][market]
        files26 = ['nyse_2026.html'] if market == 'NYSE' else ['nse_2026_holidays.pdf', 'nse_2026_election.pdf', 'nse_2026_budget.pdf']
        years['2026'] = {**spec26, 'source_files': files26}
        holidays, special, uncertain = set(), set(), set()
        records, urls, yearly = {}, set(), {}
        for year, spec in sorted(years.items()):
            files = spec.get('source_files') or [spec['source_file']]
            yearly[year] = files
            urls.update(register(f) for f in files)
            for field, kind, reason in [('holidays', 'close', 'Annual exchange trading holiday'),
                                        ('special_sessions', 'open', 'Muhurat trading session' if year != '2026' else 'Budget special session')]:
                values = spec[field]
                if len(values) != len(set(values)) or any(not d.startswith(year + '-') for d in values):
                    raise ValueError(f'Invalid/duplicate {market} {year} dates')
                (holidays if kind == 'close' else special).update(values)
                for day in values:
                    records[day] = {'date': day, 'action': kind, 'reason': reason, 'source_files': files}
        for change in amendments:
            if change['market'] != market:
                continue
            day, action = change['date'], change['action']
            if action not in {'open', 'close', 'unverified'}:
                raise ValueError(f'Invalid calendar amendment: {change}')
            urls.update(register(f) for f in change['source_files'])
            if action == 'open':
                holidays.discard(day)
                special.add(day)
            elif action == 'close':
                special.discard(day)
                holidays.add(day)
            else:
                holidays.discard(day)
                special.discard(day)
                uncertain.add(day)
            records[day] = {k: v for k, v in change.items() if k != 'market'}
        if holidays & special or uncertain & (holidays | special):
            raise ValueError(f'Contradictory {market} dates')
        result['markets'][market] = {
            'timezone': spec26['timezone'], 'verified_start': '2012-01-01',
            'verified_end': spec26['verified_end'], 'holidays': sorted(holidays),
            'special_sessions': sorted(special), 'unverified_dates': sorted(uncertain),
            'sources': sorted(urls), 'annual_source_files': yearly,
            'date_evidence': [records[d] for d in sorted(records)],
            'note': spec26['note'] + ' Explicit unverified_dates are excluded from authoritative session counts.'}
    for name in ['calendar_nse_transcription.json', 'calendar_nyse_transcription.json',
                 'calendar_2026_transcription.json', 'calendar_amendments.json']:
        evidence[CONFIG / name] = {'kind': 'reviewed_transcription_or_amendment'}
    evidence[ROOT / 'data/raw/audit_evidence/20261103/calendar_sources.json'] = {'kind': 'retrieval_metadata'}
    for path, metadata in sorted(evidence.items()):
        relative = path.relative_to(ROOT).as_posix()
        relative = relative.removeprefix('config/') if path.parent == CONFIG else '../' + relative
        result['evidence_files'].append({'path': relative, 'sha256': digest(path), **metadata})
    target = CONFIG / 'calendars.json'
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'Compiled {len(result["evidence_files"])} evidence inputs; no price data read.')


if __name__ == '__main__':
    build()
