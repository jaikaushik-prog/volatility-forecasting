"""Synthetic-data tests for the volatility model families (no market data is used)."""
import math

import numpy as np
import pandas as pd
import pytest

from volrisk.forecasting import available_model_types, build_model, build_models
from volrisk.forecasting.base import FIT_FAILED, FIT_OK, FIT_WARNING, FitError, annualized_volatility
from volrisk.forecasting.ewma import EWMAVariance, ewma_variance_path
from volrisk.forecasting.garch import ArchGARCH
from volrisk.forecasting.historical import ExpandingVariance, RollingVariance, sample_variance

GARCH_SPECS = {
    "garch_normal": {"vol": "GARCH", "o": 0, "dist": "normal"}, "garch_t": {"vol": "GARCH", "o": 0, "dist": "t"},
    "egarch_normal": {"vol": "EGARCH", "o": 1, "dist": "normal"}, "egarch_t": {"vol": "EGARCH", "o": 1, "dist": "t"},
    "gjr_normal": {"vol": "GARCH", "o": 1, "dist": "normal"}, "gjr_t": {"vol": "GARCH", "o": 1, "dist": "t"},
}


def simulate_gjr(n=1300, seed=7, omega=2e-6, alpha=0.05, gamma=0.08, beta=0.88):
    """Synthetic GJR-GARCH daily log returns in decimal units."""
    rng = np.random.default_rng(seed)
    e = rng.standard_t(6, size=n) / math.sqrt(6 / 4)
    r = np.empty(n)
    h = omega / (1 - alpha - gamma / 2 - beta)
    for t in range(n):
        if t:
            h = omega + alpha * r[t - 1] ** 2 + gamma * r[t - 1] ** 2 * (r[t - 1] < 0) + beta * h
        r[t] = math.sqrt(h) * e[t]
    return pd.Series(r, index=pd.bdate_range("2015-01-01", periods=n))


@pytest.fixture(scope="module")
def gjr_returns():
    return simulate_gjr()


def test_annualization_convention():
    assert annualized_volatility(1e-4) == pytest.approx(math.sqrt(252) * 0.01)
    np.testing.assert_allclose(annualized_volatility(np.array([4e-4, 1e-4])), [0.02 * math.sqrt(252), 0.01 * math.sqrt(252)])
    assert math.isnan(annualized_volatility(float("nan")))


def test_registry_reports_implementation_status():
    types = available_model_types()
    assert {t for t, info in types.items() if info["implementation_status"] == "implemented"} == {
        "expanding", "rolling", "ewma", "garch", "markov_switching", "xgboost", "har_rv", "rv_benchmark", "positive_har"}
    assert types["heston"]["implementation_status"] == "not_implemented"
    for pending in ("latent_sv", "realized_garch"):
        assert types[pending]["implementation_status"] == "pending_extension"


def test_build_models_refuses_pending_and_skips_disabled():
    specs = {"a": {"type": "rolling", "window": 20}, "b": {"type": "latent_sv"}, "c": {"type": "ewma", "enabled": False}}
    with pytest.raises(NotImplementedError):
        build_models(specs, ["a", "b"])
    models = build_models(specs, ["a", "c"])
    assert [m.name for m in models] == ["a"]
    for pending in ("latent_sv", "heston", "realized_garch"):
        model = build_model("p", {"type": pending})
        with pytest.raises(NotImplementedError):
            model.fit(np.zeros(600))
    with pytest.raises(KeyError):
        build_model("x", {"type": "does_not_exist"})


def test_expanding_and_rolling_match_numpy_ddof1():
    rng = np.random.default_rng(0)
    r = rng.standard_normal(400) * 0.01
    dates = pd.bdate_range("2020-01-01", periods=400)
    expanding = ExpandingVariance("exp", min_observations=252)
    report = expanding.fit(r, dates)
    assert report.status == FIT_OK and report.training_observations == 400
    assert expanding.forecast(1)[0] == pytest.approx(np.var(r, ddof=1))
    assert report.training_start == dates[0] and report.training_end == dates[-1]
    rolling = RollingVariance("roll", window=20)
    report = rolling.fit(r, dates)
    assert rolling.forecast(3).tolist() == pytest.approx([np.var(r[-20:], ddof=1)] * 3)
    assert report.training_observations == 20 and report.training_start == dates[-20]
    assert sample_variance(r, ddof=1, center=False) == pytest.approx(np.sum(r * r) / (len(r) - 1))
    with pytest.raises(FitError):
        RollingVariance("short", window=20, min_observations=252).fit(r[:100])
    with pytest.raises(FitError):
        expanding.fit(np.array([0.01, np.nan] * 200))


def test_ewma_recursion_and_configurable_lambda():
    rng = np.random.default_rng(1)
    r = rng.standard_normal(300) * 0.01
    path = ewma_variance_path(r, 0.94, 252)
    h = np.var(r[:252], ddof=1)
    assert path[251] == pytest.approx(h)
    for k in range(252, 300):
        h = 0.94 * h + 0.06 * r[k] ** 2
        assert path[k] == pytest.approx(h)
    assert np.isnan(path[:251]).all()
    fast, slow = EWMAVariance("f", decay=0.90), EWMAVariance("s", decay=0.99)
    fast.fit(r), slow.fit(r)
    assert fast.forecast(1)[0] != slow.forecast(1)[0]
    assert slow.config["decay"] == 0.99
    with pytest.raises(ValueError):
        EWMAVariance("bad", decay=1.0)


def test_ewma_incremental_update_equals_full_refit():
    rng = np.random.default_rng(2)
    r = rng.standard_normal(330) * 0.01
    full = EWMAVariance("full")
    full.fit(r)
    incremental = EWMAVariance("inc")
    incremental.fit(r[:300])
    for value in r[300:]:
        incremental.update(value)
    assert incremental.forecast(1)[0] == pytest.approx(full.forecast(1)[0], rel=1e-12)
    assert incremental.forecast(1)[0] > 0


@pytest.mark.parametrize("name,spec", GARCH_SPECS.items())
def test_garch_one_step_matches_arch_and_is_in_decimal_units(gjr_returns, name, spec):
    from arch import arch_model
    model = ArchGARCH(name, window=1000, min_observations=500, **spec)
    history = gjr_returns.values[:1000]
    report = model.fit(history, gjr_returns.index[:1000])
    assert report.status in (FIT_OK, FIT_WARNING) and report.converged
    assert report.training_observations == 1000
    variance = model.forecast(1)[0]
    assert variance > 0 and math.isfinite(variance)
    reference = arch_model(history * 100, mean="Zero", vol=spec["vol"], p=1, o=spec["o"], q=1, dist=spec["dist"],
                           rescale=False).fit(disp="off", show_warning=False, options={"maxiter": 500})
    expected = reference.forecast(horizon=1, reindex=False).variance.values[-1, 0] / 100 ** 2
    assert variance == pytest.approx(expected, rel=1e-8)
    # decimal units: the one-step variance is the same order as the sample variance of decimal returns
    assert 0.2 < variance / np.var(history) < 5
    assert "specification" in report.diagnostics and report.diagnostics["persistence"] < 1


@pytest.mark.parametrize("name,spec", GARCH_SPECS.items())
def test_garch_incremental_state_update_matches_arch_filter(gjr_returns, name, spec):
    from arch import arch_model
    model = ArchGARCH(name, window=1000, min_observations=500, **spec)
    values = gjr_returns.values
    model.fit(values[:1000])
    params = pd.Series(model.params)
    for k in range(1000, 1015):
        model.update(values[k])
    fixed = arch_model(values[:1015] * 100, mean="Zero", vol=spec["vol"], p=1, o=spec["o"], q=1, dist=spec["dist"],
                       rescale=False).fix(params)
    expected = fixed.forecast(horizon=1, reindex=False).variance.values[-1, 0] / 100 ** 2
    assert model.forecast(1)[0] == pytest.approx(expected, rel=1e-8)
    assert model.params == dict(params)  # parameters never change between refits


def test_garch_scaling_is_removed_from_forecasts(gjr_returns):
    history = gjr_returns.values[:1000]
    a = ArchGARCH("s100", scale=100.0)
    b = ArchGARCH("s50", scale=50.0)
    a.fit(history), b.fit(history)
    assert a.forecast(1)[0] == pytest.approx(b.forecast(1)[0], rel=2e-2)
    assert a.params["omega"] != pytest.approx(b.params["omega"])


def test_garch_multi_step_and_unsupported_orders(gjr_returns):
    history = gjr_returns.values[:1000]
    model = ArchGARCH("g", o=1)
    model.fit(history)
    path = model.forecast(5)
    assert path.shape == (5,) and (path > 0).all()
    persistence = model.persistence()
    omega = model.params["omega"] / 100 ** 2
    assert path[1] == pytest.approx(omega + persistence * path[0])
    egarch = ArchGARCH("e", vol="EGARCH", o=1)
    egarch.fit(history)
    with pytest.raises(NotImplementedError):
        egarch.forecast(2)
    with pytest.raises(ValueError):
        ArchGARCH("bad", p=2)
    with pytest.raises(ValueError):
        ArchGARCH("bad", dist="laplace")
    with pytest.raises(ValueError):
        ArchGARCH("bad", window=300, min_observations=500)


def test_garch_fit_failures_are_reported_not_substituted(gjr_returns, monkeypatch):
    model = ArchGARCH("g")
    with pytest.raises(FitError):
        model.fit(gjr_returns.values[:100])  # below min_observations
    assert not model.fitted

    def broken(self, y):
        raise np.linalg.LinAlgError("singular")
    monkeypatch.setattr(ArchGARCH, "_arch_model", broken)
    with pytest.raises(FitError, match="LinAlgError"):
        model.fit(gjr_returns.values[:1000])
    with pytest.raises(FitError):
        model.forecast(1)


def test_garch_boundary_flags_and_igarch_warning(gjr_returns):
    model = ArchGARCH("g", o=1)
    y = gjr_returns.values[:1000] * 100
    am = model._arch_model(y)
    base = {"omega": 0.01, "alpha[1]": 0.05, "gamma[1]": 0.05, "beta[1]": 0.9}
    assert model._boundary_flags(base, am) == []
    assert "alpha[1]_at_lower_bound" in model._boundary_flags(base | {"alpha[1]": 0.0}, am)
    assert "persistence_near_unit_root" in model._boundary_flags(base | {"beta[1]": 0.9245}, am)  # 0.05+0.025+0.9245
    assert "persistence_at_unit_root_igarch" in model._boundary_flags(base | {"beta[1]": 0.925}, am)  # exactly 1.0
    t_model = ArchGARCH("t", dist="t")
    am_t = t_model._arch_model(y)
    assert "nu_at_lower_bound" in t_model._boundary_flags({"omega": 0.01, "alpha[1]": 0.05, "beta[1]": 0.9, "nu": 2.05}, am_t)


def test_model_metadata_is_reproducible_configuration():
    model = build_model("gjr_t", {"type": "garch", "vol": "GARCH", "o": 1, "dist": "t", "window": 800})
    meta = model.metadata()
    assert meta["type"] == "garch" and meta["config"]["window"] == 800 and meta["refit_every"] == 21
    assert meta["forecast_quantity"].startswith("conditional_variance_next_session")
    clone = build_model("gjr_t", {"type": "garch"} | meta["config"])
    assert clone.config == model.config
    assert FIT_FAILED == "failed"
