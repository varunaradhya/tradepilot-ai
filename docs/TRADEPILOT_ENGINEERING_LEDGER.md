[object Object]

## 2026-10-01 — Corporate-action provenance control
- Added `backend/app/services/corporate_action_provenance.py` to separate authoritative corporate-action records from the provider's OHLCV adjustment-state attestation.
- Added regression coverage for source metadata, unknown adjustment state, positive factors, symbol/date scoping, and serialization.
- The current Dhan-derived dataset remains NOT CERTIFIED: its intraday adjustment state is not established by the available provider documentation, so the gate continues to require an explicit boolean state.
- No raw market rows were changed, deleted, or adjusted.
