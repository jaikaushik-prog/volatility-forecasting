# Experiment `econometric` (Stage 2)

The four Stage 1 benchmarks plus six GARCH-family models estimated with the `arch` package:

| Model | Specification | Innovations |
|---|---|---|
| garch_normal | GARCH(1,1), zero mean | Gaussian |
| garch_t | GARCH(1,1), zero mean | Student-t (nu estimated) |
| egarch_normal | EGARCH(1,1) with asymmetric term (p=1, o=1, q=1) | Gaussian |
| egarch_t | EGARCH(1,1) with asymmetric term | Student-t |
| gjr_normal | GJR-GARCH(1,1) (p=1, o=1, q=1) | Gaussian |
| gjr_t | GJR-GARCH(1,1) | Student-t |

Conventions (see `src/volrisk/forecasting/garch.py`):

- Zero conditional mean, consistent with the squared-return evaluation target.
- Returns are scaled by 100 for optimization; forecast variances are divided by 100² so every stored
  value is in decimal-return units. Annualized volatility = sqrt(variance × 252).
- Rolling estimation window of 1000 sessions (minimum 500), parameters re-estimated every 21 sessions.
  Between refits the conditional-variance state is advanced with each observed return through the
  model's own recursion (verified against `arch`'s filter in the tests).
- Diagnostics per fit: convergence flag, boundary estimates (parameters at `arch`'s bounds,
  persistence ≥ 0.999, IGARCH persistence = 1, Student-t nu at bounds), optimizer warnings, log-likelihood.
  Non-stationary EGARCH estimates and non-finite parameters are fit failures: the forecast is recorded
  as missing and the model is re-estimated at the next session. No other model is substituted.
- Forecasts outside 0.1%–500% annualized volatility are recorded as invalid.

```powershell
.\.venv\Scripts\python.exe -m volrisk.forecast_cli --config config/forecasting.toml run --experiment econometric --workers 4
```

The run publishes `model_comparison.md`, `model_metrics.csv`, `statistical_tests.csv`, `regime_metrics.csv`,
`parameter_stability.csv`, `pairwise_dm.csv` and `figures/` into `reports/` (configurable with
`publish_reports`, `--publish`, `--no-publish`). The benchmark for the statistical tests is `garch_normal`.
The final holdout is sealed unless `--include-holdout` is passed; do not unseal it while configurations
are still being chosen.

Output layout is the same as for the `baseline` experiment (see `../baseline/README.md`).
