"""Independent checks on saved Stage 4B results. No post-2024 numerical reads."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

from volrisk.data.storage import sha256, write_json
from volrisk.data.stage4b_dataset import assert_unchanged, validate_panel
from volrisk.forecasting.positive_har import positive_features
from volrisk.evaluation.har_walk_forward import common_dates
from volrisk.evaluation.metrics import qlike

ROOT=Path(__file__).resolve().parents[1]


def verify(root=ROOT):
    pointer=json.loads((root/'reports/latest_stage4b.json').read_text())
    run=Path(pointer['run_dir']); manifest_file=run/'manifest.json'
    assert sha256(manifest_file)==pointer['manifest_sha256']
    m=json.loads(manifest_file.read_text())
    assert m['complete'] and not m['holdout_evaluated'] and not m['independent_confirmation']
    assert m['status']=='PROVISIONAL_EXPLORATORY'
    for rel,digest in m['fingerprint']['code'].items():
        assert sha256(root/rel)==digest,rel
        assert sha256(run/'code'/rel)==digest,rel
    assert sha256(root/'config/stage4b.toml')==m['fingerprint']['config_file_sha256']
    assert_unchanged(m['historical_artifact_hashes'])
    for rel,digest in m['output_sha256'].items():
        assert sha256(run/rel)==digest,rel
        if rel.startswith('reports/'):
            assert sha256(root/'reports'/Path(rel).relative_to('reports'))==digest,rel
    snapshot=root/'experiments/stage4b/stage4_code_snapshot'
    old=json.loads((snapshot/'manifest.json').read_text())
    assert old['stage4_run_id']==m['stage4_run_id']
    for rel,digest in old['implementation_sha256'].items():
        assert sha256(snapshot/rel)==digest,rel
    panel=pd.read_parquet(run/'panel.parquet').set_index('session_date');validate_panel(panel)
    features=positive_features(panel)
    f=pd.read_parquet(run/'forecasts.parquet');fits=pd.read_parquet(run/'fits.parquet')
    assert f.target_date.min()>=pd.Timestamp('2024-01-01')
    assert f.target_date.max()<=pd.Timestamp('2024-12-31')
    assert not f.duplicated(['model','target','target_date']).any()
    np.testing.assert_array_equal(f.target_date,panel.index.to_numpy()[f.origin_index.to_numpy()+1])
    for target,g in f.groupby('target'):
        np.testing.assert_allclose(g.observed_variance,panel[target].reindex(g.target_date),equal_nan=True)
        check=common_dates(g,list(m['model_specifications'][target]))
        np.testing.assert_array_equal(check.common,g.common)
    valid=f[f.forecast_valid]
    assert np.isfinite(valid.forecast_variance).all() and valid.forecast_variance.gt(0).all()
    assert f.loc[~f.forecast_valid,'forecast_variance'].isna().all()
    assert valid.training_end.le(valid.origin_date).all()
    assert valid.forecast_created_at.lt(valid.target_open_timestamp).all()
    np.testing.assert_allclose(valid.forecast_volatility_annualized**2,252*valid.forecast_variance,rtol=1e-12)
    logs=valid[valid.model.str.contains('log_har')]
    assert not logs.prediction_floored.any()
    for row in logs.itertuples():
        p=json.loads(row.params);x=features.loc[row.origin_date]
        log_mean=p['intercept']
        for name in ('rv_daily','rv_weekly','rv_monthly','vix_implied_variance','vix_log_change'):
            if name not in p:continue
            value=x[name]
            if name!='vix_log_change':
                value=np.log(p['zero_rv_transform_floor'] if value==0 else value)
            log_mean+=p[name]*value
        expected=np.exp(log_mean)*p['smearing']
        np.testing.assert_allclose(row.forecast_variance,expected,rtol=1e-10,atol=1e-16)
        if row.model.startswith('ridge'):
            choice=m['ridge_selection'][row.target]
            assert pd.Timestamp(choice['selection_available_on'])<=row.origin_date
            assert p['ridge_alpha']==choice['alpha']
    for _,g in fits[fits.model.ne('rv_ewma') & fits.status.ne('failed')].groupby(['target','origin_date']):
        dates=[tuple(json.loads(x)['training_target_dates']) for x in g.diagnostics]
        assert len(g)==5 and len(set(dates))==1
        assert pd.Timestamp(dates[0][-1])<=g.origin_date.iloc[0]
    scores=pd.read_csv(run/'reports/stage4b_ridge_tuning.csv')
    for target,g in scores.groupby('target'):
        assert pd.to_datetime(g.last_target).max()<=pd.Timestamp('2023-12-31')
        eligible=g.groupby('ridge_alpha').agg(score=('qlike','mean'),min_n=('n_common','min'),failures=('unexpected_failures','sum'))
        eligible=eligible[(eligible.min_n>=m['config']['tuning']['minimum_fold_observations']) & eligible.failures.eq(0)]
        alpha=eligible.reset_index().sort_values(['score','ridge_alpha'],ascending=[True,False]).iloc[0].ridge_alpha
        assert alpha==m['ridge_selection'][target]['alpha']
    metrics=pd.read_csv(run/'reports/stage4b_comparison.csv')
    for row in metrics[metrics['sample'].eq('common') & metrics.comparison_group.eq('six_predefined_models')].itertuples():
        g=f[f.target.eq(row.target) & f.model.eq(row.model) & f.common]
        assert len(g)==row.n_evaluated
        assert np.isclose(qlike(g.forecast_variance,g.observed_variance).mean(),row.qlike,rtol=1e-12)
        assert np.isclose(g.observed_variance.mean()/g.forecast_variance.mean(),row.calibration_ratio,rtol=1e-12)
    count=0
    for count,line in enumerate((run/'forecast_issuance.jsonl').open(encoding='utf-8'),start=1):
        issued=json.loads(line);row=f.iloc[count-1]
        assert 'observed_variance' not in issued and 'target_observed' not in issued
        assert issued['model']==row.model and issued['target']==row.target
        assert pd.Timestamp(issued['target_date'])==row.target_date
        h=issued['forecast_variance']
        assert (h is None and pd.isna(row.forecast_variance)) or h==row.forecast_variance
    assert count==len(f)
    tests=pd.read_csv(run/'reports/stage4b_paired_tests.csv')
    assert len(tests)==m['configuration_counts']['formal_paired_comparisons']
    assert not tests.independent_confirmation.any()
    test_path=root/'reports/pytest-stage4b.xml'
    suites=ET.parse(test_path).getroot().findall('.//testsuite')
    test_counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    assert test_counts['failures']==0 and test_counts['errors']==0
    result={'run_id':m['run_id'],'status':'PASS_SAVED_ARTIFACT_CHECKS','research_status':m['status'],
        'holdout_evaluated':False,'independent_confirmation':False,'original_stage4_unchanged':True,
        'forecast_records':len(f),'positive_link_valid_forecasts':len(logs),'forecast_issuance_records':count,
        'outputs_verified':len(m['output_sha256']),'formal_paired_comparisons':len(tests),'pytest':test_counts}
    write_json(result,root/'reports/stage4b_verification.json')
    return result


if __name__=='__main__':print(json.dumps(verify(),indent=2))
