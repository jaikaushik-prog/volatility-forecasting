# Stage 5: economic value — EXPLORATORY, PROVISIONAL, NON-EXECUTABLE

This is a separate economic study. It does not modify or validate the frozen prospective forecasting protocol. All performance below is hypothetical NIFTY 50 TRI index accounting in INR, not an executed ETF portfolio or realized profits. 2024 has been repeatedly inspected. No 2025–2026 model fitting or economic evaluation occurs.

## Data and execution gates

The official NSE NIFTY 50 gross total-return index passed the existing numerical/source gates. 3220 usable daily observations were read through 2024-12-31; forecasting history begins 2012-01-03. Canonical gaps reset EWMA/GARCH estimation; no missing return is skipped in an economic path. RV/VIX predictors reuse the existing audited pre-2025 panel: 536 complete RV sessions and 541 available conservatively lagged IV observations. NSE spot identity is user-confirmed. Original vendor/export chain, timezone and bar conventions remain unverified. The extra VIX session lag does not resolve provenance.

Panel A is a **theoretical daily total-return-index panel**. Fractional index claims cannot be traded. No management fee, ETF tracking error, tax, securities lending or dividend tax is modeled. **Panel B is BLOCKED**, as is any claimed executable ETF result. The tested next-open accounting primitive is not an empirical intraday backtest.

The bounded Yahoo NIFTYBEES download covers 2012-01-02 through 2024-12-31 (3,210 rows). It contains 35 nonfinite OHLC/adjusted-close cells and 170 zero-volume rows over that history, no recorded actions and Adj Close equal to Close. The [official fund corporate-action history](https://investeasy.nipponindiaim.com/rmfGsamnew/Products/NiftyBeES/CorporateAction.aspx) lists older cash distributions and the 2019 split, also documented by the [June 2022 factsheet](https://mf.nipponindiaim.com/investorservices/factsheetsdocuments/fundamentals-july-2022/Innerpage/ETF-Nifty-BeES.html). Yahoo Close can already be split-adjusted; absent actions do not prove an unadjusted split jump. They do prevent certification of the downloaded history as a fully documented total-return execution dataset.

For 2022–2024, the OHLC cells are finite, but Yahoo omits 2023-11-12, 2024-01-20, 2024-03-02 and 2024-05-18. It reports zero volume on 2024-11-01. Eight NSE archive files were retrieved and preserved unchanged; their NIFTYBEES rows confirm these sessions and nonzero November 1 volume. NSE also agrees with the unusual June 3–5 ETF prices: those moves are not declared errors merely because TRI differs. These partial cross-checks have not certified the complete adjusted series, distributions or executable closing fills. Neither Yahoo prices nor patched ETF prices enter this experiment. No data substitution is hidden.

## Registered models and timing

Five families: daily-return EWMA (lambda .94, initialization252), Gaussian zero-mean GARCH(1,1) (window1000, minimum500, percent scaling converted to decimal variance), new daily-target standard HAR, new daily-target Log-HAR and new daily-target Log-HAR+VIX. HAR uses a 500-session-position window, minimum126 completed training pairs, refit21 sessions, common RV/VIX training masks. Log forecasts use training-only zero-RV handling and residual-smearing retransformation. Levels HAR rejects invalid predictions; there is no tiny-variance floor used to conceal a negative prediction.

The HAR regressions target **NIFTY TRI squared daily log return**, using NIFTY spot RV as an auxiliary predictor, not as the risk target. The basis difference is explicit. These are new Stage 5 specifications, not unchanged Stage 4B candidates. EWMA/GARCH use longer permitted daily history; their estimation sample is not identical to HAR. All regressions use only completed response/predictor pairs.

A forecast issued just after close t executes at close t+1 and first affects the return ending t+2. Therefore primary forecasts are horizon2, a single future daily interval, **not the sum of two days' variance**. HAR is estimated directly at that horizon; GARCH uses its analytical multi-step conditional variance and EWMA its constant expected future variance. Extra-delay sensitivity uses origin t, execution t+2, target t+3. Weekly policies trade on the first native session of each ISO week and hold units between trades; the risk signal remains daily, not a weekly integrated forecast. Exchange special-session close timestamps are retained.

Desired exposure = target annual volatility / sqrt(252 × forecast daily variance), bounded 0–100%, no leverage/shorts. Cash earns an explicit 0% scenario; 4% is a separate illustrative sensitivity, not observed risk-free data. Cash accrues ACT/365. Trades solve for the target fraction of **post-cost** wealth. Old holdings earn the completed return before the close trade. All changes, attempted targets, actual weights, costs and cash are saved. There is no same-close use of an after-close signal. A 5-point band, when specified, compares desired with drifted current weight.

Primary policy:12% target, daily, no band, 10bps per one-way traded notional, missing/invalid forecasts hold existing units. No model substitution or price/forecast filling occurs. Missing forecasts retain subsequent losses in the portfolio path. Forecast failure-to-cash and deterministic every20th signal unavailable are separate stress scenarios. Remaining allocations earn the specified cash scenario.

## Evaluation sample and results

Initial entry is the 2024-01-01 close, using a prior-session signal. All policies have 248 identical native return dates, 2024-01-02 through 2024-12-31. Initial entry cost is included in the first P&L observation. Final holdings are marked at December31 without forced liquidation; prospective exit costs are not included. There are 226 common valid h=2 forecast dates for QLIKE; the economic path retains all 248 dates even when a forecast fails. Complete primary accounting identities reconcile.

The zero-cost shadow is a counterfactual run of the same policy; gross versus net differences include cost compounding. Sharpe uses excess returns over the assumed cash return and 252 sessions. CAGR uses elapsed calendar time and is reported only for at least180 calendar days. ES95 is the mean worst ceil(5%×n) daily returns. Turnover is one-way and includes entry. Drawdown duration counts sessions below the initial-or-running peak; unrecovered drawdowns are explicitly marked. Rebound participation is equity-only upside capture on positive days within10 sessions after a <-2% index day; this is retrospective, not a prospective rule.

| strategy | observations | gross_cumulative_return | net_cumulative_return | net_sharpe | realized_volatility | maximum_drawdown | average_equity_exposure | annualized_one_way_turnover |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| buy_hold | 248 | 0.100359 | 0.0992599 | 0.758518 | 0.139683 | -0.107908 | 1 | 1.01511 |
| constant_60 | 248 | 0.0615186 | 0.0605044 | 0.754164 | 0.0838129 | -0.066006 | 0.6 | 0.97086 |
| ewma_v12_c10_daily_b0 | 248 | 0.0335957 | 0.0283652 | 0.282741 | 0.13096 | -0.107138 | 0.90082 | 5.14726 |
| garch_v12_c10_daily_b0 | 248 | 0.0370399 | 0.0294326 | 0.29269 | 0.129437 | -0.101755 | 0.891236 | 7.47088 |
| har_daily_v12_c10_daily_b0 | 248 | 0.0675961 | 0.0611045 | 0.51286 | 0.135448 | -0.103387 | 0.936941 | 6.2218 |
| log_har_daily_v12_c10_daily_b0 | 248 | 0.0826459 | 0.069309 | 0.572296 | 0.134948 | -0.10224 | 0.957455 | 12.6094 |
| log_har_vix_daily_v12_c10_daily_b0 | 248 | 0.0827069 | 0.0746218 | 0.602403 | 0.137031 | -0.108094 | 0.97654 | 7.63446 |

In this sample, **5 of 5 primary dynamic policies have lower net Sharpe than buy-and-hold**. 5 also have lower zero-cost Sharpe, so trading costs are not the sole explanation. Dynamic average exposure remains 89.1%–97.7%; their maximum drawdowns range from -10.81% to -10.18%, versus -10.79% for buy-and-hold. Some risk reduction is visible, but the primary policies do not establish a superior risk-adjusted overlay.

Illustrative 10bps trading costs reduce primary dynamic terminal returns by 0.52–1.33 percentage points relative to their zero-cost shadows. The attribution shows that reduced exposure on loss days can help while missed recoveries and persistently lower exposure on other positive days offset those benefits. These are retrospective accounting observations, not evidence that a rule anticipated a crisis. The three HAR specifications each retain22 missing-predictor holding sessions; those returns remain in P&L under the hold-units rule rather than disappearing from the sample.

All numbers are decimal units except Sharpe and turnover multiples. Full metrics, all221 predefined economic paths and their zero-cost shadows are archived, plus10 explicitly ex-post fairness diagnostics. No best sensitivity combination is selected. A target volatility is a sizing parameter, not a guaranteed realized portfolio volatility; the 100% cap can prevent attaining it.

## Mandatory fairness checks

The constants below were fixed using only 2023-10-02 through 2023-12-29. The dynamic path in that period is calibration data, not a claimed out-of-sample economic result. Matching solves a bounded scalar allocation problem, including costs and daily rebalancing; unattainable risk is reported instead of using leverage. The calibration sample is short. The constant60 policy is an additional predefined comparison. No exactly full-2024-matched benchmark is passed off as deployable.

| model | criterion | weight | development_observations | development_target | development_match_error | status |
| --- | --- | --- | --- | --- | --- | --- |
| ewma | average_equity_exposure | 0.999855 | 60 | 0.999855 | 0 | matched_development_only |
| ewma | realized_volatility | 0.999942 | 60 | 0.105848 | -2.77556e-16 | matched_development_only |
| garch | average_equity_exposure | 0.961926 | 60 | 0.961926 | -1.11022e-16 | matched_development_only |
| garch | realized_volatility | 0.978087 | 60 | 0.103534 | -1.42324e-12 | matched_development_only |
| har_daily | average_equity_exposure | 1 | 60 | 1 | 0 | matched_development_only |
| har_daily | realized_volatility | 1 | 60 | 0.105854 | 0 | matched_development_only |
| log_har_daily | average_equity_exposure | 0.999906 | 60 | 0.999906 | 1.11022e-16 | matched_development_only |
| log_har_daily | realized_volatility | 0.999963 | 60 | 0.10585 | -1.38778e-16 | matched_development_only |
| log_har_vix_daily | average_equity_exposure | 0.999886 | 60 | 0.999886 | 0 | matched_development_only |
| log_har_vix_daily | realized_volatility | 0.999955 | 60 | 0.105849 | 3.19189e-16 | matched_development_only |

Actual 2024 matched-benchmark risk/exposure need not remain equal:

| model | benchmark | constant_weight | dynamic_net_return | constant_net_return | dynamic_volatility | constant_volatility | dynamic_exposure | constant_exposure | dynamic_drawdown | constant_drawdown |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ewma | development_matched_exposure | 0.999855 | 0.0283652 | 0.0992461 | 0.13096 | 0.139663 | 0.90082 | 0.999855 | -0.107138 | -0.107893 |
| ewma | development_matched_risk | 0.999942 | 0.0283652 | 0.0992544 | 0.13096 | 0.139675 | 0.90082 | 0.999942 | -0.107138 | -0.107902 |
| garch | development_matched_exposure | 0.961926 | 0.0294326 | 0.0956349 | 0.129437 | 0.134365 | 0.891236 | 0.961926 | -0.101755 | -0.10399 |
| garch | development_matched_risk | 0.978087 | 0.0294326 | 0.0971754 | 0.129437 | 0.136623 | 0.891236 | 0.978087 | -0.101755 | -0.105655 |
| har_daily | development_matched_exposure | 1 | 0.0611045 | 0.0992599 | 0.135448 | 0.139683 | 0.936941 | 1 | -0.103387 | -0.107908 |
| har_daily | development_matched_risk | 1 | 0.0611045 | 0.0992599 | 0.135448 | 0.139683 | 0.936941 | 1 | -0.103387 | -0.107908 |
| log_har_daily | development_matched_exposure | 0.999906 | 0.069309 | 0.099251 | 0.134948 | 0.13967 | 0.957455 | 0.999906 | -0.10224 | -0.107899 |
| log_har_daily | development_matched_risk | 0.999963 | 0.069309 | 0.0992563 | 0.134948 | 0.139678 | 0.957455 | 0.999963 | -0.10224 | -0.107904 |
| log_har_vix_daily | development_matched_exposure | 0.999886 | 0.0746218 | 0.099249 | 0.137031 | 0.139667 | 0.97654 | 0.999886 | -0.108094 | -0.107897 |
| log_har_vix_daily | development_matched_risk | 0.999955 | 0.0746218 | 0.0992556 | 0.137031 | 0.139677 | 0.97654 | 0.999955 | -0.108094 | -0.107904 |

### Explicitly ex-post fairness diagnostic

After inspecting the first Stage5 results, an addendum registered10 additional diagnostic constants: each matches full-2024 average exposure or realized net volatility. The original primary run and registration remain preserved. These constants use evaluation outcomes, are **NON-DEPLOYABLE / EX-POST**, and are excluded from the15 formal contrasts. This follows the user's permitted full-sample diagnostic; it is not model selection or independent confirmation. They test whether similar realized risk could have arisen from constant de-risking.

| model | criterion | weight | evaluation_target | evaluation_match_error | matching_sample | deployable |
| --- | --- | --- | --- | --- | --- | --- |
| ewma | average_equity_exposure | 0.90082 | 0.90082 | 2.22045e-16 | EX_POST_EVALUATION_DIAGNOSTIC | False |
| ewma | realized_volatility | 0.937544 | 0.13096 | 5.33185e-14 | EX_POST_EVALUATION_DIAGNOSTIC | False |
| garch | average_equity_exposure | 0.891236 | 0.891236 | 0 | EX_POST_EVALUATION_DIAGNOSTIC | False |
| garch | realized_volatility | 0.92664 | 0.129437 | 7.15816e-14 | EX_POST_EVALUATION_DIAGNOSTIC | False |
| har_daily | average_equity_exposure | 0.936941 | 0.936941 | 1.11022e-16 | EX_POST_EVALUATION_DIAGNOSTIC | False |
| har_daily | realized_volatility | 0.969675 | 0.135448 | 1.32949e-14 | EX_POST_EVALUATION_DIAGNOSTIC | False |
| log_har_daily | average_equity_exposure | 0.957455 | 0.957455 | 2.22045e-16 | EX_POST_EVALUATION_DIAGNOSTIC | False |
| log_har_daily | realized_volatility | 0.9661 | 0.134948 | 1.67366e-14 | EX_POST_EVALUATION_DIAGNOSTIC | False |
| log_har_vix_daily | average_equity_exposure | 0.97654 | 0.97654 | 0 | EX_POST_EVALUATION_DIAGNOSTIC | False |
| log_har_vix_daily | realized_volatility | 0.981015 | 0.137031 | 5.07927e-15 | EX_POST_EVALUATION_DIAGNOSTIC | False |

| strategy | net_cumulative_return | net_sharpe | realized_volatility | maximum_drawdown | average_equity_exposure |
| --- | --- | --- | --- | --- | --- |
| expost_exposure_ewma | 0.0897878 | 0.757439 | 0.12583 | -0.0976717 | 0.90082 |
| expost_risk_ewma | 0.0933062 | 0.757838 | 0.13096 | -0.101474 | 0.937544 |
| expost_exposure_garch | 0.0888675 | 0.757334 | 0.124492 | -0.0966772 | 0.891236 |
| expost_risk_garch | 0.0922629 | 0.75772 | 0.129437 | -0.100346 | 0.92664 |
| expost_exposure_har_daily | 0.0932485 | 0.757832 | 0.130876 | -0.101411 | 0.936941 |
| expost_risk_har_daily | 0.0963739 | 0.758188 | 0.135448 | -0.104789 | 0.969675 |
| expost_exposure_log_har_daily | 0.0952084 | 0.758055 | 0.133741 | -0.103529 | 0.957455 |
| expost_risk_log_har_daily | 0.0960331 | 0.758149 | 0.134948 | -0.104421 | 0.9661 |
| expost_exposure_log_har_vix_daily | 0.097028 | 0.758263 | 0.136406 | -0.105496 | 0.97654 |
| expost_risk_log_har_vix_daily | 0.0974541 | 0.758312 | 0.137031 | -0.105957 | 0.981015 |

## Statistical limitations

Fifteen registered contrasts compare each primary dynamic policy against buy-and-hold, its development-matched exposure constant and its development-matched risk constant. Paired stationary bootstrap uses2,000 draws, mean block10 native sessions, seed20261103. All dates align without dropping failed signals. Sharpe differences have pointwise percentile intervals and centered two-sided bootstrap p-values; Holm adjusts the complete15-test family. 3 contrasts have adjusted p<.05. This is exploratory inference on saved portfolio paths, conditional on estimated models, with no adjustment that can make repeatedly examined 2024 independent. Parameter-estimation and research-selection uncertainty are not re-created by this bootstrap. Small differences, rankings and nonsignificance are not confirmation or equivalence.

| model | benchmark | sharpe_difference | ci_low | ci_high | p_value | holm_p_value |
| --- | --- | --- | --- | --- | --- | --- |
| ewma | buy_hold | -0.475777 | -0.859883 | -0.142746 | 0.009995 | 0.113943 |
| ewma | matched_exposure_ewma | -0.475775 | -0.859881 | -0.142744 | 0.009995 | 0.113943 |
| ewma | matched_risk_ewma | -0.475776 | -0.859882 | -0.142745 | 0.009995 | 0.113943 |
| garch | buy_hold | -0.465828 | -0.842757 | -0.130861 | 0.00949525 | 0.113943 |
| garch | matched_exposure_garch | -0.465414 | -0.842383 | -0.13041 | 0.00949525 | 0.113943 |
| garch | matched_risk_garch | -0.46559 | -0.842542 | -0.130601 | 0.00949525 | 0.113943 |
| har_daily | buy_hold | -0.245658 | -0.53625 | -0.0159389 | 0.0644678 | 0.193403 |
| har_daily | matched_exposure_har_daily | -0.245658 | -0.53625 | -0.0159389 | 0.0644678 | 0.193403 |
| har_daily | matched_risk_har_daily | -0.245658 | -0.53625 | -0.0159389 | 0.0644678 | 0.193403 |
| log_har_daily | buy_hold | -0.186222 | -0.337041 | -0.0248216 | 0.011994 | 0.113943 |
| log_har_daily | matched_exposure_log_har_daily | -0.186221 | -0.33704 | -0.0248204 | 0.011994 | 0.113943 |
| log_har_daily | matched_risk_log_har_daily | -0.186222 | -0.337041 | -0.0248211 | 0.011994 | 0.113943 |
| log_har_vix_daily | buy_hold | -0.156115 | -0.243564 | -0.0716938 | 0.00049975 | 0.00749625 |
| log_har_vix_daily | matched_exposure_log_har_vix_daily | -0.156114 | -0.243563 | -0.0716924 | 0.00049975 | 0.00749625 |
| log_har_vix_daily | matched_risk_log_har_vix_daily | -0.156115 | -0.243564 | -0.0716932 | 0.00049975 | 0.00749625 |

Of the adjusted statistical flags, **0 favor a dynamic policy and 3 indicate underperformance**. Multiple comparisons against nearly identical constants are correlated contrasts, not independent replications. In particular, no statistically flagged improvement supports adopting a dynamic overlay here. These exploratory negative findings also require independent confirmation before generalizing beyond this sample.

## Research integrity and next step

The registration records an inspection incident: a pre-existing review displayed later-period return rows (April2025), full-window audit aggregates and a live search snippet before filtering. This was disclosed. Those values are not Stage5 inputs, features, returns or evaluation results. All numerical dataset reads now enforce the 2024 cutoff. Do not claim no incidental later-period exposure or call the historical holdout pristine. Source bytes are hashed without decoding later numerical observations.

All earlier reports, configurations and experiment artifacts are hash-checked unchanged. Stage5 cannot amend the frozen prospective forecasting protocol. Its old statement excluding portfolio work remains historically intact; the user's new request separately authorizes this economic experiment.

The safe next step is to verify complete investable adjusted OHLC/action history, actual execution/availability conventions, and RV/VIX provenance; then register a **separate economic prospective protocol** with costs, cash and risk constraints fixed before collecting genuinely new outcomes. Do not adopt an overlay for a live portfolio on these results. No trading capability is implemented.

## Reproduction

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-stage5.xml
.\.venv\Scripts\python.exe -m volrisk.stage5_cli --config config/stage5.toml register
.\.venv\Scripts\python.exe -m volrisk.stage5_cli --config config/stage5.toml run
```

The run command uses existing bounded inputs and does not download or ingest data. Completed runs are content-identified, hash-verified and reused; incomplete runs remain for inspection. Package/code/input/config hashes and forecast creation records precede outcome attachment. Plots are in `reports/figures/stage5/`. No2025–2026 evaluation is scheduled.

