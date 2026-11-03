"""Predefined positive-VIX follow-up. Development tuning; explored-2024 evaluation only."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd

from volrisk.forecasting.registry import build_model
from volrisk.forecasting.positive_har import COMMON, positive_features
from .har_walk_forward import walk_forward, common_dates
from .har_metrics import (attach_har_losses, attach_regimes, summarize_har, paired_inference,
                          parameter_stability)
from .metrics import holm_adjust

NAMES = ('rv_ewma', 'har', 'log_har', 'log_har_vix', 'log_har_vix_change', 'ridge_log_har_vix')
STATUS = 'PROVISIONAL_EXPLORATORY'


def specifications(config, target, alpha, available_on=None):
    shared = {k: config['estimation'][k] for k in ('window', 'min_observations', 'refit_every',
                                                 'floor_fraction', 'log_bias_correction')}
    shared.update(target=target, common_columns=COMMON)
    positive = dict(type='positive_har', **shared)
    specs = {
        'rv_ewma': {'type': 'rv_benchmark', 'target': target, 'method': 'ewma', 'decay': .94, 'init_window': 22},
        'har': {'type': 'har_rv', **shared},
        'log_har': {**positive, 'vix': False},
        'log_har_vix': {**positive, 'vix': True},
        'log_har_vix_change': {**positive, 'vix': True, 'vix_change': True},
        'ridge_log_har_vix': {**positive, 'vix': True, 'ridge_alpha': float(alpha)},
    }
    if available_on is not None:
        specs['ridge_log_har_vix']['configuration_available_on'] = str(pd.Timestamp(available_on).date())
    return specs


def tune_ridge(panel, config, target, splits):
    cutoff = pd.Timestamp(config['tuning']['cutoff'])
    if cutoff > splits.development[1] or cutoff >= splits.validation[0]:
        raise ValueError('Ridge tuning must end within development, before validation')
    data = panel.loc[panel.index <= cutoff].copy()  # Before features, training or targets.
    folds = [(pd.Timestamp(a), pd.Timestamp(b)) for a,b in config['tuning']['folds']]
    if not folds or any(a>b or b>cutoff or a<splits.development[0] for a,b in folds):
        raise ValueError('Invalid chronological development folds')
    if any(folds[i][1] >= folds[i+1][0] for i in range(len(folds)-1)):
        raise ValueError('Tuning folds must be ordered and disjoint')
    frames, fit_frames = [], []
    alphas = config['tuning']['alphas']
    if len(set(alphas)) != len(alphas) or not all(np.isfinite(a) and a>0 for a in alphas):
        raise ValueError('Ridge grid must contain distinct positive finite strengths')
    for alpha in alphas:
        name = f'ridge_alpha_{alpha:g}'
        spec = specifications(config, target, alpha)['ridge_log_har_vix']
        f, fit = walk_forward(data, build_model(name, spec), target=target, splits=splits,
                             feature_builder=positive_features, emit_from=folds[0][0],
                             max_annualized_vol=config['estimation']['max_annualized_vol'])
        f['ridge_alpha'] = float(alpha)
        fit['ridge_alpha'] = float(alpha)
        frames.append(f); fit_frames.append(fit)
    all_forecasts = attach_har_losses(common_dates(pd.concat(frames, ignore_index=True),
                                                   [f'ridge_alpha_{a:g}' for a in alphas]))
    all_fits = pd.concat(fit_frames, ignore_index=True)
    features = positive_features(data)
    origin_valid = np.isfinite(features[COMMON]).all(axis=1)
    completed = origin_valid.shift(fill_value=False) & data[target].notna()
    ready = completed.rolling(config['estimation']['window'], min_periods=1).sum() >= config['estimation']['min_observations']
    rows = []
    for alpha in alphas:
        g = all_forecasts[all_forecasts.ridge_alpha.eq(alpha)]
        for i, (start, end) in enumerate(folds):
            s = g[g.target_date.between(start, end)]
            expected = origin_valid.reindex(s.origin_date).to_numpy() & ready.reindex(s.origin_date).to_numpy() & s.target_observed.to_numpy()
            failed = int((expected & ~s.forecast_valid.to_numpy()).sum())
            valid = s[s.common]
            rows.append({'target': target, 'ridge_alpha': float(alpha), 'fold': i+1,
                         'fold_start': start, 'fold_end': end, 'n_common': len(valid),
                         'qlike': valid.loss_qlike.mean(), 'unexpected_failures': failed,
                         'first_target': valid.target_date.min(), 'last_target': valid.target_date.max()})
    scores = pd.DataFrame(rows)
    eligible = scores.groupby('ridge_alpha').agg(score=('qlike','mean'), min_n=('n_common','min'),
                                                failures=('unexpected_failures','sum'))
    eligible = eligible[(eligible.min_n >= config['tuning']['minimum_fold_observations']) & eligible.failures.eq(0) & np.isfinite(eligible.score)]
    if eligible.empty:
        raise ValueError('Insufficient valid development folds; Ridge cannot be selected')
    best = eligible.reset_index().sort_values(['score','ridge_alpha'], ascending=[True,False]).iloc[0]
    chosen = float(best.ridge_alpha)
    scores['selected'] = scores.ridge_alpha.eq(chosen)
    selected_dates = all_forecasts.loc[all_forecasts.common & all_forecasts.target_date.le(cutoff), 'target_date']
    if selected_dates.empty:
        raise ValueError('No observed development selection targets')
    selection = {'target': target, 'alpha': chosen, 'selection_available_on': str(selected_dates.max().date()),
                 'tuning_cutoff': str(cutoff.date()), 'score': float(best.score),
                 'criterion': config['tuning']['selection'], 'grid_size': len(alphas)}
    return selection, scores, all_forecasts, all_fits


def evaluate_models(panel, config, target, selection, splits, save_forecast=None):
    start = pd.Timestamp(config['evaluation']['start'])
    end = pd.Timestamp(config['evaluation']['end'])
    data = panel.loc[panel.index <= min(end, splits.validation[1])].copy()
    specs = specifications(config, target, selection['alpha'], selection['selection_available_on'])
    first_target_position = int(data.index.searchsorted(start))
    if first_target_position < 1 or pd.Timestamp(selection['selection_available_on']) > data.index[first_target_position-1]:
        raise ValueError('Ridge selection was not available at the first evaluation origin')
    frames, fit_frames = [], []
    for name, spec in specs.items():
        f, fits = walk_forward(data, build_model(name,spec), target=target, splits=splits,
                              feature_builder=positive_features, emit_from=start,
                              max_annualized_vol=config['estimation']['max_annualized_vol'],
                              save_forecast=save_forecast)
        f['configuration_available_on'] = selection['selection_available_on'] if name.startswith('ridge') else None
        fits['configuration_available_on'] = selection['selection_available_on'] if name.startswith('ridge') else None
        fits['initialization_only'] = fits.target_date.lt(start)
        for frame in (f, fits):
            frame['frequency']=5; frame['scenario']='eligible'; frame['research_status']=STATUS
        frames.append(f); fit_frames.append(fits)
    forecasts = attach_regimes(attach_har_losses(common_dates(pd.concat(frames,ignore_index=True), NAMES)), data, config['evaluation'])
    # High-IV threshold uses only earlier values of the already lagged, available IV series.
    iv = data.vix_implied_variance
    threshold = iv.expanding(min_periods=config['evaluation']['regime_min_history']).quantile(config['evaluation']['vix_high_past_quantile']).shift()
    known = iv.notna() & threshold.notna()
    labels = pd.Series('unknown', index=data.index)
    labels.loc[known & iv.gt(threshold)]='high'
    labels.loc[known & iv.le(threshold)]='other'
    forecasts['origin_iv_regime']=labels.reindex(forecasts.origin_date).to_numpy()
    fits = pd.concat(fit_frames, ignore_index=True)
    # Regression rows, coefficient refit origins and training targets must match for all five regressions.
    reg = fits[fits.model.ne('rv_ewma') & fits.status.ne('failed')]
    for _,g in reg.groupby('origin_date'):
        dates = [tuple(json.loads(d)['training_target_dates']) for d in g.diagnostics]
        if len(g)!=5 or len(set(dates))!=1:
            raise AssertionError('Regression training sample/refit mismatch')
    return forecasts, fits, specs


def compare_models(forecasts, fits, config):
    metrics = summarize_har(forecasts, fits)
    metrics['status']=STATUS
    metrics['comparison_group']='six_predefined_models'
    distribution = []
    for (target,model), g in forecasts.groupby(['target','model']):
        h = g.loc[g.common, 'forecast_variance']
        distribution.append({'target':target,'model':model,'forecast_min':h.min(),
            'forecast_p01':h.quantile(.01),'forecast_median':h.median(),'forecast_p99':h.quantile(.99),
            'forecast_max':h.max(),'nonpositive_valid_predictions':int((h<=0).sum()),
            'nonfinite_valid_predictions':int((~np.isfinite(h)).sum())})
    metrics=metrics.merge(pd.DataFrame(distribution),on=['target','model'],how='left',validate='many_to_one')
    tests, slices = [], []
    for target, g in forecasts[forecasts.common].groupby('target'):
        wide = g.pivot(index=['origin_index','target_date'], columns='model', values='loss_qlike').sort_index()
        for challenger, reference in config['evaluation']['pairs']:
            d = wide[challenger]-wide[reference]
            info = paired_inference(d, wide.index.get_level_values('origin_index'),
                draws=config['evaluation']['bootstrap_draws'], block=config['evaluation']['bootstrap_block'],
                seed=config['evaluation']['seed'], min_n=config['evaluation']['minimum_inference_observations'])
            ref = g[g.model.eq(reference)].set_index('target_date').reindex(wide.index.get_level_values('target_date'))
            total = float(d.abs().sum())
            masks = {'all':np.ones(len(d),dtype=bool), 'origin_high_iv':ref.origin_iv_regime.eq('high').to_numpy(),
                     'origin_other_iv':ref.origin_iv_regime.eq('other').to_numpy(),
                     'origin_rapid_iv_change':ref.origin_rapid_vix_change.to_numpy(dtype=bool),
                     'retrospective_shock':ref.retrospective_shock.to_numpy(dtype=bool),
                     'without_retrospective_shocks':~ref.retrospective_shock.to_numpy(dtype=bool),
                     **{f'2024_Q{q}':ref.index.quarter==q for q in (1,2,3,4)}}
            for label,mask in masks.items():
                slices.append({'target':target,'challenger':challenger,'reference':reference,'slice':label,
                               'n':int(mask.sum()),'mean_loss_difference':float(d.to_numpy()[mask].mean()) if mask.any() else np.nan,
                               'status':STATUS,'inferential_test':False})
            tests.append({'target':target,'challenger':challenger,'reference':reference,**info,
                          'top5_share_absolute_loss_difference':float(d.abs().nlargest(5).sum()/total) if total else np.nan,
                          'status':STATUS})
    tests = pd.DataFrame(tests)
    tests['hac_p_holm']=holm_adjust(tests.hac_p_value)
    tests['bootstrap_p_holm']=holm_adjust(tests.bootstrap_p_value)
    tests['passes_exploratory_adjustment']=(tests.hac_p_holm<config['evaluation']['alpha']) & (tests.bootstrap_p_holm<config['evaluation']['alpha'])
    tests['independent_confirmation']=False
    stability = parameter_stability(fits)
    stability['status']=STATUS
    return metrics,tests,pd.DataFrame(slices),stability


def sample_alignment(forecasts, fits, old_forecasts, old_fits):
    """Actual old/new differences; no assumption that a new mask preserves observations."""
    rows=[]
    for target,g in forecasts.groupby('target'):
        new=g[g.model.eq('log_har') & g.common].set_index('target_date')
        old=old_forecasts[old_forecasts.target.eq(target) & old_forecasts.model.eq('log_har')
                         & old_forecasts.period.eq('validation') & old_forecasts.common].set_index('target_date')
        shared=new.index.intersection(old.index)
        matched_refits=0; different_refits=0; unpaired_refits=0
        reg=fits[fits.target.eq(target) & fits.model.eq('log_har') & fits.status.ne('failed')]
        archived=old_fits[old_fits.target.eq(target) & old_fits.model.eq('log_har')]
        for row in reg.itertuples():
            previous=archived[archived.origin_date.eq(row.origin_date)]
            if len(previous)!=1:
                unpaired_refits+=1;continue
            a=json.loads(row.diagnostics)['training_target_dates']
            b=json.loads(previous.diagnostics.iloc[0])['training_target_dates']
            matched_refits+=int(a==b);different_refits+=int(a!=b)
        rows.append({'target':target,'stage4_common_dates':len(old),'stage4b_common_dates':len(new),
            'shared_dates':len(shared),'lost_dates':json.dumps([str(x.date()) for x in old.index.difference(new.index)]),
            'gained_dates':json.dumps([str(x.date()) for x in new.index.difference(old.index)]),
            'identical_training_refits':matched_refits,'changed_training_refits':different_refits,
            'unpaired_refits':unpaired_refits,
            'max_log_har_prediction_difference':float((new.loc[shared,'forecast_variance']-old.loc[shared,'forecast_variance']).abs().max()),
            'minimum_regression_training_pairs':int(reg.training_observations.min()),
            'maximum_regression_training_pairs':int(reg.training_observations.max()),'status':STATUS})
    return pd.DataFrame(rows)
