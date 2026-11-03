"""Event accounting in currency units. Fractional index claims are theoretical.

Cash accrues ACT/365 between session closes. At a close, existing holdings first
receive that session's return, then the pre-existing signal trades. Transaction
costs are paid from cash and target weights are defined AFTER those costs.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
import numpy as np
import pandas as pd
from .alignment import validate_grid, validate_signal


@dataclass(frozen=True)
class Policy:
    target_vol: float = .12
    cost_bps: float = 10.
    frequency: str = 'daily'
    band: float = 0.
    minimum: float = 0.
    maximum: float = 1.
    annual_cash: float = 0.
    failure: str = 'hold'
    horizon: int = 2
    initial_capital: float = 1_000_000.

    def __post_init__(self):
        numeric = [self.target_vol,self.cost_bps,self.band,self.minimum,self.maximum,self.annual_cash,self.initial_capital]
        if not np.isfinite(numeric).all():
            raise ValueError('Nonfinite policy setting')
        if not (0 <= self.minimum <= self.maximum <= 1) or self.target_vol <= 0:
            raise ValueError('Long-only unlevered exposure bounds required')
        if not (0 <= self.cost_bps < 10000) or not (0 <= self.band <= 1) or self.annual_cash <= -1 or self.initial_capital <= 0:
            raise ValueError('Invalid cost, band, cash or capital')
        if self.frequency not in ('daily','weekly') or self.failure not in ('hold','cash') or self.horizon not in (2,3):
            raise ValueError('Unregistered policy convention')


def desired_weight(variance, policy):
    if not np.isfinite(variance) or variance <= 0:
        return np.nan
    return float(np.clip(policy.target_vol / np.sqrt(252*variance), policy.minimum, policy.maximum))


def rebalance(equity, cash, target, cost_rate):
    """Solve T = w*(V-c*abs(T))-E, including entry costs at full allocation."""
    if not np.isfinite([equity,cash,target,cost_rate]).all() or equity < -1e-8 or cash < -1e-8:
        raise ValueError('Invalid holdings')
    if not 0 <= target <= 1 or not 0 <= cost_rate < 1 or equity+cash <= 0:
        raise ValueError('Invalid rebalance')
    equity, cash = max(0.,equity), max(0.,cash)
    delta = target*(equity+cash)-equity
    trade = delta/(1+target*cost_rate) if delta >= 0 else delta/(1-target*cost_rate)
    cost = abs(trade)*cost_rate
    new_equity, new_cash = equity+trade, cash-trade-cost
    if new_cash < -1e-7 or new_equity < -1e-7:
        raise ArithmeticError('Rebalance created leverage or a short position')
    return max(0.,new_equity),max(0.,new_cash),trade,cost


def open_session(equity, cash, overnight_return, intraday_return, cash_return,
                 open_target, cost_rate=0., *, exit_at_close=False):
    """Tested next-open accounting primitive; not a fabricated empirical Panel B.

Old holdings earn the overnight gap. New holdings earn only open-to-close.
The cash accrual is credited before the open (a declared interval convention).
"""
    values = [overnight_return,intraday_return,cash_return]
    if not np.isfinite(values).all() or min(values) <= -1:
        raise ValueError('Invalid executable return component')
    initial = equity+cash
    overnight_pnl, cash_pnl = equity*overnight_return, cash*cash_return
    equity, cash, trade_open, cost_open = rebalance(equity+overnight_pnl,cash+cash_pnl,open_target,cost_rate)
    intraday_pnl = equity*intraday_return
    equity += intraday_pnl
    trade_close = cost_close = 0.
    if exit_at_close:
        equity,cash,trade_close,cost_close = rebalance(equity,cash,0.,cost_rate)
    return dict(equity=equity,cash=cash,wealth=equity+cash,initial=initial,
                overnight_pnl=overnight_pnl,intraday_pnl=intraday_pnl,cash_pnl=cash_pnl,
                cost=cost_open+cost_close,turnover=abs(trade_open)+abs(trade_close))


def run_close(prices, forecasts, model, policy, *, start, end, asset='NIFTY50_TRI',
              constant=None, buy_hold=False):
    """All policies retain every P&L session; missing forecasts never delete losses.

Start is the initial execution close. Initial entry cost is included in the first
subsequent P&L observation. End is marked to market without forced liquidation.
"""
    validate_grid(prices)
    dates = prices.index[(prices.index >= pd.Timestamp(start)) & (prices.index <= pd.Timestamp(end))]
    if len(dates) < 3:
        raise ValueError('Too few sessions for economic accounting')
    if constant is not None and (not np.isfinite(constant) or not 0 <= constant <= 1):
        raise ValueError('Invalid fixed exposure')
    data = prices.loc[dates]
    r = data.simple_return.to_numpy(dtype=float)
    if not np.isfinite(r[1:]).all() or (r[1:] <= -1).any():
        raise ValueError('Execution path contains invalid or missing returns; cannot skip sessions')
    selected = forecasts.loc[(forecasts.model == model) & (forecasts.horizon == policy.horizon)] if constant is None else pd.DataFrame()
    if not selected.empty and selected.execution_date.duplicated().any():
        raise ValueError('Duplicate signal for execution date')
    signals = {pd.Timestamp(x['execution_date']):x for x in selected.to_dict('records')}
    equity, cash = 0., policy.initial_capital
    held_failure = False
    weeks = [(d.isocalendar().year,d.isocalendar().week) for d in dates]

    def action(j, equity, cash):
        scheduled = j == 0 or (not buy_hold and (policy.frequency == 'daily' or weeks[j] != weeks[j-1]))
        result = dict(scheduled=scheduled,signal_failed=False,failure_reason='',desired_weight=np.nan,
                      forecast_variance=np.nan,signal_origin=pd.NaT,issued_at=pd.NaT,trade=0.,cost=0.,executed=False)
        if not scheduled or j == len(dates)-1:
            return equity,cash,result
        if constant is not None:
            weight = constant
        else:
            signal = signals.get(dates[j])
            if signal is not None:
                validate_signal(signal, data.origin_timestamp.iloc[j], dates[j+1], asset)
                result.update(signal_origin=signal['origin_date'],issued_at=signal['issued_at'],
                              forecast_variance=signal['forecast_variance'])
            variance = signal['forecast_variance'] if signal is not None else np.nan
            if signal is not None and signal.get('fit_status','ok') not in ('ok','warning'):
                variance = np.nan
            weight = desired_weight(variance,policy)
            if not np.isfinite(weight):
                result.update(signal_failed=True, failure_reason=signal.get('failure_reason','missing_forecast') if signal else 'missing_forecast')
                if policy.failure == 'hold':
                    return equity,cash,result  # Hold units, not the last percentage target.
                weight = policy.minimum
        result['desired_weight'] = weight
        before = equity/(equity+cash)
        if j != 0 and abs(weight-before) < policy.band:
            return equity,cash,result
        equity,cash,trade,cost = rebalance(equity,cash,weight,policy.cost_bps/10000)
        result.update(trade=trade,cost=cost,executed=bool(abs(trade)>1e-10))
        return equity,cash,result

    equity,cash,initial_action = action(0,equity,cash)
    held_failure = initial_action['signal_failed']
    previous_wealth = policy.initial_capital
    records = []
    for j in range(1,len(dates)):
        equity_before, cash_before = equity,cash
        actual_weight = equity/(equity+cash)
        days = (dates[j]-dates[j-1]).days
        cash_return = np.expm1(np.log1p(policy.annual_cash)*days/365.)
        equity_pnl, cash_pnl = equity*r[j],cash*cash_return
        equity,cash = equity+equity_pnl,cash+cash_pnl
        before_trade = equity+cash
        previous_failure = held_failure
        equity,cash,event = action(j,equity,cash)
        if event['scheduled'] and j != len(dates)-1:
            held_failure = event['signal_failed']
        cost = event['cost'] + (initial_action['cost'] if j == 1 else 0.)
        trade_abs = abs(event['trade']) + (abs(initial_action['trade']) if j == 1 else 0.)
        wealth = equity+cash
        residual = wealth-(previous_wealth+equity_pnl+cash_pnl-cost)
        if abs(residual) > 1e-6*max(1.,previous_wealth/1e6):
            raise ArithmeticError('P&L identity failed')
        records.append(dict(date=dates[j],period_start=dates[j-1],wealth=wealth,wealth_start=previous_wealth,
            net_return=wealth/previous_wealth-1,equity_return=r[j],cash_return=cash_return,
            equity_before=equity_before,cash_before=cash_before,equity_pnl=equity_pnl,cash_pnl=cash_pnl,
            equity_after=equity,cash_after=cash,exposure=actual_weight,executed_weight=equity/wealth,
            cost=cost,turnover_notional=trade_abs,turnover_fraction=trade_abs/previous_wealth,
            cost_fraction=cost/previous_wealth,pnl_residual=residual,holding_forecast_failure=previous_failure,
            initial_entry_cost=initial_action['cost'] if j==1 else 0.,
            initial_signal_failed=initial_action['signal_failed'] if j==1 else False,
            initial_exposure=(policy.initial_capital-initial_action['cost']-cash_before)/(policy.initial_capital-initial_action['cost']) if j==1 else np.nan,
            **{k:v for k,v in event.items() if k not in ('cost',)},
            pretrade_wealth=before_trade,asset=asset,instrument_status='NON_EXECUTABLE_THEORETICAL_TOTAL_RETURN_INDEX'))
        previous_wealth = wealth
    result = pd.DataFrame(records).set_index('date')
    result.attrs['initial_action'] = initial_action
    return result


def gross_policy(policy):
    return replace(policy,cost_bps=0.)
