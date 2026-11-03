# Stage 4B: exploratory VIX specification research

This workflow reads only the immutable, pre-2025 NIFTY 5-minute panel saved by Stage 4.
It never opens the original minute files, numerical 2025–2026 data, or a pickle.
The source run is pinned in `config/stage4b.toml`.

`stage4_code_snapshot/` preserves the 56 original Stage 4 implementation files and their
hashes before extension. `runs/<content_hash>/` stores the separate Stage 4B registration,
code snapshot, development-only Ridge search, final forecasts, coefficients, diagnostics,
reports and output hashes. Nothing is written inside a historical Stage 4 run.

The current engine adds optional feature-building and forecast-emission boundaries;
default Stage 4 behavior is covered by exact forecast/coefficient reproduction.
The original source-hash verifier intentionally detects edited implementation files;
use `scripts/verify_stage4b_outputs.py` to check both the preserved historical snapshot
and the new implementation/output hashes.

2024 informed the choice of these new specifications. Holm-adjusted results on that same
sample remain exploratory. The frozen prospective protocol requires new data collected
after provenance sign-off and registration; this workflow does not acquire or evaluate it.
