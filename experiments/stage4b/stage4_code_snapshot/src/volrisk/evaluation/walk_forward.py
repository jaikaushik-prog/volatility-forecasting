"""Walk-forward forecasting engine.

At each origin session t (oldest first):

1. the model receives history through t (returns[0..t]);
2. if a re-estimation is due it is fitted on that history, otherwise its
   state is advanced with r_t only;
3. it forecasts the variance of session t+1;
4. the forecast is persisted with its provenance before r_{t+1} is read;
5. the realized return r_{t+1} is attached for later evaluation.

Nothing after t can influence the forecast made at t: the history slice is a
prefix of the series and the model API has no access to the series itself.
Failed fits produce missing forecasts (``forecast_valid=False``); they are
never replaced by another model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import time

import numpy as np
import pandas as pd

from volrisk.forecasting.base import (FIT_FAILED, FORECAST_COLUMNS, TRADING_DAYS_PER_YEAR, FitReport, VolatilityModel,
                                      annualized_volatility, is_valid_variance, params_to_json, _json_ready)

PERIOD_NAMES = ("development", "validation", "holdout")
PERIOD_UNASSIGNED = "unassigned"


@dataclass(frozen=True)
class PeriodSplits:
    development: tuple[pd.Timestamp, pd.Timestamp]
    validation: tuple[pd.Timestamp, pd.Timestamp]
    holdout: tuple[pd.Timestamp, pd.Timestamp]
    holdout_sealed: bool = True

    @classmethod
    def from_config(cls, section: dict) -> "PeriodSplits":
        def span(name):
            value = section[name]
            start, end = pd.Timestamp(value[0]), pd.Timestamp(value[1])
            if start > end:
                raise ValueError(f"{name}: start after end")
            return start, end
        splits = cls(span("development"), span("validation"), span("holdout"),
                     holdout_sealed=bool(section.get("holdout_sealed", True)))
        order = [splits.development, splits.validation, splits.holdout]
        for (_, earlier_end), (later_start, _) in zip(order, order[1:]):
            if later_start <= earlier_end:
                raise ValueError("development, validation and holdout periods must be ordered and non-overlapping")
        return splits

    def label(self, dates) -> np.ndarray:
        index = pd.DatetimeIndex(pd.to_datetime(dates))
        labels = np.full(len(index), PERIOD_UNASSIGNED, dtype=object)
        for name in PERIOD_NAMES:
            start, end = getattr(self, name)
            labels[(index >= start) & (index <= end)] = name
        return labels

    def as_dict(self) -> dict:
        return {name: [getattr(self, name)[0].date().isoformat(), getattr(self, name)[1].date().isoformat()]
                for name in PERIOD_NAMES} | {"holdout_sealed": self.holdout_sealed}


@dataclass
class WalkForwardResult:
    asset: str
    model: dict
    forecasts: pd.DataFrame
    fits: pd.DataFrame
    summary: dict = field(default_factory=dict)


def _empty_forecasts() -> pd.DataFrame:
    return pd.DataFrame({column: pd.Series(dtype=object) for column in FORECAST_COLUMNS})


FIT_COLUMNS = ["asset", "model", "origin_date", "origin_index", "status", "message", "converged", "params",
               "diagnostics", "training_start", "training_end", "training_observations", "runtime_seconds",
               "boundary_flags", "persistence"]


def _validate_series(log_returns: pd.Series, allow_missing=False) -> tuple[np.ndarray, pd.DatetimeIndex]:
    if not isinstance(log_returns, pd.Series):
        raise TypeError("log_returns must be a pandas Series indexed by session date")
    index = pd.DatetimeIndex(log_returns.index)
    if not index.is_monotonic_increasing or not index.is_unique:
        raise ValueError("return index must be strictly increasing session dates")
    values = np.asarray(log_returns.values, dtype=float)
    if values.size and (np.isinf(values).any() or (not allow_missing and np.isnan(values).any())):
        raise ValueError("log_returns must be finite; drop unusable observations before forecasting")
    return values, index


DEFAULT_MIN_ANNUALIZED_VOL = 1e-3   # 0.1% annualized: below this a variance forecast is treated as degenerate
DEFAULT_MAX_ANNUALIZED_VOL = 5.0    # 500% annualized: above this a variance forecast is treated as explosive


def classify_forecast(variance, sessions_per_year: int, min_annualized_vol: float, max_annualized_vol: float) -> str:
    """Return '' for a usable variance forecast, otherwise the reason it is invalid."""
    if not is_valid_variance(variance):
        return "non_positive_or_non_finite"
    vol = annualized_volatility(float(variance), sessions_per_year)
    if vol < min_annualized_vol:
        return "variance_below_bound"
    if vol > max_annualized_vol:
        return "variance_above_bound"
    return ""


def run_walk_forward(log_returns: pd.Series, model: VolatilityModel, *, asset: str, min_history: int = 252,
                     retry_failed_fit: bool = True, refit_every: int | None = None,
                     sessions_per_year: int = TRADING_DAYS_PER_YEAR, max_origins: int | None = None,
                     min_annualized_vol: float = DEFAULT_MIN_ANNUALIZED_VOL,
                     max_annualized_vol: float = DEFAULT_MAX_ANNUALIZED_VOL,
                     missing_policy: str = 'error') -> WalkForwardResult:
    if getattr(model, 'input_kind', 'daily_log_returns') != 'daily_log_returns':
        raise TypeError('Realized-variance models require the target-specific volrisk.har_cli workflow')
    if missing_policy not in {'error', 'reset'}:
        raise ValueError('missing_policy must be error or reset')
    values, dates = _validate_series(log_returns, allow_missing=missing_policy == 'reset')
    if np.isnan(values).any():
        # Retain missing session positions. Restart history/filtering, never compress
        # separated observations into adjacent one-session returns or training pairs.
        valid_positions = np.flatnonzero(np.isfinite(values))
        blocks = np.split(valid_positions, np.flatnonzero(np.diff(valid_positions) > 1)+1)
        parts, remaining = [], max_origins
        for block in blocks:
            if not len(block) or remaining is not None and remaining <= 0:
                continue
            part = run_walk_forward(log_returns.iloc[block], model, asset=asset, min_history=min_history,
                retry_failed_fit=retry_failed_fit, refit_every=refit_every, sessions_per_year=sessions_per_year,
                max_origins=remaining, min_annualized_vol=min_annualized_vol, max_annualized_vol=max_annualized_vol)
            part.forecasts['origin_index'] = part.forecasts['origin_index'].astype(int) + int(block[0])
            part.fits['origin_index'] = part.fits['origin_index'].astype(int) + int(block[0])
            parts.append(part)
            if remaining is not None:
                remaining -= len(part.forecasts)
        fc, fits, summaries = combine_results(parts)
        summary = {'asset': asset, 'model': model.name, 'n_observations': int(np.isfinite(values).sum()),
            'required_history': max(min_history, model.min_observations), 'first_origin_index': int(fc.origin_index.min()) if len(fc) else None,
            'refit_every': model.refit_every if refit_every is None else refit_every, 'retry_failed_fit': retry_failed_fit,
            'gap_dates': dates[np.isnan(values)].strftime('%Y-%m-%d').tolist(), 'contiguous_segments': len(blocks),
            'invalid_forecast_flags': {}}
        for key in ('n_origins', 'n_valid_forecasts', 'n_missing_forecasts', 'fit_attempts', 'fit_failures',
                    'fit_warnings', 'fit_nonconverged', 'runtime_seconds'):
            summary[key] = sum(s[key] for s in summaries)
        for s in summaries:
            for flag, count in s['invalid_forecast_flags'].items():
                summary['invalid_forecast_flags'][flag] = summary['invalid_forecast_flags'].get(flag, 0)+count
        return WalkForwardResult(asset, model.metadata(), fc, fits, summary)
    n = values.size
    required = max(int(min_history), int(model.min_observations))
    refit_every = int(model.refit_every if refit_every is None else refit_every)
    if refit_every < 1:
        raise ValueError("refit_every must be at least 1")
    model.reset()
    metadata = model.metadata()
    records, fit_records = [], []
    last_fit_index = None
    fit_ok = False
    last_report: FitReport | None = None
    started = time.perf_counter()
    first_origin = required - 1
    origins = range(first_origin, n) if first_origin < n else range(0)
    if max_origins is not None:
        origins = range(first_origin, min(n, first_origin + int(max_origins))) if first_origin < n else range(0)
    for i in origins:
        history = values[: i + 1]
        history_dates = dates[: i + 1]
        due = (last_fit_index is None or (i - last_fit_index) >= refit_every or not model.supports_update
               or (not fit_ok and retry_failed_fit))
        tick = time.perf_counter()
        if due:
            try:
                report = model.fit(history, history_dates)
            except Exception as exc:  # noqa: BLE001 - every estimation failure must be recorded, not propagated
                report = FitReport(status=FIT_FAILED, message=f"{type(exc).__name__}: {exc}", converged=False)
            fit_ok = report.usable
            last_fit_index = i
            last_report = report
            diagnostics = report.diagnostics or {}
            fit_records.append({
                "asset": asset, "model": model.name, "origin_date": dates[i], "origin_index": i,
                "status": report.status, "message": report.message, "converged": report.converged,
                "params": params_to_json(report.params), "diagnostics": json.dumps(_json_ready(diagnostics), sort_keys=True),
                "training_start": report.training_start, "training_end": report.training_end,
                "training_observations": report.training_observations, "runtime_seconds": report.runtime_seconds,
                "boundary_flags": ";".join(diagnostics.get("boundary_flags", []) or []),
                "persistence": diagnostics.get("persistence", np.nan),
            })
        elif fit_ok:
            try:
                model.update(values[i], dates[i])
            except Exception as exc:  # noqa: BLE001
                fit_ok = False
                last_report = FitReport(status=FIT_FAILED, message=f"update failed: {type(exc).__name__}: {exc}",
                                        converged=False)
        variance = np.nan
        if fit_ok:
            try:
                variance = float(np.asarray(model.forecast(1), dtype=float)[0])
            except Exception as exc:  # noqa: BLE001
                fit_ok = False
                last_report = FitReport(status=FIT_FAILED, message=f"forecast failed: {type(exc).__name__}: {exc}",
                                        converged=False)
                variance = np.nan
        if fit_ok:
            flag = classify_forecast(variance, sessions_per_year, min_annualized_vol, max_annualized_vol)
        else:
            flag = "no_usable_state"
        valid = flag == ""
        if not valid:
            variance = np.nan
            if fit_ok:
                # An out-of-bounds forecast marks the state unusable: the next origin re-estimates
                # (when retry_failed_fit is on) instead of propagating an explosive recursion.
                fit_ok = False
                last_report = FitReport(status=FIT_FAILED, message=f"invalid forecast: {flag}", converged=False,
                                        params=model.params)
        runtime = time.perf_counter() - tick
        has_target = i + 1 < n
        report = last_report
        records.append({
            "asset": asset, "model": model.name, "model_family": model.family, "model_version": model.version,
            "origin_date": dates[i], "target_date": dates[i + 1] if has_target else pd.NaT, "origin_index": i,
            "target_observed": has_target, "forecast_variance": variance,
            "forecast_volatility_annualized": annualized_volatility(variance, sessions_per_year) if valid else np.nan,
            "forecast_valid": valid, "forecast_flag": flag,
            "realized_log_return": values[i + 1] if has_target else np.nan,
            "realized_squared_return": values[i + 1] ** 2 if has_target else np.nan,
            "training_start": None if report is None else report.training_start,
            "training_end": None if report is None else report.training_end,
            "training_observations": 0 if report is None else int(report.training_observations),
            "last_fit_date": dates[last_fit_index] if last_fit_index is not None else pd.NaT,
            "sessions_since_fit": (i - last_fit_index) if last_fit_index is not None else -1,
            "fit_status": FIT_FAILED if report is None else report.status,
            "fit_message": "" if report is None else report.message,
            "converged": None if report is None else report.converged,
            "params": params_to_json(model.params if fit_ok else (report.params if report else {})),
            "model_state": params_to_json(model.state_diagnostics() if fit_ok else {}),
            "runtime_seconds": runtime,
        })
    forecasts = pd.DataFrame.from_records(records, columns=FORECAST_COLUMNS) if records else _empty_forecasts()
    fits = pd.DataFrame.from_records(fit_records, columns=FIT_COLUMNS)
    total_runtime = time.perf_counter() - started
    n_fits = len(fits)
    summary = {
        "asset": asset, "model": model.name, "n_observations": int(n), "required_history": int(required),
        "first_origin_index": int(first_origin), "n_origins": int(len(forecasts)),
        "n_valid_forecasts": int(forecasts["forecast_valid"].sum()) if len(forecasts) else 0,
        "n_missing_forecasts": int((~forecasts["forecast_valid"].astype(bool)).sum()) if len(forecasts) else 0,
        "invalid_forecast_flags": ({str(k): int(v) for k, v in forecasts.loc[~forecasts["forecast_valid"].astype(bool),
                                                                              "forecast_flag"].value_counts().items()}
                                   if len(forecasts) else {}),
        "fit_attempts": int(n_fits),
        "fit_failures": int((fits["status"] == FIT_FAILED).sum()) if n_fits else 0,
        "fit_warnings": int((fits["status"] == "warning").sum()) if n_fits else 0,
        "fit_nonconverged": int(((fits["status"] != FIT_FAILED) & (fits["converged"] == False)).sum()) if n_fits else 0,  # noqa: E712
        "refit_every": refit_every, "retry_failed_fit": bool(retry_failed_fit),
        "runtime_seconds": float(total_runtime),
    }
    return WalkForwardResult(asset=asset, model=metadata, forecasts=forecasts, fits=fits, summary=summary)


def assign_periods(frame: pd.DataFrame, splits: PeriodSplits, date_column: str = "target_date") -> pd.DataFrame:
    out = frame.copy()
    out["period"] = splits.label(out[date_column].fillna(pd.Timestamp("1900-01-01")))
    out.loc[out[date_column].isna(), "period"] = PERIOD_UNASSIGNED
    return out


def mark_common_dates(frame: pd.DataFrame) -> pd.DataFrame:
    """``common`` is True on (asset, target_date) rows where every model in the frame has a valid, observed forecast."""
    out = frame.copy()
    models = sorted(out["model"].unique())
    usable = out[out["forecast_valid"].astype(bool) & out["target_observed"].astype(bool)]
    counts = usable.groupby(["asset", "target_date"])["model"].nunique()
    complete = counts[counts == len(models)].index
    key = pd.MultiIndex.from_frame(out[["asset", "target_date"]])
    out["common"] = key.isin(complete) & out["forecast_valid"].astype(bool) & out["target_observed"].astype(bool)
    return out


def combine_results(results: list[WalkForwardResult]) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    forecasts = pd.concat([r.forecasts for r in results], ignore_index=True) if results else _empty_forecasts()
    fits = pd.concat([r.fits for r in results], ignore_index=True) if results else pd.DataFrame(columns=FIT_COLUMNS)
    return forecasts, fits, [r.summary for r in results]
