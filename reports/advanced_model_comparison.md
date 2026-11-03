# Advanced volatility model comparison — Stage 3

Run: `20261103T115607990025Z_4774c4a9`. Modeling cutoff: 2024-12-31.

## Research protocol and earlier-run limitations

This run excludes holdout observations before fitting, prediction, losses and diagnostics.
Development ends 2021-12-31; validation covers 2022-2024. XGBoost hyperparameter searches use
chronological folds of labels already known at the origin and stop at the configured development
cutoff. Refits during validation update model weights/parameters using past observations; they do
not select hyperparameters. No models pool observations across assets.

The previous Stage 2 runner only filtered the summary tables: it generated holdout forecasts and
losses and published holdout fit diagnostics. Its research narrative discussed those failures.
Consequently the old holdout cannot honestly be described as completely untouched. No historical
exposure is undone by this fix. A genuinely fresh final confirmation needs subsequently unseen
data or a new predeclared holdout. This run performs no holdout scoring or model selection on it.

Canonical file hashes and numerical/source audit results are checked. Calendar-unverified
intervals are excluded from this experiment without modifying canonical/source files. Training
restarts after an interior gap; no model or supervised pair bridges it. This changes the NIFTY
comparison sample relative to Stage 2, so all ten comparators are rerun alongside the challengers.
The archived datasets retain statistical extreme-return review warnings; genuine large market
moves are neither clipped nor deleted. Empirical comparisons remain qualified by those warnings
and current-vintage source limitations; this is not unconditional data certification.

Squared daily log returns are noisy variance proxies under the common zero-mean convention.
QLIKE ranks are within asset and period. Development results include hyperparameter selection
and are exploratory; validation is the main selection evidence. Bootstrap intervals are pointwise;
Holm corrections apply to benchmark-test p-values within asset/period, and separately to all
pairwise DM p-values within asset/period. Tests do not eliminate model-search uncertainty.


## Validation-period evidence

### NIFTY50_TRI

| model | n evaluated | qlike | mse (x1e+08) | mae (x1e+04) | calibration ratio | bias (x1e+04) | fit failure rate | runtime seconds | rank qlike |
|---|---|---|---|---|---|---|---|---|---|
| xgboost_v1 | 743 | -8.5722 | 4.0765 | 0.8881 | 0.8719 | 0.1152 | 0.0000 | 38.9963 | 1.0000 |
| ewma_094 | 743 | -8.5585 | 4.0310 | 0.8524 | 0.9895 | 0.0084 | 0.0000 | 2.0576 | 2.0000 |
| egarch_t | 743 | -8.5493 | 3.9774 | 0.8734 | 0.8739 | 0.1132 | 0.0000 | 2.1635 | 3.0000 |
| egarch_normal | 743 | -8.5491 | 3.9878 | 0.8733 | 0.8771 | 0.1100 | 0.0000 | 1.6763 | 4.0000 |
| garch_t | 743 | -8.5472 | 4.0270 | 0.8781 | 0.9180 | 0.0701 | 0.0000 | 2.4977 | 5.0000 |
| garch_normal | 743 | -8.5471 | 4.0533 | 0.8840 | 0.9033 | 0.0840 | 0.0000 | 1.8064 | 6.0000 |
| gjr_normal | 743 | -8.5471 | 4.0468 | 0.8808 | 0.8731 | 0.1140 | 0.0000 | 1.4462 | 7.0000 |
| gjr_t | 743 | -8.5433 | 4.0365 | 0.8797 | 0.8783 | 0.1087 | 0.0000 | 2.2755 | 8.0000 |
| rolling_60 | 743 | -8.5141 | 4.0751 | 0.8628 | 0.9769 | 0.0185 | 0.0000 | 0.2791 | 9.0000 |
| rolling_20 | 743 | -8.4891 | 4.2215 | 0.8816 | 0.9929 | 0.0056 | 0.0000 | 0.2709 | 10.0000 |
| markov_switching_2 | 743 | -8.4306 | 4.7464 | 1.0556 | 0.6978 | 0.3398 | 0.0000 | 74.0352 | 11.0000 |
| expanding | 743 | -8.3936 | 4.2542 | 1.0857 | 0.6821 | 0.3655 | 0.0000 | 0.3049 | 12.0000 |

Best incumbent by validation QLIKE: ewma_094 (-8.55846).
- markov_switching_2: QLIKE difference vs best incumbent +0.12791; calibration 0.698; rank 11 of 12.
- xgboost_v1: QLIKE difference vs best incumbent -0.01379; calibration 0.872; rank 1 of 12.

Paired comparison against the prespecified GARCH-normal reference:

| model | mean loss diff | boot ci low | boot ci high | dm p holm | boot p holm |
|---|---|---|---|---|---|
| markov_switching_2 | 0.1166 | 0.0364 | 0.1980 | 0.0003 | 0.0700 |
| xgboost_v1 | -0.0251 | -0.0719 | 0.0144 | 0.9970 | 1.0000 |

markov_switching_2 has higher mean QLIKE than the reference; the two adjusted tests do not jointly establish a difference.
xgboost_v1 has lower mean QLIKE than the reference; the two adjusted tests do not jointly establish a difference.

### SPY

| model | n evaluated | qlike | mse (x1e+08) | mae (x1e+04) | calibration ratio | bias (x1e+04) | fit failure rate | runtime seconds | rank qlike |
|---|---|---|---|---|---|---|---|---|---|
| xgboost_v1 | 753 | -8.2287 | 5.7946 | 1.2770 | 0.9295 | 0.0923 | 0.0000 | 13.6768 | 1.0000 |
| egarch_t | 753 | -8.2256 | 5.3535 | 1.2973 | 0.8880 | 0.1535 | 0.0000 | 1.7162 | 2.0000 |
| egarch_normal | 753 | -8.2191 | 5.3545 | 1.2946 | 0.9323 | 0.0883 | 0.0000 | 1.2329 | 3.0000 |
| gjr_t | 753 | -8.2075 | 5.7831 | 1.3390 | 0.8713 | 0.1798 | 0.0000 | 2.0779 | 4.0000 |
| gjr_normal | 753 | -8.1974 | 5.6765 | 1.3347 | 0.9012 | 0.1334 | 0.0000 | 1.3492 | 5.0000 |
| ewma_094 | 753 | -8.1941 | 5.0329 | 1.2547 | 0.9977 | 0.0028 | 0.0000 | 2.0682 | 6.0000 |
| garch_t | 753 | -8.1766 | 5.3775 | 1.3315 | 0.9183 | 0.1082 | 0.0000 | 1.6291 | 7.0000 |
| garch_normal | 753 | -8.1723 | 5.3739 | 1.3242 | 0.9443 | 0.0718 | 0.0000 | 1.0486 | 8.0000 |
| rolling_60 | 753 | -8.1637 | 5.1387 | 1.2738 | 0.9885 | 0.0142 | 0.0000 | 0.2157 | 9.0000 |
| markov_switching_2 | 753 | -8.1363 | 5.7454 | 1.5265 | 0.7034 | 0.5130 | 0.0000 | 21.9686 | 10.0000 |
| rolling_20 | 753 | -8.1304 | 5.1132 | 1.2674 | 0.9942 | 0.0070 | 0.0000 | 0.1895 | 11.0000 |
| expanding | 753 | -8.0038 | 5.5981 | 1.2991 | 1.0952 | -0.1057 | 0.0000 | 0.2023 | 12.0000 |

Best incumbent by validation QLIKE: egarch_t (-8.22556).
- markov_switching_2: QLIKE difference vs best incumbent +0.08928; calibration 0.703; rank 10 of 12.
- xgboost_v1: QLIKE difference vs best incumbent -0.00319; calibration 0.929; rank 1 of 12.

Paired comparison against the prespecified GARCH-normal reference:

| model | mean loss diff | boot ci low | boot ci high | dm p holm | boot p holm |
|---|---|---|---|---|---|
| markov_switching_2 | 0.0360 | -0.0007 | 0.0739 | 0.3501 | 0.2400 |
| xgboost_v1 | -0.0564 | -0.0998 | -0.0023 | 0.0760 | 0.1920 |

markov_switching_2 has higher mean QLIKE than the reference; the two adjusted tests do not jointly establish a difference.
xgboost_v1 has lower mean QLIKE than the reference; the two adjusted tests do not jointly establish a difference.

### VT

| model | n evaluated | qlike | mse (x1e+08) | mae (x1e+04) | calibration ratio | bias (x1e+04) | fit failure rate | runtime seconds | rank qlike |
|---|---|---|---|---|---|---|---|---|---|
| xgboost_v1 | 753 | -8.3226 | 4.0308 | 1.0988 | 0.9847 | 0.0169 | 0.0000 | 10.6712 | 1.0000 |
| egarch_t | 753 | -8.3083 | 4.1297 | 1.1433 | 0.9089 | 0.1089 | 0.0000 | 2.2319 | 2.0000 |
| egarch_normal | 753 | -8.3027 | 4.1523 | 1.1460 | 0.9360 | 0.0743 | 0.0000 | 1.5471 | 3.0000 |
| gjr_t | 753 | -8.3004 | 4.3119 | 1.1663 | 0.9124 | 0.1042 | 0.0000 | 2.1173 | 4.0000 |
| gjr_normal | 753 | -8.2924 | 4.3506 | 1.1803 | 0.9123 | 0.1044 | 0.0000 | 1.5824 | 5.0000 |
| ewma_094 | 753 | -8.2859 | 4.0452 | 1.1232 | 0.9972 | 0.0031 | 0.0000 | 2.5977 | 6.0000 |
| garch_t | 753 | -8.2745 | 4.2305 | 1.1856 | 0.9309 | 0.0806 | 0.0000 | 1.8245 | 7.0000 |
| garch_normal | 753 | -8.2722 | 4.2249 | 1.1793 | 0.9487 | 0.0587 | 0.0000 | 1.3488 | 8.0000 |
| rolling_60 | 753 | -8.2588 | 4.1275 | 1.1409 | 0.9866 | 0.0148 | 0.0000 | 0.8057 | 9.0000 |
| markov_switching_2 | 753 | -8.2390 | 4.7705 | 1.3541 | 0.7200 | 0.4224 | 0.0000 | 17.5702 | 10.0000 |
| rolling_20 | 753 | -8.2302 | 4.1300 | 1.1265 | 0.9963 | 0.0040 | 0.0000 | 0.7958 | 11.0000 |
| expanding | 753 | -8.1266 | 4.4316 | 1.1854 | 0.9890 | 0.0121 | 0.0000 | 0.8948 | 12.0000 |

Best incumbent by validation QLIKE: egarch_t (-8.30827).
- markov_switching_2: QLIKE difference vs best incumbent +0.06927; calibration 0.720; rank 10 of 12.
- xgboost_v1: QLIKE difference vs best incumbent -0.01438; calibration 0.985; rank 1 of 12.

Paired comparison against the prespecified GARCH-normal reference:

| model | mean loss diff | boot ci low | boot ci high | dm p holm | boot p holm |
|---|---|---|---|---|---|
| markov_switching_2 | 0.0332 | -0.0029 | 0.0712 | 0.5125 | 0.4560 |
| xgboost_v1 | -0.0505 | -0.0893 | -0.0100 | 0.1843 | 0.1600 |

markov_switching_2 has higher mean QLIKE than the reference; the two adjusted tests do not jointly establish a difference.
xgboost_v1 has lower mean QLIKE than the reference; the two adjusted tests do not jointly establish a difference.

## Shock response, overreaction and model complexity

The response table measures the change in next-session forecast variance after a retrospectively identified shock becomes observable. A larger response is faster adjustment, not evidence of better advance prediction or more reliable latent-regime detection. There is no observed ground truth for latent regimes in daily closes.

| asset | model | count | median | mean |
|---|---|---|---|---|
| NIFTY50_TRI | egarch_normal | 12 | 1.9639 | 1.8811 |
| NIFTY50_TRI | egarch_t | 12 | 1.8730 | 1.8633 |
| NIFTY50_TRI | ewma_094 | 12 | 2.1004 | 2.1576 |
| NIFTY50_TRI | expanding | 12 | 1.0135 | 1.0318 |
| NIFTY50_TRI | garch_normal | 12 | 2.0989 | 2.2389 |
| NIFTY50_TRI | garch_t | 12 | 1.9679 | 2.1351 |
| NIFTY50_TRI | gjr_normal | 12 | 2.4773 | 2.4602 |
| NIFTY50_TRI | gjr_t | 12 | 2.3896 | 2.4236 |
| NIFTY50_TRI | markov_switching_2 | 12 | 1.4570 | 2.8649 |
| NIFTY50_TRI | rolling_20 | 12 | 1.9976 | 2.0003 |
| NIFTY50_TRI | rolling_60 | 12 | 1.3822 | 1.4868 |
| NIFTY50_TRI | xgboost_v1 | 12 | 1.1628 | 1.3596 |
| SPY | egarch_normal | 20 | 2.6955 | 3.2306 |
| SPY | egarch_t | 20 | 2.7198 | 3.4302 |
| SPY | ewma_094 | 20 | 1.8930 | 2.1169 |
| SPY | expanding | 20 | 1.0117 | 1.0195 |
| SPY | garch_normal | 20 | 2.7304 | 2.9505 |
| SPY | garch_t | 20 | 2.4763 | 2.9589 |
| SPY | gjr_normal | 20 | 3.7674 | 4.4094 |
| SPY | gjr_t | 20 | 3.6525 | 4.7020 |
| SPY | markov_switching_2 | 20 | 1.3212 | 2.1532 |
| SPY | rolling_20 | 20 | 1.7471 | 2.0672 |
| SPY | rolling_60 | 20 | 1.3763 | 1.4374 |
| SPY | xgboost_v1 | 20 | 1.8495 | 2.3754 |
| VT | egarch_normal | 16 | 2.7138 | 3.2719 |
| VT | egarch_t | 16 | 2.5195 | 3.3098 |
| VT | ewma_094 | 16 | 1.9151 | 2.1209 |
| VT | expanding | 16 | 1.0104 | 1.0222 |
| VT | garch_normal | 16 | 2.8572 | 3.1255 |
| VT | garch_t | 16 | 2.6541 | 2.9151 |
| VT | gjr_normal | 16 | 3.6268 | 4.6338 |
| VT | gjr_t | 16 | 3.3704 | 4.5305 |
| VT | markov_switching_2 | 16 | 1.6739 | 2.1611 |
| VT | rolling_20 | 16 | 1.7628 | 2.0331 |
| VT | rolling_60 | 16 | 1.4071 | 1.4583 |
| VT | xgboost_v1 | 16 | 1.6826 | 2.2201 |

Recovery calibration below 1 indicates aggregate overforecasting in the labelled recovery subset; it does not prove that an individual shock was transient. Shock/recovery results are descriptive, involve small and sometimes overlapping event samples, and are not used for hyperparameter tuning.

| asset | model | n evaluated | qlike | calibration ratio |
|---|---|---|---|---|
| NIFTY50_TRI | egarch_normal | 431 | -8.0230 | 1.1086 |
| NIFTY50_TRI | egarch_t | 431 | -8.0024 | 1.1710 |
| NIFTY50_TRI | ewma_094 | 431 | -7.9915 | 0.6605 |
| NIFTY50_TRI | expanding | 431 | -7.4333 | 1.9117 |
| NIFTY50_TRI | garch_normal | 431 | -8.0167 | 0.8129 |
| NIFTY50_TRI | garch_t | 431 | -8.0250 | 0.8930 |
| NIFTY50_TRI | gjr_normal | 431 | -8.0469 | 0.6991 |
| NIFTY50_TRI | gjr_t | 431 | -8.0502 | 0.7262 |
| NIFTY50_TRI | markov_switching_2 | 431 | -7.7110 | 0.8762 |
| NIFTY50_TRI | rolling_20 | 431 | -7.9513 | 0.6401 |
| NIFTY50_TRI | rolling_60 | 431 | -7.8886 | 0.6797 |
| NIFTY50_TRI | xgboost_v1 | 431 | -7.8039 | 1.1229 |
| SPY | egarch_normal | 626 | -8.3468 | 1.1655 |
| SPY | egarch_t | 626 | -8.3680 | 1.0449 |
| SPY | ewma_094 | 626 | -8.2351 | 0.7613 |
| SPY | expanding | 626 | -7.2903 | 2.4104 |
| SPY | garch_normal | 626 | -8.3191 | 0.8834 |
| SPY | garch_t | 626 | -8.3172 | 0.7648 |
| SPY | gjr_normal | 626 | -8.3322 | 0.7462 |
| SPY | gjr_t | 626 | -8.3278 | 0.6783 |
| SPY | markov_switching_2 | 626 | -8.0450 | 1.3742 |
| SPY | rolling_20 | 626 | -8.1183 | 0.7197 |
| SPY | rolling_60 | 626 | -8.0724 | 0.8002 |
| SPY | xgboost_v1 | 626 | -8.2140 | 1.4943 |
| VT | egarch_normal | 504 | -8.1465 | 1.0273 |
| VT | egarch_t | 504 | -8.1453 | 1.0918 |
| VT | ewma_094 | 504 | -8.0080 | 0.7347 |
| VT | expanding | 504 | -7.1841 | 2.4802 |
| VT | garch_normal | 504 | -8.1105 | 0.8127 |
| VT | garch_t | 504 | -8.1127 | 0.8102 |
| VT | gjr_normal | 504 | -8.1242 | 0.6817 |
| VT | gjr_t | 504 | -8.1186 | 0.7112 |
| VT | markov_switching_2 | 504 | -7.7525 | 1.3442 |
| VT | rolling_20 | 504 | -7.9600 | 0.7003 |
| VT | rolling_60 | 504 | -7.8319 | 0.7657 |
| VT | xgboost_v1 | 504 | -7.8129 | 1.3868 |

## Research interpretation

- Regime switching versus GARCH is assessed per asset using the validation differences and paired tests above. State probabilities describe the fitted model, not verified economic regimes.
- XGBoost can represent nonlinear feature interactions, but predictive gains must appear in matched-date validation losses. Feature importance alone cannot establish that it captured missing economic mechanisms.
- Cross-market consistency requires improvement on all three separate asset comparisons; pooled loss levels are not used.
- Small ranks or loss differences without corrected statistical support do not establish superiority. Validation used for selection cannot later be relabelled an untouched final test.
- Maintenance costs include optimization failures/weak state separation for Markov switching and repeated training/tuning, feature-version control and drift for XGBoost. Runtime and failure rates must be considered alongside forecast losses.
- Stage 3 ends at forecasting. No position sizing, Heston, HAR-RV, LSTM or Transformer was implemented.

## Complete tables and reproducibility

The full model/period/sample tables follow. Detailed uncertainty, regime, state and feature outputs are stored in this immutable run. All-available forecasts and common-date flags are both retained in Parquet; missing forecasts are not filled.

```powershell
.\.venv\Scripts\python.exe -m volrisk.forecast_cli --config config/forecasting.toml run --experiment advanced --workers 4
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-advanced.xml
```

# Model comparison — experiment `advanced`

Run `20261103T115607990025Z_4774c4a9` created 2026-11-03T11:56:28.541428+00:00 from configuration `C:\Users\DELL\Desktop\nexus-volatility-research\config\forecasting.toml` (sha256 `371126437a13…`).

Forecast quantity: next-session conditional variance of the daily log return (decimal units); annualized volatility = sqrt(variance x 252). Evaluation target: realized squared daily log return, a noisy, unbiased proxy of the latent conditional variance, so loss levels are compared on identical dates and differences are tested rather than read off point estimates.

Periods evaluated: development, validation. The final holdout is **sealed**: its observations are excluded before modeling and diagnostics.

Splits (by target session): development 2012-01-01..2021-12-31; validation 2022-01-01..2024-12-31; holdout 2025-01-01..2026-10-30.

## Data

| Asset | Currency | Audit | Rows | Usable returns | First | Last | Contiguous |
|---|---|---|---|---|---|---|---|
| NIFTY50_TRI | INR | 572f825c852d8c0c540a207e | 3,222 | 3,220 | 2012-01-03 | 2024-12-31 | no |
| SPY | USD | 572f825c852d8c0c540a207e | 3,270 | 3,269 | 2012-01-04 | 2024-12-31 | yes |
| VT | USD | 572f825c852d8c0c540a207e | 3,270 | 3,269 | 2012-01-04 | 2024-12-31 | yes |

## Models

| Model | Type | Family | Version | Refit every | Min obs | Configuration |
|---|---|---|---|---|---|---|
| expanding | expanding | historical | 1.0.0 | 1 | 252 | center=True, ddof=1 |
| rolling_20 | rolling | historical | 1.0.0 | 1 | 252 | center=True, ddof=1, window=20 |
| rolling_60 | rolling | historical | 1.0.0 | 1 | 252 | center=True, ddof=1, window=60 |
| ewma_094 | ewma | historical | 1.0.0 | 1 | 252 | ddof=1, decay=0.94, init_window=252 |
| garch_normal | garch | garch | 1.0.0 | 21 | 500 | boundary_tol=0.0001, dist=normal, maxiter=500, o=0, p=1, persistence_warn=0.999, q=1, scale=100.0, vol=GARCH, window=1000 |
| garch_t | garch | garch | 1.0.0 | 21 | 500 | boundary_tol=0.0001, dist=t, maxiter=500, o=0, p=1, persistence_warn=0.999, q=1, scale=100.0, vol=GARCH, window=1000 |
| egarch_normal | garch | garch | 1.0.0 | 21 | 500 | boundary_tol=0.0001, dist=normal, maxiter=500, o=1, p=1, persistence_warn=0.999, q=1, scale=100.0, vol=EGARCH, window=1000 |
| egarch_t | garch | garch | 1.0.0 | 21 | 500 | boundary_tol=0.0001, dist=t, maxiter=500, o=1, p=1, persistence_warn=0.999, q=1, scale=100.0, vol=EGARCH, window=1000 |
| gjr_normal | garch | garch | 1.0.0 | 21 | 500 | boundary_tol=0.0001, dist=normal, maxiter=500, o=1, p=1, persistence_warn=0.999, q=1, scale=100.0, vol=GARCH, window=1000 |
| gjr_t | garch | garch | 1.0.0 | 21 | 500 | boundary_tol=0.0001, dist=t, maxiter=500, o=1, p=1, persistence_warn=0.999, q=1, scale=100.0, vol=GARCH, window=1000 |
| markov_switching_2 | markov_switching | regime_switching | 1.0.0 | 21 | 500 | em_iter=5, maxiter=200, min_occupancy=0.02, min_variance_ratio=1.1, n_states=2, scale=100.0, transition_boundary=0.001, window=1000 |
| xgboost_v1 | xgboost | machine_learning | 1.0.0 | 21 | 500 | cv_folds=2, cv_min_train=100, cv_size=60, hyperparameters={}, min_train_samples=300, retune_every=252, search_space=[{'max_depth': 2, 'n_estimators': 80}, {'max_depth': 3, 'n_estimators': 80}, {'max_depth': 2, 'n_estimators': 160}], seed=20261103, target_scale=10000.0, tuning_end=2021-12-31, variance_floor=1e-10, window=1500 |

Benchmark for statistical tests: `garch_normal`.

## NIFTY50_TRI

### NIFTY50_TRI — all period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gjr_normal | 2,220 | -8.5255 | 24.179 | 1.155 | 0.959 | 4.3% | 0.095 | 5.5 | 0.0% | 0.0% | 0 | 1 |
| gjr_t | 2,220 | -8.5254 | 23.940 | 1.141 | 0.983 | 1.8% | 0.088 | 7.8 | 0.0% | 0.0% | 0 | 2 |
| egarch_normal | 2,220 | -8.5100 | 25.101 | 1.094 | 1.163 | -14.0% | 0.113 | 6.1 | 0.0% | 0.0% | 0 | 3 |
| egarch_t | 2,220 | -8.5039 | 25.366 | 1.090 | 1.190 | -16.0% | 0.113 | 9.4 | 0.0% | 0.0% | 0 | 4 |
| ewma_094 | 2,220 | -8.4881 | 25.601 | 1.195 | 0.996 | 0.4% | 0.063 | 4.5 | 0.0% | 0.0% | 0 | 5 |
| garch_normal | 2,220 | -8.4855 | 24.959 | 1.153 | 1.039 | -3.8% | 0.077 | 6.0 | 0.0% | 0.0% | 0 | 6 |
| garch_t | 2,220 | -8.4839 | 25.269 | 1.132 | 1.092 | -8.4% | 0.064 | 8.6 | 0.0% | 0.0% | 0 | 7 |
| rolling_20 | 2,220 | -8.4506 | 27.344 | 1.223 | 1.006 | -0.6% | 0.079 | 1.0 | 0.0% | 0.0% | 0 | 8 |
| rolling_60 | 2,220 | -8.4016 | 28.606 | 1.278 | 0.995 | 0.5% | 0.027 | 1.0 | 0.0% | 0.0% | 0 | 9 |
| xgboost_v1 | 2,220 | -8.3930 | 28.335 | 1.154 | 1.210 | -17.4% | 0.158 | 80.0 | 0.0% | 0.0% | 0 | 10 |
| markov_switching_2 | 2,220 | -8.2840 | 29.259 | 1.340 | 0.956 | 4.6% | 0.108 | 121.5 | 0.0% | 0.0% | 0 | 11 |
| expanding | 2,220 | -8.1186 | 28.962 | 1.261 | 1.079 | -7.3% | 0.001 | 1.1 | 0.0% | 0.0% | 0 | 12 |

All available forecasts (all): gjr_normal n=2220 QLIKE=-8.5255; gjr_t n=2220 QLIKE=-8.5254; egarch_normal n=2220 QLIKE=-8.5100; egarch_t n=2220 QLIKE=-8.5039; garch_normal n=2220 QLIKE=-8.4855; garch_t n=2220 QLIKE=-8.4839; ewma_094 n=2716 QLIKE=-8.4031; xgboost_v1 n=2220 QLIKE=-8.3930; rolling_20 n=2716 QLIKE=-8.3715; rolling_60 n=2716 QLIKE=-8.3234; markov_switching_2 n=2220 QLIKE=-8.2840; expanding n=2716 QLIKE=-8.0911

Statistical comparison vs benchmark (all, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| gjr_normal | 2,220 | -0.0400 | -2.49 | 0.013 | 0.034 | 0.140 | 0.310 | yes | no |
| gjr_t | 2,220 | -0.0400 | -2.49 | 0.013 | 0.031 | 0.140 | 0.310 | yes | no |
| egarch_normal | 2,220 | -0.0245 | -1.22 | 0.224 | 0.207 | 1.000 | 1.000 | yes | no |
| egarch_t | 2,220 | -0.0185 | -0.82 | 0.410 | 0.419 | 1.000 | 1.000 | yes | no |
| ewma_094 | 2,220 | -0.0027 | -0.31 | 0.754 | 0.780 | 1.000 | 1.000 | yes | no |
| garch_t | 2,220 | 0.0015 | 0.32 | 0.752 | 0.808 | 1.000 | 1.000 | no | no |
| rolling_20 | 2,220 | 0.0349 | 2.32 | 0.021 | 0.019 | 0.164 | 0.209 | no | no |
| rolling_60 | 2,220 | 0.0838 | 2.47 | 0.014 | 0.039 | 0.140 | 0.312 | no | no |
| xgboost_v1 | 2,220 | 0.0924 | 1.02 | 0.310 | 0.484 | 1.000 | 1.000 | no | no |
| markov_switching_2 | 2,220 | 0.2014 | 2.04 | 0.042 | 0.073 | 0.251 | 0.511 | no | no |
| expanding | 2,220 | 0.3668 | 2.18 | 0.029 | 0.074 | 0.203 | 0.511 | no | no |

### NIFTY50_TRI — development period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gjr_t | 1,477 | -8.5165 | 33.952 | 1.272 | 1.021 | -2.1% | 0.085 | 5.5 | 0.0% | 0.0% | 0 | 1 |
| gjr_normal | 1,477 | -8.5146 | 34.306 | 1.294 | 0.990 | 1.1% | 0.092 | 4.0 | 0.0% | 0.0% | 0 | 2 |
| egarch_normal | 1,477 | -8.4903 | 35.722 | 1.205 | 1.299 | -23.0% | 0.113 | 4.4 | 0.0% | 0.0% | 0 | 3 |
| egarch_t | 1,477 | -8.4811 | 36.126 | 1.199 | 1.346 | -25.7% | 0.115 | 7.2 | 0.0% | 0.0% | 0 | 4 |
| garch_normal | 1,477 | -8.4544 | 35.476 | 1.289 | 1.092 | -8.4% | 0.069 | 4.2 | 0.0% | 0.0% | 0 | 5 |
| ewma_094 | 1,477 | -8.4528 | 36.452 | 1.368 | 0.998 | 0.2% | 0.064 | 2.4 | 0.0% | 0.0% | 0 | 6 |
| garch_t | 1,477 | -8.4521 | 35.955 | 1.259 | 1.163 | -14.0% | 0.060 | 6.1 | 0.0% | 0.0% | 0 | 7 |
| rolling_20 | 1,477 | -8.4312 | 38.975 | 1.395 | 1.011 | -1.1% | 0.077 | 0.8 | 0.0% | 0.0% | 0 | 8 |
| rolling_60 | 1,477 | -8.3451 | 40.946 | 1.486 | 1.001 | -0.1% | 0.028 | 0.8 | 0.0% | 0.0% | 0 | 9 |
| xgboost_v1 | 1,477 | -8.3029 | 40.538 | 1.288 | 1.382 | -27.6% | 0.183 | 41.0 | 0.0% | 0.0% | 0 | 10 |
| markov_switching_2 | 1,477 | -8.2103 | 41.590 | 1.483 | 1.084 | -7.7% | 0.111 | 47.4 | 0.0% | 0.0% | 0 | 11 |
| expanding | 1,477 | -7.9803 | 41.392 | 1.349 | 1.325 | -24.6% | 0.001 | 0.8 | 0.0% | 0.0% | 0 | 12 |

All available forecasts (development): gjr_t n=1477 QLIKE=-8.5165; gjr_normal n=1477 QLIKE=-8.5146; egarch_normal n=1477 QLIKE=-8.4903; egarch_t n=1477 QLIKE=-8.4811; garch_normal n=1477 QLIKE=-8.4544; garch_t n=1477 QLIKE=-8.4521; ewma_094 n=1973 QLIKE=-8.3446; rolling_20 n=1973 QLIKE=-8.3272; xgboost_v1 n=1477 QLIKE=-8.3029; rolling_60 n=1973 QLIKE=-8.2516; markov_switching_2 n=1477 QLIKE=-8.2103; expanding n=1973 QLIKE=-7.9772

Statistical comparison vs benchmark (development, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| gjr_t | 1,477 | -0.0620 | -3.25 | 0.001 | 0.011 | 0.013 | 0.121 | yes | no |
| gjr_normal | 1,477 | -0.0602 | -2.94 | 0.003 | 0.017 | 0.033 | 0.170 | yes | no |
| egarch_normal | 1,477 | -0.0359 | -1.35 | 0.178 | 0.162 | 1.000 | 0.810 | yes | no |
| egarch_t | 1,477 | -0.0267 | -0.88 | 0.380 | 0.374 | 1.000 | 1.000 | yes | no |
| ewma_094 | 1,477 | 0.0017 | 0.15 | 0.884 | 0.896 | 1.000 | 1.000 | no | no |
| garch_t | 1,477 | 0.0023 | 0.33 | 0.739 | 0.790 | 1.000 | 1.000 | no | no |
| rolling_20 | 1,477 | 0.0233 | 1.29 | 0.199 | 0.135 | 1.000 | 0.810 | no | no |
| rolling_60 | 1,477 | 0.1093 | 2.41 | 0.016 | 0.069 | 0.147 | 0.621 | no | no |
| xgboost_v1 | 1,477 | 0.1516 | 1.11 | 0.266 | 0.454 | 1.000 | 1.000 | no | no |
| markov_switching_2 | 1,477 | 0.2441 | 1.65 | 0.099 | 0.101 | 0.693 | 0.800 | no | no |
| expanding | 1,477 | 0.4741 | 1.89 | 0.060 | 0.100 | 0.476 | 0.800 | no | no |

### NIFTY50_TRI — validation period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| xgboost_v1 | 743 | -8.5722 | 4.076 | 0.888 | 0.872 | 14.7% | 0.109 | 39.0 | 0.0% | 0.0% | 0 | 1 |
| ewma_094 | 743 | -8.5585 | 4.031 | 0.852 | 0.989 | 1.1% | 0.062 | 2.1 | 0.0% | 0.0% | 0 | 2 |
| egarch_t | 743 | -8.5493 | 3.977 | 0.873 | 0.874 | 14.4% | 0.110 | 2.2 | 0.0% | 0.0% | 0 | 3 |
| egarch_normal | 743 | -8.5491 | 3.988 | 0.873 | 0.877 | 14.0% | 0.112 | 1.7 | 0.0% | 0.0% | 0 | 4 |
| garch_t | 743 | -8.5472 | 4.027 | 0.878 | 0.918 | 8.9% | 0.072 | 2.5 | 0.0% | 0.0% | 0 | 5 |
| garch_normal | 743 | -8.5471 | 4.053 | 0.884 | 0.903 | 10.7% | 0.093 | 1.8 | 0.0% | 0.0% | 0 | 6 |
| gjr_normal | 743 | -8.5471 | 4.047 | 0.881 | 0.873 | 14.5% | 0.102 | 1.4 | 0.0% | 0.0% | 0 | 7 |
| gjr_t | 743 | -8.5433 | 4.037 | 0.880 | 0.878 | 13.9% | 0.093 | 2.3 | 0.0% | 0.0% | 0 | 8 |
| rolling_60 | 743 | -8.5141 | 4.075 | 0.863 | 0.977 | 2.4% | 0.025 | 0.3 | 0.0% | 0.0% | 0 | 9 |
| rolling_20 | 743 | -8.4891 | 4.222 | 0.882 | 0.993 | 0.7% | 0.082 | 0.3 | 0.0% | 0.0% | 0 | 10 |
| markov_switching_2 | 743 | -8.4306 | 4.746 | 1.056 | 0.698 | 43.3% | 0.102 | 74.0 | 0.0% | 0.0% | 0 | 11 |
| expanding | 743 | -8.3936 | 4.254 | 1.086 | 0.682 | 46.6% | 0.000 | 0.3 | 0.0% | 0.0% | 0 | 12 |

All available forecasts (validation): xgboost_v1 n=743 QLIKE=-8.5722; ewma_094 n=743 QLIKE=-8.5585; egarch_t n=743 QLIKE=-8.5493; egarch_normal n=743 QLIKE=-8.5491; garch_t n=743 QLIKE=-8.5472; garch_normal n=743 QLIKE=-8.5471; gjr_normal n=743 QLIKE=-8.5471; gjr_t n=743 QLIKE=-8.5433; rolling_60 n=743 QLIKE=-8.5141; rolling_20 n=743 QLIKE=-8.4891; markov_switching_2 n=743 QLIKE=-8.4306; expanding n=743 QLIKE=-8.3936

Statistical comparison vs benchmark (validation, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| xgboost_v1 | 743 | -0.0251 | -1.54 | 0.125 | 0.204 | 0.997 | 1.000 | yes | no |
| ewma_094 | 743 | -0.0113 | -1.00 | 0.317 | 0.297 | 1.000 | 1.000 | yes | no |
| egarch_t | 743 | -0.0022 | -0.07 | 0.940 | 0.930 | 1.000 | 1.000 | yes | no |
| egarch_normal | 743 | -0.0019 | -0.07 | 0.947 | 0.922 | 1.000 | 1.000 | yes | no |
| garch_t | 743 | -0.0001 | -0.02 | 0.983 | 0.986 | 1.000 | 1.000 | yes | no |
| gjr_normal | 743 | 0.0001 | 0.00 | 0.998 | 0.996 | 1.000 | 1.000 | no | no |
| gjr_t | 743 | 0.0038 | 0.13 | 0.894 | 0.891 | 1.000 | 1.000 | no | no |
| rolling_60 | 743 | 0.0330 | 0.72 | 0.469 | 0.468 | 1.000 | 1.000 | no | no |
| rolling_20 | 743 | 0.0580 | 2.16 | 0.031 | 0.026 | 0.283 | 0.234 | no | no |
| markov_switching_2 | 743 | 0.1166 | 4.19 | 0.000 | 0.007 | 0.000 | 0.070 | no | no |
| expanding | 743 | 0.1535 | 4.61 | 0.000 | 0.002 | 0.000 | 0.022 | no | yes |

### NIFTY50_TRI — regimes (common dates, evaluated periods)

Ex-ante regimes use the tercile of trailing 60-session variance relative to its own history at the origin (known at forecast time). Retrospective labels (shock sessions, post-shock recovery, named event windows) use information after the origin and are descriptive only.

Observations per regime: ex_ante_volatility_regime:high=619; ex_ante_volatility_regime:low=1044; ex_ante_volatility_regime:medium=557; retrospective:post_shock_recovery=431; retrospective:shock_session=12; retrospective_event:calm_2017=248; retrospective_event:covid_crash_2020=45; retrospective_event:covid_recovery_2020=170; retrospective_event:india_election_jun_2024=10; retrospective_event:q4_2018_selloff=61; retrospective_event:rate_shock_2022=248; retrospective_event:recovery_2023=246; retrospective_event:vol_spike_aug_2024=21; retrospective_event:volmageddon_feb_2018=19.

| Model (QLIKE) | ex_ante_volatility_regime:high | ex_ante_volatility_regime:low | ex_ante_volatility_regime:medium | retrospective:post_shock_recovery | retrospective:shock_session | retrospective_event:calm_2017 | retrospective_event:covid_crash_2020 | retrospective_event:covid_recovery_2020 | retrospective_event:india_election_jun_2024 | retrospective_event:q4_2018_selloff | retrospective_event:rate_shock_2022 | retrospective_event:recovery_2023 | retrospective_event:vol_spike_aug_2024 | retrospective_event:volmageddon_feb_2018 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | -7.9681 | -8.9101 | -8.3622 | -8.0230 | 10.3216 | -9.2385 | -4.8910 | -7.6499 | -0.5146 | -8.1454 | -8.1592 | -9.0581 | -8.3400 | -7.8267 |
| egarch_t | -7.9480 | -8.9099 | -8.3609 | -8.0024 | 10.6034 | -9.2352 | -4.7392 | -7.6086 | -0.5400 | -8.1546 | -8.1624 | -9.0534 | -8.3427 | -7.8581 |
| ewma_094 | -7.8982 | -8.8919 | -8.3869 | -7.9915 | 11.4131 | -9.2571 | -4.6434 | -7.8446 | -1.9568 | -7.9616 | -8.0918 | -9.1527 | -8.3436 | -7.8319 |
| expanding | -6.9369 | -8.7213 | -8.3023 | -7.4333 | 38.8778 | -9.0024 | 8.2072 | -7.8275 | -3.3396 | -7.8711 | -8.0362 | -8.7363 | -8.3869 | -8.3775 |
| garch_normal | -7.9326 | -8.8820 | -8.3565 | -8.0167 | 11.2238 | -9.1853 | -4.6652 | -7.8714 | -2.0540 | -7.9615 | -8.0874 | -9.1059 | -8.2943 | -7.9824 |
| garch_t | -7.9204 | -8.8868 | -8.3551 | -8.0250 | 12.4337 | -9.1950 | -4.3823 | -7.8981 | -1.9830 | -7.9598 | -8.0916 | -9.1005 | -8.3263 | -8.0722 |
| gjr_normal | -8.0162 | -8.9098 | -8.3711 | -8.0469 | 8.5064 | -9.2230 | -5.4345 | -7.7796 | -0.3716 | -8.1101 | -8.1578 | -9.0884 | -8.3709 | -7.9644 |
| gjr_t | -8.0153 | -8.9125 | -8.3668 | -8.0502 | 8.9592 | -9.2221 | -5.3893 | -7.8045 | -0.0776 | -8.1078 | -8.1570 | -9.0921 | -8.3609 | -7.9981 |
| markov_switching_2 | -7.3752 | -8.8006 | -8.3258 | -7.7110 | 26.3786 | -9.1101 | 1.9962 | -7.7682 | -2.7225 | -8.0048 | -7.9796 | -8.8432 | -8.1491 | -8.2986 |
| rolling_20 | -7.8788 | -8.8411 | -8.3539 | -7.9513 | 11.7542 | -9.1969 | -4.4679 | -7.8886 | -1.8264 | -7.9130 | -8.0540 | -9.0927 | -7.8906 | -7.3981 |
| rolling_60 | -7.6787 | -8.8920 | -8.2859 | -7.8886 | 21.1493 | -9.2709 | -2.7454 | -7.7295 | 0.9617 | -7.7371 | -8.0710 | -9.1586 | -8.2656 | -7.8657 |
| xgboost_v1 | -7.5164 | -8.9190 | -8.3815 | -7.8039 | 24.6162 | -9.2613 | 1.3360 | -7.8628 | -2.6424 | -8.0528 | -8.1188 | -9.0881 | -8.2475 | -8.2091 |

| Model (calibration ratio) | ex_ante_volatility_regime:high | ex_ante_volatility_regime:low | ex_ante_volatility_regime:medium | retrospective:post_shock_recovery | retrospective:shock_session | retrospective_event:calm_2017 | retrospective_event:covid_crash_2020 | retrospective_event:covid_recovery_2020 | retrospective_event:india_election_jun_2024 | retrospective_event:q4_2018_selloff | retrospective_event:rate_shock_2022 | retrospective_event:recovery_2023 | retrospective_event:vol_spike_aug_2024 | retrospective_event:volmageddon_feb_2018 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 1.434 | 0.851 | 1.025 | 1.109 | 16.219 | 0.623 | 2.841 | 1.240 | 3.764 | 1.041 | 0.883 | 0.644 | 1.002 | 1.044 |
| egarch_t | 1.510 | 0.848 | 1.027 | 1.171 | 17.269 | 0.616 | 3.163 | 1.353 | 3.566 | 1.059 | 0.891 | 0.636 | 1.018 | 1.018 |
| ewma_094 | 0.894 | 1.180 | 1.170 | 0.661 | 15.793 | 0.918 | 1.334 | 0.579 | 2.313 | 1.046 | 0.978 | 0.991 | 0.932 | 1.368 |
| expanding | 2.021 | 0.530 | 0.904 | 1.912 | 47.048 | 0.409 | 16.470 | 1.166 | 5.720 | 1.651 | 0.984 | 0.335 | 0.734 | 1.130 |
| garch_normal | 1.089 | 0.892 | 1.092 | 0.813 | 16.039 | 0.608 | 1.580 | 0.948 | 2.639 | 1.127 | 0.936 | 0.702 | 0.938 | 1.499 |
| garch_t | 1.187 | 0.889 | 1.115 | 0.893 | 18.750 | 0.622 | 1.854 | 1.003 | 2.776 | 1.183 | 0.980 | 0.682 | 0.969 | 1.402 |
| gjr_normal | 0.965 | 0.873 | 1.048 | 0.699 | 8.751 | 0.621 | 1.099 | 0.979 | 2.262 | 1.016 | 0.922 | 0.685 | 0.866 | 0.934 |
| gjr_t | 1.001 | 0.880 | 1.061 | 0.726 | 9.484 | 0.622 | 1.167 | 1.012 | 2.265 | 1.049 | 0.942 | 0.688 | 0.869 | 0.955 |
| markov_switching_2 | 1.137 | 0.684 | 0.937 | 0.876 | 40.378 | 0.498 | 3.365 | 0.621 | 5.115 | 1.229 | 0.738 | 0.397 | 0.773 | 1.022 |
| rolling_20 | 0.899 | 1.229 | 1.168 | 0.640 | 16.779 | 0.971 | 1.113 | 0.827 | 2.189 | 1.016 | 0.994 | 1.017 | 0.957 | 1.212 |
| rolling_60 | 0.887 | 1.213 | 1.165 | 0.680 | 31.886 | 0.856 | 2.424 | 0.372 | 5.169 | 1.150 | 0.937 | 1.011 | 0.552 | 1.811 |
| xgboost_v1 | 1.487 | 0.882 | 1.080 | 1.123 | 37.627 | 0.695 | 3.582 | 0.961 | 4.639 | 1.160 | 0.909 | 0.628 | 0.914 | 0.855 |

### NIFTY50_TRI — estimation stability (GARCH family)

| Model | Fits | Failed | Non-converged | Boundary flags | Persistence mean | Persistence sd | Persistence min | Persistence max | Max refit jump |
|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 107 | 0 | 0 | 0 | 0.9587 | 0.0214 | 0.8847 | 0.9908 | 0.0716 |
| egarch_t | 107 | 0 | 0 | 0 | 0.9587 | 0.0187 | 0.8880 | 0.9897 | 0.0671 |
| garch_normal | 107 | 0 | 0 | 0 | 0.9734 | 0.0199 | 0.9090 | 0.9963 | 0.0772 |
| garch_t | 107 | 0 | 0 | 0 | 0.9710 | 0.0150 | 0.9245 | 0.9955 | 0.0630 |
| gjr_normal | 107 | 0 | 0 | 97 | 0.9618 | 0.0188 | 0.9146 | 0.9924 | 0.0769 |
| gjr_t | 107 | 0 | 0 | 98 | 0.9617 | 0.0186 | 0.8960 | 0.9926 | 0.0665 |

## SPY

### SPY — all period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_t | 2,769 | -8.5660 | 15.131 | 1.148 | 1.056 | -5.3% | 0.208 | 6.8 | 0.0% | 0.0% | 0 | 1 |
| egarch_normal | 2,769 | -8.5562 | 15.679 | 1.141 | 1.116 | -10.4% | 0.207 | 5.2 | 0.0% | 0.0% | 0 | 2 |
| gjr_t | 2,769 | -8.5547 | 16.046 | 1.231 | 0.885 | 13.0% | 0.183 | 8.2 | 0.0% | 0.0% | 0 | 3 |
| gjr_normal | 2,769 | -8.5514 | 15.385 | 1.205 | 0.934 | 7.0% | 0.179 | 5.0 | 0.0% | 0.0% | 0 | 4 |
| garch_t | 2,769 | -8.5181 | 14.847 | 1.220 | 0.961 | 4.1% | 0.150 | 7.2 | 0.0% | 0.0% | 0 | 5 |
| garch_normal | 2,769 | -8.5156 | 14.552 | 1.186 | 1.035 | -3.4% | 0.156 | 3.9 | 0.0% | 0.0% | 0 | 6 |
| xgboost_v1 | 2,769 | -8.4919 | 20.701 | 1.154 | 1.314 | -23.9% | 0.236 | 127.8 | 0.0% | 0.0% | 0 | 7 |
| ewma_094 | 2,769 | -8.4537 | 17.535 | 1.260 | 1.002 | -0.2% | 0.066 | 5.3 | 0.0% | 0.0% | 0 | 8 |
| markov_switching_2 | 2,769 | -8.3723 | 21.400 | 1.371 | 0.994 | 0.6% | 0.143 | 123.6 | 0.0% | 0.0% | 0 | 9 |
| rolling_20 | 2,769 | -8.3686 | 18.950 | 1.274 | 0.994 | 0.6% | 0.084 | 0.8 | 0.0% | 0.0% | 0 | 10 |
| rolling_60 | 2,769 | -8.3459 | 21.267 | 1.383 | 0.999 | 0.1% | 0.028 | 0.8 | 0.0% | 0.0% | 0 | 11 |
| expanding | 2,769 | -8.0064 | 21.833 | 1.256 | 1.429 | -30.0% | 0.001 | 0.9 | 0.0% | 0.0% | 0 | 12 |

All available forecasts (all): egarch_t n=2769 QLIKE=-8.5660; egarch_normal n=2769 QLIKE=-8.5562; gjr_t n=2769 QLIKE=-8.5547; gjr_normal n=2769 QLIKE=-8.5514; garch_t n=2769 QLIKE=-8.5181; garch_normal n=2769 QLIKE=-8.5156; ewma_094 n=3017 QLIKE=-8.4921; xgboost_v1 n=2769 QLIKE=-8.4919; rolling_20 n=3017 QLIKE=-8.4053; rolling_60 n=3017 QLIKE=-8.3911; markov_switching_2 n=2769 QLIKE=-8.3723; expanding n=3017 QLIKE=-8.0817

Statistical comparison vs benchmark (all, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| egarch_t | 2,769 | -0.0504 | -2.26 | 0.024 | 0.020 | 0.169 | 0.160 | yes | no |
| egarch_normal | 2,769 | -0.0406 | -1.77 | 0.076 | 0.076 | 0.309 | 0.320 | yes | no |
| gjr_t | 2,769 | -0.0391 | -1.82 | 0.070 | 0.064 | 0.309 | 0.320 | yes | no |
| gjr_normal | 2,769 | -0.0358 | -1.87 | 0.062 | 0.065 | 0.309 | 0.320 | yes | no |
| garch_t | 2,769 | -0.0025 | -0.74 | 0.460 | 0.470 | 0.920 | 0.940 | yes | no |
| xgboost_v1 | 2,769 | 0.0236 | 0.43 | 0.671 | 0.717 | 0.920 | 0.940 | no | no |
| ewma_094 | 2,769 | 0.0619 | 2.87 | 0.004 | 0.003 | 0.037 | 0.030 | no | yes |
| markov_switching_2 | 2,769 | 0.1433 | 2.14 | 0.032 | 0.051 | 0.193 | 0.306 | no | no |
| rolling_20 | 2,769 | 0.1470 | 4.03 | 0.000 | 0.000 | 0.001 | 0.000 | no | yes |
| rolling_60 | 2,769 | 0.1697 | 3.62 | 0.000 | 0.006 | 0.003 | 0.054 | no | no |
| expanding | 2,769 | 0.5092 | 2.56 | 0.011 | 0.035 | 0.084 | 0.245 | no | no |

### SPY — development period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_t | 2,016 | -8.6931 | 18.783 | 1.092 | 1.141 | -12.4% | 0.225 | 5.1 | 0.0% | 0.0% | 0 | 1 |
| gjr_t | 2,016 | -8.6844 | 19.880 | 1.190 | 0.890 | 12.3% | 0.194 | 6.2 | 0.0% | 0.0% | 0 | 2 |
| gjr_normal | 2,016 | -8.6836 | 19.011 | 1.157 | 0.948 | 5.5% | 0.188 | 3.7 | 0.0% | 0.0% | 0 | 3 |
| egarch_normal | 2,016 | -8.6821 | 19.536 | 1.084 | 1.210 | -17.4% | 0.225 | 3.9 | 0.0% | 0.0% | 0 | 4 |
| garch_t | 2,016 | -8.6457 | 18.384 | 1.178 | 0.978 | 2.2% | 0.152 | 5.6 | 0.0% | 0.0% | 0 | 5 |
| garch_normal | 2,016 | -8.6438 | 17.980 | 1.135 | 1.076 | -7.1% | 0.159 | 2.9 | 0.0% | 0.0% | 0 | 6 |
| xgboost_v1 | 2,016 | -8.5903 | 26.269 | 1.109 | 1.568 | -36.2% | 0.256 | 114.1 | 0.0% | 0.0% | 0 | 7 |
| ewma_094 | 2,016 | -8.5507 | 22.205 | 1.261 | 1.004 | -0.4% | 0.067 | 3.2 | 0.0% | 0.0% | 0 | 8 |
| markov_switching_2 | 2,016 | -8.4605 | 27.247 | 1.313 | 1.186 | -15.7% | 0.148 | 101.6 | 0.0% | 0.0% | 0 | 9 |
| rolling_20 | 2,016 | -8.4575 | 24.118 | 1.277 | 0.994 | 0.6% | 0.087 | 0.6 | 0.0% | 0.0% | 0 | 10 |
| rolling_60 | 2,016 | -8.4140 | 27.292 | 1.424 | 1.003 | -0.3% | 0.030 | 0.6 | 0.0% | 0.0% | 0 | 11 |
| expanding | 2,016 | -8.0073 | 27.897 | 1.240 | 1.623 | -38.4% | 0.001 | 0.7 | 0.0% | 0.0% | 0 | 12 |

All available forecasts (development): egarch_t n=2016 QLIKE=-8.6931; gjr_t n=2016 QLIKE=-8.6844; gjr_normal n=2016 QLIKE=-8.6836; egarch_normal n=2016 QLIKE=-8.6821; garch_t n=2016 QLIKE=-8.6457; garch_normal n=2016 QLIKE=-8.6438; ewma_094 n=2264 QLIKE=-8.5912; xgboost_v1 n=2016 QLIKE=-8.5903; rolling_20 n=2264 QLIKE=-8.4967; rolling_60 n=2264 QLIKE=-8.4667; markov_switching_2 n=2016 QLIKE=-8.4605; expanding n=2264 QLIKE=-8.1077

Statistical comparison vs benchmark (development, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| egarch_t | 2,016 | -0.0493 | -1.66 | 0.096 | 0.098 | 0.578 | 0.588 | yes | no |
| gjr_t | 2,016 | -0.0405 | -1.41 | 0.159 | 0.148 | 0.634 | 0.592 | yes | no |
| gjr_normal | 2,016 | -0.0398 | -1.55 | 0.121 | 0.111 | 0.606 | 0.588 | yes | no |
| egarch_normal | 2,016 | -0.0383 | -1.25 | 0.213 | 0.202 | 0.638 | 0.606 | yes | no |
| garch_t | 2,016 | -0.0019 | -0.41 | 0.682 | 0.661 | 0.930 | 1.000 | yes | no |
| xgboost_v1 | 2,016 | 0.0536 | 0.73 | 0.465 | 0.519 | 0.930 | 1.000 | no | no |
| ewma_094 | 2,016 | 0.0931 | 3.23 | 0.001 | 0.002 | 0.011 | 0.020 | no | yes |
| markov_switching_2 | 2,016 | 0.1833 | 2.09 | 0.037 | 0.076 | 0.260 | 0.532 | no | no |
| rolling_20 | 2,016 | 0.1863 | 3.98 | 0.000 | 0.000 | 0.001 | 0.000 | no | yes |
| rolling_60 | 2,016 | 0.2298 | 3.72 | 0.000 | 0.003 | 0.002 | 0.027 | no | yes |
| expanding | 2,016 | 0.6365 | 2.43 | 0.015 | 0.063 | 0.120 | 0.504 | no | no |

### SPY — validation period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| xgboost_v1 | 753 | -8.2287 | 5.795 | 1.277 | 0.929 | 7.6% | 0.184 | 13.7 | 0.0% | 0.0% | 0 | 1 |
| egarch_t | 753 | -8.2256 | 5.354 | 1.297 | 0.888 | 12.6% | 0.161 | 1.7 | 0.0% | 0.0% | 0 | 2 |
| egarch_normal | 753 | -8.2191 | 5.354 | 1.295 | 0.932 | 7.3% | 0.159 | 1.2 | 0.0% | 0.0% | 0 | 3 |
| gjr_t | 753 | -8.2075 | 5.783 | 1.339 | 0.871 | 14.8% | 0.154 | 2.1 | 0.0% | 0.0% | 0 | 4 |
| gjr_normal | 753 | -8.1974 | 5.676 | 1.335 | 0.901 | 11.0% | 0.155 | 1.3 | 0.0% | 0.0% | 0 | 5 |
| ewma_094 | 753 | -8.1941 | 5.033 | 1.255 | 0.998 | 0.2% | 0.062 | 2.1 | 0.0% | 0.0% | 0 | 6 |
| garch_t | 753 | -8.1766 | 5.377 | 1.332 | 0.918 | 8.9% | 0.144 | 1.6 | 0.0% | 0.0% | 0 | 7 |
| garch_normal | 753 | -8.1723 | 5.374 | 1.324 | 0.944 | 5.9% | 0.149 | 1.0 | 0.0% | 0.0% | 0 | 8 |
| rolling_60 | 753 | -8.1637 | 5.139 | 1.274 | 0.989 | 1.2% | 0.024 | 0.2 | 0.0% | 0.0% | 0 | 9 |
| markov_switching_2 | 753 | -8.1363 | 5.745 | 1.526 | 0.703 | 42.2% | 0.131 | 22.0 | 0.0% | 0.0% | 0 | 10 |
| rolling_20 | 753 | -8.1304 | 5.113 | 1.267 | 0.994 | 0.6% | 0.076 | 0.2 | 0.0% | 0.0% | 0 | 11 |
| expanding | 753 | -8.0038 | 5.598 | 1.299 | 1.095 | -8.7% | 0.000 | 0.2 | 0.0% | 0.0% | 0 | 12 |

All available forecasts (validation): xgboost_v1 n=753 QLIKE=-8.2287; egarch_t n=753 QLIKE=-8.2256; egarch_normal n=753 QLIKE=-8.2191; gjr_t n=753 QLIKE=-8.2075; gjr_normal n=753 QLIKE=-8.1974; ewma_094 n=753 QLIKE=-8.1941; garch_t n=753 QLIKE=-8.1766; garch_normal n=753 QLIKE=-8.1723; rolling_60 n=753 QLIKE=-8.1637; markov_switching_2 n=753 QLIKE=-8.1363; rolling_20 n=753 QLIKE=-8.1304; expanding n=753 QLIKE=-8.0038

Statistical comparison vs benchmark (validation, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| xgboost_v1 | 753 | -0.0564 | -2.60 | 0.009 | 0.026 | 0.076 | 0.192 | yes | no |
| egarch_t | 753 | -0.0533 | -2.77 | 0.006 | 0.005 | 0.051 | 0.050 | yes | no |
| egarch_normal | 753 | -0.0468 | -3.12 | 0.002 | 0.002 | 0.019 | 0.022 | yes | yes |
| gjr_t | 753 | -0.0352 | -2.35 | 0.019 | 0.024 | 0.135 | 0.192 | yes | no |
| gjr_normal | 753 | -0.0251 | -2.13 | 0.033 | 0.047 | 0.199 | 0.240 | yes | no |
| ewma_094 | 753 | -0.0218 | -1.55 | 0.120 | 0.129 | 0.361 | 0.387 | yes | no |
| garch_t | 753 | -0.0042 | -1.81 | 0.070 | 0.040 | 0.350 | 0.240 | yes | no |
| rolling_60 | 753 | 0.0086 | 0.32 | 0.750 | 0.791 | 0.751 | 0.791 | no | no |
| markov_switching_2 | 753 | 0.0360 | 1.77 | 0.077 | 0.059 | 0.350 | 0.240 | no | no |
| rolling_20 | 753 | 0.0419 | 0.89 | 0.375 | 0.359 | 0.751 | 0.718 | no | no |
| expanding | 753 | 0.1685 | 3.55 | 0.000 | 0.005 | 0.005 | 0.050 | no | no |

### SPY — regimes (common dates, evaluated periods)

Ex-ante regimes use the tercile of trailing 60-session variance relative to its own history at the origin (known at forecast time). Retrospective labels (shock sessions, post-shock recovery, named event windows) use information after the origin and are descriptive only.

Observations per regime: ex_ante_volatility_regime:high=1252; ex_ante_volatility_regime:low=871; ex_ante_volatility_regime:medium=646; retrospective:post_shock_recovery=626; retrospective:shock_session=20; retrospective_event:calm_2017=251; retrospective_event:covid_crash_2020=50; retrospective_event:covid_recovery_2020=170; retrospective_event:india_election_jun_2024=10; retrospective_event:q4_2018_selloff=63; retrospective_event:rate_shock_2022=251; retrospective_event:recovery_2023=250; retrospective_event:vol_spike_aug_2024=22; retrospective_event:volmageddon_feb_2018=19.

| Model (QLIKE) | ex_ante_volatility_regime:high | ex_ante_volatility_regime:low | ex_ante_volatility_regime:medium | retrospective:post_shock_recovery | retrospective:shock_session | retrospective_event:calm_2017 | retrospective_event:covid_crash_2020 | retrospective_event:covid_recovery_2020 | retrospective_event:india_election_jun_2024 | retrospective_event:q4_2018_selloff | retrospective_event:rate_shock_2022 | retrospective_event:recovery_2023 | retrospective_event:vol_spike_aug_2024 | retrospective_event:volmageddon_feb_2018 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | -8.0046 | -9.1559 | -8.8166 | -8.3468 | 2.0611 | -9.8127 | -5.1041 | -7.5569 | -9.4905 | -7.0011 | -7.3035 | -8.6054 | -8.0707 | -6.6904 |
| egarch_t | -8.0264 | -9.1525 | -8.8207 | -8.3680 | 1.8715 | -9.8395 | -5.2751 | -7.5901 | -9.5219 | -7.0827 | -7.3329 | -8.6100 | -8.0458 | -6.7800 |
| ewma_094 | -7.9355 | -9.0375 | -8.6710 | -8.2351 | 10.2414 | -9.8020 | -4.5198 | -7.8103 | -9.5221 | -6.4949 | -7.3400 | -8.6101 | -7.7308 | -5.2586 |
| expanding | -7.0614 | -8.9448 | -8.5724 | -7.2903 | 24.8830 | -9.4020 | 11.7344 | -7.7710 | -8.9102 | -6.0807 | -6.9900 | -8.4813 | -7.8383 | -4.5982 |
| garch_normal | -7.9855 | -9.1245 | -8.7220 | -8.3191 | 3.9300 | -9.7499 | -5.1557 | -7.8462 | -9.4245 | -6.8766 | -7.2767 | -8.5788 | -7.8211 | -6.4457 |
| garch_t | -7.9920 | -9.1266 | -8.7174 | -8.3172 | 3.7997 | -9.7727 | -5.2096 | -7.8702 | -9.4290 | -6.8932 | -7.2906 | -8.5809 | -7.8291 | -6.5010 |
| gjr_normal | -7.9954 | -9.1775 | -8.7848 | -8.3322 | 2.4319 | -9.8006 | -5.4281 | -7.5749 | -9.4982 | -6.9688 | -7.2639 | -8.6107 | -7.9228 | -6.7643 |
| gjr_t | -7.9934 | -9.1854 | -8.7920 | -8.3278 | 2.2525 | -9.8348 | -5.4631 | -7.5252 | -9.5269 | -7.0130 | -7.2772 | -8.6274 | -7.9635 | -6.8029 |
| markov_switching_2 | -7.7004 | -9.1053 | -8.6863 | -8.0450 | 11.0436 | -9.7131 | 0.1364 | -7.7394 | -9.3873 | -6.9521 | -7.2398 | -8.5198 | -7.8966 | -6.2127 |
| rolling_20 | -7.8941 | -8.8828 | -8.5946 | -8.1183 | 12.2903 | -9.6101 | -4.6913 | -7.7451 | -9.5656 | -6.5097 | -7.3137 | -8.5915 | -7.6559 | -5.2091 |
| rolling_60 | -7.7529 | -8.9796 | -8.6409 | -8.0724 | 16.3110 | -9.8352 | -2.4131 | -7.6520 | -9.4633 | -6.2336 | -7.3180 | -8.5968 | -7.2043 | -2.7215 |
| xgboost_v1 | -7.8320 | -9.1869 | -8.8340 | -8.2140 | 8.2956 | -9.8636 | -1.3460 | -7.4209 | -9.5580 | -7.1293 | -7.3007 | -8.6081 | -8.1042 | -6.1877 |

| Model (calibration ratio) | ex_ante_volatility_regime:high | ex_ante_volatility_regime:low | ex_ante_volatility_regime:medium | retrospective:post_shock_recovery | retrospective:shock_session | retrospective_event:calm_2017 | retrospective_event:covid_crash_2020 | retrospective_event:covid_recovery_2020 | retrospective_event:india_election_jun_2024 | retrospective_event:q4_2018_selloff | retrospective_event:rate_shock_2022 | retrospective_event:recovery_2023 | retrospective_event:vol_spike_aug_2024 | retrospective_event:volmageddon_feb_2018 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 1.206 | 0.955 | 0.875 | 1.166 | 7.134 | 0.571 | 2.208 | 0.884 | 0.484 | 1.245 | 0.976 | 0.749 | 1.210 | 1.560 |
| egarch_t | 1.116 | 0.969 | 0.861 | 1.045 | 6.356 | 0.622 | 1.899 | 0.823 | 0.493 | 1.102 | 0.911 | 0.743 | 1.061 | 1.339 |
| ewma_094 | 0.948 | 1.400 | 1.080 | 0.761 | 10.369 | 0.963 | 1.216 | 0.618 | 0.565 | 1.536 | 1.023 | 0.889 | 1.110 | 1.704 |
| expanding | 2.270 | 0.622 | 0.724 | 2.410 | 36.257 | 0.305 | 19.416 | 1.361 | 0.210 | 3.632 | 2.126 | 0.599 | 1.283 | 5.066 |
| garch_normal | 1.062 | 0.997 | 0.931 | 0.883 | 5.393 | 0.552 | 1.252 | 0.979 | 0.455 | 1.356 | 1.018 | 0.789 | 1.001 | 1.411 |
| garch_t | 0.960 | 1.017 | 0.918 | 0.765 | 4.973 | 0.590 | 1.062 | 0.888 | 0.463 | 1.152 | 0.970 | 0.796 | 0.972 | 1.177 |
| gjr_normal | 0.936 | 0.996 | 0.874 | 0.746 | 4.014 | 0.578 | 1.034 | 0.893 | 0.501 | 1.054 | 0.928 | 0.810 | 0.952 | 0.936 |
| gjr_t | 0.875 | 0.999 | 0.850 | 0.678 | 3.799 | 0.625 | 0.953 | 0.845 | 0.520 | 0.898 | 0.887 | 0.823 | 0.872 | 0.757 |
| markov_switching_2 | 1.074 | 0.886 | 0.750 | 1.374 | 24.039 | 0.502 | 5.314 | 0.512 | 0.416 | 1.707 | 0.699 | 0.677 | 0.843 | 2.660 |
| rolling_20 | 0.935 | 1.472 | 1.075 | 0.720 | 10.321 | 0.986 | 1.042 | 0.854 | 0.761 | 1.383 | 0.998 | 0.946 | 0.859 | 1.366 |
| rolling_60 | 0.942 | 1.411 | 1.092 | 0.800 | 23.584 | 0.940 | 1.924 | 0.374 | 0.482 | 2.200 | 1.046 | 0.792 | 1.835 | 3.535 |
| xgboost_v1 | 1.478 | 0.968 | 0.995 | 1.494 | 17.163 | 0.646 | 4.274 | 1.493 | 0.573 | 1.447 | 1.019 | 0.698 | 1.113 | 2.296 |

### SPY — estimation stability (GARCH family)

| Model | Fits | Failed | Non-converged | Boundary flags | Persistence mean | Persistence sd | Persistence min | Persistence max | Max refit jump |
|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 132 | 0 | 0 | 0 | 0.9289 | 0.0213 | 0.8979 | 0.9897 | 0.0338 |
| egarch_t | 132 | 0 | 0 | 0 | 0.9376 | 0.0251 | 0.8952 | 0.9840 | 0.0151 |
| garch_normal | 132 | 0 | 0 | 0 | 0.9374 | 0.0429 | 0.8522 | 0.9937 | 0.0258 |
| garch_t | 132 | 0 | 0 | 21 | 0.9596 | 0.0465 | 0.8437 | 1.0000 | 0.0214 |
| gjr_normal | 132 | 0 | 0 | 73 | 0.9602 | 0.0275 | 0.9137 | 1.0000 | 0.0287 |
| gjr_t | 132 | 0 | 0 | 88 | 0.9768 | 0.0222 | 0.9181 | 1.0000 | 0.0124 |

## VT

### VT — all period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 2,769 | -8.5627 | 16.850 | 1.085 | 1.083 | -7.7% | 0.160 | 5.1 | 0.0% | 0.0% | 0 | 1 |
| gjr_normal | 2,769 | -8.5563 | 18.040 | 1.172 | 0.909 | 10.0% | 0.163 | 6.0 | 0.0% | 0.0% | 0 | 2 |
| gjr_t | 2,769 | -8.5555 | 17.410 | 1.150 | 0.932 | 7.3% | 0.153 | 7.9 | 0.0% | 0.0% | 0 | 3 |
| garch_t | 2,769 | -8.5305 | 16.778 | 1.146 | 0.996 | 0.4% | 0.135 | 7.7 | 0.0% | 0.0% | 0 | 4 |
| garch_normal | 2,769 | -8.5297 | 16.463 | 1.140 | 1.001 | -0.1% | 0.144 | 5.2 | 0.0% | 0.0% | 0 | 5 |
| ewma_094 | 2,769 | -8.4870 | 19.856 | 1.206 | 1.002 | -0.2% | 0.064 | 18.0 | 0.0% | 0.0% | 0 | 6 |
| egarch_t | 2,769 | -8.4465 | 17.573 | 1.085 | 1.100 | -9.1% | 0.169 | 8.0 | 0.0% | 0.0% | 0 | 7 |
| xgboost_v1 | 2,769 | -8.4364 | 23.012 | 1.110 | 1.296 | -22.8% | 0.176 | 55.2 | 0.0% | 0.0% | 0 | 8 |
| rolling_20 | 2,769 | -8.4219 | 21.743 | 1.226 | 0.996 | 0.4% | 0.081 | 3.2 | 0.0% | 0.0% | 0 | 9 |
| rolling_60 | 2,769 | -8.3849 | 23.418 | 1.311 | 0.998 | 0.2% | 0.027 | 3.3 | 0.0% | 0.0% | 0 | 10 |
| markov_switching_2 | 2,769 | -8.3650 | 23.739 | 1.310 | 0.987 | 1.3% | 0.133 | 61.3 | 0.0% | 0.0% | 0 | 11 |
| expanding | 2,769 | -8.0793 | 23.820 | 1.223 | 1.276 | -21.6% | 0.001 | 3.7 | 0.0% | 0.0% | 0 | 12 |

All available forecasts (all): egarch_normal n=2769 QLIKE=-8.5627; gjr_normal n=2769 QLIKE=-8.5563; gjr_t n=2769 QLIKE=-8.5555; garch_t n=2769 QLIKE=-8.5305; garch_normal n=2769 QLIKE=-8.5297; ewma_094 n=3017 QLIKE=-8.5080; egarch_t n=2769 QLIKE=-8.4465; rolling_20 n=3017 QLIKE=-8.4455; xgboost_v1 n=2769 QLIKE=-8.4364; rolling_60 n=3017 QLIKE=-8.4133; markov_switching_2 n=2769 QLIKE=-8.3650; expanding n=3017 QLIKE=-8.1307

Statistical comparison vs benchmark (all, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 2,769 | -0.0330 | -1.70 | 0.090 | 0.079 | 0.449 | 0.469 | yes | no |
| gjr_normal | 2,769 | -0.0266 | -1.86 | 0.063 | 0.069 | 0.380 | 0.469 | yes | no |
| gjr_t | 2,769 | -0.0259 | -1.47 | 0.140 | 0.149 | 0.562 | 0.596 | yes | no |
| garch_t | 2,769 | -0.0008 | -0.48 | 0.633 | 0.674 | 0.843 | 1.000 | yes | no |
| ewma_094 | 2,769 | 0.0426 | 2.53 | 0.011 | 0.016 | 0.103 | 0.144 | no | no |
| egarch_t | 2,769 | 0.0831 | 0.80 | 0.422 | 0.538 | 0.843 | 1.000 | no | no |
| xgboost_v1 | 2,769 | 0.0933 | 1.14 | 0.255 | 0.334 | 0.764 | 1.000 | no | no |
| rolling_20 | 2,769 | 0.1078 | 4.09 | 0.000 | 0.000 | 0.000 | 0.000 | no | yes |
| rolling_60 | 2,769 | 0.1447 | 3.22 | 0.001 | 0.007 | 0.013 | 0.070 | no | no |
| markov_switching_2 | 2,769 | 0.1646 | 1.93 | 0.054 | 0.067 | 0.376 | 0.469 | no | no |
| expanding | 2,769 | 0.4504 | 2.28 | 0.023 | 0.051 | 0.183 | 0.408 | no | no |

### VT — development period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 2,016 | -8.6598 | 21.593 | 1.063 | 1.148 | -12.9% | 0.168 | 3.6 | 0.0% | 0.0% | 0 | 1 |
| gjr_normal | 2,016 | -8.6548 | 23.153 | 1.170 | 0.908 | 10.2% | 0.170 | 4.4 | 0.0% | 0.0% | 0 | 2 |
| gjr_t | 2,016 | -8.6508 | 22.302 | 1.144 | 0.939 | 6.5% | 0.159 | 5.8 | 0.0% | 0.0% | 0 | 3 |
| garch_t | 2,016 | -8.6261 | 21.465 | 1.131 | 1.022 | -2.2% | 0.137 | 5.8 | 0.0% | 0.0% | 0 | 4 |
| garch_normal | 2,016 | -8.6258 | 21.034 | 1.126 | 1.021 | -2.1% | 0.149 | 3.9 | 0.0% | 0.0% | 0 | 5 |
| ewma_094 | 2,016 | -8.5622 | 25.762 | 1.237 | 1.003 | -0.3% | 0.065 | 15.4 | 0.0% | 0.0% | 0 | 6 |
| egarch_t | 2,016 | -8.4982 | 22.595 | 1.064 | 1.190 | -15.9% | 0.180 | 5.8 | 0.0% | 0.0% | 0 | 7 |
| rolling_20 | 2,016 | -8.4935 | 28.322 | 1.263 | 0.995 | 0.5% | 0.084 | 2.4 | 0.0% | 0.0% | 0 | 8 |
| xgboost_v1 | 2,016 | -8.4788 | 30.101 | 1.114 | 1.461 | -31.6% | 0.181 | 44.5 | 0.0% | 0.0% | 0 | 9 |
| rolling_60 | 2,016 | -8.4320 | 30.624 | 1.375 | 1.002 | -0.2% | 0.028 | 2.5 | 0.0% | 0.0% | 0 | 10 |
| markov_switching_2 | 2,016 | -8.4121 | 30.824 | 1.293 | 1.139 | -12.2% | 0.133 | 43.7 | 0.0% | 0.0% | 0 | 11 |
| expanding | 2,016 | -8.0616 | 31.062 | 1.236 | 1.425 | -29.8% | 0.001 | 2.8 | 0.0% | 0.0% | 0 | 12 |

All available forecasts (development): egarch_normal n=2016 QLIKE=-8.6598; gjr_normal n=2016 QLIKE=-8.6548; gjr_t n=2016 QLIKE=-8.6508; garch_t n=2016 QLIKE=-8.6261; garch_normal n=2016 QLIKE=-8.6258; ewma_094 n=2264 QLIKE=-8.5819; rolling_20 n=2264 QLIKE=-8.5170; egarch_t n=2016 QLIKE=-8.4982; xgboost_v1 n=2016 QLIKE=-8.4788; rolling_60 n=2264 QLIKE=-8.4647; markov_switching_2 n=2016 QLIKE=-8.4121; expanding n=2264 QLIKE=-8.1321

Statistical comparison vs benchmark (development, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 2,016 | -0.0339 | -1.30 | 0.193 | 0.175 | 0.871 | 0.875 | yes | no |
| gjr_normal | 2,016 | -0.0290 | -1.53 | 0.127 | 0.122 | 0.759 | 0.732 | yes | no |
| gjr_t | 2,016 | -0.0250 | -1.07 | 0.283 | 0.265 | 0.871 | 1.000 | yes | no |
| garch_t | 2,016 | -0.0002 | -0.11 | 0.913 | 0.931 | 0.913 | 1.000 | yes | no |
| ewma_094 | 2,016 | 0.0637 | 2.87 | 0.004 | 0.008 | 0.037 | 0.072 | no | no |
| egarch_t | 2,016 | 0.1277 | 0.91 | 0.361 | 0.522 | 0.871 | 1.000 | no | no |
| rolling_20 | 2,016 | 0.1324 | 4.16 | 0.000 | 0.000 | 0.000 | 0.000 | no | yes |
| xgboost_v1 | 2,016 | 0.1470 | 1.36 | 0.174 | 0.255 | 0.871 | 1.000 | no | no |
| rolling_60 | 2,016 | 0.1938 | 3.26 | 0.001 | 0.007 | 0.011 | 0.070 | no | no |
| markov_switching_2 | 2,016 | 0.2138 | 1.90 | 0.058 | 0.085 | 0.407 | 0.595 | no | no |
| expanding | 2,016 | 0.5643 | 2.16 | 0.031 | 0.074 | 0.249 | 0.592 | no | no |

### VT — validation period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| xgboost_v1 | 753 | -8.3226 | 4.031 | 1.099 | 0.985 | 1.6% | 0.163 | 10.7 | 0.0% | 0.0% | 0 | 1 |
| egarch_t | 753 | -8.3083 | 4.130 | 1.143 | 0.909 | 10.0% | 0.140 | 2.2 | 0.0% | 0.0% | 0 | 2 |
| egarch_normal | 753 | -8.3027 | 4.152 | 1.146 | 0.936 | 6.8% | 0.141 | 1.5 | 0.0% | 0.0% | 0 | 3 |
| gjr_t | 753 | -8.3004 | 4.312 | 1.166 | 0.912 | 9.6% | 0.138 | 2.1 | 0.0% | 0.0% | 0 | 4 |
| gjr_normal | 753 | -8.2924 | 4.351 | 1.180 | 0.912 | 9.6% | 0.143 | 1.6 | 0.0% | 0.0% | 0 | 5 |
| ewma_094 | 753 | -8.2859 | 4.045 | 1.123 | 0.997 | 0.3% | 0.062 | 2.6 | 0.0% | 0.0% | 0 | 6 |
| garch_t | 753 | -8.2745 | 4.230 | 1.186 | 0.931 | 7.4% | 0.130 | 1.8 | 0.0% | 0.0% | 0 | 7 |
| garch_normal | 753 | -8.2722 | 4.225 | 1.179 | 0.949 | 5.4% | 0.131 | 1.3 | 0.0% | 0.0% | 0 | 8 |
| rolling_60 | 753 | -8.2588 | 4.128 | 1.141 | 0.987 | 1.4% | 0.024 | 0.8 | 0.0% | 0.0% | 0 | 9 |
| markov_switching_2 | 753 | -8.2390 | 4.771 | 1.354 | 0.720 | 38.9% | 0.135 | 17.6 | 0.0% | 0.0% | 0 | 10 |
| rolling_20 | 753 | -8.2302 | 4.130 | 1.127 | 0.996 | 0.4% | 0.074 | 0.8 | 0.0% | 0.0% | 0 | 11 |
| expanding | 753 | -8.1266 | 4.432 | 1.185 | 0.989 | 1.1% | 0.000 | 0.9 | 0.0% | 0.0% | 0 | 12 |

All available forecasts (validation): xgboost_v1 n=753 QLIKE=-8.3226; egarch_t n=753 QLIKE=-8.3083; egarch_normal n=753 QLIKE=-8.3027; gjr_t n=753 QLIKE=-8.3004; gjr_normal n=753 QLIKE=-8.2924; ewma_094 n=753 QLIKE=-8.2859; garch_t n=753 QLIKE=-8.2745; garch_normal n=753 QLIKE=-8.2722; rolling_60 n=753 QLIKE=-8.2588; markov_switching_2 n=753 QLIKE=-8.2390; rolling_20 n=753 QLIKE=-8.2302; expanding n=753 QLIKE=-8.1266

Statistical comparison vs benchmark (validation, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| xgboost_v1 | 753 | -0.0505 | -2.36 | 0.018 | 0.016 | 0.184 | 0.160 | yes | no |
| egarch_t | 753 | -0.0361 | -2.06 | 0.040 | 0.024 | 0.349 | 0.216 | yes | no |
| egarch_normal | 753 | -0.0305 | -2.01 | 0.045 | 0.030 | 0.349 | 0.240 | yes | no |
| gjr_t | 753 | -0.0282 | -2.07 | 0.039 | 0.031 | 0.349 | 0.240 | yes | no |
| gjr_normal | 753 | -0.0203 | -1.65 | 0.099 | 0.114 | 0.513 | 0.570 | yes | no |
| ewma_094 | 753 | -0.0137 | -0.91 | 0.365 | 0.305 | 1.000 | 0.915 | yes | no |
| garch_t | 753 | -0.0023 | -1.20 | 0.231 | 0.166 | 0.925 | 0.664 | yes | no |
| rolling_60 | 753 | 0.0134 | 0.56 | 0.576 | 0.636 | 1.000 | 0.915 | no | no |
| markov_switching_2 | 753 | 0.0332 | 1.72 | 0.085 | 0.076 | 0.513 | 0.456 | no | no |
| rolling_20 | 753 | 0.0419 | 0.93 | 0.353 | 0.323 | 1.000 | 0.915 | no | no |
| expanding | 753 | 0.1456 | 3.60 | 0.000 | 0.000 | 0.004 | 0.000 | no | yes |

### VT — regimes (common dates, evaluated periods)

Ex-ante regimes use the tercile of trailing 60-session variance relative to its own history at the origin (known at forecast time). Retrospective labels (shock sessions, post-shock recovery, named event windows) use information after the origin and are descriptive only.

Observations per regime: ex_ante_volatility_regime:high=1071; ex_ante_volatility_regime:low=1008; ex_ante_volatility_regime:medium=690; retrospective:post_shock_recovery=504; retrospective:shock_session=16; retrospective_event:calm_2017=251; retrospective_event:covid_crash_2020=50; retrospective_event:covid_recovery_2020=170; retrospective_event:india_election_jun_2024=10; retrospective_event:q4_2018_selloff=63; retrospective_event:rate_shock_2022=251; retrospective_event:recovery_2023=250; retrospective_event:vol_spike_aug_2024=22; retrospective_event:volmageddon_feb_2018=19.

| Model (QLIKE) | ex_ante_volatility_regime:high | ex_ante_volatility_regime:low | ex_ante_volatility_regime:medium | retrospective:post_shock_recovery | retrospective:shock_session | retrospective_event:calm_2017 | retrospective_event:covid_crash_2020 | retrospective_event:covid_recovery_2020 | retrospective_event:india_election_jun_2024 | retrospective_event:q4_2018_selloff | retrospective_event:rate_shock_2022 | retrospective_event:recovery_2023 | retrospective_event:vol_spike_aug_2024 | retrospective_event:volmageddon_feb_2018 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | -8.0029 | -9.1412 | -8.5863 | -8.1465 | 5.4393 | -9.8298 | -5.3116 | -7.8433 | -9.4261 | -7.4882 | -7.4602 | -8.6228 | -7.8422 | -6.8255 |
| egarch_t | -7.9987 | -8.8251 | -8.5886 | -8.1453 | 5.6215 | -9.8690 | -5.2076 | -7.8097 | -9.4231 | -7.5164 | -7.4777 | -8.6239 | -7.8958 | -6.7769 |
| ewma_094 | -7.9216 | -9.0418 | -8.5541 | -8.0080 | 10.2886 | -9.7986 | -4.5460 | -7.9079 | -9.4498 | -7.2207 | -7.4691 | -8.6312 | -7.7249 | -5.6618 |
| expanding | -7.0981 | -8.8658 | -8.4531 | -7.1841 | 29.5557 | -9.2725 | 10.4774 | -7.8827 | -8.8950 | -7.1160 | -7.2459 | -8.5216 | -7.8808 | -5.6885 |
| garch_normal | -7.9787 | -9.0769 | -8.5853 | -8.1105 | 4.9077 | -9.7263 | -5.1955 | -7.9252 | -9.3671 | -7.3300 | -7.4320 | -8.6056 | -7.7675 | -6.7144 |
| garch_t | -7.9810 | -9.0773 | -8.5846 | -8.1127 | 5.0675 | -9.7371 | -5.1680 | -7.9421 | -9.3682 | -7.3517 | -7.4391 | -8.6051 | -7.7908 | -6.6621 |
| gjr_normal | -7.9967 | -9.1278 | -8.5900 | -8.1242 | 4.6000 | -9.7670 | -5.4120 | -7.8440 | -9.4179 | -7.4036 | -7.4223 | -8.6327 | -7.9246 | -6.9332 |
| gjr_t | -7.9845 | -9.1326 | -8.5988 | -8.1186 | 4.5822 | -9.7846 | -5.3936 | -7.7569 | -9.4087 | -7.4318 | -7.4373 | -8.6444 | -7.9400 | -6.9269 |
| markov_switching_2 | -7.6104 | -9.0446 | -8.5435 | -7.7525 | 15.5003 | -9.6359 | 1.2593 | -7.7570 | -9.3075 | -7.4444 | -7.3520 | -8.6038 | -7.8522 | -6.5436 |
| rolling_20 | -7.8867 | -8.9516 | -8.4789 | -7.9600 | 11.9878 | -9.6831 | -4.6726 | -7.8852 | -9.4953 | -7.1523 | -7.4394 | -8.6118 | -7.6633 | -5.5942 |
| rolling_60 | -7.7529 | -8.9882 | -8.4846 | -7.8319 | 17.7958 | -9.8070 | -2.4187 | -7.7644 | -9.4271 | -7.0187 | -7.4406 | -8.6312 | -7.1934 | -3.5678 |
| xgboost_v1 | -7.6993 | -9.1117 | -8.5938 | -7.8129 | 15.9808 | -9.8250 | 0.8676 | -7.7202 | -9.5385 | -7.3513 | -7.4553 | -8.6398 | -8.0390 | -6.2364 |

| Model (calibration ratio) | ex_ante_volatility_regime:high | ex_ante_volatility_regime:low | ex_ante_volatility_regime:medium | retrospective:post_shock_recovery | retrospective:shock_session | retrospective_event:calm_2017 | retrospective_event:covid_crash_2020 | retrospective_event:covid_recovery_2020 | retrospective_event:india_election_jun_2024 | retrospective_event:q4_2018_selloff | retrospective_event:rate_shock_2022 | retrospective_event:recovery_2023 | retrospective_event:vol_spike_aug_2024 | retrospective_event:volmageddon_feb_2018 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 1.177 | 0.966 | 0.890 | 1.027 | 7.681 | 0.701 | 1.827 | 0.980 | 0.564 | 1.067 | 0.987 | 0.759 | 1.414 | 1.269 |
| egarch_t | 1.205 | 0.959 | 0.895 | 1.092 | 8.903 | 0.753 | 2.131 | 0.994 | 0.554 | 1.054 | 0.950 | 0.761 | 1.276 | 1.322 |
| ewma_094 | 0.935 | 1.289 | 1.105 | 0.735 | 12.705 | 0.955 | 1.217 | 0.604 | 0.655 | 1.387 | 1.024 | 0.906 | 1.168 | 1.693 |
| expanding | 2.158 | 0.555 | 0.836 | 2.480 | 41.201 | 0.272 | 18.304 | 1.230 | 0.241 | 2.469 | 1.873 | 0.574 | 1.258 | 3.864 |
| garch_normal | 1.024 | 0.960 | 0.948 | 0.813 | 5.849 | 0.566 | 1.169 | 0.935 | 0.516 | 1.183 | 1.041 | 0.790 | 1.090 | 1.229 |
| garch_t | 1.014 | 0.968 | 0.953 | 0.810 | 6.564 | 0.583 | 1.199 | 0.934 | 0.522 | 1.145 | 1.004 | 0.799 | 1.054 | 1.215 |
| gjr_normal | 0.911 | 0.930 | 0.881 | 0.682 | 4.442 | 0.605 | 0.944 | 0.910 | 0.563 | 0.978 | 0.962 | 0.815 | 0.989 | 0.944 |
| gjr_t | 0.944 | 0.927 | 0.888 | 0.711 | 5.266 | 0.619 | 1.044 | 0.975 | 0.552 | 0.952 | 0.961 | 0.835 | 0.947 | 0.878 |
| markov_switching_2 | 1.103 | 0.813 | 0.793 | 1.344 | 32.913 | 0.474 | 4.908 | 0.476 | 0.449 | 1.296 | 0.716 | 0.738 | 0.886 | 2.433 |
| rolling_20 | 0.928 | 1.331 | 1.076 | 0.700 | 13.203 | 0.981 | 1.046 | 0.853 | 0.800 | 1.270 | 1.003 | 0.963 | 0.907 | 1.366 |
| rolling_60 | 0.925 | 1.285 | 1.146 | 0.766 | 28.952 | 0.925 | 1.939 | 0.361 | 0.581 | 1.872 | 1.048 | 0.818 | 1.925 | 3.441 |
| xgboost_v1 | 1.541 | 0.929 | 0.994 | 1.387 | 29.443 | 0.715 | 3.882 | 1.418 | 0.646 | 1.112 | 1.119 | 0.753 | 1.247 | 1.896 |

### VT — estimation stability (GARCH family)

| Model | Fits | Failed | Non-converged | Boundary flags | Persistence mean | Persistence sd | Persistence min | Persistence max | Max refit jump |
|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 132 | 0 | 0 | 0 | 0.9491 | 0.0142 | 0.9257 | 0.9924 | 0.0271 |
| egarch_t | 132 | 0 | 0 | 0 | 0.9536 | 0.0164 | 0.9214 | 0.9890 | 0.0242 |
| garch_normal | 132 | 0 | 0 | 0 | 0.9560 | 0.0267 | 0.8922 | 0.9926 | 0.0314 |
| garch_t | 132 | 0 | 0 | 0 | 0.9634 | 0.0282 | 0.8844 | 0.9977 | 0.0348 |
| gjr_normal | 132 | 0 | 0 | 53 | 0.9668 | 0.0232 | 0.9160 | 1.0000 | 0.0179 |
| gjr_t | 132 | 0 | 0 | 56 | 0.9676 | 0.0193 | 0.9170 | 0.9971 | 0.0164 |

## Run summaries

| Asset | Model | Origins | Valid | Missing | Invalid flags | Fits | Failed fits | Flagged fits | Non-converged | Runtime (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| NIFTY50_TRI | expanding | 2,718 | 2,718 | 0 | n/a | 2,718 | 0 | 0 | 0 | 1.7 |
| NIFTY50_TRI | rolling_20 | 2,718 | 2,718 | 0 | n/a | 2,718 | 0 | 0 | 0 | 1.6 |
| NIFTY50_TRI | rolling_60 | 2,718 | 2,718 | 0 | n/a | 2,718 | 0 | 0 | 0 | 1.6 |
| NIFTY50_TRI | ewma_094 | 2,718 | 2,718 | 0 | n/a | 2,718 | 0 | 0 | 0 | 5.2 |
| NIFTY50_TRI | garch_normal | 2,222 | 2,222 | 0 | n/a | 107 | 0 | 0 | 0 | 6.5 |
| NIFTY50_TRI | garch_t | 2,222 | 2,222 | 0 | n/a | 107 | 0 | 0 | 0 | 9.1 |
| NIFTY50_TRI | egarch_normal | 2,222 | 2,222 | 0 | n/a | 107 | 0 | 0 | 0 | 6.6 |
| NIFTY50_TRI | egarch_t | 2,222 | 2,222 | 0 | n/a | 107 | 0 | 0 | 0 | 9.9 |
| NIFTY50_TRI | gjr_normal | 2,222 | 2,222 | 0 | n/a | 107 | 0 | 97 | 0 | 6.0 |
| NIFTY50_TRI | gjr_t | 2,222 | 2,222 | 0 | n/a | 107 | 0 | 98 | 0 | 8.2 |
| NIFTY50_TRI | markov_switching_2 | 2,222 | 2,222 | 0 | n/a | 107 | 0 | 0 | 0 | 122.7 |
| NIFTY50_TRI | xgboost_v1 | 2,222 | 2,222 | 0 | n/a | 107 | 0 | 0 | 0 | 81.5 |
| SPY | expanding | 3,018 | 3,018 | 0 | n/a | 3,018 | 0 | 0 | 0 | 1.3 |
| SPY | rolling_20 | 3,018 | 3,018 | 0 | n/a | 3,018 | 0 | 0 | 0 | 1.2 |
| SPY | rolling_60 | 3,018 | 3,018 | 0 | n/a | 3,018 | 0 | 0 | 0 | 1.2 |
| SPY | ewma_094 | 3,018 | 3,018 | 0 | n/a | 3,018 | 0 | 0 | 0 | 6.0 |
| SPY | garch_normal | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 0 | 0 | 4.3 |
| SPY | garch_t | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 21 | 0 | 7.6 |
| SPY | egarch_normal | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 0 | 0 | 5.6 |
| SPY | egarch_t | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 0 | 0 | 7.2 |
| SPY | gjr_normal | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 73 | 0 | 5.4 |
| SPY | gjr_t | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 88 | 0 | 8.7 |
| SPY | markov_switching_2 | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 0 | 0 | 125.1 |
| SPY | xgboost_v1 | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 0 | 0 | 129.6 |
| VT | expanding | 3,018 | 3,018 | 0 | n/a | 3,018 | 0 | 0 | 0 | 5.7 |
| VT | rolling_20 | 3,018 | 3,018 | 0 | n/a | 3,018 | 0 | 0 | 0 | 5.3 |
| VT | rolling_60 | 3,018 | 3,018 | 0 | n/a | 3,018 | 0 | 0 | 0 | 5.0 |
| VT | ewma_094 | 3,018 | 3,018 | 0 | n/a | 3,018 | 0 | 0 | 0 | 20.9 |
| VT | garch_normal | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 0 | 0 | 5.8 |
| VT | garch_t | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 0 | 0 | 8.1 |
| VT | egarch_normal | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 0 | 0 | 5.6 |
| VT | egarch_t | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 0 | 0 | 8.5 |
| VT | gjr_normal | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 53 | 0 | 6.5 |
| VT | gjr_t | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 56 | 0 | 8.3 |
| VT | markov_switching_2 | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 0 | 0 | 62.0 |
| VT | xgboost_v1 | 2,770 | 2,770 | 0 | n/a | 132 | 0 | 0 | 0 | 56.1 |

Metric definitions: QLIKE = log(h) + r²/h (lower is better, computed only for strictly positive finite h); MSE/MAE on variance units; calibration = mean r² / mean h; relative bias = mean h / mean r² - 1; stability = mean |Δ log h| between consecutive origins; runtime = total fit+update+forecast seconds. Rank is by QLIKE within asset/period/sample. Small differences are not treated as meaningful without the statistical tests above.
