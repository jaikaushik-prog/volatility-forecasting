"""Exploratory reports and a prospective protocol; no independent-confirmation claims."""
from datetime import datetime, timezone
import json
import numpy as np
import pandas as pd

from volrisk.data.storage import write_text


def table(frame):
    def fmt(v):
        if isinstance(v,(float,np.floating)):
            return f'{v:.6g}' if np.isfinite(v) else 'NA'
        return str(v)
    lines=['| '+' | '.join(frame.columns)+' |','| '+' | '.join(['---']*len(frame.columns))+' |']
    lines.extend('| '+' | '.join(fmt(x) for x in row)+' |' for row in frame.itertuples(index=False,name=None))
    return '\n'.join(lines)


def make_plots(folder, forecasts, events, coefficients, floors):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    folder.mkdir(parents=True,exist_ok=True)
    paths=[]
    colours={'har':'#0072B2','log_har':'#E69F00','log_har_vix':'#009E73',
             'log_har_vix_change':'#D55E00','ridge_log_har_vix':'#CC79A7','rv_ewma':'#666666'}
    def save(fig,name):
        for ax in fig.axes:
            if ax.get_xlabel()=='Target session' or ax.get_xlabel().startswith('Session date'):
                locator=mdates.AutoDateLocator(minticks=3,maxticks=7)
                ax.xaxis.set_major_locator(locator);ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
            ax.grid(alpha=.15)
        fig.suptitle('NIFTY Stage 4B — PROVISIONAL / EXPLORATORY\n2024 reused sample; no independent confirmation',fontsize=12)
        fig.tight_layout(rect=(0,0,1,.93))
        path=folder/(name+'.png');fig.savefig(path,dpi=150);plt.close(fig);paths.append(path.name)
    for target,g in forecasts[forecasts.common].groupby('target'):
        calendar=pd.DatetimeIndex(forecasts.loc[forecasts.target.eq(target),'target_date'].drop_duplicates().sort_values())
        fig,axes=plt.subplots(2,1,figsize=(12,8),sharex=True)
        actual=g.drop_duplicates('target_date').sort_values('target_date')
        axes[0].plot(calendar,actual.set_index('target_date').observed_variance.reindex(calendar),color='black',lw=1.1,label='Observed proxy (matched dates)')
        wide=g.pivot(index='target_date',columns='model',values='loss_qlike').reindex(calendar)
        for model,part in g.groupby('model'):
            axes[0].plot(calendar,part.set_index('target_date').forecast_variance.reindex(calendar),lw=.8,label=model,color=colours[model])
            if model!='log_har': axes[1].plot(wide.index,(wide[model]-wide.log_har).cumsum(),label=model,lw=1.1,color=colours[model])
        axes[0].set_ylabel(target+' variance (decimal²)');axes[0].legend(fontsize=8,ncol=3)
        axes[1].axhline(0,color='black',ls='--',lw=.7)
        axes[1].set_ylabel('Cumulative QLIKE minus Log-HAR\n(lower favours challenger)');axes[1].set_xlabel('Target session')
        save(fig,target+'_forecasts_and_loss')
        fig,ax=plt.subplots(figsize=(8,6))
        for model,part in g.groupby('model'):
            bucket=pd.qcut(part.forecast_variance.rank(method='first'),5,labels=False)
            means=part.groupby(bucket).agg(h=('forecast_variance','mean'),y=('observed_variance','mean'))
            ax.plot(means.h,means.y,marker='.',label=model,color=colours[model])
        hi=max(ax.get_xlim()[1],ax.get_ylim()[1]);ax.plot([0,hi],[0,hi],'k--',lw=.7)
        ax.set(xlabel='Mean predicted variance — ex-post risk quintiles',ylabel='Mean observed '+target+' variance')
        ax.legend(fontsize=8);save(fig,target+'_calibration')
    fig,axes=plt.subplots(3,1,figsize=(12,9),sharex=True)
    calendar=pd.DatetimeIndex(forecasts.loc[forecasts.target.eq('intraday'),'target_date'].drop_duplicates().sort_values())
    aligned=events.set_index('target_date').reindex(calendar)
    axes[0].plot(calendar,aligned.lagged_vix_percent,label='Lagged VIX on matched dates',color='#0072B2')
    neg=events[events.negative_raw]
    axes[0].scatter(neg.target_date,neg.lagged_vix_percent,color='#D55E00',label='Negative legacy forecast',s=14)
    axes[0].set_ylabel('VIX percent');axes[0].legend(fontsize=8)
    axes[1].plot(calendar,aligned.raw_prediction,label='Legacy raw levels prediction',color='#D55E00')
    axes[1].axhline(0,color='black',ls='--',lw=.7);axes[1].set_ylabel('Raw variance')
    axes[2].step(coefficients.refit_origin,coefficients.vix_implied_variance,where='post',marker='.',label='Legacy IV slope')
    axes[2].set(ylabel='Levels IV coefficient',xlabel='Session date (top/middle: target; bottom: refit origin)')
    save(fig,'legacy_failure_mechanism')
    fig,ax=plt.subplots(figsize=(8,6))
    ax.plot(floors.floor_fraction_of_training_median,floors.qlike,marker='o')
    ax.set_xscale('log');ax.set_yscale('symlog',linthresh=10)
    ax.set(xlabel='Counterfactual floor / positive training-target median',ylabel='Legacy QLIKE (symmetric-log axis)')
    ax.set_title('Diagnostic only: no floor chosen to improve ranking',fontsize=10)
    save(fig,'legacy_floor_sensitivity')
    return paths


def write_stage4b_reports(run, manifest, panel, forecasts, fits, metrics, tests, slices, stability,
                         events, coefficients, correlations, floors, scores, reproduction, alignment, *, make_figures=True):
    folder=run/'reports'
    common=metrics[(metrics['sample']=='common') & metrics.comparison_group.eq('six_predefined_models')]
    primary=common[common.target.eq('intraday')].sort_values('rank_qlike')
    secondary=common[common.target.eq('intraday_overnight')].sort_values('rank_qlike')
    neg=events[events.negative_raw]
    qualifier=('**PROVISIONAL / EXPLORATORY.** Model specifications were motivated by the already inspected 2024 results. '
        'Every 2024 improvement, interval and p-value below is exploratory, not independent confirmation. '
        'Only saved Stage 4 panels through 2024-12-31 were read numerically; no 2025–2026 data was loaded. '
        'NIFTY is user-confirmed NSE spot; vendor/export, original timezone and bar labels remain unverified.')
    source=('Sources: [NSE India VIX definition](https://www.nseindia.com/static/products-services/indices-indiavix-index); '
        '[Ridge objective and penalty convention](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html). '
        'The Ridge solve uses NumPy augmented least squares, with no additional package dependency.')
    diag=['# VIX model diagnostics',qualifier,
        '## Exact reproduction',table(reproduction),
        'Forecast dates, coefficients, raw/final predictions, floor flags and training endpoints reproduced exactly. '
        'Original run artifacts and published Stage 4 reports were hash-checked and are not overwritten. '
        'A snapshot of the original Stage 4 source is preserved under experiments/stage4b/stage4_code_snapshot.',
        '## Mechanism of negative levels forecasts',
        f'On {len(events)} matched primary target dates, {len(neg)} raw levels HAR+VIX forecasts are nonpositive. '
        f'{int(neg.marginal_extrapolation.sum())} are outside at least one training feature range; '
        f'{int(neg.outside_training_convex_hull.eq(True).sum())} are outside the joint training convex hull. '
        'Marginal ranges and joint-support extrapolation are distinct checks. Convex-hull feasibility uses standardized '
        'predictors and reports solver status; extrapolation is evidence of an unfamiliar predictor combination, not proof of bad data.',
        table(neg[['target_date','refit_origin','lagged_vix_percent','log_iv_change','vix_z_score','raw_prediction',
                   'marginal_extrapolation','outside_training_convex_hull']]),
        'The available VIX value refers to the prior native session. Its signed change is log(IV_(t−1)) − log(IV_(t−2)), '
        'with IV=(VIX_percent/100)^2. Large declines in available IV can remove a positive fitted contribution while '
        'other fitted contributions and the intercept remain negative. The linear predictor has no positivity constraint.',
        table(coefficients[['refit_origin','intercept','rv_daily','rv_weekly','rv_monthly','vix_implied_variance',
                            'vix_vif','condition_standardized']]),
        'Each forecast contribution is recorded in stage4b_legacy_events.csv and reconciled to its saved raw forecast. '
        'Refit slopes are conditional associations; changes after a shock are not structural causal effects of VIX.',
        '## Correlation, standardization and numerical stability',
        f'The standardized design condition number ranges from {coefficients.condition_standardized.min():.4g} to '
        f'{coefficients.condition_standardized.max():.4g}; the VIX variance-inflation factor ranges from '
        f'{coefficients.vix_vif.min():.4g} to {coefficients.vix_vif.max():.4g}. '
        f'The maximum absolute standardized-versus-unscaled OLS prediction difference is '
        f'{events.standardized_vs_unscaled_prediction_difference.abs().max():.6g}. '
        'Standardization substantially changes numerical conditioning but, for unregularized OLS with an intercept, '
        'does not change the fitted linear function. It did not create the negative forecasts. The measured VIF/condition '
        'numbers do not support severe numerical multicollinearity as the principal cause.',
        table(correlations[correlations.feature.eq('vix_implied_variance') & correlations.other_feature.ne('vix_implied_variance')]),
        'Full feature correlation matrices are saved per refit. Moderate correlation can affect partial slopes, '
        'but unconstrained levels predictions, coefficient shifts and extrapolation are the direct observed mechanism.',
        '## QLIKE floor sensitivity — diagnostic only',table(floors),
        'These five fixed counterfactual floors retain every matched observation and refit no model. '
        'The smallest setting reproduces Stage 4. For a negative raw prediction, the y/h term grows rapidly as '
        'the replacement floor approaches zero. No floor is selected from this table; unsuccessful Stage 4 forecasts remain unchanged.',source]
    write_text('\n\n'.join(diag)+'\n',folder/'vix_model_diagnostics.md')

    cols=['rank_qlike','model','n_evaluated','qlike','mse','mae','calibration_ratio','rank_calibration','bias',
          'forecast_stability','estimation_failure_rate','prediction_failure_rate','runtime_seconds']
    selection=pd.DataFrame(list(manifest['ridge_selection'].values()))
    matched=forecasts[forecasts.common]
    positive=forecasts[forecasts.model.str.contains('log_har') & forecasts.forecast_valid]
    n_unique_training=int(fits[fits.model.eq('log_har')].training_observations.max())
    legacy=metrics[metrics.comparison_group.eq('archived_unsuccessful_comparator') & metrics['sample'].eq('common')]
    stability_subset=stability[stability.parameter.eq('vix_implied_variance') & stability.period.eq('validation')]
    by_model=primary.set_index('model')
    effect=tests[(tests.target=='intraday') & (tests.challenger=='log_har_vix') & (tests.reference=='log_har')].iloc[0]
    changes_effect=tests[(tests.target=='intraday') & (tests.challenger=='log_har_vix_change') & (tests.reference=='log_har_vix')].iloc[0]
    m1_slices=slices[(slices.target=='intraday') & (slices.challenger=='log_har_vix') & (slices.reference=='log_har')].set_index('slice')
    quarters=m1_slices.loc[[f'2024_Q{i}' for i in range(1,5)]]
    availability=[]
    for (target,name),g in forecasts.groupby(['target','model']):
        missing=g.forecast_flag.fillna('').str.contains('Missing common origin features')
        other=(~g.forecast_valid) & ~missing & g.forecast_flag.ne('warmup')
        availability.append({'target':target,'model':name,'origins':len(g),'valid_predictions':int(g.forecast_valid.sum()),
            'common_evaluation_dates':int(g.common.sum()),'missing_origin_features':int(missing.sum()),
            'warmup_or_gap_reset':int(g.forecast_flag.eq('warmup').sum()),'other_prediction_failures':int(other.sum()),
            'unavailable_targets':int((~g.target_observed).sum())})
    availability=pd.DataFrame(availability)
    availability.to_csv(folder/'stage4b_availability.csv',index=False)
    conclusion=[
        '## Empirical interpretation — exploratory only',
        f"{primary.model.iloc[0]} has the lowest primary QLIKE. M1 minus M0 is {effect.mean_loss_difference:.6f}, "
        f"with pointwise bootstrap interval [{effect.ci_low:.6f}, {effect.ci_high:.6f}]. "
        f"None of the claims should be treated as independent confirmation; {int(tests.passes_exploratory_adjustment.sum())} "
        f"of {len(tests)} contrasts pass both multiplicity-adjusted checks in this run.",
        f"M1 improves the point-estimate QLIKE in {int(quarters.mean_loss_difference.lt(0).sum())} of four quarters, "
        f"but the magnitude is uneven. High-IV origins (n={int(m1_slices.loc['origin_high_iv','n'])}) have mean "
        f"M1−M0 difference {m1_slices.loc['origin_high_iv','mean_loss_difference']:.6f}; other-IV origins have "
        f"{m1_slices.loc['origin_other_iv','mean_loss_difference']:.6f}. After removing the retrospectively labelled "
        f"shock dates, the difference is {m1_slices.loc['without_retrospective_shocks','mean_loss_difference']:.6f}. "
        f"The five largest absolute daily loss differences contribute {effect.top5_share_absolute_loss_difference:.1%} "
        'of absolute paired differences. VIX has promising conditional information in this sample, but much of '
        'the apparent gain comes from a few high-risk events.',
        f"Adding the change feature gives M2−M1 difference {changes_effect.mean_loss_difference:.6f} "
        '(negative would favour the extra feature). It does not improve the aggregate point estimate in this run. '
        'Ridge smooths some coefficient and prediction movements but does not beat unregularized M1 by mean QLIKE.',
        f"Primary calibration is {by_model.loc['log_har_vix','calibration_ratio']:.6f} for M1, "
        f"{by_model.loc['log_har','calibration_ratio']:.6f} for M0, and "
        f"{by_model.loc['har','calibration_ratio']:.6f} for standard HAR. The archived levels HAR+VIX ratio is "
        f"{legacy[legacy.target.eq('intraday')].calibration_ratio.iloc[0]:.6f}. Positivity fixes the invalid-forecast "
        'mechanism, but does not improve average calibration: M1 still underpredicts aggregate variance. '
        'An apparently reasonable average calibration can conceal catastrophic individual floor losses.',
        'Recommended research candidates: keep M0 and standard HAR/RV-EWMA as references, and M1 as the '
        'simplest promising VIX challenger. Keep M3 as a prespecified stability comparator; M2 has no '
        'demonstrated incremental benefit here. No model is certified as a replacement. '
        'All six remain in the frozen prospective comparison set to avoid silently dropping unsuccessful variants.',
        '## Forecast availability, separate from positivity',table(availability),
        'Missing origin features and benchmark gap resets are data-availability losses, not optimizer failures. '
        'They remain in the all-attempt failure denominator. A positive-link forecast can be valid when its '
        'next target later proves unavailable; it is then retained but not scored. No synthetic forecast fills a gap.',
    ]
    lines=['# Positive VIX models — exploratory 2024 results',qualifier,
        '## Frozen specifications and estimation',
        'M0 Log-HAR: log RV, log arithmetic 5-session RV average, log arithmetic 22-session RV average. '
        'M1 adds log annualized IV. M2 adds one signed change in log IV. M3 uses M1 features with Ridge. '
        'Standard HAR and RV-EWMA remain benchmarks. All regressions use a 500-session-position window, '
        '126 completed pairs minimum and 21-session refits. Gaps are preserved. The original refit schedule '
        'is replayed for initialization; only 2024 forecasts are issued for the final six-model experiment.',
        'The additional full-session VIX lag is retained. Changes require two adjacent available lagged IV values; '
        'missing values are not filled or differenced across gaps. India VIX is annualized implied volatility over '
        'approximately 30 calendar days. Log IV is a regressor with an estimated coefficient, not a one-day variance observation.',
        'All five regressions use the same completed training pairs, including the original overnight-availability '
        'restriction and an additional VIX-change-availability mask. The mask is not a regressor. RV-EWMA smooths '
        'observed target variance with lambda .94 and a 22-observation initialization; matching its estimation '
        'observations to supervised regression pairs would change the benchmark. Evaluation dates are identical.',
        'Actual sample differences from Stage 4 are shown below. Numerical roundoff can change Log-HAR predictions '
        'at machine precision because retransformation uses logsumexp; changed samples, if any, are counted explicitly.',
        table(alignment),
        'Zero RV targets/features use 10^-6 times the positive training-target median only inside the log transformation. '
        'Positive small RV values are not clipped. Missing, negative or nonfinite RV and nonpositive IV are invalid. '
        'Observed outcomes are never replaced. Back-transformation is exp(predicted log variance + log training-residual '
        'smearing), computed stably with logsumexp. All log models use the same correction. '
        'This assumes a common residual distribution and is not a guarantee of conditional unbiasedness.',
        f'{len(positive)} issued usable log-model forecasts are strictly positive; '
        f'{int(positive.prediction_floored.sum())} use a prediction floor. Overflow, underflow and nonfinite '
        'predictions are missing failures, never clipped. The configured annualized-volatility ceiling rejects explosive '
        'forecasts rather than replacing them. Standard levels HAR retains its existing flagged floor policy; '
        'it is not a new positive-link model.',
        '## Development-only Ridge choice',table(selection),table(scores),
        'Each grid strength is evaluated chronologically in fixed September–October and November–December 2023 blocks. Scaling, coefficients, '
        'zero-RV transformation and smearing are refitted using only observations available at each origin. '
        'Selection minimizes the equally weighted fold mean QLIKE, requires at least 30 common observations per '
        'fold and no unexpected forecast failures, and chooses larger alpha only on an exact tie. '
        'Alpha is frozen before the first 2024 origin. Initial historical coefficient-state replay is not published '
        'as a forecast made before configuration selection. Ridge penalizes standardized slopes, not the intercept; '
        'its penalty convention is SSE + alpha times squared slope norm.',
        'A coverage-only protocol amendment preceded all new 2024 results: the original Q3/Q4 2023 '
        'split yielded only 15/61 usable observations and failed the fixed 30-per-fold gate. '
        'The preserved aborted registration is b5441dbe33562a1781aae56f. The revised blocks provide 35/41 '
        'observations on the actual sample. The same four Ridge strengths were used; no development loss values '
        'were inspected to choose new boundaries. Two fold designs were considered and four primary-target '
        'grid runs were aborted before the final eight target/alpha grid runs. These are repeated configurations, '
        'not four additional distinct models. Only 76 development evaluation dates support tuning, so the choice '
        'of penalty is uncertain and must not be described as a robust optimum.',
        '## Primary target: 5-minute intraday RV',table(primary[cols]),
        '## Secondary target: intraday RV + overnight square',table(secondary[cols]),
        'Targets are distinct; their QLIKE levels must not be pooled or ranked across targets. '
        'Calibration is mean observed / mean predicted variance; ideal is one. A good QLIKE does not guarantee '
        'good aggregate calibration. Forecast distributions, positivity counts and failures appear in stage4b_comparison.csv.',
        '## Original unsuccessful levels comparator — archived predictions, no new ranking',
        table(legacy[['target','model','n_evaluated','qlike','calibration_ratio','prediction_floor_count']]),
        'The legacy predictions are copied unchanged from Stage 4. They do not determine the six-model common-date '
        'sample, and they receive no new rank. Their own training rows may differ if the new change-availability '
        'mask excludes observations. The legacy event file retains every original matched event.',
        '## Paired uncertainty and research-selection limits',
        table(tests[['target','challenger','reference','n','mean_loss_difference','ci_low','ci_high',
                     'hac_p_holm','bootstrap_p_holm','passes_exploratory_adjustment','top5_share_absolute_loss_difference']]),
        f"The workflow tried {manifest['configuration_counts']['distinct_model_target_configurations']} distinct model/target "
        f"configurations: {manifest['configuration_counts']['ridge_grid_candidates']} Ridge grid candidates plus five fixed "
        f"specifications per target. It produced {manifest['configuration_counts']['final_model_target_cells']} final cells, "
        f"tested {len(tests)} predefined loss contrasts and inspected {len(floors)} legacy floor counterfactuals. "
        'There are no additional inferential quarter/regime tests. The original Stage 4 search and 2024-driven '
        'specification selection are additional research exposure; current Holm adjustment cannot undo that selection.',
        'HAC uses native session positions; stationary bootstrap blocks restart across gaps. Bootstrap uses '
        '10,000 draws, expected block length 10 and the recorded seed. Intervals are pointwise approximate 95% '
        'intervals. Holm covers all five contrasts on both targets jointly (10 comparisons), separately for HAC '
        'and bootstrap; the reported adjustment flag requires both. Even a passing flag is exploratory.',
        'The interval is a percentile-style bootstrap summary, whereas the bootstrap p-value uses an absolute '
        'centered statistic. Under skewness these need not invert exactly; report both rather than inferring '
        'significance from an interval alone.',
        '## VIX increments, quarters and event concentration',
        table(slices[(slices.target=='intraday') & slices['slice'].isin(['origin_high_iv','origin_other_iv',
              'origin_rapid_iv_change','without_retrospective_shocks','2024_Q1','2024_Q2','2024_Q3','2024_Q4'])]),
        'High-IV regimes use the 75th percentile of strictly earlier available lagged IV, with at least 60 prior '
        'observations. Rapid-change regimes likewise use past thresholds. These are origin-known classifications. '
        'Shock exclusions and event windows are retrospective diagnostics only; they never enter feature selection '
        'or a prospective decision rule. The top-five concentration is a share of absolute paired loss differences, '
        'not a signed gain share. M2 versus M1 directly tests the extra change feature.',
        '## Coefficient and forecast stability',table(stability_subset),
        'These VIX coefficients are slopes on log implied variance and can be compared between the positive-link '
        'models; they cannot be compared numerically with levels-HAR slopes in raw variance units. Training centers, '
        'scales, standardized coefficients, rank and condition diagnostics are saved per fit. Ridge may shrink '
        'coefficients without improving QLIKE; stability and accuracy are reported separately.',
        f'Largest regression training sample: {n_unique_training} completed pairs. '
        'A single reused validation year and a small development window limit statistical power. '
        'Complete short special sessions remain unscaled; no session-duration regressor was added. '
        'Provenance remains the principal barrier to certified research use.',source]
    lines[2:2]=conclusion
    figures=make_plots(folder/'figures/stage4b',forecasts,events,coefficients,floors) if make_figures else []
    lines.extend(['## Figures']+[f'![{name}](figures/stage4b/{name})' for name in figures])
    write_text('\n\n'.join(lines)+'\n',folder/'positive_vix_models.md')

    manifest['protocol_frozen_at_utc']=datetime.now(timezone.utc).isoformat()
    protocol=['# Frozen forecasting protocol — subsequent prospective evaluation',
        f"Protocol frozen with Stage 4B run `{manifest['run_id']}` at {manifest['protocol_frozen_at_utc']}. "
        'It was designed after exploratory 2024 analysis. It does not retroactively make 2024 independent.',
        '## Scope and candidates',
        'NIFTY NSE spot. Primary target: next-session complete 5-minute intraday realized variance. '
        'Secondary target: that RV plus adjacent valid overnight squared log return, scored separately. '
        'Candidates: RV-EWMA, standard HAR, Log-HAR M0, Log-HAR+VIX M1, Log-HAR+VIX-change M2, Ridge M3. '
        'Retain all six as the frozen comparison set; the original negative levels HAR+VIX is an archived '
        'unsuccessful diagnostic comparator, not a prospective candidate. No portfolio or trading study is authorized.',
        '## Fixed model specification',
        'Use the exact feature definitions, 500-position window, 126-pair minimum, 21-session refits, '
        'training-only zero-RV treatment, standardized Ridge objective and residual-smearing correction recorded '
        'in this run. Keep the additional full-session VIX lag. Freeze the selected penalties below; '
        'do not retune them on 2024 or the prospective evaluation. Maintain the native session grid and '
        'common regression training pairs. Retain all attempted predictions and common-date comparisons.',table(selection),
        '## Required provenance and quality gates',
        'Before registration of the evaluation start, obtain source/export documentation identifying vendor/API, '
        'NSE spot instrument (not futures/TRI), original timezone, daylight/timestamp handling, start/end bar labels, '
        'OHLC construction and availability times. Independently reconcile sample prices/bars with exchange or '
        'documented vendor evidence; resolve quarantined/conflicting records and special-session calendars. '
        'Document licensing and data vintage. Numerical checks must pass session completeness, no cross-session '
        'intraday returns, RV reconciliation, adjacent overnight endpoints and causal VIX availability. '
        'An extra VIX lag does not certify source conventions.',
        'A corrected source vintage may change RV/feature values. That requires a new development-only audit and '
        'a new protocol version frozen before future collection begins. Preserve this protocol and all old results; '
        'do not silently reinterpret provisional numbers as verified.',
        '## Obtaining genuinely unseen data',
        'Do not use 2025–2026 as a pristine holdout: earlier project research exposed some observations. '
        'This workflow has not read them. Instead, after provenance sign-off and timestamped protocol/hash '
        'registration, start at the first scheduled NSE session strictly after both events. Collect new data '
        'as it is released, with immutable retrieval and availability timestamps. Publish each forecast to an '
        'append-only local ledger before the target session opens. No future-period evaluation is run by Stage 4B.',
        'Evaluate exactly the first 252 scheduled sessions after that start. Require at least 200 matched eligible '
        'dates for the primary conclusion; otherwise declare the result inconclusive. Never extend or stop the '
        'period based on forecast losses. Restrict interim monitoring to data integrity and operational failures, '
        'without model ranking or outcome-driven specification changes.',
        '## Statistical and selection policy',
        'Primary contrasts: M1−M0, M2−M0 and M3−M0. Secondary contrasts: M1−RV-EWMA and M2−M1. '
        'Apply the same five to the separate overnight-inclusive target; Holm-adjust all ten jointly. '
        'Use mean QLIKE as the primary loss, with MSE/MAE, bias, observed/predicted calibration, positivity, '
        'availability and computational cost as diagnostics. Use the saved gap-aware HAC and 10,000-draw '
        'stationary bootstrap, block length 10, seed 20261103. Report pointwise intervals and both adjusted p-values.',
        'Retain M0 unless a challenger has lower primary mean QLIKE and both adjusted p-values below .05, '
        'no invalid positive-link predictions on otherwise eligible origins, and aggregate calibration at least '
        'as close to one in absolute log distance as M0. If multiple challengers satisfy these rules, prefer '
        'the smaller feature set; if still tied, prefer lower primary QLIKE. If none qualifies, report no '
        'established replacement. Secondary-target gains alone do not select the primary model. '
        'No risk-management or portfolio benefit may be inferred from this test.',
        '## Failure handling and regime rules',
        'No interpolation, artificial forecasts, winsorization, automatic crisis deletion or fallback model. '
        'Reject nonfinite/underflowed predictions and annualized volatility above the fixed 5.0 ceiling; '
        'record each failure and exclude only from matched scoring, while reporting its full failure rate. '
        'Any positive-link invalid prediction disqualifies promotion under this protocol. '
        'Standard HAR retains its flagged training-derived floor policy and its floor count must be reported. '
        'Insufficient history remains warm-up. Preserve missing session rows and their effect on feature windows. '
        'Origin-known IV regimes may be reported descriptively; no regime-based switching rule is introduced. '
        'Retrospective shock labels and quarter comparisons never become prospective selection rules.',
        'The saved run registration, configuration, source snapshot and manifests identify this protocol. '
        'Any amendment requires a new timestamped version before unseen evaluation begins. No future evaluation '
        'or data acquisition is scheduled or executed by this command.']
    write_text('\n\n'.join(protocol)+'\n',folder/'frozen_forecasting_protocol.md')
    winners={target:{'model':g.sort_values('qlike').model.iloc[0],
                     'qlike':float(g.qlike.min()),'n':int(g.n_evaluated.iloc[0])}
             for target,g in common.groupby('target')}
    return {'exploratory_rankings':winners,'negative_legacy_predictions':len(neg),
            'new_log_forecast_floors':int(positive.prediction_floored.sum()),
            'adjusted_exploratory_flags':int(tests.passes_exploratory_adjustment.sum()),
            'independent_confirmation':False,'figures':figures}
