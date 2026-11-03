"""HAR models on realized-variance observations, separate from daily-return estimators.

Rows are session observations through the origin. Regression pairs are X_s -> y_(s+1).
Log-HAR logs arithmetic RV averages; training-only Duan smearing estimates a conditional
mean on retransformation, assuming a common residual distribution in the fit window.
"""
from __future__ import annotations
import time
import numpy as np
import pandas as pd

from .base import FIT_OK, FIT_WARNING, FitError, FitReport, VolatilityModel
from .registry import register

RV_FEATURES = ['rv_daily', 'rv_weekly', 'rv_monthly']
ON_FEATURES = ['overnight_daily', 'overnight_weekly', 'overnight_monthly']
VIX_FEATURES = ['vix_implied_variance']
TARGETS = ('intraday', 'intraday_overnight', 'spot_c2c_squared')


def origin_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Features observable at row t; missing sessions remain rows and break windows."""
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise ValueError('Session observations must be sorted and unique')
    out = pd.DataFrame(index=frame.index)
    for source, prefix in [('rv', 'rv'), ('overnight_squared', 'overnight')]:
        values = pd.to_numeric(frame[source]).where(lambda x: np.isfinite(x) & x.ge(0))
        out[prefix+'_daily'] = values
        out[prefix+'_weekly'] = values.rolling(5, min_periods=5).mean()
        out[prefix+'_monthly'] = values.rolling(22, min_periods=22).mean()
    # Dataset loader already applied the explicitly configured full-session lag.
    out['vix_implied_variance'] = frame['vix_implied_variance']
    return out


def supervised(history, target, columns, window, features=None):
    """Never use the last origin's unknown next target, or jump over missing rows."""
    features = origin_features(history) if features is None else features
    if not features.index.equals(history.index):
        raise ValueError('Precomputed features must match the permissible history prefix exactly')
    y = history[target].shift(-1)
    start = max(0, len(history)-1-window) if window else 0
    x = features.iloc[start:-1]
    y = y.iloc[start:-1]
    valid = np.isfinite(x[columns]).all(axis=1) & x[columns].ge(0).all(axis=1) & np.isfinite(y) & y.ge(0)
    return x.loc[valid], y.loc[valid], history.index.to_series().shift(-1).loc[x.index][valid]


@register('har_rv')
class HARRV(VolatilityModel):
    family = 'realized_volatility'
    version = '1.0.0'
    input_kind = 'session_features'
    supports_update = True

    def __init__(self, name, *, target='intraday', transform='levels', overnight=False, vix=False,
                 window=500, min_observations=126, refit_every=21, floor_fraction=1e-6,
                 nonpositive_policy='floor', log_bias_correction='smearing', common_columns=None, **extra):
        if target not in TARGETS or transform not in ('levels','log'):
            raise ValueError('Unknown HAR target or transformation')
        if min_observations < 5 or window < min_observations or refit_every < 1:
            raise ValueError('Invalid HAR estimation history or refit interval')
        if not 0 < floor_fraction < 1 or nonpositive_policy not in ('floor','reject'):
            raise ValueError('Invalid training-derived floor policy')
        if log_bias_correction not in ('smearing','none'):
            raise ValueError('Unknown log back-transformation correction')
        super().__init__(name, target=target, transform=transform, overnight=bool(overnight), vix=bool(vix),
            window=int(window), min_observations=int(min_observations), refit_every=int(refit_every),
            floor_fraction=float(floor_fraction), nonpositive_policy=nonpositive_policy,
            log_bias_correction=log_bias_correction, common_columns=list(common_columns or []), **extra)
        self.columns = RV_FEATURES + (ON_FEATURES if overnight else []) + (VIX_FEATURES if vix else [])
        self._origin = None
        self._prediction = {}

    def metadata(self):
        return super().metadata() | {'forecast_quantity': self.config['target'], 'input_kind':self.input_kind,
            'feature_columns':self.columns, 'unit':'decimal_log_return_squared'}

    def training_count(self, history):
        _, y, _ = supervised(history, self.config['target'], self.config['common_columns'] or self.columns, self.config['window'])
        return len(y)

    def _transform_x(self, x):
        a = x[self.columns].to_numpy(dtype=float)
        if not np.isfinite(a).all() or (a < 0).any():
            raise FitError('Missing/invalid origin features; no carry-forward is permitted')
        if self.config['transform']=='log':
            # All columns here are variances. VIX remains annualized, with its own coefficient.
            a = np.log(np.maximum(a, self._floor))
        return a

    def fit(self, returns, dates=None, *, features=None) -> FitReport:
        started = time.perf_counter()
        self.reset()
        if not isinstance(returns, pd.DataFrame):
            raise TypeError('HAR-RV requires a session-feature DataFrame; use volrisk.har_cli')
        history = returns
        features = origin_features(history) if features is None else features
        x, y, target_dates = supervised(history, self.config['target'],
            self.config['common_columns'] or self.columns, self.config['window'],features=features)
        if len(y) < self.min_observations:
            raise FitError(f'Insufficient completed training pairs: {len(y)} < {self.min_observations}')
        positive = y[y>0]
        if positive.empty:
            raise FitError('No positive training target from which to estimate a variance floor')
        self._floor = max(float(np.median(positive))*self.config['floor_fraction'], np.finfo(float).tiny)
        a = self._transform_x(x)
        response = np.log(np.maximum(y.to_numpy(), self._floor)) if self.config['transform']=='log' else y.to_numpy()
        self._center = a.mean(axis=0)
        scale = a.std(axis=0, ddof=0)
        self._scale = np.where(scale>np.finfo(float).eps, scale, 1.)
        design = np.column_stack([np.ones(len(a)), (a-self._center)/self._scale])
        self._coef, _, rank, singular = np.linalg.lstsq(design, response, rcond=None)
        residual = response - design@self._coef
        self._smearing = 1.
        if self.config['transform']=='log' and self.config['log_bias_correction']=='smearing':
            with np.errstate(over='ignore'):
                self._smearing = float(np.mean(np.exp(residual)))
            if not np.isfinite(self._smearing):
                raise FitError('Nonfinite training residual smearing factor')
        slopes = self._coef[1:]/self._scale
        self._params = {'intercept':float(self._coef[0]-slopes@self._center),
            **dict(zip(self.columns,map(float,slopes))), 'variance_floor':self._floor, 'smearing':self._smearing}
        condition = float(singular[0]/singular[-1]) if singular[-1]>0 else np.inf
        warning = rank < design.shape[1] or condition>1e8
        self._fitted = True
        self.update(features.iloc[-1])
        total = float(np.square(response-response.mean()).sum())
        return FitReport(status=FIT_WARNING if warning else FIT_OK, converged=True,
            message='rank_deficient_or_ill_conditioned_design' if warning else '', params=self.params,
            diagnostics={'rank':int(rank),'columns':design.shape[1],'condition_number':condition,
                'r_squared':1-float(residual@residual)/total if total>0 else None,
                'residual_sd':float(np.std(residual,ddof=1)), 'zero_training_targets':int((y==0).sum()),
                'transformation':self.config['transform'], 'bias_correction':self.config['log_bias_correction'],
                'first_predictor_session':str(x.index[0]),'last_predictor_session':str(x.index[-1]),
                'training_target_dates':[str(d) for d in target_dates]},
            training_start=pd.Timestamp(target_dates.iloc[0]),training_end=pd.Timestamp(target_dates.iloc[-1]),
            training_observations=len(y),runtime_seconds=time.perf_counter()-started)

    def update(self, observed_return, date=None):
        self._require_fitted()
        self._origin = pd.DataFrame([observed_return])

    def forecast(self, horizon=1):
        self._require_fitted()
        if horizon != 1:
            raise NotImplementedError('HAR implementation supports one-session forecasts only')
        a = self._transform_x(self._origin)[0]
        linear = float(self._coef[0] + ((a-self._center)/self._scale)@self._coef[1:])
        with np.errstate(over='ignore', under='ignore'):
            raw = float(np.exp(linear)*self._smearing) if self.config['transform']=='log' else linear
        self._prediction = {'raw_prediction':raw,'prediction_floored':False,'variance_floor':self._floor}
        if not np.isfinite(raw):
            raise FitError('Nonfinite raw variance prediction')
        if raw < self._floor:
            if self.config['nonpositive_policy']=='reject':
                raise FitError('Raw variance prediction below training-derived positive floor')
            self._prediction['prediction_floored'] = True
        return np.array([max(raw,self._floor)])

    def state_diagnostics(self):
        return dict(self._prediction)

    def reset(self):
        super().reset()
        self._origin = None
        self._prediction = {}


@register('rv_benchmark')
class RVBenchmark(VolatilityModel):
    """Smooth the observed target variance, never compute the variance of the RV series."""
    family = 'realized_benchmark'
    version = '1.0.0'
    input_kind = 'session_features'

    def __init__(self,name,*,target='intraday',method='previous',window=5,decay=.94,init_window=22,**extra):
        if target not in TARGETS or method not in ('previous','mean','ewma') or not 0<decay<1 or window<1 or init_window<1:
            raise ValueError('Invalid realized-variance benchmark configuration')
        super().__init__(name,target=target,method=method,window=window,decay=decay,init_window=init_window,**extra)

    def metadata(self):
        return super().metadata() | {'forecast_quantity':self.config['target'],'input_kind':self.input_kind}

    def fit(self,returns,dates=None):
        self.reset()
        values = returns[self.config['target']].to_numpy(dtype=float)
        last_bad = np.flatnonzero(~np.isfinite(values) | (values<0))
        start = int(last_bad[-1])+1 if len(last_bad) else 0
        values = values[start:]
        method = self.config['method']
        n = 1 if method=='previous' else self.config['window'] if method=='mean' else self.config['init_window']
        if len(values)<n:
            raise FitError(f'Need {n} contiguous valid realized observations; got {len(values)}')
        if method=='ewma':
            h = float(values[:n].mean())
            for value in values[n:]: h=self.config['decay']*h+(1-self.config['decay'])*value
            used = len(values)
        else:
            h,used = float(values[-n:].mean()),n
        self._h = h
        self._fitted = True
        self._params = {'variance':h}
        return FitReport(FIT_OK,converged=True,params=self.params,training_observations=used,
                         training_start=returns.index[-used],training_end=returns.index[-1])

    def forecast(self,horizon=1):
        self._require_fitted()
        if horizon!=1: raise NotImplementedError('Only one-session forecasts supported')
        if not np.isfinite(self._h) or self._h<=0: raise FitError('Nonpositive realized-variance benchmark forecast')
        return np.array([self._h])
