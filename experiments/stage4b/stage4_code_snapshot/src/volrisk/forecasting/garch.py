"""Family B: GARCH(1,1), EGARCH(1,1) and GJR-GARCH(1,1) with Gaussian or Student-t innovations.

Estimation uses the ``arch`` package. Conventions:

- Zero conditional mean (``mean="Zero"``): the model describes the variance
  of the raw daily log return, matching the squared-return evaluation target.
- Returns are multiplied by ``scale`` (default 100, i.e. percent units) before
  optimization and every variance is divided by ``scale**2`` on the way out,
  so all forecasts are in decimal-return units.
- Rolling estimation window of ``window`` sessions (default 1000) when
  available, never fewer than ``min_observations``.
- Parameters are re-estimated every ``refit_every`` sessions (default 21). In
  between, the conditional-variance state is advanced with each newly
  observed return through the model's own recursion, so a forecast made at
  origin t uses only returns through t.

Recursions in scaled units (``r`` is the scaled return, ``h`` the scaled variance):

    GARCH / GJR : h_{t+1} = omega + alpha r_t^2 + gamma r_t^2 1[r_t < 0] + beta h_t
    EGARCH      : ln h_{t+1} = omega + alpha (|z_t| - sqrt(2/pi)) + gamma z_t + beta ln h_t,  z_t = r_t / sqrt(h_t)

These match ``arch``'s one-step forecasts exactly (verified in tests). Only
(p, o, q) with p = q = 1 and o in {0, 1} are supported by the state update.
"""
from __future__ import annotations

import math
import time
import warnings

import numpy as np

from volrisk.forecasting.base import FIT_OK, FIT_WARNING, FitError, FitReport, VolatilityModel
from volrisk.forecasting.registry import register

_SUPPORTED_VOL = {"GARCH", "EGARCH"}
_DIST_ALIASES = {"normal": "normal", "gaussian": "normal", "t": "t", "studentst": "t", "student-t": "t", "student_t": "t"}
_ABS_Z_MEAN = math.sqrt(2.0 / math.pi)


@register("garch")
class ArchGARCH(VolatilityModel):
    family = "garch"
    version = "1.0.0"
    supports_update = True

    def __init__(self, name, *, vol: str = "GARCH", p: int = 1, o: int = 0, q: int = 1, dist: str = "normal",
                 window: int = 1000, min_observations: int = 500, refit_every: int = 21, scale: float = 100.0,
                 maxiter: int = 500, boundary_tol: float = 1e-4, persistence_warn: float = 0.999, **extra):
        vol = str(vol).upper()
        if vol not in _SUPPORTED_VOL:
            raise ValueError(f"vol must be one of {sorted(_SUPPORTED_VOL)}")
        if int(p) != 1 or int(q) != 1 or int(o) not in (0, 1):
            raise ValueError("state update is implemented for p=1, q=1 and o in {0, 1} only")
        dist_key = _DIST_ALIASES.get(str(dist).lower())
        if dist_key is None:
            raise ValueError(f"dist must be one of {sorted(_DIST_ALIASES)}")
        if int(window) < 50 or int(min_observations) < 50:
            raise ValueError("window and min_observations must be at least 50 observations")
        if int(min_observations) > int(window):
            raise ValueError("min_observations cannot exceed window")
        if int(refit_every) < 1:
            raise ValueError("refit_every must be at least 1")
        if not (float(scale) > 0 and math.isfinite(float(scale))):
            raise ValueError("scale must be positive and finite")
        if str(extra.pop("mean", "Zero")) != "Zero":
            raise ValueError("only the zero conditional mean convention is supported")
        super().__init__(name, vol=vol, p=1, o=int(o), q=1, dist=dist_key, window=int(window),
                         min_observations=int(min_observations), refit_every=int(refit_every), scale=float(scale),
                         maxiter=int(maxiter), boundary_tol=float(boundary_tol),
                         persistence_warn=float(persistence_warn), mean="Zero", **extra)
        self._h_scaled = float("nan")   # one-step-ahead conditional variance in scaled units
        self._n_updates_since_fit = 0

    # -- specification helpers -------------------------------------------------------------------
    @property
    def specification(self) -> str:
        label = {"GARCH": "GARCH", "EGARCH": "EGARCH"}[self._config["vol"]]
        if self._config["vol"] == "GARCH" and self._config["o"] == 1:
            label = "GJR-GARCH"
        return f"{label}(1,{self._config['o']},1)-{'Student-t' if self._config['dist'] == 't' else 'Gaussian'}"

    def _arch_model(self, y: np.ndarray):
        from arch import arch_model
        return arch_model(y, mean="Zero", vol=self._config["vol"], p=1, o=self._config["o"], q=1,
                          dist=self._config["dist"], rescale=False)

    def _step(self, h: float, r: float) -> float:
        """Advance the scaled conditional variance by one session using the stored parameters."""
        p = self._params
        if self._config["vol"] == "GARCH":
            gamma = p.get("gamma[1]", 0.0)
            return p["omega"] + p["alpha[1]"] * r * r + gamma * r * r * (1.0 if r < 0 else 0.0) + p["beta[1]"] * h
        z = r / math.sqrt(h)
        gamma = p.get("gamma[1]", 0.0)
        return math.exp(p["omega"] + p["alpha[1]"] * (abs(z) - _ABS_Z_MEAN) + gamma * z + p["beta[1]"] * math.log(h))

    def persistence(self, params: dict | None = None) -> float:
        p = params or self._params
        if self._config["vol"] == "GARCH":
            return p["alpha[1]"] + 0.5 * p.get("gamma[1]", 0.0) + p["beta[1]"]
        return p["beta[1]"]

    def _boundary_flags(self, params: dict, am) -> list[str]:
        flags = []
        tol = self._config["boundary_tol"]
        names = list(am.volatility.parameter_names()) + list(am.distribution.parameter_names())
        bounds = list(am.volatility.bounds(am._y)) + list(am.distribution.bounds(am._y))
        for pname, (lo, hi) in zip(names, bounds):
            value = params[pname]
            if math.isfinite(lo) and value - lo <= tol * max(1.0, abs(lo)):
                flags.append(f"{pname}_at_lower_bound")
            if math.isfinite(hi) and hi - value <= tol * max(1.0, abs(hi)):
                flags.append(f"{pname}_at_upper_bound")
        persistence = self.persistence(params)
        if persistence >= 1.0:
            flags.append("persistence_at_unit_root_igarch")
        elif persistence >= self._config["persistence_warn"]:
            flags.append("persistence_near_unit_root")
        return flags

    # -- estimation -----------------------------------------------------------------------------
    def fit(self, returns, dates=None) -> FitReport:
        started = time.perf_counter()
        values = self._as_array(returns)
        if values.size < self.min_observations:
            raise FitError(f"{self.name}: {values.size} observations < min_observations={self.min_observations}")
        used = values[-int(self._config["window"]):]
        y = used * self._config["scale"]
        caught_messages: list[str] = []
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                am = self._arch_model(y)
                result = am.fit(disp="off", show_warning=False, options={"maxiter": self._config["maxiter"]})
            except Exception as exc:  # arch raises ValueError/LinAlgError/RuntimeError on optimizer breakdown
                self._fitted = False
                raise FitError(f"{self.name}: estimation raised {type(exc).__name__}: {exc}") from exc
            caught_messages = [f"{w.category.__name__}: {str(w.message).splitlines()[0]}" for w in caught]
        params = {str(k): float(v) for k, v in result.params.items()}
        cond_var = np.asarray(result.conditional_volatility, dtype=float) ** 2
        if not all(math.isfinite(v) for v in params.values()):
            self._fitted = False
            raise FitError(f"{self.name}: non-finite parameter estimates {params}")
        if not (np.all(np.isfinite(cond_var)) and np.all(cond_var > 0)):
            self._fitted = False
            raise FitError(f"{self.name}: conditional variance path is not strictly positive and finite")
        persistence = self.persistence(params)
        if self._config["vol"] == "EGARCH" and persistence >= 1.0:
            # A unit root in log variance combined with an unbounded alpha produces explosive paths; rejected.
            self._fitted = False
            raise FitError(f"{self.name}: non-stationary EGARCH estimate (beta {persistence:.6f} >= 1); "
                           "rejected as a fit failure")
        if persistence > 1.0 + 1e-6:
            # arch constrains alpha + gamma/2 + beta <= 1; anything beyond floating-point overshoot is explosive.
            self._fitted = False
            raise FitError(f"{self.name}: explosive estimate (persistence {persistence:.8f} > 1); rejected as a fit failure")
        self._params = params
        try:
            h_next = self._step(float(cond_var[-1]), float(y[-1]))
        except (ValueError, OverflowError, ZeroDivisionError) as exc:
            self._fitted = False
            raise FitError(f"{self.name}: one-step recursion failed: {exc}") from exc
        if not (math.isfinite(h_next) and h_next > 0):
            self._fitted = False
            raise FitError(f"{self.name}: invalid one-step variance {h_next}")
        self._h_scaled = h_next
        self._fitted = True
        self._n_updates_since_fit = 0
        converged = int(result.convergence_flag) == 0
        flags = self._boundary_flags(params, am)
        opt = getattr(result, "optimization_result", None)
        diagnostics = {
            "specification": self.specification, "convergence_flag": int(result.convergence_flag),
            "loglikelihood": float(result.loglikelihood), "aic": float(result.aic), "bic": float(result.bic),
            "iterations": None if opt is None else int(getattr(opt, "nit", -1)),
            "boundary_flags": flags, "warnings": caught_messages, "persistence": float(self.persistence(params)),
            "scale": self._config["scale"], "nobs": int(result.nobs),
            "unconditional_variance_decimal": self._unconditional_variance_decimal(params),
            "nu_effectively_gaussian": bool(params.get("nu", 0.0) > 100.0) if "nu" in params else None,
        }
        status = FIT_OK if converged and not flags else FIT_WARNING
        message = "; ".join(([] if converged else [f"optimizer did not converge (flag {result.convergence_flag})"])
                            + flags + caught_messages)
        start, end = self._window_dates(dates, values.size, used.size)
        return FitReport(status=status, message=message, converged=converged, params=self.params,
                         diagnostics=diagnostics, training_start=start, training_end=end,
                         training_observations=int(used.size), runtime_seconds=time.perf_counter() - started)

    def _unconditional_variance_decimal(self, params: dict):
        if self._config["vol"] != "GARCH":
            return None
        persistence = self.persistence(params)
        if persistence >= 1.0:
            return None
        return float(params["omega"] / (1.0 - persistence) / self._config["scale"] ** 2)

    def update(self, observed_return: float, date=None) -> None:
        self._require_fitted()
        r = float(observed_return)
        if not math.isfinite(r):
            raise FitError(f"{self.name}: cannot update with a non-finite return")
        h_next = self._step(self._h_scaled, r * self._config["scale"])
        if not (math.isfinite(h_next) and h_next > 0):
            self._fitted = False
            raise FitError(f"{self.name}: state update produced invalid variance {h_next}")
        self._h_scaled = h_next
        self._n_updates_since_fit += 1

    def forecast(self, horizon: int = 1) -> np.ndarray:
        self._require_fitted()
        horizon = int(horizon)
        scale2 = self._config["scale"] ** 2
        if horizon == 1:
            return np.array([self._h_scaled / scale2], dtype=float)
        if self._config["vol"] != "GARCH":
            raise NotImplementedError("EGARCH multi-step forecasts need simulation; only horizon=1 is supported")
        out = np.empty(horizon, dtype=float)
        h = self._h_scaled
        out[0] = h
        persistence = self.persistence()
        for k in range(1, horizon):
            h = self._params["omega"] + persistence * h
            out[k] = h
        return out / scale2

    def reset(self) -> None:
        super().reset()
        self._h_scaled = float("nan")
        self._n_updates_since_fit = 0
