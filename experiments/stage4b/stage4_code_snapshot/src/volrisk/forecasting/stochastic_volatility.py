"""Family D: stochastic volatility (STAGE 4 interfaces; data-gated, not implemented).

D1. Latent (log-)stochastic volatility, physical measure
-------------------------------------------------------
    r_t = exp(x_t / 2) * eps_t,         eps_t ~ N(0, 1) or Student-t
    x_t = mu + phi (x_{t-1} - mu) + sigma_eta * eta_t,   eta_t ~ N(0, 1)

Estimation options (daily returns are sufficient; no extra data needed):
  - Quasi-maximum likelihood on log r_t^2 with a Kalman filter (Harvey,
    Ruiz & Shephard 1994): fast, slightly biased.
  - Bayesian MCMC (Kim, Shephard & Chib 1998) or particle filtering: exact
    but computationally heavier; must respect the 21-session refit schedule.
Forecast at origin t: h_{t+1} = E[exp(x_{t+1}) | F_t], evaluated from the
filtered distribution of x_t (never the smoothed distribution).

D2. Heston stochastic volatility
---------------------------------
    dS/S = mu dt + sqrt(v_t) dW_1,   dv = kappa (theta - v_t) dt + xi sqrt(v_t) dW_2,   corr(dW_1, dW_2) = rho

Heston is primarily an option-pricing model. Its parameters are usually
calibrated to an implied-volatility surface under the *risk-neutral*
measure Q. The variance drift under Q differs from the physical measure P by
the variance risk premium: kappa_Q theta_Q != kappa_P theta_P in general, and
risk-neutral expected variance systematically exceeds realized variance in
equity indices. A Q-calibrated E^Q[v_{t+1}] therefore is NOT a physical
forecast of next-session variance and must not be evaluated as one without
an explicit premium adjustment (e.g. joint P/Q estimation with returns and
options, or a documented variance-risk-premium correction).

Calibration requirements (per asset, historical, point-in-time):
  - Daily implied-volatility surfaces (strikes x maturities) or at least a
    term structure of ATM implied variances and a model-free implied
    variance (VIX-style) per session, observed at the forecast origin.
  - Risk-free and dividend-yield curves matching the option maturities.
  - A physical-measure link: either a joint P/Q estimator (returns + option
    panel) or an external variance-risk-premium model.
Possible data sources: CBOE DataShop (SPX/SPY options, VIX), OptionMetrics
IvyDB (US), NSE historical option chains / India VIX (NIFTY 50), Cboe/Eurex
for global indices. None of these are in the repository, and VT has no
liquid listed-option market, so Heston is NOT IMPLEMENTED and marked as such
in the registry. No calibration data is fabricated or substituted.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from volrisk.forecasting.base import MODEL_NOT_IMPLEMENTED, MODEL_PENDING, FitReport, VolatilityModel
from volrisk.forecasting.registry import register

OPTIONS_SURFACE_REQUIREMENTS = {
    "fields": ["session_date", "underlying", "expiry", "strike", "option_type", "implied_volatility", "mid_price",
               "risk_free_rate", "dividend_yield"],
    "point_in_time": "surfaces must be as observed at each forecast origin (no backfilled or revised vendor data)",
    "physical_link": "joint P/Q estimation or a variance-risk-premium model is required to produce a P-measure forecast",
    "candidate_sources": ["CBOE DataShop", "OptionMetrics IvyDB", "NSE historical option chains / India VIX",
                          "Cboe VIX family indices"],
}


def check_options_surface_availability(data_root: Path | str = "data") -> dict:
    """Report whether any historical options-surface data exists in the repository (none is expected)."""
    root = Path(data_root)
    patterns = ["**/*option*", "**/*implied*", "**/*vix*", "**/*surface*"]
    hits = sorted({str(p) for pattern in patterns for p in root.glob(pattern) if p.is_file()}) if root.exists() else []
    return {"data_root": str(root), "options_surface_files": hits, "available": bool(hits),
            "requirements": OPTIONS_SURFACE_REQUIREMENTS,
            "conclusion": ("options surface data present; verify point-in-time integrity before calibration" if hits
                           else "no historical options surface data in the repository; Heston calibration is not possible")}


@register("latent_sv")
class LatentStochasticVolatility(VolatilityModel):
    family = "stochastic_volatility"
    version = "0.1.0-interface"
    implementation_status = MODEL_PENDING
    supports_update = True
    pending_reason = ("Stage 4 deliverable: latent log-SV with filtered-state forecasts is specified but not "
                      "implemented. Daily returns suffice; no additional data is required.")

    def __init__(self, name, *, estimator: str = "qml_kalman", window: int = 1000, min_observations: int = 500,
                 refit_every: int = 21, **extra):
        super().__init__(name, estimator=str(estimator), window=int(window), min_observations=int(min_observations),
                         refit_every=int(refit_every), **extra)

    def fit(self, returns, dates=None) -> FitReport:
        raise NotImplementedError(self.pending_reason)

    def update(self, observed_return: float, date=None) -> None:
        raise NotImplementedError(self.pending_reason)

    def forecast(self, horizon: int = 1) -> np.ndarray:
        raise NotImplementedError(self.pending_reason)


@register("heston")
class HestonStochasticVolatility(VolatilityModel):
    family = "stochastic_volatility"
    version = "0.1.0-interface"
    implementation_status = MODEL_NOT_IMPLEMENTED
    supports_update = False
    pending_reason = ("NOT IMPLEMENTED: Heston requires point-in-time historical option surfaces and a physical-"
                      "measure link; none are available in this repository (see check_options_surface_availability).")

    def __init__(self, name, *, measure: str = "physical", options_data_dir: str | None = None, **extra):
        if str(measure) not in ("physical", "risk_neutral"):
            raise ValueError("measure must be 'physical' or 'risk_neutral'")
        super().__init__(name, measure=str(measure), options_data_dir=options_data_dir, **extra)

    def fit(self, returns, dates=None) -> FitReport:
        raise NotImplementedError(self.pending_reason)

    def forecast(self, horizon: int = 1) -> np.ndarray:
        raise NotImplementedError(self.pending_reason)
