# Trading-cost sensitivity — EXPLORATORY / PROVISIONAL / NON-EXECUTABLE

Costs5/10/20bps per one-way traded notional are illustrative scenario assumptions, not measured expenses. They do not certify actual spread, market impact, fees, taxes or closing-auction fill availability. Zero-cost paths use the same rule and timing; terminal cost drag includes compounding. No configuration is selected from this grid.

Primary-policy cost comparison:

| model | cost_bps | gross_cumulative_return | net_cumulative_return | transaction_cost_drag | net_sharpe | annualized_one_way_turnover |
| --- | --- | --- | --- | --- | --- | --- |
| ewma | 5 | 0.0335957 | 0.030977 | 0.00261867 | 0.302478 | 5.14783 |
| ewma | 10 | 0.0335957 | 0.0283652 | 0.0052305 | 0.282741 | 5.14726 |
| ewma | 20 | 0.0335957 | 0.023162 | 0.0104337 | 0.243307 | 5.14614 |
| garch | 5 | 0.0370399 | 0.0332291 | 0.00381075 | 0.321669 | 7.4715 |
| garch | 10 | 0.0370399 | 0.0294326 | 0.00760729 | 0.29269 | 7.47088 |
| garch | 20 | 0.0370399 | 0.0218819 | 0.0151579 | 0.234804 | 7.46964 |
| har_daily | 5 | 0.0675961 | 0.0643453 | 0.00325087 | 0.535528 | 6.22255 |
| har_daily | 10 | 0.0675961 | 0.0611045 | 0.00649159 | 0.51286 | 6.2218 |
| har_daily | 20 | 0.0675961 | 0.0546534 | 0.0129428 | 0.467432 | 6.2203 |
| log_har_daily | 5 | 0.0826459 | 0.0759566 | 0.00668924 | 0.618882 | 12.6103 |
| log_har_daily | 10 | 0.0826459 | 0.069309 | 0.0133369 | 0.572296 | 12.6094 |
| log_har_daily | 20 | 0.0826459 | 0.0561374 | 0.0265085 | 0.47905 | 12.6075 |
| log_har_vix_daily | 5 | 0.0827069 | 0.0786566 | 0.00405026 | 0.630039 | 7.63521 |
| log_har_vix_daily | 10 | 0.0827069 | 0.0746218 | 0.0080851 | 0.602403 | 7.63446 |
| log_har_vix_daily | 20 | 0.0827069 | 0.0665981 | 0.0161088 | 0.547055 | 7.63298 |

The full CSV preserves180 factorial dynamic configurations (five models × three targets × two frequencies × two bands × three costs),25 one-factor/operational stress paths,12 primary static/matched paths and four static cost variants =221 registered paths. A disclosed post-result addendum adds10 ex-post non-deployable matched-exposure/risk diagnostics, for231 total. Every path also has a zero-cost shadow. The five primary dynamic cases are included within the180, not counted twice. Targets are experimental parameters, not portfolio recommendations.

The minimum25% case changes target bounds, not continuous enforcement between trades. Cash4% is hypothetical ACT/365. Delay sensitivity uses genuine h=3 forecasts rather than applying a stale h=2 forecast to the wrong target. Failure-to-cash uses only the registered minimum; the operational stress marks every20th evaluation execution signal unavailable without changing saved original forecasts. Actual model failures are retained in all paths.

| strategy | net_cumulative_return | net_sharpe | realized_volatility | maximum_drawdown | average_equity_exposure | holding_failure_sessions |
| --- | --- | --- | --- | --- | --- | --- |
| ewma_minimum25 | 0.0283652 | 0.282741 | 0.13096 | -0.107138 | 0.90082 | 0 |
| ewma_cash4 | 0.0323572 | 0.00849061 | 0.130996 | -0.106911 | 0.90082 | 0 |
| ewma_delay_one_session | 0.0424875 | 0.385195 | 0.132676 | -0.107426 | 0.901021 | 0 |
| ewma_failure_to_cash | 0.0283652 | 0.282741 | 0.13096 | -0.107138 | 0.90082 | 0 |
| ewma_failure_injection | 0.0318886 | 0.309415 | 0.130865 | -0.106779 | 0.896926 | 13 |
| garch_minimum25 | 0.0294326 | 0.29269 | 0.129437 | -0.101755 | 0.891236 | 0 |
| garch_cash4 | 0.0338275 | 0.0182357 | 0.12947 | -0.101254 | 0.891236 | 0 |
| garch_delay_one_session | 0.0426518 | 0.388831 | 0.131429 | -0.102625 | 0.889123 | 0 |
| garch_failure_to_cash | 0.0294326 | 0.29269 | 0.129437 | -0.101755 | 0.891236 | 0 |
| garch_failure_injection | 0.032889 | 0.319031 | 0.129422 | -0.101253 | 0.88769 | 13 |
| har_daily_minimum25 | 0.0611045 | 0.51286 | 0.135448 | -0.103387 | 0.936941 | 22 |
| har_daily_cash4 | 0.0636688 | 0.236683 | 0.135461 | -0.10312 | 0.936941 | 22 |
| har_daily_delay_one_session | 0.0673178 | 0.554508 | 0.136144 | -0.103491 | 0.939754 | 24 |
| har_daily_failure_to_cash | 0.0318564 | 0.307974 | 0.131698 | -0.103387 | 0.848231 | 22 |
| har_daily_failure_injection | 0.0626644 | 0.524489 | 0.135238 | -0.10373 | 0.93285 | 34 |
| log_har_daily_minimum25 | 0.069309 | 0.572296 | 0.134948 | -0.10224 | 0.957455 | 22 |
| log_har_daily_cash4 | 0.071097 | 0.289496 | 0.134957 | -0.101882 | 0.957455 | 22 |
| log_har_daily_delay_one_session | 0.0800493 | 0.639941 | 0.136983 | -0.104509 | 0.964369 | 22 |
| log_har_daily_failure_to_cash | 0.0398347 | 0.36835 | 0.131192 | -0.10224 | 0.868745 | 22 |
| log_har_daily_failure_injection | 0.0673863 | 0.559341 | 0.13476 | -0.103818 | 0.953993 | 34 |
| log_har_vix_daily_minimum25 | 0.0746218 | 0.602403 | 0.137031 | -0.108094 | 0.97654 | 22 |
| log_har_vix_daily_cash4 | 0.0756374 | 0.318499 | 0.137046 | -0.108005 | 0.97654 | 22 |
| log_har_vix_daily_delay_one_session | 0.0802128 | 0.682859 | 0.126547 | -0.107822 | 0.9693 | 22 |
| log_har_vix_daily_failure_to_cash | 0.045001 | 0.402301 | 0.133338 | -0.108094 | 0.88783 | 22 |
| log_har_vix_daily_failure_injection | 0.0737525 | 0.598563 | 0.136393 | -0.108094 | 0.971904 | 34 |

Weekly rebalancing and5-point bands appear in the full CSV. They hold units between trades, not constant weights. Daily risk targets do not guarantee weekly holding-period risk. Sample length is one repeatedly examined year; no real-world profit inference is warranted.

