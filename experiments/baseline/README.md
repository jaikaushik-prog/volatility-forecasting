# Experiment `baseline` (Stage 1)

Historical benchmarks only: expanding variance, rolling 20- and 60-session variance (ddof=1) and
RiskMetrics EWMA (lambda = 0.94, initialized with the sample variance of the first 252 returns).
All four forecast the next-session conditional variance of the daily log return and are re-estimated
every session from history through the origin.

```powershell
.\.venv\Scripts\python.exe -m volrisk.forecast_cli --config config/forecasting.toml run --experiment baseline --workers 4
```

Outputs are written to `runs/<run_id>/` (git-ignored) and `latest.json` points at the newest run:

```text
forecasts.parquet          one row per (asset, model, origin); target, realized value, losses, regimes, provenance
fits.parquet               one row per estimation attempt with status, parameters, diagnostics
model_metrics.csv          QLIKE / MSE / MAE / calibration / bias / stability / runtime / failure rates / rank
statistical_tests.csv      HAC Diebold-Mariano + stationary block bootstrap vs the benchmark (Holm-adjusted)
pairwise_dm.csv            all pairwise DM tests
regime_metrics.csv         metrics by ex-ante volatility regime and retrospective event labels
parameter_stability.csv    parameter dispersion across refits (empty for benchmarks)
model_comparison.md        the report
figures/<asset>_*.png      eight diagnostic figures per asset
manifest.json              configuration hash, model metadata, data provenance, versions, output hashes
```

The benchmark for the statistical tests is `rolling_60`. The final holdout (2025-01-01 .. 2026-10-30)
is sealed: forecasts are stored but not evaluated unless `--include-holdout` is passed. This experiment
does not publish to `reports/`; the Stage 2 `econometric` experiment does.
