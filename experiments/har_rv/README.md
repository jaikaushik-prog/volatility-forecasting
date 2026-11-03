# Stage 4: provisional HAR-RV research

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m volrisk.har_cli --config config/har_rv.toml run
```

Uses existing audited intraday artifacts, with an additional full-session VIX lag.
Five fixed HAR specifications plus realized benchmarks; GARCH comparisons use a separate
spot close-to-close target. Development: 2022–2023; validation: 2024; 2025–2026 sealed.
NIFTY spot identity/source NSE were user-confirmed; timestamp/export conventions remain
unverified. All empirical findings are PROVISIONAL. Synthetic tests are not research results.

The full protocol, eligibility rules, floor/smearing assumptions and outputs are documented
in the root README and `config/har_rv.toml`. No portfolio or trading research is run here.
