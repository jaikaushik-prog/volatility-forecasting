# Project brief — Volatility Forecasting and Risk-Managed Position Sizing

The original brief, as issued at project start. Status against each item is in [`RESEARCH_HANDOVER.md`](../RESEARCH_HANDOVER.md).

| | |
| --- | --- |
| Markets | Indian equities, US ETFs, global ETFs |
| Priority | Very high |
| Difficulty | Medium |
| Duration | 3–5 sprints |
| Point of contact | Jai Kaushik |

## Executive description

Test whether better forecasts of portfolio volatility and adaptive sizing reduce drawdowns and improve risk-adjusted results without simply hiding a permanent reduction in market exposure.

## Mechanism / rationale

Financial returns exhibit volatility clustering. If current volatility forecasts future risk more reliably than future return, decreasing exposure in high-risk states can stabilize a portfolio, though it may cause whipsaw and missed rebounds.

## Falsifiable research hypothesis

A strictly lagged forecast of next-period volatility using EWMA or GARCH produces better calibrated risk estimates than a constant-volatility baseline. Bounded inverse-volatility sizing improves a strategy's downside profile when returns are compared at matched average exposure.

## Minimum viable data

Daily total-return index/ETF series and, if applicable, portfolio returns from an existing NEXUS strategy, risk-free or cash return, transaction-cost assumptions. No tick data is needed for a first study.

## Experiment design

1. Compare historical standard deviation, 20/60-day rolling volatility, EWMA and GARCH(1,1) with training windows ending before each forecast.
2. Evaluate one-step or multi-day conditional volatility forecasts with walk-forward estimation; compare calibration rather than in-sample fit.
3. Set an ex-ante target risk and define exposure = target volatility / forecast volatility, subject to strict 0–100% long-only bounds or a lower agreed cap.
4. Compare unscaled strategy, constant reduced allocation and dynamic sizing at comparable average exposure, using next-period weights and costs.
5. Stress-test fast drawdowns, sharp rebounds, volatility-model breaks and frequent rebalance effects.

## Evaluation and decision

**Measures.** Forecast error (QLIKE and squared error), volatility calibration, realized portfolio volatility, worst drawdown, turnover, cash drag, return at matched volatility, net Sharpe and tail losses.

**Main failure modes.** Using realized future volatility in sizing; reporting higher Sharpe solely because average exposure dropped; uncapped leverage; optimization on the same crisis; insufficient warm-up history.

**Go / no-go standard.** Advance if the volatility forecasts outperform simple baselines and dynamic sizing reliably improves risk at comparable opportunity cost. Accept as a successful forecasting research result even if the overlay is not worthwhile.

**Deployment route.** Potential overlay for approved Indian long-only portfolios; cannot bypass strategy approval.

## Potential second phase

Measure whether a combined momentum + volatility overlay would have altered the failure profile of NEXUS's previous live strategy.

## Suggested starting literature

- Moreira & Muir (2017), *Volatility-Managed Portfolios*: https://www.nber.org/papers/w22208
- Barroso & Santa-Clara (2015), *Momentum has its moments*: https://doi.org/10.1016/j.jfineco.2014.11.010
