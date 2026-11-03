"""Experiment runner: configuration, walk-forward execution, evaluation, persistence and manifests."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sys
import time
import tomllib
from uuid import uuid4

import numpy as np
import pandas as pd

from volrisk.data.returns import ReturnSeries, load_canonical_returns
from volrisk.data.storage import sha256, write_json, write_text
from volrisk.evaluation import diagnostics, reporting
from volrisk.evaluation.metrics import (attach_losses, compare_to_benchmark, ex_ante_volatility_regimes,
                                        pairwise_dm_matrix, retrospective_labels, summarize_group, summarize_metrics)
from volrisk.evaluation.walk_forward import (PERIOD_NAMES, PeriodSplits, WalkForwardResult, assign_periods,
                                             combine_results, mark_common_dates, run_walk_forward)
from volrisk.forecasting.base import FIT_FAILED
from volrisk.forecasting.registry import build_model, build_models

CONFIG_SECTIONS = {"data", "splits", "walk_forward", "evaluation", "models", "experiments"}
PACKAGES = ("numpy", "pandas", "scipy", "arch", "statsmodels", "matplotlib", "pyarrow", "xgboost", "scikit-learn")
DATE_COLUMNS = ("origin_date", "target_date", "training_start", "training_end", "last_fit_date")


@dataclass(frozen=True)
class ForecastingConfig:
    path: Path
    root: Path
    raw: dict
    sha256: str

    @property
    def data(self) -> dict:
        return dict(self.raw["data"])

    @property
    def splits(self) -> PeriodSplits:
        return PeriodSplits.from_config(self.raw["splits"])

    @property
    def walk_forward(self) -> dict:
        return dict(self.raw.get("walk_forward", {}))

    @property
    def evaluation(self) -> dict:
        return dict(self.raw.get("evaluation", {}))

    @property
    def models(self) -> dict:
        return {k: dict(v) for k, v in self.raw["models"].items()}

    @property
    def experiments(self) -> dict:
        return {k: dict(v) for k, v in self.raw["experiments"].items()}

    def experiment(self, name: str) -> dict:
        try:
            return dict(self.raw["experiments"][name])
        except KeyError:
            raise KeyError(f"unknown experiment {name!r}; configured: {sorted(self.raw['experiments'])}") from None


def load_forecasting_config(path: Path | str) -> ForecastingConfig:
    path = Path(path).resolve()
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    extra = set(raw) - CONFIG_SECTIONS
    if extra:
        raise ValueError(f"unknown forecasting configuration sections: {sorted(extra)}")
    for section in ("data", "splits", "models", "experiments"):
        if section not in raw:
            raise ValueError(f"forecasting configuration lacks the [{section}] section")
    return ForecastingConfig(path=path, root=path.parent.parent, raw=raw, sha256=sha256(path))


def package_versions() -> dict:
    versions = {"python": sys.version.split()[0], "platform": platform.platform()}
    for name in PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid4().hex[:8]


# -- execution -----------------------------------------------------------------------------------------------
def _run_task(task: dict) -> WalkForwardResult:
    model = build_model(task["model_name"], task["spec"])
    series = pd.Series(np.asarray(task["values"], dtype=float), index=pd.DatetimeIndex(task["dates"]))
    return run_walk_forward(series, model, asset=task["asset"], **task["options"])


def run_models(series_by_asset: dict[str, ReturnSeries], model_specs: dict[str, dict], model_names: list[str], *,
               options: dict, workers: int = 1) -> list[WalkForwardResult]:
    tasks = [{"asset": asset, "model_name": name, "spec": model_specs[name], "values": s.log_returns.values,
              "dates": s.log_returns.index.values, "options": options}
             for asset, s in series_by_asset.items() for name in model_names]
    if workers <= 1:
        return [_run_task(task) for task in tasks]
    with ProcessPoolExecutor(max_workers=int(workers)) as pool:
        return list(pool.map(_run_task, tasks))


def _parameter_stability(fits: pd.DataFrame) -> pd.DataFrame:
    records = []
    for (asset, model), rows in fits.groupby(["asset", "model"], sort=True):
        usable = rows[rows["status"] != FIT_FAILED].sort_values("origin_date")
        if usable.empty:
            records.append({"asset": asset, "model": model, "fits": int(len(rows)), "usable_fits": 0})
            continue
        params = pd.DataFrame([json.loads(p) for p in usable["params"]])
        params = params.select_dtypes(include=[np.number])
        record = {"asset": asset, "model": model, "fits": int(len(rows)), "usable_fits": int(len(usable)),
                  "failed_fits": int((rows["status"] == FIT_FAILED).sum()),
                  "nonconverged_fits": int((rows["converged"] == False).sum()),  # noqa: E712
                  "boundary_fits": int((rows["boundary_flags"].fillna("").astype(str) != "").sum())}
        persistence = pd.to_numeric(usable["persistence"], errors="coerce")
        if persistence.notna().any():
            record.update({"persistence_mean": float(persistence.mean()), "persistence_std": float(persistence.std(ddof=0)),
                           "persistence_min": float(persistence.min()), "persistence_max": float(persistence.max()),
                           "persistence_max_abs_change": float(persistence.diff().abs().max())
                           if len(persistence) > 1 else np.nan})
        for column in params.columns:
            if column in ("n",):
                continue
            values = params[column].astype(float)
            record[f"{column}_mean"] = float(values.mean())
            record[f"{column}_std"] = float(values.std(ddof=0))
            record[f"{column}_min"] = float(values.min())
            record[f"{column}_max"] = float(values.max())
        records.append(record)
    return pd.DataFrame.from_records(records)


def _regime_metrics(frame: pd.DataFrame, fits: pd.DataFrame, sessions_per_year: int) -> pd.DataFrame:
    records = []
    common = frame[frame["common"].astype(bool)]
    for asset, by_asset in common.groupby("asset", sort=True):
        groups = []
        for label in ("low", "medium", "high"):
            groups.append(("ex_ante_volatility_regime", label, by_asset[by_asset["ex_ante_regime"] == label]))
        groups.append(("retrospective", "shock_session", by_asset[by_asset["shock"].astype(bool)]))
        groups.append(("retrospective", "post_shock_recovery", by_asset[by_asset["post_shock_recovery"].astype(bool)]))
        for event in sorted({e for cell in by_asset["event"].astype(str) if cell for e in cell.split("|")}):
            groups.append(("retrospective_event", event,
                           by_asset[by_asset["event"].astype(str).str.split("|").apply(lambda parts: event in parts)]))
        for kind, label, subset in groups:
            for model, rows in subset.groupby("model", sort=True):
                record = summarize_group(rows, None, asset=asset, model=model, period="evaluated", sample="common",
                                         sessions_per_year=sessions_per_year)
                record.update({"regime_kind": kind, "regime_label": label})
                records.append(record)
    table = pd.DataFrame.from_records(records)
    if table.empty:
        return table
    table["rank_qlike"] = table.groupby(["asset", "regime_kind", "regime_label"])["qlike"].rank(method="min")
    columns = ["asset", "regime_kind", "regime_label", "model", "n_evaluated", "qlike", "mse", "mae",
               "calibration_ratio", "bias", "relative_bias", "mean_forecast_vol_annualized", "realized_vol_annualized",
               "rank_qlike"]
    return table[columns]


def _finalize_frame(forecasts: pd.DataFrame) -> pd.DataFrame:
    out = forecasts.copy()
    for column in DATE_COLUMNS:
        out[column] = pd.to_datetime(out[column])
    out["converged"] = out["converged"].astype("boolean")
    return out


def run_experiment(config: ForecastingConfig, name: str, *, assets: list[str] | None = None,
                   models: list[str] | None = None, workers: int = 1, include_holdout: bool = False,
                   max_origins: int | None = None, bootstrap_draws: int | None = None,
                   output_root: Path | None = None, publish: bool | None = None, make_figures: bool = True) -> dict:
    started = time.perf_counter()
    experiment = config.experiment(name)
    model_names = list(models or experiment["models"])
    benchmark = experiment.get("benchmark", model_names[0])
    if benchmark not in model_names:
        raise ValueError(f"benchmark {benchmark!r} is not among the experiment models {model_names}")
    model_specs = config.models
    # Selection cutoff may be earlier than development end, never later.
    for model_name in model_names:
        spec = model_specs[model_name]
        if spec.get('type') == 'xgboost':
            spec.setdefault('tuning_end', str(config.splits.development[1].date()))
            cutoff = pd.Timestamp(spec.get('tuning_end', config.splits.development[1]))
            if cutoff > config.splits.development[1]:
                raise ValueError('XGBoost tuning_end must not exceed development end')
    built = build_models(model_specs, model_names, implemented_only=True)
    model_names = [m.name for m in built]
    data_cfg = config.data
    splits = config.splits
    sealed = splits.holdout_sealed and not include_holdout
    # Sealing is enforced before loading observations into modeling/diagnostics.
    # No sealed targets, labels, states, losses, failures or features are computed.
    cutoff = splits.validation[1] if sealed else splits.holdout[1]
    series = load_canonical_returns(config.root / data_cfg['latest_audit'], assets or data_cfg.get('assets'),
        end_date=cutoff, preserve_gaps=True, require_verified_intervals=data_cfg.get('require_verified_intervals', True))
    periods_evaluated = ["development", "validation"] + ([] if sealed else ["holdout"])
    sessions_per_year = int(data_cfg.get("sessions_per_year", 252))
    wf = config.walk_forward
    options = {"min_history": int(data_cfg.get("min_history", 252)),
               "retry_failed_fit": bool(wf.get("retry_failed_fit", True)),
               "sessions_per_year": sessions_per_year, "max_origins": max_origins,
               "min_annualized_vol": float(wf.get("min_annualized_vol", 1e-3)),
               "max_annualized_vol": float(wf.get("max_annualized_vol", 5.0)), 'missing_policy': 'reset'}
    results = run_models(series, model_specs, model_names, options=options, workers=workers)
    forecasts, fits, summaries = combine_results(results)
    forecasts = _finalize_frame(forecasts)
    forecasts = mark_common_dates(assign_periods(forecasts, splits))
    forecasts = attach_losses(forecasts)

    evaluation = config.evaluation
    regime_frames = []
    for asset, s in series.items():
        ex_ante = ex_ante_volatility_regimes(s.log_returns, int(evaluation.get("regime_window", 60)),
                                            int(data_cfg.get("min_history", 252)))
        retro = retrospective_labels(s.log_returns, evaluation.get("event_windows", []),
                                     float(evaluation.get("shock_multiple", 4.0)),
                                     int(evaluation.get("regime_window", 60)),
                                     int(evaluation.get("recovery_sessions", 60)))
        rows = forecasts[forecasts["asset"] == asset]

        def lookup(series, keys, default):
            mapped = series.reindex(pd.DatetimeIndex(keys)).to_numpy(dtype=object)
            return np.where(pd.isna(mapped), default, mapped)

        regime_frames.append(pd.DataFrame({
            "ex_ante_regime": lookup(ex_ante, rows["origin_date"], "unknown").astype(str),
            "shock": lookup(retro["shock"], rows["target_date"], False).astype(bool),
            "post_shock_recovery": lookup(retro["post_shock_recovery"], rows["target_date"], False).astype(bool),
            "event": lookup(retro["event"], rows["target_date"], "").astype(str),
        }, index=rows.index))
    regimes = pd.concat(regime_frames) if regime_frames else pd.DataFrame()
    forecasts = forecasts.join(regimes)

    evaluated = forecasts[forecasts["period"].isin(periods_evaluated)]
    metrics = summarize_metrics(evaluated, fits, periods=["all"] + periods_evaluated, sessions_per_year=sessions_per_year)
    draws = int(bootstrap_draws if bootstrap_draws is not None else evaluation.get("bootstrap_draws", 1000))
    test_kwargs = {"expected_block": float(evaluation.get("bootstrap_block", 20)), "draws": draws,
                   "seed": int(evaluation.get("seed", 20261103)), "alpha": float(evaluation.get("alpha", 0.05))}
    all_periods = evaluated.assign(period="all")
    tests = pd.concat([compare_to_benchmark(all_periods, benchmark, **test_kwargs),
                       compare_to_benchmark(evaluated, benchmark, **test_kwargs)], ignore_index=True)
    pairwise = pd.concat([pairwise_dm_matrix(all_periods), pairwise_dm_matrix(evaluated)], ignore_index=True)
    regime_metrics = _regime_metrics(evaluated, fits, sessions_per_year)
    stability = _parameter_stability(fits)

    run_id = new_run_id()
    root = Path(output_root) if output_root is not None else config.root / "experiments" / name
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    forecasts.to_parquet(run_dir / "forecasts.parquet", engine="pyarrow", index=False)
    fits_out = fits.copy()
    for column in ("origin_date", "training_start", "training_end"):
        fits_out[column] = pd.to_datetime(fits_out[column])
    fits_out["converged"] = fits_out["converged"].astype("boolean")
    fits_out.to_parquet(run_dir / "fits.parquet", engine="pyarrow", index=False)
    metrics.to_csv(run_dir / "model_metrics.csv", index=False)
    tests.to_csv(run_dir / "statistical_tests.csv", index=False)
    pairwise.to_csv(run_dir / "pairwise_dm.csv", index=False)
    regime_metrics.to_csv(run_dir / "regime_metrics.csv", index=False)
    stability.to_csv(run_dir / "parameter_stability.csv", index=False)
    write_json({"summaries": summaries}, run_dir / "run_summaries.json")

    figures = []
    if make_figures:
        for asset in series:
            figures.extend(diagnostics.make_figures(evaluated[evaluated["asset"] == asset], fits[fits["asset"] == asset],
                                                    asset=asset, directory=run_dir / "figures", benchmark=benchmark,
                                                    metrics=metrics, rolling_window=int(evaluation.get("rolling_window", 252)),
                                                    sessions_per_year=sessions_per_year))
    manifest = {
        "schema_version": 1, "experiment": name, "description": experiment.get("description", ""), "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "config_path": str(config.path),
        "config_sha256": config.sha256, "effective_experiment": {"models": model_names, "benchmark": benchmark,
                                                                   "assets": list(series), "workers": int(workers),
                                                                   "max_origins": max_origins,
                                                                   "bootstrap_draws": draws},
        "walk_forward_options": options, "splits": splits.as_dict(), "periods_evaluated": periods_evaluated,
        'effective_configuration': config.raw,
        "holdout_sealed": sealed, 'modeling_data_cutoff': str(cutoff.date()),
        'holdout_policy': 'excluded before model fitting, prediction and diagnostics' if sealed else 'explicitly unsealed',
        "evaluation": evaluation, "models": [m.metadata() for m in built],
        'implementation_sha256': {p.relative_to(Path(__file__).parents[1]).as_posix(): sha256(p)
                                  for p in sorted(Path(__file__).parents[1].rglob('*.py'))},
        "data": {asset: s.provenance() for asset, s in series.items()},
        "versions": package_versions(), "seed": int(evaluation.get("seed", 20261103)),
        "run_summaries": summaries, "runtime_seconds": time.perf_counter() - started,
        "figures": [str(p) for p in figures], "run_dir": str(run_dir),
    }
    markdown = reporting.model_comparison_markdown(manifest, metrics, tests, regime_metrics, stability, summaries)
    write_text(markdown, run_dir / "model_comparison.md")
    advanced = any(m.family in {'regime_switching', 'machine_learning'} for m in built)
    if advanced:
        from volrisk.evaluation.advanced_reporting import write_advanced_reports
        figures.extend(write_advanced_reports(run_dir, manifest, evaluated, fits, metrics, tests, regime_metrics,
                                              figures=make_figures))
        manifest['figures'] = [str(p) for p in figures]
    should_publish = experiment.get('publish_reports', False) if publish is None else publish
    manifest['published'] = bool(should_publish)
    manifest["output_sha256"] = {p.relative_to(run_dir).as_posix(): sha256(p) for p in sorted(run_dir.rglob('*')) if p.is_file()}
    write_json(manifest, run_dir / "manifest.json")
    write_json({"experiment": name, "run_id": run_id, "run_dir": str(run_dir), "manifest": str(run_dir / "manifest.json"),
                "complete": True}, root / "latest.json")
    if should_publish:
        publish_reports(run_dir, config.root / "reports", advanced=advanced)
    return manifest


def publish_reports(run_dir: Path, reports_dir: Path, *, advanced=False) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    if advanced:
        for name in ('advanced_model_comparison.md', 'advanced_model_metrics.csv', 'regime_analysis.md',
                     'xgboost_features.md', 'xgboost_feature_importance.csv', 'xgboost_tuning.csv',
                     'regime_probabilities.csv', 'shock_response.csv'):
            shutil.copyfile(run_dir/name, reports_dir/name)
        for name in ('statistical_tests.csv', 'regime_metrics.csv', 'parameter_stability.csv', 'pairwise_dm.csv'):
            shutil.copyfile(run_dir/name, reports_dir/('advanced_'+name))
        source = run_dir/'figures'
        target = reports_dir/'figures'/'advanced'
        target.mkdir(parents=True, exist_ok=True)
        if source.exists():
            for png in source.glob('*.png'):
                shutil.copyfile(png, target/png.name)
        write_json({'run_dir': str(run_dir), 'manifest': str(run_dir/'manifest.json'),
                    'manifest_sha256': sha256(run_dir/'manifest.json')}, reports_dir/'latest_advanced.json')
        return
    for name in ("model_comparison.md", "model_metrics.csv", "statistical_tests.csv", "regime_metrics.csv",
                 "parameter_stability.csv", "pairwise_dm.csv"):
        source = run_dir / name
        if source.exists():
            shutil.copyfile(source, reports_dir / name)
    figures = run_dir / "figures"
    if figures.exists():
        target = reports_dir / "figures"
        target.mkdir(parents=True, exist_ok=True)
        for png in figures.glob("*.png"):
            shutil.copyfile(png, target / png.name)
    write_json({"run_dir": str(run_dir), "manifest": str(run_dir / "manifest.json"),
                "manifest_sha256": sha256(run_dir / "manifest.json")}, reports_dir / "latest_forecasting.json")
