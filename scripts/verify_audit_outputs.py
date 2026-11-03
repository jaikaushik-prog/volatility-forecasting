"""Read-only real-artifact checks, kept separate from synthetic pytest fixtures."""
import json
from pathlib import Path

import pandas as pd

from volrisk.data.storage import sha256, write_json

ROOT = Path(__file__).resolve().parents[1]
pointer = json.loads((ROOT / 'reports/latest_audit.json').read_text(encoding='utf-8'))
audit = json.loads(Path(pointer['manifest']).read_text(encoding='utf-8'))
ingestion = json.loads(Path(audit['input_manifest']).read_text(encoding='utf-8'))
entries = {e['symbol']: e for e in ingestion['assets']}
checks = []
for name, digest in audit['inputs_sha256'].items():
    path = Path(name)
    assert digest is not None and path.is_file() and sha256(path) == digest, name
for name, digest in audit['output_sha256'].items():
    assert sha256(Path(name)) == digest, name
for detail in audit['assets']:
    symbol = detail['summary']['asset']
    assert symbol in audit['canonical'], f'{symbol}: no publishable canonical artifact'
    raw = entries[symbol]['raw']
    assert all(sha256(Path(r['path'])) == r['sha256'] for r in raw)
    original = pd.read_parquet(entries[symbol]['quality']['processed']['path'])
    canonical = pd.read_parquet(audit['canonical'][symbol])
    # This assertion is deliberately specific to the current real-data run, which has
    # no confirmed missing sessions. Future runs with exclusions need explicit review.
    pd.testing.assert_frame_equal(canonical[original.columns], original)
    assert detail['original_return_audit']['status'] == 'PASS'
    assert detail['canonical_return_audit']['status'] == 'PASS'
    assert detail['source_audit']['total_return_compatible'] is True
    assert len(detail['figures']) == 5
    checks.append({'asset': symbol, 'observations': len(canonical),
                   'original_columns_unchanged': True, 'raw_hashes_unchanged': True,
                   'return_checks': 'PASS', 'source_convention_verified': True,
                   'figures_exist': 5, 'validation_status': detail['summary']['validation_status']})
result = {'audit_id': audit['audit_id'], 'data_type': 'real saved source observations; not synthetic test results',
          'input_file_hashes_verified': len(audit['inputs_sha256']),
          'output_file_hashes_verified': len(audit['output_sha256']), 'assets': checks}
write_json(result, ROOT / 'reports/sprint1b_verification.json')
print(json.dumps(result, indent=2))
