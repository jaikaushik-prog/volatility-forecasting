"""Exact P&L difference decomposition; retrospective labels are descriptive only."""
import numpy as np
import pandas as pd


def decompose(dynamic,benchmark):
    if not dynamic.index.equals(benchmark.index):
        raise ValueError('Attribution requires matched session paths')
    vd=dynamic.wealth_start; vb=benchmark.wealth_start
    # Effective beginning equity fractions include initial-entry costs correctly.
    wd=dynamic.equity_before/vd; wb=benchmark.equity_before/vb
    equity_return=dynamic.equity_return
    allocation=(wd-wb)*vd*equity_return
    wealth_scale=(vd-vb)*wb*equity_return
    cash=dynamic.cash_pnl-benchmark.cash_pnl
    costs=-(dynamic.cost-benchmark.cost)
    recovery=equity_return.lt(-.02).shift(1,fill_value=False).rolling(10,min_periods=1).max().astype(bool)
    labels=[]
    for i in range(len(dynamic)):
        if dynamic.holding_forecast_failure.iloc[i]: label='forecast_failure_affected_holding'
        elif wd.iloc[i] < wb.iloc[i] and equity_return.iloc[i] < 0:
            label='reduced_exposure_after_loss' if i>0 and equity_return.iloc[i-1]<0 else 'reduced_exposure_before_loss'
        elif wd.iloc[i] < wb.iloc[i] and equity_return.iloc[i] > 0 and recovery.iloc[i]: label='missed_recovery'
        elif wd.iloc[i] < wb.iloc[i]: label='persistent_lower_exposure_other'
        else: label='higher_or_equal_exposure'
        labels.append(label)
    out=pd.DataFrame(dict(allocation_effect=allocation,wealth_scale_effect=wealth_scale,
                          cash_pnl_difference=cash,cost_difference=costs,category=labels),index=dynamic.index)
    expected=float(dynamic.wealth.iloc[-1]-benchmark.wealth.iloc[-1])
    total=float(out.select_dtypes('number').sum().sum())
    if not np.isclose(total,expected,rtol=1e-9,atol=1e-6):
        raise ArithmeticError('Attribution does not reconcile terminal wealth')
    return out
