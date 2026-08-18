# P7 Adversarial Attack Matrix

| Attack | Expected result | Current protection |
|---|---|---|
| Unknown broker | Reject certification | Fail-closed registry lookup |
| Broker advertises live order capability | Reject certification | Forbidden capability check |
| Provider metadata enables live orders | Still disabled | `live_execution_enabled()` hard false |
| Missing sandbox credential | Not certified | Credential readiness gate |
| Secret present | Value never returned | Secret-safe status contract |
| Kill switch active | Trading operations blocked | Durable fail-safe switch |
| Missing/stale/future market data | Health degraded/block | Freshness watchdog |
| Paper reconciliation mismatch | Operations halt | Reconciliation gate |
| Weak strategy evidence | Promotion blocked | P3 readiness gates |
| Backtest/paper divergence | Promotion blocked | Evidence divergence gate |
| CI unavailable | Release blocked | Explicit release rule |

P7 does not convert any attack into a live-order path. All failures must stop or degrade safely.
