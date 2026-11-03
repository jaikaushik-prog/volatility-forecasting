"""Archive public exchange notices without changing existing source bytes.

Optional acquisition utility: pip install pypdf beautifulsoup4 requests.
Usage: python scripts/collect_calendar_evidence.py config/calendar_sources.json
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/calendar_evidence/20261103'
TEXT = ROOT / 'reports/calendar_evidence_text'


def acquire(item):
    path = RAW / item['file']
    meta = path.with_suffix(path.suffix + '.json')
    try:
        if path.exists():
            saved = json.loads(meta.read_text(encoding='utf-8'))
            if saved['url'] != item['url'] or saved['sha256'] != hashlib.sha256(path.read_bytes()).hexdigest():
                raise ValueError('Existing evidence metadata/hash mismatch')
        else:
            response = requests.get(item['url'], timeout=45, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            content = response.content
            if path.suffix == '.pdf' and not content.startswith(b'%PDF'):
                raise ValueError('Expected PDF, received another content type')
            saved = dict(item, retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                         final_url=response.url, sha256=hashlib.sha256(content).hexdigest())
            path.write_bytes(content)
            meta.write_text(json.dumps(saved, indent=2) + '\n', encoding='utf-8')
        extracted = TEXT / (path.stem + '.txt')
        if extracted.exists():
            return {'file': item['file'], 'status': 'archived', 'characters': len(extracted.read_text(encoding='utf-8'))}
        if path.suffix == '.pdf':
            body = '\n\n'.join(f'PAGE {i+1}\n{p.extract_text()}' for i, p in enumerate(PdfReader(path).pages))
        else:
            body = BeautifulSoup(path.read_bytes(), 'html.parser').get_text(' ', strip=True)
        extracted.write_text(body, encoding='utf-8')
        return {'file': item['file'], 'status': 'archived', 'characters': len(body)}
    except Exception as exc:
        return {'file': item['file'], 'status': 'unavailable', 'error': str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalog', type=Path)
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    TEXT.mkdir(parents=True, exist_ok=True)
    catalog = json.loads(args.catalog.read_text(encoding='utf-8'))
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(acquire, catalog))
    print(json.dumps(results, indent=2))
    (TEXT / 'retrieval_status.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    if any(r['status'] != 'archived' for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
