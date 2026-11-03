"""Markdown model-comparison report built from the evaluation tables."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

PERIOD_ORDER = ["all", "development", "validation", "holdout"]


def _fmt(value, digits=4, scale=1.0, percent=False):
    if value is None or (isinstance(value, float) and not math.isfinite(value)) or (isinstance(value, str) and not value):
        return "n/a"
    if isinstance(value, (bool, np.bool_)):
        return "yes" if value else "no"
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}"
    if isinstance(value, (float, np.floating)):
        number = float(value) * scale
        return f"{number * 100:.1f}%" if percent else f"{number:.{digits}f}"
    return str(value)


def markdown_table(frame: pd.DataFrame, columns: list[tuple[str, str, dict]]) -> str:
    """columns: (source column, header, format kwargs)."""
    header = "| " + " | ".join(h for _, h, _ in columns) + " |"
    rule = "|" + "|".join("---" for _ in columns) + "|"
    lines = [header, rule]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(_fmt(row.get(col), **kw) for col, _, kw in columns) + " |")
    return "\n".join(lines)


METRIC_TABLE = [("model", "Model", {}), ("n_evaluated", "Obs", {}), ("qlike", "QLIKE", {"digits": 4}),
                ("mse", "MSE (x1e8)", {"digits": 3, "scale": 1e8}), ("mae", "MAE (x1e4)", {"digits": 3, "scale": 1e4}),
                ("calibration_ratio", "Calibration", {"digits": 3}), ("relative_bias", "Rel. bias", {"percent": True}),
                ("stability", "Stability", {"digits": 3}), ("runtime_seconds", "Runtime (s)", {"digits": 1}),
                ("fit_failure_rate", "Fit fail", {"percent": True}), ("nonconvergence_rate", "Non-conv.", {"percent": True}),
                ("n_missing_forecast", "Missing", {}), ("rank_qlike", "Rank", {"digits": 0})]
TEST_TABLE = [("model", "Model", {}), ("n", "Obs", {}), ("mean_loss_diff", "Mean QLIKE diff", {"digits": 4}),
              ("dm_t_stat", "DM t", {"digits": 2}), ("dm_p_value", "DM p", {"digits": 3}),
              ("boot_p_value", "Bootstrap p", {"digits": 3}), ("dm_p_holm", "DM p (Holm)", {"digits": 3}),
              ("boot_p_holm", "Bootstrap p (Holm)", {"digits": 3}), ("better_than_benchmark", "Better", {}),
              ("significant_holm_5pct", "Significant (5%, Holm)", {})]
STABILITY_TABLE = [("model", "Model", {}), ("fits", "Fits", {}), ("failed_fits", "Failed", {}),
                   ("nonconverged_fits", "Non-converged", {}), ("boundary_fits", "Boundary flags", {}),
                   ("persistence_mean", "Persistence mean", {"digits": 4}), ("persistence_std", "Persistence sd", {"digits": 4}),
                   ("persistence_min", "Persistence min", {"digits": 4}), ("persistence_max", "Persistence max", {"digits": 4}),
                   ("persistence_max_abs_change", "Max refit jump", {"digits": 4})]


def model_comparison_markdown(manifest: dict, metrics: pd.DataFrame, tests: pd.DataFrame, regime_metrics: pd.DataFrame,
                              stability: pd.DataFrame, summaries: list[dict]) -> str:
    lines = [f"# Model comparison — experiment `{manifest['experiment']}`", "",
             f"Run `{manifest['run_id']}` created {manifest['created_at_utc']} from configuration "
             f"`{manifest['config_path']}` (sha256 `{manifest['config_sha256'][:12]}…`).", "",
             "Forecast quantity: next-session conditional variance of the daily log return (decimal units); "
             "annualized volatility = sqrt(variance x 252). Evaluation target: realized squared daily log return, "
             "a noisy, unbiased proxy of the latent conditional variance, so loss levels are compared on identical "
             "dates and differences are tested rather than read off point estimates.", "",
             f"Periods evaluated: {', '.join(manifest['periods_evaluated'])}. "
             + ("The final holdout is **sealed**: its observations are excluded before modeling and diagnostics."
                if manifest["holdout_sealed"] else "The final holdout is **unsealed** in this run."), "",
             "Splits (by target session): " + "; ".join(f"{k} {v[0]}..{v[1]}" for k, v in manifest["splits"].items()
                                                       if k != "holdout_sealed") + ".", "",
             "## Data", ""]
    data_rows = pd.DataFrame([v for v in manifest["data"].values()])
    lines.append(markdown_table(data_rows, [("asset", "Asset", {}), ("currency", "Currency", {}), ("audit_id", "Audit", {}),
                                            ("rows", "Rows", {}), ("usable_returns", "Usable returns", {}),
                                            ("first_date", "First", {}), ("last_date", "Last", {}),
                                            ("contiguous", "Contiguous", {})]))
    lines += ["", "## Models", ""]
    model_rows = pd.DataFrame([{"name": m["name"], "type": m["type"], "family": m["family"], "version": m["version"],
                                "refit_every": m["refit_every"], "min_observations": m["min_observations"],
                                "config": ", ".join(f"{k}={v}" for k, v in m["config"].items()
                                                    if k not in ("min_observations", "refit_every", "mean"))}
                               for m in manifest["models"]])
    lines.append(markdown_table(model_rows, [("name", "Model", {}), ("type", "Type", {}), ("family", "Family", {}),
                                             ("version", "Version", {}), ("refit_every", "Refit every", {}),
                                             ("min_observations", "Min obs", {}), ("config", "Configuration", {})]))
    lines += ["", f"Benchmark for statistical tests: `{manifest['effective_experiment']['benchmark']}`.", ""]

    for asset in sorted(metrics["asset"].unique()) if not metrics.empty else []:
        lines += [f"## {asset}", ""]
        for period in [p for p in PERIOD_ORDER if p in set(metrics["period"])]:
            lines += [f"### {asset} — {period} period, common dates", ""]
            rows = metrics[(metrics["asset"] == asset) & (metrics["period"] == period) & (metrics["sample"] == "common")]
            lines.append(markdown_table(rows.sort_values("rank_qlike"), METRIC_TABLE))
            rows_all = metrics[(metrics["asset"] == asset) & (metrics["period"] == period) & (metrics["sample"] == "all")]
            lines += ["", f"All available forecasts ({period}): " + "; ".join(
                f"{r.model} n={int(r.n_evaluated)} QLIKE={_fmt(r.qlike)}" for r in rows_all.sort_values("qlike").itertuples()), ""]
            if not tests.empty:
                t = tests[(tests["asset"] == asset) & (tests["period"] == period)]
                if not t.empty:
                    lines += [f"Statistical comparison vs benchmark ({period}, QLIKE, HAC Diebold-Mariano and stationary "
                              "block bootstrap; Holm-adjusted within asset/period):", "",
                              markdown_table(t.sort_values("mean_loss_diff"), TEST_TABLE), ""]
        if not regime_metrics.empty:
            r = regime_metrics[regime_metrics["asset"] == asset]
            if not r.empty:
                lines += [f"### {asset} — regimes (common dates, evaluated periods)", "",
                          "Ex-ante regimes use the tercile of trailing 60-session variance relative to its own history "
                          "at the origin (known at forecast time). Retrospective labels (shock sessions, post-shock "
                          "recovery, named event windows) use information after the origin and are descriptive only.", ""]
                pivot = r.pivot_table(index="model", columns=["regime_kind", "regime_label"], values="qlike")
                pivot.columns = [f"{k}:{lbl}" for k, lbl in pivot.columns]
                counts = r.pivot_table(index="model", columns=["regime_kind", "regime_label"], values="n_evaluated").iloc[0]
                lines.append("Observations per regime: " + "; ".join(f"{k}:{lbl}={int(v)}" for (k, lbl), v in counts.items()) + ".")
                lines.append("")
                table = pivot.reset_index()
                lines.append(markdown_table(table, [("model", "Model (QLIKE)", {})]
                                            + [(c, c, {"digits": 4}) for c in pivot.columns]))
                lines.append("")
                calib = r.pivot_table(index="model", columns=["regime_kind", "regime_label"], values="calibration_ratio")
                calib.columns = [f"{k}:{lbl}" for k, lbl in calib.columns]
                lines.append(markdown_table(calib.reset_index(), [("model", "Model (calibration ratio)", {})]
                                            + [(c, c, {"digits": 3}) for c in calib.columns]))
                lines.append("")
        if not stability.empty and "persistence_mean" in stability.columns:
            s = stability[(stability["asset"] == asset) & stability["persistence_mean"].notna()]
            if not s.empty:
                lines += [f"### {asset} — estimation stability (GARCH family)", "", markdown_table(s, STABILITY_TABLE), ""]

    lines += ["## Run summaries", ""]
    summary_rows = pd.DataFrame(summaries)
    if not summary_rows.empty:
        summary_rows["invalid_flags"] = summary_rows["invalid_forecast_flags"].apply(
            lambda d: ", ".join(f"{k}={v}" for k, v in d.items()) if isinstance(d, dict) and d else "")
        lines.append(markdown_table(summary_rows, [("asset", "Asset", {}), ("model", "Model", {}),
                                                   ("n_origins", "Origins", {}), ("n_valid_forecasts", "Valid", {}),
                                                   ("n_missing_forecasts", "Missing", {}), ("invalid_flags", "Invalid flags", {}),
                                                   ("fit_attempts", "Fits", {}), ("fit_failures", "Failed fits", {}),
                                                   ("fit_warnings", "Flagged fits", {}), ("fit_nonconverged", "Non-converged", {}),
                                                   ("runtime_seconds", "Runtime (s)", {"digits": 1})]))
    lines += ["", "Metric definitions: QLIKE = log(h) + r²/h (lower is better, computed only for strictly positive finite h); "
              "MSE/MAE on variance units; calibration = mean r² / mean h; relative bias = mean h / mean r² - 1; "
              "stability = mean |Δ log h| between consecutive origins; runtime = total fit+update+forecast seconds. "
              "Rank is by QLIKE within asset/period/sample. Small differences are not treated as meaningful without the "
              "statistical tests above.", ""]
    return "\n".join(lines)
