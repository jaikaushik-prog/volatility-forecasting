"""Synthetic-only unit tests for Stage 4B; never evidence of empirical superiority."""
from copy import deepcopy
import json
from pathlib import Path
import tomllib
import numpy as np
import pandas as pd
import pytest

from test_har_rv import synthetic_daily
from volrisk.data.har_dataset import prepare_panel, ReadinessError
from volrisk.data.stage4b_dataset import validate_panel
from volrisk.forecasting.base import FitError
from volrisk.forecasting.har import HARRV, supervised
from volrisk.forecasting.positive_har import PositiveHAR, positive_features, COMMON, CHANGE
from volrisk.forecasting.registry import build_model
from volrisk.evaluation.walk_forward import PeriodSplits
from volrisk.evaluation.har_walk_forward import walk_forward, common_dates, model_specs
from volrisk.evaluation.stage4b import tune_ridge, evaluate_models, compare_models, specifications, NAMES

ROOT=Path(__file__).resolve().parents[1]
CONFIG=tomllib.loads((ROOT/'config/stage4b.toml').read_text())


@pytest.fixture
def panel():
    d,v=synthetic_daily(560,seed=481,start='2022-10-25')
    # This fixture can contain synthetic 2025 dates, never real holdout observations.
    return prepare_panel(d,v)


@pytest.fixture
def config():
    c=deepcopy(CONFIG)
    c['estimation'].update(window=150,min_observations=40,refit_every=21)
    c['tuning'].update(alphas=[.1,10.],minimum_fold_observations=20)
    c['evaluation']['bootstrap_draws']=50
    return c


@pytest.fixture
def splits():
    return PeriodSplits.from_config({'development':['2022-01-01','2023-12-31'],
        'validation':['2024-01-01','2024-12-31'],'holdout':['2025-01-01','2026-10-30'],'holdout_sealed':True})


def model(**kwargs):
    return PositiveHAR('positive',window=150,min_observations=40,**kwargs)


def test_positive_features_lag_scaling_and_signed_change(panel):
    f=positive_features(panel)
    i=50
    expected=np.log(panel.vix_implied_variance.iloc[i]/panel.vix_implied_variance.iloc[i-1])
    assert f[CHANGE].iloc[i]==pytest.approx(expected)
    assert panel.vix_source_session.iloc[i]==panel.index[i-1]
    assert panel.vix_available_at.iloc[i]<=panel.origin_timestamp.iloc[i-1]
    p=panel.copy();p.loc[p.index[49],'vix_implied_variance']=np.nan
    f=positive_features(p)
    assert f[CHANGE].iloc[49:51].isna().all()
    assert f.vix_change_available.iloc[49:51].isna().all()


def test_transformed_features_are_log_of_arithmetic_rv_means(panel):
    p=panel.iloc[:120]
    m=model(vix_change=True);m.fit(p)
    f=positive_features(p)
    a=m._transform_x(f.iloc[[-1]])[0]
    np.testing.assert_allclose(a[:3],np.log([p.rv.iloc[-1],p.rv.iloc[-5:].mean(),p.rv.iloc[-22:].mean()]))
    assert a[3]==pytest.approx(np.log(p.vix_implied_variance.iloc[-1]))
    assert a[4]==pytest.approx(f[CHANGE].iloc[-1])


def test_zero_transformation_training_only_and_positive_small_values_preserved(panel):
    p=panel.iloc[:120].copy();p.loc[p.index[70],'intraday']=0.;p.loc[p.index[72],'rv']=0.
    m=model();result=m.fit(p)
    assert result.diagnostics['zero_training_targets']==1
    assert result.diagnostics['zero_training_features']>=1
    f=positive_features(p).iloc[[-1]].copy()
    f['rv_daily']=m.params['zero_rv_transform_floor']/100
    assert m._transform_x(f)[0,0]==pytest.approx(np.log(f.rv_daily.iloc[0]))
    assert p.intraday.iloc[70]==0
    p['intraday']=0.
    with pytest.raises(FitError,match='No positive'):
        m.fit(p)


@pytest.mark.parametrize('alpha',[0.,.1,10.,100.])
def test_ridge_solution_and_intercept_penalty(alpha,panel):
    p=panel.iloc[:140]
    m=model(ridge_alpha=alpha);r=m.fit(p)
    f=positive_features(p);x,y,_=supervised(p,'intraday',COMMON,150,f)
    a=m._transform_x(x)
    design=np.column_stack([np.ones(len(x)),(a-m._center)/m._scale])
    penalty=np.diag([0.]+[alpha]*len(m.columns))
    expected=np.linalg.solve(design.T@design+penalty,design.T@np.log(y))
    np.testing.assert_allclose(m._coef,expected,atol=1e-10)
    assert r.diagnostics['bias_correction']=='smearing'
    assert m.forecast()[0]>0 and not m.state_diagnostics()['prediction_floored']


def test_log_har_baseline_equivalence_and_retransformation(panel):
    p=panel.iloc[:120]
    new=model(vix=False);old=HARRV('old',transform='log',common_columns=COMMON,window=150,min_observations=40)
    f=positive_features(p);new.fit(p,features=f);old.fit(p,features=f)
    np.testing.assert_allclose(new.forecast(),old.forecast(),rtol=1e-12)
    no_smear=model(vix=False,log_bias_correction='none');no_smear.fit(p)
    assert new.forecast()[0]==pytest.approx(no_smear.forecast()[0]*new.params['smearing'])


@pytest.mark.parametrize('intercept',[1000.,-1000.])
def test_positive_link_overflow_underflow_are_failures_not_floor(intercept,panel):
    m=model();m.fit(panel.iloc[:120]);m._coef[:]=0;m._coef[0]=intercept
    with pytest.raises(FitError,match='no clipping'):
        m.forecast()
    assert not m.state_diagnostics()['prediction_floored']


def test_extremely_small_positive_forecast_is_not_raised_to_floor(panel):
    m=model();m.fit(panel.iloc[:120]);m._coef[:]=0;m._coef[0]=-100.
    h=m.forecast()[0]
    assert 0<h<m.params['zero_rv_transform_floor']
    assert h==pytest.approx(np.exp(-100.)*m.params['smearing'],abs=1e-55)


@pytest.mark.parametrize('bad_iv',[0.,-1.,np.inf,np.nan])
def test_invalid_vix_is_not_replaced(bad_iv,panel):
    m=model();m.fit(panel.iloc[:120]);f=positive_features(panel.iloc[:120]).iloc[-1].copy()
    f['vix_implied_variance']=bad_iv;m.update(f)
    with pytest.raises(FitError):m.forecast()


def test_readiness_rechecks_native_lag_and_incomplete_sessions(panel):
    p=panel.loc[:'2024-12-31'].copy();validate_panel(p)
    p.loc[p.index[40],'vix_source_session']=p.index[40]
    with pytest.raises(ReadinessError,match='previous native'):validate_panel(p)
    p=panel.loc[:'2024-12-31'].copy();p.loc[p.index[45],'rv_eligible']=False
    with pytest.raises(ReadinessError,match='Ineligible'):validate_panel(p)
    if panel.index.max()>pd.Timestamp('2024-12-31'):
        with pytest.raises(ReadinessError,match='pre-2025'):validate_panel(panel)


@pytest.mark.parametrize('kwargs',[{'vix':False},{'vix':True},{'vix_change':True},{'ridge_alpha':10.}])
def test_synthetic_future_shock_does_not_change_forecasts(panel,splits,kwargs):
    p=panel.iloc[:400].copy()
    def run(data):
        return walk_forward(data,model(**kwargs),target='intraday',splits=splits,
                            feature_builder=positive_features,emit_from='2024-01-01')[0]
    a=run(p);changed=p.copy();cut=p.index[350]
    changed.loc[changed.index>cut,['rv','intraday','vix_implied_variance','overnight_squared']]*=50
    b=run(changed)
    cols=['origin_date','target_date','forecast_variance','params','forecast_flag']
    pd.testing.assert_frame_equal(a.loc[a.origin_date<=cut,cols],b.loc[b.origin_date<=cut,cols])


def test_holdout_cutoff_before_feature_builder(panel,splits):
    seen=[]
    def builder(p):seen.append(p.index.max());return positive_features(p)
    walk_forward(panel,model(),target='intraday',splits=splits,feature_builder=builder,emit_from='2024-01-01')
    assert max(seen)<=pd.Timestamp('2024-12-31')


def test_tuning_uses_only_development_and_is_reproducible(panel,config,splits):
    a,score,forecast,_=tune_ridge(panel,config,'intraday',splits)
    changed=panel.copy();changed.loc['2024-01-01':,['rv','intraday','vix_implied_variance']]=1e9
    b,other,second,_=tune_ridge(changed,config,'intraday',splits)
    assert a==b and a['selection_available_on']<'2024-01-01'
    pd.testing.assert_frame_equal(score,other)
    pd.testing.assert_frame_equal(forecast.drop(columns='runtime_seconds'),second.drop(columns='runtime_seconds'))
    assert forecast.target_date.max()<=pd.Timestamp('2023-12-31')
    bad=deepcopy(config);bad['tuning']['cutoff']='2024-01-31'
    with pytest.raises(ValueError,match='development'):tune_ridge(panel,bad,'intraday',splits)


def test_tuning_insufficient_sample_has_no_default_fallback(panel,config,splits):
    config['tuning']['minimum_fold_observations']=500
    with pytest.raises(ValueError,match='Insufficient'):tune_ridge(panel,config,'intraday',splits)


def test_matched_pairs_refit_timestamps_issuance_and_metrics(panel,config,splits):
    selection,_,_,_=tune_ridge(panel,config,'intraday',splits)
    issued=[]
    f,fits,_=evaluate_models(panel,config,'intraday',selection,splits,issued.append)
    assert set(f.model)==set(NAMES) and len(issued)==len(f)
    assert all('observed_variance' not in row for row in issued)
    assert f.target_date.min()>=pd.Timestamp('2024-01-01')
    assert f.target_date.max()<=pd.Timestamp('2024-12-31')
    assert f.loc[f.forecast_valid,'training_end'].le(f.loc[f.forecast_valid,'origin_date']).all()
    assert f[f.common].groupby('model').target_date.agg(tuple).nunique()==1
    for _,g in fits[fits.model.ne('rv_ewma')].groupby('origin_date'):
        assert len({tuple(json.loads(x)['training_target_dates']) for x in g.diagnostics})==1
    for _,g in fits[fits.model.ne('rv_ewma')].groupby('model'):
        np.testing.assert_array_equal(np.diff(g.origin_index),np.full(len(g)-1,21))
    metrics,tests,slices,_=compare_models(f,fits,config)
    assert len(tests)==5 and not tests.independent_confirmation.any()
    assert metrics.status.eq('PROVISIONAL_EXPLORATORY').all()
    assert not slices.inferential_test.any()


def test_configuration_cannot_issue_forecasts_before_selection(panel,splits):
    m=model(configuration_available_on='2024-02-01')
    f,_=walk_forward(panel,m,target='intraday',splits=splits,feature_builder=positive_features,emit_from='2024-01-01')
    early=f[f.origin_date<'2024-02-01']
    assert early.forecast_variance.isna().all()
    assert early.forecast_flag.eq('configuration_unavailable_at_origin').all()


def test_shared_sample_mask_breaks_on_missing_vix_change(panel,config,splits):
    p=panel.copy();p.loc[p.index[330],'vix_implied_variance']=np.nan
    selection={'alpha':.1,'selection_available_on':'2023-12-29'}
    f,_,_=evaluate_models(p,config,'intraday',selection,splits)
    affected=f[f.origin_date.isin(p.index[330:332]) & f.model.ne('rv_ewma')]
    assert not affected.forecast_valid.any()
    assert not f[f.origin_date.isin(p.index[330:332])].common.any()
    assert affected.loc[affected.model.str.contains('log_har'),'raw_prediction'].isna().all()


def test_experiment_synthetic_idempotence_and_old_artifacts_untouched(tmp_path,monkeypatch,panel,config):
    from volrisk.evaluation import stage4b_experiment as runner
    import volrisk.evaluation.stage4b_reporting  # ensure real reporting module is exercised
    config['tuning']['minimum_fold_observations']=20
    old_config=tomllib.loads((ROOT/'config/har_rv.toml').read_text())
    old_config['estimation'].update(window=150,min_observations=40)
    splits=PeriodSplits.from_config(old_config['splits'])
    p=panel.loc[:'2024-12-31']
    records,fit_records=[],[]
    for target in config['evaluation']['targets']:
        frames=[]
        for name in ('har','log_har','har_vix','rv_ewma'):
            spec=model_specs('NIFTY',target,old_config)[name]
            f,fit=walk_forward(p,build_model(name,spec),target=target,splits=splits)
            for frame in (f,fit):frame['frequency']=5;frame['scenario']='eligible'
            frames.append(f);fit_records.append(fit)
        from volrisk.evaluation.har_metrics import attach_har_losses
        records.append(attach_har_losses(common_dates(pd.concat(frames,ignore_index=True),['har','log_har','har_vix','rv_ewma'])))
    old_f=pd.concat(records,ignore_index=True);old_fit=pd.concat(fit_records,ignore_index=True)
    before=old_f.copy(deep=True)
    monkeypatch.setattr(runner,'load_stage4',lambda c,r:(p,old_f,old_fit,{'run_id':'SYNTHETIC_ONLY','config':old_config},{}))
    (tmp_path/'config').mkdir()
    # Keep TOML setup dependency-free by substituting the tiny synthetic test settings.
    text=(ROOT/'config/stage4b.toml').read_text().replace('window = 500','window = 150').replace('min_observations = 126','min_observations = 40')
    text=text.replace('alphas = [0.1, 1.0, 10.0, 100.0]','alphas = [0.1, 10.0]').replace('bootstrap_draws = 10000','bootstrap_draws = 50')
    text=text.replace('minimum_fold_observations = 30','minimum_fold_observations = 20')
    cfg=tmp_path/'config/stage4b.toml';cfg.write_text(text)
    a=runner.run_stage4b(cfg,make_figures=False);b=runner.run_stage4b(cfg,make_figures=False)
    assert a==b and a['reproduction_passed'] and a['historical_artifacts_unchanged']
    assert not a['holdout_evaluated'] and not a['independent_confirmation']
    pd.testing.assert_frame_equal(old_f,before)
    for report in ('vix_model_diagnostics','positive_vix_models','frozen_forecasting_protocol'):
        assert (tmp_path/'reports'/f'{report}.md').exists()
    assert 'EXPLORATORY' in (tmp_path/'reports/positive_vix_models.md').read_text(encoding='utf-8')
