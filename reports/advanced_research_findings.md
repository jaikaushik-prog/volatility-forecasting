# Stage 3 research findings

Evidence: run `20261103T115607990025Z_4774c4a9`, current audited canonical data, modeling cutoff
2024-12-31. The CLI regenerated all ten incumbents and the two challengers. This interpretation is
pinned to that run; detailed tables are in `advanced_model_comparison.md` and its immutable run directory.

## Validation selection evidence: 2022-2024

QLIKE is lower-is-better and compared only within each asset on identical target sessions.

| Asset | Currency | Matched sessions | Best incumbent (QLIKE) | XGBoost QLIKE | XGBoost rank / 12 | Markov QLIKE | Markov rank / 12 |
|---|---|---:|---|---:|---:|---:|---:|
| NIFTY 50 TRI | INR | 743 | EWMA (-8.558458) | -8.572250 | 1 | -8.430553 | 11 |
| SPY | USD | 753 | EGARCH-t (-8.225559) | -8.228747 | 1 | -8.136284 | 10 |
| VT | USD | 753 | EGARCH-t (-8.308270) | -8.322645 | 1 | -8.239002 | 10 |

XGBoost has a consistent point-estimate improvement across these three markets. Its advantage over
the best incumbent is only 0.013792, 0.003187 and 0.014376 QLIKE respectively. All three corresponding
Holm-adjusted all-pair DM p-values equal 1.0. These ranks do **not** establish superiority.
No XGBoost improvement versus the prespecified GARCH-normal reference survives both corrected tests:

| Asset | XGBoost minus GARCH QLIKE | Pointwise block-bootstrap 95% interval | DM p, Holm | Bootstrap p, Holm |
|---|---:|---|---:|---:|
| NIFTY 50 TRI | -0.025123 | [-0.071948, 0.014435] | 0.9970 | 1.0000 |
| SPY | -0.056440 | [-0.099773, -0.002303] | 0.0760 | 0.1920 |
| VT | -0.050476 | [-0.089268, -0.010039] | 0.1843 | 0.1600 |

Bootstrap intervals are pointwise, not multiplicity-adjusted. The benchmark family contains eleven
comparisons within each asset/period; all-pair DM uses a separate family. There are 1,000 bootstrap
draws, so Monte Carlo uncertainty and the limited validation sample also matter. Development results
include tuning and should not be pooled with validation to strengthen a selection claim.

Markov switching does not beat GARCH-normal in validation for any asset: QLIKE differences are
+0.116574, +0.036022 and +0.033168. NIFTY's adjusted DM test indicates worse performance, but its
adjusted bootstrap p-value is 0.070, so the two methods do not jointly reject at 5%. Daily returns
provide no observed ground truth with which to assert accurate latent-regime classification.

## Calibration, shock response and recovery

XGBoost validation calibration ratios (mean squared return / mean forecast variance) are 0.872,
0.929 and 0.985 for NIFTY, SPY and VT. Markov ratios are 0.698, 0.703 and 0.720, indicating substantial
aggregate overforecasting in this period. EWMA is closer to aggregate calibration one for all assets;
calibration alone does not determine QLIKE rank.

The following development-plus-validation diagnostics are retrospective and exploratory. They are
not hyperparameter-selection evidence and do not establish advance prediction of shocks.

| Asset | Matched shock events | GJR-normal median variance response | Markov response | XGBoost response |
|---|---:|---:|---:|---:|
| NIFTY 50 TRI | 12 | 2.477x | 1.457x | 1.163x |
| SPY | 20 | 3.767x | 1.321x | 1.849x |
| VT | 16 | 3.627x | 1.674x | 1.683x |

Response is next-session variance after observing the shock divided by the forecast made before
observing it. GJR-normal has the largest median response across all twelve models in these small
samples. Faster response is not necessarily more accurate or evidence of better transition detection.

In the post-shock recovery subsets, XGBoost calibration is 1.123 / 1.494 / 1.387 and Markov is
0.876 / 1.374 / 1.344. Thus XGBoost underforecasts aggregate squared returns in these subsets; Markov
does so for SPY/VT despite overforecasting the overall validation period. EWMA ratios are
0.661 / 0.761 / 0.735, indicating aggregate overforecasting during these labelled recoveries.
The subsets contain subsequent shocks and overlapping 60-session windows. They cannot identify which
individual shock was short-lived, and variance is latent: no reliable overreaction ranking follows.

## Complexity and next research decision

All 371 scheduled fits for each challenger succeeded in this run, with zero missing forecasts and
zero recorded clipping for XGBoost. This observed success does not guarantee future convergence;
synthetic tests separately exercise failed fits and invalid predictions.

Measured model-task runtimes, including refits and filtering/prediction, were:

| Asset | GARCH-normal seconds | Markov seconds | XGBoost seconds |
|---|---:|---:|---:|
| NIFTY 50 TRI | 6.5 | 122.7 | 81.5 |
| SPY | 4.3 | 125.1 | 129.6 |
| VT | 5.8 | 62.0 | 56.1 |

Parallel scheduling and machine load affect these timings. The overall experiment took about
353 seconds, including comparisons and 30 figures. XGBoost costs roughly 10-30 times the GARCH
reference per asset here; its modest validation gains justify retaining it as a challenger, not
replacing the econometric benchmarks. Keep EWMA and the leading EGARCH/GJR models as comparators.
The present two-state Gaussian Markov specification does not justify promotion for forecast accuracy
alone. Its filtered state diagnostics remain useful descriptive research outputs.

Feature gain demonstrates which inputs the trained trees used, not causal economic mechanisms or
out-of-sample incremental information. Claims that nonlinear interactions explain the gains would
require predeclared ablation or permutation studies on permissible data. Do not retune this run to
its validation results. Freeze a candidate set and protocol before obtaining genuinely unseen final
confirmation. No position sizing or Stage 4 model is implemented by this work.

## Data and protocol limitations

- All three source audits retain extreme-return manual-review warnings. Numerical/source checks
  pass, raw files are unchanged and crisis observations were not removed or winsorized. These are
  qualified research comparisons, not unconditional data certification.
- NIFTY's 2014-04-25 return interval remains calendar-unverified. It is excluded and training restarts
  after it for every model. The resulting sample differs from the archived Stage 2 comparison.
- The old Stage 2 runner generated holdout predictions/losses and published holdout diagnostics.
  Stage 3 excludes holdout observations before all modeling/diagnostics, but cannot undo prior
  exposure. The original 2025-2026 period is not historically untouched.
- Prices are current-vintage adjusted data, not a point-in-time archive. Squared daily log returns
  are noisy variance proxies under the common zero-mean convention.
- Additional raw files now present include NIFTY/SENSEX minute-price CSVs and India VIX files.
  They were not ingested, audited or used in Stage 3. The legacy `data-check` command uses filename
  matches and incorrectly treats VIX filenames as evidence of an options surface; it also misses
  some `1min` names. Its availability flag is not verification. A VIX OHLC file is not an options
  surface, and these raw candidates do not yet establish usable realized-variance inputs. Validate
  schemas, licensing/provenance, calendars and asset mapping before any later data-gated extension.

## Verification and rerun

The full pytest suite passed **198 tests in 57.26 seconds**, with warnings treated as errors.
Tests cover past-only filtering, transitions/label ordering, positivity, causal features and labels,
refit schedules, failures, missing-history resets, reproducibility and future-shock invariance.
The real-artifact verifier passed for 97,112 forecast rows, 37,984 fit attempts, 47 output hashes and
34 unchanged raw-source files. It checks cutoff exclusion, target alignment, Markov forecast
identities, XGBoost label/CV dates, source/config/code hashes and identical comparison targets.
These artifact checks are distinct from synthetic unit tests and do not prove model superiority.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-advanced.xml
.\.venv\Scripts\python.exe -m volrisk.forecast_cli --config config/forecasting.toml run --experiment advanced --workers 4
.\.venv\Scripts\python.exe scripts/verify_advanced_outputs.py
```

The four requested reports and numerical outputs are regenerated by the CLI. This interpretation
is tied to the run ID above and must be reviewed if configurations, data or results change.
