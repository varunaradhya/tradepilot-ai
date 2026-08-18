# P6 Release Gates

1. CI backend compile and tests must pass.
2. Frontend build and deployment configuration must pass.
3. Observability endpoints remain read-only.
4. Sandbox credential readiness must not expose secret values.
5. Live execution must remain disabled.
6. Real sandbox connectivity and independent live-execution review remain deployment gates.