"""Synthetic unit fixtures only; no synthetic research results."""
from dataclasses import replace
import numpy as np
import pandas as pd
import pytest
from volrisk.economics.accounting import Policy,rebalance,open_session,run_close,desired_weight
from volrisk.economics.alignment import Instrument,validate_signal
from volrisk.economics.metrics import summarize,match_constant,paired_uncertainty,holm
from volrisk.economics.attribution import decompose


def prices(n=70,start='2023-09-01',seed=2):
    rng=np.random.default_rng(seed); dates=pd.bdate_range(start,periods=n)
    r=rng.normal(.0004,.012,n)
    return pd.DataFrame({'simple_return':r,'origin_timestamp':dates.tz_localize('Asia/Kolkata')+pd.Timedelta(hours=15,minutes=30)},index=dates)


def signals(p,weights=.5,model='m'):
    rows=[]
    for i in range(1,len(p)-1):
        w=weights if np.isscalar(weights) else weights[i]
        rows.append(dict(model=model,horizon=2,asset='NIFTY50_TRI',origin_date=p.index[i-1],
            execution_date=p.index[i],target_date=p.index[i+1],issued_at=p.origin_timestamp.iloc[i-1]+pd.Timedelta(microseconds=1),
            forecast_variance=(.12/w)**2/252 if w else np.nan,target_quantity='daily_close_to_close_log_return_variance',failure_reason=''))
    return pd.DataFrame(rows)


@pytest.mark.parametrize('target',[0.,.1,.6,1.])
@pytest.mark.parametrize('equity,cash',[(0.,1000.),(700.,300.),(1000.,0.)])
def test_post_cost_weight_and_pnl(target,equity,cash):
    e,c,t,cost=rebalance(equity,cash,target,.002)
    assert e>=0 and c>=0
    assert e/(e+c)==pytest.approx(target)
    assert e+c==pytest.approx(equity+cash-cost)
    assert cost==pytest.approx(abs(t)*.002)


def test_no_same_close_or_misaligned_signal():
    p=prices();row=signals(p).iloc[0].to_dict();execution=p.origin_timestamp.iloc[1]
    validate_signal(row,execution,p.index[2],'NIFTY50_TRI')
    with pytest.raises(ValueError,match='Same-close'):
        validate_signal(row|{'issued_at':execution},execution,p.index[2],'NIFTY50_TRI')
    with pytest.raises(ValueError,match='subsequent'):
        validate_signal(row,execution,p.index[3],'NIFTY50_TRI')
    with pytest.raises(ValueError,match='risk mismatch'):
        validate_signal(row|{'target_quantity':'intraday_rv'},execution,p.index[2],'NIFTY50_TRI')


def test_next_open_old_holdings_receive_overnight():
    x=open_session(100.,100.,-.1,.2,0.,1.,.001)
    assert x['overnight_pnl']==-10.
    assert x['intraday_pnl']==pytest.approx((190.-x['cost'])*.2)
    assert x['wealth']==pytest.approx(x['initial']+x['overnight_pnl']+x['intraday_pnl']+x['cash_pnl']-x['cost'])


def test_intraday_exit_leaves_no_overnight_equity():
    x=open_session(0.,100.,.9,.1,.001,.5,.002,exit_at_close=True)
    assert x['overnight_pnl']==0 and x['equity']==0 and x['cost']>0
    assert x['wealth']==pytest.approx(x['initial']+x['cash_pnl']+x['intraday_pnl']-x['cost'])


def test_close_execution_does_not_receive_completed_return():
    p=prices(8);p['simple_return']=[0.,0.,.5,-.1,.2,.1,0.,0.]
    s=signals(p,1.); s.loc[s.execution_date.eq(p.index[1]),'forecast_variance']=np.nan
    result=run_close(p,s,'m',Policy(cost_bps=0),start=p.index[1],end=p.index[-1])
    assert result.iloc[0].net_return==0 # +50% occurred before the first valid execution.
    assert result.iloc[0].executed_weight==pytest.approx(1.)
    assert result.iloc[1].net_return==pytest.approx(-.1)


def test_cash_act365_compounding_and_costs():
    p=prices(20);p['simple_return']=0.
    policy=Policy(annual_cash=.04,cost_bps=10)
    cash=run_close(p,pd.DataFrame(),'static',policy,start=p.index[0],end=p.index[-1],constant=0.)
    days=(p.index[-1]-p.index[0]).days
    assert cash.wealth.iloc[-1]==pytest.approx(policy.initial_capital*1.04**(days/365))
    equity=run_close(p,pd.DataFrame(),'static',replace(policy,annual_cash=0),start=p.index[0],end=p.index[-1],constant=1.,buy_hold=True)
    assert equity.cost.sum()==pytest.approx(policy.initial_capital*.001/1.001)
    assert np.prod(1+equity.net_return)*policy.initial_capital==pytest.approx(equity.wealth.iloc[-1])
    assert equity.pnl_residual.abs().max()<1e-6


def test_failure_holds_units_or_moves_to_cash():
    p=prices(10);s=signals(p,.5)
    s.loc[s.execution_date.ge(p.index[2]),'forecast_variance']=np.nan
    hold=run_close(p,s,'m',Policy(cost_bps=0),start=p.index[1],end=p.index[-1])
    cash=run_close(p,s,'m',Policy(cost_bps=0,failure='cash'),start=p.index[1],end=p.index[-1])
    assert hold.holding_forecast_failure.iloc[1:].all()
    assert hold.iloc[1:].trade.eq(0).all()
    assert cash.iloc[1:].exposure.eq(0).all()
    assert len(hold)==len(cash)==8


def test_weekly_band_and_bounds():
    p=prices(30);s=signals(p,.6)
    result=run_close(p,s,'m',Policy(frequency='weekly',band=.05),start=p.index[1],end=p.index[-1])
    assert result.exposure.between(0,1).all() and result.cash_after.ge(0).all()
    assert result.executed.sum()<=result.scheduled.sum()
    assert desired_weight(1e-10,Policy())==1.
    assert desired_weight(1.,Policy(minimum=.25))==.25
    with pytest.raises(ValueError):Policy(maximum=1.1)
    with pytest.raises(ValueError):Policy(minimum=-.1)


def test_missing_return_cannot_disappear():
    p=prices();p.loc[p.index[10],'simple_return']=np.nan
    with pytest.raises(ValueError,match='cannot skip'):
        run_close(p,pd.DataFrame(),'s',Policy(),start=p.index[0],end=p.index[-1],constant=.6)


def test_index_is_non_executable():
    instrument=Instrument('NIFTY50_TRI','INR',True,False,'gross TRI')
    instrument.require_panel('A')
    assert 'NON_EXECUTABLE' in instrument.label
    with pytest.raises(ValueError,match='Panel B'):
        instrument.require_panel('B',adjusted_ohlc_verified=True,actions_verified=True)


def test_matched_benchmarks_development_only():
    p=prices();s=signals(p,.6);policy=Policy(cost_bps=0)
    for metric in ['average_equity_exposure','realized_volatility']:
        match=match_constant(p,s,'m',policy,start=p.index[1],end=p.index[-1],metric=metric)
        assert match['weight']==pytest.approx(.6,abs=1e-7)
        assert abs(match['development_match_error'])<1e-8
    with pytest.raises(ValueError,match='before 2024'):
        match_constant(p,s,'m',policy,start=p.index[1],end='2024-12-31',metric='realized_volatility')


def test_exact_attribution_and_reproducible_resampling():
    p=prices();s=signals(p,.6);kw=dict(start=p.index[1],end=p.index[-1])
    a=run_close(p,s,'m',Policy(),**kw)
    b=run_close(p,pd.DataFrame(),'s',Policy(),constant=1.,buy_hold=True,**kw)
    parts=decompose(a,b)
    assert parts.select_dtypes('number').sum().sum()==pytest.approx(a.wealth.iloc[-1]-b.wealth.iloc[-1])
    assert paired_uncertainty(a,b,draws=100,seed=3)==paired_uncertainty(a,b,draws=100,seed=3)
    with pytest.raises(ValueError):paired_uncertainty(a.iloc[1:],b)
    np.testing.assert_allclose(holm([.01,.02,.9]),[.03,.04,.9])


def test_future_returns_do_not_change_earlier_holdings():
    p=prices();s=signals(p,.6);kw=dict(start=p.index[1],end=p.index[-1])
    before=run_close(p,s,'m',Policy(),**kw)
    p.loc[p.index[40]:,'simple_return']=.3
    after=run_close(p,s,'m',Policy(),**kw)
    pd.testing.assert_frame_equal(before.loc[:p.index[39]],after.loc[:p.index[39]])


def test_duplicate_signal_and_unsorted_path_rejected():
    p=prices();s=signals(p);s=pd.concat([s,s.iloc[:1]],ignore_index=True)
    with pytest.raises(ValueError,match='Duplicate'):
        run_close(p,s,'m',Policy(),start=p.index[1],end=p.index[-1])
    with pytest.raises(ValueError,match='chronological'):
        run_close(p.iloc[::-1],pd.DataFrame(),'s',Policy(),start=p.index[0],end=p.index[-1],constant=.5)


def test_future_training_and_failed_fit_are_ineligible():
    p=prices();s=signals(p);row=s.iloc[0].to_dict()
    with pytest.raises(ValueError,match='Training includes future'):
        validate_signal(row|{'training_end':p.index[5]},p.origin_timestamp.iloc[1],p.index[2],'NIFTY50_TRI')
    s['fit_status']='failed'
    result=run_close(p,s,'m',Policy(),start=p.index[1],end=p.index[-1])
    assert result.exposure.eq(0).all() and result.holding_forecast_failure.all()


def test_ledger_storage_roundtrip_retains_entry_separately(tmp_path):
    from volrisk.economics.experiment import write_json,write_ledger
    p=prices();path=run_close(p,pd.DataFrame(),'s',Policy(),start=p.index[0],end=p.index[-1],constant=1.,buy_hold=True)
    write_json(tmp_path/'entry.json',path.attrs['initial_action'])
    write_ledger(tmp_path/'path.parquet',path)
    restored=pd.read_parquet(tmp_path/'path.parquet').set_index('date')
    pd.testing.assert_frame_equal(path,restored,check_freq=False)
    assert (tmp_path/'entry.json').exists()


def test_expost_risk_match_is_explicitly_non_deployable():
    from volrisk.economics.metrics import expost_constant
    p=prices(start='2024-01-01');s=signals(p,.6)
    result=expost_constant(p,s,'m',Policy(cost_bps=0),start=p.index[1],end=p.index[-1],metric='realized_volatility')
    assert result['weight']==pytest.approx(.6,abs=1e-7)
    assert result['deployable'] is False
    assert result['matching_sample']=='EX_POST_EVALUATION_DIAGNOSTIC'
    assert result['status']=='matched_ex_post_not_deployable'
    assert 'development_target' not in result
