# VIX model diagnostics

**PROVISIONAL / EXPLORATORY.** Model specifications were motivated by the already inspected 2024 results. Every 2024 improvement, interval and p-value below is exploratory, not independent confirmation. Only saved Stage 4 panels through 2024-12-31 were read numerically; no 2025–2026 data was loaded. NIFTY is user-confirmed NSE spot; vendor/export, original timezone and bar labels remain unverified.

## Exact reproduction

| target | model | n | qlike | exact_forecast_and_coefficient_reproduction |
| --- | --- | --- | --- | --- |
| intraday | har | 226 | -8.91741 | True |
| intraday | log_har | 226 | -8.93276 | True |
| intraday | har_vix | 226 | 125284 | True |
| intraday | rv_ewma | 226 | -8.83928 | True |
| intraday_overnight | har | 226 | -8.51075 | True |
| intraday_overnight | log_har | 226 | -8.54731 | True |
| intraday_overnight | har_vix | 226 | 118806 | True |
| intraday_overnight | rv_ewma | 226 | -8.4938 | True |

Forecast dates, coefficients, raw/final predictions, floor flags and training endpoints reproduced exactly. Original run artifacts and published Stage 4 reports were hash-checked and are not overwritten. A snapshot of the original Stage 4 source is preserved under experiments/stage4b/stage4_code_snapshot.

## Mechanism of negative levels forecasts

On 226 matched primary target dates, 21 raw levels HAR+VIX forecasts are nonpositive. 18 are outside at least one training feature range; 20 are outside the joint training convex hull. Marginal ranges and joint-support extrapolation are distinct checks. Convex-hull feasibility uses standardized predictors and reports solver status; extrapolation is evidence of an unfamiliar predictor combination, not proof of bad data.

| target_date | refit_origin | lagged_vix_percent | log_iv_change | vix_z_score | raw_prediction | marginal_extrapolation | outside_training_convex_hull |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-06-07 00:00:00 | 2024-06-06 00:00:00 | 19.05 | -0.613579 | 2.18359 | -9.27629e-05 | True | True |
| 2024-06-10 00:00:00 | 2024-06-06 00:00:00 | 16.6 | -0.275329 | 1.07633 | -0.000177154 | True | True |
| 2024-06-11 00:00:00 | 2024-06-06 00:00:00 | 16.85 | 0.0298959 | 1.18234 | -0.000173867 | True | True |
| 2024-06-12 00:00:00 | 2024-06-06 00:00:00 | 16.43 | -0.0504834 | 1.00514 | -2.46435e-05 | True | True |
| 2024-06-13 00:00:00 | 2024-06-06 00:00:00 | 14.79 | -0.210315 | 0.356059 | -1.65357e-05 | True | True |
| 2024-06-14 00:00:00 | 2024-06-06 00:00:00 | 14.46 | -0.0451301 | 0.233692 | -1.07796e-05 | True | True |
| 2024-06-18 00:00:00 | 2024-06-06 00:00:00 | 13.35 | -0.15974 | -0.157642 | -2.228e-05 | True | True |
| 2024-06-19 00:00:00 | 2024-06-06 00:00:00 | 12.91 | -0.0670284 | -0.30412 | -2.57349e-05 | False | True |
| 2024-06-20 00:00:00 | 2024-06-06 00:00:00 | 13.04 | 0.0200387 | -0.261353 | -1.25923e-05 | True | True |
| 2024-06-21 00:00:00 | 2024-06-06 00:00:00 | 13.74 | 0.104579 | -0.023706 | -8.48176e-06 | True | True |
| 2024-06-24 00:00:00 | 2024-06-06 00:00:00 | 13.31 | -0.0635913 | -0.171161 | -1.59051e-05 | True | True |
| 2024-06-25 00:00:00 | 2024-06-06 00:00:00 | 13.21 | -0.015083 | -0.204781 | -2.87819e-05 | True | True |
| 2024-06-26 00:00:00 | 2024-06-06 00:00:00 | 13.97 | 0.111876 | 0.0570897 | -1.71667e-05 | True | True |
| 2024-06-27 00:00:00 | 2024-06-06 00:00:00 | 14.27 | 0.0424945 | 0.164491 | -8.46534e-06 | True | True |
| 2024-06-28 00:00:00 | 2024-06-06 00:00:00 | 13.99 | -0.0396333 | 0.0641788 | -1.30303e-06 | True | True |
| 2024-07-01 00:00:00 | 2024-06-06 00:00:00 | 14.02 | 0.00428419 | 0.0748315 | -8.15248e-06 | True | True |
| 2024-07-02 00:00:00 | 2024-06-06 00:00:00 | 13.69 | -0.0476385 | -0.0410928 | -1.88192e-05 | True | True |
| 2024-07-03 00:00:00 | 2024-06-06 00:00:00 | 13.83 | 0.020349 | 0.00774999 | -1.22247e-05 | True | True |
| 2024-07-04 00:00:00 | 2024-06-06 00:00:00 | 13.67 | -0.023273 | -0.0480298 | -1.70491e-05 | True | True |
| 2024-07-05 00:00:00 | 2024-06-06 00:00:00 | 13.25 | -0.0624122 | -0.191363 | -1.98848e-05 | False | True |
| 2024-07-26 00:00:00 | 2024-07-08 00:00:00 | 11.73 | -0.141506 | -0.701703 | -2.56554e-06 | False | False |

The available VIX value refers to the prior native session. Its signed change is log(IV_(t−1)) − log(IV_(t−2)), with IV=(VIX_percent/100)^2. Large declines in available IV can remove a positive fitted contribution while other fitted contributions and the intercept remain negative. The linear predictor has no positivity constraint.

| refit_origin | intercept | rv_daily | rv_weekly | rv_monthly | vix_implied_variance | vix_vif | condition_standardized |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2023-12-04 00:00:00 | -1.84995e-05 | 0.377377 | -0.0656499 | -0.0593115 | 0.00242918 | 2.21549 | 3.29358 |
| 2024-01-03 00:00:00 | -1.68011e-05 | 0.38794 | -0.068476 | -0.0115462 | 0.00220086 | 2.05584 | 3.25345 |
| 2024-02-02 00:00:00 | -1.62912e-05 | 0.374545 | -0.0404866 | -0.0217008 | 0.00218821 | 2.06247 | 3.25548 |
| 2024-03-02 00:00:00 | -1.12916e-05 | 0.373391 | 0.0117398 | -0.092031 | 0.00190032 | 2.16462 | 3.2296 |
| 2024-04-04 00:00:00 | -9.5508e-06 | 0.365517 | 0.0245242 | -0.0819989 | 0.00179125 | 2.11232 | 3.19448 |
| 2024-05-08 00:00:00 | -9.08033e-06 | 0.349742 | 0.0241258 | -0.0672347 | 0.00178414 | 2.00636 | 3.16197 |
| 2024-06-06 00:00:00 | -6.08786e-05 | 0.300553 | -0.487293 | -0.474701 | 0.00644316 | 1.51615 | 3.8562 |
| 2024-07-08 00:00:00 | -6.50177e-05 | 0.218345 | -0.203649 | -0.147905 | 0.0057848 | 1.30956 | 2.39219 |
| 2024-08-07 00:00:00 | -6.10204e-05 | 0.215262 | -0.190129 | -0.146485 | 0.00556103 | 1.29877 | 2.38061 |
| 2024-09-06 00:00:00 | -6.03206e-05 | 0.218484 | -0.181176 | -0.152386 | 0.00541979 | 1.29398 | 2.38274 |
| 2024-10-08 00:00:00 | -5.88217e-05 | 0.219689 | -0.182334 | -0.155341 | 0.00537201 | 1.2935 | 2.38066 |
| 2024-11-06 00:00:00 | -5.82514e-05 | 0.220418 | -0.184422 | -0.153069 | 0.00534064 | 1.29455 | 2.37684 |
| 2024-12-09 00:00:00 | -5.77236e-05 | 0.218154 | -0.183861 | -0.154842 | 0.00533921 | 1.29977 | 2.38495 |

Each forecast contribution is recorded in stage4b_legacy_events.csv and reconciled to its saved raw forecast. Refit slopes are conditional associations; changes after a shock are not structural causal effects of VIX.

## Correlation, standardization and numerical stability

The standardized design condition number ranges from 2.377 to 3.856; the VIX variance-inflation factor ranges from 1.294 to 2.215. The maximum absolute standardized-versus-unscaled OLS prediction difference is 2.98427e-17. Standardization substantially changes numerical conditioning but, for unregularized OLS with an intercept, does not change the fitted linear function. It did not create the negative forecasts. The measured VIF/condition numbers do not support severe numerical multicollinearity as the principal cause.

| refit_origin | feature | other_feature | correlation |
| --- | --- | --- | --- |
| 2023-12-04 00:00:00 | vix_implied_variance | rv_daily | 0.573566 |
| 2023-12-04 00:00:00 | vix_implied_variance | rv_weekly | 0.696936 |
| 2023-12-04 00:00:00 | vix_implied_variance | rv_monthly | 0.58055 |
| 2024-01-03 00:00:00 | vix_implied_variance | rv_daily | 0.557285 |
| 2024-01-03 00:00:00 | vix_implied_variance | rv_weekly | 0.681181 |
| 2024-01-03 00:00:00 | vix_implied_variance | rv_monthly | 0.542139 |
| 2024-02-02 00:00:00 | vix_implied_variance | rv_daily | 0.548558 |
| 2024-02-02 00:00:00 | vix_implied_variance | rv_weekly | 0.685386 |
| 2024-02-02 00:00:00 | vix_implied_variance | rv_monthly | 0.544837 |
| 2024-03-02 00:00:00 | vix_implied_variance | rv_daily | 0.535455 |
| 2024-03-02 00:00:00 | vix_implied_variance | rv_weekly | 0.67449 |
| 2024-03-02 00:00:00 | vix_implied_variance | rv_monthly | 0.615358 |
| 2024-04-04 00:00:00 | vix_implied_variance | rv_daily | 0.521295 |
| 2024-04-04 00:00:00 | vix_implied_variance | rv_weekly | 0.665077 |
| 2024-04-04 00:00:00 | vix_implied_variance | rv_monthly | 0.611554 |
| 2024-05-08 00:00:00 | vix_implied_variance | rv_daily | 0.495217 |
| 2024-05-08 00:00:00 | vix_implied_variance | rv_weekly | 0.654561 |
| 2024-05-08 00:00:00 | vix_implied_variance | rv_monthly | 0.594265 |
| 2024-06-06 00:00:00 | vix_implied_variance | rv_daily | 0.348519 |
| 2024-06-06 00:00:00 | vix_implied_variance | rv_weekly | 0.529927 |
| 2024-06-06 00:00:00 | vix_implied_variance | rv_monthly | 0.546682 |
| 2024-07-08 00:00:00 | vix_implied_variance | rv_daily | 0.352398 |
| 2024-07-08 00:00:00 | vix_implied_variance | rv_weekly | 0.452965 |
| 2024-07-08 00:00:00 | vix_implied_variance | rv_monthly | 0.318541 |
| 2024-08-07 00:00:00 | vix_implied_variance | rv_daily | 0.353685 |
| 2024-08-07 00:00:00 | vix_implied_variance | rv_weekly | 0.44319 |
| 2024-08-07 00:00:00 | vix_implied_variance | rv_monthly | 0.313941 |
| 2024-09-06 00:00:00 | vix_implied_variance | rv_daily | 0.347813 |
| 2024-09-06 00:00:00 | vix_implied_variance | rv_weekly | 0.441464 |
| 2024-09-06 00:00:00 | vix_implied_variance | rv_monthly | 0.315074 |
| 2024-10-08 00:00:00 | vix_implied_variance | rv_daily | 0.344925 |
| 2024-10-08 00:00:00 | vix_implied_variance | rv_weekly | 0.440696 |
| 2024-10-08 00:00:00 | vix_implied_variance | rv_monthly | 0.318744 |
| 2024-11-06 00:00:00 | vix_implied_variance | rv_daily | 0.345316 |
| 2024-11-06 00:00:00 | vix_implied_variance | rv_weekly | 0.440723 |
| 2024-11-06 00:00:00 | vix_implied_variance | rv_monthly | 0.320103 |
| 2024-12-09 00:00:00 | vix_implied_variance | rv_daily | 0.344948 |
| 2024-12-09 00:00:00 | vix_implied_variance | rv_weekly | 0.443861 |
| 2024-12-09 00:00:00 | vix_implied_variance | rv_monthly | 0.326906 |

Full feature correlation matrices are saved per refit. Moderate correlation can affect partial slopes, but unconstrained levels predictions, coefficient shifts and extrapolation are the direct observed mechanism.

## QLIKE floor sensitivity — diagnostic only

| floor_fraction_of_training_median | n | qlike | calibration_ratio | floored_count | status |
| --- | --- | --- | --- | --- | --- |
| 1e-06 | 226 | 125284 | 1.14688 | 21 | DIAGNOSTIC_COUNTERFACTUAL_NOT_MODEL_SELECTION |
| 0.0001 | 226 | 1242.98 | 1.14687 | 21 | DIAGNOSTIC_COUNTERFACTUAL_NOT_MODEL_SELECTION |
| 0.001 | 226 | 115.549 | 1.14682 | 21 | DIAGNOSTIC_COUNTERFACTUAL_NOT_MODEL_SELECTION |
| 0.01 | 226 | 2.99828 | 1.14629 | 21 | DIAGNOSTIC_COUNTERFACTUAL_NOT_MODEL_SELECTION |
| 0.1 | 226 | -8.06425 | 1.14098 | 21 | DIAGNOSTIC_COUNTERFACTUAL_NOT_MODEL_SELECTION |

These five fixed counterfactual floors retain every matched observation and refit no model. The smallest setting reproduces Stage 4. For a negative raw prediction, the y/h term grows rapidly as the replacement floor approaches zero. No floor is selected from this table; unsuccessful Stage 4 forecasts remain unchanged.

Sources: [NSE India VIX definition](https://www.nseindia.com/static/products-services/indices-indiavix-index); [Ridge objective and penalty convention](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html). The Ridge solve uses NumPy augmented least squares, with no additional package dependency.
