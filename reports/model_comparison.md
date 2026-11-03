# Model comparison — experiment `econometric`

Run `20261103T112009388792Z_e137742e` created 2026-11-03T11:20:26.072949+00:00 from configuration `C:\Users\DELL\Desktop\nexus-volatility-research\config\forecasting.toml` (sha256 `7d3fd6d328bb…`).

Forecast quantity: next-session conditional variance of the daily log return (decimal units); annualized volatility = sqrt(variance x 252). Evaluation target: realized squared daily log return, a noisy, unbiased proxy of the latent conditional variance, so loss levels are compared on identical dates and differences are tested rather than read off point estimates.

Periods evaluated: development, validation. The final holdout is **sealed**: its forecasts are stored but not evaluated here.

Splits (by target session): development 2012-01-01..2021-12-31; validation 2022-01-01..2024-12-31; holdout 2025-01-01..2026-10-30.

## Data

| Asset | Currency | Audit | Rows | Usable returns | First | Last | Contiguous |
|---|---|---|---|---|---|---|---|
| NIFTY50_TRI | INR | 572f825c852d8c0c540a207e | 3,677 | 3,676 | 2012-01-03 | 2026-11-02 | yes |
| SPY | USD | 572f825c852d8c0c540a207e | 3,730 | 3,729 | 2012-01-04 | 2026-11-02 | yes |
| VT | USD | 572f825c852d8c0c540a207e | 3,730 | 3,729 | 2012-01-04 | 2026-11-02 | yes |

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

Benchmark for statistical tests: `garch_normal`.

## NIFTY50_TRI

### NIFTY50_TRI — all period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gjr_normal | 2,721 | -8.4691 | 21.175 | 1.145 | 0.952 | 5.1% | 0.091 | 5.7 | 0.0% | 0.0% | 0 | 1 |
| gjr_t | 2,721 | -8.4683 | 20.827 | 1.135 | 0.968 | 3.3% | 0.085 | 6.8 | 0.0% | 0.0% | 0 | 2 |
| egarch_normal | 2,721 | -8.4665 | 21.354 | 1.079 | 1.136 | -12.0% | 0.104 | 4.7 | 0.0% | 0.0% | 0 | 3 |
| egarch_t | 2,721 | -8.4634 | 21.498 | 1.077 | 1.152 | -13.2% | 0.105 | 6.3 | 0.0% | 0.0% | 0 | 4 |
| garch_normal | 2,721 | -8.4380 | 21.026 | 1.137 | 1.022 | -2.1% | 0.073 | 4.6 | 0.0% | 0.0% | 0 | 5 |
| garch_t | 2,721 | -8.4371 | 21.154 | 1.114 | 1.068 | -6.4% | 0.061 | 6.2 | 0.0% | 0.0% | 0 | 6 |
| ewma_094 | 2,721 | -8.4332 | 21.774 | 1.168 | 0.999 | 0.1% | 0.063 | 5.0 | 0.0% | 0.0% | 0 | 7 |
| rolling_20 | 2,721 | -8.4016 | 23.208 | 1.192 | 1.006 | -0.6% | 0.078 | 0.6 | 0.0% | 0.0% | 0 | 8 |
| rolling_60 | 2,721 | -8.3585 | 24.236 | 1.237 | 1.001 | -0.1% | 0.027 | 0.7 | 0.0% | 0.0% | 0 | 9 |
| expanding | 2,721 | -8.1420 | 24.499 | 1.232 | 1.047 | -4.5% | 0.001 | 0.7 | 0.0% | 0.0% | 0 | 10 |

All available forecasts (all): gjr_normal n=2721 QLIKE=-8.4691; gjr_t n=2721 QLIKE=-8.4683; egarch_normal n=2721 QLIKE=-8.4665; egarch_t n=2721 QLIKE=-8.4634; garch_normal n=2721 QLIKE=-8.4380; garch_t n=2721 QLIKE=-8.4371; ewma_094 n=2969 QLIKE=-8.4002; rolling_20 n=2969 QLIKE=-8.3707; rolling_60 n=2969 QLIKE=-8.3289; expanding n=2969 QLIKE=-8.1229

Statistical comparison vs benchmark (all, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| gjr_normal | 2,721 | -0.0312 | -2.12 | 0.034 | 0.046 | 0.215 | 0.322 | yes | no |
| gjr_t | 2,721 | -0.0303 | -2.01 | 0.045 | 0.057 | 0.224 | 0.342 | yes | no |
| egarch_normal | 2,721 | -0.0285 | -1.77 | 0.077 | 0.087 | 0.307 | 0.348 | yes | no |
| egarch_t | 2,721 | -0.0255 | -1.53 | 0.126 | 0.145 | 0.379 | 0.435 | yes | no |
| garch_t | 2,721 | 0.0009 | 0.23 | 0.819 | 0.843 | 1.000 | 1.000 | no | no |
| ewma_094 | 2,721 | 0.0048 | 0.66 | 0.512 | 0.507 | 1.000 | 1.000 | no | no |
| rolling_20 | 2,721 | 0.0363 | 2.88 | 0.004 | 0.001 | 0.036 | 0.009 | no | yes |
| rolling_60 | 2,721 | 0.0795 | 2.75 | 0.006 | 0.020 | 0.048 | 0.160 | no | no |
| expanding | 2,721 | 0.2959 | 2.16 | 0.031 | 0.064 | 0.215 | 0.342 | no | no |

### NIFTY50_TRI — development period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gjr_t | 1,978 | -8.4426 | 27.125 | 1.229 | 0.994 | 0.6% | 0.081 | 5.0 | 0.0% | 0.0% | 0 | 1 |
| gjr_normal | 1,978 | -8.4419 | 27.595 | 1.243 | 0.976 | 2.4% | 0.086 | 4.6 | 0.0% | 0.0% | 0 | 2 |
| egarch_normal | 1,978 | -8.4355 | 27.875 | 1.155 | 1.229 | -18.6% | 0.101 | 3.8 | 0.0% | 0.0% | 0 | 3 |
| egarch_t | 1,978 | -8.4312 | 28.077 | 1.153 | 1.254 | -20.3% | 0.103 | 4.8 | 0.0% | 0.0% | 0 | 4 |
| garch_normal | 1,978 | -8.3979 | 27.389 | 1.229 | 1.060 | -5.6% | 0.065 | 3.7 | 0.0% | 0.0% | 0 | 5 |
| garch_t | 1,978 | -8.3959 | 27.582 | 1.201 | 1.116 | -10.4% | 0.057 | 4.8 | 0.0% | 0.0% | 0 | 6 |
| ewma_094 | 1,978 | -8.3861 | 28.439 | 1.286 | 1.001 | -0.1% | 0.064 | 2.9 | 0.0% | 0.0% | 0 | 7 |
| rolling_20 | 1,978 | -8.3688 | 30.340 | 1.309 | 1.009 | -0.9% | 0.077 | 0.5 | 0.0% | 0.0% | 0 | 8 |
| rolling_60 | 1,978 | -8.3000 | 31.809 | 1.378 | 1.007 | -0.7% | 0.027 | 0.5 | 0.0% | 0.0% | 0 | 9 |
| expanding | 1,978 | -8.0454 | 32.109 | 1.292 | 1.198 | -16.5% | 0.001 | 0.5 | 0.0% | 0.0% | 0 | 10 |

All available forecasts (development): gjr_t n=1978 QLIKE=-8.4426; gjr_normal n=1978 QLIKE=-8.4419; egarch_normal n=1978 QLIKE=-8.4355; egarch_t n=1978 QLIKE=-8.4312; garch_normal n=1978 QLIKE=-8.3979; garch_t n=1978 QLIKE=-8.3959; ewma_094 n=2226 QLIKE=-8.3474; rolling_20 n=2226 QLIKE=-8.3312; rolling_60 n=2226 QLIKE=-8.2671; expanding n=2226 QLIKE=-8.0306

Statistical comparison vs benchmark (development, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| gjr_t | 1,978 | -0.0447 | -2.85 | 0.004 | 0.011 | 0.039 | 0.099 | yes | no |
| gjr_normal | 1,978 | -0.0440 | -2.65 | 0.008 | 0.018 | 0.057 | 0.144 | yes | no |
| egarch_normal | 1,978 | -0.0376 | -1.97 | 0.049 | 0.065 | 0.255 | 0.325 | yes | no |
| egarch_t | 1,978 | -0.0333 | -1.67 | 0.095 | 0.110 | 0.284 | 0.392 | yes | no |
| garch_t | 1,978 | 0.0020 | 0.41 | 0.685 | 0.746 | 0.685 | 0.746 | no | no |
| ewma_094 | 1,978 | 0.0118 | 1.30 | 0.193 | 0.216 | 0.386 | 0.432 | no | no |
| rolling_20 | 1,978 | 0.0291 | 2.03 | 0.042 | 0.019 | 0.255 | 0.144 | no | no |
| rolling_60 | 1,978 | 0.0979 | 2.84 | 0.005 | 0.033 | 0.039 | 0.198 | no | no |
| expanding | 1,978 | 0.3525 | 1.95 | 0.051 | 0.098 | 0.255 | 0.392 | no | no |

### NIFTY50_TRI — validation period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ewma_094 | 743 | -8.5585 | 4.031 | 0.852 | 0.989 | 1.1% | 0.062 | 2.0 | 0.0% | 0.0% | 0 | 1 |
| egarch_t | 743 | -8.5492 | 3.982 | 0.875 | 0.871 | 14.8% | 0.110 | 1.5 | 0.0% | 0.0% | 0 | 2 |
| egarch_normal | 743 | -8.5490 | 3.995 | 0.875 | 0.874 | 14.5% | 0.113 | 0.9 | 0.0% | 0.0% | 0 | 3 |
| garch_t | 743 | -8.5467 | 4.040 | 0.881 | 0.914 | 9.4% | 0.073 | 1.4 | 0.0% | 0.0% | 0 | 4 |
| garch_normal | 743 | -8.5446 | 4.084 | 0.891 | 0.895 | 11.7% | 0.094 | 0.9 | 0.0% | 0.0% | 0 | 5 |
| gjr_normal | 743 | -8.5416 | 4.083 | 0.887 | 0.866 | 15.5% | 0.104 | 1.1 | 0.0% | 0.0% | 0 | 6 |
| gjr_t | 743 | -8.5366 | 4.060 | 0.882 | 0.875 | 14.3% | 0.095 | 1.8 | 0.0% | 0.0% | 0 | 7 |
| rolling_60 | 743 | -8.5141 | 4.075 | 0.863 | 0.977 | 2.4% | 0.025 | 0.2 | 0.0% | 0.0% | 0 | 8 |
| rolling_20 | 743 | -8.4891 | 4.222 | 0.882 | 0.993 | 0.7% | 0.082 | 0.2 | 0.0% | 0.0% | 0 | 9 |
| expanding | 743 | -8.3994 | 4.239 | 1.070 | 0.698 | 43.3% | 0.000 | 0.2 | 0.0% | 0.0% | 0 | 10 |

All available forecasts (validation): ewma_094 n=743 QLIKE=-8.5585; egarch_t n=743 QLIKE=-8.5492; egarch_normal n=743 QLIKE=-8.5490; garch_t n=743 QLIKE=-8.5467; garch_normal n=743 QLIKE=-8.5446; gjr_normal n=743 QLIKE=-8.5416; gjr_t n=743 QLIKE=-8.5366; rolling_60 n=743 QLIKE=-8.5141; rolling_20 n=743 QLIKE=-8.4891; expanding n=743 QLIKE=-8.3994

Statistical comparison vs benchmark (validation, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| ewma_094 | 743 | -0.0138 | -1.20 | 0.231 | 0.207 | 1.000 | 1.000 | yes | no |
| egarch_t | 743 | -0.0046 | -0.15 | 0.878 | 0.851 | 1.000 | 1.000 | yes | no |
| egarch_normal | 743 | -0.0044 | -0.15 | 0.883 | 0.855 | 1.000 | 1.000 | yes | no |
| garch_t | 743 | -0.0021 | -0.51 | 0.609 | 0.576 | 1.000 | 1.000 | yes | no |
| gjr_normal | 743 | 0.0031 | 0.11 | 0.916 | 0.911 | 1.000 | 1.000 | no | no |
| gjr_t | 743 | 0.0080 | 0.23 | 0.821 | 0.798 | 1.000 | 1.000 | no | no |
| rolling_60 | 743 | 0.0306 | 0.65 | 0.513 | 0.505 | 1.000 | 1.000 | no | no |
| rolling_20 | 743 | 0.0555 | 2.08 | 0.038 | 0.032 | 0.301 | 0.256 | no | no |
| expanding | 743 | 0.1453 | 4.43 | 0.000 | 0.002 | 0.000 | 0.018 | no | yes |

### NIFTY50_TRI — regimes (common dates, evaluated periods)

Ex-ante regimes use the tercile of trailing 60-session variance relative to its own history at the origin (known at forecast time). Retrospective labels (shock sessions, post-shock recovery, named event windows) use information after the origin and are descriptive only.

Observations per regime: ex_ante_volatility_regime:high=812; ex_ante_volatility_regime:low=1189; ex_ante_volatility_regime:medium=720; retrospective:post_shock_recovery=551; retrospective:shock_session=14; retrospective_event:calm_2017=248; retrospective_event:covid_crash_2020=45; retrospective_event:covid_recovery_2020=170; retrospective_event:india_election_jun_2024=10; retrospective_event:q4_2018_selloff=61; retrospective_event:rate_shock_2022=248; retrospective_event:recovery_2023=246; retrospective_event:vol_spike_aug_2024=21; retrospective_event:volmageddon_feb_2018=19.

| Model (QLIKE) | ex_ante_volatility_regime:high | ex_ante_volatility_regime:low | ex_ante_volatility_regime:medium | retrospective:post_shock_recovery | retrospective:shock_session | retrospective_event:calm_2017 | retrospective_event:covid_crash_2020 | retrospective_event:covid_recovery_2020 | retrospective_event:india_election_jun_2024 | retrospective_event:q4_2018_selloff | retrospective_event:rate_shock_2022 | retrospective_event:recovery_2023 | retrospective_event:vol_spike_aug_2024 | retrospective_event:volmageddon_feb_2018 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | -8.0316 | -8.8497 | -8.3242 | -8.0896 | 11.1092 | -9.2500 | -4.8562 | -7.6758 | -0.4675 | -8.1480 | -8.1589 | -9.0611 | -8.3341 | -7.9398 |
| egarch_t | -8.0245 | -8.8484 | -8.3227 | -8.0824 | 11.2473 | -9.2410 | -4.7430 | -7.6617 | -0.5022 | -8.1565 | -8.1622 | -9.0568 | -8.3334 | -7.9646 |
| ewma_094 | -7.9743 | -8.8176 | -8.3158 | -8.0624 | 13.3473 | -9.2571 | -4.6434 | -7.8446 | -1.9568 | -7.9616 | -8.0918 | -9.1527 | -8.3436 | -7.8319 |
| expanding | -7.2720 | -8.6641 | -8.2611 | -7.6139 | 33.2050 | -8.9398 | 7.6079 | -7.8191 | -3.2900 | -7.9501 | -8.0359 | -8.7506 | -8.3898 | -8.3868 |
| garch_normal | -8.0019 | -8.8192 | -8.3002 | -8.0846 | 12.5439 | -9.1939 | -4.6925 | -7.8676 | -2.0528 | -7.9660 | -8.0861 | -9.1050 | -8.2896 | -7.9933 |
| garch_t | -7.9952 | -8.8227 | -8.2986 | -8.0918 | 13.4559 | -9.2026 | -4.4400 | -7.8947 | -2.0095 | -7.9630 | -8.0911 | -9.0999 | -8.3349 | -8.0976 |
| gjr_normal | -8.0528 | -8.8441 | -8.3194 | -8.0878 | 10.0985 | -9.2243 | -5.4211 | -7.7633 | -0.0677 | -8.1091 | -8.1556 | -9.0898 | -8.3726 | -8.0336 |
| gjr_t | -8.0535 | -8.8461 | -8.3121 | -8.0901 | 10.5925 | -9.2218 | -5.3847 | -7.7899 | 0.3925 | -8.1053 | -8.1552 | -9.0936 | -8.3620 | -8.0563 |
| rolling_20 | -7.9476 | -8.7806 | -8.2877 | -8.0256 | 13.2089 | -9.1969 | -4.4679 | -7.8886 | -1.8264 | -7.9130 | -8.0540 | -9.0927 | -7.8906 | -7.3981 |
| rolling_60 | -7.7937 | -8.8159 | -8.2401 | -7.9680 | 21.5116 | -9.2709 | -2.7454 | -7.7295 | 0.9617 | -7.7371 | -8.0710 | -9.1586 | -8.2656 | -7.8657 |

| Model (calibration ratio) | ex_ante_volatility_regime:high | ex_ante_volatility_regime:low | ex_ante_volatility_regime:medium | retrospective:post_shock_recovery | retrospective:shock_session | retrospective_event:calm_2017 | retrospective_event:covid_crash_2020 | retrospective_event:covid_recovery_2020 | retrospective_event:india_election_jun_2024 | retrospective_event:q4_2018_selloff | retrospective_event:rate_shock_2022 | retrospective_event:recovery_2023 | retrospective_event:vol_spike_aug_2024 | retrospective_event:volmageddon_feb_2018 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 1.301 | 0.916 | 1.068 | 1.060 | 16.575 | 0.649 | 2.684 | 1.274 | 3.522 | 1.039 | 0.878 | 0.644 | 1.006 | 0.880 |
| egarch_t | 1.352 | 0.910 | 1.061 | 1.109 | 17.497 | 0.631 | 3.002 | 1.374 | 3.477 | 1.059 | 0.885 | 0.636 | 1.013 | 0.898 |
| ewma_094 | 0.875 | 1.204 | 1.196 | 0.668 | 16.615 | 0.918 | 1.334 | 0.579 | 2.313 | 1.046 | 0.978 | 0.991 | 0.932 | 1.368 |
| expanding | 1.816 | 0.553 | 0.934 | 1.655 | 41.652 | 0.369 | 16.234 | 1.221 | 5.792 | 1.445 | 1.018 | 0.343 | 0.742 | 0.985 |
| garch_normal | 1.014 | 0.948 | 1.129 | 0.777 | 14.905 | 0.617 | 1.409 | 0.960 | 2.388 | 1.091 | 0.929 | 0.700 | 0.933 | 1.669 |
| garch_t | 1.098 | 0.944 | 1.142 | 0.851 | 17.548 | 0.632 | 1.685 | 1.012 | 2.633 | 1.156 | 0.976 | 0.680 | 0.962 | 1.428 |
| gjr_normal | 0.917 | 0.922 | 1.081 | 0.691 | 9.114 | 0.620 | 1.053 | 1.010 | 2.088 | 1.005 | 0.913 | 0.682 | 0.874 | 0.847 |
| gjr_t | 0.940 | 0.929 | 1.086 | 0.711 | 9.731 | 0.619 | 1.107 | 1.039 | 2.176 | 1.035 | 0.934 | 0.686 | 0.866 | 0.897 |
| rolling_20 | 0.878 | 1.248 | 1.185 | 0.649 | 17.543 | 0.971 | 1.113 | 0.827 | 2.189 | 1.016 | 0.994 | 1.017 | 0.957 | 1.212 |
| rolling_60 | 0.866 | 1.248 | 1.208 | 0.688 | 32.274 | 0.856 | 2.424 | 0.372 | 5.169 | 1.150 | 0.937 | 1.011 | 0.552 | 1.811 |

### NIFTY50_TRI — estimation stability (GARCH family)

| Model | Fits | Failed | Non-converged | Boundary flags | Persistence mean | Persistence sd | Persistence min | Persistence max | Max refit jump |
|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 152 | 0 | 0 | 0 | 0.9444 | 0.0511 | 0.7934 | 0.9908 | 0.0708 |
| egarch_t | 152 | 0 | 0 | 0 | 0.9505 | 0.0362 | 0.8430 | 0.9898 | 0.0515 |
| garch_normal | 152 | 0 | 0 | 0 | 0.9690 | 0.0331 | 0.8047 | 0.9974 | 0.1486 |
| garch_t | 152 | 0 | 0 | 0 | 0.9687 | 0.0276 | 0.8386 | 0.9899 | 0.1036 |
| gjr_normal | 152 | 0 | 0 | 109 | 0.9547 | 0.0339 | 0.8303 | 0.9924 | 0.0567 |
| gjr_t | 152 | 0 | 0 | 109 | 0.9528 | 0.0379 | 0.8285 | 0.9926 | 0.0484 |

## SPY

### SPY — all period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_t | 2,769 | -8.5660 | 15.131 | 1.148 | 1.056 | -5.3% | 0.208 | 6.2 | 0.0% | 0.0% | 0 | 1 |
| egarch_normal | 2,769 | -8.5562 | 15.679 | 1.141 | 1.116 | -10.4% | 0.207 | 4.0 | 0.0% | 0.0% | 0 | 2 |
| gjr_t | 2,769 | -8.5547 | 16.046 | 1.231 | 0.885 | 13.0% | 0.183 | 7.5 | 0.0% | 0.0% | 0 | 3 |
| gjr_normal | 2,769 | -8.5514 | 15.385 | 1.205 | 0.934 | 7.0% | 0.179 | 4.7 | 0.0% | 0.0% | 0 | 4 |
| garch_t | 2,769 | -8.5181 | 14.847 | 1.220 | 0.961 | 4.1% | 0.150 | 5.9 | 0.0% | 0.0% | 0 | 5 |
| garch_normal | 2,769 | -8.5156 | 14.552 | 1.186 | 1.035 | -3.4% | 0.156 | 3.3 | 0.0% | 0.0% | 0 | 6 |
| ewma_094 | 2,769 | -8.4537 | 17.535 | 1.260 | 1.002 | -0.2% | 0.066 | 5.1 | 0.0% | 0.0% | 0 | 7 |
| rolling_20 | 2,769 | -8.3686 | 18.950 | 1.274 | 0.994 | 0.6% | 0.084 | 0.8 | 0.0% | 0.0% | 0 | 8 |
| rolling_60 | 2,769 | -8.3459 | 21.267 | 1.383 | 0.999 | 0.1% | 0.028 | 0.7 | 0.0% | 0.0% | 0 | 9 |
| expanding | 2,769 | -8.0064 | 21.833 | 1.256 | 1.429 | -30.0% | 0.001 | 0.7 | 0.0% | 0.0% | 0 | 10 |

All available forecasts (all): egarch_t n=2769 QLIKE=-8.5660; egarch_normal n=2769 QLIKE=-8.5562; gjr_t n=2769 QLIKE=-8.5547; gjr_normal n=2769 QLIKE=-8.5514; garch_t n=2769 QLIKE=-8.5181; garch_normal n=2769 QLIKE=-8.5156; ewma_094 n=3017 QLIKE=-8.4921; rolling_20 n=3017 QLIKE=-8.4053; rolling_60 n=3017 QLIKE=-8.3911; expanding n=3017 QLIKE=-8.0817

Statistical comparison vs benchmark (all, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| egarch_t | 2,769 | -0.0504 | -2.26 | 0.024 | 0.020 | 0.121 | 0.120 | yes | no |
| egarch_normal | 2,769 | -0.0406 | -1.77 | 0.076 | 0.076 | 0.247 | 0.256 | yes | no |
| gjr_t | 2,769 | -0.0391 | -1.82 | 0.070 | 0.064 | 0.247 | 0.256 | yes | no |
| gjr_normal | 2,769 | -0.0358 | -1.87 | 0.062 | 0.065 | 0.247 | 0.256 | yes | no |
| garch_t | 2,769 | -0.0025 | -0.74 | 0.460 | 0.470 | 0.460 | 0.470 | yes | no |
| ewma_094 | 2,769 | 0.0619 | 2.87 | 0.004 | 0.003 | 0.029 | 0.024 | no | yes |
| rolling_20 | 2,769 | 0.1470 | 4.03 | 0.000 | 0.000 | 0.001 | 0.000 | no | yes |
| rolling_60 | 2,769 | 0.1697 | 3.62 | 0.000 | 0.006 | 0.002 | 0.042 | no | yes |
| expanding | 2,769 | 0.5092 | 2.56 | 0.011 | 0.035 | 0.063 | 0.175 | no | no |

### SPY — development period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_t | 2,016 | -8.6931 | 18.783 | 1.092 | 1.141 | -12.4% | 0.225 | 4.6 | 0.0% | 0.0% | 0 | 1 |
| gjr_t | 2,016 | -8.6844 | 19.880 | 1.190 | 0.890 | 12.3% | 0.194 | 5.4 | 0.0% | 0.0% | 0 | 2 |
| gjr_normal | 2,016 | -8.6836 | 19.011 | 1.157 | 0.948 | 5.5% | 0.188 | 3.5 | 0.0% | 0.0% | 0 | 3 |
| egarch_normal | 2,016 | -8.6821 | 19.536 | 1.084 | 1.210 | -17.4% | 0.225 | 2.9 | 0.0% | 0.0% | 0 | 4 |
| garch_t | 2,016 | -8.6457 | 18.384 | 1.178 | 0.978 | 2.2% | 0.152 | 4.4 | 0.0% | 0.0% | 0 | 5 |
| garch_normal | 2,016 | -8.6438 | 17.980 | 1.135 | 1.076 | -7.1% | 0.159 | 2.4 | 0.0% | 0.0% | 0 | 6 |
| ewma_094 | 2,016 | -8.5507 | 22.205 | 1.261 | 1.004 | -0.4% | 0.067 | 2.9 | 0.0% | 0.0% | 0 | 7 |
| rolling_20 | 2,016 | -8.4575 | 24.118 | 1.277 | 0.994 | 0.6% | 0.087 | 0.6 | 0.0% | 0.0% | 0 | 8 |
| rolling_60 | 2,016 | -8.4140 | 27.292 | 1.424 | 1.003 | -0.3% | 0.030 | 0.5 | 0.0% | 0.0% | 0 | 9 |
| expanding | 2,016 | -8.0073 | 27.897 | 1.240 | 1.623 | -38.4% | 0.001 | 0.5 | 0.0% | 0.0% | 0 | 10 |

All available forecasts (development): egarch_t n=2016 QLIKE=-8.6931; gjr_t n=2016 QLIKE=-8.6844; gjr_normal n=2016 QLIKE=-8.6836; egarch_normal n=2016 QLIKE=-8.6821; garch_t n=2016 QLIKE=-8.6457; garch_normal n=2016 QLIKE=-8.6438; ewma_094 n=2264 QLIKE=-8.5912; rolling_20 n=2264 QLIKE=-8.4967; rolling_60 n=2264 QLIKE=-8.4667; expanding n=2264 QLIKE=-8.1077

Statistical comparison vs benchmark (development, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| egarch_t | 2,016 | -0.0493 | -1.66 | 0.096 | 0.098 | 0.482 | 0.490 | yes | no |
| gjr_t | 2,016 | -0.0405 | -1.41 | 0.159 | 0.148 | 0.485 | 0.490 | yes | no |
| gjr_normal | 2,016 | -0.0398 | -1.55 | 0.121 | 0.111 | 0.485 | 0.490 | yes | no |
| egarch_normal | 2,016 | -0.0383 | -1.25 | 0.213 | 0.202 | 0.485 | 0.490 | yes | no |
| garch_t | 2,016 | -0.0019 | -0.41 | 0.682 | 0.661 | 0.682 | 0.661 | yes | no |
| ewma_094 | 2,016 | 0.0931 | 3.23 | 0.001 | 0.002 | 0.009 | 0.016 | no | yes |
| rolling_20 | 2,016 | 0.1863 | 3.98 | 0.000 | 0.000 | 0.001 | 0.000 | no | yes |
| rolling_60 | 2,016 | 0.2298 | 3.72 | 0.000 | 0.003 | 0.002 | 0.021 | no | yes |
| expanding | 2,016 | 0.6365 | 2.43 | 0.015 | 0.063 | 0.090 | 0.378 | no | no |

### SPY — validation period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_t | 753 | -8.2256 | 5.354 | 1.297 | 0.888 | 12.6% | 0.161 | 1.6 | 0.0% | 0.0% | 0 | 1 |
| egarch_normal | 753 | -8.2191 | 5.354 | 1.295 | 0.932 | 7.3% | 0.159 | 1.0 | 0.0% | 0.0% | 0 | 2 |
| gjr_t | 753 | -8.2075 | 5.783 | 1.339 | 0.871 | 14.8% | 0.154 | 2.1 | 0.0% | 0.0% | 0 | 3 |
| gjr_normal | 753 | -8.1974 | 5.676 | 1.335 | 0.901 | 11.0% | 0.155 | 1.3 | 0.0% | 0.0% | 0 | 4 |
| ewma_094 | 753 | -8.1941 | 5.033 | 1.255 | 0.998 | 0.2% | 0.062 | 2.2 | 0.0% | 0.0% | 0 | 5 |
| garch_t | 753 | -8.1766 | 5.377 | 1.332 | 0.918 | 8.9% | 0.144 | 1.5 | 0.0% | 0.0% | 0 | 6 |
| garch_normal | 753 | -8.1723 | 5.374 | 1.324 | 0.944 | 5.9% | 0.149 | 1.0 | 0.0% | 0.0% | 0 | 7 |
| rolling_60 | 753 | -8.1637 | 5.139 | 1.274 | 0.989 | 1.2% | 0.024 | 0.2 | 0.0% | 0.0% | 0 | 8 |
| rolling_20 | 753 | -8.1304 | 5.113 | 1.267 | 0.994 | 0.6% | 0.076 | 0.2 | 0.0% | 0.0% | 0 | 9 |
| expanding | 753 | -8.0038 | 5.598 | 1.299 | 1.095 | -8.7% | 0.000 | 0.2 | 0.0% | 0.0% | 0 | 10 |

All available forecasts (validation): egarch_t n=753 QLIKE=-8.2256; egarch_normal n=753 QLIKE=-8.2191; gjr_t n=753 QLIKE=-8.2075; gjr_normal n=753 QLIKE=-8.1974; ewma_094 n=753 QLIKE=-8.1941; garch_t n=753 QLIKE=-8.1766; garch_normal n=753 QLIKE=-8.1723; rolling_60 n=753 QLIKE=-8.1637; rolling_20 n=753 QLIKE=-8.1304; expanding n=753 QLIKE=-8.0038

Statistical comparison vs benchmark (validation, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| egarch_t | 753 | -0.0533 | -2.77 | 0.006 | 0.005 | 0.040 | 0.040 | yes | yes |
| egarch_normal | 753 | -0.0468 | -3.12 | 0.002 | 0.002 | 0.015 | 0.018 | yes | yes |
| gjr_t | 753 | -0.0352 | -2.35 | 0.019 | 0.024 | 0.116 | 0.144 | yes | no |
| gjr_normal | 753 | -0.0251 | -2.13 | 0.033 | 0.047 | 0.166 | 0.200 | yes | no |
| ewma_094 | 753 | -0.0218 | -1.55 | 0.120 | 0.129 | 0.361 | 0.387 | yes | no |
| garch_t | 753 | -0.0042 | -1.81 | 0.070 | 0.040 | 0.280 | 0.200 | yes | no |
| rolling_60 | 753 | 0.0086 | 0.32 | 0.750 | 0.791 | 0.751 | 0.791 | no | no |
| rolling_20 | 753 | 0.0419 | 0.89 | 0.375 | 0.359 | 0.751 | 0.718 | no | no |
| expanding | 753 | 0.1685 | 3.55 | 0.000 | 0.005 | 0.004 | 0.040 | no | yes |

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
| rolling_20 | -7.8941 | -8.8828 | -8.5946 | -8.1183 | 12.2903 | -9.6101 | -4.6913 | -7.7451 | -9.5656 | -6.5097 | -7.3137 | -8.5915 | -7.6559 | -5.2091 |
| rolling_60 | -7.7529 | -8.9796 | -8.6409 | -8.0724 | 16.3110 | -9.8352 | -2.4131 | -7.6520 | -9.4633 | -6.2336 | -7.3180 | -8.5968 | -7.2043 | -2.7215 |

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
| rolling_20 | 0.935 | 1.472 | 1.075 | 0.720 | 10.321 | 0.986 | 1.042 | 0.854 | 0.761 | 1.383 | 0.998 | 0.946 | 0.859 | 1.366 |
| rolling_60 | 0.942 | 1.411 | 1.092 | 0.800 | 23.584 | 0.940 | 1.924 | 0.374 | 0.482 | 2.200 | 1.046 | 0.792 | 1.835 | 3.535 |

### SPY — estimation stability (GARCH family)

| Model | Fits | Failed | Non-converged | Boundary flags | Persistence mean | Persistence sd | Persistence min | Persistence max | Max refit jump |
|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 154 | 0 | 0 | 0 | 0.9342 | 0.0237 | 0.8979 | 0.9897 | 0.0338 |
| egarch_t | 154 | 0 | 0 | 0 | 0.9417 | 0.0254 | 0.8952 | 0.9840 | 0.0151 |
| garch_normal | 154 | 0 | 0 | 0 | 0.9424 | 0.0417 | 0.8522 | 0.9937 | 0.0258 |
| garch_t | 154 | 0 | 0 | 21 | 0.9621 | 0.0437 | 0.8437 | 1.0000 | 0.0214 |
| gjr_normal | 154 | 0 | 0 | 95 | 0.9623 | 0.0262 | 0.9137 | 1.0000 | 0.0287 |
| gjr_t | 154 | 0 | 0 | 110 | 0.9773 | 0.0208 | 0.9181 | 1.0000 | 0.0124 |

## VT

### VT — all period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 2,769 | -8.5627 | 16.850 | 1.085 | 1.083 | -7.7% | 0.160 | 4.1 | 0.0% | 0.0% | 0 | 1 |
| gjr_normal | 2,769 | -8.5563 | 18.040 | 1.172 | 0.909 | 10.0% | 0.163 | 4.4 | 0.0% | 0.0% | 0 | 2 |
| gjr_t | 2,769 | -8.5555 | 17.410 | 1.150 | 0.932 | 7.3% | 0.153 | 5.7 | 0.0% | 0.0% | 0 | 3 |
| garch_t | 2,769 | -8.5305 | 16.778 | 1.146 | 0.996 | 0.4% | 0.135 | 5.6 | 0.0% | 0.0% | 0 | 4 |
| garch_normal | 2,769 | -8.5297 | 16.463 | 1.140 | 1.001 | -0.1% | 0.144 | 3.6 | 0.0% | 0.0% | 0 | 5 |
| ewma_094 | 2,769 | -8.4870 | 19.856 | 1.206 | 1.002 | -0.2% | 0.064 | 5.0 | 0.0% | 0.0% | 0 | 6 |
| egarch_t | 2,769 | -8.4465 | 17.573 | 1.085 | 1.100 | -9.1% | 0.169 | 6.0 | 1.2% | 1.2% | 0 | 7 |
| rolling_20 | 2,769 | -8.4219 | 21.743 | 1.226 | 0.996 | 0.4% | 0.081 | 0.8 | 0.0% | 0.0% | 0 | 8 |
| rolling_60 | 2,769 | -8.3849 | 23.418 | 1.311 | 0.998 | 0.2% | 0.027 | 0.7 | 0.0% | 0.0% | 0 | 9 |
| expanding | 2,769 | -8.0793 | 23.820 | 1.223 | 1.276 | -21.6% | 0.001 | 0.7 | 0.0% | 0.0% | 0 | 10 |

All available forecasts (all): egarch_normal n=2769 QLIKE=-8.5627; gjr_normal n=2769 QLIKE=-8.5563; gjr_t n=2769 QLIKE=-8.5555; garch_t n=2769 QLIKE=-8.5305; garch_normal n=2769 QLIKE=-8.5297; ewma_094 n=3017 QLIKE=-8.5080; egarch_t n=2769 QLIKE=-8.4465; rolling_20 n=3017 QLIKE=-8.4455; rolling_60 n=3017 QLIKE=-8.4133; expanding n=3017 QLIKE=-8.1307

Statistical comparison vs benchmark (all, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 2,769 | -0.0330 | -1.70 | 0.090 | 0.079 | 0.359 | 0.345 | yes | no |
| gjr_normal | 2,769 | -0.0266 | -1.86 | 0.063 | 0.069 | 0.316 | 0.345 | yes | no |
| gjr_t | 2,769 | -0.0259 | -1.47 | 0.140 | 0.149 | 0.421 | 0.447 | yes | no |
| garch_t | 2,769 | -0.0008 | -0.48 | 0.633 | 0.674 | 0.843 | 1.000 | yes | no |
| ewma_094 | 2,769 | 0.0426 | 2.53 | 0.011 | 0.016 | 0.080 | 0.112 | no | no |
| egarch_t | 2,769 | 0.0831 | 0.80 | 0.422 | 0.538 | 0.843 | 1.000 | no | no |
| rolling_20 | 2,769 | 0.1078 | 4.09 | 0.000 | 0.000 | 0.000 | 0.000 | no | yes |
| rolling_60 | 2,769 | 0.1447 | 3.22 | 0.001 | 0.007 | 0.011 | 0.056 | no | no |
| expanding | 2,769 | 0.4504 | 2.28 | 0.023 | 0.051 | 0.137 | 0.306 | no | no |

### VT — development period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 2,016 | -8.6598 | 21.593 | 1.063 | 1.148 | -12.9% | 0.168 | 3.0 | 0.0% | 0.0% | 0 | 1 |
| gjr_normal | 2,016 | -8.6548 | 23.153 | 1.170 | 0.908 | 10.2% | 0.170 | 3.4 | 0.0% | 0.0% | 0 | 2 |
| gjr_t | 2,016 | -8.6508 | 22.302 | 1.144 | 0.939 | 6.5% | 0.159 | 4.5 | 0.0% | 0.0% | 0 | 3 |
| garch_t | 2,016 | -8.6261 | 21.465 | 1.131 | 1.022 | -2.2% | 0.137 | 4.2 | 0.0% | 0.0% | 0 | 4 |
| garch_normal | 2,016 | -8.6258 | 21.034 | 1.126 | 1.021 | -2.1% | 0.149 | 2.6 | 0.0% | 0.0% | 0 | 5 |
| ewma_094 | 2,016 | -8.5622 | 25.762 | 1.237 | 1.003 | -0.3% | 0.065 | 3.0 | 0.0% | 0.0% | 0 | 6 |
| egarch_t | 2,016 | -8.4982 | 22.595 | 1.064 | 1.190 | -15.9% | 0.180 | 4.6 | 0.0% | 0.0% | 0 | 7 |
| rolling_20 | 2,016 | -8.4935 | 28.322 | 1.263 | 0.995 | 0.5% | 0.084 | 0.6 | 0.0% | 0.0% | 0 | 8 |
| rolling_60 | 2,016 | -8.4320 | 30.624 | 1.375 | 1.002 | -0.2% | 0.028 | 0.5 | 0.0% | 0.0% | 0 | 9 |
| expanding | 2,016 | -8.0616 | 31.062 | 1.236 | 1.425 | -29.8% | 0.001 | 0.5 | 0.0% | 0.0% | 0 | 10 |

All available forecasts (development): egarch_normal n=2016 QLIKE=-8.6598; gjr_normal n=2016 QLIKE=-8.6548; gjr_t n=2016 QLIKE=-8.6508; garch_t n=2016 QLIKE=-8.6261; garch_normal n=2016 QLIKE=-8.6258; ewma_094 n=2264 QLIKE=-8.5819; rolling_20 n=2264 QLIKE=-8.5170; egarch_t n=2016 QLIKE=-8.4982; rolling_60 n=2264 QLIKE=-8.4647; expanding n=2264 QLIKE=-8.1321

Statistical comparison vs benchmark (development, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 2,016 | -0.0339 | -1.30 | 0.193 | 0.175 | 0.770 | 0.700 | yes | no |
| gjr_normal | 2,016 | -0.0290 | -1.53 | 0.127 | 0.122 | 0.633 | 0.610 | yes | no |
| gjr_t | 2,016 | -0.0250 | -1.07 | 0.283 | 0.265 | 0.849 | 0.795 | yes | no |
| garch_t | 2,016 | -0.0002 | -0.11 | 0.913 | 0.931 | 0.913 | 1.000 | yes | no |
| ewma_094 | 2,016 | 0.0637 | 2.87 | 0.004 | 0.008 | 0.029 | 0.056 | no | no |
| egarch_t | 2,016 | 0.1277 | 0.91 | 0.361 | 0.522 | 0.849 | 1.000 | no | no |
| rolling_20 | 2,016 | 0.1324 | 4.16 | 0.000 | 0.000 | 0.000 | 0.000 | no | yes |
| rolling_60 | 2,016 | 0.1938 | 3.26 | 0.001 | 0.007 | 0.009 | 0.056 | no | no |
| expanding | 2,016 | 0.5643 | 2.16 | 0.031 | 0.074 | 0.186 | 0.444 | no | no |

### VT — validation period, common dates

| Model | Obs | QLIKE | MSE (x1e8) | MAE (x1e4) | Calibration | Rel. bias | Stability | Runtime (s) | Fit fail | Non-conv. | Missing | Rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| egarch_t | 753 | -8.3083 | 4.130 | 1.143 | 0.909 | 10.0% | 0.140 | 1.4 | 0.0% | 0.0% | 0 | 1 |
| egarch_normal | 753 | -8.3027 | 4.152 | 1.146 | 0.936 | 6.8% | 0.141 | 1.1 | 0.0% | 0.0% | 0 | 2 |
| gjr_t | 753 | -8.3004 | 4.312 | 1.166 | 0.912 | 9.6% | 0.138 | 1.2 | 0.0% | 0.0% | 0 | 3 |
| gjr_normal | 753 | -8.2924 | 4.351 | 1.180 | 0.912 | 9.6% | 0.143 | 1.0 | 0.0% | 0.0% | 0 | 4 |
| ewma_094 | 753 | -8.2859 | 4.045 | 1.123 | 0.997 | 0.3% | 0.062 | 2.0 | 0.0% | 0.0% | 0 | 5 |
| garch_t | 753 | -8.2745 | 4.230 | 1.186 | 0.931 | 7.4% | 0.130 | 1.4 | 0.0% | 0.0% | 0 | 6 |
| garch_normal | 753 | -8.2722 | 4.225 | 1.179 | 0.949 | 5.4% | 0.131 | 0.9 | 0.0% | 0.0% | 0 | 7 |
| rolling_60 | 753 | -8.2588 | 4.128 | 1.141 | 0.987 | 1.4% | 0.024 | 0.2 | 0.0% | 0.0% | 0 | 8 |
| rolling_20 | 753 | -8.2302 | 4.130 | 1.127 | 0.996 | 0.4% | 0.074 | 0.2 | 0.0% | 0.0% | 0 | 9 |
| expanding | 753 | -8.1266 | 4.432 | 1.185 | 0.989 | 1.1% | 0.000 | 0.2 | 0.0% | 0.0% | 0 | 10 |

All available forecasts (validation): egarch_t n=753 QLIKE=-8.3083; egarch_normal n=753 QLIKE=-8.3027; gjr_t n=753 QLIKE=-8.3004; gjr_normal n=753 QLIKE=-8.2924; ewma_094 n=753 QLIKE=-8.2859; garch_t n=753 QLIKE=-8.2745; garch_normal n=753 QLIKE=-8.2722; rolling_60 n=753 QLIKE=-8.2588; rolling_20 n=753 QLIKE=-8.2302; expanding n=753 QLIKE=-8.1266

Statistical comparison vs benchmark (validation, QLIKE, HAC Diebold-Mariano and stationary block bootstrap; Holm-adjusted within asset/period):

| Model | Obs | Mean QLIKE diff | DM t | DM p | Bootstrap p | DM p (Holm) | Bootstrap p (Holm) | Better | Significant (5%, Holm) |
|---|---|---|---|---|---|---|---|---|---|
| egarch_t | 753 | -0.0361 | -2.06 | 0.040 | 0.024 | 0.311 | 0.192 | yes | no |
| egarch_normal | 753 | -0.0305 | -2.01 | 0.045 | 0.030 | 0.311 | 0.210 | yes | no |
| gjr_t | 753 | -0.0282 | -2.07 | 0.039 | 0.031 | 0.311 | 0.210 | yes | no |
| gjr_normal | 753 | -0.0203 | -1.65 | 0.099 | 0.114 | 0.496 | 0.570 | yes | no |
| ewma_094 | 753 | -0.0137 | -0.91 | 0.365 | 0.305 | 1.000 | 0.915 | yes | no |
| garch_t | 753 | -0.0023 | -1.20 | 0.231 | 0.166 | 0.925 | 0.664 | yes | no |
| rolling_60 | 753 | 0.0134 | 0.56 | 0.576 | 0.636 | 1.000 | 0.915 | no | no |
| rolling_20 | 753 | 0.0419 | 0.93 | 0.353 | 0.323 | 1.000 | 0.915 | no | no |
| expanding | 753 | 0.1456 | 3.60 | 0.000 | 0.000 | 0.003 | 0.000 | no | yes |

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
| rolling_20 | -7.8867 | -8.9516 | -8.4789 | -7.9600 | 11.9878 | -9.6831 | -4.6726 | -7.8852 | -9.4953 | -7.1523 | -7.4394 | -8.6118 | -7.6633 | -5.5942 |
| rolling_60 | -7.7529 | -8.9882 | -8.4846 | -7.8319 | 17.7958 | -9.8070 | -2.4187 | -7.7644 | -9.4271 | -7.0187 | -7.4406 | -8.6312 | -7.1934 | -3.5678 |

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
| rolling_20 | 0.928 | 1.331 | 1.076 | 0.700 | 13.203 | 0.981 | 1.046 | 0.853 | 0.800 | 1.270 | 1.003 | 0.963 | 0.907 | 1.366 |
| rolling_60 | 0.925 | 1.285 | 1.146 | 0.766 | 28.952 | 0.925 | 1.939 | 0.361 | 0.581 | 1.872 | 1.048 | 0.818 | 1.925 | 3.441 |

### VT — estimation stability (GARCH family)

| Model | Fits | Failed | Non-converged | Boundary flags | Persistence mean | Persistence sd | Persistence min | Persistence max | Max refit jump |
|---|---|---|---|---|---|---|---|---|---|
| egarch_normal | 154 | 0 | 0 | 0 | 0.9533 | 0.0169 | 0.9257 | 0.9924 | 0.0271 |
| egarch_t | 160 | 2 | 4 | 3 | 0.9514 | 0.0780 | 0.0000 | 0.9890 | 0.9866 |
| garch_normal | 154 | 0 | 0 | 0 | 0.9578 | 0.0253 | 0.8922 | 0.9926 | 0.0314 |
| garch_t | 154 | 0 | 0 | 0 | 0.9648 | 0.0267 | 0.8844 | 0.9977 | 0.0348 |
| gjr_normal | 154 | 0 | 0 | 75 | 0.9677 | 0.0217 | 0.9160 | 1.0000 | 0.0179 |
| gjr_t | 154 | 0 | 0 | 78 | 0.9688 | 0.0183 | 0.9170 | 0.9971 | 0.0164 |

## Run summaries

| Asset | Model | Origins | Valid | Missing | Invalid flags | Fits | Failed fits | Flagged fits | Non-converged | Runtime (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| NIFTY50_TRI | expanding | 3,425 | 3,425 | 0 | n/a | 3,425 | 0 | 0 | 0 | 1.3 |
| NIFTY50_TRI | rolling_20 | 3,425 | 3,425 | 0 | n/a | 3,425 | 0 | 0 | 0 | 1.2 |
| NIFTY50_TRI | rolling_60 | 3,425 | 3,425 | 0 | n/a | 3,425 | 0 | 0 | 0 | 1.3 |
| NIFTY50_TRI | ewma_094 | 3,425 | 3,425 | 0 | n/a | 3,425 | 0 | 0 | 0 | 7.2 |
| NIFTY50_TRI | garch_normal | 3,177 | 3,177 | 0 | n/a | 152 | 0 | 0 | 0 | 5.5 |
| NIFTY50_TRI | garch_t | 3,177 | 3,177 | 0 | n/a | 152 | 0 | 0 | 0 | 7.6 |
| NIFTY50_TRI | egarch_normal | 3,177 | 3,177 | 0 | n/a | 152 | 0 | 0 | 0 | 5.8 |
| NIFTY50_TRI | egarch_t | 3,177 | 3,177 | 0 | n/a | 152 | 0 | 0 | 0 | 7.7 |
| NIFTY50_TRI | gjr_normal | 3,177 | 3,177 | 0 | n/a | 152 | 0 | 109 | 0 | 6.9 |
| NIFTY50_TRI | gjr_t | 3,177 | 3,177 | 0 | n/a | 152 | 0 | 109 | 0 | 8.3 |
| SPY | expanding | 3,478 | 3,478 | 0 | n/a | 3,478 | 0 | 0 | 0 | 1.5 |
| SPY | rolling_20 | 3,478 | 3,478 | 0 | n/a | 3,478 | 0 | 0 | 0 | 1.6 |
| SPY | rolling_60 | 3,478 | 3,478 | 0 | n/a | 3,478 | 0 | 0 | 0 | 1.3 |
| SPY | ewma_094 | 3,478 | 3,478 | 0 | n/a | 3,478 | 0 | 0 | 0 | 7.3 |
| SPY | garch_normal | 3,230 | 3,230 | 0 | n/a | 154 | 0 | 0 | 0 | 4.3 |
| SPY | garch_t | 3,230 | 3,230 | 0 | n/a | 154 | 0 | 21 | 0 | 7.0 |
| SPY | egarch_normal | 3,230 | 3,230 | 0 | n/a | 154 | 0 | 0 | 0 | 5.1 |
| SPY | egarch_t | 3,230 | 3,230 | 0 | n/a | 154 | 0 | 0 | 0 | 7.7 |
| SPY | gjr_normal | 3,230 | 3,230 | 0 | n/a | 154 | 0 | 95 | 0 | 5.9 |
| SPY | gjr_t | 3,230 | 3,230 | 0 | n/a | 154 | 0 | 110 | 0 | 9.2 |
| VT | expanding | 3,478 | 3,478 | 0 | n/a | 3,478 | 0 | 0 | 0 | 1.4 |
| VT | rolling_20 | 3,478 | 3,478 | 0 | n/a | 3,478 | 0 | 0 | 0 | 1.4 |
| VT | rolling_60 | 3,478 | 3,478 | 0 | n/a | 3,478 | 0 | 0 | 0 | 1.3 |
| VT | ewma_094 | 3,478 | 3,478 | 0 | n/a | 3,478 | 0 | 0 | 0 | 7.3 |
| VT | garch_normal | 3,230 | 3,230 | 0 | n/a | 154 | 0 | 0 | 0 | 4.6 |
| VT | garch_t | 3,230 | 3,230 | 0 | n/a | 154 | 0 | 0 | 0 | 7.1 |
| VT | egarch_normal | 3,230 | 3,230 | 0 | n/a | 154 | 0 | 0 | 0 | 5.5 |
| VT | egarch_t | 3,230 | 3,224 | 6 | variance_above_bound=4, no_usable_state=2 | 160 | 2 | 5 | 2 | 11.5 |
| VT | gjr_normal | 3,230 | 3,230 | 0 | n/a | 154 | 0 | 75 | 0 | 5.3 |
| VT | gjr_t | 3,230 | 3,230 | 0 | n/a | 154 | 0 | 78 | 0 | 7.0 |

Metric definitions: QLIKE = log(h) + r²/h (lower is better, computed only for strictly positive finite h); MSE/MAE on variance units; calibration = mean r² / mean h; relative bias = mean h / mean r² - 1; stability = mean |Δ log h| between consecutive origins; runtime = total fit+update+forecast seconds. Rank is by QLIKE within asset/period/sample. Small differences are not treated as meaningful without the statistical tests above.
