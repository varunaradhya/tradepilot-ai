# P7 Release Gates

P7 is a hard validation gate for TradePilot's current simulation-only trading architecture.

## Required before release-ready status

- [ ] GitHub Actions backend job passes.
- [ ] GitHub Actions frontend build passes.
- [ ] GitHub Actions deployment-config job passes.
- [ ] P1–P6 regression suites remain green.
- [x] Every registered broker is explicitly live-order disabled.
- [x] Sandbox certification is read-only and cannot authorize live execution.
- [x] Unknown broker paths fail closed.
- [ ] Controlled provider sandbox connectivity is independently certified.
- [ ] Production metrics/alerts are configured.
- [ ] Independent review signs off on any future live-execution architecture.

## Stop conditions

Any failed safety regression, stale/future market-data gate, reconciliation mismatch, evidence-quality failure, secret exposure, or live-order capability discovery blocks promotion.

**No CI run = no CI pass.**
