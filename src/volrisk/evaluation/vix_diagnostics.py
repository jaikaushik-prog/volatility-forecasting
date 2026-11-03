"""Reproduce and diagnose saved levels-HAR forecasts without changing their values."""
import json
import numpy as np
import pandas as pd
from scipy.optimize import linprog

from volrisk.forecasting.har import HARRV, origin_features, supervised
from volrisk.forecasting.registry import build_model
from .har_walk_forward import walk_forward, model_specs
from .walk_forward import PeriodSplits
from .metrics import qlike


def reproduce_stage4(panel, forecasts, manifest):
    rows = []
    config = manifest['config']
    splits = PeriodSplits.from_config(config['splits'])
    for target in ('intraday', 'intraday_overnight'):
        specs = model_specs('NIFTY', target, config)
        for name in ('har', 'log_har', 'har_vix', 'rv_ewma'):
            fresh, _ = walk_forward(panel, build_model(name, specs[name]), target=target, splits=splits)
            saved = forecasts[(forecasts.model == name) & (forecasts.target == target)].reset_index(drop=True)
            cols = ['origin_date', 'target_date', 'forecast_variance', 'forecast_flag', 'params',
                    'raw_prediction', 'prediction_floored', 'training_observations', 'training_end']
            pd.testing.assert_frame_equal(fresh[cols], saved[cols])
            good = saved.common & saved.period.eq('validation')
            rows.append({'target': target, 'model': name, 'n': int(good.sum()),
                         'qlike': float(qlike(saved.loc[good, 'forecast_variance'], saved.loc[good, 'observed_variance']).mean()),
                         'exact_forecast_and_coefficient_reproduction': True})
    return pd.DataFrame(rows)


def diagnose_levels(panel, forecasts, manifest, floor_fractions):
    features = origin_features(panel)
    specs = model_specs('NIFTY', 'intraday', manifest['config'])
    selected = forecasts[(forecasts.model == 'har_vix') & (forecasts.target == 'intraday')
                         & forecasts.period.eq('validation') & forecasts.common].sort_values('target_date')
    events, coefficients, correlations = [], [], []
    changes = np.log(panel.vix_implied_variance).diff()
    for fit_date, group in selected.groupby('last_fit_date', sort=True):
        hist = panel.loc[:fit_date]
        spec = dict(specs['har_vix']); spec.pop('type')
        model = HARRV('legacy_levels_vix', **spec)
        fit = model.fit(hist)
        x, y, _ = supervised(hist, 'intraday', model.config['common_columns'], model.config['window'])
        a = x[model.columns].to_numpy()
        z = (a-model._center)/model._scale
        design = np.column_stack([np.ones(len(a)), z])
        unscaled = np.column_stack([np.ones(len(a)), a])
        unscaled_coef = np.linalg.lstsq(unscaled, y, rcond=None)[0]
        cov_inverse = np.linalg.pinv(np.cov(z, rowvar=False))
        training_distances = np.einsum('ij,jk,ik->i', z, cov_inverse, z)
        corr = np.corrcoef(a, rowvar=False)
        inv_corr = np.linalg.pinv(corr)
        coefficients.append({'refit_origin': fit_date, 'n': len(y), **model.params,
            'standardized_intercept': model._coef[0],
            **{'standardized_'+c: model._coef[j+1] for j, c in enumerate(model.columns)},
            'condition_unscaled': np.linalg.cond(unscaled), 'condition_standardized': np.linalg.cond(design),
            'vix_vif': inv_corr[-1, -1], 'target_max': y.max(), 'training_median_target': y[y>0].median(),
            'training_end': fit.training_end})
        for j, c in enumerate(model.columns):
            for k, other in enumerate(model.columns):
                correlations.append({'refit_origin': fit_date, 'feature': c, 'other_feature': other,
                                     'correlation': corr[j,k]})
        for row in group.itertuples():
            vector = features.loc[row.origin_date, model.columns].to_numpy(dtype=float)
            standardized = (vector-model._center)/model._scale
            params = json.loads(row.params)
            reconstructed = params['intercept'] + sum(params[c]*vector[j] for j,c in enumerate(model.columns))
            np.testing.assert_allclose(reconstructed, row.raw_prediction, rtol=1e-10, atol=1e-15)
            unscaled_prediction = float(unscaled_coef @ np.r_[1.,vector])
            # Exact feasibility test in standardized coordinates, distinct from marginal ranges.
            hull = linprog(np.zeros(len(a)), A_eq=design.T, b_eq=np.r_[1.,standardized],
                           bounds=(0,None), method='highs')
            contributions = {'contribution_'+c: params[c]*vector[j] for j,c in enumerate(model.columns)}
            event = {'origin_date': row.origin_date, 'target_date': row.target_date, 'refit_origin': fit_date,
                'vix_source_session': row.vix_source_session,
                'lagged_vix_percent': 100*np.sqrt(vector[-1]), 'log_iv_change': changes.loc[row.origin_date],
                'raw_prediction': row.raw_prediction, 'forecast_variance': row.forecast_variance,
                'observed_variance': row.observed_variance, 'negative_raw': row.raw_prediction <= 0,
                'prediction_floored': row.prediction_floored, 'intercept': params['intercept'], **contributions,
                'marginal_extrapolation': bool(((vector<a.min(axis=0)) | (vector>a.max(axis=0))).any()),
                'outside_training_convex_hull': True if hull.status==2 else False if hull.success else None,
                'hull_solver_status': hull.status, 'vix_z_score': standardized[-1],
                'mahalanobis_squared': standardized @ cov_inverse @ standardized,
                'max_training_mahalanobis_squared': training_distances.max(),
                'standardized_vs_unscaled_prediction_difference': row.raw_prediction-unscaled_prediction,
                'training_median_target': float(y[y>0].median()),
                **{c: vector[j] for j,c in enumerate(model.columns)},
                **{'coefficient_'+c: params[c] for c in model.columns}}
            events.append(event)
    events = pd.DataFrame(events)
    floor_rows = []
    for fraction in floor_fractions:
        counterfactual = np.maximum(events.raw_prediction, events.training_median_target*fraction)
        floor_rows.append({'floor_fraction_of_training_median': fraction, 'n': len(events),
            'qlike': float(qlike(counterfactual, events.observed_variance).mean()),
            'calibration_ratio': events.observed_variance.mean()/counterfactual.mean(),
            'floored_count': int((events.raw_prediction < events.training_median_target*fraction).sum()),
            'status': 'DIAGNOSTIC_COUNTERFACTUAL_NOT_MODEL_SELECTION'})
    return events, pd.DataFrame(coefficients), pd.DataFrame(correlations), pd.DataFrame(floor_rows)
