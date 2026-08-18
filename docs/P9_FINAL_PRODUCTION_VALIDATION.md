# P9 — Final Production Validation

P9 is the final engineering gate before any consideration of real-money execution.

## Automated gates

- Backend compile and complete test suite
- Frontend production build
- Docker Compose validation
- Explicit release gate
- Missing CI run is a failure, not a pass

## Trading safety gates

- SIMULATION_ONLY remains the default
- Live order path remains disabled
- Kill switch is fail-closed
- Market-data freshness failure halts paper execution
- Reconciliation failure halts paper execution
- Unsupported broker fails closed
- Sandbox certification cannot authorize live execution

## Strategy evidence gates

- Historical backtest
- Robustness testing
- Walk-forward validation
- Untouched out-of-sample validation
- Cross-stock validation
- Realistic costs and slippage
- Minimum paper sample
- Expectancy/profit-factor quality
- Drawdown and loss-streak limits
- Regime stability
- Strategy fingerprint/parameter stability
- Backtest-vs-paper divergence
- Evidence freshness

## Operational failure-injection matrix

| Failure | Required result |
|---|---|
| Stale data | Halt affected paper execution |
| Missing candle | Halt/mark data unhealthy |
| Out-of-order candle | Reject data |
| Duplicate signal | Idempotent/no duplicate position |
| Duplicate execution request | Idempotent/no duplicate trade |
| Broker timeout/rejection | No unsafe retry; reconcile |
| Restart with open position | Restore/reconcile before continuing |
| Database unavailable | Fail closed |
| Reconciliation mismatch | `HALT_AND_RECONCILE` |
| Kill switch active | No execution |
| Session boundary | No invalid session execution |
| Large gap | Apply execution/risk policy |
| Insufficient liquidity | Apply slippage/participation limits |

## Security gates

- Authentication/authorization on operational APIs
- No secrets in API responses or logs
- No client-controlled live authorization
- Idempotency on execution-sensitive requests
- Audit events retained
- Unsafe broker identifiers rejected
- Production rate limiting and network controls verified

## External blocking gates

These require real deployment/provider access and cannot be fabricated by repository tests:

1. Real broker sandbox credentials and certification.
2. External monitoring/alert destination configuration.
3. Production database backup and restore drill.
4. TLS, reverse proxy, firewall and network verification.
5. Independent review of any proposed live-order implementation.

## Live execution rule

P9 does not enable live trading. A green CI run, profitable backtest, profitable paper account, or broker sandbox certification is never sufficient to authorize real-money orders.

Live execution requires all gates to pass **and** explicit user approval after a separate safety review.
