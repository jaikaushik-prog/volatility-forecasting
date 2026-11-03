import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from volrisk.data.models import ASSETS, DataError
from volrisk.data.normalization import normalize_yfinance


def normalize(frame, settings):
    return normalize_yfinance(frame, ASSETS[0], settings.start, settings.end)


def test_simple_log_and_legacy_alias_are_distinct(raw_frame, settings):
    raw_frame["Close"] = [100.0, 110.0, 99.0]
    original = raw_frame.copy(deep=True)
    frame = normalize(raw_frame, settings).frame
    np.testing.assert_allclose(frame["simple_return"], [np.nan, .1, -.1], equal_nan=True)
    np.testing.assert_allclose(frame["log_return"], [np.nan, np.log(1.1), np.log(.9)], equal_nan=True)
    np.testing.assert_allclose(frame["daily_return"], frame["simple_return"], equal_nan=True)
    assert frame["currency"].eq("USD").all()
    assert frame["dividends"].tolist() == [0.0, .2, 0.0]
    assert_frame_equal(raw_frame, original)
    assert not np.isclose(frame["simple_return"].iloc[-1], frame["log_return"].iloc[-1])


def test_missing_price_is_not_forward_filled(raw_frame, settings):
    raw_frame.loc[raw_frame.index[1], "Close"] = np.nan
    frame = normalize(raw_frame, settings).frame
    assert frame["price"].isna().sum() == 1
    assert frame["simple_return"].isna().all()
    assert frame["log_return"].isna().all()


@pytest.mark.parametrize("bad", [0, -10, np.inf, "not a number", True])
def test_invalid_price_does_not_create_usable_returns(raw_frame, settings, bad):
    raw_frame["Close"] = pd.Series([100, bad, 110], index=raw_frame.index, dtype=object)
    frame = normalize(raw_frame, settings).frame
    assert frame["simple_return"].isna().all()
    assert frame["log_return"].isna().all()


@pytest.mark.parametrize("ticker_first", [False, True])
def test_yfinance_multiindex_variants(raw_frame, settings, ticker_first):
    frame = raw_frame.copy()
    frame.columns = pd.MultiIndex.from_tuples(
        [("SPY", c) if ticker_first else (c, "SPY") for c in raw_frame.columns])
    assert normalize(frame, settings).frame["price"].tolist() == [100, 101, 99]


def test_exchange_local_dates_preserved_and_source_order_flagged(raw_frame, settings):
    raw_frame.index = raw_frame.index.tz_localize("America/New_York")
    data = normalize(raw_frame.iloc[::-1], settings)
    assert data.frame["date"].dt.strftime("%Y-%m-%d").tolist() == ["2024-01-02", "2024-01-03", "2024-01-04"]
    assert data.frame["date"].dt.tz is None
    assert "source_non_monotonic" in {i["code"] for i in data.issues}


def test_filter_before_returns_and_no_calendar_expansion(raw_frame, settings):
    raw_frame.index = pd.DatetimeIndex(["2023-12-29", "2024-01-02", "2024-01-04"])
    data = normalize(raw_frame, settings)
    assert len(data.frame) == 2
    assert pd.isna(data.frame["simple_return"].iloc[0])
    assert data.frame["return_interval_days"].iloc[1] == 2
    assert data.details["outside_requested_range"] == 1


def test_identical_duplicates_flagged_and_conflicts_rejected(raw_frame, settings):
    data = normalize(pd.concat([raw_frame, raw_frame.iloc[[0]]]), settings)
    assert len(data.frame) == 3
    assert any(i["code"] == "identical_duplicates_collapsed" and i["count"] == 1 for i in data.issues)
    conflict = raw_frame.iloc[[0]].copy()
    conflict["Close"] = 900
    with pytest.raises(DataError, match="Conflicting duplicate"):
        normalize(pd.concat([raw_frame, conflict]), settings)


def test_missing_actions_are_unknown_not_zero(raw_frame, settings):
    data = normalize(raw_frame[["Close"]], settings)
    assert "dividends" not in data.frame
    assert len([i for i in data.issues if i["code"] == "actions_unavailable"]) == 2


def test_intraday_data_rejected(raw_frame, settings):
    raw_frame.index += pd.Timedelta(hours=12)
    with pytest.raises(DataError, match="intraday"):
        normalize(raw_frame, settings)
