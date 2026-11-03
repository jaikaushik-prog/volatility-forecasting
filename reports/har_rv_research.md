# HAR-RV research — PROVISIONAL

**Validation findings only; final holdout not evaluated.** NSE spot identity for NIFTY was confirmed by the user; the export/timezone/bar conventions remain unverified. The additional full-session VIX lag does not resolve those uncertainties.

## Predeclared models and targets

M1 `har`: OLS in variance levels using RV_t, arithmetic mean RV over 5 sessions through t and over 22 sessions through t. M2 `log_har`: log target and logs of those arithmetic averages. M3 `har_overnight`: M1 plus observed overnight square and 5/22-session means. M4 `har_vix`: M1 plus annualized implied variance (VIX_(t−1)/100)^2. M5 `har_vix_overnight`: M1 plus both groups. SENSEX uses M1–M3; India VIX is NIFTY-based and is not silently treated as SENSEX IV.

Primary target: next-session within-session RV at 5 minutes. Secondary: next-session intraday RV plus squared overnight log return. Scheduled-break reopening squares are deliberately NOT added to this requested secondary target. It is distinct from squared close-to-close return. The additional spot-c2c panel fits HAR predictors to squared close-to-close returns and compares them with the existing zero-mean EWMA/GARCH/EGARCH/GJR implementations on that SAME target. Daily NIFTY TRI is never imported into these spot comparisons. Daily-return GARCH is not ranked against intraday RV.

Benchmarks: previous observed target variance, 5/22-session target means, EWMA of observed variance (lambda .94; initial 22-session mean). In the spot-c2c panel, these smooth squared spot returns. Return-EWMA uses the existing sample-variance initialization. Daily GARCH uses ×100 return scaling, converted back to decimal variance, 252-return minimum, 500-session window and 21-session refits. Missing returns reset its filter; no model substitutes for failed fits.

HAR uses a rolling 500-session-position window, at least 126 completed pairs, and refits every 21 sessions. Every HAR variant within an asset/target/frequency/scenario uses the SAME completed training rows (union of required features), not just matched evaluation dates. Thus added VIX/overnight effects are not disguised training-sample changes. SENSEX uses its own sample. Parameters remain fixed between refits, while current observable predictors update.

The positive floor is 10^-6 times the median positive training target, recomputed only at refits. Zero observations remain unchanged for evaluation; log-HAR floors them only inside its training transformation. Nonpositive level predictions are floored with raw predictions and flags retained. Nonfinite/explosive forecasts are missing. Log-HAR uses training residual smearing: exp(predicted log variance) × mean(exp(training residual)). This assumes a common residual retransformation factor and is not a guarantee against conditional bias. OLS is standardized using training statistics; rank, condition number, coefficients, fit dates and residual diagnostics are saved.

All complete verified special sessions retain their measured duration. No normalization to 375 minutes is invented; the basic HAR has no explicit duration regressor, a remaining specification limitation. Missing or excluded sessions break rolling feature windows. Forecasts are issued after the origin close and before the next session; `forecast_created_at` is a historical-simulation convention, not evidence of actual historical issuance.

Method: [Corsi, A Simple Approximate Long-Memory Model of Realized Volatility](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1365738). India VIX units/horizon: [NSE definition](https://www.nseindia.com/static/products-services/indices-indiavix-index).

## Validation rankings — separate targets

| asset | target | model | n_evaluated | qlike | mse | mae | calibration_ratio | bias | estimation_failure_rate | prediction_failure_rate | runtime_seconds | rank_qlike |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NIFTY | intraday | log_har | 226 | -8.93276 | 1.39728e-08 | 3.19171e-05 | 1.1579 | -6.99294e-06 | 0 | 0.0883534 | 0.80075 | 1 |
| NIFTY | intraday | har | 226 | -8.91741 | 1.46439e-08 | 3.61889e-05 | 1.02901 | -1.4456e-06 | 0 | 0.0883534 | 0.884562 | 2 |
| NIFTY | intraday | rv_ewma | 226 | -8.83928 | 1.5068e-08 | 3.80402e-05 | 1.03667 | -1.81415e-06 | 0 | 0 | 0.404579 | 3 |
| NIFTY | intraday | mean22 | 226 | -8.8216 | 1.55746e-08 | 4.04998e-05 | 1.01832 | -9.22579e-07 | 0 | 0 | 0.475698 | 4 |
| NIFTY | intraday | mean5 | 226 | -8.82022 | 1.73019e-08 | 3.96709e-05 | 1.01091 | -5.53587e-07 | 0 | 0 | 0.307138 | 5 |
| NIFTY | intraday | previous | 226 | -8.72841 | 2.16693e-08 | 4.13094e-05 | 1.00266 | -1.35789e-07 | 0 | 0 | 0.305494 | 6 |
| NIFTY | intraday | har_overnight | 226 | -8.63803 | 1.49602e-08 | 3.79902e-05 | 1.05902 | -2.85774e-06 | 0 | 0.0883534 | 0.706859 | 7 |
| NIFTY | intraday | har_vix_overnight | 226 | 11295.1 | 1.29831e-08 | 3.55155e-05 | 1.06991 | -3.35094e-06 | 0 | 0.0883534 | 0.69022 | 8 |
| NIFTY | intraday | har_vix | 226 | 125284 | 1.32534e-08 | 3.43869e-05 | 1.14688 | -6.56743e-06 | 0 | 0.0883534 | 0.754019 | 9 |
| NIFTY | intraday_overnight | har_overnight | 226 | -8.55768 | 2.28262e-08 | 5.03018e-05 | 1.15538 | -9.93784e-06 | 0 | 0.0883534 | 0.727591 | 1 |
| NIFTY | intraday_overnight | log_har | 226 | -8.54731 | 2.25997e-08 | 4.72576e-05 | 1.20621 | -1.2633e-05 | 0 | 0.0883534 | 0.701121 | 2 |
| NIFTY | intraday_overnight | har | 226 | -8.51075 | 2.36474e-08 | 5.22501e-05 | 1.09644 | -6.49958e-06 | 0 | 0.0883534 | 0.782046 | 3 |
| NIFTY | intraday_overnight | rv_ewma | 226 | -8.4938 | 2.35168e-08 | 5.65077e-05 | 1.04067 | -2.88808e-06 | 0 | 0 | 0.351111 | 4 |
| NIFTY | intraday_overnight | mean5 | 226 | -8.48732 | 2.65099e-08 | 5.80978e-05 | 1.01697 | -1.23295e-06 | 0 | 0 | 0.285436 | 5 |
| NIFTY | intraday_overnight | mean22 | 226 | -8.4494 | 2.49962e-08 | 6.10099e-05 | 1.02962 | -2.12608e-06 | 0 | 0 | 0.284494 | 6 |
| NIFTY | intraday_overnight | previous | 226 | -8.42027 | 1.98575e-08 | 5.29115e-05 | 1.00695 | -5.09915e-07 | 0 | 0 | 0.292037 | 7 |
| NIFTY | intraday_overnight | har_vix_overnight | 226 | 101186 | 2.01728e-08 | 5.06116e-05 | 1.22108 | -1.33787e-05 | 0 | 0.0883534 | 0.750756 | 8 |
| NIFTY | intraday_overnight | har_vix | 226 | 118806 | 2.16553e-08 | 5.15336e-05 | 1.21064 | -1.28569e-05 | 0 | 0.0883534 | 0.695413 | 9 |
| NIFTY | spot_c2c_squared | spot_garch | 227 | -8.46127 | 6.18154e-08 | 7.5861e-05 | 1.49634 | -2.48493e-05 | 0 | 0 | 0.454183 | 1 |
| NIFTY | spot_c2c_squared | rv_ewma | 227 | -8.44196 | 6.29737e-08 | 9.1395e-05 | 0.999924 | 5.68491e-09 | 0 | 0 | 0.670339 | 2 |
| NIFTY | spot_c2c_squared | spot_ewma | 227 | -8.44178 | 6.29739e-08 | 9.13679e-05 | 1.0007 | -5.23612e-08 | 0 | 0 | 0.365562 | 3 |
| NIFTY | spot_c2c_squared | log_har | 227 | -8.43298 | 6.24236e-08 | 7.89451e-05 | 1.27591 | -1.61999e-05 | 0 | 0.0883534 | 0.714377 | 4 |
| NIFTY | spot_c2c_squared | spot_gjr | 227 | -8.33102 | 6.1611e-08 | 7.50212e-05 | 1.4445 | -2.30526e-05 | 0 | 0 | 0.555684 | 5 |
| NIFTY | spot_c2c_squared | mean22 | 227 | -8.31153 | 6.61473e-08 | 9.69473e-05 | 0.98641 | 1.03214e-06 | 0 | 0 | 0.281671 | 6 |
| NIFTY | spot_c2c_squared | spot_egarch | 227 | -8.15159 | 6.27647e-08 | 7.62033e-05 | 1.53593 | -2.61399e-05 | 0 | 0 | 0.424835 | 7 |
| NIFTY | spot_c2c_squared | mean5 | 227 | -7.96066 | 7.18533e-08 | 9.39319e-05 | 0.9931 | 5.20484e-07 | 0 | 0 | 0.287846 | 8 |
| NIFTY | spot_c2c_squared | previous | 227 | 33730.4 | 7.60662e-08 | 0.000100579 | 0.999765 | 1.75954e-08 | 0 | 0 | 0.274932 | 9 |
| NIFTY | spot_c2c_squared | har | 227 | 75791.6 | 6.38091e-08 | 8.49425e-05 | 1.24431 | -1.47091e-05 | 0 | 0.0883534 | 0.812101 | 10 |
| NIFTY | spot_c2c_squared | har_overnight | 227 | 100254 | 6.81518e-08 | 8.68919e-05 | 1.26507 | -1.56969e-05 | 0 | 0.0883534 | 0.777864 | 11 |
| NIFTY | spot_c2c_squared | har_vix_overnight | 227 | 207573 | 6.60574e-08 | 8.24814e-05 | 1.41455 | -2.19546e-05 | 0 | 0.0883534 | 0.710262 | 12 |
| NIFTY | spot_c2c_squared | har_vix | 227 | 219063 | 6.21748e-08 | 7.90123e-05 | 1.37218 | -2.03194e-05 | 0 | 0.0883534 | 0.785094 | 13 |

Calibration is mean(observed variance)/mean(predicted variance); above one means aggregate underprediction. QLIKE is log(h)+y/h. Only strictly positive finite forecasts and observed nonnegative targets are scored. All-available metrics are diagnostic; only common-date rows are ranked. Failed/warm-up attempts and runtime are retained outside the common-date filter. Calibration ranking uses distance of log(calibration ratio) from zero.

## Incremental information and statistical uncertainty

log_har versus har: n=226, mean QLIKE difference=-0.0153459 (negative favours log_har); gap-aware bootstrap 95% interval [-0.0709816, 0.0303041]; HAC/Holm p=1, bootstrap/Holm p=1. Multiplicity-adjusted evidence under both checks: False. Without retrospective shocks, mean difference=-0.0260738; top five dates account for 22.7% of absolute paired loss differences. Inference status: approximate_exploratory.

har_vix versus har: n=226, mean QLIKE difference=125293 (negative favours har_vix); gap-aware bootstrap 95% interval [4195.21, 300559]; HAC/Holm p=1, bootstrap/Holm p=1. Multiplicity-adjusted evidence under both checks: False. Without retrospective shocks, mean difference=128710; top five dates account for 47.5% of absolute paired loss differences. Inference status: approximate_exploratory.

har_overnight versus har: n=226, mean QLIKE difference=0.279377 (negative favours har_overnight); gap-aware bootstrap 95% interval [-0.00126475, 0.810039]; HAC/Holm p=1, bootstrap/Holm p=1. Multiplicity-adjusted evidence under both checks: False. Without retrospective shocks, mean difference=0.326963; top five dates account for 48.6% of absolute paired loss differences. Inference status: approximate_exploratory.

har_vix_overnight versus har_overnight: n=226, mean QLIKE difference=11303.7 (negative favours har_vix_overnight); gap-aware bootstrap 95% interval [-0.708881, 33911.7]; HAC/Holm p=1, bootstrap/Holm p=1. Multiplicity-adjusted evidence under both checks: False. Without retrospective shocks, mean difference=11612; top five dates account for 100.0% of absolute paired loss differences. Inference status: approximate_exploratory.

Paired losses use identical targets/dates. HAC covariance respects session-position spacing; stationary block-bootstrap blocks restart at missing-session gaps. Intervals are pointwise approximate 95% intervals; p-values receive Holm adjustment over ALL predeclared validation comparisons across assets, frequencies, targets and exclusion scenarios. Nested models, short samples and model misspecification limit these asymptotic/resampling checks. Rankings alone do not establish superiority.

## Robustness and concentration

1/5/10/15-minute targets are evaluated separately; no pooled frequency ranking is produced. The 10-minute series retains its labelled final short interval. Sensitivity refits after excluding absolute-return/stale-price flags; legitimate crisis moves can meet those thresholds. Excluded observations remain missing, with no interpolation. Compare eligible/exclusion scenarios also on their intersection of target dates in `har_rv_sensitivity.csv`. SENSEX is a secondary robustness sample, not a pooled estimate of NIFTY predictability.

Regime and quarter tables distinguish origin-known trailing-RV regimes, transitions and lagged VIX changes from retrospective shock/recovery labels. Shock definitions are fixed in configuration. Shock windows never enter model estimation. Small event samples cannot identify which model universally adapts fastest. Paired-test output includes the mean loss difference outside shocks and the concentration of absolute loss differences in five dates.

## Limitations and next research step

These results are PROVISIONAL. Confirm the source/export conventions, rerun the same frozen specifications on a verified vintage, and obtain a genuinely unseen evaluation period before advancing models to position-sizing research. A gain in intraday-RV accuracy is not evidence of portfolio utility. No position sizing, trading, Heston or LSTM was implemented.

Forecasts, pre-observation issuance records, fit diagnostics and input/config/code/output hashes are stored in the immutable run `d3094f857ec08cfaad204970`. The protected 2025–2026 holdout remains unevaluated by this workflow.

## Small or unavailable comparison samples

| asset | frequency | scenario | target | model | n_evaluated |
| --- | --- | --- | --- | --- | --- |
| SENSEX | 5 | eligible | spot_c2c_squared | har | 0 |
| SENSEX | 5 | eligible | spot_c2c_squared | har_overnight | 0 |
| SENSEX | 5 | eligible | spot_c2c_squared | log_har | 0 |
| SENSEX | 5 | eligible | spot_c2c_squared | mean22 | 0 |
| SENSEX | 5 | eligible | spot_c2c_squared | mean5 | 0 |
| SENSEX | 5 | eligible | spot_c2c_squared | previous | 0 |
| SENSEX | 5 | eligible | spot_c2c_squared | rv_ewma | 0 |
| SENSEX | 5 | eligible | spot_c2c_squared | spot_egarch | 0 |
| SENSEX | 5 | eligible | spot_c2c_squared | spot_ewma | 0 |
| SENSEX | 5 | eligible | spot_c2c_squared | spot_garch | 0 |
| SENSEX | 5 | eligible | spot_c2c_squared | spot_gjr | 0 |
| SENSEX | 5 | exclude_questionable | spot_c2c_squared | har | 0 |
| SENSEX | 5 | exclude_questionable | spot_c2c_squared | har_overnight | 0 |
| SENSEX | 5 | exclude_questionable | spot_c2c_squared | log_har | 0 |
| SENSEX | 5 | exclude_questionable | spot_c2c_squared | mean22 | 0 |
| SENSEX | 5 | exclude_questionable | spot_c2c_squared | mean5 | 0 |
| SENSEX | 5 | exclude_questionable | spot_c2c_squared | previous | 0 |
| SENSEX | 5 | exclude_questionable | spot_c2c_squared | rv_ewma | 0 |
| SENSEX | 5 | exclude_questionable | spot_c2c_squared | spot_egarch | 0 |
| SENSEX | 5 | exclude_questionable | spot_c2c_squared | spot_ewma | 0 |
| SENSEX | 5 | exclude_questionable | spot_c2c_squared | spot_garch | 0 |
| SENSEX | 5 | exclude_questionable | spot_c2c_squared | spot_gjr | 0 |

These panels are insufficient for strong statistical conclusions; zero means no common comparable forecasts, not zero forecasting loss.

## Figures

- [NIFTY_forecast_vs_realized.png](figures/har_rv/NIFTY_forecast_vs_realized.png)
- [NIFTY_qlike.png](figures/har_rv/NIFTY_qlike.png)
- [NIFTY_incremental_information.png](figures/har_rv/NIFTY_incremental_information.png)
- [NIFTY_calibration.png](figures/har_rv/NIFTY_calibration.png)
- [NIFTY_shock_diagnostics.png](figures/har_rv/NIFTY_shock_diagnostics.png)
- [NIFTY_garch_comparable_target.png](figures/har_rv/NIFTY_garch_comparable_target.png)
- [NIFTY_vix_subsequent_rv.png](figures/har_rv/NIFTY_vix_subsequent_rv.png)
- [SENSEX_forecast_vs_realized.png](figures/har_rv/SENSEX_forecast_vs_realized.png)
- [SENSEX_qlike.png](figures/har_rv/SENSEX_qlike.png)
- [SENSEX_incremental_information.png](figures/har_rv/SENSEX_incremental_information.png)
- [SENSEX_calibration.png](figures/har_rv/SENSEX_calibration.png)
- [SENSEX_shock_diagnostics.png](figures/har_rv/SENSEX_shock_diagnostics.png)
