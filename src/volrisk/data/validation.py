"""Conservative quality checks; flags do not trim, winsorize or impute observations."""

from datetime import date

import numpy as np
import pandas as pd

from volrisk.config import ValidationSettings
from volrisk.data.models import Asset, NormalizedData, issue


def validate(data: NormalizedData, asset: Asset, start: date, end: date,
             settings: ValidationSettings) -> dict:
    frame = data.frame
    issues = list(data.issues)
    dates = frame["date"]
    prices = pd.to_numeric(frame["price"], errors="coerce")
    valid_dates = dates.dropna()
    ordered_dates = pd.DatetimeIndex(valid_dates.unique()).sort_values()
    missing = prices.isna()
    nonfinite = prices.notna() & ~np.isfinite(prices)
    nonpositive = prices.le(0)

    def rows(mask) -> list[dict]:
        result = []
        for i in frame.index[mask]:
            row = {"row": int(i), "date": None if pd.isna(dates.loc[i]) else dates.loc[i].date().isoformat()}
            if "source_file" in frame:
                row.update(source_file=str(frame.loc[i, "source_file"]), source_row=int(frame.loc[i, "source_row"]))
            result.append(row)
        return result

    for code, mask, message in (
        ("invalid_date", dates.isna(), "Unparseable or missing dates"),
        ("missing_or_invalid_price", missing, "Missing or nonnumeric prices"),
        ("nonfinite_price", nonfinite, "Infinite prices"),
        ("nonpositive_price", nonpositive, "Zero or negative prices"),
        ("duplicate_dates", dates.notna() & dates.duplicated(keep=False), "Duplicate timestamps"),
    ):
        if mask.any():
            issues.append(issue(code, "error", message, count=int(mask.sum()), observations=rows(mask)))
    if not valid_dates.is_monotonic_increasing:
        issues.append(issue("non_monotonic_dates", "error", "Processed timestamps must be ascending"))
    if (dates.notna() & ~dates.between(pd.Timestamp(start), pd.Timestamp(end))).any():
        issues.append(issue("outside_date_range", "error", "Processed data is outside the requested range"))
    for column, expected in (("asset", asset.symbol), ("currency", asset.currency),
                              ("source", asset.source), ("price_convention", asset.price_convention)):
        if not frame[column].eq(expected).all():
            issues.append(issue("metadata_mismatch", "error", f"Unexpected {column}; expected {expected}"))
    safe_prices = prices.where(np.isfinite(prices) & prices.gt(0) & dates.notna())
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        expected_simple = safe_prices.pct_change(fill_method=None)
        expected_log = np.log(safe_prices / safe_prices.shift(1))
    for column, expected in (("simple_return", expected_simple), ("daily_return", expected_simple),
                              ("log_return", expected_log)):
        values = frame[column].to_numpy(dtype=float)
        if np.isinf(values).any() or not np.isclose(values, expected.to_numpy(),
                                                  rtol=1e-10, atol=1e-12, equal_nan=True).all():
            issues.append(issue("invalid_returns", "error", f"{column} does not match its documented definition"))
    extreme = frame["simple_return"].abs().gt(settings.extreme_simple_return)
    if extreme.any():
        observations = rows(extreme)
        for row, value in zip(observations, frame.loc[extreme, "simple_return"]):
            row["simple_return"] = float(value) if np.isfinite(value) else None
        issues.append(issue("extreme_return", "warning", "Large absolute simple returns retained for review.",
                            threshold=settings.extreme_simple_return, count=int(extreme.sum()), observations=observations))
    gaps = []
    for previous, current in zip(ordered_dates[:-1], ordered_dates[1:]):
        length = (current - previous).days
        if length > settings.max_calendar_gap_days:
            gaps.append({"previous_date": previous.date().isoformat(), "date": current.date().isoformat(),
                         "calendar_days": length})
    if gaps:
        issues.append(issue("long_date_gap", "warning", "Long gaps may represent missing sessions or market closures.",
                            count=len(gaps), gaps=gaps))
    # A weekday heuristic is transparent and deliberately NOT an exchange calendar.
    candidates = pd.bdate_range(start, end).difference(ordered_dates)
    if len(candidates):
        issues.append(issue("unobserved_weekdays", "info",
                            "Candidate gaps include exchange holidays. No verified exchange-session calendar is supplied; these are not confirmed missing trading days.",
                            count=len(candidates), dates=candidates.strftime("%Y-%m-%d").tolist()))
    stale_runs = []
    runs = safe_prices.ne(safe_prices.shift()).cumsum()
    for _, group in frame.groupby(runs, sort=False):
        if len(group) >= settings.stale_observations and np.isfinite(group["price"].iloc[0]) and group["price"].iloc[0] > 0:
            stale_runs.append({"start": group["date"].iloc[0].date().isoformat(),
                               "end": group["date"].iloc[-1].date().isoformat(),
                               "observations": len(group), "price": float(group["price"].iloc[0])})
    if stale_runs:
        issues.append(issue("stale_price_run", "warning", "Repeated identical positive prices; retained for review.",
                            count=len(stale_runs), runs=stale_runs))
    first = ordered_dates[0].date() if len(ordered_dates) else None
    last = ordered_dates[-1].date() if len(ordered_dates) else None
    if not len(frame):
        issues.append(issue("empty_data", "error", "No observations in the requested interval"))
    elif len(ordered_dates) < settings.min_observations:
        issues.append(issue("low_observation_count", "warning", "Coverage has fewer observations than configured minimum.",
                            count=len(ordered_dates), minimum=settings.min_observations))
    coverage = {"requested_start": start.isoformat(), "requested_end": end.isoformat(),
                "start_gap_calendar_days": (first - start).days if first else None,
                "end_gap_calendar_days": (end - last).days if last else None,
                "calendar_check": "Weekday candidates only; exchange holidays and special sessions are not verified."}
    if first and ((first - start).days > settings.coverage_tolerance_days or
                  (end - last).days > settings.coverage_tolerance_days):
        issues.append(issue("incomplete_boundary_coverage", "warning", "Requested date range is not fully covered within the configured tolerance.", **coverage))
    status = "failed" if any(i["severity"] == "error" for i in issues) else (
        "warning" if any(i["severity"] == "warning" for i in issues) else "passed")
    return {
        "asset": asset.symbol, "asset_name": asset.name, "currency": asset.currency,
        "source": asset.source, "price_convention": asset.price_convention,
        "earliest": first.isoformat() if first else None,
        "latest": last.isoformat() if last else None,
        "observation_count": len(frame), "unique_date_count": len(ordered_dates),
        "valid_price_count": int((np.isfinite(prices) & prices.gt(0)).sum()),
        "missing_or_invalid_price_count": int(missing.sum()),
        "invalid_price_count": int((missing | nonfinite | nonpositive).sum()),
        "invalid_date_count": int(dates.isna().sum()),
        "duplicate_date_count": int((dates.notna() & dates.duplicated(keep=False)).sum()),
        "source_duplicate_rows_collapsed": sum(i.get("count", 0) for i in issues if i["code"] == "identical_duplicates_collapsed"),
        "source_order_flag_count": sum(i["code"] == "source_non_monotonic" for i in issues),
        "nonfinite_price_count": int(nonfinite.sum()), "nonpositive_price_count": int(nonpositive.sum()),
        "extreme_return_count": int(extreme.sum()), "long_gap_count": len(gaps),
        "stale_run_count": len(stale_runs), "unobserved_weekday_count": len(candidates),
        "simple_return_count": int(frame["simple_return"].notna().sum()),
        "daily_return_count": int(frame["daily_return"].notna().sum()),
        "log_return_count": int(frame["log_return"].notna().sum()),
        "coverage": coverage, "status": status, "issues": issues,
    }
