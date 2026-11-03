"""Stage 3 evidence tables and figures, derived only from the evaluated run."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from volrisk.data.storage import write_text
from volrisk.evaluation.reporting import markdown_table


PROTOCOL = '''## Research protocol and earlier-run limitations

This run excludes holdout observations before fitting, prediction, losses and diagnostics.
Development ends 2021-12-31; validation covers 2022-2024. XGBoost hyperparameter searches use
chronological folds of labels already known at the origin and stop at the configured development
cutoff. Refits during validation update model weights/parameters using past observations; they do
not select hyperparameters. No models pool observations across assets.

The previous Stage 2 runner only filtered the summary tables: it generated holdout forecasts and
losses and published holdout fit diagnostics. Its research narrative discussed those failures.
Consequently the old holdout cannot honestly be described as completely untouched. No historical
exposure is undone by this fix. A genuinely fresh final confirmation needs subsequently unseen
data or a new predeclared holdout. This run performs no holdout scoring or model selection on it.

Canonical file hashes and numerical/source audit results are checked. Calendar-unverified
intervals are excluded from this experiment without modifying canonical/source files. Training
restarts after an interior gap; no model or supervised pair bridges it. This changes the NIFTY
comparison sample relative to Stage 2, so all ten comparators are rerun alongside the challengers.
The archived datasets retain statistical extreme-return review warnings; genuine large market
moves are neither clipped nor deleted. Empirical comparisons remain qualified by those warnings
and current-vintage source limitations; this is not unconditional data certification.

Squared daily log returns are noisy variance proxies under the common zero-mean convention.
QLIKE ranks are within asset and period. Development results include hyperparameter selection
and are exploratory; validation is the main selection evidence. Bootstrap intervals are pointwise;
Holm corrections apply to benchmark-test p-values within asset/period, and separately to all
pairwise DM p-values within asset/period. Tests do not eliminate model-search uncertainty.
'''


def _table(frame, columns):
    scaling = {'mse': 1e8, 'mae': 1e4, 'bias': 1e4}
    return markdown_table(frame, [(c, c.replace('_', ' ') + (f' (x{scaling[c]:.0e})' if c in scaling else ''),
                                  {'digits': 4, 'scale': scaling.get(c, 1.)}) for c in columns])


def write_advanced_reports(run_dir: Path, manifest, forecasts, fits, metrics, tests, regimes, *, figures=True):
    """Write the requested Stage 3 reports without replacing Stage 2 publication."""
    families = {m['name']: m['family'] for m in manifest['models']}
    markov_names = [n for n, family in families.items() if family == 'regime_switching']
    ml_names = [n for n, family in families.items() if family == 'machine_learning']
    challengers = markov_names + ml_names
    common = forecasts[forecasts.common.astype(bool)].copy()
    selected_metrics = metrics[(metrics['sample'] == 'common') & metrics.period.eq('validation')]
    lines = ['# Advanced volatility model comparison — Stage 3', '',
             f"Run: `{manifest['run_id']}`. Modeling cutoff: {manifest['modeling_data_cutoff']}.", '', PROTOCOL, '',
             '## Validation-period evidence', '']
    for asset, rows in selected_metrics.groupby('asset', sort=True):
        baseline = rows[~rows.model.isin(challengers)].sort_values('qlike')
        lines += [f'### {asset}', '',
                  _table(rows.sort_values('qlike'), ['model', 'n_evaluated', 'qlike', 'mse', 'mae',
                      'calibration_ratio', 'bias', 'fit_failure_rate', 'runtime_seconds', 'rank_qlike']), '']
        if not baseline.empty:
            best = baseline.iloc[0]
            lines.append(f"Best incumbent by validation QLIKE: {best.model} ({best.qlike:.5f}).")
            for name in challengers:
                candidate = rows[rows.model.eq(name)]
                if candidate.empty:
                    lines.append(f'{name}: no common-date validation results available.')
                    continue
                row = candidate.iloc[0]
                lines.append(f'- {name}: QLIKE difference vs best incumbent {row.qlike-best.qlike:+.5f}; '
                             f'calibration {row.calibration_ratio:.3f}; rank {int(row.rank_qlike)} of {len(rows)}.')
        evidence = tests[tests.asset.eq(asset) & tests.period.eq('validation') & tests.model.isin(challengers)] if not tests.empty else pd.DataFrame()
        if not evidence.empty:
            lines += ['', 'Paired comparison against the prespecified GARCH-normal reference:', '',
                _table(evidence, ['model', 'mean_loss_diff', 'boot_ci_low', 'boot_ci_high', 'dm_p_holm', 'boot_p_holm']), '']
            for row in evidence.itertuples():
                direction = 'lower' if row.mean_loss_diff < 0 else 'higher'
                supported = bool(row.significant_holm_5pct)
                lines.append(f'{row.model} has {direction} mean QLIKE than the reference; '
                             f'{"both adjusted tests reject equality" if supported else "the two adjusted tests do not jointly establish a difference"}.')
        lines.append('')

    # Reaction to an observed shock is the forecast CHANGE at the next origin.
    # This is different from claiming to predict the previously unseen shock.
    responses = []
    for (asset, model), group in forecasts.groupby(['asset', 'model'], sort=True):
        rows = group.sort_values('origin_date').reset_index(drop=True)
        for i in range(len(rows)-1):
            before, after = rows.iloc[i], rows.iloc[i+1]
            if (bool(before.shock) and bool(before.common) and bool(after.common)
                    and after.origin_date == before.target_date and before.forecast_variance > 0):
                responses.append({'asset': asset, 'model': model, 'shock_session': before.target_date,
                    'variance_before_shock': before.forecast_variance, 'variance_after_observation': after.forecast_variance,
                    'response_ratio': after.forecast_variance/before.forecast_variance})
    response_frame = pd.DataFrame(responses, columns=['asset', 'model', 'shock_session', 'variance_before_shock',
                                                     'variance_after_observation', 'response_ratio'])
    response_frame.to_csv(run_dir/'shock_response.csv', index=False)
    response_summary = response_frame.groupby(['asset', 'model']).response_ratio.agg(['count', 'median', 'mean']).reset_index()
    lines += ['## Shock response, overreaction and model complexity', '',
        'The response table measures the change in next-session forecast variance after a retrospectively identified shock becomes observable. '
        'A larger response is faster adjustment, not evidence of better advance prediction or more reliable latent-regime detection. '
        'There is no observed ground truth for latent regimes in daily closes.', '',
        _table(response_summary, ['asset', 'model', 'count', 'median', 'mean']), '',
        'Recovery calibration below 1 indicates aggregate overforecasting in the labelled recovery subset; it does not prove that an individual shock was transient. '
        'Shock/recovery results are descriptive, involve small and sometimes overlapping event samples, and are not used for hyperparameter tuning.', '']
    recovery = regimes[regimes.regime_label.eq('post_shock_recovery')] if not regimes.empty else pd.DataFrame()
    if not recovery.empty:
        lines += [_table(recovery, ['asset', 'model', 'n_evaluated', 'qlike', 'calibration_ratio']), '']
    lines += ['## Research interpretation', '',
        '- Regime switching versus GARCH is assessed per asset using the validation differences and paired tests above. State probabilities describe the fitted model, not verified economic regimes.',
        '- XGBoost can represent nonlinear feature interactions, but predictive gains must appear in matched-date validation losses. Feature importance alone cannot establish that it captured missing economic mechanisms.',
        '- Cross-market consistency requires improvement on all three separate asset comparisons; pooled loss levels are not used.',
        '- Small ranks or loss differences without corrected statistical support do not establish superiority. Validation used for selection cannot later be relabelled an untouched final test.',
        '- Maintenance costs include optimization failures/weak state separation for Markov switching and repeated training/tuning, feature-version control and drift for XGBoost. Runtime and failure rates must be considered alongside forecast losses.',
        '- Stage 3 ends at forecasting. No position sizing, Heston, HAR-RV, LSTM or Transformer was implemented.', '',
        '## Complete tables and reproducibility', '',
        'The full model/period/sample tables follow. Detailed uncertainty, regime, state and feature outputs are stored in this immutable run. '
        'All-available forecasts and common-date flags are both retained in Parquet; missing forecasts are not filled.', '',
        '```powershell', r'.\.venv\Scripts\python.exe -m volrisk.forecast_cli --config config/forecasting.toml run --experiment advanced --workers 4',
        r"$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'", r'.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-advanced.xml', '```', '']
    generic = (run_dir/'model_comparison.md').read_text(encoding='utf-8')
    write_text('\n'.join(lines)+'\n'+generic, run_dir/'advanced_model_comparison.md')
    metrics.to_csv(run_dir/'advanced_model_metrics.csv', index=False)

    states, importances, tuning = [], [], []
    for row in forecasts[forecasts.model.isin(markov_names)].itertuples():
        state = json.loads(row.model_state)
        if state:
            states.append({'asset': row.asset, 'model': row.model, 'origin_date': row.origin_date,
                'target_date': row.target_date, 'period': row.period, 'fit_status': row.fit_status,
                'filtered_probability_high': state['filtered_probability_high'],
                'predictive_probability_high': state['predictive_probability_high'],
                'variance_low': state['state_variances'][0], 'variance_high': state['state_variances'][1]})
    for row in fits[fits.model.isin(ml_names) & fits.status.ne('failed')].itertuples():
        diag = json.loads(row.diagnostics)
        for feature, importance in diag.get('feature_importance_gain_normalized', {}).items():
            importances.append({'asset': row.asset, 'model': row.model, 'fit_date': row.origin_date,
                                'feature': feature, 'normalized_gain': importance})
        for candidate in diag.get('tuning_candidates', []):
            tuning.append({'asset': row.asset, 'model': row.model, 'tuning_date': row.origin_date,
                'hyperparameters': json.dumps(candidate['hyperparameters'], sort_keys=True),
                'mean_cv_qlike': candidate['mean_qlike'], 'error': candidate['error'],
                'folds': json.dumps(candidate['folds'], sort_keys=True)})
    states = pd.DataFrame(states)
    importance = pd.DataFrame(importances)
    pd.DataFrame(tuning).to_csv(run_dir/'xgboost_tuning.csv', index=False)
    importance.to_csv(run_dir/'xgboost_feature_importance.csv', index=False)
    states.to_csv(run_dir/'regime_probabilities.csv', index=False)
    regime_lines = ['# Filtered Markov-switching regime analysis', '',
        'Zero-mean Gaussian observations; states reordered by ascending variance on every training-window refit. '
        'Forecast probabilities equal filtered probabilities multiplied by the estimated row-stochastic transition matrix. '
        'No full-sample smoothed states enter the forecasting path. EM initialization may smooth within the permissible training window only.', '',
        'State shares and transitions below describe the fitted filter. They are not latent-state classification accuracy. '
        'Near-boundary transitions, weak occupancy and insufficient variance separation remain visible as fit warnings.', '']
    if not states.empty:
        summaries = []
        for (asset, model, period), rows in states.groupby(['asset', 'model', 'period']):
            if period not in manifest['periods_evaluated']:
                continue
            high = rows.filtered_probability_high.ge(.5)
            summaries.append({'asset': asset, 'model': model, 'period': period, 'origins': len(rows),
                'high_state_share': high.mean(), 'classification_changes': int(high.astype(int).diff().abs().sum()),
                'mean_variance_ratio': (rows.variance_high/rows.variance_low).mean()})
        regime_lines += [_table(pd.DataFrame(summaries), ['asset', 'model', 'period', 'origins', 'high_state_share',
                                                         'classification_changes', 'mean_variance_ratio']), '']
    regime_lines += ['Refits may change classifications and state variances discontinuously. Inspect `fits.parquet` for transition estimates, '
        'expected durations, convergence attempts and boundary flags; `regime_probabilities.csv` records saved origin-time states.', '',
        '[statsmodels MarkovRegression documentation](https://www.statsmodels.org/stable/generated/statsmodels.tsa.regime_switching.markov_regression.MarkovRegression.html)', '']
    write_text('\n'.join(regime_lines), run_dir/'regime_analysis.md')

    feature_lines = ['# XGBoost variance forecasting and feature evidence', '',
        'The target is next-session squared decimal log return. Features at origin t use observations through t only. '
        'Training ends with feature row t-1 and label r_t². The current origin row has no known next-session training label.', '',
        'Features: squared/absolute current and preceding returns, 5/20/60-session sample variance (ddof=1), '
        'EWMA (lambda .94; first 20 squared returns initialize its mean), negative-return indicators/counts, '
        'variance differences, and trailing 60-session log drawdown. These daily-price features are not intraday realized variance.', '',
        'Tweedie objective with variance power 1.5 and log link predicts a positive conditional mean of a nonnegative target. '
        'Targets are multiplied by 10,000 for optimization; predictions are divided by that scale. '
        'No naive exponentiation of a log-target regression is used. A configurable 1e-10 decimal-variance floor is recorded per prediction; '
        'nonfinite or negative predictions fail explicitly. Trees require no fitted feature standardizer.', '',
        'The predefined depth/tree-count grid is selected with chronological blocked validation on labels already known at the origin, '
        'retuned at most every 252 observations during development, then frozen. Model weights refit every 21 observations. '
        'Each asset has independent training and selection. CPU histogram trees use one thread and a fixed seed.', '',
        'Importance is normalized split gain from each fitted booster, averaged across refits. It is training-set model importance, '
        'not causal importance or out-of-sample permutation evidence; correlated features can share or substitute importance.', '']
    if not importance.empty:
        means = importance.groupby(['asset', 'feature']).normalized_gain.mean().reset_index()
        for asset, rows in means.groupby('asset'):
            feature_lines += [f'## {asset}', '', _table(rows.sort_values('normalized_gain', ascending=False), ['feature', 'normalized_gain']), '']
    clipped = []
    for (asset, model), rows in forecasts[forecasts.model.isin(ml_names)].groupby(['asset', 'model']):
        states_ml = rows.model_state.apply(json.loads)
        clipped.append({'asset': asset, 'model': model, 'origins': len(rows),
            'clipped_predictions': sum(bool(s.get('prediction_clipped', False)) for s in states_ml),
            'missing_forecasts': int((~rows.forecast_valid.astype(bool)).sum())})
    if clipped:
        feature_lines += ['## Prediction safeguards', '', _table(pd.DataFrame(clipped), ['asset', 'model', 'origins', 'clipped_predictions', 'missing_forecasts']), '']
    feature_lines += ['Exact search outcomes/fold boundaries are in `xgboost_tuning.csv`; fitted parameters and booster hashes are in '
        '`fits.parquet`. All trees can be reproduced from the archived data hashes, code hashes, model configuration, seeds and package versions.', '',
        '[XGBoost objective and parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html)', '']
    write_text('\n'.join(feature_lines), run_dir/'xgboost_features.md')

    paths = []
    if figures:
        directory = run_dir/'figures'
        directory.mkdir(exist_ok=True)
        for asset, rows in states.groupby('asset') if not states.empty else []:
            fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
            axes[0].plot(rows.origin_date, rows.filtered_probability_high, lw=.7, label='Filtered high-state probability at origin')
            axes[0].plot(rows.origin_date, rows.predictive_probability_high, lw=.6, alpha=.7, label='Predictive high-state probability for next session')
            axes[0].set(ylim=(-.02, 1.02), ylabel='Probability', title=f'{asset}: filtered regime state; development/validation only')
            axes[0].legend(fontsize=8)
            for col, label in [('variance_low', 'Low state'), ('variance_high', 'High state')]:
                axes[1].plot(rows.origin_date, np.sqrt(rows[col]*252)*100, lw=.7, label=label)
            axes[1].set(ylabel='State annualized volatility (%)', xlabel='Forecast origin session')
            axes[1].legend(fontsize=8)
            fig.tight_layout()
            path = directory/f'{asset}_filtered_regimes.png'
            fig.savefig(path, dpi=140)
            plt.close(fig)
            paths.append(path)
        if not importance.empty:
            for asset, rows in importance.groupby('asset'):
                mean = rows.groupby('feature').normalized_gain.mean().sort_values()
                fig, ax = plt.subplots(figsize=(9, 6))
                ax.barh(mean.index, mean.values, color='#167b86')
                ax.set(title=f'{asset}: XGBoost split gain averaged across refits', xlabel='Normalized gain (not causal importance)')
                fig.tight_layout()
                path = directory/f'{asset}_xgboost_gain.png'
                fig.savefig(path, dpi=140)
                plt.close(fig)
                paths.append(path)
    return paths
