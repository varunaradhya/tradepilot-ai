# TradePilot V1 Release Checklist

## Verified engineering baseline

- [x] Backend regression suite green: 362 passed at the latest local checkpoint
- [x] Frontend TypeScript/Vite production build green at the latest local checkpoint
- [x] Long-first intraday signal path
- [x] Position sizing and risk limits
- [x] Central execution safety gate
- [x] Paper-trading guardrails
- [x] Strategy qualification / robustness / walk-forward gates
- [x] Strategy readiness and deployment readiness gates
- [x] Market-data quality validation
- [x] Multi-broker capability abstraction
- [x] Docker Compose stack
- [x] CI workflow for backend tests and frontend build

## Pre-paper-production checks

- [ ] Configure PostgreSQL with a strong unique password
- [ ] Configure a strong JWT secret
- [ ] Configure the broker-encryption key from a real secret manager
- [ ] Restrict CORS to the deployed frontend origin
- [ ] Confirm `/health` and `/ready` after deployment
- [ ] Confirm paper mode is the only enabled execution mode
- [ ] Confirm no broker credentials are present in source control or frontend bundles
- [ ] Verify market-data provider rate limits and failure handling
- [ ] Verify clock/timezone assumptions for the NSE trading session
- [ ] Run a complete paper-trading session and reconcile trades

## Strategy validation gate

A strategy must not be promoted because of one profitable backtest.

Review:

1. Trade count and sample size
2. Profit factor and expectancy
3. Maximum drawdown
4. Robustness / sensitivity results
5. Walk-forward results
6. Regime-specific behavior
7. Realized paper-trading evidence
8. Data-quality incidents
9. Operational failures

## Broker rollout

Broker integrations are staged independently.

### Dhan

- [ ] Credentials configured outside source control
- [ ] Account/portfolio read verified
- [ ] Market-data read verified
- [ ] Paper order lifecycle reconciled
- [ ] Broker errors normalized
- [ ] Live order path independently reviewed

### Groww

- [ ] Integration availability confirmed for the intended API/account
- [ ] Credentials configured outside source control
- [ ] Account/market-data read verified
- [ ] Paper workflow verified
- [ ] Broker errors normalized

### Angel One

- [ ] SmartAPI access and account eligibility confirmed
- [ ] Credentials configured outside source control
- [ ] Account/market-data read verified
- [ ] Paper workflow verified
- [ ] Broker errors normalized

## Live execution policy

Live execution remains **disabled** until all strategy, data, security, operational and broker review gates are explicitly satisfied.

A passing software test suite alone is not sufficient to enable live orders.
