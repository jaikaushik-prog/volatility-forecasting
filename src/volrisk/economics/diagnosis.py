"""Stage 6 forensic diagnosis of saved Stage 5 economic paths.

Read-only: every function consumes archived ledgers, forecasts and tables from a
completed Stage 5 run and writes only new Stage 6 artifacts. No new allocation
rule is simulated, no model is refitted, and no observation after the registered
2024-12-31 cutoff is read. All labels are retrospective accounting descriptions,
not evidence of foreknowledge.
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
from volrisk.data.storage import sha256

CUTOFF = pd.Timestamp('2024-12-31')
PRIMARY_MODELS = ['ewma','garch','har_daily','log_har_daily','log_har_vix_daily']
PRIMARY_SUFFIX = '_v12_c10_daily_b0'
SHOCK_RETURN = -.02
RECOVERY_SESSIONS = 10
TARGET_VOL = .12


# ---------------------------------------------------------------- loading ---
def locate_run(root):
    root = Path(root)
    pointer = json.loads((root/'reports/latest_stage5.json').read_text())
    run = root/Path(pointer['run'])
    manifest_file = run/'manifest.json'
    if sha256(manifest_file) != pointer['manifest_sha256']:
        raise ValueError('Stage 5 manifest hash does not match its pointer')
    return run, json.loads(manifest_file.read_text())


def verify_outputs(run, manifest):
    """Confirm the Stage 5 archive is byte-identical to its manifest (read-only guarantee)."""
    changed = [rel for rel,digest in manifest['output_hashes'].items()
               if not (run/rel).exists() or sha256(run/rel) != digest]
    if changed:
        raise ValueError(f'Stage 5 artifacts changed: {changed[:5]}')
    return len(manifest['output_hashes'])


def assert_within_cutoff(frame, column=None, cutoff=CUTOFF):
    dates = pd.DatetimeIndex(frame.index if column is None else frame[column].dropna())
    if len(dates) and dates.max() > cutoff:
        raise ValueError(f'Observation after {cutoff.date()} encountered')
    return True


def read_ledger(run, name):
    frame = pd.read_parquet(Path(run)/'ledgers'/f'{name}.parquet').set_index('date')
    assert_within_cutoff(frame)
    return frame


def load_run(root):
    run, manifest = locate_run(root)
    verified = verify_outputs(run, manifest)
    inputs = pd.read_parquet(run/'bounded_inputs.parquet').set_index('date')
    assert_within_cutoff(inputs)
    forecasts = pd.read_parquet(run/'forecasts.parquet')
    assert_within_cutoff(forecasts,'target_date')
    economic = pd.read_csv(run/'economic_model_comparison.csv')
    ledgers = {n:read_ledger(run,n) for n in ['buy_hold','constant_60']}
    for m in PRIMARY_MODELS:
        ledgers[m+PRIMARY_SUFFIX] = read_ledger(run,m+PRIMARY_SUFFIX)
        ledgers[m+PRIMARY_SUFFIX+'_gross'] = read_ledger(run,m+PRIMARY_SUFFIX+'_gross')
        ledgers[f'{m}_delay_one_session'] = read_ledger(run,f'{m}_delay_one_session')
        for kind in ('matched_exposure','matched_risk','expost_exposure','expost_risk'):
            ledgers[f'{kind}_{m}'] = read_ledger(run,f'{kind}_{m}')
    return dict(run=run,manifest=manifest,verified_files=verified,inputs=inputs,forecasts=forecasts,
                economic=economic,ledgers=ledgers,
                pnl_attribution=pd.read_csv(run/'pnl_attribution.csv'),
                matched=pd.read_csv(run/'matched_benchmarks.csv'),
                expost=pd.read_csv(run/'expost_matching.csv'),
                forecast_metrics=pd.read_csv(run/'forecast_metrics.csv'),
                uncertainty=pd.read_csv(run/'economic_uncertainty.csv'))


# ------------------------------------------------------- decomposition ---
def recovery_window(equity_return, shock=SHOCK_RETURN, sessions=RECOVERY_SESSIONS):
    """Sessions 1..`sessions` after a day whose return was below `shock`."""
    return equity_return.lt(shock).shift(1,fill_value=False).rolling(sessions,min_periods=1).max().astype(bool)


def terminal_decomposition(dynamic, benchmark, initial):
    """Exact split of (dynamic - benchmark) terminal wealth into eight mechanisms.

    Allocation effects use the dynamic path's own beginning wealth, so the sum of
    all components equals the terminal wealth difference to numerical precision.
    Categories are retrospective labels of saved decisions, not causal claims.
    """
    if not dynamic.index.equals(benchmark.index):
        raise ValueError('Decomposition requires identical session paths')
    r = dynamic.equity_return
    wd = dynamic.equity_before/dynamic.wealth_start
    wb = benchmark.equity_before/benchmark.wealth_start
    allocation = (wd-wb)*dynamic.wealth_start*r/initial
    failure = dynamic.holding_forecast_failure.astype(bool)
    rebound = recovery_window(r)
    prev_negative = r.shift(1,fill_value=0.).lt(0)
    parts = dict(
        avoided_loss_before=allocation[(r<0)&~failure&~prev_negative].sum(),
        avoided_loss_after=allocation[(r<0)&~failure&prev_negative].sum(),
        missed_rebound=allocation[(r>0)&~failure&rebound].sum(),
        missed_positive_other=allocation[(r>0)&~failure&~rebound].sum(),
        forecast_failure_holding=allocation[failure].sum(),
        wealth_scale=((dynamic.wealth_start-benchmark.wealth_start)*wb*r).sum()/initial,
        cash_pnl=(dynamic.cash_pnl-benchmark.cash_pnl).sum()/initial,
        transaction_cost=-(dynamic.cost-benchmark.cost).sum()/initial)
    parts = {k:float(v) for k,v in parts.items()}
    total = sum(parts.values())
    expected = float((dynamic.wealth.iloc[-1]-benchmark.wealth.iloc[-1])/initial)
    if not np.isclose(total,expected,rtol=1e-9,atol=1e-10):
        raise ArithmeticError('Stage 6 decomposition does not reconcile to terminal wealth')
    parts.update(avoided_loss_total=parts['avoided_loss_before']+parts['avoided_loss_after'],
                 missed_upside_total=parts['missed_rebound']+parts['missed_positive_other'],
                 allocation_total=float(allocation.sum()),components_sum=total,
                 terminal_return_difference=expected,reconciliation_error=total-expected)
    return parts


def spell_lengths(flags):
    out, run = [], 0
    for value in np.asarray(flags,dtype=bool):
        if value: run += 1
        elif run: out.append(run); run = 0
    if run: out.append(run)
    return out


def cash_exposure(ledger):
    cash = 1-ledger.exposure
    r = ledger.equity_return; c = ledger.cash_return
    below = ledger.exposure.lt(1-1e-10)
    spells = spell_lengths(below)
    return dict(average_cash_fraction=float(cash.mean()),sessions_with_cash=int(below.sum()),
                sessions_cash_above_10pct=int(cash.gt(.1).sum()),sessions_cash_above_50pct=int(cash.gt(.5).sum()),
                longest_below_cap_spell=int(max(spells) if spells else 0),below_cap_spells=len(spells),
                cash_drag_arithmetic=float((cash*(r-c)).sum()),
                cash_drag_on_positive_days=float((cash*r)[r>0].sum()),
                cash_benefit_on_negative_days=float(-(cash*r)[r<0].sum()),
                cap_binding_fraction=float(ledger.exposure.ge(1-1e-10).mean()))


# ------------------------------------------------------------ forecasts ---
def forecast_bias(ledger, log_return, target=TARGET_VOL):
    """Row t carries the forecast for the return ending t+1; compare with that return."""
    h = ledger.forecast_variance
    y = (log_return.reindex(ledger.index).shift(-1))**2
    frame = pd.DataFrame(dict(h=h,y=y)).dropna()
    frame = frame[frame.h.gt(0)]
    def stats(g):
        fv = np.sqrt(252*g.h)
        return pd.Series(dict(sessions=len(g),mean_forecast_vol=float(fv.mean()),median_forecast_vol=float(fv.median()),
            realized_vol_of_targets=float(np.sqrt(252*g.y.mean())),calibration_ratio=float(g.y.mean()/g.h.mean()),
            fraction_forecast_above_target=float(fv.gt(target).mean()),fraction_forecast_above_15pct=float(fv.gt(.15).mean()),
            fraction_forecast_above_20pct=float(fv.gt(.20).mean())))
    quarters = pd.DataFrame({k:stats(g) for k,g in frame.groupby(frame.index.to_period('Q').astype(str))}).T
    quarters['overall'] = np.nan
    quarters = pd.concat([quarters.drop(columns='overall'),stats(frame).to_frame('overall').T])
    quarters.index.name = 'period'
    return quarters


def shock_event_study(ledger, initial, shock=SHOCK_RETURN, horizon=RECOVERY_SESSIONS, pre=3, post=15, target=TARGET_VOL,
                      persistence_window=120):
    """Forecast and exposure paths around each shock day.

    Row i is the shock session. The first forecast that can observe the shock has
    origin i, is stored on row i+1 and governs the exposure of row i+2.
    """
    r = ledger.equity_return
    w = ledger.equity_before/ledger.wealth_start
    fvol = np.sqrt(252*ledger.forecast_variance)
    allocation = (w-1)*ledger.wealth_start*r/initial
    rows, paths = [], []
    n = len(ledger)
    for i in np.flatnonzero(r.lt(shock).to_numpy()):
        after = fvol.iloc[i+1:i+1+post]
        elevated = 0
        for value in fvol.iloc[i+1:i+1+persistence_window]:
            if np.isfinite(value) and value > target: elevated += 1
            else: break
        exposures = ledger.exposure.iloc[i+2:i+2+horizon]
        window = slice(i+1,i+1+horizon)
        pos = r.iloc[window].gt(0)
        rows.append(dict(shock_date=ledger.index[i].date(),shock_return=float(r.iloc[i]),
            exposure_on_shock_day=float(ledger.exposure.iloc[i]),
            forecast_vol_before_shock=float(fvol.iloc[i]),
            forecast_vol_first_after=float(fvol.iloc[i+1]) if i+1 < n else np.nan,
            peak_forecast_vol_15=float(after.max()) if len(after) else np.nan,
            consecutive_sessions_forecast_above_target=int(elevated),
            first_reactive_exposure=float(ledger.exposure.iloc[i+2]) if i+2 < n else np.nan,
            minimum_exposure_10=float(exposures.min()) if len(exposures) else np.nan,
            sessions_below_95pct_next_60=int(ledger.exposure.iloc[i+2:i+2+60].lt(.95).sum()),
            asset_return_next_10=float((1+r.iloc[window]).prod()-1),
            positive_sessions_next_10=int(pos.sum()),
            allocation_effect_next_10=float(allocation.iloc[window].sum()),
            missed_rebound_next_10=float(allocation.iloc[window][pos].sum())))
        lo, hi = max(0,i-pre), min(n,i+post+1)
        seg = pd.DataFrame(dict(offset=np.arange(lo-i,hi-i),forecast_vol=fvol.iloc[lo:hi].to_numpy(),
                                exposure=ledger.exposure.iloc[lo:hi].to_numpy(),equity_return=r.iloc[lo:hi].to_numpy()))
        seg.insert(0,'shock_date',ledger.index[i].date()); paths.append(seg)
    return pd.DataFrame(rows), (pd.concat(paths,ignore_index=True) if paths else pd.DataFrame())


def event_concentration(ledger, initial, sessions=60, shock=SHOCK_RETURN):
    """Share of the full-year allocation effect arising within `sessions` after the largest shock.

    Descriptive fragility measure: a large share means one episode dominates the result.
    Measured against 100% equity (not the buy-and-hold ledger, which differs only by its entry cost).
    """
    r = ledger.equity_return; w = ledger.equity_before/ledger.wealth_start
    allocation = (w-1)*ledger.wealth_start*r/initial
    i = int(np.argmin(r.to_numpy()))
    if r.iloc[i] >= shock:
        return dict(largest_shock_date=None,largest_shock_return=float(r.iloc[i]),window_sessions=0,
                    window_allocation_effect=0.,full_year_allocation_effect=float(allocation.sum()),
                    window_share=np.nan,allocation_effect_outside_window=float(allocation.sum()))
    window = allocation.iloc[i+1:i+1+sessions]
    total = float(allocation.sum())
    return dict(largest_shock_date=ledger.index[i].date(),largest_shock_return=float(r.iloc[i]),window_sessions=len(window),
                window_allocation_effect=float(window.sum()),full_year_allocation_effect=total,
                window_share=float(window.sum()/total) if total else np.nan,
                allocation_effect_outside_window=total-float(window.sum()),
                asset_return_in_window=float((1+r.iloc[i+1:i+1+sessions]).prod()-1),
                mean_exposure_in_window=float(ledger.exposure.iloc[i+1:i+1+sessions].mean()))


def exposure_spells(ledger, initial, trailing=20):
    r = ledger.equity_return; w = ledger.equity_before/ledger.wealth_start
    allocation = (w-1)*ledger.wealth_start*r/initial
    below = ledger.exposure.lt(1-1e-10).to_numpy()
    rows, start = [], None
    for i,flag in enumerate(np.r_[below,False]):
        if flag and start is None: start = i
        if not flag and start is not None:
            rows.append(dict(start=ledger.index[start].date(),end=ledger.index[i-1].date(),length=i-start,
                mean_exposure=float(ledger.exposure.iloc[start:i].mean()),minimum_exposure=float(ledger.exposure.iloc[start:i].min()),
                trailing_20_asset_return=float((1+r.iloc[max(0,start-trailing):start]).prod()-1),
                asset_return_in_spell=float((1+r.iloc[start:i]).prod()-1),
                allocation_effect=float(allocation.iloc[start:i].sum())))
            start = None
    return pd.DataFrame(rows)


def cap_and_volatility(ledger, target=TARGET_VOL):
    r = ledger.equity_return; p = ledger.net_return; capped = ledger.exposure.ge(1-1e-10)
    n = len(p); annual = lambda x: float(np.sqrt(252*np.mean(np.square(x)))) if len(x) else np.nan
    total_var = float(np.sum(np.square(p)))
    return dict(cap_binding_fraction=float(capped.mean()),portfolio_volatility=float(p.std(ddof=1)*np.sqrt(252)),
        asset_volatility=float(r.std(ddof=1)*np.sqrt(252)),
        asset_rms_vol_on_capped_days=annual(r[capped]),portfolio_rms_vol_on_uncapped_days=annual(p[~capped]),
        asset_rms_vol_on_uncapped_days=annual(r[~capped]),
        variance_share_from_capped_days=float(np.sum(np.square(p[capped]))/total_var) if total_var else np.nan,
        excess_variance_capped_vs_target=float(np.sum(np.square(r[capped]))/n*252-target**2*capped.mean()),
        excess_variance_uncapped_vs_target=float(np.sum(np.square(p[~capped]))/n*252-target**2*(~capped).mean()),
        target_variance=target**2)


def sharpe(ledger):
    excess = ledger.net_return-ledger.cash_return
    return float(excess.mean()/excess.std(ddof=1)*np.sqrt(252))


def timing_statistics(dynamic, constant_same_exposure, gross=None):
    r = dynamic.equity_return; w = dynamic.exposure
    out = dict(corr_exposure_return=float(np.corrcoef(w,r)[0,1]),corr_exposure_squared_return=float(np.corrcoef(w,r**2)[0,1]),
        corr_exposure_abs_return=float(np.corrcoef(w,r.abs())[0,1]),
        mean_exposure_on_positive_days=float(w[r>0].mean()),mean_exposure_on_negative_days=float(w[r<0].mean()),
        net_sharpe=sharpe(dynamic),constant_same_exposure_sharpe=sharpe(constant_same_exposure),
        timing_sharpe_vs_same_exposure_constant=sharpe(dynamic)-sharpe(constant_same_exposure))
    if gross is not None:
        out['gross_sharpe'] = sharpe(gross); out['cost_sharpe_effect'] = sharpe(dynamic)-sharpe(gross)
        out['gross_timing_sharpe'] = sharpe(gross)-sharpe(constant_same_exposure)
    return out


def delay_comparison(base, delayed, initial):
    r = base.equity_return
    rebound = recovery_window(r)&r.gt(0)
    part = lambda l: float((l.exposure[rebound]*r[rebound]).sum()/r[rebound].sum()) if r[rebound].sum() else np.nan
    return dict(base_terminal_return=float(base.wealth.iloc[-1]/initial-1),delayed_terminal_return=float(delayed.wealth.iloc[-1]/initial-1),
        delay_gain=float((delayed.wealth.iloc[-1]-base.wealth.iloc[-1])/initial),
        base_mean_exposure=float(base.exposure.mean()),delayed_mean_exposure=float(delayed.exposure.mean()),
        exposure_path_correlation=float(np.corrcoef(base.exposure,delayed.exposure)[0,1]),
        lagged_base_vs_delayed_correlation=float(np.corrcoef(base.exposure.shift(1).iloc[1:],delayed.exposure.iloc[1:])[0,1]),
        base_rebound_participation=part(base),delayed_rebound_participation=part(delayed),
        asset_lag1_autocorrelation=float(r.autocorr(1)))


def exposure_buckets(ledger, initial, edges=(0,.5,.7,.8,.9,.95,1-1e-10,1.01)):
    r = ledger.equity_return; w = ledger.equity_before/ledger.wealth_start
    allocation = (w-1)*ledger.wealth_start*r/initial
    labels = ['<=0.50','0.50-0.70','0.70-0.80','0.80-0.90','0.90-0.95','0.95-<1.00','1.00 (cap)']
    bucket = pd.cut(ledger.exposure,list(edges),labels=labels,right=True,include_lowest=True)
    frame = pd.DataFrame(dict(allocation_effect=allocation,sessions=1,bucket=bucket))
    out = frame.groupby('bucket',observed=False).agg(sessions=('sessions','sum'),allocation_effect=('allocation_effect','sum')).reset_index()
    total = float(allocation.sum())
    out['share_of_allocation_effect'] = out.allocation_effect/total if total else np.nan
    return out


def constant_sharpe_invariance(ledgers):
    rows = []
    for name,l in ledgers.items():
        if not name.startswith(('buy_hold','constant_','matched_','expost_')) or name.endswith('_gross'): continue
        rows.append(dict(strategy=name,average_equity_exposure=float(l.exposure.mean()),net_sharpe=sharpe(l),
                         realized_volatility=float(l.net_return.std(ddof=1)*np.sqrt(252)),deployable=not name.startswith('expost_')))
    return pd.DataFrame(rows)


def registered_variants(economic, models=PRIMARY_MODELS):
    """Already-saved Stage 5 factorial paths at the primary target and cost; descriptive, not selection."""
    keep = economic[economic.model.isin(models)&economic.target_vol.eq(.12)&economic.cost_bps.eq(10.)&economic.kind.eq('factorial_sensitivity')]
    cols = ['strategy','model','frequency','band','net_cumulative_return','net_sharpe','realized_volatility','maximum_drawdown',
            'average_equity_exposure','annualized_one_way_turnover','transaction_cost_drag','rebound_participation','cap_binding_fraction']
    return keep[cols].sort_values(['model','frequency','band']).reset_index(drop=True)


def run_diagnosis(root):
    data = load_run(root)
    L = data['ledgers']; capital = float(data['economic'].initial_capital.iloc[0])
    bh = L['buy_hold']; log_return = data['inputs'].log_return
    tables = {}
    decomposition, cash, bias, events, paths, spells, caps, timing, delays, buckets, concentration = [],[],[],[],[],[],[],[],[],[],[]
    saved = data['pnl_attribution'].set_index(['model','benchmark'])
    for m in PRIMARY_MODELS:
        d = L[m+PRIMARY_SUFFIX]
        parts = terminal_decomposition(d,bh,capital)
        parts['stage5_saved_terminal_difference'] = float(saved.loc[(m,'buy_hold'),'terminal_return_difference'])
        parts['matches_stage5'] = bool(np.isclose(parts['terminal_return_difference'],parts['stage5_saved_terminal_difference'],atol=1e-9))
        decomposition.append(dict(model=m,**parts))
        cash.append(dict(model=m,**cash_exposure(d)))
        b = forecast_bias(d,log_return).reset_index(); b.insert(0,'model',m); bias.append(b)
        e,p = shock_event_study(d,capital); e.insert(0,'model',m); p.insert(0,'model',m); events.append(e); paths.append(p)
        s = exposure_spells(d,capital); s.insert(0,'model',m); spells.append(s)
        caps.append(dict(model=m,**cap_and_volatility(d)))
        timing.append(dict(model=m,**timing_statistics(d,L[f'expost_exposure_{m}'],L[m+PRIMARY_SUFFIX+'_gross'])))
        delays.append(dict(model=m,**delay_comparison(d,L[f'{m}_delay_one_session'],capital)))
        k = exposure_buckets(d,capital); k.insert(0,'model',m); buckets.append(k)
        concentration.append(dict(model=m,**event_concentration(d,capital)))
    tables['terminal_decomposition'] = pd.DataFrame(decomposition)
    tables['event_concentration'] = pd.DataFrame(concentration)
    tables['cash_exposure'] = pd.DataFrame(cash)
    tables['forecast_bias'] = pd.concat(bias,ignore_index=True)
    tables['shock_event_study'] = pd.concat(events,ignore_index=True)
    tables['shock_event_paths'] = pd.concat(paths,ignore_index=True)
    tables['exposure_spells'] = pd.concat(spells,ignore_index=True)
    tables['cap_and_volatility'] = pd.DataFrame(caps)
    tables['timing_statistics'] = pd.DataFrame(timing)
    tables['delay_comparison'] = pd.DataFrame(delays)
    tables['h1_exposure_buckets'] = pd.concat(buckets,ignore_index=True)
    tables['constant_benchmarks'] = constant_sharpe_invariance(L)
    tables['h3_registered_frequency_variants'] = registered_variants(data['economic'])
    fm = data['forecast_metrics'].set_index('model'); ec = data['economic'].set_index('strategy')
    ts = tables['timing_statistics'].set_index('model')
    tables['complexity'] = pd.DataFrame([dict(model=m,qlike=fm.loc[m,'qlike'],qlike_rank=int(fm.loc[m,'qlike_rank']),calibration=fm.loc[m,'calibration'],
        failure_rate=fm.loc[m,'failure_rate'],average_equity_exposure=ec.loc[m+PRIMARY_SUFFIX,'average_equity_exposure'],
        net_sharpe=ec.loc[m+PRIMARY_SUFFIX,'net_sharpe'],gross_sharpe=ec.loc[m+PRIMARY_SUFFIX,'gross_sharpe'],
        timing_sharpe_vs_same_exposure_constant=ts.loc[m,'timing_sharpe_vs_same_exposure_constant'],
        transaction_cost_drag=ec.loc[m+PRIMARY_SUFFIX,'transaction_cost_drag'],annualized_one_way_turnover=ec.loc[m+PRIMARY_SUFFIX,'annualized_one_way_turnover'])
        for m in PRIMARY_MODELS])
    r = bh.equity_return
    tables['asset_context'] = pd.DataFrame([dict(period=str(k),sessions=len(g),asset_return=float((1+g).prod()-1),asset_volatility=float(g.std(ddof=1)*np.sqrt(252)),
        shock_days=int(g.lt(SHOCK_RETURN).sum()),lag1_autocorrelation=float(g.autocorr(1)))
        for k,g in list(r.groupby(r.index.to_period('Q')))+[('2024',r)]])
    tables['quarterly_dynamic'] = pd.DataFrame([dict(model=m,quarter=str(k),strategy_return=float((1+g.net_return).prod()-1),
        asset_return=float((1+g.equity_return).prod()-1),mean_exposure=float(g.exposure.mean()),
        allocation_effect=float(((g.equity_before/g.wealth_start-1)*g.wealth_start*g.equity_return).sum()/capital))
        for m in PRIMARY_MODELS for k,g in L[m+PRIMARY_SUFFIX].groupby(L[m+PRIMARY_SUFFIX].index.to_period('Q'))])
    return data, tables
