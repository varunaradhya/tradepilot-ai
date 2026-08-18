# P6 Deployment Validation Checklist

- [x] Request latency and 5xx telemetry captured.
- [x] SLO endpoint reports database and market-data dependency health.
- [x] Kill-switch state included in operational SLO output.
- [x] Live execution hard-block remains active.
- [x] Sandbox credential readiness is secret-safe.
- [x] Unsupported broker sandbox is fail-closed.
- [x] Regression tests cover failure telemetry and credential leakage.
- [x] Broker certification remains read-only.
- [ ] Connect real broker sandbox credentials in deployment secret storage.
- [ ] Execute provider-specific external sandbox certification.
- [ ] Configure external metrics/alerts and SLO thresholds.
- [ ] Perform independent live-execution architecture review.
