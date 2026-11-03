# Overnight-risk forecasting — PROVISIONAL

All overnight predictors are already observed at the forecast origin. Weekly/monthly means retain missing-session gaps. The target is intraday RV plus overnight squared return, not squared close-to-close return and not the integration artifact that also includes scheduled-break reopening squares.

har_overnight versus har: n=226, mean QLIKE difference=0.279377 (negative favours har_overnight); gap-aware bootstrap 95% interval [-0.00126475, 0.810039]; HAC/Holm p=1, bootstrap/Holm p=1. Multiplicity-adjusted evidence under both checks: False. Without retrospective shocks, mean difference=0.326963; top five dates account for 48.6% of absolute paired loss differences. Inference status: approximate_exploratory.

har_overnight versus har: n=226, mean QLIKE difference=-0.04693 (negative favours har_overnight); gap-aware bootstrap 95% interval [-0.132982, 0.0486101]; HAC/Holm p=1, bootstrap/Holm p=1. Multiplicity-adjusted evidence under both checks: False. Without retrospective shocks, mean difference=0.0137633; top five dates account for 40.9% of absolute paired loss differences. Inference status: approximate_exploratory.

har_vix_overnight versus har_vix: n=226, mean QLIKE difference=-17620 (negative favours har_vix_overnight); gap-aware bootstrap 95% interval [-39602.1, -0.0114819]; HAC/Holm p=1, bootstrap/Holm p=1. Multiplicity-adjusted evidence under both checks: False. Without retrospective shocks, mean difference=-18100.5; top five dates account for 100.0% of absolute paired loss differences. Inference status: approximate_exploratory.

Incremental performance and risk-share magnitude answer different questions. A material overnight variance share does not by itself imply that lagged overnight features improve forecasts. Holdout and portfolio utility remain untested.