"""H4 draft monitoring: synthetic unit tests plus guards on the draft configuration."""
import copy
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from volrisk.monitoring import spec, alerts as al, evaluation as ev

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'config/h4_monitoring.toml'


@pytest.fixture
def config():
    return spec.load(CONFIG)


def test_draft_config_is_valid_advisory_and_unfrozen(config):
    p = config['protocol']
    assert p['status'] == spec.DRAFT and p['advisory_only']
    assert not any(p[k] for k in spec.FORBIDDEN_TRUE)
    assert config['risk']['scope'] == 'market_index_risk'


@pytest.mark.parametrize('key',spec.FORBIDDEN_TRUE)
def test_trading_pnl_or_directional_flags_rejected(config,key):
    bad = copy.deepcopy(config); bad['protocol'][key] = True
    with pytest.raises(ValueError,match=key): spec.validate(bad)


@pytest.mark.parametrize('section,field,value',[('alerts','elevated_percentile',95.),('alerts','thresholds_optimized_on_2024',True),
    ('alerts','no_model_substitution',False),('schedule','primary_horizon_sessions',5),('evaluation','early_stopping',True),
    ('risk','common_target','next_session_intraday_rv'),('risk','scope','portfolio_risk'),('risk','reliability_reported_separately',False)])
def test_invalid_protocol_settings_rejected(config,section,field,value):
    bad = copy.deepcopy(config); bad[section][field] = value
    with pytest.raises(ValueError): spec.validate(bad)


def test_development_window_must_precede_2024(config):
    bad = copy.deepcopy(config); bad['models']['development_window'] = ['2012-01-01','2024-06-30']
    with pytest.raises(ValueError,match='before 2024'): spec.validate(bad)


def test_alert_model_must_be_production_grade(config):
    bad = copy.deepcopy(config); bad['models']['alert_model'] = 'log_har'
    with pytest.raises(ValueError,match='production-grade'): spec.validate(bad)


def test_provisional_models_cannot_contribute_or_overlap(config):
    bad = copy.deepcopy(config); bad['models']['provisional']['contributes_to_production'] = True
    with pytest.raises(ValueError,match='must not contribute'): spec.validate(bad)
    bad = copy.deepcopy(config); bad['models']['production']['names'].append('har')
    with pytest.raises(ValueError,match='both production and provisional'): spec.validate(bad)


@pytest.mark.parametrize('text',spec.REQUIRED_LIMITATIONS)
def test_required_limitations_enforced(config,text):
    bad = copy.deepcopy(config); bad['alerts']['standard_limitations'].remove(text)
    with pytest.raises(ValueError,match='limitation'): spec.validate(bad)


def test_inventory_covers_every_prior_model_once(config):
    rows = spec.model_inventory(config); names = [r['model'] for r in rows]
    assert len(names) == len(set(names)) == 32
    sprint2 = {'expanding','rolling_20','rolling_60','ewma_094','garch_normal','garch_t','egarch_normal','egarch_t','gjr_normal','gjr_t'}
    stage4 = {'previous','mean5','mean22','rv_ewma','har','har_overnight','har_vix','har_vix_overnight','log_har',
              'spot_ewma','spot_garch','spot_egarch','spot_gjr'}
    assert sprint2|{'markov_switching_2','xgboost_v1'} == {r['model'] for r in rows if r['grade']=='PRODUCTION'}
    assert stage4|{'legacy_levels_har_vix'} <= {r['model'] for r in rows if r['grade']=='PROVISIONAL'}
    assert all(r['target'] == spec.COMMON_TARGET for r in rows)
    assert not any(r['contributes_to_production'] for r in rows if r['grade']=='PROVISIONAL')


def test_production_view_drops_provisional(config):
    view = spec.production_view({'gjr_normal':.2,'har':.3,'log_har_vix_c2c_h1':.4,'ewma_094':.18},config)
    assert set(view) == {'gjr_normal','ewma_094'}


def test_prospective_start_refused_while_draft(config):
    with pytest.raises(spec.ProtocolNotFrozen): spec.assert_prospective_allowed(config,CONFIG)
    frozen = copy.deepcopy(config); frozen['protocol']['status'] = spec.FROZEN
    with pytest.raises(spec.ProtocolNotFrozen,match='registration'): spec.assert_prospective_allowed(frozen,CONFIG,{'config_sha256':'x'})


def test_escalation_is_immediate_and_deescalation_waits():
    out = al.classify([.10,.25,.10,.10,.10,.10,.10,.10],.15,.20,deescalate_after=3)
    assert out[:4] == ['NORMAL','CRITICAL','CRITICAL','CRITICAL'] and out[4] == 'ELEVATED' and out[7] == 'NORMAL'


def test_reading_back_above_threshold_resets_deescalation_counter():
    out = al.classify([.25,.10,.10,.25,.10,.10,.10],.15,.20,deescalate_after=3)
    assert out[:6] == ['CRITICAL']*6 and out[6] == 'ELEVATED'


def test_operational_states_never_reported_as_normal():
    assert al.classify([.10,np.nan,.10,.10],.15,.20,operational=[None,None,'DATA_STALE',None]) == ['NORMAL','MODEL_FAILURE','DATA_STALE','NORMAL']
    with pytest.raises(ValueError): al.classify([.1],.15,.20,operational=['SOMETHING'])
    with pytest.raises(ValueError): al.classify([.1],.2,.15)


def test_exceedance_probability_normal_and_filtered():
    assert al.exceedance_probability(1e-4,.01*1.959964) == pytest.approx(.05,rel=1e-4)
    z = np.random.default_rng(0).standard_t(4,20000)
    pf = al.exceedance_probability(1e-4,.02,'filtered_historical',z)
    assert pf > al.exceedance_probability(1e-4,.02)            # fat tails raise large-move probability
    assert al.exceedance_probability(4e-4,.02) > al.exceedance_probability(1e-4,.02)
    assert np.isnan(al.exceedance_probability(np.nan,.02))
    with pytest.raises(ValueError): al.exceedance_probability(1e-4,.02,'filtered_historical',z[:10])


THR = dict(elevated=.16,critical=.20,elevated_percentile=75,critical_percentile=90)
EVENTS = dict(elevated=.0098,critical=.0157)
RELIABILITY = dict(calibration_status='NOT_YET_EVALUATED',recent_forecast_errors='none',availability_status='CURRENT',
                   last_return_date='2027-01-04',data_retrieved_at='2027-01-04T16:10+05:30',data_freshness_status='CURRENT',
                   data_quality_issues=[],provenance_status='DAILY_TRI_AUDITED')


def record(config,level='CRITICAL',var=1.96e-4,held=None):
    return al.build_record(asset='NIFTY50_TRI',report_date='2027-01-04',target_session='2027-01-05',level=level,previous_level='ELEVATED',
        forecast_variance=var,thresholds=THR,events=EVENTS,percentile=92.,model='gjr_normal',model_version='1.0.0',
        production_vols={'gjr_normal':.222,'ewma_094':.21,'rolling_20':.15},provisional_vols={'har':.30,'log_har':.25},
        reliability=RELIABILITY,limitations=config['alerts']['standard_limitations'],held_level=held)


def check(config,r):
    a = config['alerts']
    return al.validate_record(r,a['risk_fields'],a['reliability_fields'],spec.REQUIRED_LIMITATIONS)


def test_record_separates_risk_from_reliability(config):
    r = record(config)
    assert check(config,r)
    assert r['risk']['forecast_volatility_annualized'] == pytest.approx(np.sqrt(252*1.96e-4))
    assert 0 < r['risk']['prob_abs_return_above_critical_event'] < r['risk']['prob_abs_return_above_elevated_event'] < 1
    assert '90th percentile' in r['risk']['reason']
    assert not set(r['risk']) & set(r['reliability'])


def test_provisional_models_do_not_enter_production_consensus(config):
    r = record(config)['reliability']
    assert r['production_models_available'] == 3 and r['production_models_above_critical'] == 2
    assert {p['model'] for p in r['provisional_panel']} == {'har','log_har'}
    assert all(p['grade'] == 'PROVISIONAL' for p in r['provisional_panel'])


def test_held_level_is_explained(config):
    assert 'held by the de-escalation rule' in record(config,var=1e-4,held='CRITICAL')['risk']['reason']


def test_operational_record_carries_no_forecast(config):
    r = record(config,level='DATA_STALE',var=np.nan)
    assert np.isnan(r['risk']['forecast_volatility_annualized']) and np.isnan(r['risk']['prob_abs_return_above_critical_event'])
    assert 'no forecast was issued' in r['risk']['reason'] and check(config,r)


@pytest.mark.parametrize('text',['Reduce position now','Crash likely','Bearish conditions','Market will fall'])
def test_directional_or_trade_language_rejected(config,text):
    r = record(config); r['risk']['reason'] = text
    with pytest.raises(ValueError,match='non-directional'): check(config,r)


def test_missing_limitation_rejected(config):
    r = record(config); r['limitations'] = r['limitations'][1:]
    with pytest.raises(ValueError,match='limitation'): check(config,r)


def test_detection_metrics():
    d = ev.detection([1,1,0,0,1,0,0,0],[1,0,1,0,1,0,0,0])
    assert (d['true_positive'],d['false_positive'],d['false_negative'],d['true_negative']) == (2,1,1,4)
    assert d['precision'] == pytest.approx(2/3) and d['recall'] == pytest.approx(2/3)
    assert d['false_positive_rate'] == pytest.approx(1/5) and d['missed_event_rate'] == pytest.approx(1/3)
    assert d['lift'] == pytest.approx((2/3)/(3/8))
    lo,hi = d['precision_ci']; assert lo < d['precision'] < hi
    with pytest.raises(ValueError): ev.detection([1,0],[1])


def test_volatility_calibration_statistics():
    rng = np.random.default_rng(3); h = rng.uniform(5e-5,4e-4,5000); y = h*rng.chisquare(1,5000)
    assert ev.calibration_ratio(h,y) == pytest.approx(1,abs=.06)
    mz = ev.mincer_zarnowitz(h,y); assert mz['slope'] == pytest.approx(1,abs=.15)
    assert ev.qlike(h,y) < ev.qlike(2*h,y)


def test_brier_skill_and_reliability():
    rng = np.random.default_rng(4); p = rng.uniform(0,.5,4000); e = rng.random(4000) < p
    b = ev.brier_skill(p,e,base_rate=e.mean())
    assert b['skill'] > 0
    assert ev.brier_skill(np.full(4000,e.mean()),e,e.mean())['skill'] == pytest.approx(0,abs=1e-12)
    bins = ev.reliability_bins(p,e)
    assert sum(b['n'] for b in bins) == 4000
    for row in bins:
        if row['n'] > 200: assert abs(row['observed_frequency']-row['mean_probability']) < .06


def test_operational_availability():
    o = ev.operational(['NORMAL','CRITICAL','DATA_STALE','ELEVATED'],[True,True,True,False])
    assert o['availability'] == pytest.approx(.5) and o['count_data_stale'] == 1


def test_burden_counts_entries():
    b = al.burden(['NORMAL','CRITICAL','CRITICAL','NORMAL','ELEVATED']*252)
    assert b['entries_per_year_critical'] == pytest.approx(252/5) and b['share_critical'] == pytest.approx(.4)


@pytest.mark.skipif(not (ROOT/'experiments/econometric/runs').exists(),reason='forecast archive not present')
def test_draft_thresholds_read_only_development_rows(config):
    from volrisk.monitoring.thresholds import production_thresholds, provisional_thresholds, read_window, DAILY_COLUMNS
    m = config['models']
    f = read_window(ROOT/m['source_run']/'forecasts.parquet',DAILY_COLUMNS,*m['development_window'])
    assert f.target_date.max() <= pd.Timestamp('2021-12-31')
    thr,evt,_,_ = production_thresholds(config,ROOT)
    assert (thr.threshold_elevated < thr.threshold_critical).all() and set(thr.grade) == {'PRODUCTION'}
    assert pd.to_datetime(thr.last_target).max() <= pd.Timestamp('2021-12-31')
    assert evt.base_rate_critical.between(.09,.11).all()
    prov = provisional_thresholds(config,ROOT)
    assert set(prov.grade) == {'PROVISIONAL'} and pd.to_datetime(prov.last_target).max() <= pd.Timestamp('2023-12-31')
