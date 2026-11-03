"""Static research artifacts from actual saved Stage 5 paths, never synthetic results."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .metrics import drawdown,summarize


def table(frame,columns=None):
    frame=frame if columns is None else frame[columns]
    def cell(x):
        if isinstance(x,(float,np.floating)):
            return 'NA' if not np.isfinite(x) else f'{x:.6g}'
        return str(x).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(map(str,frame.columns))+' |',
        '| '+' | '.join(['---']*len(frame.columns))+' |']+['| '+' | '.join(cell(x) for x in row)+' |' for row in frame.itertuples(index=False,name=None)])


def create_reports(out,config,data_info,economic,forecast_metrics,stats,matches,ledgers,names,attribution,common):
    out=Path(out); figures=out/'figures';figures.mkdir()
    models=config['estimation']['models'];capital=config['policy']['initial_capital']
    selected=['buy_hold','constant_60']+[names[m] for m in models]
    primary=economic.set_index('strategy').loc[selected].reset_index()
    primary['sharpe_rank']=primary.net_sharpe.rank(ascending=False,method='min')
    title='EXPLORATORY / PROVISIONAL / NON-EXECUTABLE NIFTY TRI — 2024'
    def finish(fig,name):
        fig.suptitle(title,fontsize=10);fig.tight_layout(rect=(0,0,1,.95));fig.savefig(figures/name,dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(12,6))
    for name in selected:
        p=ledgers[name];ax.plot(p.index,p.wealth/capital,label=name.replace('_v12_c10_daily_b0',''))
    ax.set(ylabel='Net hypothetical wealth / initial capital',xlabel='Session close',xlim=(p.index.min(),p.index.max()));ax.legend(fontsize=8)
    finish(fig,'cumulative_values.png')
    fig,ax=plt.subplots(figsize=(12,6))
    for name in selected:
        p=ledgers[name];ax.plot(p.index,100*drawdown(p.wealth,capital),label=name.replace('_v12_c10_daily_b0',''))
    ax.set(ylabel='Drawdown (%)',xlabel='Session close',xlim=(p.index.min(),p.index.max()));ax.legend(fontsize=8);finish(fig,'drawdowns.png')
    fig,ax=plt.subplots(figsize=(12,6))
    for model in models:
        p=ledgers[names[model]];ax.plot(p.index,p.exposure,label=model)
    ax.axhline(.60,c='black',ls='--',label='constant60 target');ax.set(ylabel='Equity weight held during return',ylim=(0,1.03),xlim=(p.index.min(),p.index.max()));ax.legend(fontsize=8)
    finish(fig,'exposures.png')
    fig,ax=plt.subplots(figsize=(12,6))
    for model in models:
        f=common.loc[common.model.eq(model)];ax.plot(f.target_date,np.sqrt(252*f.forecast_variance),label=model)
    f=common.loc[common.model.eq(models[0])]
    ax.scatter(f.target_date,np.sqrt(252*f.observed_squared_log_return),s=7,alpha=.35,c='black',label='absolute daily log return × sqrt252 (noisy proxy)')
    ax.set(ylabel='Annualized risk units',xlabel='Target session',xlim=(f.target_date.min(),f.target_date.max()));ax.legend(fontsize=8);finish(fig,'forecast_risk.png')
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    axes[0].bar(primary.strategy,primary.rebound_participation);axes[0].set(ylabel='Equity-only recovery upside participation',title='Retrospective: + days within 10 sessions after return < −2%')
    axes[1].bar(primary.strategy,primary.annualized_one_way_turnover);axes[1].set(ylabel='Annualized one-way notional / wealth',title='Turnover, includes initial entry')
    for ax in axes:ax.tick_params(axis='x',rotation=75,labelsize=7)
    finish(fig,'rebound_turnover.png')
    cost=economic.loc[economic.model.isin(models)&economic.kind.isin(['primary','factorial_sensitivity'])&economic.target_vol.eq(.12)&economic.frequency.eq('daily')&economic.band.eq(0)]
    fig,ax=plt.subplots(figsize=(10,5))
    for model in models:
        f=cost.loc[cost.model.eq(model)].sort_values('cost_bps');ax.plot(f.cost_bps,100*f.transaction_cost_drag,marker='o',label=model)
    ax.set(xlabel='Illustrative one-way cost (bps)',ylabel='Terminal zero-cost minus net return (percentage points)');ax.legend(fontsize=8)
    finish(fig,'cost_sensitivity.png')
    economic_models=primary.loc[primary.model.isin(models)].merge(forecast_metrics,on='model',suffixes=('','_forecast'))
    fig,ax=plt.subplots(figsize=(10,5));ax.scatter(economic_models.qlike,economic_models.net_sharpe)
    for row in economic_models.itertuples():ax.annotate(row.model,(row.qlike,row.net_sharpe),xytext=(4,4),textcoords='offset points',fontsize=8)
    ax.set(xlabel='QLIKE (common valid h=2 dates; lower better)',ylabel='Net hypothetical Sharpe (all P&L dates)');finish(fig,'forecast_vs_economic.png')
    economic_models.to_csv(out/'forecast_vs_economic.csv',index=False)
    quarter_rows=[]
    for name in selected:
        for quarter,path in ledgers[name].groupby(ledgers[name].index.to_period('Q')):
            row=summarize(path,float(path.wealth_start.iloc[0]));quarter_rows.append(dict(strategy=name,quarter=str(quarter),**row))
    quarters=pd.DataFrame(quarter_rows);quarters.to_csv(out/'quarterly_metrics.csv',index=False)
    comparisons=[]
    for model in models:
        dyn=economic.loc[economic.strategy.eq(names[model])].iloc[0]
        for kind in ['exposure','risk']:
            bm=economic.loc[economic.strategy.eq(f'matched_{kind}_{model}')].iloc[0]
            comparisons.append(dict(model=model,benchmark=f'development_matched_{kind}',constant_weight=bm.constant,
                dynamic_net_return=dyn.net_cumulative_return,constant_net_return=bm.net_cumulative_return,
                dynamic_volatility=dyn.realized_volatility,constant_volatility=bm.realized_volatility,
                dynamic_exposure=dyn.average_equity_exposure,constant_exposure=bm.average_equity_exposure,
                dynamic_drawdown=dyn.maximum_drawdown,constant_drawdown=bm.maximum_drawdown))
    comparisons=pd.DataFrame(comparisons);comparisons.to_csv(out/'matched_benchmarks.csv',index=False)
    ex_post=economic.loc[economic.kind.eq('EX_POST_NON_DEPLOYABLE_DIAGNOSTIC')]
    ex_post_matching=pd.read_csv(out/'expost_matching.csv')
    ex_post_matching=ex_post_matching.rename(columns={'development_target':'evaluation_target',
        'development_match_error':'evaluation_match_error','development_observations':'evaluation_observations'})
    winner_forecast=forecast_metrics.sort_values('qlike').model.iloc[0]
    winner_economic=economic_models.sort_values('net_sharpe',ascending=False).model.iloc[0]
    signifs=int(stats.holm_p_value.lt(.05).sum())
    significant_benefits=int((stats.holm_p_value.lt(.05)&stats.sharpe_difference.gt(0)).sum())
    significant_underperformance=int((stats.holm_p_value.lt(.05)&stats.sharpe_difference.lt(0)).sum())
    bh=primary.loc[primary.strategy.eq('buy_hold')].iloc[0]
    dyn=primary.loc[primary.model.isin(models)]
    lower_sharpe=int(dyn.net_sharpe.lt(bh.net_sharpe).sum())
    lower_gross_sharpe=int(dyn.gross_sharpe.lt(bh.gross_sharpe).sum())
    n=len(ledgers['buy_hold']);first=ledgers['buy_hold'].index[0].date();last=ledgers['buy_hold'].index[-1].date()
    write=lambda name,text:(out/name).write_text(text+'\n',encoding='utf-8')
    write('position_sizing_experiment.md',f'''# Stage 5: economic value — EXPLORATORY, PROVISIONAL, NON-EXECUTABLE

This is a separate economic study. It does not modify or validate the frozen prospective forecasting protocol. All performance below is hypothetical NIFTY 50 TRI index accounting in INR, not an executed ETF portfolio or realized profits. 2024 has been repeatedly inspected. No 2025–2026 model fitting or economic evaluation occurs.

## Data and execution gates

The official NSE NIFTY 50 gross total-return index passed the existing numerical/source gates. {data_info['daily_valid']} usable daily observations were read through {data_info['input_last']}; forecasting history begins {data_info['input_first']}. Canonical gaps reset EWMA/GARCH estimation; no missing return is skipped in an economic path. RV/VIX predictors reuse the existing audited pre-2025 panel: {data_info['complete_rv_pre2025']} complete RV sessions and {data_info['lagged_iv_pre2025']} available conservatively lagged IV observations. NSE spot identity is user-confirmed. Original vendor/export chain, timezone and bar conventions remain unverified. The extra VIX session lag does not resolve provenance.

Panel A is a **theoretical daily total-return-index panel**. Fractional index claims cannot be traded. No management fee, ETF tracking error, tax, securities lending or dividend tax is modeled. **Panel B is BLOCKED**, as is any claimed executable ETF result. The tested next-open accounting primitive is not an empirical intraday backtest.

The bounded Yahoo NIFTYBEES download covers 2012-01-02 through 2024-12-31 (3,210 rows). It contains 35 nonfinite OHLC/adjusted-close cells and 170 zero-volume rows over that history, no recorded actions and Adj Close equal to Close. The [official fund corporate-action history](https://investeasy.nipponindiaim.com/rmfGsamnew/Products/NiftyBeES/CorporateAction.aspx) lists older cash distributions and the 2019 split, also documented by the [June 2022 factsheet](https://mf.nipponindiaim.com/investorservices/factsheetsdocuments/fundamentals-july-2022/Innerpage/ETF-Nifty-BeES.html). Yahoo Close can already be split-adjusted; absent actions do not prove an unadjusted split jump. They do prevent certification of the downloaded history as a fully documented total-return execution dataset.

For 2022–2024, the OHLC cells are finite, but Yahoo omits 2023-11-12, 2024-01-20, 2024-03-02 and 2024-05-18. It reports zero volume on 2024-11-01. Eight NSE archive files were retrieved and preserved unchanged; their NIFTYBEES rows confirm these sessions and nonzero November 1 volume. NSE also agrees with the unusual June 3–5 ETF prices: those moves are not declared errors merely because TRI differs. These partial cross-checks have not certified the complete adjusted series, distributions or executable closing fills. Neither Yahoo prices nor patched ETF prices enter this experiment. No data substitution is hidden.

## Registered models and timing

Five families: daily-return EWMA (lambda .94, initialization252), Gaussian zero-mean GARCH(1,1) (window1000, minimum500, percent scaling converted to decimal variance), new daily-target standard HAR, new daily-target Log-HAR and new daily-target Log-HAR+VIX. HAR uses a 500-session-position window, minimum126 completed training pairs, refit21 sessions, common RV/VIX training masks. Log forecasts use training-only zero-RV handling and residual-smearing retransformation. Levels HAR rejects invalid predictions; there is no tiny-variance floor used to conceal a negative prediction.

The HAR regressions target **NIFTY TRI squared daily log return**, using NIFTY spot RV as an auxiliary predictor, not as the risk target. The basis difference is explicit. These are new Stage 5 specifications, not unchanged Stage 4B candidates. EWMA/GARCH use longer permitted daily history; their estimation sample is not identical to HAR. All regressions use only completed response/predictor pairs.

A forecast issued just after close t executes at close t+1 and first affects the return ending t+2. Therefore primary forecasts are horizon2, a single future daily interval, **not the sum of two days' variance**. HAR is estimated directly at that horizon; GARCH uses its analytical multi-step conditional variance and EWMA its constant expected future variance. Extra-delay sensitivity uses origin t, execution t+2, target t+3. Weekly policies trade on the first native session of each ISO week and hold units between trades; the risk signal remains daily, not a weekly integrated forecast. Exchange special-session close timestamps are retained.

Desired exposure = target annual volatility / sqrt(252 × forecast daily variance), bounded 0–100%, no leverage/shorts. Cash earns an explicit 0% scenario; 4% is a separate illustrative sensitivity, not observed risk-free data. Cash accrues ACT/365. Trades solve for the target fraction of **post-cost** wealth. Old holdings earn the completed return before the close trade. All changes, attempted targets, actual weights, costs and cash are saved. There is no same-close use of an after-close signal. A 5-point band, when specified, compares desired with drifted current weight.

Primary policy:12% target, daily, no band, 10bps per one-way traded notional, missing/invalid forecasts hold existing units. No model substitution or price/forecast filling occurs. Missing forecasts retain subsequent losses in the portfolio path. Forecast failure-to-cash and deterministic every20th signal unavailable are separate stress scenarios. Remaining allocations earn the specified cash scenario.

## Evaluation sample and results

Initial entry is the 2024-01-01 close, using a prior-session signal. All policies have {n} identical native return dates, {first} through {last}. Initial entry cost is included in the first P&L observation. Final holdings are marked at December31 without forced liquidation; prospective exit costs are not included. There are {int(forecast_metrics.observations.iloc[0])} common valid h=2 forecast dates for QLIKE; the economic path retains all {n} dates even when a forecast fails. Complete primary accounting identities reconcile.

The zero-cost shadow is a counterfactual run of the same policy; gross versus net differences include cost compounding. Sharpe uses excess returns over the assumed cash return and 252 sessions. CAGR uses elapsed calendar time and is reported only for at least180 calendar days. ES95 is the mean worst ceil(5%×n) daily returns. Turnover is one-way and includes entry. Drawdown duration counts sessions below the initial-or-running peak; unrecovered drawdowns are explicitly marked. Rebound participation is equity-only upside capture on positive days within10 sessions after a <-2% index day; this is retrospective, not a prospective rule.

{table(primary,['strategy','observations','gross_cumulative_return','net_cumulative_return','net_sharpe','realized_volatility','maximum_drawdown','average_equity_exposure','annualized_one_way_turnover'])}

In this sample, **{lower_sharpe} of {len(models)} primary dynamic policies have lower net Sharpe than buy-and-hold**. {lower_gross_sharpe} also have lower zero-cost Sharpe, so trading costs are not the sole explanation. Dynamic average exposure remains {100*dyn.average_equity_exposure.min():.1f}%–{100*dyn.average_equity_exposure.max():.1f}%; their maximum drawdowns range from {100*dyn.maximum_drawdown.min():.2f}% to {100*dyn.maximum_drawdown.max():.2f}%, versus {100*bh.maximum_drawdown:.2f}% for buy-and-hold. Some risk reduction is visible, but the primary policies do not establish a superior risk-adjusted overlay.

Illustrative 10bps trading costs reduce primary dynamic terminal returns by {100*dyn.transaction_cost_drag.min():.2f}–{100*dyn.transaction_cost_drag.max():.2f} percentage points relative to their zero-cost shadows. The attribution shows that reduced exposure on loss days can help while missed recoveries and persistently lower exposure on other positive days offset those benefits. These are retrospective accounting observations, not evidence that a rule anticipated a crisis. The three HAR specifications each retain22 missing-predictor holding sessions; those returns remain in P&L under the hold-units rule rather than disappearing from the sample.

All numbers are decimal units except Sharpe and turnover multiples. Full metrics, all221 predefined economic paths and their zero-cost shadows are archived, plus10 explicitly ex-post fairness diagnostics. No best sensitivity combination is selected. A target volatility is a sizing parameter, not a guaranteed realized portfolio volatility; the 100% cap can prevent attaining it.

## Mandatory fairness checks

The constants below were fixed using only 2023-10-02 through 2023-12-29. The dynamic path in that period is calibration data, not a claimed out-of-sample economic result. Matching solves a bounded scalar allocation problem, including costs and daily rebalancing; unattainable risk is reported instead of using leverage. The calibration sample is short. The constant60 policy is an additional predefined comparison. No exactly full-2024-matched benchmark is passed off as deployable.

{table(matches,['model','criterion','weight','development_observations','development_target','development_match_error','status'])}

Actual 2024 matched-benchmark risk/exposure need not remain equal:

{table(comparisons)}

### Explicitly ex-post fairness diagnostic

After inspecting the first Stage5 results, an addendum registered10 additional diagnostic constants: each matches full-2024 average exposure or realized net volatility. The original primary run and registration remain preserved. These constants use evaluation outcomes, are **NON-DEPLOYABLE / EX-POST**, and are excluded from the15 formal contrasts. This follows the user's permitted full-sample diagnostic; it is not model selection or independent confirmation. They test whether similar realized risk could have arisen from constant de-risking.

{table(ex_post_matching,['model','criterion','weight','evaluation_target','evaluation_match_error','matching_sample','deployable'])}

{table(ex_post,['strategy','net_cumulative_return','net_sharpe','realized_volatility','maximum_drawdown','average_equity_exposure'])}

## Statistical limitations

Fifteen registered contrasts compare each primary dynamic policy against buy-and-hold, its development-matched exposure constant and its development-matched risk constant. Paired stationary bootstrap uses2,000 draws, mean block10 native sessions, seed20261103. All dates align without dropping failed signals. Sharpe differences have pointwise percentile intervals and centered two-sided bootstrap p-values; Holm adjusts the complete15-test family. {signifs} contrasts have adjusted p<.05. This is exploratory inference on saved portfolio paths, conditional on estimated models, with no adjustment that can make repeatedly examined 2024 independent. Parameter-estimation and research-selection uncertainty are not re-created by this bootstrap. Small differences, rankings and nonsignificance are not confirmation or equivalence.

{table(stats,['model','benchmark','sharpe_difference','ci_low','ci_high','p_value','holm_p_value'])}

Of the adjusted statistical flags, **{significant_benefits} favor a dynamic policy and {significant_underperformance} indicate underperformance**. Multiple comparisons against nearly identical constants are correlated contrasts, not independent replications. In particular, no statistically flagged improvement supports adopting a dynamic overlay here. These exploratory negative findings also require independent confirmation before generalizing beyond this sample.

## Research integrity and next step

The registration records an inspection incident: a pre-existing review displayed later-period return rows (April2025), full-window audit aggregates and a live search snippet before filtering. This was disclosed. Those values are not Stage5 inputs, features, returns or evaluation results. All numerical dataset reads now enforce the 2024 cutoff. Do not claim no incidental later-period exposure or call the historical holdout pristine. Source bytes are hashed without decoding later numerical observations.

All earlier reports, configurations and experiment artifacts are hash-checked unchanged. Stage5 cannot amend the frozen prospective forecasting protocol. Its old statement excluding portfolio work remains historically intact; the user's new request separately authorizes this economic experiment.

The safe next step is to verify complete investable adjusted OHLC/action history, actual execution/availability conventions, and RV/VIX provenance; then register a **separate economic prospective protocol** with costs, cash and risk constraints fixed before collecting genuinely new outcomes. Do not adopt an overlay for a live portfolio on these results. No trading capability is implemented.

## Reproduction

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\\.venv\\Scripts\\python.exe -m pytest -q --junitxml=reports/pytest-stage5.xml
.\\.venv\\Scripts\\python.exe -m volrisk.stage5_cli --config config/stage5.toml register
.\\.venv\\Scripts\\python.exe -m volrisk.stage5_cli --config config/stage5.toml run
```

The run command uses existing bounded inputs and does not download or ingest data. Completed runs are content-identified, hash-verified and reused; incomplete runs remain for inspection. Package/code/input/config hashes and forecast creation records precede outcome attachment. Plots are in `reports/figures/stage5/`. No2025–2026 evaluation is scheduled.
''')
    allocation=attribution.groupby(['model','benchmark','category']).allocation_effect.sum().div(capital).reset_index()
    totals=attribution.groupby(['model','benchmark'])[['allocation_effect','wealth_scale_effect','cash_pnl_difference','cost_difference']].sum().div(capital).reset_index()
    totals['terminal_return_difference']=totals[['allocation_effect','wealth_scale_effect','cash_pnl_difference','cost_difference']].sum(axis=1)
    allocation.to_csv(out/'allocation_attribution.csv',index=False);totals.to_csv(out/'pnl_attribution.csv',index=False)
    write('exposure_attribution.md',f'''# Exposure attribution — EXPLORATORY / PROVISIONAL / NON-EXECUTABLE

Each row reconciles exactly to dynamic minus benchmark terminal wealth, divided by initial capital. Allocation effect is (effective dynamic equity fraction − benchmark fraction) × dynamic beginning wealth × equity return. Wealth-scale effect captures different accumulated wealth at the benchmark fraction. Cash P&L difference and negative transaction-cost difference complete the identity. Initial entry costs are included. This separates compounding from allocation; it is an accounting explanation, not causal evidence of forecasting skill.

{table(totals)}

Allocation categories below are retrospective. Reduced exposure before a loss means less equity on the loss day without a negative immediately preceding session; after-loss means the preceding return was negative. Neither demonstrates foreknowledge. Missed recovery uses positive-return days within10 sessions after a <-2% return. Failure-affected holdings take category precedence, and the remaining categories partition every day. None of these labels affects signals. Persistent low exposure can duplicate constant de-risking.

{table(allocation.loc[allocation.benchmark.eq('buy_hold')])}

The full daily ledger and all matched-benchmark decompositions are saved. Cash drag in the metrics table is a separate arithmetic opportunity-cost diagnostic against100% equity; it is not added again to the reconciled decomposition. Costs, missed recoveries and lower participation must be weighed against drawdown reduction. Rebound and quarterly plots are retrospective diagnostics. No2025–2026 outcomes enter.
''')
    sensitivity=economic.loc[economic.kind.isin(['one_factor_sensitivity','operational_stress'])]
    write('trading_cost_sensitivity.md',f'''# Trading-cost sensitivity — EXPLORATORY / PROVISIONAL / NON-EXECUTABLE

Costs5/10/20bps per one-way traded notional are illustrative scenario assumptions, not measured expenses. They do not certify actual spread, market impact, fees, taxes or closing-auction fill availability. Zero-cost paths use the same rule and timing; terminal cost drag includes compounding. No configuration is selected from this grid.

Primary-policy cost comparison:

{table(cost.sort_values(['model','cost_bps']),['model','cost_bps','gross_cumulative_return','net_cumulative_return','transaction_cost_drag','net_sharpe','annualized_one_way_turnover'])}

The full CSV preserves180 factorial dynamic configurations (five models × three targets × two frequencies × two bands × three costs),25 one-factor/operational stress paths,12 primary static/matched paths and four static cost variants =221 registered paths. A disclosed post-result addendum adds10 ex-post non-deployable matched-exposure/risk diagnostics, for231 total. Every path also has a zero-cost shadow. The five primary dynamic cases are included within the180, not counted twice. Targets are experimental parameters, not portfolio recommendations.

The minimum25% case changes target bounds, not continuous enforcement between trades. Cash4% is hypothetical ACT/365. Delay sensitivity uses genuine h=3 forecasts rather than applying a stale h=2 forecast to the wrong target. Failure-to-cash uses only the registered minimum; the operational stress marks every20th evaluation execution signal unavailable without changing saved original forecasts. Actual model failures are retained in all paths.

{table(sensitivity,['strategy','net_cumulative_return','net_sharpe','realized_volatility','maximum_drawdown','average_equity_exposure','holding_failure_sessions'])}

Weekly rebalancing and5-point bands appear in the full CSV. They hold units between trades, not constant weights. Daily risk targets do not guarantee weekly holding-period risk. Sample length is one repeatedly examined year; no real-world profit inference is warranted.
''')
    write('forecast_vs_economic_value.md',f'''# Forecast accuracy versus economic value — EXPLORATORY / PROVISIONAL

The forecast comparison is for NIFTY TRI **daily close-to-close log-return variance**, at horizon2, on common finite target dates. Portfolio P&L uses simple total returns on every native session, with failures explicitly handled. Original spot intraday RV QLIKE scores are not imported into this ranking. HAR/Log-HAR/VIX below are newly estimated economic-study specifications. The shorter common QLIKE sample and complete economic path are different estimands; this scatter is descriptive, not a controlled causal test.

{table(economic_models,['model','qlike','qlike_rank','calibration','failure_rate','net_cumulative_return','net_sharpe','maximum_drawdown','average_equity_exposure','transaction_cost_drag'])}

Lowest exploratory QLIKE: **{winner_forecast}**. Highest primary dynamic-policy net Sharpe: **{winner_economic}**. These are point-estimate descriptions, not selected winners or statistically confirmed alpha. Their agreement/disagreement does not prove that forecast accuracy causes economic benefit. Inverse-volatility weights, the100% cap, next-close delay, lower average exposure, cash and costs all intervene. Better error loss can produce worse timing or missed recovery; a lower-quality forecast can accidentally de-risk before a loss. Static matched benchmarks are essential to distinguish this from persistent exposure reduction.

Economic uncertainty is based on the15 predeclared paired Sharpe contrasts, with {signifs} adjusted p-values below.05. See `position_sizing_experiment.md` for all intervals, matching errors and the conditional-bootstrap limitation. Even a small adjusted p-value in this reused exploratory sample would not be independent confirmation.

Quarter diagnostics for the primary dynamic paths (no quarter is used for model selection):

{table(quarters.loc[quarters.strategy.isin(list(names.values()))],['strategy','quarter','net_cumulative_return','net_sharpe','realized_volatility','maximum_drawdown'])}

Retain EWMA and both static controls as essential low-complexity economic baselines. Retain GARCH and daily-target HAR/Log-HAR/VIX as research challengers only after provenance and executable data gates pass. Do not advance a live risk overlay or alter the frozen forecasting candidates on these findings. A newly registered, genuinely prospective economic study is required.
''')
