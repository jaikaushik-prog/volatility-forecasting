"""Metric, regime, statistical-test and ML-feature alignment tests on synthetic data."""
import numpy as np
import pandas as pd
import pytest

from volrisk.evaluation.metrics import (attach_losses, bootstrap_mean_difference, compare_to_benchmark, diebold_mariano,
                                        ex_ante_volatility_regimes, holm_adjust, qlike, retrospective_labels,
                                        stability, summarize_metrics)
from volrisk.forecasting.ml import FEATURE_NAMES, build_lagged_features


def make_frame(n=400, seed=3):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n + 1)
    r = rng.standard_normal(n + 1) * 0.01
    rows = []
    for model, scale in (("good", 1.0), ("bad", 3.0)):
        for i in range(n):
            h = (0.01 * scale) ** 2
            rows.append({"asset": "SYN", "model": model, "origin_date": dates[i], "target_date": dates[i + 1],
                         "target_observed": True, "forecast_variance": h, "forecast_valid": True,
                         "realized_log_return": r[i + 1], "realized_squared_return": r[i + 1] ** 2,
                         "runtime_seconds": 0.0, "period": "development", "common": True})
    return pd.DataFrame(rows)


def test_qlike_formula_and_domain():
    h = np.array([1e-4, 2e-4, 0.0, -1e-4, np.nan, np.inf])
    r2 = np.full(6, 1e-4)
    out = qlike(h, r2)
    assert out[0] == pytest.approx(np.log(1e-4) + 1.0)
    assert out[1] == pytest.approx(np.log(2e-4) + 0.5)
    assert np.isnan(out[2:]).all()
    # QLIKE is minimized at the true variance in expectation
    grid = np.array([0.5e-4, 1e-4, 2e-4])
    assert np.argmin([np.mean(qlike(np.full(1000, g), np.random.default_rng(0).standard_normal(1000) ** 2 * 1e-4))
                      for g in grid]) == 1


def test_summary_metrics_and_ranking():
    frame = attach_losses(make_frame())
    table = summarize_metrics(frame, periods=("development",), samples=("common",))
    good = table[table["model"] == "good"].iloc[0]
    bad = table[table["model"] == "bad"].iloc[0]
    assert good["n_evaluated"] == 400 and good["qlike"] < bad["qlike"]
    assert good["rank_qlike"] == 1 and bad["rank_qlike"] == 2
    assert good["calibration_ratio"] == pytest.approx(frame.loc[frame["model"] == "good", "realized_squared_return"].mean() / 1e-4)
    assert bad["relative_bias"] == pytest.approx(9e-4 / frame.loc[frame["model"] == "bad", "realized_squared_return"].mean() - 1)
    assert bad["mse"] > good["mse"] and bad["mae"] > good["mae"]
    assert good["stability"] == 0.0
    assert stability(pd.Series([1e-4, 2e-4, 1e-4])) == pytest.approx(np.log(2))
    # rows without a usable forecast are excluded, never filled
    frame.loc[frame.index[:10], ["forecast_valid", "forecast_variance"]] = [False, np.nan]
    frame = attach_losses(frame)
    table = summarize_metrics(frame, periods=("development",), samples=("all",)).set_index("model")
    assert table.loc["good", "n_missing_forecast"] == 10 and table.loc["good", "n_evaluated"] == 390
    assert table.loc["bad", "n_missing_forecast"] == 0


def test_diebold_mariano_bootstrap_and_holm():
    rng = np.random.default_rng(5)
    base = rng.standard_normal(600)
    same = base + rng.standard_normal(600) * 0.1
    dm = diebold_mariano(same, base)
    assert dm["n"] == 600 and abs(dm["t_stat"]) < 3 and 0 <= dm["p_value"] <= 1
    worse = diebold_mariano(base + 0.5, base)
    assert worse["mean_diff"] == pytest.approx(0.5) and worse["p_value"] < 1e-6 and worse["t_stat"] > 0
    boot = bootstrap_mean_difference(base + 0.5, base, draws=200, seed=1)
    assert boot["boot_p_value"] < 0.05 and boot["ci_low"] <= 0.5 <= boot["ci_high"]
    assert bootstrap_mean_difference(base + 0.5, base, draws=200, seed=1) == boot  # seeded, reproducible
    np.testing.assert_allclose(holm_adjust([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
    assert np.isnan(holm_adjust([np.nan])).all()
    frame = attach_losses(make_frame())
    tests = compare_to_benchmark(frame, "good", draws=100)
    assert list(tests["model"]) == ["bad"] and tests.iloc[0]["mean_loss_diff"] > 0
    assert not tests.iloc[0]["better_than_benchmark"]


def test_ex_ante_regimes_use_only_past_information():
    rng = np.random.default_rng(9)
    r = pd.Series(rng.standard_normal(600) * 0.01, index=pd.bdate_range("2019-01-01", periods=600))
    labels = ex_ante_volatility_regimes(r, window=60, min_history=252)
    assert (labels.iloc[:251] == "unknown").all()
    assert set(labels.iloc[251:]) <= {"low", "medium", "high"}
    shocked = r.copy()
    shocked.iloc[400:] *= 10
    altered = ex_ante_volatility_regimes(shocked, window=60, min_history=252)
    pd.testing.assert_series_equal(labels.iloc[:400], altered.iloc[:400])
    assert (altered.iloc[460:] == "high").all()


def test_retrospective_labels_mark_shocks_and_recovery():
    r = pd.Series(np.full(300, 0.005), index=pd.bdate_range("2019-01-01", periods=300))
    r.iloc[::2] *= -1
    r.iloc[200] = -0.10
    labels = retrospective_labels(r, [{"name": "evt", "start": r.index[10], "end": r.index[12]}], shock_multiple=4.0,
                                  trailing_window=60, recovery_sessions=20)
    assert labels["shock"].iloc[200] and labels["shock"].sum() == 1
    assert labels["post_shock_recovery"].iloc[201:221].all() and not labels["post_shock_recovery"].iloc[221]
    assert list(labels["event"].iloc[10:13]) == ["evt"] * 3 and labels["event"].iloc[13] == ""


def test_ml_features_are_observable_at_origin():
    rng = np.random.default_rng(2)
    r = pd.Series(rng.standard_normal(300) * 0.01, index=pd.bdate_range("2020-01-01", periods=300))
    features = build_lagged_features(r)
    assert list(features.columns) == FEATURE_NAMES + ["target_sq_return_next"]
    np.testing.assert_allclose(features["target_sq_return_next"].values[:-1], (r.values[1:]) ** 2)
    assert np.isnan(features["target_sq_return_next"].iloc[-1])
    shocked = r.copy()
    shocked.iloc[200:] += 0.05
    altered = build_lagged_features(shocked)
    pd.testing.assert_frame_equal(features.iloc[:199].drop(columns="target_sq_return_next"),
                                  altered.iloc[:199].drop(columns="target_sq_return_next"))
    assert features["var_20"].iloc[100] == pytest.approx(np.var(r.values[81:101], ddof=1))
    assert features["sq_return_lag1"].iloc[100] == pytest.approx(r.values[100] ** 2)


def test_common_date_metrics_preserve_failed_fit_attempts():
    frame = attach_losses(make_frame(n=40))
    origin = frame.origin_date.iloc[0]
    frame.loc[frame.origin_date.eq(origin), 'common'] = False
    frame['runtime_seconds'] = .5
    fits = pd.DataFrame([
        {'asset': 'SYN', 'model': 'good', 'origin_date': origin, 'status': 'failed',
         'converged': False, 'boundary_flags': ''},
        {'asset': 'SYN', 'model': 'good', 'origin_date': frame.origin_date.iloc[1], 'status': 'ok',
         'converged': True, 'boundary_flags': ''}])
    table = summarize_metrics(frame, fits, periods=('development',), samples=('common',)).set_index('model')
    assert table.loc['good', 'n_evaluated'] == 39
    assert table.loc['good', 'fit_attempts'] == 2
    assert table.loc['good', 'fit_failure_rate'] == .5
    assert table.loc['good', 'runtime_seconds'] == 20.
