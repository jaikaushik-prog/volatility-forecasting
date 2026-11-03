# India VIX incremental value — PROVISIONAL

NIFTY validation only. VIX enters as (prior-session EOD percentage / 100)^2, an ANNUALIZED implied-variance regressor. Its coefficient estimates its relationship with the next-session target; it is not divided by 252 and called an observed daily variance. The prior-session shift is additional to origin/target alignment. Missing VIX is never filled. Annualized VIX refers to roughly 30 calendar days, unlike the daily realized target. Method: [Corsi, A Simple Approximate Long-Memory Model of Realized Volatility](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1365738). India VIX units/horizon: [NSE definition](https://www.nseindia.com/static/products-services/indices-indiavix-index).

har_vix versus har: n=226, mean QLIKE difference=125293 (negative favours har_vix); gap-aware bootstrap 95% interval [4195.21, 300559]; HAC/Holm p=1, bootstrap/Holm p=1. Multiplicity-adjusted evidence under both checks: False. Without retrospective shocks, mean difference=128710; top five dates account for 47.5% of absolute paired loss differences. Inference status: approximate_exploratory.

har_vix_overnight versus har_overnight: n=226, mean QLIKE difference=11303.7 (negative favours har_vix_overnight); gap-aware bootstrap 95% interval [-0.708881, 33911.7]; HAC/Holm p=1, bootstrap/Holm p=1. Multiplicity-adjusted evidence under both checks: False. Without retrospective shocks, mean difference=11612; top five dates account for 100.0% of absolute paired loss differences. Inference status: approximate_exploratory.

Secondary overnight-inclusive target:

har_vix versus har: n=226, mean QLIKE difference=118814 (negative favours har_vix); gap-aware bootstrap 95% interval [3375.81, 287147]; HAC/Holm p=1, bootstrap/Holm p=1. Multiplicity-adjusted evidence under both checks: False. Without retrospective shocks, mean difference=122055; top five dates account for 38.7% of absolute paired loss differences. Inference status: approximate_exploratory.

Inspect quarter/regime robustness and adjusted paired evidence before attributing incremental value. No final-holdout evidence or portfolio conclusion is available.