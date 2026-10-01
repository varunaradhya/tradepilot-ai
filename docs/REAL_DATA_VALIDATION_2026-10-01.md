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

This remains a structural data-quality failure. NSE documentation confirms April 9, 2022 was a **mock trading** date in the Capital Market segment, not a live market session. The dataset therefore contains source rows from a mock session and they must not be silently treated as live-market research data. citeturn2search1

### Weekend session classification

The 7,316 weekend rows are not all equivalent. Authoritative NSE evidence changes the interpretation:

| Date | Rows | Classification | Evidence |
|---|---:|---|---|
| 2022-04-09 | 986 | **MOCK — exclude from live research** | NSE scheduled a Capital Market mock session on this Saturday. citeturn2search1 |
| 2022-04-30 | 676 | **MOCK — exclude from live research** | NSE scheduled a Capital Market mock session on this Saturday. citeturn1search10 |
| 2023-11-12 | 254 | **LIVE SPECIAL — valid session type** | NSE scheduled Diwali Muhurat trading, normal market 18:15–19:15. The dataset's 18:15–19:10 observations fall inside that window. citeturn7search1 |
| 2024-01-20 | 1,500 | **LIVE SPECIAL/REGULAR-DAY — valid session type** | NSE notified regular equity trading on Saturday Jan 20; the dataset contains the normal 09:15–15:25 grid. citeturn5search1turn5search0 |
| 2024-03-02 | 440 | **LIVE SPECIAL — valid session type** | NSE scheduled a special live equity session on Saturday Mar 2, including 09:15–10:00 and a later DR-site session. citeturn0search23 |
| 2024-05-18 | 460 | **LIVE SPECIAL — valid session type** | NSE scheduled special live equity trading with sessions around 09:15–10:00 and 11:30–12:30; the dataset contains 09:15–12:30 observations. citeturn6search3 |
| 2025-02-01 | 1,500 | **LIVE SPECIAL — valid session type** | NSE explicitly scheduled a live equity session on Saturday Feb 1 for the Union Budget, using normal trading-day timings. citeturn0search22 |
| 2026-02-01 | 1,500 | **LIVE SPECIAL — valid session type** | NSE explicitly scheduled live equity trading on Sunday Feb 1 with normal 09:15–15:30 market hours. citeturn3search0 |

NSE's general equity-market documentation says equities normally trade Monday–Friday except holidays, with regular market hours 09:15–15:30; the dates above are documented exceptions rather than grounds for automatically deleting every weekend record. citeturn0search0turn0search1

### Weekday bars outside the regular session

The 722 weekday outside-session rows are concentrated on:

- 2022-10-24 — 240 rows, 18:15–19:10 IST
- 2024-11-01 — 228 rows, 18:00–18:55 IST

These are now source-resolved Muhurat sessions:
- **2022-10-24 — LIVE SPECIAL:** NSE Capital Market circular NSE/CMTR/54023 specifies normal market 18:15–19:15. The dataset observations fall inside that window. citeturn2search2
- **2024-11-01 — LIVE SPECIAL:** NSE Capital Market circular NSE/CMTR/64628 specifies normal market 18:00–19:00. The dataset observations fall inside that window. citeturn0search19

Therefore these 468 rows should not be quarantined merely for being outside normal 09:15–15:30 hours. They are now represented in the source-backed session calendar.

## Timestamp spacing

The dataset is predominantly 300-second intervals, but it contains irregular adjacent timestamp deltas, including 299, 301, 240, 360 and other values. The source timestamps were not rounded, resampled, repaired, or deleted.

This report therefore preserves the observed source behavior rather than converting it into an artificial 5-minute grid.

## Certification status

The dataset remains **NOT CERTIFIED**.

However, the weekend finding is now more precise:

- 2022-04-09 and 2022-04-30 are documented mock sessions and must be excluded from live-market research.
- 2023-11-12, 2024-01-20, 2024-03-02, 2024-05-18, 2025-02-01, and 2026-02-01 are documented live/special trading dates and should not be rejected solely because they fall on Saturday/Sunday.
- 2022-10-24 and 2024-11-01 are also documented live Muhurat sessions and are now included in the source-backed session calendar. citeturn2search2turn0search19
- The certification gate now uses explicit REGULAR, LIVE_SPECIAL, MOCK, HOLIDAY, and UNKNOWN session classifications.
- The 2022-04-09 negative-volume records remain a separate structural failure.
- After applying the session calendar, the previously unresolved 468 weekday after-hours rows are explained by documented Muhurat sessions; no unknown weekend rows remain in the analyzed dataset.
- Persisted provenance and explicit corporate-action adjustment state are still required.

## Session-calendar implementation status

The source-backed NSE equity session calendar is now implemented in backend/app/services/nse_equity_calendar.py and consumed by the research certification gate.

It distinguishes:

1. regular trading dates;
2. documented live special-session dates and their permitted windows;
3. documented mock/non-live sessions;
4. holidays;
5. unknown exceptional dates, which fail closed.

Regression tests cover Muhurat sessions, mock sessions, multi-window special sessions, unknown weekends, and out-of-window observations.

No raw data was deleted or repaired as part of this change.

## Important safety constraint

No performance/backtest conclusion should be treated as certified research from this raw dataset until the certification requirements are satisfied. In particular, the data's corporate-action adjustment state must come from authoritative provenance rather than being inferred from observed price jumps.

No source rows were silently repaired or removed.
