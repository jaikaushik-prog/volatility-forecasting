"""Synthetic Stage 3 fixtures only: state filtering, labels, tuning and future-shock invariance."""
from types import SimpleNamespace
import json

import numpy as np
import pandas as pd
import pytest

from volrisk.forecasting.base import FitError
from volrisk.forecasting.registry import build_model
from volrisk.forecasting.regime_switching import MarkovSwitchingVariance, filter_observation
from volrisk.forecasting.ml import XGBoostVolatility, FEATURE_NAMES, build_lagged_features, latest_features
from volrisk.evaluation.walk_forward import run_walk_forward


@pytest.fixture(scope='module')
def history():
    rng = np.random.default_rng(41)
    r = rng.normal(size=600) * np.tile(np.r_[np.full(100, .005), np.full(100, .025)], 3)
    return pd.Series(r, index=pd.bdate_range('2020-01-01', periods=len(r)))


def small_xgb(**kwargs):
    return XGBoostVolatility('x', window=400, min_observations=180, min_train_samples=100,
        cv_min_train=40, cv_size=20, cv_folds=2, search_space=[{'max_depth': 2, 'n_estimators': 15},
                                                         {'max_depth': 3, 'n_estimators': 15}], **kwargs)


def test_markov_transition_and_label_switching_uses_filtered_probabilities(monkeypatch):
    class Fake:
        def fit(self, **kwargs):
            return SimpleNamespace(params=np.array([.8, .1, 9., 1.]), llf=-2., mle_retvals={'converged': True})
        def regime_transition_matrix(self, params):
            return np.array([[[.8], [.1]], [[.2], [.9]]])
        def filter(self, params, **kwargs):
            return SimpleNamespace(filtered_marginal_probabilities=np.tile([.2, .8], (100, 1)))
        def smooth(self, *args, **kwargs):
            raise AssertionError('Forecast state must not use smoothing')
    model = MarkovSwitchingVariance('m', min_observations=100)
    monkeypatch.setattr(model, '_model', lambda x: Fake())
    report = model.fit(np.tile([.01, -.02], 50))
    state = model.state_diagnostics()
    np.testing.assert_allclose(state['filtered_probabilities'], [.8, .2])
    np.testing.assert_allclose(state['transition'], [[.9, .1], [.2, .8]])
    assert model.params['variance_low'] == pytest.approx(.0001)
    assert model.params['variance_high'] == pytest.approx(.0009)
    assert state['predictive_probability_high'] == pytest.approx(.24)
    assert model.forecast()[0] == pytest.approx(.76*.0001+.24*.0009)
    assert report.diagnostics['label_order_from_estimator'] == [1, 0]


def test_hamilton_update_matches_bayes_and_handles_large_returns():
    p, transition, variances = np.array([.8, .2]), np.array([[.9, .1], [.2, .8]]), np.array([1e-5, 4e-4])
    likelihood = np.exp(-.5*.02**2/variances) / np.sqrt(2*np.pi*variances)
    expected = (p@transition)*likelihood
    expected /= expected.sum()
    np.testing.assert_allclose(filter_observation(p, transition, variances, .02), expected)
    shock = filter_observation(p, transition, variances, 10.)
    assert np.isfinite(shock).all() and shock.sum() == pytest.approx(1.)
    assert shock[1] == pytest.approx(1.)


def test_markov_incremental_filter_matches_statsmodels_and_scaling(history):
    model = MarkovSwitchingVariance('m', window=600)
    report = model.fit(history.values[:500], history.index[:500])
    params = model.params
    for day, value in history.iloc[500:510].items():
        model.update(value, day)
    p = [params['p_low_low'], params['p_high_low'], params['variance_low']*10000, params['variance_high']*10000]
    reference = model._model(history.values[:510]*100).filter(p, cov_type='none')
    expected = np.asarray(reference.filtered_marginal_probabilities)[-1]
    np.testing.assert_allclose(model.state_diagnostics()['filtered_probabilities'], expected, atol=1e-10)
    assert model.params == params and report.converged
    assert 1e-6 < model.forecast()[0] < .01
    transition = np.array(model.state_diagnostics()['transition'])
    np.testing.assert_allclose(model.forecast(2)[1], expected@transition@transition@np.array([params['variance_low'], params['variance_high']]))


def test_markov_nonconvergence_is_failure_without_substitution(monkeypatch, history):
    fake = SimpleNamespace(fit=lambda **kw: SimpleNamespace(params=np.ones(4), llf=0., mle_retvals={'converged': False}))
    m = MarkovSwitchingVariance('bad')
    monkeypatch.setattr(m, '_model', lambda values: fake)
    with pytest.raises(FitError, match='did not converge'):
        m.fit(history.values)
    assert not m.fitted
    result = run_walk_forward(history, m, asset='SYN', max_origins=2)
    assert result.summary['fit_failures'] == 2
    assert result.forecasts.forecast_variance.isna().all()


def test_features_future_causality_and_incremental_equivalence(history):
    f = build_lagged_features(history)
    changed = history.copy()
    changed.iloc[350:] = .3
    altered = build_lagged_features(changed)
    pd.testing.assert_frame_equal(f[FEATURE_NAMES].iloc[:350], altered[FEATURE_NAMES].iloc[:350])
    assert f.target_sq_return_next.iloc[349] != altered.target_sq_return_next.iloc[349]
    for n in (100, 230, 400):
        got = latest_features(history.values[:n], f.ewma_094.iloc[n-1]).iloc[0]
        np.testing.assert_allclose(got, f[FEATURE_NAMES].iloc[n-1], atol=1e-13)
        assert f.target_sq_return_next.iloc[n-1] == pytest.approx(history.iloc[n]**2)


def test_xgboost_known_labels_chronological_tuning_and_positive_forecast(history):
    m = small_xgb()
    r = m.fit(history.values[:300], history.index[:300])
    d = r.diagnostics
    assert r.training_end == history.index[299]
    assert d['training_feature_end'] == history.index[298]
    assert d['training_label_end'] <= d['origin']
    assert len(d['tuning_candidates']) == 2
    for candidate in d['tuning_candidates']:
        for fold in candidate['folds']:
            assert fold['training_label_end'] <= fold['validation_origin_start'] < fold['validation_label_end'] <= d['origin']
    assert m.forecast()[0] > 0
    assert sum(d['feature_importance_gain_normalized'].values()) == pytest.approx(1.)
    assert set(d['feature_importance_gain_normalized']) == set(FEATURE_NAMES)


def test_xgboost_training_targets_include_zero_without_log_retransformation(history):
    values = history.values.copy()
    values[::7] = 0.
    m = small_xgb()
    m.fit(values[:300], history.index[:300])
    assert m.params['objective'] == 'reg:tweedie' and m.forecast()[0] > 0
    with pytest.raises(FitError, match='All-zero'):
        m.fit(np.zeros(300), history.index[:300])


def test_xgboost_updates_features_without_refitting(history):
    m = small_xgb()
    m.fit(history.values[:300], history.index[:300])
    original_hash = m.params['booster_sha256']
    for day, value in history.iloc[300:310].items():
        m.update(value, day)
    m.forecast()
    full = build_lagged_features(history.iloc[:310])[FEATURE_NAMES].iloc[-1]
    np.testing.assert_allclose(pd.Series(m.state_diagnostics()['features'])[FEATURE_NAMES], full, atol=1e-13)
    assert m.params['booster_sha256'] == original_hash


def test_xgboost_floor_is_recorded_invalid_forecast_fails(history, monkeypatch):
    m = small_xgb()
    m.fit(history.values[:300], history.index[:300])
    monkeypatch.setattr(m._estimator, 'predict', lambda X: np.array([0.]))
    assert m.forecast()[0] == m.config['variance_floor']
    assert m.state_diagnostics()['prediction_clipped']
    monkeypatch.setattr(m._estimator, 'predict', lambda X: np.array([np.nan]))
    with pytest.raises(FitError, match='Invalid XGBoost prediction'):
        m.forecast()


def test_hyperparameters_frozen_after_development(history):
    m = small_xgb(retune_every=21, tuning_end='2020-12-31')
    first = m.fit(history.values[:240], history.index[:240])
    selected = m.params['hyperparameters'].copy()
    assert first.diagnostics['tuning_candidates']
    later = m.fit(history.values[:330], history.index[:330])
    assert later.diagnostics['tuning_candidates'] == []
    assert m.params['hyperparameters'] == selected
    assert m.params['selection_date'] <= pd.Timestamp('2020-12-31')


@pytest.mark.parametrize('kind', ['markov_switching', 'xgboost'])
def test_advanced_future_shock_schedule_and_reproducibility(history, kind):
    spec = {'type': kind, 'min_observations': 180, 'window': 300, 'refit_every': 21}
    if kind == 'xgboost':
        spec.update(min_train_samples=100, cv_min_train=40, cv_size=20,
                    search_space=[{'max_depth': 2, 'n_estimators': 15}])
    r = history.iloc[:245]
    a = run_walk_forward(r, build_model('m', spec), asset='SYN', min_history=180)
    changed = r.copy()
    changed.iloc[222:] = .12
    b = run_walk_forward(changed, build_model('m', spec), asset='SYN', min_history=180)
    excluded = ['runtime_seconds', 'realized_log_return', 'realized_squared_return']
    before = a.forecasts[a.forecasts.origin_date <= r.index[221]].drop(columns=excluded).reset_index(drop=True)
    after = b.forecasts[b.forecasts.origin_date <= r.index[221]].drop(columns=excluded).reset_index(drop=True)
    pd.testing.assert_frame_equal(before, after)
    assert a.summary['n_valid_forecasts'] > 0
    usable_fits = a.fits[a.fits.status.ne('failed')]
    assert len(usable_fits) > 1
    for _, block in a.forecasts[a.forecasts.forecast_valid].groupby('last_fit_date'):
        assert block.params.nunique() == 1
    assert a.forecasts.model_state.apply(json.loads).apply(bool).any()


@pytest.mark.parametrize('kind', ['markov_switching', 'xgboost'])
def test_missing_observations_are_rejected_and_reset_clears_model(history, kind):
    m = MarkovSwitchingVariance('m') if kind == 'markov_switching' else small_xgb()
    m.fit(history.values, history.index)
    with pytest.raises(FitError):
        m.update(np.nan)
    bad = history.values.copy()
    bad[50] = np.nan
    with pytest.raises(FitError):
        m.fit(bad, history.index)
    m.reset()
    assert not m.fitted and not m.params
    with pytest.raises(FitError):
        m.forecast()


def test_features_reject_missing_values_instead_of_silently_imputing(history):
    bad = history.copy()
    bad.iloc[100] = np.nan
    with pytest.raises(FitError, match='finite contiguous'):
        build_lagged_features(bad)


@pytest.mark.parametrize('kind', ['markov_switching', 'xgboost'])
def test_advanced_configuration_clone(kind):
    original = build_model('m', {'type': kind})
    clone = build_model('clone', {'type': kind, **original.config})
    assert clone.config == original.config
