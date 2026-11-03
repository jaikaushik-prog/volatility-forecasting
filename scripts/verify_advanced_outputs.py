"""Read-only checks of real Stage 3 artifacts; synthetic unit tests remain separate.

Does not load sealed holdout return values. Writes only a verification receipt in reports/.
Run after the full advanced CLI experiment, not after a shortened smoke run.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from volrisk.data.returns import load_canonical_returns
from volrisk.data.storage import sha256, write_json


def verify(root: Path) -> dict:
    pointer = json.loads((root / 'reports/latest_advanced.json').read_text(encoding='utf-8'))
    manifest_path = Path(pointer['manifest'])
    assert sha256(manifest_path) == pointer['manifest_sha256'], 'Published manifest changed'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    run = Path(manifest['run_dir'])
    assert manifest['holdout_sealed'] and manifest['effective_experiment']['max_origins'] is None
    assert len(manifest['models']) == 12, 'Expected all ten incumbents and both challengers'
    for name, digest in manifest['output_sha256'].items():
        assert sha256(run / name) == digest, f'Output changed: {name}'
    for name, digest in manifest['implementation_sha256'].items():
        assert sha256(root / 'src/volrisk' / name) == digest, f'Implementation changed since run: {name}'
    assert sha256(Path(manifest['config_path'])) == manifest['config_sha256']
    cutoff = pd.Timestamp(manifest['modeling_data_cutoff'])
    source_pointer = root / manifest['effective_configuration']['data']['latest_audit']
    series = load_canonical_returns(source_pointer, end_date=cutoff, preserve_gaps=True,
                                    require_verified_intervals=True)
    audit_pointer = json.loads(source_pointer.read_text(encoding='utf-8'))
    audit = json.loads(Path(audit_pointer['manifest']).read_text(encoding='utf-8'))
    ingestion = json.loads(Path(audit['input_manifest']).read_text(encoding='utf-8'))
    raw_files = 0
    for item in ingestion['assets']:
        for raw in item['raw']:
            assert sha256(Path(raw['path'])) == raw['sha256'], raw['path']
            raw_files += 1
    forecasts = pd.read_parquet(run / 'forecasts.parquet')
    fits = pd.read_parquet(run / 'fits.parquet')
    metrics = pd.read_csv(run / 'advanced_model_metrics.csv')
    assert forecasts.origin_date.max() <= cutoff and fits.origin_date.max() <= cutoff
    assert forecasts.target_date.dropna().max() <= cutoff
    assert 'holdout' not in set(forecasts.period) | set(metrics.period)
    assert not forecasts.duplicated(['asset', 'model', 'origin_date']).any()
    valid = forecasts[forecasts.forecast_valid.astype(bool)]
    assert np.isfinite(valid.forecast_variance).all() and (valid.forecast_variance > 0).all()
    np.testing.assert_allclose(valid.forecast_volatility_annualized, np.sqrt(252 * valid.forecast_variance))
    assert (fits.loc[fits.status.ne('failed'), 'training_end'] <= fits.loc[fits.status.ne('failed'), 'origin_date']).all()
    common = forecasts[forecasts.common.astype(bool)]
    counts = common.groupby(['asset', 'target_date']).model.nunique()
    assert counts.eq(12).all()
    summaries = []
    for asset, s in series.items():
        assert manifest['data'][asset]['source_sha256'] == s.source_sha256
        rows = forecasts[forecasts.asset.eq(asset)]
        finite = s.log_returns.dropna()
        assert rows.origin_date.isin(finite.index).all()
        targets = rows[rows.target_observed.astype(bool)]
        expected_next = pd.Series(s.log_returns.index[1:], index=s.log_returns.index[:-1])
        np.testing.assert_array_equal(targets.target_date, expected_next.reindex(targets.origin_date))
        np.testing.assert_allclose(targets.realized_log_return, finite.reindex(targets.target_date))
        # No fitted window or supervised pair crosses any excluded calendar interval.
        for gap in s.log_returns.index[s.log_returns.isna()]:
            asset_fits = fits[fits.asset.eq(asset) & fits.status.ne('failed')]
            assert not ((asset_fits.training_start <= gap) & (asset_fits.training_end >= gap)).any()
        selected = metrics[metrics.asset.eq(asset) & metrics.period.eq('validation') & metrics['sample'].eq('common')]
        assert len(selected) == 12 and selected.n_evaluated.nunique() == 1
        summaries.append({'asset': asset, 'currency': s.currency, 'validation_common_sessions': int(selected.n_evaluated.iloc[0]),
                          'calendar_intervals_excluded': s.dropped['unverified_return_dates'],
                          'audit_status': s.audit_status})
    for row in forecasts[forecasts.model.eq('markov_switching_2') & forecasts.forecast_valid.astype(bool)].itertuples():
        state = json.loads(row.model_state)
        p, transition, variances = (np.asarray(state[k]) for k in ('filtered_probabilities', 'transition', 'state_variances'))
        assert variances[0] <= variances[1] and (p >= 0).all()
        np.testing.assert_allclose(transition.sum(axis=1), 1.)
        np.testing.assert_allclose(p.sum(), 1.)
        np.testing.assert_allclose(p @ transition @ variances, row.forecast_variance)
        assert pd.Timestamp(state['origin']) == row.origin_date
    development_end = pd.Timestamp(manifest['splits']['development'][1])
    for row in fits[fits.model.eq('xgboost_v1') & fits.status.ne('failed')].itertuples():
        diag, parameters = json.loads(row.diagnostics), json.loads(row.params)
        assert pd.Timestamp(diag['training_feature_end']) < pd.Timestamp(diag['training_label_end']) <= row.origin_date
        selection_date = parameters['selection_date']
        assert selection_date is None or pd.Timestamp(selection_date) <= development_end
        for candidate in diag['tuning_candidates']:
            assert row.origin_date <= development_end
            for fold in candidate['folds']:
                assert pd.Timestamp(fold['training_label_end']) <= pd.Timestamp(fold['validation_origin_start'])
                assert pd.Timestamp(fold['validation_label_end']) <= row.origin_date
    return {'run_id': manifest['run_id'], 'status': 'PASS', 'artifact_hashes_verified': len(manifest['output_sha256']),
            'raw_source_files_unchanged': raw_files, 'sealed_cutoff': str(cutoff.date()),
            'forecast_rows': len(forecasts), 'fit_attempts': len(fits), 'assets': summaries,
            'scope': 'Artifact, provenance and temporal checks; does not certify statistical superiority or remove prior holdout exposure.'}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    result = verify(root)
    write_json(result, root / 'reports/advanced_verification.json')
    print(json.dumps(result, indent=2))
