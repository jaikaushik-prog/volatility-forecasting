"""Canonical-dataset loader tests with synthetic frames in temporary directories."""
import json

import numpy as np
import pandas as pd
import pytest

from volrisk.data.returns import load_canonical_returns, returns_from_frame


def canonical_frame(asset="SPY", n=400, seed=0, currency="USD"):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n)
    log_r = rng.standard_normal(n) * 0.01
    log_r[0] = np.nan
    prices = 100 * np.exp(np.nancumsum(log_r))
    frame = pd.DataFrame({"date": dates, "asset": asset, "price": prices, "daily_return": np.expm1(log_r),
                          "currency": currency, "source": "synthetic", "price_convention": "synthetic",
                          "simple_return": np.expm1(log_r), "log_return": log_r, "return_interval_days": 1,
                          "return_usable": ~np.isnan(log_r), "return_exclusion_reason": np.where(np.isnan(log_r), "first_observation", ""),
                          "audit_status": "PASS", "review_reasons": "", "calendar_interval_verified": True,
                          "source_timezone": "America/New_York"})
    return frame


def test_returns_from_frame_separates_log_and_simple_returns():
    frame = canonical_frame()
    series = returns_from_frame(frame, "SPY")
    assert series.n_rows == 400 and series.n_usable == 399 and series.contiguous
    assert series.dropped["total_dropped"] == 1 and series.dropped["reasons"] == {"first_observation": 1}
    assert series.log_returns.index[0] == frame["date"].iloc[1]
    np.testing.assert_allclose(series.simple_returns.values, np.expm1(series.log_returns.values))
    assert series.log_returns.name == "log_return" and series.simple_returns.name == "simple_return"
    assert series.provenance()["estimation_series"].startswith("log_return")


def test_interior_gap_is_reported_not_filled():
    frame = canonical_frame()
    frame.loc[100, ["return_usable", "log_return", "simple_return"]] = [False, np.nan, np.nan]
    series = returns_from_frame(frame, "SPY")
    assert not series.contiguous and series.n_usable == 398
    assert frame["date"].iloc[100] not in series.log_returns.index
    with pytest.raises(ValueError):
        returns_from_frame(frame.assign(asset="VT"), "SPY")
    with pytest.raises(ValueError):
        returns_from_frame(pd.concat([frame, frame.iloc[[5]]]), "SPY")


def test_load_canonical_returns_from_latest_audit(tmp_path, audit_pointer):
    for asset in ("SPY", "NIFTY50_TRI"):
        (tmp_path / "data").mkdir(exist_ok=True)
        canonical_frame(asset, currency="INR" if asset.startswith("NIFTY") else "USD").to_parquet(
            tmp_path / "data" / f"{asset}.parquet", index=False)
    (tmp_path / "reports").mkdir()
    pointer = tmp_path / "reports" / "latest_audit.json"
    audit_pointer(tmp_path, {a: str(tmp_path / 'data' / f'{a}.parquet') for a in ('SPY', 'NIFTY50_TRI')}, audit_id='abc')
    series = load_canonical_returns(pointer)
    assert set(series) == {"SPY", "NIFTY50_TRI"} and series["NIFTY50_TRI"].currency == "INR"
    assert series["SPY"].audit_id == "abc" and len(series["SPY"].source_sha256) == 64
    only = load_canonical_returns(pointer, ["SPY"])
    assert list(only) == ["SPY"]
    with pytest.raises(KeyError):
        load_canonical_returns(pointer, ["VT"])
    pointer.write_text(json.dumps({"audit_id": "abc", "complete": False, "canonical": {}}))
    with pytest.raises(ValueError):
        load_canonical_returns(pointer)


def test_calendar_uncertainty_preserved_as_gap_without_changing_source():
    frame = canonical_frame()
    frame.loc[100, 'calendar_interval_verified'] = False
    original = frame.copy(deep=True)
    series = returns_from_frame(frame, 'SPY', preserve_gaps=True, require_verified_intervals=True)
    assert np.isnan(series.log_returns.loc[frame.date.iloc[100]])
    assert not series.contiguous and series.dropped['unverified_return_intervals'] == 1
    assert series.log_returns.loc[frame.date.iloc[101]] == frame.log_return.iloc[101]
    pd.testing.assert_frame_equal(frame, original)


def test_unverifiable_or_tampered_canonical_fails(tmp_path, audit_pointer):
    (tmp_path / 'reports').mkdir()
    path = tmp_path / 'synthetic.parquet'
    canonical_frame().to_parquet(path)
    pointer = audit_pointer(tmp_path, {'SPY': str(path)})
    frame = canonical_frame()
    frame.loc[10, 'log_return'] = .5
    frame.to_parquet(path)
    with pytest.raises(ValueError, match='canonical hash'):
        load_canonical_returns(pointer)
    pointer.write_text(json.dumps({'complete': True, 'canonical': {'SPY': str(path)}}))
    with pytest.raises(ValueError, match='manifest required'):
        load_canonical_returns(pointer)
