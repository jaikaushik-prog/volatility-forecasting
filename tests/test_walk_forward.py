"""Walk-forward engine tests on synthetic returns: alignment, warm-up, no look-ahead, failures, reproducibility."""
import json

import numpy as np
import pandas as pd
import pytest

from volrisk.evaluation.walk_forward import (PERIOD_UNASSIGNED, PeriodSplits, assign_periods, combine_results,
                                             mark_common_dates, run_walk_forward)
from volrisk.forecasting import build_model
from volrisk.forecasting.base import FIT_FAILED, FIT_OK, FitError, FitReport, VolatilityModel


@pytest.fixture
def returns():
    rng = np.random.default_rng(11)
    return pd.Series(rng.standard_normal(700) * 0.01, index=pd.bdate_range("2016-01-04", periods=700))


class RecordingModel(VolatilityModel):
    """Records the last date it was allowed to see; forecasts a constant."""
    family = "test"
    version = "0"
    supports_update = True

    def __init__(self, name, **config):
        super().__init__(name, min_observations=config.pop("min_observations", 10), **config)
        self.seen = []

    def fit(self, returns, dates=None):
        self.seen.append(("fit", pd.Timestamp(dates[-1]), len(returns)))
        self._fitted = True
        self._params = {"last": float(returns[-1])}
        return FitReport(status=FIT_OK, converged=True, params=self.params, training_start=dates[0],
                         training_end=dates[-1], training_observations=len(returns))

    def update(self, observed_return, date=None):
        self.seen.append(("update", pd.Timestamp(date), 1))

    def forecast(self, horizon=1):
        return np.full(horizon, 1e-4)


class FlakyModel(RecordingModel):
    def __init__(self, name, fail_on=(), **config):
        super().__init__(name, **config)
        self.fail_on = set(fail_on)
        self.calls = 0

    def fit(self, returns, dates=None):
        self.calls += 1
        if pd.Timestamp(dates[-1]).strftime("%Y-%m-%d") in self.fail_on:
            self._fitted = False
            raise FitError("synthetic estimation failure")
        return super().fit(returns, dates)


def test_forecast_target_alignment_and_warmup(returns):
    model = build_model("roll", {"type": "rolling", "window": 20, "min_observations": 252})
    result = run_walk_forward(returns, model, asset="SYN", min_history=252)
    fc = result.forecasts
    assert result.summary["first_origin_index"] == 251
    assert fc["origin_date"].iloc[0] == returns.index[251]
    observed = fc[fc["target_observed"]]
    positions = returns.index.get_indexer(observed["origin_date"])
    assert (observed["target_date"].values == returns.index[positions + 1].values).all()
    np.testing.assert_allclose(observed["realized_log_return"].values, returns.values[positions + 1])
    np.testing.assert_allclose(observed["realized_squared_return"].values, returns.values[positions + 1] ** 2)
    last = fc.iloc[-1]
    assert not last["target_observed"] and pd.isna(last["target_date"]) and np.isnan(last["realized_log_return"])
    # the forecast for the next session equals the variance of the 20 returns through the origin
    for _, row in fc.sample(5, random_state=0).iterrows():
        pos = returns.index.get_loc(row["origin_date"])
        assert row["forecast_variance"] == pytest.approx(np.var(returns.values[pos - 19: pos + 1], ddof=1))
        assert row["forecast_volatility_annualized"] == pytest.approx(np.sqrt(row["forecast_variance"] * 252))
    garch = build_model("g", {"type": "garch", "min_observations": 500, "window": 600})
    result = run_walk_forward(returns, garch, asset="SYN", min_history=252, max_origins=5)
    assert result.summary["first_origin_index"] == 499 and len(result.forecasts) == 5


def test_models_never_see_data_after_origin(returns):
    model = RecordingModel("rec", refit_every=5)
    result = run_walk_forward(returns, model, asset="SYN", min_history=30)
    for (kind, last_seen, _), (_, row) in zip(model.seen, result.forecasts.iterrows()):
        assert last_seen == row["origin_date"]
        assert last_seen < row["target_date"] or pd.isna(row["target_date"])
    kinds = [k for k, _, _ in model.seen]
    assert kinds[:6] == ["fit", "update", "update", "update", "update", "fit"]
    assert (result.forecasts["sessions_since_fit"].values[:6] == [0, 1, 2, 3, 4, 0]).all()


@pytest.mark.parametrize("spec", [{"type": "expanding"}, {"type": "rolling", "window": 20}, {"type": "ewma"},
                                  {"type": "garch", "min_observations": 300, "window": 400},
                                  {"type": "garch", "vol": "EGARCH", "o": 1, "dist": "t", "min_observations": 300,
                                   "window": 400}])
def test_future_shock_never_alters_saved_forecasts(returns, spec):
    cut = returns.index[450]
    baseline = run_walk_forward(returns, build_model("m", spec), asset="SYN").forecasts
    shocked = returns.copy()
    shocked.iloc[451:] = shocked.iloc[451:] * 5 + 0.08  # violent regime change after the cut
    altered = run_walk_forward(shocked, build_model("m", spec), asset="SYN").forecasts
    before = baseline[baseline["origin_date"] <= cut].reset_index(drop=True)
    after = altered[altered["origin_date"] <= cut].reset_index(drop=True)
    pd.testing.assert_frame_equal(before.drop(columns=["runtime_seconds", "realized_log_return", "realized_squared_return"]),
                                  after.drop(columns=["runtime_seconds", "realized_log_return", "realized_squared_return"]))
    # the realized value at the cut's target differs, the forecast does not
    assert before["forecast_variance"].iloc[-1] == after["forecast_variance"].iloc[-1]
    assert before["realized_log_return"].iloc[-1] != after["realized_log_return"].iloc[-1]
    later = altered[altered["origin_date"] > cut]
    assert later["forecast_variance"].mean() > before["forecast_variance"].mean()


def test_refit_schedule_keeps_parameters_fixed_between_refits(returns):
    model = build_model("g", {"type": "garch", "min_observations": 300, "window": 400, "refit_every": 21})
    result = run_walk_forward(returns, model, asset="SYN")
    fc = result.forecasts
    fit_origins = result.fits["origin_date"]
    assert (np.diff(result.fits["origin_index"].values) == 21).all()
    assert fit_origins.iloc[0] == fc["origin_date"].iloc[0]
    for _, block in fc.groupby("last_fit_date"):
        assert block["params"].nunique() == 1
        assert list(block["sessions_since_fit"]) == list(range(len(block)))
    assert result.summary["fit_attempts"] == len(result.fits)
    assert (fc["forecast_variance"] > 0).all()


def test_failed_fit_records_missing_forecasts_and_retries(returns):
    dates = returns.index
    fail_on = {dates[300].strftime("%Y-%m-%d"), dates[301].strftime("%Y-%m-%d")}
    model = FlakyModel("flaky", fail_on=fail_on, refit_every=5)
    result = run_walk_forward(returns, model, asset="SYN", min_history=301, retry_failed_fit=True)
    fc = result.forecasts.set_index("origin_date")
    assert fc.loc[dates[300], "fit_status"] == FIT_FAILED and np.isnan(fc.loc[dates[300], "forecast_variance"])
    assert fc.loc[dates[301], "fit_status"] == FIT_FAILED and not fc.loc[dates[301], "forecast_valid"]
    assert fc.loc[dates[302], "fit_status"] == FIT_OK and fc.loc[dates[302], "forecast_valid"]
    assert fc.loc[dates[300], "forecast_flag"] == "no_usable_state"
    assert result.summary["fit_failures"] == 2 and result.summary["n_missing_forecasts"] == 2
    assert "synthetic estimation failure" in result.fits.iloc[0]["message"]
    no_retry = run_walk_forward(returns, FlakyModel("flaky", fail_on=fail_on, refit_every=5), asset="SYN",
                                min_history=301, retry_failed_fit=False)
    assert no_retry.summary["n_missing_forecasts"] == 5  # whole block missing until the next scheduled refit


def test_invalid_forecasts_are_flagged_not_filled(returns):
    class Explosive(RecordingModel):
        def forecast(self, horizon=1):
            return np.full(horizon, 10.0)  # 500% annualized bound exceeded

    result = run_walk_forward(returns, Explosive("x"), asset="SYN", min_history=20, max_origins=5)
    assert (~result.forecasts["forecast_valid"]).all()
    assert (result.forecasts["forecast_flag"] == "variance_above_bound").all()
    assert result.forecasts["forecast_variance"].isna().all()
    assert result.summary["invalid_forecast_flags"] == {"variance_above_bound": 5}


def test_reproducible_runs(returns):
    runs = [run_walk_forward(returns, build_model("g", {"type": "garch", "o": 1, "dist": "t", "min_observations": 300,
                                                       "window": 400}), asset="SYN").forecasts for _ in range(2)]
    pd.testing.assert_frame_equal(runs[0].drop(columns="runtime_seconds"), runs[1].drop(columns="runtime_seconds"))


def test_periods_and_common_dates(returns):
    fast = run_walk_forward(returns, build_model("fast", {"type": "rolling", "window": 20}), asset="SYN")
    slow = run_walk_forward(returns, build_model("slow", {"type": "garch", "min_observations": 400, "window": 400}),
                            asset="SYN")
    fc, fits, summaries = combine_results([fast, slow])
    splits = PeriodSplits.from_config({"development": ["2016-01-01", "2017-06-30"], "validation": ["2017-07-01", "2018-03-31"],
                                       "holdout": ["2018-04-01", "2018-12-31"]})
    fc = mark_common_dates(assign_periods(fc, splits))
    assert set(fc["period"]) <= {"development", "validation", "holdout", PERIOD_UNASSIGNED}
    assert fc.loc[fc["target_date"].isna(), "period"].eq(PERIOD_UNASSIGNED).all()
    common_dates = fc.loc[fc["common"], "target_date"].unique()
    assert len(common_dates) == slow.summary["n_valid_forecasts"] - 1  # slow model's last origin has no target
    assert fc.loc[fc["common"]].groupby("target_date")["model"].nunique().eq(2).all()
    assert fc.loc[(fc["model"] == "fast") & (fc["target_date"] < returns.index[400]), "common"].eq(False).all()
    with pytest.raises(ValueError):
        PeriodSplits.from_config({"development": ["2016-01-01", "2017-06-30"], "validation": ["2017-06-01", "2018-03-31"],
                                  "holdout": ["2018-04-01", "2018-12-31"]})


def test_series_validation():
    bad = pd.Series([0.01, np.nan, 0.02], index=pd.bdate_range("2020-01-01", periods=3))
    with pytest.raises(ValueError):
        run_walk_forward(bad, build_model("r", {"type": "rolling", "window": 2}), asset="SYN", min_history=2)
    unsorted = pd.Series([0.01, 0.02, 0.0], index=pd.DatetimeIndex(["2020-01-03", "2020-01-01", "2020-01-02"]))
    with pytest.raises(ValueError):
        run_walk_forward(unsorted, build_model("r", {"type": "rolling", "window": 2}), asset="SYN", min_history=2)
    params = json.loads(run_walk_forward(pd.Series(np.full(300, 0.01) * np.r_[np.ones(150), -np.ones(150)],
                                                   index=pd.bdate_range("2020-01-01", periods=300)),
                                         build_model("e", {"type": "expanding"}), asset="SYN").forecasts["params"].iloc[0])
    assert params["n"] == 252


def test_missing_session_resets_training_and_does_not_bridge_targets():
    dates = pd.bdate_range('2020-01-01', periods=40)
    series = pd.Series(np.tile([.01, -.01], 20), index=dates)
    series.iloc[20] = np.nan
    model = RecordingModel('rec', refit_every=5, min_observations=5)
    result = run_walk_forward(series, model, asset='SYN', min_history=5, missing_policy='reset')
    before = result.forecasts[result.forecasts.origin_date.eq(dates[19])].iloc[0]
    assert not before.target_observed and pd.isna(before.target_date)
    after = result.forecasts[result.forecasts.origin_date.gt(dates[20])]
    assert after.origin_date.iloc[0] == dates[25]
    assert result.summary['gap_dates'] == [dates[20].date().isoformat()]
    assert all(start > dates[20] for start in after.training_start)
    assert not result.forecasts.target_date.eq(dates[21]).any()


def test_all_missing_reset_has_no_artificial_forecasts():
    series = pd.Series(np.nan, index=pd.bdate_range('2020-01-01', periods=10))
    result = run_walk_forward(series, RecordingModel('r'), asset='SYN', missing_policy='reset')
    assert result.forecasts.empty and result.summary['n_valid_forecasts'] == 0
