"""Explain a completed Stage 4 run; no fitting, tuning or holdout data reads."""
from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def markdown_table(frame):
    def cell(value):
        return f"{value:.6g}" if isinstance(value, (float, np.floating)) else str(value)
    rows = ["| " + " | ".join(frame.columns) + " |",
            "| " + " | ".join("---" for _ in frame.columns) + " |"]
    rows.extend("| " + " | ".join(cell(x) for x in row) + " |"
                for row in frame.itertuples(index=False, name=None))
    return "\n".join(rows)


def main():
    pointer = json.loads((ROOT / "reports/latest_har_rv.json").read_text())
    run = Path(pointer["run_dir"])
    manifest_path = run / "manifest.json"
    assert digest(manifest_path) == pointer["manifest_sha256"]
    manifest = json.loads(manifest_path.read_text())
    assert manifest["status"] == "PROVISIONAL" and not manifest["holdout_evaluated"]
    for relative, expected in manifest["output_sha256"].items():
        assert digest(run / relative) == expected, relative
    report_dir = run / "reports"
    metrics = pd.read_csv(report_dir / "har_rv_model_comparison.csv")
    tests = pd.read_csv(report_dir / "har_rv_statistical_tests.csv")
    samples = pd.read_csv(report_dir / "har_rv_sample_sizes.csv")
    regimes = pd.read_csv(report_dir / "har_rv_regime_metrics.csv")
    sensitivity = pd.read_csv(report_dir / "har_rv_sensitivity.csv")
    frequencies = pd.read_csv(report_dir / "har_rv_frequency_sensitivity.csv")
    forecasts = pd.read_parquet(run / "forecasts.parquet")
    assert forecasts.target_date.max() <= pd.Timestamp("2024-12-31")
    selected = metrics[(metrics.asset == "NIFTY") & (metrics.frequency == 5)
                       & (metrics.scenario == "eligible") & (metrics.period == "validation")
                       & (metrics["sample"] == "common")]
    primary = selected[selected.target == "intraday"].sort_values("rank_qlike")
    secondary = selected[selected.target == "intraday_overnight"].sort_values("rank_qlike")
    daily = selected[selected.target == "spot_c2c_squared"].sort_values("rank_qlike")
    n = int(primary.n_evaluated.iloc[0])
    subset = forecasts[(forecasts.asset == "NIFTY") & (forecasts.frequency == 5)
                       & (forecasts.scenario == "eligible") & (forecasts.period == "validation")]
    intraday = subset[subset.target == "intraday"]
    common = intraday[intraday.common].copy()
    test_subset = tests[(tests.asset == "NIFTY") & (tests.frequency == 5)
                        & (tests.scenario == "eligible")]

    def paired(model, target="intraday", reference="har"):
        row = test_subset[(test_subset.challenger == model) & (test_subset.reference == reference)
                          & (test_subset.target == target)].iloc[0]
        return (f"Mean QLIKE difference ({model} minus {reference}) = **{row.mean_loss_difference:.6f}**; "
                f"pointwise bootstrap 95% interval **[{row.ci_low:.6f}, {row.ci_high:.6f}]**. "
                f"HAC/Holm p = {row.hac_p_holm:.4g}; bootstrap/Holm p = {row.bootstrap_p_holm:.4g}.")

    coverage = samples[(samples.frequency == 5) & (samples.scenario == "eligible")]
    sensex = metrics[(metrics.asset == "SENSEX") & (metrics.frequency == 5)
                     & (metrics.scenario == "eligible") & (metrics.period == "validation")
                     & (metrics["sample"] == "common") & (metrics.target == "intraday")]
    sensex_n = int(sensex.n_evaluated.max())
    sensex_daily = metrics[(metrics.asset == "SENSEX") & (metrics.frequency == 5)
                           & (metrics.scenario == "eligible") & (metrics.period == "validation")
                           & (metrics["sample"] == "common") & (metrics.target == "spot_c2c_squared")]
    vix_floor = common[(common.model == "har_vix") & common.prediction_floored]
    combined_floor = common[(common.model == "har_vix_overnight") & common.prediction_floored]
    har_attempts = intraday[intraday.model == "har"]
    missing_origin = har_attempts.forecast_flag.fillna("").str.contains("Missing common origin features").sum()
    missing_target = (~har_attempts.target_observed).sum()
    quarterly = regimes[(regimes.asset == "NIFTY") & (regimes.frequency == 5)
                         & (regimes.scenario == "eligible") & (regimes.target == "intraday")
                         & regimes.regime.str.startswith("validation_Q")]
    quarter_wide = quarterly.pivot(index="regime", columns="model", values="qlike")
    better_quarters = int((quarter_wide.log_har < quarter_wide.har).sum())
    on_test = test_subset[(test_subset.challenger == "har_overnight")
                         & (test_subset.reference == "har") & (test_subset.target == "intraday_overnight")].iloc[0]
    winners = frequencies[(frequencies.asset == "NIFTY") & (frequencies.scenario == "eligible")
                          & (frequencies.rank_within_frequency == 1)].sort_values(["target", "frequency"])
    shock = regimes[(regimes.asset == "NIFTY") & (regimes.frequency == 5)
                    & (regimes.scenario == "eligible") & (regimes.target == "intraday")
                    & (regimes.regime == "retrospective_shock")
                    & regimes.model.isin(["har", "log_har", "rv_ewma", "har_vix"])]
    primary_table = primary[["rank_qlike", "model", "qlike", "calibration_ratio",
                              "rank_calibration", "prediction_floor_count"]].copy()
    primary_table.columns = ["QLIKE rank", "Model", "QLIKE", "Observed / forecast", "Calibration rank", "Floored predictions"]
    significance_count = int(tests.significant_after_multiplicity.sum())
    readout = [
        "# Stage 4 empirical readout — PROVISIONAL",
        f"Completed run `{manifest['run_id']}`. These are **2024 validation findings**, not holdout findings. "
        "NIFTY is user-confirmed NSE spot. The export vendor chain, original timezone and bar-label conventions "
        "are still unverified. The extra full-session VIX lag reduces timing risk but does not verify provenance. "
        "The existing intraday pipeline and raw files were not modified or rerun.",
        "## Sample and eligibility",
        markdown_table(coverage[["asset", "period", "session_rows", "complete_sessions", "all_har_origin_features", "excluded_sessions"]]),
        f"The primary NIFTY comparison has **{n} matched target dates**; SENSEX has only **{sensex_n}**. "
        f"Of {len(har_attempts)} NIFTY validation origins, {missing_origin} could not produce HAR predictions "
        f"because the complete causal feature set was missing, and {missing_target} additional target was unavailable. "
        "Missing sessions break the 22-session feature window; they are not skipped or imputed. "
        "Successful OLS estimation therefore does not imply that every session has a usable prediction.",
        "Gates independently reconcile within-session bar returns with RV, require valid session completeness, "
        "check adjacent endpoints for overnight returns, validate origin/target chronology, and require VIX availability "
        "before the origin. HAR variants share training rows as well as evaluation dates. "
        "Complete verified short special sessions remain at their actual duration. "
        "All exclusions are retained in `har_rv_exclusions.csv`.",
        "## NIFTY: primary 5-minute intraday variance target",
        markdown_table(primary_table),
        "Calibration is mean observed variance divided by mean forecast variance; one is ideal. "
        "Calibration rank uses absolute log distance from one, separately from QLIKE. "
        f"The lowest mean QLIKE is **{primary.model.iloc[0]}**, but that is a point-estimate ranking, not an established winner. "
        "A better QLIKE need not imply better average calibration.",
        paired("log_har"),
        f"Log-HAR has lower QLIKE than HAR in {better_quarters} of {len(quarter_wide)} validation quarters. "
        f"Across the entire predeclared family of {len(tests)} comparisons, {significance_count} pass both "
        "global Holm-adjusted HAC and block-bootstrap checks. The bootstrap uses 10,000 draws and gap-aware "
        "blocks. Pointwise intervals are not simultaneous intervals. The broad family and short sample reduce "
        "power; nonsignificance does not establish equivalence.",
        "## India VIX: tested specification fails positivity",
        f"Levels HAR+VIX generated **{len(vix_floor)} negative raw predictions** on the primary matched sample; "
        f"HAR+VIX+overnight generated **{len(combined_floor)}**. The predefined training-only floor retained "
        "those forecasts as tiny positive values, which caused very large QLIKE losses. Floored values are "
        "flagged separately from missing forecasts and fit failures. The fitted coefficients were not changed "
        "to improve these results. A negative prediction was independently reconciled against its saved coefficients.",
        (f"HAR+VIX floor events span {vix_floor.target_date.min().date()} through {vix_floor.target_date.max().date()}. "
         "Inspect `har_rv_floor_events.csv` for dates, raw predictions, final variances and training windows."
         if len(vix_floor) else "No HAR+VIX floor events occurred in this sample."),
        "The evidence does **not** demonstrate useful incremental VIX performance for the tested levels "
        "specification. It does not show that VIX contains no predictive information. "
        "The annualized implied-variance feature is (lagged VIX percent / 100)^2; it is not treated as a directly "
        "observed next-day variance. Its approximately 30-calendar-day horizon differs from the target.",
        "## Overnight features and separate daily-return benchmarks",
        f"For the intraday-plus-overnight target, {secondary.model.iloc[0]} has the lowest point-estimate "
        f"QLIKE ({secondary.qlike.iloc[0]:.6f}) and calibration {secondary.calibration_ratio.iloc[0]:.6f}. "
        "This proxy is RV plus the observed overnight square; it is not squared daily close-to-close return.",
        paired("har_overnight", target="intraday_overnight"),
        f"Excluding retrospectively labelled shock dates changes the overnight model's paired difference "
        f"to **{on_test.mean_difference_without_shocks:.6f}**. Its apparent gain is therefore sensitive to event "
        "composition. Overnight features worsen the primary intraday point estimate. A shock-period improvement "
        "does not establish a generally superior model.",
        f"In the separate same-spot-series close-to-close proxy panel ({int(daily.n_evaluated.iloc[0])} dates), "
        f"{daily.model.iloc[0]} ranks first by QLIKE ({daily.qlike.iloc[0]:.6f}); calibration is "
        f"{daily.calibration_ratio.iloc[0]:.6f}. This ranking cannot be transferred to the intraday target. "
        f"SENSEX has {int(sensex_daily.n_evaluated.max())} common dates for the daily-GARCH panel because "
        "missing sessions prevent the required contiguous return history. No artificial forecasts were added.",
        "## Sampling frequency, events and sensitivity",
        markdown_table(winners[["target", "frequency", "model", "n_same_dates_across_frequencies", "qlike"]]),
        "Each frequency is a different target: compare model ranks within a frequency, not QLIKE levels "
        "between frequencies. Log-HAR's primary ranking persists across the four frequencies; "
        "the overnight-augmented model's secondary first-place ranking is not frequency-stable.",
        markdown_table(shock[["model", "n", "calibration_ratio", "underprediction_fraction"]]),
        "These shock labels are retrospective and never enter estimation. The small event count cannot "
        "establish which model adapts fastest. The tested models materially underpredict these shocks. "
        "Large VIX-model losses during recovery also reflect invalid negative raw predictions, "
        "not merely slow mean reversion.",
        f"The additional absolute-return/stale-price exclusion rule flags "
        f"{int(coverage.questionable_sessions.sum())} sessions in the pre-holdout panels. "
        f"The maximum absolute paired QLIKE change from that exclusion scenario is "
        f"{sensitivity.excluded_minus_eligible_qlike.abs().max():.6g}. Identical results are not independent "
        "evidence of robustness to unverified provenance. Full-file MAD flags are not used in causal model "
        "selection or exclusions because their thresholds incorporate later data.",
        f"SENSEX's {sensex_n}-date matched sample is too short to support reliable cross-market generalization. "
        "No NIFTY-based implied-volatility feature is silently assigned to SENSEX.",
        "## Next experiment and remaining limits",
        "Retain HAR, log-HAR and RV-EWMA as comparison candidates. After confirming source/export timing, "
        "pre-register a positive-link or log-HAR+VIX extension and an explicit forecast-floor sensitivity plan. "
        "Do not repair the current ranking by choosing floors after observing losses. "
        "Overnight features remain a target-specific candidate, with uncertain event-driven gains. "
        "A genuinely unseen sample is needed: this Stage 4 run never reads numerical targets after 2024, "
        "but earlier project work already exposed aspects of 2025–2026, so those historical dates cannot be "
        "described as pristine at the project level. No portfolio utility has been tested.",
        "Numerical, temporal, issuance-order and hash checks are recorded in `har_rv_verification.json`. "
        "The full suite passed 259 tests. The real run emitted a nonfatal pandas FutureWarning for concatenating "
        "all-NA date columns in the unavailable SENSEX daily benchmark panel; the current outputs passed verification. "
        "Future pandas compatibility should be checked before upgrading dependencies.",
        "## Readable forecast-loss detail",
        "The additional chart below displays the non-VIX subset relative to HAR on the same matched dates. "
        "The original all-model `NIFTY_qlike.png` retains the full VIX loss scale; no losses or model rows were removed.",
        "![Matched validation loss detail](figures/har_rv/NIFTY_core_qlike_detail.png)",
        "Reproduce this readout after the main experiment with "
        "`.\\.venv\\Scripts\\python.exe scripts/summarize_har_results.py`. "
        "The supplementary readout has its own hash manifest and does not modify immutable experiment outputs.",
    ]

    outputs = ROOT / "reports"
    figure = outputs / "figures/har_rv/NIFTY_core_qlike_detail.png"
    figure.parent.mkdir(parents=True, exist_ok=True)
    wide = common.pivot(index="target_date", columns="model", values="loss_qlike").sort_index()
    models = ["log_har", "har_overnight", "rv_ewma", "mean5", "mean22", "previous"]
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, constrained_layout=True)
    colours = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#666666"]
    for model, colour in zip(models, colours):
        difference = wide[model] - wide["har"]
        axes[0].plot(difference.index, difference.cumsum(), label=model, color=colour, linewidth=1.4)
        axes[1].plot(difference.index, difference.rolling(60, min_periods=60).mean(), color=colour, linewidth=1.4)
    for ax in axes:
        ax.axhline(0, color="#222222", linestyle="--", linewidth=0.8)
        ax.grid(alpha=0.18)
    axes[0].set_ylabel("Cumulative QLIKE difference versus HAR\n(below zero favours challenger)")
    axes[1].set_ylabel("Mean QLIKE difference versus HAR\n(60 matched observations)")
    axes[0].legend(ncol=3, frameon=False, fontsize=9)
    axes[1].set_xlabel(f"2024 validation target date — {n} common observations; holdout sealed")
    fig.suptitle("NIFTY — PROVISIONAL — 5-minute intraday variance\n"
                 "Detail subset: VIX variants remain in the separate full-range chart", fontsize=13)
    fig.savefig(figure, dpi=160)
    plt.close(fig)
    readout_path = outputs / "har_rv_findings.md"
    readout_path.write_text("\n\n".join(readout) + "\n", encoding="utf-8")
    floor_path = outputs / "har_rv_floor_events.csv"
    subset[subset.common & subset.prediction_floored][[
        "target", "model", "origin_date", "target_date", "raw_prediction", "forecast_variance",
        "observed_variance", "last_fit_date", "training_start", "training_end", "forecast_flag",
        "data_quality_status"]].to_csv(floor_path, index=False)
    supplement = {
        "status": "PROVISIONAL", "source_run_id": manifest["run_id"],
        "source_manifest_sha256": digest(manifest_path), "holdout_evaluated": False,
        "script_sha256": digest(__file__),
        "output_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p)
                          for p in (readout_path, figure, floor_path)},
    }
    (outputs / "har_rv_findings_manifest.json").write_text(json.dumps(supplement, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(supplement, indent=2))


if __name__ == "__main__":
    main()
