"""Volatility forecasting models and registry (Sprint 2: Stage 1 and Stage 2)."""
from volrisk.forecasting import (  # noqa: F401  (import for registration side effects)
    ewma, garch, historical, ml, realized_volatility, regime_switching, stochastic_volatility)
from volrisk.forecasting.base import (FIT_FAILED, FIT_OK, FIT_WARNING, FORECAST_QUANTITY, PRIMARY_HORIZON,
                                      TRADING_DAYS_PER_YEAR, FitError, FitReport, VolatilityModel,
                                      annualized_volatility)
from volrisk.forecasting.registry import available_model_types, build_model, build_models

__all__ = ["FIT_FAILED", "FIT_OK", "FIT_WARNING", "FORECAST_QUANTITY", "PRIMARY_HORIZON", "TRADING_DAYS_PER_YEAR",
           "FitError", "FitReport", "VolatilityModel", "annualized_volatility", "available_model_types",
           "build_model", "build_models"]
