[object Object]

## 2026-10-01 — CI JWT warning cleanup
- CI backend/deployment test JWT placeholders were lengthened to satisfy the HS256 minimum recommended key length.
- This removes an avoidable `InsecureKeyLengthWarning` from CI without weakening production secret enforcement.
