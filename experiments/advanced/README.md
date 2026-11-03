# Advanced experiment: Stage 3 implemented; Stage 4 pending

Stage 3 runs two-state Markov switching and XGBoost alongside all ten Stage 1/2 models.
See the root README for setup, methodological details and the earlier holdout-exposure limitation.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,ml]"
.\.venv\Scripts\python.exe -m volrisk.forecast_cli --config config/forecasting.toml run --experiment advanced --workers 4
.\.venv\Scripts\python.exe scripts/verify_advanced_outputs.py
```

## Stage 3 models

Markov switching uses zero-mean Gaussian returns, two state variances, a past-only 1000-session
window (minimum 500), two deterministic optimizer starts and 21-session refits. Forecasting propagates
filtered probabilities through the fitted transition matrix; incremental Hamilton filtering updates
between refits. Sorting states by variance handles label switching. Near-boundary transitions, weak
occupancy/separation and optimizer failures are visible in fit diagnostics. Smoothed states never
enter forecasts; EM initialization may smooth inside the permissible training window only.

XGBoost uses causal squared/absolute returns, rolling sample variances, EWMA, negative-return
indicators, variance differences and log drawdown. It predicts the conditional mean of squared
next-session log returns with Tweedie regression, power 1.5 and a log link. This supports zero targets
and avoids retransformation bias from naive log-target exponentiation. Targets are scaled by 10,000;
positive forecasts are converted back and an explicit numerical floor is tracked. Invalid values
fail rather than being replaced. Up to 1500 known labelled pairs, minimum 500 history observations,
21-session weight refits, three prespecified candidates, two chronological development-only folds,
fixed CPU seeds and independent per-asset selection control cost and leakage. Hyperparameters freeze
after development. Split gain is model importance, not causal evidence.

Outputs are immutable `runs/<run_id>/` directories plus `reports/latest_advanced.json`. All forecasts
and fits are preserved, with common-date evaluation flags, source/config/code/output hashes,
package versions and seeds. Runtime fields are nondeterministic. Published advanced reports and
figures do not overwrite Stage 2 publications. Default modeling stops before 2025; the old Stage 2
runner had already exposed holdout diagnostics, so a genuinely fresh final confirmation remains needed.
NIFTY's calendar-unverified interval breaks history; all comparators are rerun under that policy.

## Stage 4: interfaces and specifications only

### Latent stochastic volatility

Log-SV: `x_t = mu + phi*(x_(t-1)-mu) + sigma_eta*eta_t`, `r_t = exp(x_t/2)*eps_t`.
Daily returns suffice for a physical-measure model. Planned estimators include QML filtering or
particle methods; forecasts must integrate the filtered latent state and lognormal uncertainty.
No estimator or empirical results are implemented here.

### Heston: NOT IMPLEMENTED

Requires historical point-in-time options surfaces, maturities, strikes, rates, dividends, quality
controls and an explicit physical-measure estimation/link. Risk-neutral option calibration is not
a physical conditional variance forecast: a variance risk premium separates them. No suitable
options surface archive exists in this repository. Potential sources to assess include Cboe DataShop,
OptionMetrics IvyDB and NSE licensed options history. Availability, coverage and licensing need
verification before use. No calibration data or fake Heston approximation is provided.

### HAR-RV and Realized GARCH: pending

Require suitable intraday observations or defensible realized measures, with microstructure noise,
overnight returns, timestamps and sessions handled consistently. The validated forecasting inputs
are daily closes. Additional NIFTY/SENSEX minute-price and India VIX raw files are present but have
not been audited or used in Stage 3. The legacy filename-based `data-check` is not a schema validation;
in particular VIX OHLC is not an options surface. For the current daily-only forecasting inputs,
squared daily returns do not carry the information of intraday realized variance and are not relabelled
HAR-RV. Candidate sources to investigate include exchange-licensed intraday data, TAQ and LSEG Tick
History. Data access/coverage must be verified before implementation.

### LSTM and temporal Transformer: future research

Causal sequence features, development-only time-series tuning, frozen final holdout, positive variance
outputs and training-cost controls are prerequisites. Neither model is implemented or run.

Stage 3 stops at forecasting. No position sizing, trading strategy or portfolio optimization.
