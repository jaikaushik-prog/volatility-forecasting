from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd
import pytest

from volrisk.data.models import ASSETS
from volrisk.data.normalization import normalize_yfinance
from volrisk.data.validation import validate


def check(frame, settings):
    data = normalize_yfinance(frame, ASSETS[0], settings.start, settings.end)
    return data, validate(data, ASSETS[0], settings.start, settings.end, settings.validation)


def test_clean_data_passes_with_first_return_missing(raw_frame, settings):
    _, report = check(raw_frame, settings)
    assert report["status"] == "passed"
    assert report["observation_count"] == 3
    assert report["simple_return_count"] == report["log_return_count"] == 2
    assert report["missing_or_invalid_price_count"] == 0


def test_crisis_move_flagged_but_preserved(raw_frame, settings):
    raw_frame["Close"] = [100, 75, 80]
    data, report = check(raw_frame, settings)
    assert data.frame["price"].tolist() == [100, 75, 80]
    assert report["extreme_return_count"] == 1
    assert report["status"] == "warning"
    assert next(i for i in report["issues"] if i["code"] == "extreme_return")["observations"][0]["simple_return"] == -.25


@pytest.mark.parametrize("bad,code", [(np.nan, "missing_or_invalid_price"), (np.inf, "nonfinite_price"),
                                      (0, "nonpositive_price"), (-10, "nonpositive_price")])
def test_invalid_prices_fail(raw_frame, settings, bad, code):
    raw_frame["Close"] = [100, bad, 110]
    _, report = check(raw_frame, settings)
    assert report["status"] == "failed"
    assert code in {i["code"] for i in report["issues"]}


def test_gap_staleness_and_partial_coverage(raw_frame, settings):
    raw_frame["Close"] = [100, 100, 100]
    raw_frame.index = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-20"])
    wide = replace(settings, start=date(2023, 1, 1), end=date(2024, 2, 28))
    _, report = check(raw_frame, wide)
    assert {"long_date_gap", "stale_price_run", "incomplete_boundary_coverage"} <= {i["code"] for i in report["issues"]}
    assert report["long_gap_count"] == 1
    assert report["stale_run_count"] == 1


def test_holiday_candidate_is_not_confirmed_missing_session(raw_frame, settings):
    holiday = replace(settings, start=date(2024, 1, 1))
    _, report = check(raw_frame, holiday)
    candidate = next(i for i in report["issues"] if i["code"] == "unobserved_weekdays")
    assert candidate["dates"] == ["2024-01-01"]
    assert candidate["severity"] == "info"
    assert report["status"] == "passed"


def test_post_normalization_duplicate_order_and_return_corruption_detected(raw_frame, settings):
    data = normalize_yfinance(raw_frame, ASSETS[0], settings.start, settings.end)
    data.frame = data.frame.iloc[[2, 0, 0]].reset_index(drop=True)
    report = validate(data, ASSETS[0], settings.start, settings.end, settings.validation)
    assert report["status"] == "failed"
    assert {"duplicate_dates", "non_monotonic_dates", "invalid_returns"} <= {i["code"] for i in report["issues"]}


def test_empty_interval_cannot_pass(raw_frame, settings):
    future = replace(settings, start=date(2025, 1, 1), end=date(2025, 1, 5))
    _, report = check(raw_frame, future)
    assert report["status"] == "failed"
    assert report["observation_count"] == 0


def test_low_observation_count_is_flagged(raw_frame, settings):
    limited = replace(settings, validation=replace(settings.validation, min_observations=10))
    _, report = check(raw_frame, limited)
    assert report["status"] == "warning"
    assert "low_observation_count" in {i["code"] for i in report["issues"]}


def test_quality_markdown_lists_crisis_dates(raw_frame, settings):
    from volrisk.data.reporting import quality_markdown
    raw_frame["Close"] = [100, 75, 80]
    _, report = check(raw_frame, settings)
    markdown = quality_markdown({"run_id":"synthetic", "start":"2024-01-02", "end":"2024-01-04", "assets":[report]})
    assert "2024-01-03" in markdown
    assert "-25.0000%" in markdown
    assert "Warning observations are retained" in markdown
