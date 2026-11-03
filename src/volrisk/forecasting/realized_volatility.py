"""Family E: HAR-RV is implemented; Realized GARCH remains a pending extension.

E1. HAR-RV (Corsi 2009)
    RV_{t+1} = c + b_d RV_t + b_w mean(RV_{t-4..t}) + b_m mean(RV_{t-21..t}) + e_{t+1}
E2. Realized GARCH (Hansen, Huang & Shek 2012)
    r_t = sqrt(h_t) z_t;  log h_t = omega + beta log h_{t-1} + gamma log RV_{t-1};
    log RV_t = xi + phi log h_t + tau(z_t) + u_t

Both require realized variance built from intraday observations. The repository
now has provisional Indian minute data and audited session measures. Availability
does not certify source identity, timestamp conventions or research readiness.
Use volrisk.har_cli for target-specific, holdout-protected HAR experiments.
A squared daily return is a distinct noisy variance proxy, never a replacement
for intraday realized variance. Realized GARCH is not implemented here.

Additional data requirements (per asset, per session):
  - Intraday prices or returns at a regular grid (1- or 5-minute), including
    exchange-local session boundaries (NSE 09:15-15:30 IST; NYSE/Arca
    09:30-16:00 ET), with overnight returns handled explicitly.
  - Trade/quote timestamps to compute realized kernels or sub-sampled RV.
  - Candidate sources: NSE historical tick/minute data (paid), TAQ / Polygon /
    Refinitiv for SPY and VT, Oxford-Man Realized Library equivalents for the
    S&P 500 (index level, not SPY).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from volrisk.forecasting.base import MODEL_PENDING, FitReport, VolatilityModel
from volrisk.forecasting.registry import register
from volrisk.forecasting.har import HARRV  # noqa: F401 - registry and public compatibility

INTRADAY_REQUIREMENTS = {
    "fields": ["session_date", "timestamp_exchange_local", "price", "volume_optional"],
    "grid": "regular 1-5 minute bars or tick data per full session",
    "estimator": "sub-sampled 5-minute realized variance or realized kernel; overnight return treated separately",
    "candidate_sources": ["NSE historical minute data", "TAQ", "Polygon.io", "Refinitiv Tick History",
                          "Oxford-Man Realized Library (S&P 500 index, not SPY)"],
}


def check_intraday_availability(data_root: Path | str = "data") -> dict:
    """Inventory only; eligibility is determined by the Stage 4 manifest/schema gates."""
    root = Path(data_root)
    patterns = ["**/*intraday*", "**/*minute*", "**/*tick*", "**/*realized*", "**/*_1m*", "**/*_5m*", "**/*1min*.csv"]
    hits = sorted({str(p) for pattern in patterns for p in root.glob(pattern) if p.is_file()}) if root.exists() else []
    return {"data_root": str(root), "intraday_files": hits, "available": bool(hits), "certified":False,
            "requirements": INTRADAY_REQUIREMENTS,
            "conclusion": ("intraday files present; verify grid, session boundaries and provenance" if hits
                           else "intraday inputs unavailable; HAR empirical evaluation cannot run")}


class _RealizedVarianceModel(VolatilityModel):
    family = "realized_volatility"
    version = "0.1.0-interface"
    implementation_status = MODEL_PENDING
    supports_update = False

    def __init__(self, name, *, realized_variance_source: str | None = None, window: int = 1000,
                 min_observations: int = 500, refit_every: int = 21, **extra):
        super().__init__(name, realized_variance_source=realized_variance_source, window=int(window),
                         min_observations=int(min_observations), refit_every=int(refit_every), **extra)

    def fit(self, returns, dates=None, realized_variance=None) -> FitReport:
        raise NotImplementedError(self.pending_reason)

    def forecast(self, horizon: int = 1) -> np.ndarray:
        raise NotImplementedError(self.pending_reason)


@register("realized_garch")
class RealizedGARCH(_RealizedVarianceModel):
    pending_reason = ("Realized GARCH measurement equation remains unimplemented; provisional minute data "
                      "availability alone does not implement or certify this extension.")
