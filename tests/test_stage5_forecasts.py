"""Only synthetic numerical fixtures are used in these tests."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from volrisk.economics.alignment import causal_features,bounded_parquet
from volrisk.economics.forecasts import DirectDailyHAR,generate_forecasts,COMMON
from volrisk.economics.metrics import forecast_scores
from volrisk.economics.experiment import register,verify_protected,load_config


def panel(n=190):
    rng=np.random.default_rng(937)
    dates=pd.bdate_range('2023-01-02',periods=n)
    ts=dates.tz_localize('Asia/Kolkata')+pd.Timedelta(hours=15,minutes=30)
    rv=np.exp(rng.normal(-9,.5,n));returns=rng.normal(0,np.sqrt(rv))
    return pd.DataFrame(dict(rv=rv,overnight_squared=rv*.2,vix_implied_variance=np.exp(rng.normal(-3.5,.2,n)),
        log_return=returns,simple_return=np.expm1(returns),origin_timestamp=ts,
        vix_available_at=pd.Series(ts).shift(1).array,vix_source_session=pd.Series(dates).shift(1).array,
        rv_eligible=True),index=dates)


def config():
    return dict(data={'asset':'NIFTY50_TRI','status':'SYNTHETIC_TEST_ONLY','instrument_status':'NON_EXECUTABLE_THEORETICAL_TOTAL_RETURN_INDEX'},
        estimation=dict(forecast_start='2023-05-01',models=['ewma','garch','har_daily','log_har_daily','log_har_vix_daily'],
            horizons=[2,3],har_window=100,har_min_pairs=20,refit_every=21,garch_window=100,garch_min_observations=50,
            ewma_decay=.94,ewma_initial_observations=20,max_annual_volatility=5.))


def test_har_horizon_uses_only_completed_pairs():
    p=panel();features=causal_features(p)
    for h in [2,3]:
        model=DirectDailyHAR('har_daily',h,window=100,min_observations=20)
        report=model.fit(p.iloc[:140],features.iloc[:140])
        assert report.training_end==p.index[139]
        dates=pd.to_datetime(report.diagnostics['training_target_dates'])
        assert (dates<=p.index[139]).all()
        x=features.shift(h-1).iloc[39:139]
        y=p.log_return.pow(2).shift(-1).iloc[39:139]
        keep=np.isfinite(x[COMMON]).all(axis=1)&np.isfinite(y)
        # Independently reconstruct the direct-horizon OLS on unstandardized levels.
        a=np.column_stack([np.ones(keep.sum()),x.loc[keep,['rv_daily','rv_weekly','rv_monthly']]])
        coef=np.linalg.lstsq(a,y[keep],rcond=None)[0]
        origin=features.iloc[139][['rv_daily','rv_weekly','rv_monthly']].to_numpy()
        expected=float(np.r_[1.,origin]@coef)
        if expected>0:assert model.forecast()==pytest.approx(expected,rel=1e-8)


def test_vix_availability_lag_and_missing_rv_windows():
    p=panel();f=causal_features(p)
    assert np.isnan(f.vix_implied_variance.iloc[0])
    assert f.rv_weekly.iloc[30]==pytest.approx(p.rv.iloc[26:31].mean())
    p.loc[p.index[10],'rv']=np.nan;p.loc[p.index[10],'rv_eligible']=False
    f=causal_features(p)
    assert f.rv_monthly.iloc[10:32].isna().all()
    p.loc[p.index[50],'vix_available_at']=p.origin_timestamp.iloc[51]
    with pytest.raises(ValueError,match='availability'):causal_features(p)


def test_reject_ineligible_rv():
    p=panel();p.loc[p.index[10],'rv_eligible']=False
    with pytest.raises(ValueError,match='Ineligible'):causal_features(p)


def test_positive_direct_link_and_training_transform():
    p=panel();f=causal_features(p)
    model=DirectDailyHAR('log_har_vix_daily',2,window=100,min_observations=20)
    report=model.fit(p.iloc[:150],f.iloc[:150])
    assert model.forecast()>0
    assert report.params['smearing']>0
    assert model.model.state_diagnostics()['prediction_floored'] is False


def test_forecast_alignment_callback_and_future_shock():
    p=panel();cfg=config();saved=[]
    original=generate_forecasts(p,cfg,save=saved.append)
    assert saved and all('observed_squared_log_return' not in x for x in saved)
    for row in original.itertuples():
        i=p.index.get_loc(row.origin_date)
        assert row.target_date==p.index[i+row.horizon]
        assert row.execution_date==p.index[i+row.horizon-1]
        assert row.issued_at<row.execution_timestamp
        assert row.training_end<=row.origin_date
    cutoff=p.index[145]
    shock=p.copy();shock.loc[shock.index>cutoff,'rv']*=20
    shock.loc[shock.index>cutoff,'log_return']*=10
    shock.loc[shock.index>cutoff,'vix_implied_variance']*=5
    changed=generate_forecasts(shock,cfg)
    cols=['asset','model','horizon','origin_date','target_date','forecast_variance','params','fit_status','training_end','last_fit_date']
    pd.testing.assert_frame_equal(original.loc[original.origin_date.le(cutoff),cols].reset_index(drop=True),
                                  changed.loc[changed.origin_date.le(cutoff),cols].reset_index(drop=True))
    for (_,h),f in original.groupby(['model','horizon']):
        refits=f.loc[f.refitted,'origin_date']
        if len(refits)>1:
            gaps=np.diff([p.index.get_loc(x) for x in refits])
            assert (gaps==21).all()


def test_failed_forecast_remains_and_common_scores():
    p=panel();p.loc[p.index[130],'rv']=np.nan;p.loc[p.index[130],'rv_eligible']=False
    cfg=config();f=generate_forecasts(p,cfg)
    missing=f.loc[f.origin_date.eq(p.index[130])&f.model.eq('log_har_daily')]
    assert missing.forecast_variance.isna().all() and missing.fit_status.eq('failed').all()
    scores,common=forecast_scores(f,cfg['estimation']['models'],'2023-01-01','2023-12-31')
    assert scores.observations.nunique()==1
    assert common.groupby('target_date').model.nunique().eq(5).all()


def test_bounded_read_rejects_future_request(tmp_path):
    path=tmp_path/'synthetic.parquet'
    pd.DataFrame({'date':pd.to_datetime(['2024-12-31','2025-01-01']),'value':[1.,999.]}).to_parquet(path,index=False)
    result=bounded_parquet(path,'date')
    assert result.value.tolist()==[1.]
    with pytest.raises(ValueError,match='cutoff'):bounded_parquet(path,'date',end='2025-01-01')


def test_registration_and_protected_artifacts(tmp_path,monkeypatch):
    source=Path('config/stage5.toml').read_text()
    monkeypatch.chdir(tmp_path);Path('config').mkdir();Path('reports').mkdir()
    Path('config/stage5.toml').write_text(source);Path('reports/frozen_forecasting_protocol.md').write_text('synthetic frozen artifact')
    registration=register('config/stage5.toml')
    assert register('config/stage5.toml')==registration
    verify_protected(registration)
    Path('reports/frozen_forecasting_protocol.md').write_text('changed')
    with pytest.raises(ValueError,match='changed'):verify_protected(registration)


def test_config_cutoff_guard(tmp_path):
    text=Path('config/stage5.toml').read_text().replace('evaluation_end = "2024-12-31"','evaluation_end = "2025-12-31"')
    path=tmp_path/'bad.toml';path.write_text(text)
    with pytest.raises(ValueError,match='future-period'):load_config(path)


def test_garch_multi_step_scaling_matches_arch():
    from volrisk.forecasting.garch import ArchGARCH
    p=panel();values=p.log_return.to_numpy()
    model=ArchGARCH('garch',window=150,min_observations=50)
    report=model.fit(values,dates=p.index)
    assert report.converged
    am=model._arch_model(values[-150:]*100)
    # Fix identical coefficients and compare arch's own forecast recursion.
    backend=am.fix(np.array([model.params[name] for name in ['omega','alpha[1]','beta[1]']]))
    expected=backend.forecast(horizon=3,reindex=False).variance.iloc[-1].to_numpy()/10000
    np.testing.assert_allclose(model.forecast(3),expected,rtol=1e-10,atol=1e-14)


def test_reproducible_forecast_values():
    p=panel(130);cfg=config();cfg['estimation']['models']=['log_har_daily']
    a=generate_forecasts(p,cfg).drop(columns=['runtime_seconds'])
    b=generate_forecasts(p,cfg).drop(columns=['runtime_seconds'])
    pd.testing.assert_frame_equal(a,b)


def test_entry_and_failed_forecast_json_nulls(tmp_path):
    from volrisk.economics.experiment import write_json
    path=tmp_path/'synthetic.json'
    write_json(path,{'issued_at':pd.NaT,'forecast':np.nan,'extra':{'missing':pd.NA}})
    assert json.loads(path.read_text())=={'issued_at':None,'forecast':None,'extra':{'missing':None}}
