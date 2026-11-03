# Research findings — volatility forecasting, Stages 1 and 2

Source run: experiment `econometric`, run `20261103T112009388792Z_e137742e` (see `reports/latest_forecasting.json`,
`reports/model_comparison.md`, `reports/model_metrics.csv`, `reports/statistical_tests.csv`,
`reports/regime_metrics.csv`, `reports/parameter_stability.csv`, `reports/figures/`). Data: canonical audit
`572f825c852d8c0c540a207e` (NIFTY 50 TRI 3,676 usable log returns 2012-01-03..2026-11-02; SPY and VT 3,729 each,
2012-01-04..2026-11-02). All numbers below are walk-forward, one-session-ahead, out-of-sample on the
development (targets 2012–2021) and validation (2022–2024) periods. **The final holdout (2025-01-01..2026-10-30)
is sealed and has not been evaluated.** Unless stated otherwise, results refer to the common-date sample
(sessions on which all ten models have a valid forecast: 2,721 NIFTY, 2,769 SPY, 2,769 VT).

Evaluation target reminder: the realized squared daily log return is an unbiased but very noisy observation of the
latent conditional variance. QLIKE differences of a few hundredths are typical; only the HAC Diebold–Mariano and
block-bootstrap tests (Holm-adjusted within asset and period, nine comparisons against the GARCH(1,1) benchmark)
decide what is meaningful.

## Headline comparison (common dates, development + validation)

QLIKE (lower is better) and rank:

| Model | NIFTY50_TRI | SPY | VT |
|---|---|---|---|
| gjr_normal | -8.4691 (1) | -8.5514 (4) | -8.5563 (2) |
| gjr_t | -8.4683 (2) | -8.5547 (3) | -8.5555 (3) |
| egarch_normal | -8.4665 (3) | -8.5562 (2) | -8.5627 (1) |
| egarch_t | -8.4634 (4) | -8.5660 (1) | -8.4465 (7) |
| garch_normal (benchmark) | -8.4380 (5) | -8.5156 (6) | -8.5297 (5) |
| garch_t | -8.4371 (6) | -8.5181 (5) | -8.5305 (4) |
| ewma_094 | -8.4332 (7) | -8.4537 (7) | -8.4870 (6) |
| rolling_20 | -8.4016 (8) | -8.3686 (8) | -8.4219 (8) |
| rolling_60 | -8.3585 (9) | -8.3459 (9) | -8.3849 (9) |
| expanding | -8.1420 (10) | -8.0064 (10) | -8.0793 (10) |

Calibration ratio (mean realized r² / mean forecast variance; 1 = calibrated, below 1 = over-forecast):

| Model | NIFTY50_TRI | SPY | VT |
|---|---|---|---|
| gjr_normal / gjr_t | 0.95 / 0.97 | 0.93 / 0.88 | 0.91 / 0.93 |
| egarch_normal / egarch_t | 1.14 / 1.15 | 1.12 / 1.06 | 1.08 / 1.10 |
| garch_normal / garch_t | 1.02 / 1.07 | 1.04 / 0.96 | 1.00 / 1.00 |
| ewma_094 | 1.00 | 1.00 | 1.00 |
| rolling_20 / rolling_60 | 1.01 / 1.00 | 0.99 / 1.00 | 1.00 / 1.00 |
| expanding | 1.05 | 1.43 | 1.28 |

Estimation: 152–154 scheduled refits per GARCH model and asset; zero fit failures in the evaluated periods.
The only failures in the whole run are two VT EGARCH-t refits in May and July 2025 (inside the sealed holdout),
which produced an overflow in the log-variance recursion and were recorded as missing forecasts with daily retries.

## A. Which model forecasts best overall?

The asymmetric GARCH models. GJR-GARCH(1,1) ranks first or second on NIFTY and VT and 3rd–4th on SPY; EGARCH(1,1)
ranks first on SPY (Student-t) and VT (Gaussian). The spread among the four asymmetric models is 0.003–0.01 QLIKE on
NIFTY and SPY, far inside the noise: pairwise DM tests between EGARCH and GJR variants have p-values of 0.28–0.79,
so no asymmetric specification is distinguishable from another. The one exception is VT EGARCH-t, which ranks 7th
because of a single degenerate refit (December 2017) whose forecasts collapsed toward 1–2% annualized volatility for
three weeks in January 2018 (daily QLIKE up to 177); its validation-period rank is 1st. Against the GARCH(1,1)
benchmark the asymmetric models are better by 0.025–0.05 QLIKE on every asset, with unadjusted DM p-values of
0.02–0.14 and Holm-adjusted p-values of 0.12–0.44 over the full evaluated sample.

## B. Does model complexity improve accuracy?

Up to a point. Every GARCH-family model beats every historical benchmark on every asset in the full sample, and the
benchmarks' deficit is the only result that survives multiple-testing correction in most cases: rolling-20 is
significantly worse than GARCH(1,1) on all three assets (Holm-adjusted DM and bootstrap p ≤ 0.04), rolling-60 on
SPY, EWMA on SPY, and the expanding variance on all three assets in validation. Beyond GARCH(1,1), the extra
leverage parameter adds a consistent 0.03–0.05 QLIKE improvement; the extra Student-t parameter adds nothing
measurable (see D). The benchmarks are, however, far better calibrated unconditionally (ratios 0.99–1.01) than the
asymmetric models, and EWMA is competitive in calm periods: it ranks 1st on NIFTY in validation (not significantly,
Holm p = 1.0) and is never significantly worse than GARCH(1,1) except on SPY.

## C. Do asymmetric GARCH models outperform symmetric GARCH?

Yes, consistently in sign, marginally in significance. GJR vs GARCH(1,1), Gaussian innovations, full sample:
mean QLIKE difference -0.031 (NIFTY, DM p = 0.034), -0.036 (SPY, p = 0.062), -0.027 (VT, p = 0.063); EGARCH vs
GARCH(1,1): -0.029 (p = 0.077), -0.041 (p = 0.076), -0.033 (p = 0.090). After Holm adjustment none of these is
below 0.05 over the full sample. In the validation period on SPY, EGARCH (both innovations) is significantly better
than GARCH(1,1) even after adjustment (Holm DM p = 0.015 and 0.040, bootstrap p = 0.018 and 0.040); GJR-t on SPY
and VT is close (unadjusted p = 0.02–0.04). The estimated leverage effect is strong and stable: GJR gamma averages
0.15–0.32 while alpha is driven to its zero lower bound in 49–72% of refits (the familiar "all ARCH from negative
returns" result for equity indices), and EGARCH gamma is negative in every refit on every asset.

## D. Are Student-t innovations beneficial?

Not for one-step variance forecasts. GARCH-t vs GARCH-normal: |mean QLIKE difference| ≤ 0.003 on every asset
(DM p = 0.46–0.82); GJR-t vs GJR-normal: ≤ 0.003 (p = 0.54–0.89); EGARCH-t vs EGARCH-normal: -0.003 (NIFTY,
p = 0.09), +0.010 (SPY, p = 0.11), +0.116 (VT, driven by the degenerate episode). The estimated degrees of freedom
(nu ≈ 7–9 on average, minima 4–6) confirm fat tails, but with a zero mean the t-distribution mainly changes the
likelihood weights of extreme observations, not the variance recursion. Student-t variants also cost 30–60% more
runtime, hit the IGARCH boundary more often (SPY GARCH-t: 21 of 154 fits at or near persistence 1) and, for EGARCH on
VT, produced the only pathological fits in the study (nu at its 2.05 lower bound, alpha of -31 to -112, in 2025).

## E. Which models adapt fastest to shocks?

The GJR models. On the 14–20 retrospectively labelled shock sessions per asset (|r| > 4 trailing standard
deviations) the calibration ratio, i.e. how far realized variance exceeded the forecast, is lowest for GJR
(9–10 NIFTY, 3.8–4.0 SPY, 4.4–5.3 VT), then EGARCH (6.4–7.7 on SPY/VT, 17 on NIFTY), GARCH(1,1) (5–15), EWMA
(10–17), rolling-20 (10–18), rolling-60 (24–32) and expanding (36–42). The same ordering holds in the COVID crash
window (20 Feb–30 Apr 2020): GJR 0.94–1.11, GARCH-t 1.06–1.69, GARCH-normal 1.17–1.41, EWMA 1.22–1.33, EGARCH
1.83–3.00, rolling-60 1.9–2.4, expanding 16–19. EGARCH reacts strongly to the first shock day (its QLIKE on shock
sessions is the best on SPY) but its multiplicative recursion then overshoots in the weeks after, which is why its
COVID-window calibration is worse than GJR's. Note that shock sessions are by construction the days when every model
under-forecasts; the comparison is about the size of the miss.

## F. Which models overestimate volatility during recoveries?

All of them, but the asymmetric models most. In the 60 sessions after each shock the calibration ratio is 0.68–0.75
for GJR on SPY/VT (i.e. forecasts about 35–45% above realized variance), 0.76–0.88 for GARCH(1,1), 0.72–0.80 for
EWMA and rolling-20, and 1.03–1.17 for EGARCH on SPY/VT (EGARCH is the exception: it does not over-forecast in
recoveries on average, because it has already mean-reverted). In the named recovery windows (May–Dec 2020 and
calendar 2023) every GARCH-family model over-forecasts (ratios 0.74–0.99), while in the calm 2017 window the whole
GARCH family over-forecasts by 40–45% (ratios 0.55–0.65) against 0.92–0.99 for EWMA and rolling windows. The
expanding variance over-forecasts in calm periods and under-forecasts in crises, which is why it is last everywhere.
Ex-ante regimes (terciles of trailing 60-session variance, known at the origin) show the same pattern: in the low
regime the GARCH family ratios are 0.91–1.02 while rolling/EWMA sit at 1.2–1.5 (they under-forecast calm markets);
in the high regime GJR is 0.88–0.94 and EGARCH 1.1–1.35.

## G. Are results consistent across Indian, US and global equity markets?

Largely. The ordering historical < GARCH(1,1) ≈ GARCH-t < asymmetric GARCH holds on all three assets in the full
sample and the development period. Differences: (i) NIFTY's gains from asymmetry are the most significant in
development (GJR Holm DM p = 0.04–0.06) and vanish in validation 2022–2024, where EWMA is nominally best and all
GARCH variants are within 0.01 QLIKE of each other; (ii) SPY shows the clearest validation-period advantage for
EGARCH; (iii) VT behaves like SPY except for the EGARCH-t instability. Volatility levels and persistence are similar
(mean persistence 0.93–0.98), and the leverage parameter is larger on SPY/VT (GJR gamma 0.22–0.32) than on NIFTY
(0.15–0.16). The loss values are not pooled across assets: NIFTY QLIKE levels differ because its variance level and
sample differ, and all comparisons are within asset.

## H. Are improvements statistically meaningful?

Only some. With Holm adjustment at 5%: rolling-20 is significantly worse than GARCH(1,1) on all assets; rolling-60
and EWMA on SPY; the expanding variance in validation on all assets; EGARCH (normal and t) is significantly better
than GARCH(1,1) on SPY in validation. Everything else, including every asymmetric-vs-symmetric and every t-vs-normal
comparison over the full sample, is not significant after adjustment, although the asymmetric improvements have the
same sign on all three assets and in both periods for SPY and VT. The bootstrap and HAC p-values agree closely. The
practical reading: the asymmetric models are the best point estimate, the gain over GARCH(1,1) is real in sign but
small relative to proxy noise, and nothing distinguishes GJR from EGARCH or Gaussian from Student-t.

## I. Which models should advance to the portfolio position-sizing study?

Recommended: **gjr_normal** (best or near-best everywhere, fastest to shocks, no failures, cheapest asymmetric model),
**egarch_normal** (best on SPY/VT in validation, complementary recovery behaviour), **garch_normal** as the
econometric reference, and **ewma_094** as the required practitioner benchmark (well calibrated, never a fit
failure, competitive in calm regimes). Student-t variants add runtime and instability without forecast gains and can
be dropped from the sizing study; EGARCH-t in particular should not be used on VT without a variance floor.
Rolling and expanding variances are retained only as sanity benchmarks. Position sizing will need the calibration
findings: asymmetric models over-forecast by 10–15% unconditionally and by 30–45% after shocks, so volatility
targets based on them would be conservative in recoveries.

## Diagnostics worth noting

- Parameter stability: persistence standard deviations across refits are 0.02–0.05; the largest single refit jumps
  (0.10–0.15) occur in NIFTY GARCH(1,1) during 2020. GJR alpha sits at zero in half to three quarters of refits.
- IGARCH boundary: SPY GARCH-t landed exactly on persistence 1 in 16 refits (2019–2021) and within 0.001 of it in 5
  more; these are flagged, kept, and tested. Constraint overshoots by less than 1e-6 (GJR on SPY/VT) carry the same
  flag; anything larger would be a fit failure, and none occurred.
- Invalid-forecast bounds (0.1%–500% annualized) were never triggered in the evaluated periods; the VT EGARCH-t
  collapse in January 2018 stayed inside them, so it is reflected in the losses rather than hidden.
- Runtime: 0.7 s (rolling/expanding), 5 s (EWMA, re-estimated daily) and 3.3–7.5 s per GARCH model and asset for
  the full sample with 21-session refits; the whole experiment runs in about 2.5 minutes with four workers.

## Unresolved modelling and data issues

1. EGARCH with Student-t innovations is numerically fragile on VT (degenerate fits with nu at its lower bound and
   unbounded alpha). Options: tighter parameter bounds, a floor on daily variance, or dropping EGARCH-t.
2. The benchmark EWMA is initialized with the sample variance of the first 252 returns; its first-year forecasts
   therefore depend on that initialization (negligible after ~100 sessions).
3. The shock and recovery labels are retrospective and few (14–20 shock sessions per asset); the regime tables are
   descriptive and no significance is claimed for them.
4. Only daily closes exist: realized-variance models (HAR-RV, Realized GARCH) remain pending; no options data
   exists, so Heston is not implemented (see `experiments/advanced/README.md`).
5. NSE 2014-04-24 remains an unverified calendar date in the audit; it does not affect any return used here.
6. The 2026 sample is partial (through 2026-11-02) and inside the sealed holdout.

## Recommendations for Stage 3

- Implement the two-state Markov-switching model and the XGBoost challenger against the four models above, using
  the development period for tuning and the validation period for selection; keep the holdout sealed.
- Give the XGBoost challenger the GJR and EGARCH forecasts as candidate features only if they are computed
  strictly from information through the origin (they are, by construction of the engine).
- Add a model confidence set (Hansen–Lunde–Nason) to the comparison; the current Holm correction is conservative.
- Consider a second benchmark set with the 21-session refit replaced by daily refits for one GARCH model to
  quantify the cost of the re-estimation schedule.
