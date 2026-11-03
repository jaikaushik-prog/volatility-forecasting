"""Forecast evaluation metrics, regime labels and statistical comparisons.

The evaluation target is the realized squared daily log return r_{t+1}^2.
It is an unbiased but very noisy observation of the latent conditional
variance (its sampling error is of the same order as the variance itself),
so loss levels must be compared across models on identical dates and
differences must be tested, not read off point estimates.

QLIKE(h, r^2) = log(h) + r^2 / h is minimized in expectation by the true
conditional variance and is robust to the noise in the proxy (Patton 2011).
It is evaluated only where the predicted variance is strictly positive and
finite.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from volrisk.forecasting.base import FIT_FAILED, FIT_WARNING, TRADING_DAYS_PER_YEAR

METRIC_COLUMNS = ["asset", "model", "period", "sample", "n_origins", "n_evaluated", "n_missing_forecast",
                  "qlike", "mse", "mae", "calibration_ratio", "mz_slope", "bias", "relative_bias",
                  "mean_forecast_vol_annualized", "realized_vol_annualized", "stability", "runtime_seconds",
                  "fit_attempts", "fit_failure_rate", "fit_warning_rate", "nonconvergence_rate", "boundary_rate",
                  "rank_qlike"]


# -- loss functions ---------------------------------------------------------------------------------------------
def qlike(predicted_variance, realized_squared) -> np.ndarray:
    h = np.asarray(predicted_variance, dtype=float)
    r2 = np.asarray(realized_squared, dtype=float)
    out = np.full(h.shape, np.nan)
    ok = np.isfinite(h) & (h > 0) & np.isfinite(r2)
    out[ok] = np.log(h[ok]) + r2[ok] / h[ok]
    return out


def squared_error(predicted_variance, realized_squared) -> np.ndarray:
    h = np.asarray(predicted_variance, dtype=float)
    r2 = np.asarray(realized_squared, dtype=float)
    return (h - r2) ** 2


def absolute_error(predicted_variance, realized_squared) -> np.ndarray:
    h = np.asarray(predicted_variance, dtype=float)
    r2 = np.asarray(realized_squared, dtype=float)
    return np.abs(h - r2)


def evaluable_rows(frame: pd.DataFrame) -> pd.Series:
    h = frame["forecast_variance"].astype(float)
    r2 = frame["realized_squared_return"].astype(float)
    return frame["forecast_valid"].astype(bool) & frame["target_observed"].astype(bool) & np.isfinite(h) & (h > 0) \
        & np.isfinite(r2)


def attach_losses(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    ok = evaluable_rows(out)
    h = out["forecast_variance"].astype(float).values
    r2 = out["realized_squared_return"].astype(float).values
    out["evaluable"] = ok
    mask = ok.values
    for column, function in (("loss_qlike", qlike), ("loss_se", squared_error), ("loss_ae", absolute_error)):
        losses = np.full(len(out), np.nan)
        with np.errstate(over="ignore"):
            losses[mask] = function(h[mask], r2[mask])
        out[column] = losses
    return out


# -- summary metrics ------------------------------------------------------------------------------------------
def _fit_statistics(fits: pd.DataFrame | None, asset: str, model: str, mask_dates=None) -> dict:
    if fits is None or fits.empty:
        return {"fit_attempts": 0, "fit_failure_rate": np.nan, "fit_warning_rate": np.nan,
                "nonconvergence_rate": np.nan, "boundary_rate": np.nan}
    rows = fits[(fits["asset"] == asset) & (fits["model"] == model)]
    if mask_dates is not None:
        rows = rows[rows["origin_date"].isin(mask_dates)]
    n = len(rows)
    if n == 0:
        return {"fit_attempts": 0, "fit_failure_rate": np.nan, "fit_warning_rate": np.nan,
                "nonconvergence_rate": np.nan, "boundary_rate": np.nan}
    return {"fit_attempts": int(n),
            "fit_failure_rate": float((rows["status"] == FIT_FAILED).mean()),
            "fit_warning_rate": float((rows["status"] == FIT_WARNING).mean()),
            "nonconvergence_rate": float(((rows["status"] != FIT_FAILED) & (rows["converged"] == False)).mean()),  # noqa: E712
            "boundary_rate": float((rows["boundary_flags"].fillna("").astype(str) != "").mean())}


def stability(forecast_variance: pd.Series) -> float:
    """Mean absolute change of log forecast variance between consecutive origins."""
    h = np.asarray(forecast_variance, dtype=float)
    h = h[np.isfinite(h) & (h > 0)]
    if h.size < 2:
        return np.nan
    return float(np.mean(np.abs(np.diff(np.log(h)))))


def summarize_group(frame: pd.DataFrame, fits: pd.DataFrame | None = None, asset: str = "", model: str = "",
                    period: str = "all", sample: str = "all", sessions_per_year: int = TRADING_DAYS_PER_YEAR) -> dict:
    rows = frame.sort_values("origin_date")
    ok = evaluable_rows(rows)
    h = rows.loc[ok, "forecast_variance"].astype(float).values
    r2 = rows.loc[ok, "realized_squared_return"].astype(float).values
    n = int(ok.sum())
    record = {"asset": asset, "model": model, "period": period, "sample": sample, "n_origins": int(len(rows)),
              "n_evaluated": n, "n_missing_forecast": int((~rows["forecast_valid"].astype(bool)).sum())}
    if n == 0:
        record.update({k: np.nan for k in ("qlike", "mse", "mae", "calibration_ratio", "mz_slope", "bias",
                                           "relative_bias", "mean_forecast_vol_annualized", "realized_vol_annualized",
                                           "stability")})
    else:
        mean_h, mean_r2 = float(np.mean(h)), float(np.mean(r2))
        slope = np.nan
        with np.errstate(over="ignore", invalid="ignore"):
            var_h = float(np.var(h, ddof=1)) if n > 2 else 0.0
            if n > 2 and np.isfinite(var_h) and var_h > 0:
                slope = float(np.cov(h, r2, ddof=1)[0, 1] / var_h)
            record.update({
                "qlike": float(np.mean(qlike(h, r2))), "mse": float(np.mean(squared_error(h, r2))),
                "mae": float(np.mean(absolute_error(h, r2))),
                "calibration_ratio": mean_r2 / mean_h, "mz_slope": slope,
                "bias": mean_h - mean_r2, "relative_bias": mean_h / mean_r2 - 1.0,
                "mean_forecast_vol_annualized": float(np.mean(np.sqrt(h * sessions_per_year))),
                "realized_vol_annualized": float(np.sqrt(mean_r2 * sessions_per_year)),
                "stability": stability(rows["forecast_variance"]),
            })
    record["runtime_seconds"] = float(rows["runtime_seconds"].astype(float).sum())
    mask_dates = rows["origin_date"]
    record.update(_fit_statistics(fits, asset, model, mask_dates))
    return record


def summarize_metrics(forecasts: pd.DataFrame, fits: pd.DataFrame | None = None, *, periods=("all",),
                      samples=("all", "common"), sessions_per_year: int = TRADING_DAYS_PER_YEAR) -> pd.DataFrame:
    """Per asset/model/period/sample metrics. ``sample='common'`` restricts to rows where ``common`` is True."""
    records = []
    frame = forecasts.copy()
    if "period" not in frame.columns:
        frame["period"] = "all"
    if "common" not in frame.columns:
        frame["common"] = frame["forecast_valid"].astype(bool) & frame["target_observed"].astype(bool)
    for asset, by_asset in frame.groupby("asset", sort=True):
        for period in periods:
            in_period = by_asset if period == "all" else by_asset[by_asset["period"] == period]
            for sample in samples:
                subset = in_period if sample == "all" else in_period[in_period["common"].astype(bool)]
                for model, rows in subset.groupby("model", sort=True):
                    record = summarize_group(rows, fits, asset=asset, model=model, period=period, sample=sample,
                                             sessions_per_year=sessions_per_year)
                    # Common-date loss selection must not hide failed fit attempts.
                    attempted = in_period[in_period.model.eq(model)]
                    record.update(_fit_statistics(fits, asset, model, attempted.origin_date))
                    record['runtime_seconds'] = float(attempted.runtime_seconds.sum())
                    records.append(record)
    table = pd.DataFrame.from_records(records, columns=METRIC_COLUMNS)
    if table.empty:
        return table
    table["rank_qlike"] = table.groupby(["asset", "period", "sample"])["qlike"].rank(method="min")
    return table


# -- regimes ----------------------------------------------------------------------------------------------
def ex_ante_volatility_regimes(log_returns: pd.Series, window: int = 60, min_history: int = 252) -> pd.Series:
    """Regime known at the origin: tercile of trailing-window variance relative to its own past values.

    Cut-offs at origin t use only trailing variances observed at or before t (expanding quantiles), so the
    label never depends on later data.
    """
    trailing = log_returns.rolling(window).var(ddof=1)
    labels = pd.Series("unknown", index=log_returns.index, dtype=object)
    values = trailing.values
    for i in range(len(values)):
        if i + 1 < min_history or not np.isfinite(values[i]):
            continue
        past = values[: i + 1]
        past = past[np.isfinite(past)]
        low, high = np.quantile(past, [1 / 3, 2 / 3])
        labels.iloc[i] = "low" if values[i] <= low else ("high" if values[i] > high else "medium")
    labels.name = "ex_ante_regime"
    return labels


def retrospective_labels(log_returns: pd.Series, event_windows: list[dict] | None = None, shock_multiple: float = 4.0,
                         trailing_window: int = 60, recovery_sessions: int = 60) -> pd.DataFrame:
    """Labels that use information after the origin (for descriptive analysis only).

    ``shock`` marks target sessions whose absolute return exceeds ``shock_multiple`` trailing standard
    deviations; ``post_shock_recovery`` marks the ``recovery_sessions`` sessions after each shock; ``event``
    carries the name of a configured historical window containing the target date.
    """
    r = log_returns.astype(float)
    trailing_sd = np.sqrt(r.rolling(trailing_window).var(ddof=1).shift(1))
    shock = (r.abs() > shock_multiple * trailing_sd).fillna(False)
    recovery = pd.Series(False, index=r.index)
    positions = np.flatnonzero(shock.values)
    for pos in positions:
        recovery.iloc[pos + 1: pos + 1 + recovery_sessions] = True
    recovery &= ~shock
    event = pd.Series("", index=r.index, dtype=object)
    for window in event_windows or []:
        start, end = pd.Timestamp(window["start"]), pd.Timestamp(window["end"])
        mask = (r.index >= start) & (r.index <= end)
        event[mask] = np.where(event[mask] == "", window["name"], event[mask] + "|" + window["name"])
    return pd.DataFrame({"shock": shock.values, "post_shock_recovery": recovery.values, "event": event.values},
                        index=r.index)


# -- statistical comparisons ---------------------------------------------------------------------------------
def newey_west_variance(d: np.ndarray, lags: int) -> float:
    d = np.asarray(d, dtype=float)
    n = d.size
    centered = d - d.mean()
    variance = float(np.dot(centered, centered) / n)
    for lag in range(1, lags + 1):
        weight = 1.0 - lag / (lags + 1.0)
        cov = float(np.dot(centered[lag:], centered[:-lag]) / n)
        variance += 2.0 * weight * cov
    return variance


def diebold_mariano(loss_a, loss_b, hac_lags: int | None = None) -> dict:
    """DM test of H0: E[loss_a - loss_b] = 0 with a Newey-West long-run variance. Negative mean favours A."""
    a = np.asarray(loss_a, dtype=float)
    b = np.asarray(loss_b, dtype=float)
    ok = np.isfinite(a) & np.isfinite(b)
    d = a[ok] - b[ok]
    n = d.size
    if n < 10:
        return {"n": int(n), "mean_diff": np.nan, "t_stat": np.nan, "p_value": np.nan, "hac_lags": 0}
    if hac_lags is None:
        hac_lags = int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))
    lrv = newey_west_variance(d, hac_lags)
    if lrv <= 0:
        return {"n": int(n), "mean_diff": float(d.mean()), "t_stat": np.nan, "p_value": np.nan, "hac_lags": hac_lags}
    t_stat = float(d.mean() / np.sqrt(lrv / n))
    p_value = float(2.0 * stats.t.sf(abs(t_stat), df=n - 1))
    return {"n": int(n), "mean_diff": float(d.mean()), "t_stat": t_stat, "p_value": p_value, "hac_lags": hac_lags}


def stationary_bootstrap_indices(n: int, expected_block: float, rng: np.random.Generator) -> np.ndarray:
    p = 1.0 / float(expected_block)
    idx = np.empty(n, dtype=int)
    idx[0] = rng.integers(n)
    new_block = rng.random(n) < p
    starts = rng.integers(0, n, size=n)
    for k in range(1, n):
        idx[k] = starts[k] if new_block[k] else (idx[k - 1] + 1) % n
    return idx


def bootstrap_mean_difference(loss_a, loss_b, *, expected_block: float = 20.0, draws: int = 1000,
                              seed: int = 20261103) -> dict:
    """Stationary block bootstrap (Politis & Romano) for the mean loss differential; two-sided p-value."""
    a = np.asarray(loss_a, dtype=float)
    b = np.asarray(loss_b, dtype=float)
    ok = np.isfinite(a) & np.isfinite(b)
    d = a[ok] - b[ok]
    n = d.size
    if n < 10:
        return {"boot_p_value": np.nan, "ci_low": np.nan, "ci_high": np.nan, "draws": 0}
    rng = np.random.default_rng(seed)
    observed = d.mean()
    centered = d - observed
    means = np.empty(draws)
    for k in range(draws):
        means[k] = centered[stationary_bootstrap_indices(n, expected_block, rng)].mean()
    p_value = float(np.mean(np.abs(means) >= abs(observed)))
    low, high = np.quantile(means, [0.025, 0.975])
    return {"boot_p_value": p_value, "ci_low": float(observed + low), "ci_high": float(observed + high),
            "draws": int(draws)}


def holm_adjust(p_values) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    adjusted = np.full(p.shape, np.nan)
    ok = np.isfinite(p)
    if not ok.any():
        return adjusted
    values = p[ok]
    order = np.argsort(values)
    m = values.size
    running = 0.0
    out = np.empty(m)
    for rank, position in enumerate(order):
        running = max(running, (m - rank) * values[position])
        out[position] = min(1.0, running)
    adjusted[ok] = out
    return adjusted


def compare_to_benchmark(frame: pd.DataFrame, benchmark: str, *, loss: str = "loss_qlike", by=("asset", "period"),
                         expected_block: float = 20.0, draws: int = 1000, seed: int = 20261103,
                         alpha: float = 0.05) -> pd.DataFrame:
    """DM and block-bootstrap tests of each model against ``benchmark`` on common dates, with Holm adjustment.

    ``frame`` must already carry loss columns and the ``common`` flag (see :func:`attach_losses`).
    """
    records = []
    data = frame[frame["common"].astype(bool)]
    for keys, group in data.groupby(list(by), sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        wide = group.pivot(index="target_date", columns="model", values=loss).sort_index()
        if benchmark not in wide.columns:
            continue
        base = wide[benchmark].values
        for model in wide.columns:
            if model == benchmark:
                continue
            dm = diebold_mariano(wide[model].values, base)
            boot = bootstrap_mean_difference(wide[model].values, base, expected_block=expected_block, draws=draws,
                                             seed=seed)
            records.append(dict(zip(by, keys)) | {"model": model, "benchmark": benchmark, "loss": loss,
                                                   "n": dm["n"], "mean_loss_diff": dm["mean_diff"],
                                                   "dm_t_stat": dm["t_stat"], "dm_p_value": dm["p_value"],
                                                   "hac_lags": dm["hac_lags"], "boot_p_value": boot["boot_p_value"],
                                                   "boot_ci_low": boot["ci_low"], "boot_ci_high": boot["ci_high"]})
    table = pd.DataFrame.from_records(records)
    if table.empty:
        return table
    table["dm_p_holm"] = np.nan
    table["boot_p_holm"] = np.nan
    for _, idx in table.groupby(list(by)).groups.items():
        table.loc[idx, "dm_p_holm"] = holm_adjust(table.loc[idx, "dm_p_value"].values)
        table.loc[idx, "boot_p_holm"] = holm_adjust(table.loc[idx, "boot_p_value"].values)
    table["better_than_benchmark"] = table["mean_loss_diff"] < 0
    table["significant_holm_5pct"] = (table["dm_p_holm"] < alpha) & (table["boot_p_holm"] < alpha)
    return table


def pairwise_dm_matrix(frame: pd.DataFrame, *, loss: str = "loss_qlike", by=("asset", "period")) -> pd.DataFrame:
    records = []
    data = frame[frame["common"].astype(bool)]
    for keys, group in data.groupby(list(by), sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        wide = group.pivot(index="target_date", columns="model", values=loss).sort_index()
        for a in wide.columns:
            for b in wide.columns:
                if a >= b:
                    continue
                dm = diebold_mariano(wide[a].values, wide[b].values)
                records.append(dict(zip(by, keys)) | {"model_a": a, "model_b": b, "n": dm["n"],
                                                       "mean_loss_diff_a_minus_b": dm["mean_diff"],
                                                       "dm_t_stat": dm["t_stat"], "dm_p_value": dm["p_value"]})
    table = pd.DataFrame.from_records(records)
    if not table.empty:
        table['dm_p_holm'] = np.nan
        for _, idx in table.groupby(list(by)).groups.items():
            table.loc[idx, 'dm_p_holm'] = holm_adjust(table.loc[idx, 'dm_p_value'].values)
    return table
