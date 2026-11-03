# Exposure attribution — EXPLORATORY / PROVISIONAL / NON-EXECUTABLE

Each row reconciles exactly to dynamic minus benchmark terminal wealth, divided by initial capital. Allocation effect is (effective dynamic equity fraction − benchmark fraction) × dynamic beginning wealth × equity return. Wealth-scale effect captures different accumulated wealth at the benchmark fraction. Cash P&L difference and negative transaction-cost difference complete the identity. Initial entry costs are included. This separates compounding from allocation; it is an accounting explanation, not causal evidence of forecasting skill.

| model | benchmark | allocation_effect | wealth_scale_effect | cash_pnl_difference | cost_difference | terminal_return_difference |
| --- | --- | --- | --- | --- | --- | --- |
| ewma | buy_hold | -0.0662479 | -0.000368478 | 0 | -0.00427832 | -0.0708947 |
| ewma | matched_exposure_ewma | -0.0662333 | -0.000369275 | 0 | -0.00427823 | -0.0708808 |
| ewma | matched_risk_ewma | -0.0662421 | -0.000368793 | 0 | -0.00427828 | -0.0708892 |
| garch | buy_hold | -0.062478 | -0.000661922 | 0 | -0.00668737 | -0.0698273 |
| garch | matched_exposure_garch | -0.0586858 | -0.000849718 | 0 | -0.00666687 | -0.0662024 |
| garch | matched_risk_garch | -0.0602955 | -0.000772357 | 0 | -0.00667496 | -0.0677428 |
| har_daily | buy_hold | -0.0325944 | -6.22214e-05 | 0 | -0.00549866 | -0.0381553 |
| har_daily | matched_exposure_har_daily | -0.0325944 | -6.22214e-05 | 0 | -0.00549866 | -0.0381553 |
| har_daily | matched_risk_har_daily | -0.0325944 | -6.22214e-05 | 0 | -0.00549866 | -0.0381553 |
| log_har_daily | buy_hold | -0.0176503 | 0.000206806 | 0 | -0.0125074 | -0.0299509 |
| log_har_daily | matched_exposure_log_har_daily | -0.0176409 | 0.000206238 | 0 | -0.0125073 | -0.029942 |
| log_har_daily | matched_risk_log_har_daily | -0.0176466 | 0.00020658 | 0 | -0.0125073 | -0.0299473 |
| log_har_vix_daily | buy_hold | -0.0176264 | 0.000133408 | 0 | -0.00714513 | -0.0246381 |
| log_har_vix_daily | matched_exposure_log_har_vix_daily | -0.0176149 | 0.000132726 | 0 | -0.00714506 | -0.0246273 |
| log_har_vix_daily | matched_risk_log_har_vix_daily | -0.0176218 | 0.000133138 | 0 | -0.0071451 | -0.0246338 |

Allocation categories below are retrospective. Reduced exposure before a loss means less equity on the loss day without a negative immediately preceding session; after-loss means the preceding return was negative. Neither demonstrates foreknowledge. Missed recovery uses positive-return days within10 sessions after a <-2% return. Failure-affected holdings take category precedence, and the remaining categories partition every day. None of these labels affects signals. Persistent low exposure can duplicate constant de-risking.

| model | benchmark | category | allocation_effect |
| --- | --- | --- | --- |
| ewma | buy_hold | higher_or_equal_exposure | 0 |
| ewma | buy_hold | missed_recovery | -0.0541985 |
| ewma | buy_hold | persistent_lower_exposure_other | -0.0447985 |
| ewma | buy_hold | reduced_exposure_after_loss | 0.01206 |
| ewma | buy_hold | reduced_exposure_before_loss | 0.0206891 |
| garch | buy_hold | higher_or_equal_exposure | 0 |
| garch | buy_hold | missed_recovery | -0.0621003 |
| garch | buy_hold | persistent_lower_exposure_other | -0.0452497 |
| garch | buy_hold | reduced_exposure_after_loss | 0.0199686 |
| garch | buy_hold | reduced_exposure_before_loss | 0.0249034 |
| har_daily | buy_hold | forecast_failure_affected_holding | 0 |
| har_daily | buy_hold | higher_or_equal_exposure | 0 |
| har_daily | buy_hold | missed_recovery | -0.020991 |
| har_daily | buy_hold | persistent_lower_exposure_other | -0.033285 |
| har_daily | buy_hold | reduced_exposure_after_loss | 0.0120787 |
| har_daily | buy_hold | reduced_exposure_before_loss | 0.00960287 |
| log_har_daily | buy_hold | forecast_failure_affected_holding | 0 |
| log_har_daily | buy_hold | higher_or_equal_exposure | 0 |
| log_har_daily | buy_hold | missed_recovery | -0.0204434 |
| log_har_daily | buy_hold | persistent_lower_exposure_other | -0.0209841 |
| log_har_daily | buy_hold | reduced_exposure_after_loss | 0.0149867 |
| log_har_daily | buy_hold | reduced_exposure_before_loss | 0.00879044 |
| log_har_vix_daily | buy_hold | forecast_failure_affected_holding | 0 |
| log_har_vix_daily | buy_hold | higher_or_equal_exposure | 0 |
| log_har_vix_daily | buy_hold | missed_recovery | -0.0163709 |
| log_har_vix_daily | buy_hold | persistent_lower_exposure_other | -0.011822 |
| log_har_vix_daily | buy_hold | reduced_exposure_after_loss | 0.00208396 |
| log_har_vix_daily | buy_hold | reduced_exposure_before_loss | 0.0084825 |

The full daily ledger and all matched-benchmark decompositions are saved. Cash drag in the metrics table is a separate arithmetic opportunity-cost diagnostic against100% equity; it is not added again to the reconciled decomposition. Costs, missed recoveries and lower participation must be weighed against drawdown reduction. Rebound and quarterly plots are retrospective diagnostics. No2025–2026 outcomes enter.

