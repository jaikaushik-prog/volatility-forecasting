# Stage 6: next research hypotheses — DESIGN ONLY, NOT BACKTESTED

These four hypotheses were motivated by the 2024 diagnosis. Because 2024 motivated them, **2024 cannot test them**. Nothing here has been simulated. No threshold, lookback, frequency or band below is calibrated; where a number appears, it is a placeholder that a future registration must fix from development data before any evaluation outcome is seen. The rule "do not choose the variant that would have worked best in 2024" applies throughout. Several hypotheses would have fared differently on 2024, and that is deliberately not examined.

## Shared requirements for any successor study

- **Fresh outcome data.** Use either genuinely post-registration sessions, per the frozen protocol's "Obtaining genuinely unseen data" procedure, or long historical samples from markets and periods never used in Stages 2–5 economic work. The 2025–2026 window is not pristine: earlier research exposed some observations. It may serve at most as a disclosed, single-use secondary check, never as primary confirmation.
- **An executable instrument.** Verified adjusted ETF OHLC, corporate actions, closing-auction availability and cost evidence must pass before any economic claim is called executable. Panel A index results stay labelled theoretical.
- **Registration before outcomes.** Configuration, benchmarks, primary metric, sample length, stopping rule and multiplicity family are hashed and timestamped before outcome collection. The frozen forecasting protocol is not amended. Economic studies get their own protocol.
- **Mandatory baselines in every study.** Buy-and-hold; a development-fixed constant allocation; the Stage 5 continuous inverse-volatility rule, unchanged, as the negative control; and a non-deployable ex-post exposure-matched constant, labelled as such.
- **Failure accounting.** Every forecast failure, held position and cash path is retained, and both the hold and to-cash conventions are reported.
- **Holm adjustment across all registered contrasts**, with paired stationary bootstrap including research-selection caveats. Use a pre-declared minimum effect size. "Not significantly worse" is not success.

---

## H1 — Forecasts suit exceptional-risk limits better than continuous inverse-volatility sizing

**Economic mechanism.** Continuous sizing trades on small forecast changes near the cap, which produce turnover and noise, and on persistent post-shock elevation, which produces rebound drag. A limit rule is fully invested unless forecast risk exceeds a high pre-set threshold, then reduces to a fixed floor. It would trade rarely. In principle it acts only in tail states, where volatility clustering is strongest and drawdown avoidance most valuable.

**Critical assessment.** The 2024 evidence cuts against the naive version of H1. 94–119% of EWMA, GARCH and HAR shortfall arose in the exceptional-risk episode after 4 June, when forecasts were 28–33%. Any plausible limit threshold would have fired there too. The mechanism could reduce boundary turnover, which is Inference 5. It does not, by itself, address rebound drag. H1 is worth testing only together with an explicit, pre-registered **exit rule**, for example a fixed maximum de-risking duration or a re-entry condition fixed from development data. That doubles the parameter count.

- **Null hypothesis.** Over the registered sample, the limit rule's net Sharpe is no greater than buy-and-hold's. Its maximum drawdown and expected shortfall are no better than those of a development-fixed constant with equal average exposure.
- **Observable predictions if true.** (a) Turnover is far below continuous sizing. (b) Exposure is at 100% on most sessions. (c) Drawdown and ES95 gains are concentrated in multi-week high-volatility episodes that continue falling after the trigger. (d) There is no material Sharpe loss in reversal episodes relative to buy-and-hold.
- **Required data.** Long daily history with several distinct crisis types: crash-then-continuation (2008), crash-then-V (March 2020), and slow grinds. Use NIFTY TRI pre-2012 if obtainable and verified, SPY and VT from the existing canonical datasets, and at least one further market. Also required: executable ETF data and cost evidence.
- **Necessary benchmarks.** The shared baselines, plus the continuous rule using the same forecast.
- **Main failure modes.** Threshold fires late, after the jump, as on 4 June. Exit rule re-enters after the rebound. Too few trigger events give no power. Trigger frequency is regime-dependent.
- **Risk of overfitting.** High. Threshold, floor and exit rule are three free parameters with very few events per decade. Mitigate by fixing them from economic reasoning or development-only percentiles of forecast volatility, and by evaluating a small pre-declared grid reported in full, not a selected point.
- **Experimental methodology.** Walk-forward forecasts under the frozen model specifications, with a threshold defined as a development-sample percentile of the forecast distribution. Registered across several markets at once. Event-level reporting: each trigger, its timing relative to the drawdown trough, and the re-entry outcome.
- **Independent confirmation requirements.** Replicate the sign of the drawdown benefit in at least two markets not used to motivate H1, with no Sharpe deterioration beyond a pre-declared tolerance. Then a prospective post-registration period. A single crisis episode cannot confirm.

## H2 — A trend or momentum filter combined with volatility targeting reduces rebound drag

**Economic mechanism.** Volatility targeting reacts to variance regardless of direction. 2024 combined a sharp shock followed by a rally, where de-risking was penalized, with a slow low-volatility decline that was not addressed. A trend condition might separate shocks inside uptrends, where de-risking is unnecessary, from deteriorating markets, where it may help. That would let exposure be cut only when both risk and trend are adverse.

**Critical assessment.** The trailing 20-session index return at the start of EWMA's June de-risking spell was −1.5%, so a short-horizon trend filter would have agreed with the cut. Long-horizon filters behave differently. This shows the outcome depends heavily on lookback choice, which is the classic overfitting channel. Trend filters also carry their own whipsaw costs and documented long flat periods. H2 adds a second signal with its own estimation risk on top of an overlay that has not yet shown value alone.

- **Null hypothesis.** The combined rule's net Sharpe and rebound participation are no better than the volatility-only rule's, and its net Sharpe is no better than buy-and-hold's.
- **Observable predictions if true.** Higher rebound participation than volatility-only after shocks in uptrends. Lower exposure during sustained declines. Turnover and whipsaw cost below the gain. The benefit holds across lookbacks within a pre-declared range, not at one lookback.
- **Required data.** Multi-decade daily histories across several equity markets. Trend effects need long samples: at least 20 years per market, ideally more. Executable data and costs are also needed.
- **Necessary benchmarks.** The shared baselines; a pure trend filter without volatility scaling, to isolate the incremental contribution; and the volatility-only rule.
- **Main failure modes.** Lookback chosen on 2024 by implication. Whipsaw in range-bound markets. The trend signal does the work alone and volatility adds nothing. Post-publication decay of trend premia.
- **Risk of overfitting.** Very high. Lookback, combination logic and thresholds are free, and the hypothesis was suggested by a single year's shape.
- **Experimental methodology.** Register a small family of lookbacks taken from the published literature, not tuned. Report every member. Use a factorial design separating trend-only, volatility-only and combined effects. Evaluate in markets and periods untouched by this project.
- **Independent confirmation requirements.** A consistent sign across lookbacks and at least three markets, and a combined-minus-trend-only contrast surviving multiplicity adjustment. Then prospective confirmation.

## H3 — Lower-frequency adjustment reduces implementation cost

**Economic mechanism.** Most turnover in continuous sizing comes from small daily forecast changes, especially oscillation around the cap. Rebalancing weekly or monthly, or only when desired and current weight differ by more than a band, should reduce turnover. It may also mechanically reduce reactive post-shock cuts.

**Critical assessment.** This is the most mechanically grounded hypothesis, because cost reduction from fewer trades is nearly an identity. But the registered Stage 5 weekly variants were already computed and seen on 2024. They roughly halved turnover. That observation is now in-sample and cannot count as evidence. Lower frequency also changes timing, and so confounds cost reduction with the reaction-lag effect that happened to help in 2024. Costs explained only 6–42% of the 2024 shortfall, so H3 at best addresses a secondary cause.

- **Null hypothesis.** Lower-frequency rebalancing does not reduce net implementation drag (cost plus timing slippage relative to the daily rule's zero-cost shadow) relative to daily rebalancing of the same rule.
- **Observable predictions if true.** Turnover falls roughly in proportion to frequency. Cost drag falls. The gross-path difference against daily is small and of unpredictable sign, because the timing effect is noise. Net Sharpe against buy-and-hold is still not assumed to improve.
- **Required data.** Executable instrument data with measured or credibly bounded spread, impact and auction-fill costs. The 5/10/20 bps scenarios are illustrative, not measured.
- **Necessary benchmarks.** The daily rule (same forecast, same target) as primary comparator; buy-and-hold; and constant allocations under the same rebalancing frequency.
- **Main failure modes.** Cost savings are offset by stale exposure during fast markets. Week-boundary effects. Measured costs differ from the scenarios.
- **Risk of overfitting.** Moderate if frequencies and bands are fixed from a small, conventional set (weekly or monthly; one band) before evaluation. High if chosen from Stage 5 results.
- **Experimental methodology.** Paired comparison of frequency variants that share an identical forecast path, isolating implementation from forecasting. Decompose net differences into cost and timing components with the Stage 6 accounting.
- **Independent confirmation requirements.** The cost-component reduction should replicate trivially. The claim requiring confirmation is that timing slippage does not offset it. That needs a prospective sample with real execution evidence.

## H4 — Forecasts add more value in risk monitoring than in active allocation

**Economic mechanism.** A volatility forecast is directly useful for risk measurement: value-at-risk and expected-shortfall limits, margin and exposure budgeting, stress flags and position-limit alerts. None of these needs the forecast to time returns. Stage 5 showed that converting forecasts into exposure introduces cap asymmetry, the reaction lag and return-timing risk, and loses information. Evaluating the forecast as a risk measure tests the property it is designed to have.

**Critical assessment.** This is the hypothesis least exposed to the 2024 overfitting problem. It requires no allocation rule and no return prediction. It is also closest to what the forecasts demonstrably do: calibration near one for EWMA and GARCH, and clustering detection. Its weakness is that "value" in monitoring is harder to monetise and easier to claim vaguely. The study must define a decision-relevant loss in advance: exceedance coverage, ES backtest statistics, or false-alarm and missed-alarm rates at fixed alert thresholds.

- **Null hypothesis.** Model-based one-day 95% and 99% VaR and ES forecasts are no better calibrated than a historical-simulation benchmark. Calibration is assessed by unconditional coverage (Kupiec), independence (Christoffersen) and an ES backtest such as Acerbi–Székely or the Fissler–Ziegel joint loss. Alert-flag precision and recall are no better than a trailing-volatility rule's.
- **Observable predictions if true.** Exceedance rates are near nominal, with no clustering of exceedances. Lower joint VaR–ES loss than historical simulation. Alerts precede, not follow, high-realized-risk weeks at a rate above the benchmark's.
- **Required data.** Daily returns, and optionally verified intraday RV and VIX after provenance sign-off. The same canonical datasets already exist for NIFTY TRI, SPY and VT. No executable instrument is required, since no trading is implied. This is the main practical advantage.
- **Necessary benchmarks.** Historical simulation (250 sessions); a rolling-variance Gaussian rule; EWMA as the low-complexity reference; and an unconditional-volatility constant.
- **Main failure modes.** Distributional misspecification dominates. Gaussian tails under-cover at 99%. Too few 99% exceedances for power within one year. Provenance problems in RV and VIX inputs.
- **Risk of overfitting.** Low to moderate. The frozen forecasting protocol already fixes the model specifications, and VaR/ES tests have standard forms. The residual risk lies in choosing the innovation distribution and alert thresholds, which must be fixed in registration.
- **Experimental methodology.** Prospective, append-only forecast ledger under the existing frozen protocol, with distributional mapping (Gaussian, plus a pre-declared Student-t or filtered historical simulation) registered in advance. Coverage and ES tests per market, Holm-adjusted across the registered family. Report the 99% level with an explicit power analysis. Report alerting as an event table, not a single score.
- **Independent confirmation requirements.** Coverage and independence tests pass in each of NIFTY, SPY and VT over the first 252 post-registration sessions, with no specification change. Model superiority over historical simulation requires a pre-declared joint-loss contrast surviving Holm adjustment.

---

## Summary of the critical assessment

| hypothesis | addresses the dominant 2024 mechanism? | overfitting risk | needs executable data? | needs data the project lacks? |
| --- | --- | --- | --- | --- |
| H1 exceptional-risk limits | Only with an exit rule; the naive version would have fired in the same episode | High | Yes | Yes: multi-crisis, multi-market history |
| H2 trend + volatility | Possibly, but highly lookback-dependent | Very high | Yes | Yes: multi-decade histories |
| H3 lower frequency | No; it targets costs, a secondary cause | Moderate | Yes, with measured costs | Yes: execution and cost evidence |
| H4 risk monitoring | Sidesteps allocation entirely | Low to moderate | No | No: prospective data only |
