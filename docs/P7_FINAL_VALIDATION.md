# P7 — Final Trading-System Validation

## Objective

P7 is a validation and attack phase, not a feature expansion phase. The objective is to prove that the existing intraday paper-trading system remains deterministic, evidence-gated, fail-closed and incapable of placing live orders.

## Validation gates

| Gate | Status | Evidence |
|---|---|---|
| Live execution capability disabled for every registered broker | IMPLEMENTED | `backend/tests/test_p7_final_safety.py` |
| Sandbox certification can never authorize live execution | IMPLEMENTED | `backend/tests/test_p7_final_safety.py` |
| Unknown broker certification fails closed | IMPLEMENTED | `backend/tests/test_p7_final_safety.py` |
| Broker capability contract has no live-order enablement | IMPLEMENTED | `backend/tests/test_p7_final_safety.py` |
| Existing P1–P6 regression suites retained | REQUIRED CI GATE | Repository CI |
| Backend compile/tests | REQUIRED CI GATE | `.github/workflows/ci.yml` |
| Frontend production build | REQUIRED CI GATE | `.github/workflows/ci.yml` |
| Docker Compose configuration validation | REQUIRED CI GATE | `.github/workflows/ci.yml` |
| Real broker sandbox connectivity | ENVIRONMENTAL | Requires controlled provider credentials |
| Production monitoring/alerts | ENVIRONMENTAL | Deployment configuration |
| Independent live-execution safety review | BLOCKING | Required before any live-order work |

## Attack scenarios to execute in CI/deployment

1. Unknown broker name → certification must fail closed.
2. Provider adapter advertises a live-order capability → certification must fail.
3. Broker capability metadata attempts to enable live orders → capability gate must remain false.
4. Kill switch active → paper operations remain halted.
5. Market-data timestamp missing, stale or in the future → health gate remains unhealthy.
6. Paper ledger/state mismatch → reconciliation gate remains blocking.
7. Strategy evidence below qualification thresholds → strategy readiness remains blocked.
8. Backtest/paper divergence beyond configured limits → promotion remains blocked.
9. Invalid or missing sandbox credentials → no secret values exposed and no trading authority granted.
10. Production configuration attempts to enable live execution → safety layer remains disabled.

## Release rule

P7 is complete only when backend tests, frontend build and deployment configuration checks are green in GitHub Actions and the safety regression suite remains green. A missing CI run is not equivalent to a passing CI run.

## Trading progression

Historical backtest → robustness/walk-forward → paper trading → paper evidence → strategy readiness → production safety → broker sandbox/read-only certification → independent safety review → **future live-trading decision**.

No P7 change removes the existing live-trading lock.
