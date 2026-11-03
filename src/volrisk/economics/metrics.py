"""Economic metrics and development-only fairness calibration."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from .accounting import run_close


def drawdown(values, initial):
    values = np.asarray(values,dtype=float)
    peaks = np.maximum.accumulate(np.r_[initial,values])[1:]
    return values/peaks-1


def summarize(ledger, initial):
    r = ledger.net_return.to_numpy()
    excess = r-ledger.cash_return.to_numpy()
    sd = float(np.std(r,ddof=1))
    excess_sd = float(np.std(excess,ddof=1))
    dd = drawdown(ledger.wealth,initial)
    duration = maximum_duration = 0
    for value in dd:
        duration = duration+1 if value < -1e-12 else 0
        maximum_duration = max(maximum_duration,duration)
    n = len(r)
    days = (ledger.index[-1]-pd.Timestamp(ledger.period_start.iloc[0])).days
    cumulative = float(ledger.wealth.iloc[-1]/initial-1)
    worst = lambda k: float(np.expm1(pd.Series(np.log1p(r)).rolling(k).sum()).min()) if n>=k else np.nan
    es_n = max(1,int(np.ceil(.05*n)))
    # Retrospective recovery label, never a feature/decision rule.
    shock = ledger.equity_return.lt(-.02)
    recovery = shock.shift(1,fill_value=False).rolling(10,min_periods=1).max().astype(bool) & ledger.equity_return.gt(0)
    rebound_den = float(ledger.loc[recovery,'equity_return'].sum())
    rebound_num = float((ledger.loc[recovery,'equity_return']*ledger.loc[recovery,'exposure']).sum())
    return dict(observations=n,net_cumulative_return=cumulative,
        cagr=float(np.expm1(np.log1p(cumulative)*365.25/days)) if days>=180 else np.nan,
        net_sharpe=float(excess.mean()/excess_sd*np.sqrt(252)) if excess_sd>0 else np.nan,
        realized_volatility=sd*np.sqrt(252),maximum_drawdown=float(dd.min()),
        max_drawdown_duration_sessions=maximum_duration,drawdown_unrecovered=bool(dd[-1]<-1e-12),
        worst_5_session_return=worst(5),worst_20_session_return=worst(20),
        expected_shortfall_95=float(np.sort(r)[:es_n].mean()),average_equity_exposure=float(ledger.exposure.mean()),
        annualized_one_way_turnover=float(ledger.turnover_fraction.sum()*252/n),
        costs_paid_fraction_initial=float(ledger.cost.sum()/initial),cash_pnl_fraction_initial=float(ledger.cash_pnl.sum()/initial),
        cash_drag_arithmetic_vs_equity=float(((1-ledger.exposure)*(ledger.equity_return-ledger.cash_return)).sum()),
        rebound_participation=rebound_num/rebound_den if rebound_den else np.nan,
        rebound_sessions=int(recovery.sum()),holding_failure_sessions=int(ledger.holding_forecast_failure.sum()),
        scheduled_signal_failures=int(ledger.signal_failed.sum()+ledger.initial_signal_failed.sum()),
        cap_binding_fraction=float(ledger.exposure.ge(1-1e-10).mean()))


def match_constant(prices, forecasts, model, policy, *, start, end, metric, asset='NIFTY50_TRI'):
    """Only development observations may select a deployable constant allocation."""
    if pd.Timestamp(end) >= pd.Timestamp('2024-01-01'):
        raise ValueError('A deployable matched benchmark must be selected before 2024')
    return _match_constant(prices,forecasts,model,policy,start=start,end=end,metric=metric,asset=asset,expost=False)


def expost_constant(prices,forecasts,model,policy,*,start,end,metric,asset='NIFTY50_TRI'):
    """Evaluation-fitted diagnostic ONLY; never a deployable benchmark or formal test."""
    result=_match_constant(prices,forecasts,model,policy,start=start,end=end,metric=metric,asset=asset,expost=True)
    for suffix in ('target','match_error','observations'):
        result['evaluation_'+suffix]=result.pop('development_'+suffix)
    if result['status']=='matched_development_only':
        result['status']='matched_ex_post_not_deployable'
    return result


def _match_constant(prices,forecasts,model,policy,*,start,end,metric,asset,expost):
    if metric not in ('average_equity_exposure','realized_volatility'):
        raise ValueError('Unknown matching criterion')
    dynamic = run_close(prices,forecasts,model,policy,start=start,end=end,asset=asset)
    target = summarize(dynamic,policy.initial_capital)[metric]
    def objective(weight):
        path = run_close(prices,forecasts,model,policy,start=start,end=end,asset=asset,constant=weight)
        return summarize(path,policy.initial_capital)[metric]-target
    lo,hi = objective(0.),objective(1.)
    if lo*hi > 0:
        weight,status = (0. if abs(lo)<abs(hi) else 1.),'unattainable_long_only'
    elif abs(lo)<1e-12:
        weight,status=0.,'matched_development_only'
    elif abs(hi)<1e-12:
        weight,status=1.,'matched_development_only'
    else:
        weight,status=float(brentq(objective,0.,1.,xtol=1e-9)),'matched_development_only'
    return dict(model=model,criterion=metric,weight=weight,development_target=target,
                development_match_error=objective(weight),status=status,selected_through=str(pd.Timestamp(end).date()),
                development_observations=len(dynamic),deployable=not expost,
                matching_sample='EX_POST_EVALUATION_DIAGNOSTIC' if expost else 'DEVELOPMENT_ONLY')


def stationary_indices(n, draws, block, seed):
    rng = np.random.default_rng(seed)
    result = np.empty((draws,n),dtype=int)
    result[:,0]=rng.integers(n,size=draws)
    for j in range(1,n):
        restart = rng.random(draws)<1./block
        result[:,j]=np.where(restart,rng.integers(n,size=draws),(result[:,j-1]+1)%n)
    return result


def paired_uncertainty(left,right,*,draws=2000,block=10,seed=0):
    """Paired stationary bootstrap on complete native-session P&L paths.

Conditional on saved signals; does not re-estimate models or account for research
selection. Calendar weekends are not missing trading observations. Reject any
misaligned dates instead of concatenating disjoint subsets.
"""
    if not left.index.equals(right.index) or len(left)<30:
        raise ValueError('Inference requires identical, sufficiently long session paths')
    a=(left.net_return-left.cash_return).to_numpy()
    b=(right.net_return-right.cash_return).to_numpy()
    indices=stationary_indices(len(a),draws,block,seed)
    sharpe=lambda x,axis: np.mean(x,axis=axis)/np.std(x,axis=axis,ddof=1)*np.sqrt(252)
    if np.std(a,ddof=1)==0 or np.std(b,ddof=1)==0:
        return dict(sharpe_difference=np.nan,p_value=np.nan,ci_low=np.nan,ci_high=np.nan,status='degenerate_variance')
    point=float(sharpe(a,0)-sharpe(b,0))
    aa,bb=a[indices],b[indices]
    nondegenerate=(aa.std(axis=1,ddof=1)>0)&(bb.std(axis=1,ddof=1)>0)
    values=sharpe(aa[nondegenerate],1)-sharpe(bb[nondegenerate],1)
    p=(1+int((np.abs(values-point)>=abs(point)).sum()))/(1+len(values))
    low,high=np.quantile(values,[.025,.975])
    mean_values=(aa-bb).mean(axis=1)*252
    ml,mh=np.quantile(mean_values,[.025,.975])
    return dict(sharpe_difference=point,p_value=float(p),ci_low=float(low),ci_high=float(high),
                annualized_mean_excess_difference=float((a-b).mean()*252),mean_ci_low=float(ml),mean_ci_high=float(mh),
                draws=draws,block_length=block,status='EXPLORATORY_CONDITIONAL_PATH_BOOTSTRAP')


def holm(values):
    values=np.asarray(values,float)
    # Undefined tests remain in the registered multiplicity family.
    clean=np.where(np.isfinite(values),values,1.)
    order=np.argsort(clean)
    out=np.empty(len(clean))
    out[order]=np.minimum(1.,np.maximum.accumulate(clean[order]*(len(clean)-np.arange(len(clean)))))
    out[~np.isfinite(values)]=np.nan
    return out


def forecast_scores(forecasts,models,start,end,horizon=2):
    frame=forecasts.loc[forecasts.horizon.eq(horizon)&forecasts.target_date.between(pd.Timestamp(start),pd.Timestamp(end))].copy()
    finite=np.isfinite(frame.forecast_variance)&frame.forecast_variance.gt(0)&np.isfinite(frame.observed_squared_log_return)
    good=frame.loc[finite]
    counts=good.groupby('target_date').model.nunique()
    common=counts.index[counts.eq(len(models))]
    rows=[]
    for model in models:
        all_rows=frame.loc[frame.model.eq(model)]
        sample=good.loc[good.model.eq(model)&good.target_date.isin(common)]
        h=sample.forecast_variance.to_numpy(); y=sample.observed_squared_log_return.to_numpy()
        rows.append(dict(model=model,observations=len(sample),qlike=float(np.mean(np.log(h)+y/h)) if len(h) else np.nan,
            calibration=float(y.mean()/h.mean()) if len(h) else np.nan,
            failure_rate=float((~np.isfinite(all_rows.forecast_variance)).mean()),runtime_seconds=float(all_rows.runtime_seconds.sum())))
    result=pd.DataFrame(rows)
    result['qlike_rank']=result.qlike.rank(method='min')
    return result,good.loc[good.target_date.isin(common)]
