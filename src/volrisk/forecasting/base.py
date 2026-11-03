"""Unified interface for one-step-ahead volatility models.

Every model forecasts the same quantity: the conditional variance of the
next session's daily log return, in decimal-return units (a daily log
return of 1% is 0.01, so its variance is 1e-4). Annualized volatility is
``sqrt(variance_daily * 252)``. Models never see observations after the
forecast origin; the walk-forward engine enforces this by construction and
the test-suite verifies it with a synthetic future-shock test.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import math
from typing import Any

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252
FORECAST_QUANTITY = "conditional_variance_next_session_daily_log_return_decimal"
PRIMARY_HORIZON = 1

FIT_OK = "ok"            # estimation succeeded without diagnostic flags
FIT_WARNING = "warning"  # estimation produced a usable forecast but raised a diagnostic flag
FIT_FAILED = "failed"    # no usable forecast; the record carries a missing variance

MODEL_IMPLEMENTED = "implemented"
MODEL_PENDING = "pending_extension"
MODEL_NOT_IMPLEMENTED = "not_implemented"


class FitError(RuntimeError):
    """Raised by a model when estimation cannot produce a usable state."""


def annualized_volatility(variance_daily, sessions_per_year: int = TRADING_DAYS_PER_YEAR):
    """sigma_annual = sqrt(variance_daily * sessions_per_year); NaN propagates, negatives become NaN."""
    values = np.asarray(variance_daily, dtype=float)
    with np.errstate(invalid="ignore"):
        out = np.sqrt(values * float(sessions_per_year))
    return out if values.ndim else float(out)


def is_valid_variance(value) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number > 0.0


def _json_ready(value: Any):
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    if isinstance(value, (np.floating, np.integer)):
        return _json_ready(value.item())
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def params_to_json(params: dict | None) -> str:
    return json.dumps(_json_ready(params or {}), sort_keys=True)


@dataclass
class FitReport:
    """What happened during one estimation attempt."""
    status: str
    message: str = ""
    converged: bool | None = None
    params: dict = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)
    training_start: pd.Timestamp | None = None
    training_end: pd.Timestamp | None = None
    training_observations: int = 0
    runtime_seconds: float = 0.0

    @property
    def usable(self) -> bool:
        return self.status != FIT_FAILED

    def as_dict(self) -> dict:
        return {
            "status": self.status, "message": self.message, "converged": self.converged,
            "params": _json_ready(self.params), "diagnostics": _json_ready(self.diagnostics),
            "training_start": None if self.training_start is None else pd.Timestamp(self.training_start).isoformat(),
            "training_end": None if self.training_end is None else pd.Timestamp(self.training_end).isoformat(),
            "training_observations": int(self.training_observations),
            "runtime_seconds": float(self.runtime_seconds),
        }


FORECAST_COLUMNS = [
    "asset", "model", "model_family", "model_version", "origin_date", "target_date", "origin_index",
    "target_observed", "forecast_variance", "forecast_volatility_annualized", "forecast_valid", "forecast_flag",
    "realized_log_return", "realized_squared_return", "training_start", "training_end",
    "training_observations", "last_fit_date", "sessions_since_fit", "fit_status", "fit_message",
    "converged", "params", "model_state", "runtime_seconds",
]


class VolatilityModel(ABC):
    """Base class. Subclasses set ``family``, ``version`` and implement fit/forecast.

    Contract
    --------
    - ``fit(returns, dates)`` receives all permissible history through the
      forecast origin as decimal daily log returns (oldest first). The model
      selects its own training window and returns a :class:`FitReport`.
    - ``update(observed_return, date)`` advances the internal state with one
      newly observed return without re-estimating parameters (only when
      ``supports_update`` is True).
    - ``forecast(horizon)`` returns an array of conditional variances for the
      next ``horizon`` sessions in decimal-return units. Horizon 1 is primary.
    - ``refit_every`` tells the engine how often (in sessions) parameters are
      re-estimated; 1 means every session.
    """

    family: str = "abstract"
    version: str = "0.0.0"
    implementation_status: str = MODEL_IMPLEMENTED
    supports_update: bool = False
    type_name: str = ""

    def __init__(self, name: str, **config):
        self.name = str(name)
        self._config = dict(config)
        self._fitted = False
        self._params: dict = {}

    # -- configuration / metadata ------------------------------------------------
    @property
    def config(self) -> dict:
        return dict(sorted(self._config.items()))

    @property
    def params(self) -> dict:
        return dict(self._params)

    @property
    def fitted(self) -> bool:
        return self._fitted

    @property
    def min_observations(self) -> int:
        return int(self._config.get("min_observations", 2))

    @property
    def refit_every(self) -> int:
        return int(self._config.get("refit_every", 1))

    def metadata(self) -> dict:
        return {"name": self.name, "type": self.type_name, "family": self.family, "version": self.version,
                "implementation_status": self.implementation_status, "config": _json_ready(self.config),
                "forecast_quantity": FORECAST_QUANTITY, "primary_horizon": PRIMARY_HORIZON,
                "annualization_sessions": TRADING_DAYS_PER_YEAR, "supports_update": self.supports_update,
                "refit_every": self.refit_every, "min_observations": self.min_observations}

    # -- estimation ------------------------------------------------------------------
    @abstractmethod
    def fit(self, returns: np.ndarray, dates: pd.DatetimeIndex | None = None) -> FitReport:
        """Estimate the model from history through the origin and set the forecast state."""

    def update(self, observed_return: float, date: pd.Timestamp | None = None) -> None:
        raise NotImplementedError(f"{self.name} does not support incremental state updates")

    @abstractmethod
    def forecast(self, horizon: int = PRIMARY_HORIZON) -> np.ndarray:
        """Conditional variance for the next ``horizon`` sessions (decimal units)."""

    def reset(self) -> None:
        self._fitted = False
        self._params = {}

    def state_diagnostics(self) -> dict:
        """Observable filtering/features state at the origin, separate from fitted parameters."""
        return {}

    # -- helpers ----------------------------------------------------------------------
    @staticmethod
    def _as_array(returns) -> np.ndarray:
        values = np.asarray(returns, dtype=float).ravel()
        if values.size and not np.all(np.isfinite(values)):
            raise FitError("returns passed to fit must be finite; drop unusable observations first")
        return values

    @staticmethod
    def _window_dates(dates, n_total: int, n_used: int):
        if dates is None or n_used == 0:
            return None, None
        index = pd.DatetimeIndex(dates)
        return index[n_total - n_used], index[n_total - 1]

    def _require_fitted(self):
        if not self._fitted:
            raise FitError(f"{self.name} has no usable state; call fit() first")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r}, config={self.config})"
