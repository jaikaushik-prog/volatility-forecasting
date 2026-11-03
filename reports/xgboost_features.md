# XGBoost variance forecasting and feature evidence

The target is next-session squared decimal log return. Features at origin t use observations through t only. Training ends with feature row t-1 and label r_t². The current origin row has no known next-session training label.

Features: squared/absolute current and preceding returns, 5/20/60-session sample variance (ddof=1), EWMA (lambda .94; first 20 squared returns initialize its mean), negative-return indicators/counts, variance differences, and trailing 60-session log drawdown. These daily-price features are not intraday realized variance.

Tweedie objective with variance power 1.5 and log link predicts a positive conditional mean of a nonnegative target. Targets are multiplied by 10,000 for optimization; predictions are divided by that scale. No naive exponentiation of a log-target regression is used. A configurable 1e-10 decimal-variance floor is recorded per prediction; nonfinite or negative predictions fail explicitly. Trees require no fitted feature standardizer.

The predefined depth/tree-count grid is selected with chronological blocked validation on labels already known at the origin, retuned at most every 252 observations during development, then frozen. Model weights refit every 21 observations. Each asset has independent training and selection. CPU histogram trees use one thread and a fixed seed.

Importance is normalized split gain from each fitted booster, averaged across refits. It is training-set model importance, not causal importance or out-of-sample permutation evidence; correlated features can share or substitute importance.

## NIFTY50_TRI

| feature | normalized gain |
|---|---|
| drawdown_60 | 0.3036 |
| var_20 | 0.1145 |
| ewma_094 | 0.0826 |
| var_5 | 0.0820 |
| abs_return_lag2 | 0.0773 |
| var_change_20_60 | 0.0739 |
| neg_count_5 | 0.0690 |
| sq_return_lag1 | 0.0670 |
| var_change_5_20 | 0.0501 |
| neg_return_lag1 | 0.0417 |
| var_60 | 0.0383 |
| abs_return_lag1 | 0.0000 |
| sq_return_lag2 | 0.0000 |

## SPY

| feature | normalized gain |
|---|---|
| drawdown_60 | 0.3910 |
| ewma_094 | 0.0838 |
| var_5 | 0.0826 |
| var_change_20_60 | 0.0708 |
| abs_return_lag2 | 0.0676 |
| var_20 | 0.0656 |
| var_change_5_20 | 0.0596 |
| var_60 | 0.0522 |
| sq_return_lag1 | 0.0514 |
| neg_count_5 | 0.0417 |
| neg_return_lag1 | 0.0337 |
| abs_return_lag1 | 0.0000 |
| sq_return_lag2 | 0.0000 |

## VT

| feature | normalized gain |
|---|---|
| drawdown_60 | 0.3061 |
| sq_return_lag1 | 0.0994 |
| var_5 | 0.0959 |
| abs_return_lag2 | 0.0954 |
| ewma_094 | 0.0904 |
| var_change_20_60 | 0.0855 |
| var_20 | 0.0736 |
| var_change_5_20 | 0.0547 |
| var_60 | 0.0491 |
| neg_count_5 | 0.0419 |
| neg_return_lag1 | 0.0079 |
| abs_return_lag1 | 0.0000 |
| sq_return_lag2 | 0.0000 |

## Prediction safeguards

| asset | model | origins | clipped predictions | missing forecasts |
|---|---|---|---|---|
| NIFTY50_TRI | xgboost_v1 | 2,220 | 0 | 0 |
| SPY | xgboost_v1 | 2,769 | 0 | 0 |
| VT | xgboost_v1 | 2,769 | 0 | 0 |

Exact search outcomes/fold boundaries are in `xgboost_tuning.csv`; fitted parameters and booster hashes are in `fits.parquet`. All trees can be reproduced from the archived data hashes, code hashes, model configuration, seeds and package versions.

[XGBoost objective and parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html)
