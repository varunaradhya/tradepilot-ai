[object Object]

## 2026-10-01 — CI JWT warning cleanup
- CI backend/deployment test JWT placeholders were lengthened to satisfy the HS256 minimum recommended key length.
- This removes an avoidable `InsecureKeyLengthWarning` from CI without weakening production secret enforcement.


## 2026-10-01 — Recovery validation and CI runtime maintenance
- CI run #1781 passed all release-gate jobs.
- Backend verification: 862 passed, 1 skipped, 4 warnings.
- PostgreSQL migration upgrade/downgrade/re-upgrade passed.
- Backup/restore drill now validates restored data, upgrades the restored database to Alembic head, and smoke-tests `/health` and `/ready` against the restored PostgreSQL database.
- GitHub Actions runtimes were upgraded to checkout v5, setup-python v7, and setup-node v7; the prior Node 20 action-runtime deprecation warning is no longer part of the CI maintenance target.


## 2026-10-01 — Premium portfolio/product UX batch
- Reworked the Portfolio workspace into the shared TradePilot premium dark visual system.
- Added portfolio analytics KPIs for current value, deployed capital, unrealized P&L, total return, realized P&L, performer leaders and market-data availability.
- Added position intelligence filtering, quote-status indicators, responsive holdings tables, refresh state, premium add/edit/remove workflow and clearer paper-execution boundaries.
- Fixed frontend request cancellation semantics so the global timeout remains active even when a caller supplies an AbortSignal; caller cancellation now aborts the same request controller.
- No live-trading execution was enabled by this product UX work.
- The next product batches remain focused on connecting the existing Market → Strategy → Risk → Decision → Paper Trading workflow and broker read-only architecture rather than reopening completed research-certification work.
