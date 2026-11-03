"""Two-state zero-mean Gaussian Markov-switching conditional variance.

statsmodels estimates parameters on a rolling past-only window. EM may smooth
inside that training window; forecasting explicitly calls filter() and consumes
only the terminal filtered probabilities. Our transition rows are current states
and columns are next states (the transpose of statsmodels' convention). Labels
are sorted by variance at every refit. Variances are decimal daily log-return units.
"""
from __future__ import annotations

import time
import warnings

import numpy as np
from scipy.special import logsumexp

from volrisk.forecasting.base import FIT_OK, FIT_WARNING, FitError, FitReport, VolatilityModel
from volrisk.forecasting.registry import register


def filter_observation(probabilities, transition, variances, observed_return):
    """Hamilton update in log space: propagate probabilities, then condition on r_t."""
    prior = np.asarray(probabilities, dtype=float) @ np.asarray(transition, dtype=float)
    variances = np.asarray(variances, dtype=float)
    if not np.isfinite(observed_return) or np.any(variances <= 0) or not np.isfinite(variances).all():
        raise FitError('Invalid observation or regime variance')
    with np.errstate(divide='ignore', over='ignore'):
        weights = np.log(prior) - .5 * (np.log(2 * np.pi * variances) + observed_return ** 2 / variances)
    normalizer = logsumexp(weights)
    if not np.isfinite(normalizer):
        raise FitError('Regime filter has zero/nonfinite likelihood')
    return np.exp(weights - normalizer)


@register('markov_switching')
class MarkovSwitchingVariance(VolatilityModel):
    family = 'regime_switching'
    version = '1.0.0'
    supports_update = True

    def __init__(self, name, *, n_states=2, window=1000, min_observations=500,
                 refit_every=21, scale=100., maxiter=200, em_iter=5,
                 transition_boundary=.001, min_occupancy=.02, min_variance_ratio=1.1):
        if n_states != 2 or min_observations < 20 or window < min_observations or refit_every < 1:
            raise ValueError('Require two states, window >= min_observations >= 20, refit_every >= 1')
        if not np.isfinite(scale) or scale <= 0 or maxiter < 1 or em_iter < 0:
            raise ValueError('Invalid numerical optimization settings')
        if not 0 < transition_boundary < .5 or not 0 < min_occupancy < .5 or min_variance_ratio <= 1:
            raise ValueError('Invalid regime diagnostic thresholds')
        super().__init__(name, n_states=2, window=int(window), min_observations=int(min_observations),
            refit_every=int(refit_every), scale=float(scale), maxiter=int(maxiter), em_iter=int(em_iter),
            transition_boundary=float(transition_boundary), min_occupancy=float(min_occupancy),
            min_variance_ratio=float(min_variance_ratio))
        self.reset()

    def reset(self):
        super().reset()
        self._probabilities = self._transition = self._variances = None
        self._origin = None

    def _model(self, values):
        from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
        return MarkovRegression(values, k_regimes=2, trend='n', switching_variance=True)

    def fit(self, returns, dates=None):
        tick = time.perf_counter()
        previous = self._params.copy()
        self._fitted = False
        values = self._as_array(returns)
        if len(values) < self.min_observations:
            raise FitError('Insufficient Markov-switching history')
        used = values[-self._config['window']:]
        scaled = used * self._config['scale']
        second_moment = float(np.mean(scaled ** 2))
        if second_moment <= 0 or not np.isfinite(second_moment):
            raise FitError('Degenerate Markov training observations')
        model = self._model(scaled)
        candidates, attempts = [], []
        for low, high, persistence in ((.25, 2., .97), (.5, 1.5, .90)):
            initial = [persistence, 1 - persistence, low * second_moment, high * second_moment]
            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always')
                    result = model.fit(start_params=initial, transformed=True, method='bfgs',
                        maxiter=self._config['maxiter'], em_iter=self._config['em_iter'], search_reps=0,
                        disp=False, cov_type='none')
                converged = bool(result.mle_retvals.get('converged', False))
                params = np.asarray(result.params, dtype=float)
                good = converged and np.isfinite(params).all() and np.isfinite(result.llf)
                attempts.append({'converged': converged, 'log_likelihood': float(result.llf),
                                 'warnings': [str(w.message) for w in caught]})
                if good:
                    candidates.append((float(result.llf), params))
            except (ValueError, RuntimeError, FloatingPointError, np.linalg.LinAlgError) as exc:
                attempts.append({'converged': False, 'error': f'{type(exc).__name__}: {exc}'})
        if not candidates:
            raise FitError(f'All Markov starts failed or did not converge: {attempts}')
        loglike, fitted_params = max(candidates, key=lambda x: x[0])
        # Never read the fit result's smoothed probabilities.
        filtered = model.filter(fitted_params, cov_type='none')
        raw_variances = fitted_params[-2:] / self._config['scale'] ** 2
        order = np.argsort(raw_variances)
        variances = raw_variances[order]
        transition = np.asarray(model.regime_transition_matrix(fitted_params))[:, :, 0].T
        transition = transition[np.ix_(order, order)]
        path = np.asarray(filtered.filtered_marginal_probabilities)[:, order]
        probabilities = path[-1]
        if (not np.isfinite(variances).all() or np.any(variances <= 0)
                or not np.isfinite(transition).all() or np.any(transition < 0)
                or not np.allclose(transition.sum(axis=1), 1., atol=1e-10)
                or not np.isfinite(probabilities).all() or np.any(probabilities < 0)
                or not np.isclose(probabilities.sum(), 1.)):
            raise FitError('Invalid estimated Markov probabilities or variances')
        flags = []
        boundary = self._config['transition_boundary']
        if np.any(transition < boundary) or np.any(transition > 1-boundary):
            flags.append('transition_near_boundary')
        ratio = float(variances[1] / variances[0])
        if ratio < self._config['min_variance_ratio']:
            flags.append('weak_variance_separation')
        if np.min(path.mean(axis=0)) < self._config['min_occupancy']:
            flags.append('weak_regime_occupancy')
        if ratio > 1000:
            flags.append('extreme_variance_ratio')
        self._variances, self._transition, self._probabilities = variances, transition, probabilities.copy()
        self._origin = None if dates is None else dates[-1]
        self._params = {'variance_low': float(variances[0]), 'variance_high': float(variances[1]),
            'p_low_low': float(transition[0, 0]), 'p_low_high': float(transition[0, 1]),
            'p_high_low': float(transition[1, 0]), 'p_high_high': float(transition[1, 1])}
        self._fitted = True
        start, end = self._window_dates(dates, len(values), len(used))
        diagnostics = {'boundary_flags': flags, 'probability_convention': 'filtered',
            'transition_convention': 'row=current, column=next', 'log_likelihood_scaled_returns': loglike,
            'label_order_from_estimator': order.tolist(), 'filtered_occupancy': path.mean(axis=0).tolist(),
            'variance_ratio': ratio, 'optimization_attempts': attempts,
            'expected_durations': [float(1 / (1-p)) if p < 1 else None for p in np.diag(transition)]}
        if previous:
            diagnostics['max_abs_log_variance_change'] = max(abs(np.log(self._params[k] / previous[k]))
                                                            for k in ('variance_low', 'variance_high'))
        return FitReport(status=FIT_WARNING if flags else FIT_OK, message='; '.join(flags), converged=True,
            params=self.params, diagnostics=diagnostics, training_start=start, training_end=end,
            training_observations=len(used), runtime_seconds=time.perf_counter()-tick)

    def update(self, observed_return, date=None):
        self._require_fitted()
        if date is not None and self._origin is not None and date <= self._origin:
            raise FitError('Markov updates must advance the origin date')
        self._probabilities = filter_observation(self._probabilities, self._transition, self._variances, observed_return)
        self._origin = date

    def forecast(self, horizon=1):
        self._require_fitted()
        if horizon < 1 or int(horizon) != horizon:
            raise ValueError('horizon must be a positive integer')
        probabilities = self._probabilities.copy()
        result = []
        for _ in range(int(horizon)):
            probabilities = probabilities @ self._transition
            result.append(float(probabilities @ self._variances))
        return np.array(result)

    def state_diagnostics(self):
        self._require_fitted()
        return {'filtered_probability_high': float(self._probabilities[1]),
                'predictive_probability_high': float((self._probabilities @ self._transition)[1]),
                'filtered_probabilities': self._probabilities.tolist(), 'transition': self._transition.tolist(),
                'state_variances': self._variances.tolist(), 'origin': self._origin}
