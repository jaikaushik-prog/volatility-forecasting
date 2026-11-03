"""Read-only Stage 4 artifact verification; never forecasts or reads holdout values."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from volrisk.data.storage import sha256, write_json  # noqa: E402
from volrisk.evaluation.har_walk_forward import common_dates  # noqa: E402


def verify(root=ROOT):
    pointer=json.loads((root/'reports/latest_har_rv.json').read_text())
    run=Path(pointer['run_dir'])
    manifest_file=Path(pointer['manifest'])
    assert sha256(manifest_file)==pointer['manifest_sha256'],'Experiment manifest hash mismatch'
    m=json.loads(manifest_file.read_text())
    assert m['status']=='PROVISIONAL' and m['holdout_evaluated'] is False
    assert m['config_sha256']==sha256(root/'config/har_rv.toml'),'Configuration changed since experiment'
    for relative,digest in m['implementation_sha256'].items():
        assert sha256(root/relative)==digest,f'Implementation changed: {relative}'
    source_pointer=json.loads((root/m['config']['data']['latest_intraday']).read_text())
    source_path=Path(source_pointer['manifest'])
    source=json.loads(source_path.read_text())
    assert source['run_id']==m['data_readiness']['intraday_run_id'],'Source run changed'
    for relative,digest in m['data_readiness']['input_hashes'].items():
        if relative=='intraday_manifest': p=source_path
        elif relative=='protected_protocol': p=root/m['config']['data']['protected_protocol']
        else: p=source_path.parent/relative
        assert sha256(p)==digest,f'Source artifact changed: {relative}'
    for relative,digest in source['inputs_sha256'].items():
        assert sha256(root/relative)==digest,f'Raw/config/calendar evidence changed: {relative}'
    for relative,digest in m['output_sha256'].items():
        assert sha256(run/relative)==digest,f'Immutable artifact changed: {relative}'
        if relative.startswith('reports/'):
            p=root/m['config']['outputs']['reports']/Path(relative).relative_to('reports')
            assert sha256(p)==digest,f'Published report differs: {p}'
    f=pd.read_parquet(run/'forecasts.parquet')
    fits=pd.read_parquet(run/'fits.parquet')
    assert f.data_quality_status.eq('PROVISIONAL').all()
    assert f.period.isin(['development','validation']).all()
    cutoff=pd.Timestamp(m['numerical_data_cutoff'])
    assert f.target_date.max()<=cutoff and fits.origin_date.max()<=cutoff
    assert (f.target_date>f.origin_date).all()
    assert f.loc[f.forecast_valid,'forecast_variance'].gt(0).all()
    assert np.isfinite(f.loc[f.forecast_valid,'forecast_variance']).all()
    assert f.loc[~f.forecast_valid,'forecast_variance'].isna().all()
    assert f.observed_variance.dropna().ge(0).all()
    np.testing.assert_allclose(f.forecast_volatility_annualized**2,252*f.forecast_variance,equal_nan=True,atol=1e-14)
    valid=f.forecast_valid & f.target_observed
    assert (f.loc[valid,'forecast_created_at']<f.loc[valid,'target_open_timestamp']).all()
    assert (pd.to_datetime(f.loc[valid,'training_end'])<=f.loc[valid,'origin_date']).all()
    uses_vix=f.model.isin(['har_vix','har_vix_overnight']) & f.forecast_valid
    assert (f.loc[uses_vix,'vix_source_session']<f.loc[uses_vix,'origin_date']).all()
    assert (f.loc[uses_vix,'vix_available_at']<=f.loc[uses_vix,'origin_timestamp']).all()
    assert not f.duplicated(['asset','frequency','scenario','target','model','target_date']).any()
    for (asset,frequency,scenario,target),g in f.groupby(['asset','frequency','scenario','target']):
        panel=pd.read_parquet(run/'panels'/f'{asset}_{frequency}m_{scenario}.parquet').set_index('session_date')
        assert panel.index.max()<=cutoff
        np.testing.assert_array_equal(g.target_date.to_numpy(),panel.index.to_numpy()[g.origin_index.to_numpy()+1])
        expected=panel[target].reindex(g.target_date).to_numpy()
        np.testing.assert_allclose(g.observed_variance,expected,equal_nan=True,atol=1e-15)
        specs=m['model_specifications'][f'{asset}/{frequency}/{scenario}/{target}']
        recomputed=common_dates(g,list(specs))
        np.testing.assert_array_equal(g.common,recomputed.common)
        if target=='intraday_overnight':
            np.testing.assert_allclose(panel[target],panel.rv+panel.overnight_squared,equal_nan=True,atol=1e-15)
    harfits=fits[fits.model.isin(['har','log_har','har_overnight','har_vix','har_vix_overnight']) & fits.status.ne('failed')]
    for _,g in harfits.groupby(['asset','frequency','scenario','target','origin_date']):
        samples=[tuple(json.loads(x)['training_target_dates']) for x in g.diagnostics]
        assert len(set(samples))==1,'HAR variants used different training samples'
    count=0
    with (run/'forecast_issuance.jsonl').open(encoding='utf-8') as issued:
        for count,line in enumerate(issued,start=1):
            row=json.loads(line)
            assert 'observed_variance' not in row and 'target_observed' not in row
            saved=f.iloc[count-1]
            assert row['model']==saved.model and row['asset']==saved.asset
            assert pd.Timestamp(row['target_date'])==saved.target_date
            actual=row['forecast_variance']
            assert (actual is None and pd.isna(saved.forecast_variance)) or actual==saved.forecast_variance
    assert count==len(f),'Issuance records and evaluated forecasts differ'
    tests_file=root/'reports/pytest-har-rv.xml'
    test_result={}
    if tests_file.exists():
        suites=ET.parse(tests_file).getroot().findall('.//testsuite')
        test_result={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
        assert test_result['failures']==0 and test_result['errors']==0
    result={'run_id':m['run_id'],'status':'PASS_NUMERICAL_TEMPORAL_AND_HASH_CHECKS','findings_status':'PROVISIONAL',
        'holdout_evaluated':False,'last_target':str(f.target_date.max().date()),'forecast_records':len(f),
        'issued_before_outcome_records':count,'fit_records':len(fits),'outputs_verified':len(m['output_sha256']),
        'source_input_hashes_verified':len(source['inputs_sha256']),'pytest':test_result}
    write_json(result,root/'reports/har_rv_verification.json')
    return result


if __name__=='__main__': print(json.dumps(verify(),indent=2))
