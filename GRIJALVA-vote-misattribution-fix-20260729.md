# Grijalva vote-misattribution fix: the 62 votes that will change

Generated 2026-07-29, before running `fix-grijalva-vote-misattribution.py` for real against production Postgres. Found during the OPEN-2 backfill's post-run verification (see `OPEN-2-backfill-affected-legislators-20260729.md`'s "Follow-up" section) — a separate, pre-existing issue, not caused by that backfill.

## What's wrong and why

**Raúl M. Grijalva** (bioguide `G000551`) represented AZ-7 in the U.S. House. He was sworn in for the 119th Congress (starting 2025-01-03) but did not cast any votes during the period covered below — every one of his vote records for this window is recorded as **"not voting"**, not a real Yes/No/Present position. **Adelita Grijalva** — his successor in the same AZ-7 seat, and his daughter — later won the special election to fill the vacancy.

The 62 vote records below all correctly carry Raúl's own bioguide id (`G000551`) in their `note` column — that part was captured correctly by the scraper at the time. But `voter_id` on these rows already points to **Adelita Grijalva**, not Raúl. This is old, pre-OPEN-2 behavior: before identifier-based matching existed, the importer resolved the name "Grijalva" to whichever `Person` record it found — in this case, Adelita, likely because she was the current officeholder for this seat by the time these specific rows were last (re-)processed. Because `voter_id` was already set (not blank), the OPEN-2 backfill correctly left these rows alone — it only ever fills in *blank* records, by design, so it can never overwrite an existing value, right or wrong.

**The fix:** re-point all 62 rows' `voter_id` from Adelita Grijalva (`ocd-person/e6661e65-1d1e-4c00-9c79-383941edc17a`) to Raúl Grijalva (`ocd-person/06cee575-8fbe-5552-9f2b-9fe5aa2a3725`) — the person the row's own `note` (bioguide `G000551`) actually identifies. Confirmed via a full sweep of every U.S. Congress vote record with a note: this exact pattern exists **only** for this one bioguide / this one wrong person-id pair — nowhere else in the current data.

**Rows affected: 62**  
**All recorded as:** not voting  
**Distinct bills:** 47  
**Date range:** 2025-01-03 to 2025-03-11 (119th Congress, first session)  
**Change:** `voter_id` Adelita Grijalva → Raúl Grijalva (nothing else on these rows changes — not the vote option, not the note, not the bill or vote event)

## Every affected vote

| Date | Bill | Motion | Result | Recorded vote |
|---|---|---|---|---|
| 2025-01-03 | HRES 5 | On Ordering the Previous Question | pass | not voting |
| 2025-01-03 | HRES 5 | On Motion to Commit with Instructions | fail | not voting |
| 2025-01-03 | HRES 5 | On Agreeing to the Resolution | pass | not voting |
| 2025-01-07 | HR 29 | On Passage | pass | not voting |
| 2025-01-09 | HR 23 | On Passage | pass | not voting |
| 2025-01-13 | HR 192 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-01-14 | HR 152 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-01-14 | HR 153 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-01-14 | HR 28 | On Motion to Recommit | fail | not voting |
| 2025-01-14 | HR 28 | On Passage | pass | not voting |
| 2025-01-15 | HR 164 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-01-15 | HR 144 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-01-15 | HR 33 | On Passage | pass | not voting |
| 2025-01-16 | HR 30 | On Motion to Recommit | fail | not voting |
| 2025-01-16 | HR 30 | On Passage | pass | not voting |
| 2025-01-21 | HR 186 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-01-22 | HR 187 | On Motion to Suspend the Rules and Pass, as Amended | pass | not voting |
| 2025-01-22 | HRES 53 | On Ordering the Previous Question | pass | not voting |
| 2025-01-22 | HRES 53 | On Agreeing to the Resolution | pass | not voting |
| 2025-01-22 | HR 165 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-01-22 | S 5 | On Passage | pass | not voting |
| 2025-01-23 | HR 375 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-01-23 | HR 471 | On Passage | pass | not voting |
| 2025-01-23 | HR 21 | On Motion to Recommit | fail | not voting |
| 2025-01-23 | HR 21 | On Passage | pass | not voting |
| 2025-02-04 | HR 43 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-02-05 | HR 776 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-02-05 | HRES 93 | On Ordering the Previous Question | pass | not voting |
| 2025-02-05 | HRES 93 | On Agreeing to the Resolution | pass | not voting |
| 2025-02-06 | HR 27 | On Passage | pass | not voting |
| 2025-02-07 | HR 26 | On Motion to Recommit | fail | not voting |
| 2025-02-07 | HR 26 | On Passage | pass | not voting |
| 2025-02-10 | HR 692 | On Motion to Suspend the Rules and Pass, as Amended | pass | not voting |
| 2025-02-10 | HR 736 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-02-11 | HRES 122 | On Ordering the Previous Question | pass | not voting |
| 2025-02-11 | HRES 122 | On Agreeing to the Resolution | pass | not voting |
| 2025-02-12 | HR 77 | On Motion to Recommit | fail | not voting |
| 2025-02-12 | HR 77 | On Passage | pass | not voting |
| 2025-02-13 | HR 35 | On Passage | pass | not voting |
| 2025-02-24 | HR 825 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-02-25 | HR 832 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-02-25 | HR 818 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-02-25 | HRES 161 | On Ordering the Previous Question | pass | not voting |
| 2025-02-25 | HRES 161 | On Agreeing to the Resolution | pass | not voting |
| 2025-02-26 | HR 788 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-02-26 | HR 804 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-02-26 | HCONRES 14 | On Agreeing to the Resolution, as Amended | pass | not voting |
| 2025-02-26 | HR 695 | On Motion to Suspend the Rules and Pass, as Amended | pass | not voting |
| 2025-03-03 | HR 856 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-03-04 | HR 758 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-03-04 | HRES 177 | On Ordering the Previous Question | pass | not voting |
| 2025-03-04 | HRES 177 | On Agreeing to the Resolution | pass | not voting |
| 2025-03-05 | HRES 189 | On Motion to Table | fail | not voting |
| 2025-03-06 | HRES 189 | On Agreeing to the Resolution | pass | not voting |
| 2025-03-10 | HR 495 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-03-10 | HR 901 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-03-10 | HR 993 | On Motion to Suspend the Rules and Pass | pass | not voting |
| 2025-03-11 | HRES 211 | On Ordering the Previous Question | pass | not voting |
| 2025-03-11 | HRES 211 | On Agreeing to the Resolution | pass | not voting |
| 2025-03-11 | HR 1156 | On Passage | pass | not voting |
| 2025-03-11 | HR 1968 | On Motion to Recommit | fail | not voting |
| 2025-03-11 | HR 1968 | On Passage | pass | not voting |
