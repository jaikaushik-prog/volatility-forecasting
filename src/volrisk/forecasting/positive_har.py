"""Positive-link HAR with causal lagged VIX and optional Ridge regularization.

Ridge minimizes SSE + alpha * sum(standardized slopes squared); intercept unpenalized.
Strictly positive exp(log forecast) * training-residual smearing; no prediction clipping.
"""
from __future__ import annotations
import time
import numpy as np
import pandas as pd
from scipy.special import logsumexp

from .base import FitError, FitReport, FIT_OK, FIT_WARNING
from .har import HARRV, origin_features, supervised, RV_FEATURES, ON_FEATURES, VIX_FEATURES
from .registry import register

CHANGE = 'vix_log_change'
AVAILABLE = 'vix_change_available'
COMMON = RV_FEATURES + ON_FEATURES + VIX_FEATURES + [AVAILABLE]


def positive_features(panel):
    """IV already has the conservative session lag. diff never jumps missing rows.

The nonnegative availability column is only a common-sample mask, never a regressor.
Keeping overnight availability preserves the original Stage 4 training restriction.
"""
    f = origin_features(panel)
    iv = f.vix_implied_variance.where(lambda x: np.isfinite(x) & x.gt(0))
    f['vix_implied_variance'] = iv
    f[CHANGE] = np.log(iv).diff()
    f[AVAILABLE] = np.where(np.isfinite(f[CHANGE]), 1., np.nan)
    return f


@register('positive_har')
class PositiveHAR(HARRV):
    version = '1.0.0'

    def __init__(self, name, *, vix=True, vix_change=False, ridge_alpha=0., **kwargs):
        if not np.isfinite(ridge_alpha) or ridge_alpha < 0 or (vix_change and not vix):
            raise ValueError('Invalid Ridge penalty or VIX-change specification')
        kwargs.pop('transform', None)
        kwargs.pop('nonpositive_policy', None)
        kwargs.setdefault('common_columns', COMMON)
        super().__init__(name, transform='log', vix=vix, nonpositive_policy='reject',
                         vix_change=bool(vix_change), ridge_alpha=float(ridge_alpha), **kwargs)
        self.columns = RV_FEATURES + (VIX_FEATURES if vix else []) + ([CHANGE] if vix_change else [])

    def _transform_x(self, x):
        result = []
        self._last_transform_zeros = 0
        for column in self.columns:
            values = x[column].to_numpy(dtype=float)
            if not np.isfinite(values).all():
                raise FitError('Missing/nonfinite origin predictors; no imputation')
            if column == CHANGE:
                result.append(values)  # Signed log IV change; never log it again.
            elif column == 'vix_implied_variance':
                if (values <= 0).any():
                    raise FitError('Nonpositive implied variance is invalid, not a zero-RV event')
                result.append(np.log(values))
            else:
                if (values < 0).any():
                    raise FitError('Negative realized variance predictor')
                self._last_transform_zeros += int((values == 0).sum())
                # Positive small values are not clipped. Only exact zeros use training floor.
                result.append(np.log(np.where(values == 0, self._floor, values)))
        return np.column_stack(result)

    def fit(self, returns, dates=None, *, features=None):
        started = time.perf_counter()
        self.reset()
        features = positive_features(returns) if features is None else features
        x, y, target_dates = supervised(returns, self.config['target'],
                                        self.config['common_columns'], self.config['window'], features)
        if len(y) < self.min_observations:
            raise FitError(f'Insufficient completed training pairs: {len(y)}')
        positive = y[y > 0]
        if positive.empty:
            raise FitError('No positive training variance for zero-RV transformation')
        self._floor = max(float(positive.median()) * self.config['floor_fraction'], np.finfo(float).tiny)
        a = self._transform_x(x)
        zero_features = self._last_transform_zeros
        response = np.log(np.where(y.to_numpy() == 0, self._floor, y.to_numpy()))
        self._center = a.mean(axis=0)
        scale = a.std(axis=0, ddof=0)
        self._scale = np.where(scale > np.finfo(float).eps, scale, 1.)
        z = (a - self._center) / self._scale
        design = np.column_stack([np.ones(len(z)), z])
        alpha = self.config['ridge_alpha']
        # An augmented least-squares solve avoids squared condition numbers of normal equations.
        penalty = np.column_stack([np.zeros(len(self.columns)), np.eye(len(self.columns))])
        aug = np.vstack([design, np.sqrt(alpha) * penalty]) if alpha else design
        rhs = np.r_[response, np.zeros(len(self.columns))] if alpha else response
        self._coef, _, _, _ = np.linalg.lstsq(aug, rhs, rcond=None)
        residual = response - design @ self._coef
        log_smear = float(logsumexp(residual) - np.log(len(residual))) if self.config['log_bias_correction'] == 'smearing' else 0.
        self._log_smearing = log_smear
        with np.errstate(over='ignore', under='ignore'):
            self._smearing = float(np.exp(log_smear))
        if not np.isfinite(self._smearing) or self._smearing <= 0:
            raise FitError('Nonfinite/nonpositive training smearing factor')
        slopes = self._coef[1:] / self._scale
        self._params = {'intercept': float(self._coef[0] - slopes @ self._center),
                        **dict(zip(self.columns, map(float, slopes))), 'smearing': self._smearing,
                        'zero_rv_transform_floor': self._floor, 'ridge_alpha': alpha}
        rank = int(np.linalg.matrix_rank(design))
        condition = float(np.linalg.cond(design))
        warning = rank < design.shape[1] or condition > 1e8
        self._fitted = True
        self.update(features.iloc[-1])
        return FitReport(FIT_WARNING if warning else FIT_OK, converged=True, params=self.params,
            message='rank_deficient_or_ill_conditioned_design' if warning else '',
            training_start=pd.Timestamp(target_dates.iloc[0]), training_end=pd.Timestamp(target_dates.iloc[-1]),
            training_observations=len(y), runtime_seconds=time.perf_counter()-started,
            diagnostics={'rank': rank, 'condition_number': condition, 'regularized_condition_number': float(np.linalg.cond(aug)),
                'training_target_dates': [str(d) for d in target_dates], 'zero_training_targets': int(y.eq(0).sum()),
                'zero_training_features': zero_features, 'center': dict(zip(self.columns, map(float, self._center))),
                'scale': dict(zip(self.columns, map(float, self._scale))), 'standardized_coefficients': self._coef.tolist(),
                'residual_sd': float(residual.std(ddof=1)), 'log_smearing': log_smear,
                'transformation': 'log; signed change unchanged', 'prediction_floor': None,
                'bias_correction': self.config['log_bias_correction'], 'penalty': 'SSE + alpha * standardized slope L2 squared'})

    def forecast(self, horizon=1):
        self._require_fitted()
        if horizon != 1:
            raise NotImplementedError('Positive HAR supports one-session forecasts only')
        self._prediction = {}
        a = self._transform_x(self._origin)[0]
        log_prediction = float(self._coef[0] + ((a-self._center)/self._scale) @ self._coef[1:] + self._log_smearing)
        with np.errstate(over='ignore', under='ignore', invalid='ignore'):
            raw = float(np.exp(log_prediction))
        self._prediction = {'raw_prediction': raw, 'prediction_floored': False,
                            'log_prediction': log_prediction, 'zero_origin_features': self._last_transform_zeros}
        if not np.isfinite(raw) or raw <= 0:
            raise FitError('Nonfinite or underflowed positive-link forecast; no clipping or replacement')
        return np.array([raw])

    def update(self, observed_return, date=None):
        super().update(observed_return, date)
        # A missing next origin must not inherit the preceding origin's raw prediction.
        self._prediction = {}
