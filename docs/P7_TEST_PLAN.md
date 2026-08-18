# P7 Test Plan

## Automated

1. Run the complete backend pytest suite.
2. Compile every backend module.
3. Run broker safety regression tests.
4. Build the frontend with production TypeScript/Vite checks.
5. Validate Docker Compose configuration with CI-safe placeholders.

## Safety assertions

- No broker reports live-order capability.
- No broker certification returns `live_execution_allowed=true`.
- Unknown brokers fail closed.
- Sandbox checks never return secret values.
- Existing kill-switch and market-data/reconciliation gates remain fail-closed.

## Manual/environmental

- Configure provider sandbox credentials only in deployment secret storage.
- Perform read-only provider sandbox certification.
- Confirm external monitoring/alert routing.
- Record results in the release evidence before considering any future live-execution review.
