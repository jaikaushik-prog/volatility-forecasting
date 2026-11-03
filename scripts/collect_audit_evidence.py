"""Optional network evidence capture. Never replaces Sprint 1A source prices."""
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
import urllib.request

import yfinance as yf
from yfinance.utils import auto_adjust

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/raw/audit_evidence/20261103'
OUT.mkdir(parents=True, exist_ok=True)
yf.set_tz_cache_location(str(OUT / '.cache'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

for symbol in ('SPY', 'VT'):
    target = OUT / f'{symbol}_adjustment_reference.parquet'
    metadata = OUT / f'{symbol}_adjustment_reference.json'
    if target.exists() or metadata.exists():
        if not target.is_file() or not metadata.is_file():
            raise RuntimeError(f'{symbol}: incomplete existing evidence; inspect it instead of overwriting')
        saved = json.loads(metadata.read_text(encoding='utf-8'))
        if saved.get('sha256') != digest(target):
            raise RuntimeError(f'{symbol}: existing evidence hash mismatch; original evidence retained')
        print(f'{symbol}: existing evidence retained', flush=True)
        continue
    request = dict(tickers=symbol, start='2012-01-01', end='2026-11-03', interval='1d',
                   auto_adjust=False, actions=True, back_adjust=False, repair=False,
                   keepna=True, rounding=False, threads=False, progress=False,
                   ignore_tz=True, multi_level_index=False, timeout=30)
    frame = yf.download(**request)
    if frame is None or frame.empty or not {'Close', 'Adj Close'} <= set(frame):
        raise RuntimeError(f'{symbol}: adjustment reference unavailable')
    frame.to_parquet(target, index=True)
    metadata.write_text(json.dumps({'symbol': symbol, 'currency': 'USD', 'request': request,
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(), 'yfinance_version': yf.__version__,
        'file': target.name, 'sha256': digest(target),
        'source_url': f'https://finance.yahoo.com/quote/{symbol}/history/',
        'limitation': 'Same-provider, current-vintage comparison; not independent-vendor or point-in-time evidence.'}, indent=2), encoding='utf-8')
    print(f'{symbol}: {len(frame)} adjustment reference rows saved', flush=True)

code = OUT / 'yfinance_auto_adjust.py.txt'
if not code.exists():
    code.write_text(inspect.getsource(auto_adjust), encoding='utf-8')
sources = {
    'nyse_2026.html': 'https://www.nyse.com/trade/hours-calendars',
    'nse_2026_holidays.pdf': 'https://nsearchives.nseindia.com/content/circulars/CMTR71775.pdf',
    'nse_2026_election.pdf': 'https://nsearchives.nseindia.com/content/circulars/CMTR72260.pdf',
    'nse_2026_budget.pdf': 'https://nsearchives.nseindia.com/content/circulars/CMTR72349.pdf',
}
manifest = []
for name, url in sources.items():
    target = OUT / name
    if not target.exists():
        with urllib.request.urlopen(url, timeout=30) as response:
            target.write_bytes(response.read())
    manifest.append({'file': name, 'url': url, 'sha256': digest(target),
                     'archived_at_utc': datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).isoformat()})
manifest_path = OUT / 'calendar_sources.json'
if manifest_path.exists():
    if json.loads(manifest_path.read_text(encoding='utf-8')) != manifest:
        raise RuntimeError('Calendar evidence differs from its existing manifest; inspect instead of overwriting')
else:
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('Calendar source documents archived', flush=True)
