# TradePilot Real Market Dataset Validation — 2026-10-01

## Dataset analyzed

- Dataset ID: `equity_nse_discovery_5m`
- Source: Dhan
- Interval: 5 minutes
- Universe: 20 NSE equities
- Source range: 2021-08-16 through 2026-08-16
- Rows analyzed: 1,854,970
- Uploaded analysis artifact: `equity_nse_discovery_5m.csv.gz`
- Original SQLite source remains unchanged and was not modified during extraction.

## First-pass structural results

| Check | Result |
|---|---:|
| Rows | 1,854,970 |
| Symbols | 20 |
| Duplicate (symbol,timestamp) keys | 0 |
| Missing OHLCV values | 0 |
| Invalid OHLC relationships detected | 0 |
| Negative-volume rows | 18 |
| Weekend-dated rows | 7,316 |
| Weekday rows outside 09:15–15:30 IST | 722 |

### Negative volume

All 18 negative-volume rows occur at the same timestamp:

- Epoch: 1649488800
- Local time: 2022-04-09 12:50 IST
- Symbols affected: 18 of 20

This is a structural data-quality failure under the current certification gate.

### Weekend rows

Weekend rows occur on eight dates:

- 2022-04-09 — 986 rows
- 2022-04-30 — 676 rows
- 2023-11-12 — 254 rows
- 2024-01-20 — 1,500 rows
- 2024-03-02 — 440 rows
- 2024-05-18 — 460 rows
- 2025-02-01 — 1,500 rows
- 2026-02-01 — 1,500 rows

The current TradePilot certification gate treats all weekend-dated bars as structural failures. Some dates may represent exchange special-session trading and therefore require an authoritative exchange-calendar check before changing that rule. No such inference is made by this report.

### Weekday bars outside the regular session

The 722 weekday outside-session rows are concentrated on:

- 2022-10-24 — 240 rows, 18:15–19:10 IST
- 2024-11-01 — 228 rows, 18:00–18:55 IST

The current certification gate treats these as outside regular-session bars.

## Timestamp spacing

The dataset is predominantly 300-second intervals, but it contains irregular adjacent timestamp deltas, including 299, 301, 240, 360 and other values. The source timestamps were not rounded, resampled, repaired, or deleted.

This report therefore preserves the observed source behavior rather than converting it into an artificial 5-minute grid.

## Certification status

The current TradePilot research certification gate would **not certify this dataset as-is** because structural issues are present:

- weekend bars
- outside-regular-session bars
- negative-volume bars

Additionally, the uploaded CSV does not contain the persisted provenance record required by the application, including the explicit corporate-action adjustment state. Therefore this artifact alone cannot establish full research certification.

## Important safety constraint

No performance/backtest conclusion should be treated as certified research from this raw dataset until the certification requirements are satisfied. In particular, the data's corporate-action adjustment state must come from authoritative provenance rather than being inferred from observed price jumps.

No source rows were silently repaired or removed during this validation.
