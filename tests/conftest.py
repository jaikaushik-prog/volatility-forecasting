"""All test prices are synthetic and exist only in temporary test directories."""

from datetime import date
import json
from pathlib import Path

import pandas as pd
import pytest

from volrisk.config import DownloadSettings, Settings, ValidationSettings
from volrisk.data.storage import sha256


@pytest.fixture
def audit_pointer():
    """Synthetic audit provenance, separate from real research data."""
    def write(root, canonical, audit_id='synthetic'):
        root = Path(root)
        manifest = root / 'reports' / 'synthetic_audit.json'
        assets = [{'summary': {'asset': a, 'validation_status': 'PASS', 'return_checks': 'PASS'},
                   'data_artifact': {'path': str(p), 'sha256': sha256(Path(p))},
                   'source_audit': {'total_return_compatible': True}} for a, p in canonical.items()]
        manifest.write_text(json.dumps({'audit_id': audit_id, 'assets': assets}), encoding='utf-8')
        pointer = root / 'reports' / 'latest_audit.json'
        pointer.write_text(json.dumps({'audit_id': audit_id, 'complete': True, 'manifest': str(manifest),
                                       'canonical': canonical}), encoding='utf-8')
        return pointer
    return write


@pytest.fixture
def settings(tmp_path):
    return Settings(
        start=date(2024, 1, 2), end=date(2024, 1, 4),
        raw_dir=tmp_path / "data/raw", processed_dir=tmp_path / "data/processed",
        reports_dir=tmp_path / "reports", nifty_csv_dir=tmp_path / "inputs",
        download=DownloadSettings(attempts=2, timeout_seconds=1, retry_backoff_seconds=0),
        validation=ValidationSettings(min_observations=2),
    )


@pytest.fixture
def raw_frame():
    return pd.DataFrame(
        {"Close": [100.0, 101.0, 99.0], "Dividends": [0.0, 0.2, 0.0], "Stock Splits": [0.0, 0.0, 0.0]},
        index=pd.date_range("2024-01-02", periods=3, name="Date"),
    )
