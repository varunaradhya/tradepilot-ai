# P6 Feature Register

| Capability | Status | Safety boundary |
|---|---|---|
| Request telemetry | Complete | Read-only |
| Error-rate/latency SLO snapshot | Complete | Read-only |
| Database readiness signal | Complete | Fail-closed health signal |
| Market-data freshness signal | Complete | Rejects unhealthy state |
| Kill-switch visibility | Complete | Cannot deactivate |
| Sandbox credential readiness | Complete | Never exposes secrets |
| Broker sandbox certification | Complete from P5 | Read-only |
| Live order execution | Disabled | Hard-blocked |
| External metrics/alerting | Deployment follow-up | Not implied by P6 |
| Real provider sandbox connectivity | Deployment follow-up | Requires controlled credentials |
| Independent live-execution review | Required before any future change | Mandatory gate |
