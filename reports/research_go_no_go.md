# Stage 6: research go / no-go decision

**Decision date:** 2026-11-03. **Basis:** the Stage 6 retrospective diagnosis of Stage 5 run `dc64d101044366e3c892ea30` (NIFTY 50 TRI, 2024, theoretical and non-executable). **Status:** EXPLORATORY.

These decisions rest on mechanism, data feasibility and overfitting exposure. **None was made by comparing which rule would have performed best in 2024**, and no new rule was simulated to inform them.

## Live deployment

**NO-GO.** No volatility-targeting overlay, and no rule derived from this research, is justified for live capital. All five primary overlays underperformed buy-and-hold on net and gross Sharpe. None of the 15 formal contrasts favours a dynamic policy. The instrument is a non-executable index, Panel B is blocked, and 2024 is a repeatedly inspected sample.

## Continuous inverse-volatility sizing (Stage 5 primary rule)

**Do not advance as a candidate overlay. Retain it as the negative-control baseline** in every successor study, unchanged. The Stage 5 result is recorded as a provisional negative finding. It is not a general refutation, because it rests on one year with one dominant episode.

## Hypothesis decisions

| hypothesis | decision | reason | precondition before any test |
| --- | --- | --- | --- |
| **H4** forecasts for risk monitoring | **Advance to new independent research** | Lowest overfitting risk. Uses the frozen forecast specifications. Needs no executable instrument and no return timing. Testable prospectively with existing canonical datasets | Register a VaR/ES monitoring protocol (distribution mapping, coverage, independence and ES tests, alert thresholds, Holm family, 252-session window) before any new outcome is collected |
| **H3** lower-frequency adjustment | **Remain exploratory** | Mechanism is sound for costs, but costs were a secondary cause. The only existing evidence (Stage 5 weekly variants) is in-sample | Verified executable instrument and measured cost evidence; frequency and band fixed from a conventional set before outcomes |
| **H1** exceptional-risk limits | **Defer pending data** | The naive version would have fired in the same 2024 episode that caused the losses. A credible design needs an exit rule and multi-crisis evidence the project does not hold | Multi-market, multi-decade verified daily history including crash-continuation and crash-reversal episodes; executable data |
| **H2** trend filter plus volatility | **Defer pending data** | Plausible mechanism, but outcome is highly lookback-dependent and was suggested by one year's shape. Highest overfitting risk | Multi-decade, multi-market data; lookbacks fixed from the published literature; factorial design isolating the volatility contribution |
| Any variant chosen from the 221 saved Stage 5 paths | **Reject** | Selecting from inspected 2024 results is model selection on the evaluation sample | None. Not eligible |

No hypothesis is rejected outright on its merits. H1 and H2 are deferred, not rejected, because the data needed to test them do not yet exist in verified form.

## Recommended next research direction

1. **Data remediation first, as a gating step.** Resolve the provenance items already listed in the frozen forecasting protocol: vendor and export chain, timezone, bar conventions and VIX availability. Complete the executable ETF dataset: adjusted OHLC, the full corporate-action record, closing-auction availability and a cost evidence base. Every economic hypothesis except H4 is blocked on this.
2. **Register and run H4 prospectively.** It requires no new modelling and can begin collecting genuinely new sessions immediately after registration. It directly tests whether the forecasting work has decision value without routing it through an allocation rule.
3. **Assemble an independent multi-market historical panel** for H1 and H2: SPY and VT from the existing canonical data, plus a verified longer NIFTY history and one further market. Freeze its use for economic work before any economic statistic is computed on it.
4. **Keep the frozen forecasting protocol untouched.** Stage 6 findings about economic value do not justify any change to forecast model specifications, penalties or candidates.

## Evidence and uncertainty supporting the decision

| finding | magnitude | confidence |
| --- | --- | --- |
| Missed upside exceeded avoided losses | 1.7–3.0× across models | Exact accounting |
| Shortfall concentrated after 4 June 2024 | 62–119% of allocation effect | Exact accounting; implies low effective sample size |
| De-risking took effect after the main loss | Two-session structural lag; ≥91% exposure on every shock session | Structural |
| Costs not the primary cause | Zero-cost shadows also underperform; costs 6–42% of shortfall | Exact accounting |
| Forecast accuracy unrelated to allocation value | QLIKE vs net Sharpe Spearman 0.10, n = 5 | Descriptive only |
| Realized volatility exceeded target due to cap and one jump | Excluding 4 June, 11.5–12.4% | Exact accounting |
| Dynamic underperformance statistically flagged | 3 of 15 contrasts after Holm, all against Log-HAR+VIX | Conditional bootstrap; ignores selection uncertainty |

## What Stage 6 did not do

No trades were executed and no allocation rule was optimized or simulated. No frozen forecasting protocol, prior configuration or prior result was modified; all Stage 5 outputs were hash-verified before and after. No 2025–2026 observation was read. No successful overlay is claimed.

**Stage 6 stops here.** Any next step requires a new, separately registered protocol.
