# P6 — Deployment Observability & Broker Sandbox Readiness

P6 adds operational visibility and a safe sandbox credential contract without enabling live trading.

## Operational endpoints

- `GET /api/v1/observability/metrics` — bounded request telemetry.
- `GET /api/v1/observability/slo` — database, market-data, SLO and safety snapshot.
- `GET /api/v1/observability/broker-sandbox/{broker}` — credential readiness only.

## Safety boundaries

- Live execution remains disabled regardless of environment configuration.
- Sandbox credential checks never return secret values.
- Credential readiness does not imply broker connectivity, certification or trading authority.
- Broker sandbox certification remains read-only.
- Kill-switch behavior from P5 remains fail-closed.

## SLO interpretation

`healthy` requires database availability, fresh market data and no request failures in the current telemetry window. `degraded` is an operational signal and must not be interpreted as permission to trade.

## Production follow-up

External metrics/alert delivery, provider-specific sandbox credentials, real sandbox connectivity tests and independent live-execution review remain deployment responsibilities. P6 deliberately does not remove the live-trading safety boundary.
