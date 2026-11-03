# Forecast accuracy versus economic value — EXPLORATORY / PROVISIONAL

The forecast comparison is for NIFTY TRI **daily close-to-close log-return variance**, at horizon2, on common finite target dates. Portfolio P&L uses simple total returns on every native session, with failures explicitly handled. Original spot intraday RV QLIKE scores are not imported into this ranking. HAR/Log-HAR/VIX below are newly estimated economic-study specifications. The shorter common QLIKE sample and complete economic path are different estimands; this scatter is descriptive, not a controlled causal test.

| model | qlike | qlike_rank | calibration | failure_rate | net_cumulative_return | net_sharpe | maximum_drawdown | average_equity_exposure | transaction_cost_drag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ewma | -8.15289 | 4 | 1.00796 | 0 | 0.0283652 | 0.282741 | -0.107138 | 0.90082 | 0.0052305 |
| garch | -8.21784 | 2 | 0.959158 | 0 | 0.0294326 | 0.29269 | -0.101755 | 0.891236 | 0.00760729 |
| har_daily | -8.19888 | 3 | 1.16979 | 0.0887097 | 0.0611045 | 0.51286 | -0.103387 | 0.936941 | 0.00649159 |
| log_har_daily | -8.28888 | 1 | 1.39041 | 0.0887097 | 0.069309 | 0.572296 | -0.10224 | 0.957455 | 0.0133369 |
| log_har_vix_daily | -8.14583 | 5 | 1.57793 | 0.0887097 | 0.0746218 | 0.602403 | -0.108094 | 0.97654 | 0.0080851 |

Lowest exploratory QLIKE: **log_har_daily**. Highest primary dynamic-policy net Sharpe: **log_har_vix_daily**. These are point-estimate descriptions, not selected winners or statistically confirmed alpha. Their agreement/disagreement does not prove that forecast accuracy causes economic benefit. Inverse-volatility weights, the100% cap, next-close delay, lower average exposure, cash and costs all intervene. Better error loss can produce worse timing or missed recovery; a lower-quality forecast can accidentally de-risk before a loss. Static matched benchmarks are essential to distinguish this from persistent exposure reduction.

Economic uncertainty is based on the15 predeclared paired Sharpe contrasts, with 3 adjusted p-values below.05. See `position_sizing_experiment.md` for all intervals, matching errors and the conditional-bootstrap limitation. Even a small adjusted p-value in this reused exploratory sample would not be independent confirmation.

Quarter diagnostics for the primary dynamic paths (no quarter is used for model selection):

| strategy | quarter | net_cumulative_return | net_sharpe | realized_volatility | maximum_drawdown |
| --- | --- | --- | --- | --- | --- |
| ewma_v12_c10_daily_b0 | 2024Q1 | 0.0234528 | 0.882096 | 0.116121 | -0.0380708 |
| ewma_v12_c10_daily_b0 | 2024Q2 | 0.0368479 | 0.959841 | 0.171019 | -0.0588857 |
| ewma_v12_c10_daily_b0 | 2024Q3 | 0.0577386 | 2.15793 | 0.104988 | -0.0380796 |
| ewma_v12_c10_daily_b0 | 2024Q4 | -0.0838088 | -2.82279 | 0.123295 | -0.0931199 |
| garch_v12_c10_daily_b0 | 2024Q1 | 0.0209659 | 0.824059 | 0.111466 | -0.0368357 |
| garch_v12_c10_daily_b0 | 2024Q2 | 0.0370825 | 0.964962 | 0.171094 | -0.0588874 |
| garch_v12_c10_daily_b0 | 2024Q3 | 0.0580035 | 2.09077 | 0.109038 | -0.0405649 |
| garch_v12_c10_daily_b0 | 2024Q4 | -0.0810619 | -2.87006 | 0.117279 | -0.0877392 |
| har_daily_v12_c10_daily_b0 | 2024Q1 | 0.0272804 | 0.981291 | 0.120639 | -0.0388424 |
| har_daily_v12_c10_daily_b0 | 2024Q2 | 0.0526659 | 1.27788 | 0.178407 | -0.0586517 |
| har_daily_v12_c10_daily_b0 | 2024Q3 | 0.0647949 | 2.30123 | 0.110072 | -0.039273 |
| har_daily_v12_c10_daily_b0 | 2024Q4 | -0.0784632 | -2.6246 | 0.123595 | -0.0899222 |
| log_har_daily_v12_c10_daily_b0 | 2024Q1 | 0.0253244 | 0.922257 | 0.119702 | -0.0393241 |
| log_har_daily_v12_c10_daily_b0 | 2024Q2 | 0.0662833 | 1.57559 | 0.178438 | -0.0586964 |
| log_har_daily_v12_c10_daily_b0 | 2024Q3 | 0.0598159 | 2.12287 | 0.11065 | -0.0406311 |
| log_har_daily_v12_c10_daily_b0 | 2024Q4 | -0.0771335 | -2.62232 | 0.121563 | -0.0881449 |
| log_har_vix_daily_v12_c10_daily_b0 | 2024Q1 | 0.0254042 | 0.924855 | 0.119715 | -0.0393289 |
| log_har_vix_daily_v12_c10_daily_b0 | 2024Q2 | 0.071504 | 1.67478 | 0.180102 | -0.0586465 |
| log_har_vix_daily_v12_c10_daily_b0 | 2024Q3 | 0.0672739 | 2.34869 | 0.111833 | -0.0405382 |
| log_har_vix_daily_v12_c10_daily_b0 | 2024Q4 | -0.0835878 | -2.73669 | 0.126664 | -0.0940911 |

Retain EWMA and both static controls as essential low-complexity economic baselines. Retain GARCH and daily-target HAR/Log-HAR/VIX as research challengers only after provenance and executable data gates pass. Do not advance a live risk overlay or alter the frozen forecasting candidates on these findings. A newly registered, genuinely prospective economic study is required.

