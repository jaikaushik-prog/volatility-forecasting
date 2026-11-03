"""Normalize source observations without inventing prices or aligning calendars."""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from volrisk.data.models import Asset, DataError, NormalizedData, issue
from volrisk.data.nse_csv import read_tri_csv
from volrisk.data.nse_json import read_tri_json


def _finalize(frame: pd.DataFrame, asset: Asset, start: date, end: date,
              issues: list[dict], details: dict) -> NormalizedData:
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    # Invalid dates stay visible to validation; only valid out-of-window rows are excluded.
    in_window = frame["date"].between(pd.Timestamp(start), pd.Timestamp(end))
    details["outside_requested_range"] = int((~in_window & frame["date"].notna()).sum())
    frame = frame.loc[in_window | frame["date"].isna()].copy()
    boolean_prices = frame["price"].map(lambda value: isinstance(value, (bool, np.bool_)))
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce").astype(float).mask(boolean_prices)
    duplicate_mask = frame["date"].notna() & frame.duplicated("date", keep=False)
    if duplicate_mask.any():
        duplicated = frame.loc[duplicate_mask]
        compared = [c for c in ("price", "dividends", "stock_splits", "capital_gains") if c in frame]
        conflicts = duplicated.groupby("date")[compared].nunique(dropna=False).gt(1).any(axis=1)
        if conflicts.any():
            conflict_dates = conflicts.index[conflicts].strftime("%Y-%m-%d").tolist()
            raise DataError(f"Conflicting duplicate observations on {conflict_dates}; reconcile source files before publishing")
        before = len(frame)
        # Invalid timestamps must not be collapsed together.
        frame = frame.loc[~(frame["date"].notna() & frame.duplicated("date", keep="first"))]
        issues.append(issue("identical_duplicates_collapsed", "warning",
                            "Identical overlapping observations collapsed; source snapshots remain intact.",
                            count=before - len(frame),
                            dates=duplicated["date"].drop_duplicates().dt.strftime("%Y-%m-%d").tolist()))
    frame = frame.sort_values("date", kind="stable", na_position="last").reset_index(drop=True)
    # Invalid prices are retained for inspection, but cannot create usable returns.
    prices = frame["price"].where(np.isfinite(frame["price"]) & frame["price"].gt(0))
    prices = prices.where(frame["date"].notna())
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        frame["daily_return"] = prices / prices.shift(1) - 1
        frame["log_return"] = np.log(prices / prices.shift(1))
    frame["simple_return"] = frame["daily_return"]
    frame["asset"] = asset.symbol
    frame["currency"] = asset.currency
    frame["source"] = asset.source
    frame["price_convention"] = asset.price_convention
    frame["return_interval_days"] = frame["date"].diff().dt.days.astype("Int64")
    core = ["date", "asset", "price", "daily_return", "currency", "source", "price_convention",
            "simple_return", "log_return", "return_interval_days"]
    frame = frame[core + [c for c in frame if c not in core]]
    return NormalizedData(frame, issues, details)


def normalize_yfinance(raw: pd.DataFrame, asset: Asset, start: date, end: date) -> NormalizedData:
    source = raw.copy()
    if isinstance(source.columns, pd.MultiIndex):
        symbol_levels = [i for i in range(source.columns.nlevels)
                         if asset.symbol in source.columns.get_level_values(i)]
        if len(symbol_levels) != 1:
            raise DataError(f"{asset.symbol}: cannot identify ticker in yfinance MultiIndex")
        source = source.xs(asset.symbol, axis=1, level=symbol_levels[0])
    if "Close" not in source or not isinstance(source["Close"], pd.Series):
        raise DataError(f"{asset.symbol}: exactly one auto-adjusted Close column is required")
    if not isinstance(source.index, pd.DatetimeIndex):
        raise DataError(f"{asset.symbol}: yfinance must return a DatetimeIndex")
    dates = source.index
    original_timezone = str(dates.tz) if dates.tz is not None else None
    if dates.tz is not None:
        dates = dates.tz_convert(asset.timezone).tz_localize(None)
    if not dates.dropna().equals(dates.dropna().normalize()):
        raise DataError(f"{asset.symbol}: intraday timestamps are not daily observations")
    issues = []
    if not dates.dropna().is_monotonic_increasing:
        issues.append(issue("source_non_monotonic", "warning", "Source dates were not ascending; output sorted."))
    frame = pd.DataFrame({"date": dates, "price": source["Close"].to_numpy()})
    available = []
    for original, normalized in (("Dividends", "dividends"), ("Stock Splits", "stock_splits"),
                                 ("Capital Gains", "capital_gains")):
        if original in source:
            frame[normalized] = pd.to_numeric(source[original], errors="coerce").to_numpy()
            available.append(original)
    for field in ("Dividends", "Stock Splits"):
        if field not in available:
            issues.append(issue("actions_unavailable", "warning", f"Provider omitted {field}; absence is not zero."))
    return _finalize(frame, asset, start, end, issues,
                     {"input_rows": len(raw), "available_action_columns": available,
                      "source_timezone": asset.timezone, "original_index_timezone": original_timezone,
                      "session_date_policy": "Convert aware timestamps to source exchange timezone; naive daily labels are exchange-local."})


def normalize_nifty(paths: list[Path], asset: Asset, start: date, end: date,
                    date_format: str = "") -> NormalizedData:
    if not paths:
        raise DataError("No official NIFTY 50 TRI source files supplied")
    frames, issues, files = [], [], []
    for path in sorted(paths):
        reader = read_tri_json if path.suffix.lower() == ".json" else read_tri_csv
        frame, notices, details = reader(path, date_format)
        frames.append(frame)
        issues.extend(notices)
        files.append(details)
    combined = pd.concat(frames, ignore_index=True)
    return _finalize(combined, asset, start, end, issues,
                     {"files": files, "input_rows": len(combined), "source_timezone": asset.timezone,
                      "session_date_policy": "NSE date-only observations interpreted in Asia/Kolkata."})
