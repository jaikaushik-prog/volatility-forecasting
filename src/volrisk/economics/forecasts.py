"""New daily-risk specifications; archived intraday forecasts are never traded.

Direct HAR horizon h pairs X_s with daily squared log return at s+h. Existing
OLS/positive-link estimators are reused through a shift of h-1 predictor rows;
the existing supervised builder supplies the remaining one-session shift.
The final forecast always uses the unshifted, currently available predictors.
"""
from __future__ import annotations
import time
import numpy as np
import pandas as pd
from volrisk.forecasting.base import FitError, params_to_json
from volrisk.forecasting.ewma import EWMAVariance
from volrisk.forecasting.garch import ArchGARCH
from volrisk.forecasting.har import HARRV, RV_FEATURES, VIX_FEATURES
from volrisk.forecasting.positive_har import PositiveHAR
from .alignment import causal_features, validate_grid

COMMON = RV_FEATURES + VIX_FEATURES


class DirectDailyHAR:
    """Adapter, not an amendment to any Stage 4/4B candidate."""
    def __init__(self, name, horizon, *, window=500, min_observations=126, refit_every=21):
        if horizon not in (2, 3):
            raise ValueError('Registered next-close horizons are 2 and 3')
        self.horizon = horizon
        kw = dict(target='spot_c2c_squared', window=window, min_observations=min_observations,
                  refit_every=refit_every, common_columns=COMMON)
        # Legacy internal target slot is explicitly replaced by the selected instrument's
        # squared daily total-return log return. Metadata records the actual instrument.
        self.model = (HARRV(name, nonpositive_policy='reject', **kw) if name == 'har_daily'
                      else PositiveHAR(name, vix=name == 'log_har_vix_daily', **kw))

    def fit(self, history, features):
        data = history.assign(spot_c2c_squared=history['log_return'].pow(2))
        report = self.model.fit(data, features=features.shift(self.horizon-1))
        self.model.update(features.iloc[-1])
        report.diagnostics['economic_direct_horizon'] = self.horizon
        report.diagnostics['target_quantity'] = 'selected_instrument_daily_close_to_close_log_return_squared'
        return report

    def update(self, row):
        self.model.update(row)

    def forecast(self):
        return float(self.model.forecast(1)[0])


def generate_forecasts(panel, settings, *, save=None):
    """Save each forecast before attaching its future outcome. History is prefix-only."""
    validate_grid(panel)
    features = causal_features(panel)
    rows = []
    cfg = settings['estimation']
    start = pd.Timestamp(cfg['forecast_start'])
    for name in cfg['models']:
        for horizon in cfg['horizons']:
            is_har = 'har_daily' in name or name == 'log_har_vix_daily'
            if is_har:
                adapter = DirectDailyHAR(name, horizon, window=cfg['har_window'],
                    min_observations=cfg['har_min_pairs'], refit_every=cfg['refit_every'])
                model = adapter.model
            elif name == 'ewma':
                model = EWMAVariance(name, decay=cfg['ewma_decay'], init_window=cfg['ewma_initial_observations'],
                                     min_observations=cfg['ewma_initial_observations'])
            elif name == 'garch':
                model = ArchGARCH(name, window=cfg['garch_window'], min_observations=cfg['garch_min_observations'],
                                  refit_every=cfg['refit_every'])
            else:
                raise ValueError(f'Unregistered economic model {name}')
            last_fit = -10**9
            report = None
            for i in range(len(panel)-horizon):
                date = panel.index[i]
                if date < start:
                    continue
                started = time.perf_counter()
                flag, prediction, fitted_now = '', np.nan, False
                try:
                    if not model.fitted or (name != 'ewma' and i-last_fit >= cfg['refit_every']):
                        history = panel.iloc[:i+1]
                        if is_har:
                            report = adapter.fit(history, features.iloc[:i+1])
                        else:
                            values = history.log_return
                            bad = np.flatnonzero(~np.isfinite(values.to_numpy()))
                            values = values.iloc[int(bad[-1])+1:] if len(bad) else values
                            report = model.fit(values.to_numpy(), dates=values.index)
                        if not report.usable or report.converged is False:
                            model.reset()
                            raise FitError('Unusable or nonconverged fit')
                        last_fit, fitted_now = i, True
                    else:
                        if is_har:
                            adapter.update(features.iloc[i])
                        else:
                            model.update(panel.log_return.iloc[i], date)
                    if is_har and not np.isfinite(features.iloc[i][COMMON]).all():
                        raise FitError('Common HAR origin predictors unavailable; no imputation')
                    prediction = adapter.forecast() if is_har else float(model.forecast(horizon)[-1])
                    if not np.isfinite(prediction) or prediction <= 0 or np.sqrt(prediction*252) > cfg['max_annual_volatility']:
                        raise FitError('Invalid/implausible positive variance forecast')
                except (FitError, ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
                    flag, prediction = str(exc), np.nan
                    # A bad observation invalidates daily variance state; do not bridge it.
                    if not is_har and not np.isfinite(panel.log_return.iloc[i]):
                        model.reset()
                execution_i, target_i = i+horizon-1, i+horizon
                record = dict(asset=settings['data']['asset'], model=name, horizon=horizon,
                    origin_date=date, issued_at=panel.origin_timestamp.iloc[i]+pd.Timedelta(microseconds=1),
                    execution_date=panel.index[execution_i], execution_timestamp=panel.origin_timestamp.iloc[execution_i],
                    target_date=panel.index[target_i], target_quantity='daily_close_to_close_log_return_variance',
                    forecast_variance=prediction, forecast_volatility_annualized=np.sqrt(prediction*252),
                    fit_status='failed' if flag else report.status, failure_reason=flag,
                    training_start=report.training_start if report else pd.NaT,
                    training_end=report.training_end if report else pd.NaT,
                    training_observations=report.training_observations if report else 0,
                    refitted=fitted_now, last_fit_date=panel.index[last_fit] if last_fit >= 0 else pd.NaT,
                    model_version=model.version, params=params_to_json(model.params),
                    diagnostics=params_to_json(report.diagnostics if report and fitted_now else {}),
                    runtime_seconds=time.perf_counter()-started,
                    data_quality_status=settings['data']['status'], instrument_status=settings['data']['instrument_status'])
                if save:
                    save(record.copy())  # Callback cannot see the future return.
                record['observed_squared_log_return'] = float(panel.log_return.iloc[target_i]**2)
                rows.append(record)
    return pd.DataFrame(rows)
