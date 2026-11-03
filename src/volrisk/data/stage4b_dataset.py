"""Read only Stage 4's immutable pre-2025 panels; no raw/intraday/holdout loader."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

from .storage import sha256
from .har_dataset import ReadinessError

HARD_CUTOFF = pd.Timestamp('2024-12-31')


def validate_panel(panel):
    if panel.empty or panel.index.max() > HARD_CUTOFF:
        raise ReadinessError('Only nonempty pre-2025 panels are permitted')
    if not panel.index.is_unique or not panel.index.is_monotonic_increasing:
        raise ReadinessError('Unsorted or duplicated session dates')
    for column in ('rv', 'intraday', 'overnight_squared', 'intraday_overnight', 'vix_implied_variance'):
        values = panel[column]
        if np.isinf(values).any() or values.dropna().lt(0).any():
            raise ReadinessError('Invalid variance: '+column)
    np.testing.assert_allclose(panel.intraday, panel.rv, equal_nan=True, atol=1e-15)
    np.testing.assert_allclose(panel.intraday_overnight, panel.rv+panel.overnight_squared, equal_nan=True, atol=1e-15)
    if panel.loc[~panel.rv_eligible, 'rv'].notna().any():
        raise ReadinessError('Ineligible sessions contain usable RV')
    v = panel.vix_implied_variance.notna()
    if not panel.loc[v, 'vix_implied_variance'].gt(0).all():
        raise ReadinessError('Nonpositive implied variance')
    previous = panel.index.to_series().shift()
    if not (panel.loc[v, 'vix_source_session'] == previous[v]).all():
        raise ReadinessError('VIX must use exactly the previous native session')
    previous_close = panel.origin_timestamp.shift()
    if not (panel.loc[v, 'vix_available_at'] <= previous_close[v]).all():
        raise ReadinessError('VIX not available by its prior-session close')
    if not (panel.session_open < panel.origin_timestamp).all():
        raise ReadinessError('Invalid session timestamps')
    if str(panel.origin_timestamp.dt.tz) != 'Asia/Kolkata':
        raise ReadinessError('Expected the provisional Asia/Kolkata convention')


def load_stage4(config, root):
    root = Path(root)
    cutoff = pd.Timestamp(config['data']['cutoff'])
    if cutoff != HARD_CUTOFF:
        raise ReadinessError('Stage 4B is restricted to the fixed 2024 cutoff')
    pointer = json.loads((root/config['data']['stage4_pointer']).read_text(encoding='utf-8'))
    source = Path(pointer['run_dir'])
    if sha256(source/'manifest.json') != pointer['manifest_sha256']:
        raise ReadinessError('Stage 4 manifest changed')
    manifest = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    if manifest['run_id'] != config['data']['required_stage4_run'] or not manifest['complete']:
        raise ReadinessError('Unexpected/incomplete Stage 4 source run')
    if manifest['holdout_evaluated'] or pd.Timestamp(manifest['numerical_data_cutoff']) > cutoff:
        raise ReadinessError('Source experiment includes protected observations')
    hashes = {str(source/'manifest.json'): sha256(source/'manifest.json')}
    for relative, expected in manifest['output_sha256'].items():
        path = source/relative
        if sha256(path) != expected:
            raise ReadinessError('Immutable Stage 4 output changed: '+relative)
        hashes[str(path)] = expected
        if relative.startswith('reports/'):
            published = root/'reports'/Path(relative).relative_to('reports')
            if published.exists():
                hashes[str(published)] = sha256(published)
    # No raw data, source intraday datasets or 2025-2026 numerical files are opened.
    panel = pd.read_parquet(source/'panels/NIFTY_5m_eligible.parquet',
                            filters=[('session_date', '<=', cutoff)]).set_index('session_date')
    validate_panel(panel)
    selection = [('asset', '==', 'NIFTY'), ('frequency', '==', 5), ('scenario', '==', 'eligible')]
    forecasts = pd.read_parquet(source/'forecasts.parquet', filters=selection+[('target_date', '<=', cutoff)])
    fits = pd.read_parquet(source/'fits.parquet', filters=selection+[('origin_date', '<=', cutoff)])
    return panel, forecasts, fits, manifest, hashes


def assert_unchanged(hashes):
    for filename, expected in hashes.items():
        if sha256(Path(filename)) != expected:
            raise ReadinessError('Historical Stage 4 artifact modified: '+filename)
