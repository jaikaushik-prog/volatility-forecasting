"""Synthetic fixtures only; these tests are not empirical research results."""
from copy import deepcopy
import json
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd
import pytest

from volrisk.data.intraday.calendar import SessionCalendar, local_time
from volrisk.data.intraday.normalize import read_source, normalize_frames
from volrisk.data.intraday.realized import aggregate_session, daily_measures
from volrisk.data.intraday.features import realized_features, vix_features
from volrisk.data.intraday.pipeline import run_integration
from volrisk.data.storage import sha256

ROOT=Path(__file__).resolve().parents[1]
CONFIG=tomllib.loads((ROOT/'config/intraday.toml').read_text())


@pytest.fixture
def calendar():
    market={'verified_start':'2024-01-01','verified_end':'2024-12-31',
            'regular_segments':[['09:15','09:30']], 'holidays':['2024-01-03'],
            'special_sessions':['2024-01-06'], 'session_overrides':{
                '2024-01-06':{'segments':[['09:15','09:20'],['09:25','09:30']],'verified':True,'kind':'special'}}}
    return SessionCalendar('NSE',{}, {'markets':{'NSE':market}})


def source(calendar, dates=('2024-01-02',), asset='NIFTY', shift=0.):
    times=pd.DatetimeIndex([t for d in dates for t in calendar.minutes(d).timestamp])
    n=len(times)
    close=100*np.exp(np.arange(1,n+1)*.001+shift)
    opened=100*np.exp(np.arange(n)*.001+shift)
    return pd.DataFrame({'timestamp':times,'open':opened,'high':close+.1,'low':opened-.1,'close':close,
        'volume':np.zeros(n),'source_file':'synthetic.csv','source_sha256':'test','source_row':np.arange(n)+2,
        'source_timestamp':times.astype(str),'identity_mismatch':False})


def canonical(calendar, dates=('2024-01-02',), raw=None, key='nifty'):
    raw=source(calendar,dates) if raw is None else raw
    return normalize_frames([raw],CONFIG['assets'][key],calendar,CONFIG['quality'])[0]


def test_calendar_holiday_special_and_unknown(calendar):
    assert not calendar.describe('2024-01-03')['expected_session']
    assert calendar.describe('2024-01-06')['expected_minutes']==10
    assert calendar.describe('2024-01-06')['schedule_verified']
    assert not calendar.describe('2025-01-02')['schedule_verified']
    dates=calendar.grid('2024-01-02','2024-01-07').session_date.dt.strftime('%Y-%m-%d').tolist()
    assert dates==['2024-01-02','2024-01-04','2024-01-05','2024-01-06']


def test_source_schema_timezone_and_pickle_refusal(tmp_path):
    path=tmp_path/'input.csv'
    pd.DataFrame({'time':['2024-01-02 09:15','2024-01-02 09:16'],
                  'open':[100,101],'high':[102,103],'low':[99,100],'close':[101,102]}).to_csv(path,index=False)
    digest=sha256(path)
    frame,report=read_source(path,CONFIG['assets']['nifty'])
    assert str(frame.timestamp.dt.tz)=='Asia/Kolkata'
    assert not report['timezone_verified']
    assert report['rows']==2 and report['source_timezone']=='not encoded; unknown'
    assert sha256(path)==digest
    with pytest.raises(ValueError,match='never deserialized'):
        read_source(tmp_path/'malicious.pkl',CONFIG['assets']['india_vix'])


def test_explicit_utc_and_end_bar(tmp_path):
    path=tmp_path/'input.csv'
    pd.DataFrame({'timestamp':['2024-01-02T03:46:00+00:00'],
        'open':[100],'high':[101],'low':[99],'close':[100]}).to_csv(path,index=False)
    spec={**CONFIG['assets']['nifty'],'bar_label':'end'}
    frame,_=read_source(path,spec)
    assert frame.timestamp.iloc[0]==local_time('2024-01-02','09:15')


def test_sort_identical_duplicates_ignore_export_index(calendar):
    raw=source(calendar)
    duplicate=raw.iloc[[2]].assign(source_row=99)
    frame,rejected,actions=normalize_frames([pd.concat([raw.iloc[::-1],duplicate])],CONFIG['assets']['nifty'],calendar,CONFIG['quality'])
    assert frame.timestamp.is_monotonic_increasing and frame.timestamp.is_unique
    assert len(frame)==15 and len(rejected)==1
    assert actions['identical_duplicates_removed']==1
    assert frame.iloc[2].source_row==4


def test_conflicting_duplicates_quarantine_all(calendar):
    raw=source(calendar)
    conflict=raw.iloc[[2]].assign(close=103.,high=104.,source_row=99)
    frame,rejected,actions=normalize_frames([pd.concat([raw,conflict])],CONFIG['assets']['nifty'],calendar,CONFIG['quality'])
    assert len(frame)==14 and len(rejected)==2 and actions['conflicting_timestamps']==1
    assert raw.iloc[2].timestamp not in set(frame.timestamp)


@pytest.mark.parametrize('column,value,flag',[('close',0.,'invalid_price'),('open',np.inf,'invalid_price'),
    ('low',np.nan,'invalid_price'),('high',99.,'invalid_ohlc')])
def test_invalid_prices_retained_and_rv_missing(calendar,column,value,flag):
    raw=source(calendar);raw.loc[3,column]=value
    frame=canonical(calendar,raw=raw)
    assert len(frame)==15 and frame.loc[3,flag] and not frame.loc[3,'valid_bar']
    daily,_=daily_measures(frame,calendar)
    assert pd.isna(daily.loc[0,'rv_1min']) and daily.loc[0,'missing_or_invalid_minutes']==1


def test_off_grid_never_floored(calendar):
    raw=source(calendar);raw.loc[3,'timestamp']+=pd.Timedelta(seconds=1)
    frame=canonical(calendar,raw=raw)
    assert frame.iloc[3].off_minute_grid and frame.iloc[3].timestamp.second==1
    daily,_=daily_measures(frame,calendar)
    assert daily.iloc[0].missing_minutes==1 and not daily.iloc[0].rv_eligible


def test_extreme_price_not_deleted(calendar):
    raw=source(calendar)
    raw.loc[7,['open','close','high','low']]=[115.,115.,116.,114.]
    frame=canonical(calendar,raw=raw)
    assert len(frame)==15 and frame.extreme_return.sum()==2
    assert frame.iloc[7].valid_bar


def test_bar_aggregation_and_short_tail(calendar):
    frame=canonical(calendar)
    bars=aggregate_session(frame,calendar.describe('2024-01-02'),5)
    assert len(bars)==3 and bars.complete.all()
    assert bars.iloc[0].open==frame.iloc[0].open
    assert bars.iloc[0].close==frame.iloc[4].close
    assert bars.iloc[0].high==frame.iloc[:5].high.max()
    assert bars.iloc[0].low==frame.iloc[:5].low.min()
    assert bars.iloc[0].available_at==local_time('2024-01-02','09:20')
    np.testing.assert_allclose(bars.intraday_log_return,.005,atol=1e-14)
    ten=aggregate_session(frame,calendar.describe('2024-01-02'),10)
    assert ten.duration_minutes.tolist()==[10,5] and ten.short_interval.tolist()==[False,True]


def test_rv_semivariances_and_annualization(calendar):
    daily,bars=daily_measures(canonical(calendar),calendar)
    row=daily.iloc[0]
    assert row.rv_1min==pytest.approx(15*.001**2)
    assert row.rv_5min==pytest.approx(3*.005**2)
    assert row.rv_10min==pytest.approx(.01**2+.005**2)
    assert row.rv_15min==pytest.approx(.015**2)
    assert row.annualized_realized_vol_5min==pytest.approx(np.sqrt(row.rv_5min*252))
    for f in (1,5,10,15):
        assert row[f'positive_semivariance_{f}min']+row[f'negative_semivariance_{f}min']==pytest.approx(row[f'rv_{f}min'])
    assert pd.isna(row.overnight_log_return) and not row.research_ready


def test_negative_semivariance(calendar):
    raw=source(calendar)
    raw[['open','close']]=200-raw[['open','close']]
    raw['high']=raw[['open','close']].max(axis=1)+1
    raw['low']=raw[['open','close']].min(axis=1)-1
    daily,_=daily_measures(canonical(calendar,raw=raw),calendar)
    assert daily.iloc[0].positive_semivariance_1min==0
    assert daily.iloc[0].negative_semivariance_1min==pytest.approx(daily.iloc[0].rv_1min)


def test_missing_day_blocks_overnight_and_lags(calendar):
    daily,_=daily_measures(canonical(calendar,dates=('2024-01-02','2024-01-05')),calendar)
    assert daily.session_date.dt.strftime('%Y-%m-%d').tolist()==['2024-01-02','2024-01-04','2024-01-05']
    assert daily.iloc[1].source_rows==0 and pd.isna(daily.iloc[1].rv_5min)
    assert pd.isna(daily.iloc[2].overnight_log_return)
    assert pd.isna(realized_features(daily).iloc[2].rv_lag1)


def test_overnight_holiday_and_return_reconciliation(calendar):
    raw=source(calendar,dates=('2024-01-02','2024-01-04'))
    raw.loc[15:,['open','high','low','close']]*=1.02
    daily,bars=daily_measures(canonical(calendar,raw=raw),calendar)
    row=daily.iloc[1]
    assert row.overnight_log_return==pytest.approx(np.log(1.02))
    assert row.close_to_close_log_return==pytest.approx(row.overnight_log_return+row.intraday_open_to_close_log_return)
    assert row.full_rv_proxy_5min==pytest.approx(row.rv_5min+np.log(1.02)**2)
    assert daily.iloc[1].rv_5min==pytest.approx(daily.iloc[0].rv_5min)


def test_interior_gap_does_not_remove_valid_overnight_endpoints(calendar):
    raw=source(calendar,dates=('2024-01-02','2024-01-04')).drop(index=[4])
    daily,_=daily_measures(canonical(calendar,raw=raw),calendar)
    assert pd.isna(daily.iloc[0].rv_5min)
    assert np.isfinite(daily.iloc[1].overnight_log_return)


def test_special_break_is_separate(calendar):
    raw=source(calendar,dates=('2024-01-06',))
    raw.loc[5:,['open','high','low','close']]*=1.03
    daily,bars=daily_measures(canonical(calendar,raw=raw),calendar,jump_min_intervals=2)
    row=daily.iloc[0]
    assert row.rv_5min==pytest.approx(2*.005**2)
    assert row.reopening_log_return==pytest.approx(np.log(1.03))
    assert row.full_session_rv_5min==pytest.approx(row.rv_5min+np.log(1.03)**2)
    assert bars[5].segment.tolist()==[0,1]
    assert pd.isna(row.bipower_variation_5min)


def test_unverified_calendar_blocks_rv_and_overnight(calendar):
    calendar.unknown.add('2024-01-04')
    daily,_=daily_measures(canonical(calendar,dates=('2024-01-02','2024-01-04','2024-01-05')),calendar)
    assert not daily.iloc[1].schedule_verified and pd.isna(daily.iloc[1].rv_1min)
    assert pd.isna(daily.iloc[2].overnight_log_return)


def daily_fixture(calendar,n=35):
    dates=calendar.grid('2024-02-01','2024-04-01').session_date.iloc[:n].dt.strftime('%Y-%m-%d').tolist()
    daily,_=daily_measures(canonical(calendar,dates=dates),calendar)
    return daily,dates


def test_features_lags_and_future_shock(calendar):
    daily,_=daily_fixture(calendar)
    daily['rv_5min']=np.arange(1,len(daily)+1)/10000
    before=realized_features(daily)
    assert before.iloc[5].rv_mean5_lag1==pytest.approx(np.mean(np.arange(1,6))/10000)
    assert pd.isna(before.iloc[21].rv_mean22_lag1)
    changed=daily.copy();changed.loc[25:,'rv_5min']*=1000
    pd.testing.assert_frame_equal(before.iloc[:25],realized_features(changed).iloc[:25])


def test_vix_available_at_origin_no_future_or_cross_day_fill(calendar):
    daily,dates=daily_fixture(calendar,4)
    frame=canonical(calendar,dates=dates,key='india_vix')
    frame['close']=20.
    after=frame.iloc[[14]].copy()
    after['available_at']=daily.iloc[0].session_close+pd.Timedelta(minutes=1)
    after['close']=999.
    frame=pd.concat([frame,after],ignore_index=True)
    frame=frame[~frame.session_date.eq(daily.iloc[1].session_date)]
    result=vix_features(daily,frame,percentile_min_history=1)
    assert result.iloc[0].vix_eod_percent==20 and pd.isna(result.iloc[1].vix_eod_percent)
    assert pd.isna(result.iloc[2].vix_lag1_percent)
    assert result.iloc[2].vix_percentile_past==.5
    assert (result.vix_observation_available_at.dropna()<=result.feature_origin_timestamp[result.vix_eod_available]).all()
    changed=frame.copy();changed.loc[changed.session_date>daily.iloc[2].session_date,'close']=99.
    pd.testing.assert_frame_equal(result.iloc[:3],vix_features(daily,changed,percentile_min_history=1).iloc[:3])


def test_vix_stale_endpoint_missing_and_units(calendar):
    daily,dates=daily_fixture(calendar,4)
    frame=canonical(calendar,dates=dates,key='india_vix')
    frame['close']=20.
    first=daily.iloc[0]
    frame=frame[~(frame.session_date.eq(first.session_date)&frame.available_at.gt(first.session_close-pd.Timedelta(minutes=2)))]
    result=vix_features(daily,frame,percentile_min_history=1)
    assert pd.isna(result.iloc[0].vix_eod_percent)
    assert result.iloc[1].vix_annualized_decimal==.2
    assert result.iloc[1].vix_30calendar_variance_proxy==pytest.approx(.2**2*30/365)
    assert not result.research_ready.any()


def test_pipeline_reproducibility_and_raw_preservation(tmp_path,calendar):
    (tmp_path/'config').mkdir();(tmp_path/'data/raw').mkdir(parents=True)
    config_text=(ROOT/'config/intraday.toml').read_text()
    (tmp_path/'config/intraday.toml').write_text(config_text)
    market=deepcopy(calendar.spec)
    cal={'markets':{'NSE':market,'BSE':market},'evidence':[]}
    (tmp_path/'config/intraday_calendar.json').write_text(json.dumps(cal))
    (tmp_path/'config/calendars.json').write_text('{}')
    for key,spec in CONFIG['assets'].items():
        for i,name in enumerate(spec['files']):
            date='2024-01-02' if i==0 else '2024-01-04'
            raw=source(calendar,dates=(date,))
            raw.timestamp=raw.timestamp.dt.tz_localize(None)
            raw[['timestamp','open','high','low','close','volume']].to_csv(tmp_path/name,index=False)
    path=tmp_path/'config/intraday.toml'
    inputs={str(p):sha256(p) for p in (tmp_path/'data/raw').iterdir()}
    first=run_integration(path,make_figures=False)
    second=run_integration(path,make_figures=False)
    assert first==second and not first['summary']['research_ready']
    assert inputs=={str(p):sha256(p) for p in (tmp_path/'data/raw').iterdir()}
    assert (tmp_path/'reports/intraday_data_audit.md').exists()
    assert (tmp_path/'data/processed/features/nifty_vix_features_daily.parquet').exists()
    run=tmp_path/'data/processed/intraday_runs'/first['run_id']
    for relative,digest in first['output_sha256'].items():
        assert sha256(run/relative)==digest
    (run/'features/nifty_realized_vol_daily.parquet').write_bytes(b'corrupted')
    with pytest.raises(ValueError,match='Immutable intraday output has changed'):
        run_integration(path,make_figures=False)


def test_no_adjacent_returns_and_empty_source(calendar):
    frame=canonical(calendar,raw=source(calendar).iloc[:1])
    assert frame.intraday_log_return_adjacent.isna().all()
    assert not frame.mad_outlier.any()
    with pytest.raises(ValueError,match='no canonical timestamps'):
        canonical(calendar,raw=source(calendar).iloc[:0])


def test_stale_threshold_counts_elapsed_minutes(calendar):
    raw=source(calendar)
    raw[['open','high','low','close']]=100.
    frame=canonical(calendar,raw=raw)
    assert frame.iloc[9].unchanged_run_minutes==9
    assert not frame.iloc[9].stale_sequence and frame.iloc[10].stale_sequence
    daily,_=daily_measures(frame,calendar)
    assert daily.iloc[0].rv_5min==0.  # Valid flat series stays observable, with review flags.


def test_bipower_formula_and_interval_requirement(calendar):
    daily,_=daily_measures(canonical(calendar),calendar,jump_min_intervals=3)
    assert daily.iloc[0].bipower_variation_5min==pytest.approx(np.pi/2*3*.005**2)
    assert daily.iloc[0].jump_variance_proxy_5min==0.
    insufficient,_=daily_measures(canonical(calendar),calendar,jump_min_intervals=4)
    assert pd.isna(insufficient.iloc[0].jump_variance_proxy_5min)


def test_future_raw_price_shock_does_not_change_saved_features(calendar):
    _,dates=daily_fixture(calendar,30)
    raw=source(calendar,dates=dates)
    daily,_=daily_measures(canonical(calendar,raw=raw),calendar)
    before=realized_features(daily)
    origin=daily.iloc[23].session_close
    altered=raw.copy()
    altered.loc[altered.timestamp>origin,['open','high','low','close']]*=1.5
    updated,_=daily_measures(canonical(calendar,raw=altered),calendar)
    pd.testing.assert_frame_equal(before.iloc[:24],realized_features(updated).iloc[:24])


def test_missing_source_fails_without_fabricating_output(tmp_path):
    (tmp_path/'config').mkdir()
    (tmp_path/'config/intraday.toml').write_text((ROOT/'config/intraday.toml').read_text())
    (tmp_path/'config/calendars.json').write_text('{}')
    (tmp_path/'config/intraday_calendar.json').write_text('{}')
    with pytest.raises(FileNotFoundError,match='no substitute generated'):
        run_integration(tmp_path/'config/intraday.toml',make_figures=False)
    assert not (tmp_path/'data/processed').exists()
