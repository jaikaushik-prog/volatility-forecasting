"""Honest provisional reports and target-labelled scientific diagnostics for Stage 4."""
from __future__ import annotations
import numpy as np
import pandas as pd
from volrisk.data.storage import write_text
from volrisk.data.intraday.reporting import table


def readiness_report(manifest,coverage):
    info=manifest['data_readiness']
    subset=coverage[coverage.frequency.eq(5) & coverage.scenario.eq('eligible')]
    return '\n'.join(['# Forecast readiness — PROVISIONAL','',
        'Numerical and temporal integrity gates passed on the loaded development/validation artifacts. '
        'This is not independent source certification. The user confirmed NIFTY as an NSE spot-index series '
        '(reported source: NSE); the original audit remains unchanged. Export documentation, original timezone '
        'and bar labels remain unverified. SENSEX retains its separate BSE calendar and source-identity limitation.', '',
        f'Run `{manifest["run_id"]}`; source intraday run `{info["intraday_run_id"]}`. Numerical values were loaded only through '
        f'**{info["loaded_through"]}**. No 2025–2026 forecasting or evaluation occurred.', '',
        '## Gates and exclusions','',
        '- Verify input, calendar-evidence, intraday implementation and artifact hashes; never re-ingest or alter raw data.',
        '- Reconcile saved 5/10/15-minute bars to daily RV, semivariances, bar availability and session boundaries.',
        '- Require complete valid within-session minutes. Preserve verified special sessions at their actual duration; do not scale them to a normal day.',
        '- Reconcile overnight and spot close-to-close returns to adjacent valid session endpoints. Never bridge absent/unverified sessions.',
        '- Preserve missing/excluded session rows, so 5/22-session feature windows cannot compress gaps.',
        '- Verify VIX EOD age, same-session availability and percent/decimal conversion; apply one additional FULL SESSION lag.',
        '- The extra VIX lag reduces timing ambiguity but does not verify timezone, source identity or bar labels.',
        '- Exclude incomplete/unverified sessions; identical duplicate copies were already quarantined by integration.',
        '- Sensitivity additionally excludes sessions with absolute-return flags or at least ten unchanged-price minutes. These flags may represent genuine market moves; this is not a new raw-data cleaning rule.',
        '- Whole-file MAD flags from integration are NOT used for model features or exclusions: their thresholds used the full source sample.', '',
        table(subset),'',
        'Complete sessions count usable measured RV, not supervised training pairs or evaluated forecasts. '
        'All-HAR-origin-feature counts include rolling-history/VIX constraints. `har_rv_sample_sizes.csv` covers every scenario/frequency; '
        '`har_rv_exclusions.csv` identifies each excluded session. `har_rv_model_comparison.csv` contains actual evaluated counts.', '',
        '## Holdout protection','',
        'Development is 2022–2023 (actual NIFTY starts 2022-10-25); validation is 2024. Holdout remains 2025–2026, '
        'with the earlier project boundary preserved. Parquet predicate filters and a second walk-forward cutoff prevent holdout '
        'values from entering features, training, plots, losses or selection. File hashing examines bytes only. '
        'Earlier Stage 2 outputs and the descriptive integration audit had already exposed aspects of 2025–2026; '
        'the archive cannot be described as historically pristine. Future final confirmation needs a genuinely unseen, predeclared period.', ''])


def _plots(folder,forecasts,panels,config):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder.mkdir(parents=True,exist_ok=True)
    paths=[]
    for asset in sorted(forecasts.asset.unique()):
        base=forecasts[forecasts.asset.eq(asset)&forecasts.frequency.eq(5)&forecasts.scenario.eq('eligible')]
        main=base[base.target.eq('intraday') & base.common]
        val=main[main.period.eq('validation')]
        if val.empty: continue
        def save(fig,name,title):
            fig.suptitle(f'{asset} — PROVISIONAL — {title}',fontsize=11)
            fig.tight_layout()
            path=folder/f'{asset}_{name}.png'
            fig.savefig(path,dpi=145)
            plt.close(fig)
            paths.append(str(path.name))
        wide=main.pivot(index='target_date',columns='model',values='forecast_variance').sort_index()
        actual=main.drop_duplicates('target_date').set_index('target_date').observed_variance.sort_index()
        fig,ax=plt.subplots(figsize=(12,5))
        ax.plot(actual.index,actual,lw=.8,color='black',alpha=.6,label='Observed 5-minute intraday RV')
        for m in ('har','log_har','har_vix','har_overnight'):
            if m in wide: ax.plot(wide.index,wide[m],lw=.8,label=m)
        split=pd.Timestamp(config['splits']['validation'][0])
        ax.axvline(split,color='grey',ls='--',label='Validation begins (2024); earlier = development')
        ax.set_ylabel('Daily intraday variance (decimal return²)')
        ax.legend(fontsize=8,ncol=2)
        save(fig,'forecast_vs_realized','5-minute target; holdout sealed')
        fig,axes=plt.subplots(2,1,figsize=(12,7))
        for model,g in val.groupby('model'):
            g=g.sort_values('target_date')
            axes[0].plot(g.target_date,g.loss_qlike.cumsum(),label=model,lw=.8)
            axes[1].plot(g.target_date,g.loss_qlike.rolling(config['evaluation']['rolling_loss_window'],min_periods=20).mean(),label=model,lw=.8)
        axes[0].set_ylabel('Cumulative QLIKE (lower is better)')
        axes[1].set_ylabel('Rolling mean QLIKE (matched observations)')
        axes[0].legend(fontsize=8,ncol=3)
        save(fig,'qlike','validation only; matched 5-minute intraday target dates')
        comparison='har_vix' if asset=='NIFTY' else 'har_overnight'
        selected=val[val.model.isin(['har',comparison])]
        fig,axes=plt.subplots(2,1,figsize=(12,7))
        for name,g in selected.groupby('model'):
            axes[0].plot(g.target_date,np.sqrt(g.forecast_variance*252)*100,label=name,lw=1)
        a=selected.pivot(index='target_date',columns='model',values='loss_qlike')
        if {'har',comparison}<=set(a): axes[1].plot(a.index,(a[comparison]-a.har).cumsum(),color='#b24c35')
        axes[0].set_ylabel('Predicted annualized volatility (%)')
        axes[1].set_ylabel(f'Cumulative QLIKE difference: {comparison} − HAR')
        axes[0].legend()
        save(fig,'incremental_information','validation; same target, dates and HAR training samples')
        fig,ax=plt.subplots(figsize=(8,6))
        for name,g in val.groupby('model'):
            bucket=pd.qcut(g.forecast_variance.rank(method='first'),5,labels=False)
            calibration=g.groupby(bucket).agg(predicted=('forecast_variance','mean'),observed=('observed_variance','mean'))
            ax.plot(calibration.predicted,calibration.observed,marker='.',label=name)
        hi=max(ax.get_xlim()[1],ax.get_ylim()[1])
        ax.plot([0,hi],[0,hi],color='black',ls='--',lw=.8)
        ax.set(xlabel='Mean predicted variance',ylabel='Mean observed intraday RV')
        ax.legend(fontsize=8)
        save(fig,'calibration','validation; ex-post predicted-risk quintiles (diagnostic only)')
        observed=val.drop_duplicates('target_date').set_index('target_date').observed_variance
        event=observed.idxmax()
        event_rows=val[val.target_date.between(event-pd.Timedelta(days=12),event+pd.Timedelta(days=12))]
        fig,axes=plt.subplots(2,1,figsize=(12,7))
        e=event_rows.drop_duplicates('target_date')
        axes[0].plot(e.target_date,e.observed_variance,color='black',label='Actual RV',marker='.')
        for name,g in event_rows[event_rows.model.isin(['har','log_har','har_vix','har_overnight'])].groupby('model'):
            axes[0].plot(g.target_date,g.forecast_variance,label=name,marker='.')
            axes[1].plot(g.target_date,g.forecast_variance-g.observed_variance,label=name,marker='.')
        axes[0].legend(fontsize=8,ncol=3)
        axes[0].set_ylabel('Variance (decimal²)')
        axes[1].set_ylabel('Forecast minus observed RV')
        save(fig,'shock_diagnostics',f'validation retrospective window around largest matched RV: {event.date()}')
        c2c=base[base.target.eq('spot_c2c_squared') & base.common & base.period.eq('validation')]
        if len(c2c):
            fig,axes=plt.subplots(2,1,figsize=(12,7))
            for name,g in c2c[c2c.model.isin(['har','log_har','spot_garch','spot_egarch','spot_gjr'])].groupby('model'):
                axes[0].plot(g.target_date,np.sqrt(g.forecast_variance*252)*100,label=name,lw=.8)
                axes[1].plot(g.target_date,g.loss_qlike.cumsum(),label=name,lw=.8)
            axes[0].legend(fontsize=8,ncol=3)
            axes[0].set_ylabel('Predicted annualized volatility (%)')
            axes[1].set_ylabel('Cumulative QLIKE')
            save(fig,'garch_comparable_target','validation; SPOT close-to-close squared-return target, NOT intraday RV')
        if asset=='NIFTY':
            panel=panels[(asset,5,'eligible')]
            g=val[val.model.eq('har')]
            implied=panel.vix_implied_variance.reindex(g.origin_date).to_numpy()
            fig,ax=plt.subplots(figsize=(8,5))
            ax.scatter(np.sqrt(implied)*100,np.sqrt(g.observed_variance*252)*100,s=10,alpha=.5)
            ax.set(xlabel='Prior-session India VIX (annualized %, ~30 calendar days)',
                   ylabel='Next-session intraday RV: sqrt(252 × RV), %')
            save(fig,'vix_subsequent_rv','validation diagnostic; distinct forward/realized horizons')
    return paths


def _effect_text(tests,challenger,reference,target='intraday'):
    if tests.empty: return 'No matched observations support this comparison.'
    selected=tests[tests.asset.eq('NIFTY') & tests.frequency.eq(5) & tests.scenario.eq('eligible') & tests.target.eq(target)
                   & tests.challenger.eq(challenger) & tests.reference.eq(reference)]
    if selected.empty: return 'No matched observations support this comparison.'
    r=selected.iloc[0]
    return (f'{challenger} versus {reference}: n={int(r.n)}, mean QLIKE difference={r.mean_loss_difference:.6g} '
        f'(negative favours {challenger}); gap-aware bootstrap 95% interval [{r.ci_low:.6g}, {r.ci_high:.6g}]; '
        f'HAC/Holm p={r.hac_p_holm:.6g}, bootstrap/Holm p={r.bootstrap_p_holm:.6g}. '
        f'Multiplicity-adjusted evidence under both checks: {bool(r.significant_after_multiplicity)}. '
        f'Without retrospective shocks, mean difference={r.mean_difference_without_shocks:.6g}; '
        f'top five dates account for {r.top5_share_absolute_loss_difference:.1%} of absolute paired loss differences. '
        f'Inference status: {r.inference_status}.')


def write_reports(run,manifest,forecasts,fits,metrics,tests,regimes,cov,panels,*,make_figures=True):
    folder=run/'reports'
    write_text(readiness_report(manifest,cov),folder/'forecast_readiness.md')
    validation=metrics[metrics.period.eq('validation') & metrics['sample'].eq('common')]
    primary=validation[validation.asset.eq('NIFTY') & validation.frequency.eq(5) & validation.scenario.eq('eligible')]
    columns=['asset','target','model','n_evaluated','qlike','mse','mae','calibration_ratio','bias',
             'estimation_failure_rate','prediction_failure_rate','runtime_seconds','rank_qlike']
    sources=('Method: [Corsi, A Simple Approximate Long-Memory Model of Realized Volatility]'
             '(https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1365738). '
             'India VIX units/horizon: [NSE definition]'
             '(https://www.nseindia.com/static/products-services/indices-indiavix-index).')
    intro=['# HAR-RV research — PROVISIONAL','',
        '**Validation findings only; final holdout not evaluated.** NSE spot identity for NIFTY was confirmed by the user; '
        'the export/timezone/bar conventions remain unverified. The additional full-session VIX lag does not resolve those uncertainties.', '',
        '## Predeclared models and targets','',
        'M1 `har`: OLS in variance levels using RV_t, arithmetic mean RV over 5 sessions through t and over 22 sessions through t. '
        'M2 `log_har`: log target and logs of those arithmetic averages. M3 `har_overnight`: M1 plus observed overnight square '
        'and 5/22-session means. M4 `har_vix`: M1 plus annualized implied variance (VIX_(t−1)/100)^2. '
        'M5 `har_vix_overnight`: M1 plus both groups. SENSEX uses M1–M3; India VIX is NIFTY-based and is not silently treated as SENSEX IV.', '',
        'Primary target: next-session within-session RV at 5 minutes. Secondary: next-session intraday RV plus squared overnight '
        'log return. Scheduled-break reopening squares are deliberately NOT added to this requested secondary target. '
        'It is distinct from squared close-to-close return. The additional spot-c2c panel fits HAR predictors to squared '
        'close-to-close returns and compares them with the existing zero-mean EWMA/GARCH/EGARCH/GJR implementations on that SAME target. '
        'Daily NIFTY TRI is never imported into these spot comparisons. Daily-return GARCH is not ranked against intraday RV.', '',
        'Benchmarks: previous observed target variance, 5/22-session target means, EWMA of observed variance (lambda .94; initial '
        '22-session mean). In the spot-c2c panel, these smooth squared spot returns. Return-EWMA uses the existing sample-variance '
        'initialization. Daily GARCH uses ×100 return scaling, converted back to decimal variance, 252-return minimum, 500-session '
        'window and 21-session refits. Missing returns reset its filter; no model substitutes for failed fits.', '',
        'HAR uses a rolling 500-session-position window, at least 126 completed pairs, and refits every 21 sessions. '
        'Every HAR variant within an asset/target/frequency/scenario uses the SAME completed training rows (union of required features), '
        'not just matched evaluation dates. Thus added VIX/overnight effects are not disguised training-sample changes. '
        'SENSEX uses its own sample. Parameters remain fixed between refits, while current observable predictors update.', '',
        'The positive floor is 10^-6 times the median positive training target, recomputed only at refits. Zero observations '
        'remain unchanged for evaluation; log-HAR floors them only inside its training transformation. Nonpositive level predictions '
        'are floored with raw predictions and flags retained. Nonfinite/explosive forecasts are missing. '
        'Log-HAR uses training residual smearing: exp(predicted log variance) × mean(exp(training residual)). '
        'This assumes a common residual retransformation factor and is not a guarantee against conditional bias. '
        'OLS is standardized using training statistics; rank, condition number, coefficients, fit dates and residual diagnostics are saved.', '',
        'All complete verified special sessions retain their measured duration. No normalization to 375 minutes is invented; '
        'the basic HAR has no explicit duration regressor, a remaining specification limitation. Missing or excluded sessions break '
        'rolling feature windows. Forecasts are issued after the origin close and before the next session; '
        '`forecast_created_at` is a historical-simulation convention, not evidence of actual historical issuance.', '',sources,'',
        '## Validation rankings — separate targets','',table(primary[columns].sort_values(['target','rank_qlike'])),'',
        'Calibration is mean(observed variance)/mean(predicted variance); above one means aggregate underprediction. '
        'QLIKE is log(h)+y/h. Only strictly positive finite forecasts and observed nonnegative targets are scored. '
        'All-available metrics are diagnostic; only common-date rows are ranked. Failed/warm-up attempts and runtime are retained outside '
        'the common-date filter. Calibration ranking uses distance of log(calibration ratio) from zero.', '',
        '## Incremental information and statistical uncertainty','',
        _effect_text(tests,'log_har','har'),'',_effect_text(tests,'har_vix','har'),'',
        _effect_text(tests,'har_overnight','har'),'',_effect_text(tests,'har_vix_overnight','har_overnight'),'',
        'Paired losses use identical targets/dates. HAC covariance respects session-position spacing; stationary block-bootstrap '
        'blocks restart at missing-session gaps. Intervals are pointwise approximate 95% intervals; p-values receive Holm adjustment '
        'over ALL predeclared validation comparisons across assets, frequencies, targets and exclusion scenarios. '
        'Nested models, short samples and model misspecification limit these asymptotic/resampling checks. Rankings alone do not establish superiority.', '',
        '## Robustness and concentration','',
        '1/5/10/15-minute targets are evaluated separately; no pooled frequency ranking is produced. The 10-minute series '
        'retains its labelled final short interval. Sensitivity refits after excluding absolute-return/stale-price flags; '
        'legitimate crisis moves can meet those thresholds. Excluded observations remain missing, with no interpolation. '
        'Compare eligible/exclusion scenarios also on their intersection of target dates in `har_rv_sensitivity.csv`. '
        'SENSEX is a secondary robustness sample, not a pooled estimate of NIFTY predictability.', '',
        'Regime and quarter tables distinguish origin-known trailing-RV regimes, transitions and lagged VIX changes from '
        'retrospective shock/recovery labels. Shock definitions are fixed in configuration. Shock windows never enter model estimation. '
        'Small event samples cannot identify which model universally adapts fastest. Paired-test output includes the mean loss difference '
        'outside shocks and the concentration of absolute loss differences in five dates.', '',
        '## Limitations and next research step','',
        'These results are PROVISIONAL. Confirm the source/export conventions, rerun the same frozen specifications on a verified vintage, '
        'and obtain a genuinely unseen evaluation period before advancing models to position-sizing research. '
        'A gain in intraday-RV accuracy is not evidence of portfolio utility. No position sizing, trading, Heston or LSTM was implemented.', '',
        'Forecasts, pre-observation issuance records, fit diagnostics and input/config/code/output hashes are stored in the immutable '
        f'run `{manifest["run_id"]}`. The protected 2025–2026 holdout remains unevaluated by this workflow.', '']
    # Explicitly identify inadequate panels, rather than hiding them in empty plots/rankings.
    thin=validation[validation.n_evaluated.lt(60)]
    if len(thin): intro += ['## Small or unavailable comparison samples','',table(thin[['asset','frequency','scenario','target','model','n_evaluated']]),'',
        'These panels are insufficient for strong statistical conclusions; zero means no common comparable forecasts, not zero forecasting loss.','']
    figures=_plots(folder/'figures/har_rv',forecasts,panels,manifest['config']) if make_figures else []
    intro += ['## Figures','']+[f'- [{name}](figures/har_rv/{name})' for name in figures]
    write_text('\n'.join(intro)+'\n',folder/'har_rv_research.md')
    write_text('\n'.join(['# India VIX incremental value — PROVISIONAL','',
        'NIFTY validation only. VIX enters as (prior-session EOD percentage / 100)^2, an ANNUALIZED implied-variance regressor. '
        'Its coefficient estimates its relationship with the next-session target; it is not divided by 252 and called an observed '
        'daily variance. The prior-session shift is additional to origin/target alignment. Missing VIX is never filled. '
        'Annualized VIX refers to roughly 30 calendar days, unlike the daily realized target. '+sources,'',
        _effect_text(tests,'har_vix','har'),'',_effect_text(tests,'har_vix_overnight','har_overnight'),'',
        'Secondary overnight-inclusive target:', '',_effect_text(tests,'har_vix','har','intraday_overnight'),'',
        'Inspect quarter/regime robustness and adjusted paired evidence before attributing incremental value. '
        'No final-holdout evidence or portfolio conclusion is available.']),folder/'vix_incremental_value.md')
    write_text('\n'.join(['# Overnight-risk forecasting — PROVISIONAL','',
        'All overnight predictors are already observed at the forecast origin. Weekly/monthly means retain missing-session gaps. '
        'The target is intraday RV plus overnight squared return, not squared close-to-close return and not the integration '
        'artifact that also includes scheduled-break reopening squares.','',
        _effect_text(tests,'har_overnight','har'),'',_effect_text(tests,'har_overnight','har','intraday_overnight'),'',
        _effect_text(tests,'har_vix_overnight','har_vix','intraday_overnight'),'',
        'Incremental performance and risk-share magnitude answer different questions. A material overnight variance share '
        'does not by itself imply that lagged overnight features improve forecasts. Holdout and portfolio utility remain untested.']),
        folder/'overnight_risk_analysis.md')
    winners=[]
    for target,g in primary[primary.n_evaluated.gt(0)].groupby('target'):
        r=g.sort_values('qlike').iloc[0]
        winners.append({'target':target,'lowest_validation_qlike_model':r.model,'qlike':float(r.qlike),
                        'calibration_ratio':float(r.calibration_ratio),'n':int(r.n_evaluated),'status':'PROVISIONAL_RANK_ONLY'})
    return {'nifty_5min_validation':winners,'figures':figures,'holdout_evaluated':False,'research_certified':False}


def write_blocked_reports(folder,message):
    folder.mkdir(parents=True,exist_ok=True)
    for name in ('har_rv_research','vix_incremental_value','overnight_risk_analysis','forecast_readiness'):
        write_text(f'# Stage 4 — BLOCKED\n\nCritical data gate failed: {message}\n\nNo empirical models or comparisons were run. '
                   'Synthetic unit tests do not establish real-data results. Holdout remains sealed.\n',folder/f'{name}.md')
    pd.DataFrame(columns=['asset','model','target','n_evaluated','qlike','calibration_ratio','status']).to_csv(folder/'har_rv_model_comparison.csv',index=False)
