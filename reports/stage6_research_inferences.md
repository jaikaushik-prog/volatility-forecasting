# Stage 6: research inferences — EXPLORATORY / RETROSPECTIVE

This report interprets the accounting in `stage6_failure_analysis.md`. It separates what the saved Stage 5 paths show from what they suggest. Every causal statement here is a hypothesis about mechanism, derived from one repeatedly inspected year (2024) of one theoretical, non-executable index (NIFTY 50 TRI). None is a confirmed finding, and none is grounds for deployment.

## Evidence hierarchy used here

1. **Accounting identities.** These are exact and reproducible: the terminal-wealth decomposition, cap-binding fractions and variance shares.
2. **Structural facts of the registered design.** These hold by construction: the two-session reaction lag, the 100% cap and the hold-on-failure rule.
3. **Descriptive associations.** These come from n = 5 models and 248 sessions: forecast rank against economic rank, and exposure against return correlation.
4. **Mechanistic interpretations.** These are hypotheses, and they are labelled as such below.

## Inference 1 — The failure was a rebound-timing failure, concentrated in one episode

*Evidence (levels 1–2).* Missed upside exceeded avoided losses by 1.7–3.0× for every model. Within 60 sessions after the 4 June 2024 election-result shock, the allocation effect equals 62–119% of the full-year total. Every model held at least 91% equity on each of the four shock sessions. Exposure fell only after the loss, by construction of the next-close timing.

*Interpretation (level 4).* Inverse-volatility sizing on daily close-to-close forecasts reacts to realized shocks. In a market that reverses after large moves (2024 lag-1 autocorrelation −0.17), a reactive cut lands on the rebound. The cost then scales with how long forecasts stay elevated: EWMA 61 sessions above 12%, GARCH 29, the log-HAR models 3–7. That ordering matches the ordering of missed rebound.

*Uncertainty.* This is one event. Whether post-shock reversal is a stable property of NIFTY, or of the 2024 political-event shock specifically, cannot be told from these data. A crash followed by a further decline, as in 2008 or March 2020, would reward the same reaction. The literature on volatility-managed portfolios reports exactly this dependence on drawdown shape.

## Inference 2 — Forecast accuracy and allocation value are different estimands

*Evidence (level 3).* QLIKE rank and net-Sharpe rank were essentially unrelated (Spearman 0.10). Mean exposure and net Sharpe were strongly related (Spearman 0.90). The two best economic paths came from the two most under-biased forecasts, with realized-to-forecast ratios of 1.39 and 1.58.

*Interpretation (level 4).* With a 100% cap, a forecast that is biased low acts as a "stay invested" prior. In a rising year it is economically rewarded however poor its loss score. QLIKE scores a variance forecast symmetrically in log space. The policy's payoff is asymmetric: over-forecasting cuts exposure, under-forecasting is truncated by the cap. A forecast can therefore improve QLIKE and worsen allocation.

*Uncertainty.* Five correlated models in one year cannot establish that accuracy is irrelevant. They establish only that the Stage 5 data contain no evidence that accuracy improvements translated into allocation value.

## Inference 3 — Model complexity bought less de-risking, not better timing

*Evidence (level 1–3).* Same-exposure timing Sharpe was negative for all five models, before costs (−0.09 to −0.44) and after (−0.16 to −0.47). The more complex HAR-family models lost less mainly because they held 94–98% equity on average. EWMA and GARCH held 89–90%.

*Interpretation.* There is no evidence in 2024 that richer volatility models add allocation skill under continuous inverse-volatility sizing. The apparent ranking by complexity mostly reflects how close each model stayed to buy-and-hold.

## Inference 4 — The 12% target was not a reachable average under the design

*Evidence (level 1–2).* The cap bound on 39–78% of sessions, and those capped sessions supplied 53–86% of portfolio variance. Excluding the single 4 June session, dynamic portfolios realized 11.5–12.4%. Uncapped sessions realized 10.4–12.5%.

*Interpretation.* The overshoot is mainly two things: the unlevered cap in calm-but-underestimated states, and one jump that arrived after the decision. It is not evidence that the sizing arithmetic failed. A long-only target sized for an asset with about 14% volatility binds most of the time and acts only as a one-sided de-risking trigger. Its economic function is closer to "cut when forecast risk is high" than to "hold constant risk".

## Inference 5 — Costs are a second-order cause, and turnover reflects boundary noise

*Evidence (level 1).* Zero-cost shadows also underperformed buy-and-hold for all five models. Costs account for 6–14% of the shortfall for EWMA, GARCH and HAR, and 29–42% for the two log models. Log-HAR turnover reached 12.6× a year through 29 short below-cap spells.

*Interpretation.* Removing costs would not have rescued any policy in 2024. Turnover concentrates where forecasts oscillate around the target-implied threshold. That is a property of continuous sizing near a cap. It is a specific target for H3 (lower-frequency adjustment) and for hysteresis designs, not evidence for them.

## Inference 6 — Availability failures and delay were not the cause, but expose design fragility

*Evidence (level 1–2).* The 22 HAR missing-predictor sessions cost 0.00 pp under the hold rule, because exposure was already at 100%. The registered failure-to-cash stress cost 2.9–3.0 pp. The one-session-delay stress improved every model by 0.56–1.41 pp.

*Interpretation.* The economic result depends on a failure convention whose effect was zero only by coincidence of starting state. Delay helping is consistent with Inference 1, since slower reaction gives more rebound participation. It must not be read as an argument for slower signals; that would be a rule chosen on 2024.

## Inference 7 — Benchmark fairness does not rescue the overlays

Development-matched constants were 96–100% equity because the calibration window was calm. They did not remain matched in 2024. Ex-post constants with the same 2024 exposure or volatility beat every dynamic path on Sharpe by 0.16–0.47, but they are non-deployable. Because constant-allocation Sharpe is nearly weight-invariant under a 0% cash return, the Sharpe conclusion holds against either benchmark family. The conclusion is that 2024 dynamic de-risking delivered less risk-adjusted return than static de-risking of the same size. It is not that volatility forecasts are useless.

## Limits on every inference

- **One year, one market, one dominant episode.** Effective sample size for "timing after shocks" is four events, one of them dominant.
- **Repeated inspection.** 2024 was examined across Stages 3–5. Any hypothesis motivated here is fitted to its features and must be tested on data that played no part in its formulation.
- **Theoretical instrument.** Index accounting excludes ETF tracking error, fees, closing-auction fill risk and taxes. Panel B (executable ETF) remains blocked.
- **Provenance.** RV and VIX inputs for the HAR models carry unresolved vendor, timezone and bar-convention questions.
- **Literature context, not verified in this session.** Published work on volatility-managed portfolios reports mixed out-of-sample results. Examples include Moreira and Muir (2017), Harvey et al. (2018), Cederburg et al. (2020) and Liu, Tang and Zhou (2019). Benefits are often attributed to fat-tailed crash periods and are sensitive to rebalancing costs and look-ahead. The 2024 NIFTY result is consistent with the sceptical strand. It does not independently test any published claim.
