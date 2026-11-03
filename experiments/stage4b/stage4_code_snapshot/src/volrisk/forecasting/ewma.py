"""Family A4: RiskMetrics-style exponentially weighted moving-average variance.

Recursion under a zero conditional mean:

    h_{t+1} = decay * h_t + (1 - decay) * r_t ** 2

Initialization: ``h`` after the first ``init_window`` observations is their
sample variance (ddof=1). The recursion then runs forward through the origin.
``decay`` (lambda) defaults to 0.94 and is configurable. Incremental updates
reproduce the full recursion exactly (verified by the tests).
"""
from __future__ import annotations

import time

import numpy as np

from volrisk.forecasting.base import FIT_OK, FitError, FitReport, VolatilityModel
from volrisk.forecasting.historical import sample_variance
from volrisk.forecasting.registry import register


def ewma_variance_path(returns: np.ndarray, decay: float, init_window: int, ddof: int = 1) -> np.ndarray:
    """path[k] is the variance forecast for observation k+1 given returns[:k+1]; NaN before init_window-1."""
    values = np.asarray(returns, dtype=float)
    n = values.size
    if n < init_window:
        raise FitError(f"EWMA needs at least init_window={init_window} observations, got {n}")
    path = np.full(n, np.nan)
    h = sample_variance(values[:init_window], ddof=ddof, center=True)
    path[init_window - 1] = h
    for k in range(init_window, n):
        h = decay * h + (1.0 - decay) * values[k] * values[k]
        path[k] = h
    return path


@register("ewma")
class EWMAVariance(VolatilityModel):
    family = "historical"
    version = "1.0.0"
    supports_update = True

    def __init__(self, name, *, decay: float = 0.94, init_window: int = 252, min_observations: int = 252,
                 ddof: int = 1, **extra):
        decay = float(decay)
        if not 0.0 < decay < 1.0:
            raise ValueError("decay must lie strictly inside (0, 1)")
        if int(init_window) < 2:
            raise ValueError("init_window must be at least 2")
        super().__init__(name, decay=decay, init_window=int(init_window),
                         min_observations=max(int(min_observations), int(init_window)), ddof=int(ddof), **extra)
        self._h = float("nan")
        self._n_seen = 0

    def fit(self, returns, dates=None) -> FitReport:
        started = time.perf_counter()
        values = self._as_array(returns)
        if values.size < self.min_observations:
            raise FitError(f"{self.name}: {values.size} observations < min_observations={self.min_observations}")
        path = ewma_variance_path(values, self._config["decay"], self._config["init_window"], self._config["ddof"])
        h = float(path[-1])
        if not np.isfinite(h) or h <= 0:
            self._fitted = False
            raise FitError(f"{self.name}: non-positive or non-finite variance {h}")
        self._h = h
        self._fitted = True
        self._n_seen = int(values.size)
        self._params = {"decay": self._config["decay"], "variance": self._h, "n": self._n_seen}
        start, end = self._window_dates(dates, values.size, values.size)
        return FitReport(status=FIT_OK, converged=True, params=self.params, training_start=start, training_end=end,
                         training_observations=self._n_seen, runtime_seconds=time.perf_counter() - started)

    def update(self, observed_return: float, date=None) -> None:
        self._require_fitted()
        r = float(observed_return)
        if not np.isfinite(r):
            raise FitError(f"{self.name}: cannot update with a non-finite return")
        decay = self._config["decay"]
        self._h = decay * self._h + (1.0 - decay) * r * r
        self._n_seen += 1
        self._params["variance"] = self._h
        self._params["n"] = self._n_seen

    def forecast(self, horizon: int = 1) -> np.ndarray:
        self._require_fitted()
        return np.full(int(horizon), self._h, dtype=float)
