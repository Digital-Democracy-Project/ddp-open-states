# FL WAF vote-gap re-scrape — verification (steps 4-6), OPEN-41, 2026-08-08

Closes out `PLAN-open-states.md` §8.1a's FL item, left "IN PROGRESS 2026-07-30" after steps 1-3
(regenerate the 540-bill list, capture the BEFORE baseline of 75, clear the cutoff, launch the
re-scrape). Steps 4-6 — the actual verification — had never been run. Gates the FL leg of
`DDP_OPENSTATES_JURISDICTIONS` (tracked separately, not part of this ticket's scope) and BROKER-16.

Full options analysis in `OPEN-41-architecture-assessment-20260808.md` (this ticket's
`/architect-ticket` pass) — recommended Approach B: an explicit, recorded `current_database()`
assertion around every DB-touching step, closing the exact gap §8.1a's own open question flagged
("whatever validation... may have actually run against the local Mac Studio dev stack").

## Environment evidence (Approach B)

Before any DB-touching step, and again immediately before the Step 6 sweep:

```
$ docker exec ddp-openstates-postgres-1 psql -U openstates -d openstates -c "SELECT current_database(), now();"
 current_database |              now
------------------+-------------------------------
 openstates       | 2026-08-08 21:54:00.027654+00
(1 row)
```

Not `openstates_dev`. `docker ps` confirmed `ddp-openstates-postgres-1` (:5433) and
`ddp-openstates-api-1` (:8002) both healthy, and `ps aux` confirmed no FL scrape process was
running before starting. Steps 4 and 5 below used `docker exec` directly against the named
container (never an ambient shell `$DATABASE_URL`), which sidesteps the dev/prod ambiguity
entirely for those two steps. Step 6 has no such option (`quality_check.py` needs `DATABASE_URL`
as a Python env var for `psycopg2`), so its evidence is captured in the same shell, immediately
adjacent to the invocation — see below.

## Corrected re-scrape completion timeline

The ticket's steps 1-3 note says the re-scrape "started 2026-07-30, ~13-14h expected," which read
as if that manual trigger simply ran to completion. Checking `logs/scraper.log*` directly (the
real prod checkout, read-only) shows it's more involved than that:

| When | What | Outcome |
|---|---|---|
| 2026-07-30 13:50:38 | Manual `./run-scrape.sh fl "session=2026"` (trigger #1) | Hung after last progress at 15:12:22; killed 16:15:03 (~63min stall, no traceback — looks like a hung request finally timing out) |
| 2026-07-30 16:16:27 | Manual retry (trigger #2) | Crashed 18:21:47 on `scrapelib.HTTPError: 503 while retrieving https://flhouse.gov/Sections/Bills/bills.aspx?...` — a genuine transient site error, unhandled after retries exhausted |
| 2026-08-01 22:00:00 | Next scheduled run (picked up the still-cleared cutoff, so ran full instead of incremental) | **Completed successfully** 2026-08-02 11:35:52 (scrape done) / 11:38:42 (import done) — ~13h38m, matching the estimate |

So the repair did land, just not via the manual trigger directly — two manual attempts failed
first, and the actual completion was an incidental side effect of the next scheduled cron cycle
still finding an empty cutoff file. `logs/last-run/fl_session_2026.ts` = `2026-08-02T15:38:42`
(UTC; matches the import-done timestamp above once the EDT/UTC offset is accounted for) confirms
this is still the current state as of this verification — no newer full run has occurred since.

**WAF fix holds under the real long-running full scrape:** across the successful 08-01→08-02 run,
`grep -c "flhouse.gov bot detection"` over that run's log window returns **0** (vs. 538 in the
original 2026-06-25/26 bad run), across 1,902 House-search fetches, with only 1
"could not find bill in House Search" miss (a 99.95% hit rate — consistent with a genuinely
missing/renumbered bill, not a systemic issue).

**Tech-debt note (not actioned here, flagged for awareness):** both manual full-scrape attempts on
07-30 failed outright rather than resuming/retrying gracefully — a hang with no clean traceback,
then an unhandled 503. This class of fragility isn't new to this ticket and is out of scope for a
verification-only ticket, but worth someone's attention if manual full re-scrapes need to become
more reliably re-triggerable (right now, the only reason this one closed out was a lucky scheduled
retry two days later).

## Step 4 — AFTER count vs BEFORE baseline (75)

The original `/tmp/fl-2026-waf-affected-bills.txt` from steps 1-3 no longer existed (scratch file,
not preserved). Re-derived from the same source per the documented extraction — confirmed to
reproduce exactly 540 distinct bill numbers:

```
$ gzcat logs/scraper.log.20260714T020000Z.gz | sed -n '21838,51119p' \
    | grep "flhouse.gov bot detection" | grep -oE "BillNumber=[0-9]+" | grep -oE "[0-9]+" \
    | sort -un > /tmp/open-41-fl-2026-waf-affected-bills.txt
$ wc -l /tmp/open-41-fl-2026-waf-affected-bills.txt
     540 /tmp/open-41-fl-2026-waf-affected-bills.txt
```

AFTER count (same query as the BEFORE baseline, against the re-derived list, via
`docker exec ddp-openstates-postgres-1`):

```
 house_vote_events
-------------------
               143
(1 row)
```

**BEFORE: 75 → AFTER: 143 (+68 House vote events, +91%)** across the 540 affected bills. A
substantial, real increase — consistent with the WAF fix genuinely recovering previously-missing
House committee votes, not a flat/no-op re-scrape.

## Step 5 — spot-diff against live data

Three bills selected from the re-derived candidate list, chosen because a direct DB check showed
they now have vote rows (`b.identifier` uses a `"HB 1109"`-style space, not the bare digits in the
candidate list, so the identifier had to be resolved via a DB lookup first — matches the caveat in
`PLAN-open-states.md` §8.1a about the numeric match being a superset, not an exact per-bill key):

| Bill | Local votes (api-v3, `:8002`) | Live votes (`v3.openstates.org`) | Content match |
|---|---|---|---|
| HB 1109 | 1 | 1 | Exact (`motion_text`, `start_date` identical) |
| SB 1722 | 1 | 1 | Exact |
| SB 1724 | 3 | 3 | Exact once order-normalized (array order differed between the two APIs — same pattern already documented in `quality_check.py`'s comment history / OPEN-27's "ordering artifact" note; not a content discrepancy) |

All three bills' local House/committee votes now match live `v3.openstates.org` exactly.

## Step 6 — `quality_check.py` FL sweep

Same shell, DB-identity confirmed immediately before invoking:

```
$ export DATABASE_URL="postgresql://openstates:openstates_dev@localhost:5433/openstates"
$ docker exec ddp-openstates-postgres-1 psql -U openstates -d openstates -c "SELECT current_database(), now();"
 current_database |              now
------------------+-------------------------------
 openstates       | 2026-08-08 21:57:33.935833+00
(1 row)
$ python3 quality_check.py --tier2 fl 2026 --tier2-limit 250 --tier2-random
```

**1231/1254 checks passed (98.2%) | 10 warnings | 13 failures | 0 skipped.**

(First attempt at this sweep was orphaned mid-run when the executing session was interrupted —
confirmed no completion record and the process no longer running; re-ran cleanly to completion
rather than trusting the partial output. Re-confirmed `current_database()` = `openstates`
immediately before the successful re-run too.)

Breakdown, matching OPEN-27's prior FL tier2 sweep shape closely (no new failure category):

- **9 of 10 warnings**: "local has MORE votes than live" — the already-diagnosed, expected pattern
  from `notes/fl-tier2-more-votes-than-live-diagnosis-20260805.md` (local's WAF-cookie fix isn't
  merged upstream yet, PR openstates/openstates-scrapers#5751 still open)
- **1 of 10 warnings**: a cosmetic `latest_action` phrasing difference (local: "adopted by
  publication"; live: "adopted by publication; companion bill(s) passed, ") — not vote-related
- **13 of 13 failures**: "local is MISSING votes vs live" — the separate, pre-existing, already-
  documented ~1.8-3% gap (out of scope for this ticket, same category noted in OPEN-27's sweep)

No new/unexpected failure pattern introduced by the re-scrape. Full output:
`logs/quality-check/fl_2026_tier2only.log` (this checkout; not committed, `logs/*.log` is
gitignored).

## References

- `OPEN-41-architecture-assessment-20260808.md` — options considered, tradeoffs, Approach B rationale
- `PLAN-open-states.md` §8.1a (moved to `ddp-infra`) — the FL item this closes out; update PR:
  [Digital-Democracy-Project/ddp-infra#36](https://github.com/Digital-Democracy-Project/ddp-infra/pull/36)
- `notes/fl-tier2-more-votes-than-live-diagnosis-20260805.md` — OPEN-27's prior FL tier2 sweep and
  the "local has MORE votes than live" diagnosis this run's warnings are expected to match
- Jira: OPEN-41 (this ticket), OPEN-27 (prior FL tier2 work), OPEN-46 (tech-debt follow-up filed
  from this ticket for the `quality_check.py` preflight guard, Approach C, deferred)
