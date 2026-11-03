"""Stage 4 synthetic-only tests. Numerical success here is not a market-data result."""
from copy import deepcopy
import json
from pathlib import Path
import tomllib
import numpy as np
import pandas as pd
import pytest

from volrisk.forecasting.har import HARRV, RVBenchmark, origin_features, supervised, RV_FEATURES, ON_FEATURES, VIX_FEATURES
from volrisk.forecasting.base import FitError, FitReport, FIT_FAILED
from volrisk.forecasting.registry import build_model
from volrisk.data.har_dataset import (prepare_panel, validate_vix, validate_daily, protected_splits, ReadinessError)
from volrisk.evaluation.walk_forward import PeriodSplits, run_walk_forward
from volrisk.evaluation.har_walk_forward import walk_forward, common_dates, model_specs
from volrisk.evaluation.har_metrics import paired_inference, attach_har_losses, summarize_har, comparisons, attach_regimes
from volrisk.evaluation.har_experiment import run_har_experiment

ROOT=Path(__file__).resolve().parents[1]
CONFIG=tomllib.loads((ROOT/'config/har_rv.toml').read_text())


def synthetic_daily(n=300,seed=71,start='2022-01-03'):
    rng=np.random.default_rng(seed)
    dates=pd.bdate_range(start,periods=n)
    rv=np.exp(-10+np.cumsum(rng.normal(0,.07,n)))
    on=rng.normal(0,.003,n)
    r=on+rng.normal(0,np.sqrt(rv),n)
    close=100*np.exp(np.cumsum(r))
    opened=np.r_[100.,close[:-1]]*np.exp(on)
    d=pd.DataFrame({'session_date':dates,'asset':'NIFTY',
        'session_open':dates.tz_localize('Asia/Kolkata')+pd.Timedelta(hours=9,minutes=15),
        'session_close':dates.tz_localize('Asia/Kolkata')+pd.Timedelta(hours=15,minutes=30),
        'expected_minutes':375,'schedule_verified':True,'expected_session':True,'rv_eligible':True,
        'session_complete':True,'endpoint_open_valid':True,'endpoint_close_valid':True,'missing_or_invalid_minutes':0,
        'extreme_return_flags':0,'max_unchanged_run_minutes':0,'overnight_endpoints_valid':True,
        'open':opened,'close':close,'overnight_log_return':on,'overnight_squared_return':on**2,
        'close_to_close_log_return':r})
    d.loc[0,['overnight_log_return','overnight_squared_return','close_to_close_log_return']]=np.nan
    d.loc[0,'overnight_endpoints_valid']=False
    for f in (1,5,10,15):
        d[f'rv_{f}min']=rv*(1+f/100)
        d[f'positive_semivariance_{f}min']=d[f'rv_{f}min']*.4
        d[f'negative_semivariance_{f}min']=d[f'rv_{f}min']*.6
    d['reopening_squared_return']=.02  # Deliberately large: secondary target must NOT use this.
    vix=pd.DataFrame({'session_date':dates,'vix_eod_percent':15+np.arange(n)*.002+rng.uniform(0,2,n),
        'vix_eod_available':True,'feature_origin_timestamp':d.session_close.copy(deep=True),
        'vix_observation_available_at':d.session_close.copy(deep=True),'vix_age_seconds':0.})
    vix['vix_annualized_decimal']=vix.vix_eod_percent/100
    return d,vix


@pytest.fixture
def panel():
    d,v=synthetic_daily()
    return prepare_panel(d,v)


@pytest.fixture
def splits():
    return PeriodSplits.from_config({'development':['2022-01-01','2022-09-30'],
        'validation':['2022-10-01','2023-12-31'],'holdout':['2024-01-01','2026-10-30'],'holdout_sealed':True})


def small_model(**kwargs):
    args={'window':100,'min_observations':30,'refit_every':10}
    args.update(kwargs)
    return HARRV('har',**args)


def test_har_features_exact_windows_and_target_alignment(panel):
    features=origin_features(panel)
    assert features.iloc[21].rv_daily==panel.rv.iloc[21]
    assert features.iloc[21].rv_weekly==pytest.approx(panel.rv.iloc[17:22].mean())
    assert features.iloc[21].rv_monthly==pytest.approx(panel.rv.iloc[:22].mean())
    assert pd.isna(features.iloc[20].rv_monthly)
    x,y,dates=supervised(panel.iloc[:80],'intraday',RV_FEATURES,50)
    assert y.iloc[-1]==panel.intraday.iloc[79]
    assert x.index[-1]==panel.index[78] and dates.iloc[-1]==panel.index[79]
    assert len(x)==50


def test_overnight_and_secondary_target_are_distinct(panel):
    np.testing.assert_allclose(panel.intraday_overnight,panel.rv+panel.overnight_squared,equal_nan=True)
    assert not np.allclose(panel.intraday_overnight.iloc[1:],panel.spot_c2c_squared.iloc[1:])
    features=origin_features(panel)
    assert features.iloc[24].overnight_weekly==pytest.approx(panel.overnight_squared.iloc[20:25].mean())
    assert features.iloc[24].overnight_monthly==pytest.approx(panel.overnight_squared.iloc[3:25].mean())


def test_vix_extra_full_session_lag_and_percent_scaling():
    d,v=synthetic_daily(50)
    p=prepare_panel(d,v,vix_extra_lag=1)
    assert p.iloc[25].vix_implied_variance==pytest.approx((v.vix_eod_percent.iloc[24]/100)**2)
    assert p.iloc[25].vix_available_at==d.session_close.iloc[24]
    assert p.iloc[25].vix_source_session==d.session_date.iloc[24]
    assert p.iloc[25].vix_available_at<p.iloc[25].origin_timestamp
    assert pd.isna(p.iloc[0].vix_implied_variance)
    v.loc[24,'vix_eod_available']=False
    assert pd.isna(prepare_panel(d,v).iloc[25].vix_implied_variance)


def test_vix_future_timestamp_is_critical():
    _,v=synthetic_daily(20)
    v.loc[5,'vix_observation_available_at']+=pd.Timedelta(minutes=1)
    with pytest.raises(ReadinessError,match='availability'):
        validate_vix(v)


def test_no_vix_experiment_beyond_source_end():
    d,v=synthetic_daily(60)
    end=d.session_date.iloc[40]
    p=prepare_panel(d,v,vix_end=end)
    assert p.index[-1]==end and len(p)==41


def test_incomplete_and_unverified_sessions_remain_gaps():
    d,v=synthetic_daily(80)
    d.loc[25,['session_complete','rv_eligible']]=False
    d.loc[26,'schedule_verified']=False
    p=prepare_panel(d,v)
    assert len(p)==80 and p.rv.iloc[25:27].isna().all()
    assert pd.isna(origin_features(p).iloc[47].rv_monthly)
    assert np.isfinite(origin_features(p).iloc[48].rv_monthly)


def test_special_sessions_not_filled_or_duration_scaled():
    d,v=synthetic_daily(50)
    d.loc[25,'expected_minutes']=60
    p=prepare_panel(d,v)
    assert p.iloc[25].rv==d.loc[25,'rv_5min'] and p.iloc[25].nonstandard_duration


def test_questionable_sensitivity_preserves_original_and_breaks_endpoint_pairs():
    d,v=synthetic_daily(80)
    d.loc[30,'extreme_return_flags']=1
    original=d.copy(deep=True)
    primary=prepare_panel(d,v)
    strict=prepare_panel(d,v,scenario='exclude_questionable')
    assert np.isfinite(primary.rv.iloc[30]) and pd.isna(strict.rv.iloc[30])
    assert strict.overnight_squared.iloc[30:32].isna().all()
    assert pd.isna(origin_features(strict).iloc[51].rv_monthly)
    pd.testing.assert_frame_equal(d,original)


def test_validation_rejects_bad_overnight_alignment():
    d,_=synthetic_daily(40)
    validate_daily(d,{})
    d.loc[20,'overnight_log_return']+=.01
    with pytest.raises(ReadinessError,match='adjacency'):
        validate_daily(d,{})


@pytest.mark.parametrize('transform',['levels','log'])
def test_fit_forecast_positive_training_bounds_and_configuration(panel,transform):
    m=small_model(transform=transform)
    r=m.fit(panel.iloc[:100])
    assert r.usable and r.training_end==panel.index[99]
    assert r.training_start>panel.index[0] and r.training_observations>=30
    assert np.isfinite(m.forecast()[0]) and m.forecast()[0]>0
    assert m.params['variance_floor']>0
    clone=HARRV('clone',**m.config)
    clone.fit(panel.iloc[:100])
    np.testing.assert_array_equal(m.forecast(),clone.forecast())
    with pytest.raises(NotImplementedError): m.forecast(2)


def test_log_floor_and_smearing_use_training_only(panel):
    history=panel.iloc[:100].copy()
    history.loc[history.index[40],'intraday']=0
    raw=history.copy(deep=True)
    model=small_model(transform='log')
    result=model.fit(history)
    assert result.diagnostics['zero_training_targets']==1
    assert model.params['smearing']>=1-1e-12
    x,y,_=supervised(history,'intraday',RV_FEATURES,100)
    expected=np.median(y[y>0])*1e-6
    assert model.params['variance_floor']==pytest.approx(expected)
    pd.testing.assert_frame_equal(history,raw)
    no_correction=small_model(transform='log',log_bias_correction='none')
    no_correction.fit(history)
    assert model.forecast()[0]==pytest.approx(no_correction.forecast()[0]*model.params['smearing'])


def test_negative_prediction_floor_records_raw_and_reject_option(panel):
    m=small_model();m.fit(panel.iloc[:100])
    m._coef[:]=0;m._coef[0]=-1.
    assert m.forecast()[0]==m.params['variance_floor']
    assert m.state_diagnostics()['raw_prediction']==-1 and m.state_diagnostics()['prediction_floored']
    reject=small_model(nonpositive_policy='reject');reject.fit(panel.iloc[:100])
    reject._coef[:]=0;reject._coef[0]=-1
    with pytest.raises(FitError,match='floor'): reject.forecast()


def test_no_positive_training_variance_explicit_failure(panel):
    p=panel.iloc[:100].copy();p['intraday']=0.
    with pytest.raises(FitError,match='No positive'):
        small_model().fit(p)


def test_har_variants_use_identical_training_rows(panel):
    p=panel.iloc[:150].copy();p.loc[p.index[70],'vix_implied_variance']=np.nan
    common=RV_FEATURES+ON_FEATURES+VIX_FEATURES
    reports=[]
    for kwargs in ({},{'overnight':True},{'vix':True},{'vix':True,'overnight':True},{'transform':'log'}):
        reports.append(small_model(common_columns=common,**kwargs).fit(p))
    assert len({tuple(r.diagnostics['training_target_dates']) for r in reports})==1
    assert len({r.training_observations for r in reports})==1


@pytest.mark.parametrize('method,window',[('previous',1),('mean',5),('mean',22)])
def test_rv_benchmarks_are_mean_variance_not_variance_of_variance(panel,method,window):
    m=RVBenchmark('b',method=method,window=window)
    m.fit(panel.iloc[:100])
    assert m.forecast()[0]==pytest.approx(panel.intraday.iloc[100-window:100].mean())


def test_realized_ewma_recursion_and_gap_reset(panel):
    p=panel.iloc[:100].copy()
    m=RVBenchmark('ew',method='ewma',init_window=22,decay=.94)
    m.fit(p)
    h=p.intraday.iloc[:22].mean()
    for y in p.intraday.iloc[22:]: h=.94*h+.06*y
    assert m.forecast()[0]==pytest.approx(h)
    p.loc[p.index[-10],'intraday']=np.nan
    with pytest.raises(FitError,match='contiguous'): m.fit(p)


def test_walk_forward_refit_schedule_and_persist_before_outcome(panel,splits):
    issued=[]
    f,fits=walk_forward(panel.iloc[:140],small_model(),target='intraday',splits=splits,save_forecast=issued.append)
    usable=f[f.forecast_valid]
    assert len(usable)>50
    assert all('observed_variance' not in x for x in issued)
    assert (usable.target_date>usable.origin_date).all()
    assert (usable.training_end<=usable.origin_date).all()
    assert (usable.target_open_timestamp>usable.forecast_created_at).all()
    np.testing.assert_array_equal(np.diff(fits.origin_index),10)
    for _,g in usable.groupby('last_fit_date'): assert g.params.nunique()==1
    p=panel.intraday.reindex(f.target_date).to_numpy()
    np.testing.assert_allclose(f.observed_variance,p,equal_nan=True)


@pytest.mark.parametrize('transform,vix,overnight',[('levels',False,False),('log',False,False),('levels',True,False),('levels',False,True),('levels',True,True)])
def test_future_shock_cannot_change_issued_forecast(panel,splits,transform,vix,overnight):
    p=panel.iloc[:150].copy()
    m=lambda:small_model(transform=transform,vix=vix,overnight=overnight)
    a,_=walk_forward(p,m(),target='intraday',splits=splits)
    changed=p.copy()
    changed.loc[changed.index[110]:,['rv','intraday','intraday_overnight','overnight_squared','vix_implied_variance']]*=100
    b,_=walk_forward(changed,m(),target='intraday',splits=splits)
    cols=['origin_date','target_date','forecast_variance','params','fit_status','raw_prediction','prediction_floored']
    pd.testing.assert_frame_equal(a.loc[a.origin_date<=p.index[109],cols].reset_index(drop=True),
                                  b.loc[b.origin_date<=p.index[109],cols].reset_index(drop=True))


def test_holdout_cutoff_before_features(panel):
    s=PeriodSplits.from_config({'development':['2022-01-01','2022-02-28'],
        'validation':['2022-03-01','2022-05-31'],'holdout':['2022-06-01','2026-12-31'],'holdout_sealed':True})
    a,_=walk_forward(panel,small_model(),target='intraday',splits=s)
    changed=panel.copy();changed.loc['2022-06-01':,'rv']=np.inf
    b,_=walk_forward(changed,small_model(),target='intraday',splits=s)
    assert a.target_date.max()<=pd.Timestamp('2022-05-31')
    pd.testing.assert_frame_equal(a.drop(columns='runtime_seconds'),b.drop(columns='runtime_seconds'))


def test_daily_return_engine_rejects_har_and_har_engine_rejects_target_mismatch(panel,splits):
    with pytest.raises(TypeError,match='target-specific'):
        run_walk_forward(panel.spot_return,small_model(),asset='SYN')
    garch=build_model('g',{'type':'garch','min_observations':50,'window':100})
    with pytest.raises(ValueError,match='directly ranked'):
        walk_forward(panel,garch,target='intraday',splits=splits)


def test_fit_failure_never_substitutes_a_forecast(panel,splits):
    class Broken(HARRV):
        def fit(self,*args,**kwargs): raise RuntimeError('synthetic fit failure')
    m=Broken('broken',min_observations=30,window=100)
    f,fits=walk_forward(panel.iloc[:100],m,target='intraday',splits=splits)
    assert not f.forecast_valid.any() and f.forecast_variance.isna().all()
    assert len(fits)>0 and fits.status.eq('failed').all()


def test_matched_dates_require_all_configured_models(panel,splits):
    a,_=walk_forward(panel.iloc[:100],small_model(),target='intraday',splits=splits)
    b=a.copy();b['model']='other';b.loc[b.index[-1],'forecast_valid']=False
    out=common_dates(pd.concat([a,b],ignore_index=True),['har','other'])
    assert not out[out.target_date.eq(a.target_date.iloc[-1])].common.any()
    assert out.common.sum()>0
    assert not common_dates(a,['har','never_forecast']).common.any()


def test_gap_aware_inference_reproducible_and_short_sample_explicit():
    rng=np.random.default_rng(21)
    d=rng.normal(-.1,.3,80)
    idx=np.r_[np.arange(40),np.arange(50,90)]
    a=paired_inference(d,idx,draws=100)
    b=paired_inference(d,idx,draws=100)
    assert a==b and a['contiguous_blocks']==2
    assert a['ci_low']<a['ci_high']
    short=paired_inference(d[:10],idx[:10],draws=100)
    assert short['inference_status']=='insufficient_sample' and np.isnan(short['hac_p_value'])


def test_prior_holdout_boundary_cannot_be_moved(tmp_path):
    (tmp_path/'config').mkdir()
    (tmp_path/'config/forecasting.toml').write_text((ROOT/'config/forecasting.toml').read_text())
    config=deepcopy(CONFIG)
    config['splits']['validation']=['2024-01-01','2025-01-31']
    config['splits']['holdout']=['2025-02-01','2026-10-30']
    with pytest.raises(ReadinessError,match='previously protected'):
        protected_splits(config,tmp_path)


def test_end_to_end_synthetic_run_reproducible_and_reports_explicit(tmp_path,monkeypatch):
    from volrisk.evaluation import har_experiment
    (tmp_path/'config').mkdir()
    (tmp_path/'config/forecasting.toml').write_text((ROOT/'config/forecasting.toml').read_text())
    text=(ROOT/'config/har_rv.toml').read_text().replace('assets = ["NIFTY", "SENSEX"]','assets = ["NIFTY"]')
    text=text.replace('min_observations = 126','min_observations = 20').replace('window = 500','window = 100')
    text=text.replace('daily_min_observations = 252','daily_min_observations = 50')
    text=text.replace('bootstrap_draws = 10000','bootstrap_draws = 20')
    text=text.replace('development = ["2022-01-01", "2023-12-31"]','development = ["2022-01-01", "2022-02-28"]')
    text=text.replace('validation = ["2024-01-01", "2024-12-31"]','validation = ["2022-03-01", "2022-05-31"]')
    path=tmp_path/'config/har_rv.toml';path.write_text(text)
    d,v=synthetic_daily(100)
    readiness={'status':'PROVISIONAL','input_hashes':{'synthetic':'unit-test-only'},'intraday_run_id':'SYNTHETIC_TEST',
               'vix_source_last_session':'2022-05-31','loaded_through':'2022-05-31','holdout_sealed':True}
    monkeypatch.setattr(har_experiment,'load_har_inputs',lambda config,root:({'NIFTY':d},v,readiness))
    first=run_har_experiment(path,make_figures=False)
    second=run_har_experiment(path,make_figures=False)
    assert first==second and first['holdout_evaluated'] is False
    run=tmp_path/'experiments/har_rv/runs'/first['run_id']
    forecast=pd.read_parquet(run/'forecasts.parquet')
    assert forecast.data_quality_status.eq('PROVISIONAL').all()
    assert forecast.target_date.max()<=pd.Timestamp('2022-05-31')
    for name in ('har_rv_research','vix_incremental_value','overnight_risk_analysis','forecast_readiness'):
        assert 'PROVISIONAL' in (tmp_path/'reports'/f'{name}.md').read_text(encoding='utf-8')
    issued=json.loads((run/'forecast_issuance.jsonl').read_text().splitlines()[0])
    assert 'observed_variance' not in issued


def test_critical_gate_writes_no_fake_results(tmp_path,monkeypatch):
    from volrisk.evaluation import har_experiment
    (tmp_path/'config').mkdir()
    for name in ('har_rv.toml','forecasting.toml'):
        (tmp_path/'config'/name).write_text((ROOT/'config'/name).read_text())
    def broken(*args): raise ReadinessError('synthetic corrupt artifact')
    monkeypatch.setattr(har_experiment,'load_har_inputs',broken)
    result=run_har_experiment(tmp_path/'config/har_rv.toml')
    assert result['status']=='BLOCKED_CRITICAL_DATA_GATE'
    assert pd.read_csv(tmp_path/'reports/har_rv_model_comparison.csv').empty
    assert not (tmp_path/'experiments/har_rv/runs').exists()
