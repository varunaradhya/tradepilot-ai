# P7 Validation Record

## Application checks added

- Registered brokers are asserted to have `live_orders == false`.
- Broker live execution is asserted disabled for every registered broker.
- Sandbox certification is asserted to return `live_execution_allowed == false`.
- Unknown broker certification is asserted to fail closed.
- Provider capability metadata is asserted not to enable live orders.

## Evidence policy

These checks must run as part of the existing backend pytest suite. No manual claim of release readiness is valid without successful CI evidence.
