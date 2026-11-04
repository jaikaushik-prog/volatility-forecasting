"""Behavioral checks for report issuance and the monitoring defects found in review."""
import json
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import pytest

from volrisk.monitoring import alerts, evaluation
from volrisk.monitoring import daily
from volrisk.monitoring.ledger import Ledger
from volrisk.daily_cli import main, record_review, record_outcome

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config/daily_monitoring.toml'


def test_brier_reference_uses_same_missing_outcome_mask():
    result=evaluation.brier_skill([.1,.2,.3,np.nan],[0,np.nan,1,0],.1)
    assert result['n']==2
    assert result['brier']==pytest.approx(.25)
    assert result['reference']==pytest.approx(.41)
    assert result['skill']==pytest.approx(1-.25/.41)
    assert np.isnan(evaluation.brier_skill([np.nan],[np.nan],.1)['skill'])


@pytest.mark.parametrize('p,e',[([.1],[0,1]),([[.1]],[0]),([1.2],[0]),([.1],[.5])])
def test_invalid_probability_inputs_rejected(p,e):
    with pytest.raises(ValueError): evaluation.brier_skill(p,e,.1)


def test_alert_alignment_cannot_silently_drop_sessions():
    with pytest.raises(ValueError,match='aligned'):
        alerts.classify([.3,.1,.1],.15,.2,operational=[None])
    with pytest.raises(ValueError): alerts.classify([.3],.15,np.inf)


def test_mz_intervals_match_statsmodels_hac_on_complete_series():
    import statsmodels.api as sm
    rng=np.random.default_rng(17)
    h=rng.uniform(.0001,.001,300); y=h*rng.chisquare(1,300)
    result=evaluation.mincer_zarnowitz(h,y,maxlags=5)
    expected=sm.OLS(y,sm.add_constant(h)).fit(cov_type='HAC',cov_kwds={'maxlags':5,'use_correction':True})
    np.testing.assert_allclose(result['slope_ci'],expected.conf_int()[1],rtol=1e-8)
    assert np.isnan(evaluation.mincer_zarnowitz([1,1,1],[1,2,3])['slope'])


def test_mz_keeps_gap_spacing():
    h=np.linspace(.001,.002,30); y=h*(1+.3*np.sin(np.arange(30)))
    h[10:20]=np.nan
    kept=np.isfinite(h)
    full=evaluation.mincer_zarnowitz(h,y)
    compressed=evaluation.mincer_zarnowitz(h[kept],y[kept])
    assert full['slope']==pytest.approx(compressed['slope'])
    assert not np.allclose(full['slope_ci'],compressed['slope_ci'])


def test_ledger_atomicity_conflicts_and_hash_verification(tmp_path):
    path=tmp_path/'ledger.sqlite3'
    with Ledger(path) as ledger:
        ledger.append_batch([('forecast','a',{'v':1}),('alert','a',{'level':'NORMAL'})])
        ledger.append_batch([('forecast','a',{'v':1})])
        assert ledger.verify()==2
        with pytest.raises(ValueError,match='Conflicting'):
            ledger.append_batch([('forecast','b',{'v':2}),('alert','a',{'level':'CRITICAL'})])
        assert ledger.get('forecast','b') is None
        with pytest.raises(sqlite3.IntegrityError): ledger.db.execute('DELETE FROM events')
    # Even if a writer bypasses the SQL guard, the chain detects a changed payload.
    with sqlite3.connect(path) as db:
        db.execute('DROP TRIGGER no_update')
        db.execute("UPDATE events SET payload='{}' WHERE sequence=1")
    with pytest.raises(ValueError,match='integrity'): Ledger(path)


@pytest.fixture
def input_case(tmp_path,monkeypatch):
    calendar=daily.Calendar(ROOT/'config/calendars.json')
    dates=calendar.sessions('2021-01-01','2023-12-29')
    frame=pd.DataFrame({'Date':dates.strftime('%Y-%m-%d'),'Index Name':'NIFTY 50',
        'Total Returns Index':10000*np.exp(np.cumsum(np.random.default_rng(2).normal(0,.01,len(dates))))})
    source=tmp_path/'tri.csv'; frame.to_csv(source,index=False)
    def models(returns,cfg):
        assert returns.index.max()==pd.Timestamp('2023-12-29')
        return [dict(model=name,variance=.00025,annualized_volatility=float(np.sqrt(252*.00025)),
            status='ok',message='',last_fit_date='2023-12-29') for name in cfg['report']['models']]
    monkeypatch.setattr(daily,'forecast_models',models)
    return dict(config=CONFIG,source=source,as_of='2023-12-29',output=tmp_path/'output'),frame


def test_daily_report_is_idempotent_and_has_forecast_before_alert(input_case):
    kw,frame=input_case
    result,path=daily.run_daily(**kw)
    repeated,_=daily.run_daily(**kw)
    assert repeated==result and result['level']=='CRITICAL'
    assert result['target_session']=='2024-01-01'
    assert result['daily_volatility']==pytest.approx(np.sqrt(.00025))
    assert path.is_file() and 'HISTORICAL PREVIEW' in path.read_text(encoding='utf-8')
    assert json.loads(path.with_suffix('.json').read_text())['run_id']==result['run_id']
    with Ledger(kw['output']/'preview/ledger.sqlite3') as ledger:
        assert ledger.verify()==2
        assert ledger.records('forecast')[0]['_sequence']<ledger.records('alert')[0]['_sequence']
    frame.loc[len(frame)-1,'Total Returns Index']*=1.01; frame.to_csv(kw['source'],index=False)
    with pytest.raises(ValueError,match='already issued'): daily.run_daily(**kw)


@pytest.mark.parametrize('defect,expected',[
    ('stale','DATA_STALE'),('missing_file','DATA_UNAVAILABLE'),('missing_session','DATA_UNAVAILABLE'),
    ('negative','DATA_UNAVAILABLE'),('duplicate','DATA_UNAVAILABLE'),('future','DATA_UNAVAILABLE')])
def test_bad_inputs_never_generate_normal_or_a_forecast(input_case,defect,expected):
    kw,frame=input_case
    if defect=='stale': frame=frame.iloc[:-1]
    elif defect=='missing_session': frame=frame.drop(frame.index[-3])
    elif defect=='negative': frame.loc[frame.index[-1],'Total Returns Index']=-2
    elif defect=='duplicate': frame=pd.concat([frame,frame.iloc[-1:]])
    elif defect=='future': frame.loc[frame.index[-1],'Date']='2024-01-01'
    if defect=='missing_file': kw['source'].unlink()
    else: frame.to_csv(kw['source'],index=False)
    result,path=daily.run_daily(**kw)
    assert result['level']==expected and path.is_file()
    assert result['variance'] is None and result['probability_critical'] is None
    assert not result['forecasts']


def test_failed_alert_model_is_not_replaced_by_comparison(input_case,monkeypatch):
    kw,_=input_case
    def failed(returns,cfg):
        return [dict(model='gjr_normal',variance=None,annualized_volatility=None,status='failed',message='fit failed'),
                dict(model='ewma_094',variance=.0001,annualized_volatility=.16,status='ok',message='')]
    monkeypatch.setattr(daily,'forecast_models',failed)
    result,_=daily.run_daily(**kw)
    assert result['level']=='MODEL_FAILURE' and result['variance'] is None


def test_missing_session_resets_step_down_counter():
    state=daily.advance(None,'CRITICAL',3)
    state=daily.advance(state,'NORMAL',3); state=daily.advance(state,'NORMAL',3)
    assert state['below_count']==2
    state=daily.advance(state,'DATA_STALE',3)
    state=daily.advance(state,'NORMAL',3)
    assert state==dict(held_level='CRITICAL',below_count=1)


def test_calendar_does_not_infer_future_coverage():
    cal=daily.Calendar(ROOT/'config/calendars.json')
    assert not cal.verified('2026-11-05')
    with pytest.raises(ValueError,match='coverage'): cal.next_session('2026-11-02')
    assert cal.next_session('2023-12-29')==pd.Timestamp('2024-01-01')


def test_preview_and_live_guards(input_case):
    kw,_=input_case
    with pytest.raises(ValueError,match='pre-2025'): daily.run_daily(**dict(kw,as_of='2026-11-05'))
    with pytest.raises(ValueError,match='FROZEN'): daily.run_daily(**kw,mode='live')
    with pytest.raises(ValueError,match='FROZEN'): daily.register(CONFIG,kw['output']/'registration.json','Reviewer')


def test_render_escapes_source_text(input_case):
    from volrisk.monitoring.daily_reporting import render_html
    kw,_=input_case; result,_=daily.run_daily(**kw)
    result['source_name']='<script>alert(1)</script>'
    html=render_html(result)
    assert '<script>' not in html and '&lt;script&gt;' in html


def test_reviews_and_outcomes_are_separate_from_forecast(input_case):
    kw,frame=input_case; result,_=daily.run_daily(**kw)
    ledger_path=kw['output']/'preview/ledger.sqlite3'
    record_review(ledger_path,result['run_id'],'Analyst','Reviewed concentration; recorded for discussion')
    source=kw['source'].with_name('outcome.csv')
    target=frame.iloc[-1:].copy(); target['Date']=result['target_session']; target['Total Returns Index']*=1.02
    pd.concat([frame,target]).to_csv(source,index=False)
    outcome=record_outcome(ledger_path,result['run_id'],source)
    assert outcome['log_return']==pytest.approx(np.log(1.02))
    record_outcome(ledger_path,result['run_id'],source)
    with Ledger(ledger_path) as ledger:
        assert ledger.verify()==4
        assert ledger.get('alert',result['run_id'])==result
    frame.loc[len(frame)-1,'Total Returns Index']*=1.01
    pd.concat([frame,target]).to_csv(source,index=False)
    with pytest.raises(ValueError,match='revised'): record_outcome(ledger_path,result['run_id'],source)


def test_cli_reports_missing_data_as_nonzero_exit(input_case):
    kw,_=input_case
    assert main(['report','--config',str(CONFIG),'--source',str(kw['source'].with_name('absent.csv')),
        '--as-of',kw['as_of'],'--output',str(kw['output'])])==1


def test_issuance_lock_prevents_competing_state_updates(input_case):
    kw,_=input_case
    with daily.issuance_lock(kw['output']/'preview'):
        with pytest.raises(ValueError,match='issuance is running'): daily.run_daily(**kw)
    assert not (kw['output']/'preview/.issuance.lock').exists()


def test_settings_change_cannot_rewrite_an_issued_report(input_case,tmp_path):
    kw,_=input_case
    cfg=tmp_path/'config/daily.toml'; cfg.parent.mkdir()
    text=CONFIG.read_text(encoding='utf-8').replace('"config/',f'"{ROOT.as_posix()}/config/')
    text=text.replace('"reports/',f'"{ROOT.as_posix()}/reports/')
    cfg.write_text(text,encoding='utf-8')
    kw['config']=cfg
    daily.run_daily(**kw)
    cfg.write_text(text.replace('deescalation_sessions = 3','deescalation_sessions = 4'),encoding='utf-8')
    with pytest.raises(ValueError,match='already issued'): daily.run_daily(**kw)


def test_registration_binds_code_and_inputs(tmp_path):
    cfg=tmp_path/'config/daily.toml'; cfg.parent.mkdir()
    text=CONFIG.read_text(encoding='utf-8').replace('"config/',f'"{ROOT.as_posix()}/config/')
    text=text.replace('"reports/',f'"{ROOT.as_posix()}/reports/').replace('status = "DRAFT"','status = "FROZEN"')
    cfg.write_text(text,encoding='utf-8')
    registration=tmp_path/'registration.json'
    result=daily.register(cfg,registration,'Synthetic test reviewer')
    result['registered_at']='2023-12-28T00:00:00Z'  # test clock only; no real registration changed
    registration.write_text(json.dumps(result),encoding='utf-8')
    settings=daily.load_settings(cfg)
    daily._authorize(settings,'live',pd.Timestamp('2023-12-29'),registration,pd.Timestamp('2023-12-29T11:00:00Z'),True)
    with pytest.raises(ValueError,match='not closed'):
        daily._authorize(settings,'live',pd.Timestamp('2023-12-29'),registration,pd.Timestamp('2023-12-29T06:00:00Z'),True)
    result['fingerprint']['code']['monitoring/daily.py']='altered'
    registration.write_text(json.dumps(result),encoding='utf-8')
    with pytest.raises(ValueError,match='does not match'):
        daily._authorize(settings,'live',pd.Timestamp('2023-12-29'),registration,pd.Timestamp('2023-12-29T11:00:00Z'),True)


def test_live_report_rejects_late_issuance(input_case,tmp_path):
    kw,_=input_case
    cfg=tmp_path/'config/daily.toml'; cfg.parent.mkdir()
    text=CONFIG.read_text(encoding='utf-8').replace('"config/',f'"{ROOT.as_posix()}/config/')
    text=text.replace('"reports/',f'"{ROOT.as_posix()}/reports/').replace('status = "DRAFT"','status = "FROZEN"')
    cfg.write_text(text,encoding='utf-8')
    reg=tmp_path/'reg.json'; payload=daily.register(cfg,reg,'Test reviewer')
    payload['registered_at']='2023-12-28T00:00:00Z'; reg.write_text(json.dumps(payload),encoding='utf-8')
    kw.update(config=cfg,mode='live',registration=reg,source_confirmed=True,now='2024-01-01T05:00:00Z')
    with pytest.raises(ValueError,match='already opened'): daily.run_daily(**kw)


def test_cli_missing_ledger_does_not_create_one(tmp_path):
    path=tmp_path/'absent.sqlite3'
    assert main(['verify','--ledger',str(path)])==2
    assert not path.exists()
