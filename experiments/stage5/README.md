# Stage 5 economic experiment

Separate PROVISIONAL, EXPLORATORY research. The existing prospective forecasting
protocol is preserved. No numerical dataset observations after 2024 are read.
An incidental pre-existing-report exposure is disclosed in registration.json.

The registered empirical panel uses official NIFTY 50 TRI, a NON-EXECUTABLE gross
total-return index. It is not an ETF performance claim. Panel B and executable
ETF economics remain blocked by adjusted source/execution verification.

Run from the repository root:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-stage5.xml
.\.venv\Scripts\python.exe -m volrisk.stage5_cli --config config/stage5.toml register
.\.venv\Scripts\python.exe -m volrisk.stage5_cli --config config/stage5.toml run
```

Registration fixes the economic configurations before new economic results.
Horizon2 predicts the daily interval following next-close execution. Horizon3
is used for an additional execution-session delay. Direct daily-target HAR
models reuse existing estimators but are new economic specifications.

Each run archives bounded inputs, a forecast-creation JSONL ledger without
future outcomes, evaluated forecasts, entry events, net and zero-cost-shadow
position ledgers, policies, development-only benchmark calibration, paired
uncertainty, P&L attribution, reports, figures and hashes. A completed run is
verified and reused on identical inputs/code/config. No final liquidation is
assumed. All costs and cash rates are explicit scenarios. No broker connection
or live execution function is present.

The optional acquisition scripts `scripts/acquire_stage5_data.py` and
`scripts/check_stage5_exchange.py` preserve source downloads without modification.
They are not called by the experiment and their ETF data is not used in the
theoretical portfolio results. The exchange check has eight fixed 2023–2024 dates.
