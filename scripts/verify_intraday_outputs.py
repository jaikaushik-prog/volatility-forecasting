"""Read-only verification of a published real integration; never fits a model."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from volrisk.data.storage import sha256, write_json  # noqa: E402


def verify(root=ROOT):
    pointer=json.loads((root/'reports/latest_intraday.json').read_text())
    run=Path(pointer['run_dir'])
    manifest_path=Path(pointer['manifest'])
    assert sha256(manifest_path)==pointer['manifest_sha256'],'Manifest hash mismatch'
    manifest=json.loads(manifest_path.read_text())
    for relative,digest in manifest['inputs_sha256'].items():
        assert sha256(root/relative)==digest,f'Changed input: {relative}'
    for relative,digest in manifest['implementation_sha256'].items():
        assert sha256(root/relative)==digest,f'Changed implementation: {relative}; rerun integration'
    for item in manifest['omitted_pickle']:
        if item['exists']: assert sha256(Path(item['path']))==item['sha256'],'Pickle bytes changed'
    for relative,digest in manifest['output_sha256'].items():
        assert sha256(run/relative)==digest,f'Changed immutable output: {relative}'
        if relative.startswith(('intraday/','features/')):
            published=root/manifest['config']['output_root']/relative
        elif relative.startswith('reports/'):
            published=root/manifest['config']['reports_root']/Path(relative).relative_to('reports')
        else: continue
        assert sha256(published)==digest,f'Published copy differs: {published}'
    results=[]
    for asset in manifest['config']['assets']:
        frame=pd.read_parquet(run/'intraday'/f'{asset}.parquet')
        assert frame.timestamp.is_monotonic_increasing and frame.timestamp.is_unique
        assert str(frame.timestamp.dt.tz)=='Asia/Kolkata'
        assert (frame.available_at==frame.timestamp+pd.Timedelta(minutes=1)).all()
        assert not frame.reindex(columns=['provenance_verified']).any().any(),'Expected provisional supplied sources'
        if asset=='india_vix': continue
        daily=pd.read_parquet(run/'features'/f'{asset}_realized_vol_daily.parquet')
        assert daily.session_date.is_monotonic_increasing and daily.session_date.is_unique
        assert not daily.research_ready.any()
        assert daily.loc[~daily.rv_eligible,[f'rv_{f}min' for f in (1,5,10,15)]].isna().all().all()
        for f in (1,5,10,15):
            rv=daily[f'rv_{f}min']
            assert (rv.dropna()>=0).all()
            np.testing.assert_allclose(rv,daily[f'positive_semivariance_{f}min']+daily[f'negative_semivariance_{f}min'],equal_nan=True,atol=1e-15)
            np.testing.assert_allclose(daily[f'annualized_realized_vol_{f}min']**2,rv*manifest['config']['sessions_per_year'],equal_nan=True,atol=1e-14)
            np.testing.assert_allclose(daily[f'full_rv_proxy_{f}min'],rv+daily.reopening_squared_return+daily.overnight_squared_return,equal_nan=True,atol=1e-15)
            if f==1: continue
            bars=pd.read_parquet(run/'intraday'/f'{asset}_{f}min.parquet')
            assert bars.timestamp.is_unique and bars.timestamp.is_monotonic_increasing
            assert ((bars.available_at-bars.timestamp).dt.total_seconds()==bars.duration_minutes*60).all()
            assert bars.loc[bars.complete,'expected_minutes'].eq(bars.loc[bars.complete,'observed_valid_minutes']).all()
            assert bars.loc[~bars.complete,['open','high','low','close']].isna().all().all()
            for _,g in bars.groupby(['session_date','segment']):
                assert (g.timestamp.iloc[1:].to_numpy()>=g.available_at.iloc[:-1].to_numpy()).all()
        valid=daily[['close_to_close_log_return','overnight_log_return','intraday_open_to_close_log_return']].notna().all(axis=1)
        np.testing.assert_allclose(daily.loc[valid,'close_to_close_log_return'],
            daily.loc[valid,'overnight_log_return']+daily.loc[valid,'intraday_open_to_close_log_return'],atol=1e-14)
        np.testing.assert_allclose(daily.rv_lag1,daily.rv_5min.shift(),equal_nan=True)
        assert daily.overnight_log_return[daily.source_rows.eq(0)].isna().all()
        results.append({'asset':asset,'sessions':len(daily),'complete_rv_sessions':int(daily.rv_eligible.sum()),
                        'overnight_observations':int(daily.overnight_log_return.notna().sum())})
    vix=pd.read_parquet(run/'features/nifty_vix_features_daily.parquet')
    available=vix.vix_eod_available
    assert (vix.loc[available,'vix_observation_available_at']<=vix.loc[available,'feature_origin_timestamp']).all()
    assert vix.loc[available,'vix_age_seconds'].between(0,manifest['config']['quality']['vix_max_age_seconds']).all()
    assert vix.loc[~available,'vix_eod_percent'].isna().all()
    np.testing.assert_allclose(vix.vix_annualized_decimal,vix.vix_eod_percent/100,equal_nan=True)
    assert not vix.research_ready.any()
    result={'run_id':manifest['run_id'],'status':'PASS_NUMERICAL_AND_HASH_CHECKS',
        'research_readiness':'PROVISIONAL_NOT_CERTIFIED','input_files_verified':len(manifest['inputs_sha256']),
        'outputs_verified':len(manifest['output_sha256']),'assets':results,
        'vix_eod_available':int(available.sum()),'pickle_deserialized':False}
    write_json(result,root/'reports/intraday_verification.json')
    return result


if __name__=='__main__':
    print(json.dumps(verify(),indent=2))
