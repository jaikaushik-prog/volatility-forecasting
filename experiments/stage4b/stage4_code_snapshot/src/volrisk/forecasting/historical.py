"""Family A benchmarks: expanding and rolling sample variance of daily log returns.

Sample variance uses ``ddof=1`` and is demeaned by default (``center=True``).
These estimators are re-estimated every session from history through the
origin; the variance of the last ``window`` observations (or of all history)
is the forecast for the next session. The forecast is flat across horizons.
"""
from __future__ import annotations

import time

import numpy as np

from volrisk.forecasting.base import FIT_OK, FitError, FitReport, VolatilityModel
from volrisk.forecasting.registry import register


def sample_variance(values: np.ndarray, ddof: int = 1, center: bool = True) -> float:
    values = np.asarray(values, dtype=float)
    n = values.size
    if n - ddof < 1:
        raise FitError(f"need more than {ddof} observations for a ddof={ddof} variance, got {n}")
    if center:
        return float(np.var(values, ddof=ddof))
    return float(np.sum(values * values) / (n - ddof))


class _SampleVarianceModel(VolatilityModel):
    family = "historical"
    version = "1.0.0"
    supports_update = False

    def __init__(self, name, *, min_observations: int = 252, ddof: int = 1, center: bool = True, **extra):
        super().__init__(name, min_observations=int(min_observations), ddof=int(ddof), center=bool(center), **extra)
        if self.min_observations < 2:
            raise ValueError("min_observations must be at least 2")
        self._variance = float("nan")

    def _training_slice(self, values: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def fit(self, returns, dates=None) -> FitReport:
        started = time.perf_counter()
        values = self._as_array(returns)
        if values.size < self.min_observations:
            raise FitError(f"{self.name}: {values.size} observations < min_observations={self.min_observations}")
        used = self._training_slice(values)
        variance = sample_variance(used, ddof=self._config["ddof"], center=self._config["center"])
        if not np.isfinite(variance) or variance <= 0:
            self._fitted = False
            raise FitError(f"{self.name}: non-positive or non-finite variance {variance}")
        self._variance = variance
        self._fitted = True
        self._params = {"variance": self._variance, "n": int(used.size)}
        start, end = self._window_dates(dates, values.size, used.size)
        return FitReport(status=FIT_OK, converged=True, params=self.params, training_start=start,
                         training_end=end, training_observations=int(used.size),
                         runtime_seconds=time.perf_counter() - started)

    def forecast(self, horizon: int = 1) -> np.ndarray:
        self._require_fitted()
        return np.full(int(horizon), self._variance, dtype=float)


@register("expanding")
class ExpandingVariance(_SampleVarianceModel):
    """A1: variance of all history through the origin."""

    def _training_slice(self, values):
        return values


@register("rolling")
class RollingVariance(_SampleVarianceModel):
    """A2/A3: variance of the last ``window`` observations through the origin."""

    def __init__(self, name, *, window: int = 20, min_observations: int = 252, **extra):
        if int(window) < 2:
            raise ValueError("window must be at least 2")
        super().__init__(name, min_observations=max(int(min_observations), int(window)), window=int(window), **extra)

    def _training_slice(self, values):
        return values[-int(self._config["window"]):]
