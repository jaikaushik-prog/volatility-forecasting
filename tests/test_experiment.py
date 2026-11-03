"""End-to-end experiment runner and CLI tests on a synthetic repository in a temporary directory."""
import json

import numpy as np
import pandas as pd
import pytest

from volrisk.evaluation.experiment import load_forecasting_config, run_experiment
from volrisk.forecast_cli import main

CONFIG = """
[data]
latest_audit = "reports/latest_audit.json"
assets = ["AAA", "BBB"]
min_history = 252
sessions_per_year = 252

[splits]
development = ["2016-01-01", "2017-12-31"]
validation = ["2018-01-01", "2018-06-30"]
holdout = ["2018-07-01", "2019-12-31"]
holdout_sealed = true

[walk_forward]
retry_failed_fit = true

[evaluation]
regime_window = 60
shock_multiple = 4.0
recovery_sessions = 20
bootstrap_block = 10
bootstrap_draws = 30
seed = 1
alpha = 0.05
rolling_window = 60

[[evaluation.event_windows]]
name = "window_a"
start = "2017-03-01"
end = "2017-03-31"
kind = "shock"

[models.rolling_20]
type = "rolling"
window = 20
[models.ewma_094]
type = "ewma"
[models.garch_normal]
type = "garch"
min_observations = 300
window = 400
refit_every = 21
[models.pending]
type = "xgboost"
enabled = false
[models.ms]
type = "latent_sv"

[experiments.small]
models = ["rolling_20", "ewma_094", "garch_normal", "pending"]
benchmark = "rolling_20"
publish_reports = false
[experiments.advanced]
models = ["ms"]
benchmark = "ms"
"""


def synthetic_canonical(asset, n, seed):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2016-01-04", periods=n)
    log_r = rng.standard_normal(n) * 0.01
    log_r[0] = np.nan
    return pd.DataFrame({"date": dates, "asset": asset, "price": 100 * np.exp(np.nancumsum(log_r)),
                         "daily_return": np.expm1(log_r), "currency": "USD", "source": "synthetic",
                         "price_convention": "synthetic", "simple_return": np.expm1(log_r), "log_return": log_r,
                         "return_usable": ~np.isnan(log_r), "calendar_interval_verified": ~np.isnan(log_r),
                         "return_exclusion_reason": np.where(np.isnan(log_r), "first_observation", "")})


@pytest.fixture
def repo(tmp_path, audit_pointer):
    (tmp_path / "config").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "config" / "forecasting.toml").write_text(CONFIG, encoding="utf-8")
    canonical = {}
    for asset, n in (("AAA", 800), ("BBB", 760)):
        path = tmp_path / "data" / f"{asset}.parquet"
        synthetic_canonical(asset, n, seed=len(asset) + n).to_parquet(path, index=False)
        canonical[asset] = str(path)
    audit_pointer(tmp_path, canonical)
    return tmp_path


def test_run_experiment_end_to_end(repo):
    config = load_forecasting_config(repo / "config" / "forecasting.toml")
    assert config.root == repo
    manifest = run_experiment(config, "small", bootstrap_draws=20)
    run_dir = repo / "experiments" / "small" / "runs" / manifest["run_id"]
    for name in ("forecasts.parquet", "fits.parquet", "model_metrics.csv", "statistical_tests.csv", "regime_metrics.csv",
                 "parameter_stability.csv", "pairwise_dm.csv", "model_comparison.md", "manifest.json", "run_summaries.json"):
        assert (run_dir / name).exists(), name
    assert manifest["holdout_sealed"] and manifest["periods_evaluated"] == ["development", "validation"]
    assert manifest["effective_experiment"]["models"] == ["rolling_20", "ewma_094", "garch_normal"]  # disabled skipped
    assert set(manifest["data"]) == {"AAA", "BBB"} and manifest["versions"]["arch"]
    assert not manifest["published"] and not (repo / "reports" / "model_comparison.md").exists()
    figures = sorted(p.name for p in (run_dir / "figures").glob("*.png"))
    assert len(figures) == 16 and "AAA_cumulative_qlike.png" in figures
    forecasts = pd.read_parquet(run_dir / "forecasts.parquet")
    assert {'development', 'validation'} <= set(forecasts['period'])
    assert 'holdout' not in set(forecasts['period'])
    assert forecasts.origin_date.max() < pd.Timestamp('2018-07-01')
    assert {"ex_ante_regime", "shock", "event", "loss_qlike", "common"} <= set(forecasts.columns)
    metrics = pd.read_csv(run_dir / "model_metrics.csv")
    assert "holdout" not in set(metrics["period"])  # sealed
    assert set(metrics["period"]) == {"all", "development", "validation"}
    common = metrics[(metrics["sample"] == "common") & (metrics["period"] == "all")]
    assert common.groupby("asset")["n_evaluated"].nunique().eq(1).all()  # identical dates across models
    tests = pd.read_csv(run_dir / "statistical_tests.csv")
    assert set(tests["benchmark"]) == {"rolling_20"} and {"dm_p_holm", "boot_p_holm"} <= set(tests.columns)
    stored = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert stored["output_sha256"]["forecasts.parquet"]
    unsealed = run_experiment(config, "small", include_holdout=True, bootstrap_draws=20, make_figures=False, publish=True)
    assert unsealed["periods_evaluated"] == ["development", "validation", "holdout"]
    assert (repo / "reports" / "model_comparison.md").exists() and (repo / "reports" / "model_metrics.csv").exists()
    text = (repo / "reports" / "model_comparison.md").read_text(encoding="utf-8")
    assert "unsealed" in text and "## AAA" in text


def test_cli_rejects_pending_experiment_and_lists_models(repo, capsys):
    config_path = str(repo / "config" / "forecasting.toml")
    assert main(["--config", config_path, "list-models"]) == 0
    assert "pending_extension" in capsys.readouterr().out
    assert main(["--config", config_path, "run", "--experiment", "advanced"]) == 3
    assert "cannot run" in capsys.readouterr().err
    assert main(["--config", config_path, "run", "--experiment", "missing"]) == 2
    assert main(["--config", config_path, "run", "--experiment", "small", "--models", "rolling_20,ewma_094",
                 "--assets", "AAA", "--max-origins", "40", "--bootstrap-draws", "10", "--no-figures", "--no-publish"]) == 0
    out = capsys.readouterr().out
    assert "origins=   40" in out and "holdout sealed=True" in out
    assert main(["--config", config_path, "data-check"]) == 0
    assert "\"available\": false" in capsys.readouterr().out


def test_holdout_is_excluded_before_models_losses_diagnostics_and_summaries(repo, audit_pointer):
    config = load_forecasting_config(repo / 'config/forecasting.toml')
    first = run_experiment(config, 'small', models=['rolling_20', 'ewma_094'], bootstrap_draws=10, make_figures=False)
    canonical = {}
    for asset in ('AAA', 'BBB'):
        path = repo / 'data' / f'{asset}.parquet'
        frame = pd.read_parquet(path)
        mask = frame.date.ge('2018-07-01')
        frame.loc[mask, 'log_return'] = .5
        frame.loc[mask, 'simple_return'] = np.expm1(.5)
        frame.to_parquet(path, index=False)
        canonical[asset] = str(path)
    audit_pointer(repo, canonical)
    second = run_experiment(config, 'small', models=['rolling_20', 'ewma_094'], bootstrap_draws=10, make_figures=False)
    a = pd.read_parquet(first['run_dir'] + '/forecasts.parquet')
    b = pd.read_parquet(second['run_dir'] + '/forecasts.parquet')
    pd.testing.assert_frame_equal(a.drop(columns='runtime_seconds'), b.drop(columns='runtime_seconds'))
    fits = pd.read_parquet(first['run_dir'] + '/fits.parquet')
    assert fits.origin_date.max() < pd.Timestamp('2018-07-01')
    assert a.target_date.dropna().max() < pd.Timestamp('2018-07-01')
    assert 'holdout' not in set(a.period)
    assert all(pd.Timestamp(v['last_date']) < pd.Timestamp('2018-07-01') for v in first['data'].values())


def test_advanced_publication_and_chronological_tuning(repo):
    path = repo / 'config/forecasting.toml'
    text = path.read_text(encoding='utf-8').replace('models = ["ms"]', 'models = ["rolling_20", "markov", "boost"]')
    text = text.replace('benchmark = "ms"', 'benchmark = "rolling_20"')
    text += '''
[models.markov]
type = "markov_switching"
min_observations = 300
window = 400
refit_every = 200
[models.boost]
type = "xgboost"
min_observations = 300
window = 400
refit_every = 200
cv_folds = 2
cv_size = 20
cv_min_train = 80
min_train_samples = 150
search_space = [{max_depth = 2, n_estimators = 5}]
'''
    path.write_text(text, encoding='utf-8')
    config = load_forecasting_config(path)
    manifest = run_experiment(config, 'advanced', assets=['AAA'], bootstrap_draws=10, make_figures=False, publish=True)
    reports = repo / 'reports'
    for name in ('advanced_model_comparison.md', 'advanced_model_metrics.csv', 'regime_analysis.md',
                 'xgboost_features.md', 'latest_advanced.json'):
        assert (reports / name).exists()
    assert not (reports / 'latest_forecasting.json').exists()
    assert not (reports / 'model_comparison.md').exists()
    assert manifest['published']
    states = pd.read_csv(reports / 'regime_probabilities.csv')
    assert states.filtered_probability_high.between(0, 1).all()
    assert (states.variance_high > states.variance_low).all()
    tuning = pd.read_csv(reports / 'xgboost_tuning.csv')
    assert pd.to_datetime(tuning.tuning_date).max() <= config.splits.development[1]
    table = pd.read_csv(reports / 'advanced_model_metrics.csv')
    validation = table[(table['sample'] == 'common') & table.period.eq('validation')]
    assert len(validation) == 3 and validation.n_evaluated.nunique() == 1
