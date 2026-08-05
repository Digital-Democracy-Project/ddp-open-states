# FL "local has MORE votes than live" — diagnosis and fix, OPEN-27, 2026-08-05

Closes the open item both prior FL Tier 2 sweeps flagged but didn't diagnose:
`notes/fl-tier2-500-bill-random-sample-20260803.md` (25/500 warnings) and
`notes/fl-tier2-250-bill-post-fix-sweep-20260803.md` (18/250 warnings). `compare_bills()`'s own
comment (`quality_check.py`, near the vote-count check) said this pattern was *expected* for UT/MI
specifically ("we have fixes not yet merged upstream") — nobody had checked whether an equivalent
FL fix existed, or whether this was a local-side duplication artifact instead.

## Diagnosis: genuine local-only fix, not duplication

Full evidence trail in `OPEN-27-architecture-assessment-20260805.md` (this ticket's
`/architect-ticket` pass). Summary, independently re-verified before acting on it:

1. **Direct DB query** of FL HB 559, HB 1175, HB 1137 (session 2026): every local vote row has a
   distinct `(motion_text, start_date, organization_id)` — no duplicate roll calls in local data.
2. **Direct live-API query** (`v3.openstates.org/bills`, `include=votes`) for the same three bills:
   live's votes are a strict subset of local's, matching byte-for-byte on `start_date` +
   `motion_text` for every vote live does have. Live is missing *only* committee-level votes.
3. **Fork-vs-upstream diff**: `openstates-scrapers` commit `ec6a5af` (merged to the DDP fork
   2026-07-18, tracked in `RUNBOOK.md` as PR #5) added `_FLHouseWAFSource` to `scrapers/fl/bills.py`.
   `flhouse.gov` (the only source for FL **House** committee votes) sits behind an F5 BIG-IP WAF
   that issues a session cookie valid ~1hr; a full FL regular-session scrape runs 26+ hours on one
   persistent connection, so every House-committee-vote request past the first hour silently gets a
   "Request Rejected" page back with HTTP 200 — no exception, no retry, just zero votes for the
   rest of the run. `_FLHouseWAFSource.get_response()` drops stale `flhouse.gov` cookies before
   each request so votes keep flowing for the full run. Confirmed upstream's real `main` (fetched
   live) has no such mechanism — upstream's own independent scrape of FL genuinely loses House
   committee votes past ~1hr into any long run, which is exactly the gap seen in step 2.

## Fix: contributed upstream, comment corrected

- Cherry-picked `ec6a5af` (`_FLHouseWAFSource` + its one call-site swap in `HouseSearchPage`) onto
  a branch off the real `upstream/main` and opened
  [openstates/openstates-scrapers#5751](https://github.com/openstates/openstates-scrapers/pull/5751).
  One merge conflict in `accept_response`'s fallback branch (upstream had independently evolved
  that specific branch since the fork point) was resolved by keeping upstream's own fallback logic
  untouched and only bringing over the `_FLHouseWAFSource` mechanism itself — kept the contribution
  minimal and focused on the actual fix rather than smuggling in an unrelated behavior change.
- `quality_check.py`'s `compare_bills()` comment now names FL alongside UT/MI, with the specific
  mechanism and PR link (previously just "UT/MI... fixes not yet merged upstream" — see
  `OPEN-27-architecture-assessment-20260805.md`'s residual finding on why that specificity matters).
- `RUNBOOK.md`'s PR #5 row updated from "upstream PR candidate" to "upstream PR opened" with the
  new PR link — this was Tier 1 tracked debt (`tech-debt.md`) sitting unactioned since 2026-07-18.

## Tier 2 re-run: pattern confirmed stable, not a bug to "fix away"

Re-ran the same invocation as the 250-bill post-fix sweep:

```
python3 quality_check.py --tier2 fl 2026 --tier2-limit 250 --tier2-random
```

**1251/1279 checks passed (97.8%) | 20 warnings | 8 failures | 0 skipped**

All 20 warnings are "local has MORE votes than live" — same category, none of the "first vote
counts differ" ordering artifact (that's PR #73's fix, confirmed still fully resolved). 20/250
(8.0%) vs the prior run's 18/250 (7.2%) is within random-sampling noise for a different sample —
proportionally consistent, confirming this is a stable, explained pattern rather than a regression
or a newly-introduced bug.

The count did **not** drop, and per the diagnosis above it isn't supposed to: the local scraper's
fix has been running since 2026-07-18, so nothing in this ticket's remaining work (contributing the
fix upstream, correcting the comment) changes local scrape data. AC #4 is satisfied as "confirmed
stable and now explained," not "warning count drops" — the warning is telling the truth about a
real, permanent (until upstream merges PR #5751) local-vs-public-API gap, not flagging a defect.

The 8 failures are all "local is MISSING votes vs live" (0/1, 0/2, 0/3) — a separate, distinct,
already-known FL gap (documented in both prior sweeps as ~1.8-3% of bills), out of scope here.

Raw log: `logs/quality-check/fl_2026_tier2only.log` (this checkout).

## Follow-up recommendation (not actioned under OPEN-27 — out of scope)

The UT/MI half of the `quality_check.py` comment ("we have fixes not yet merged upstream") has
never been independently verified the way FL's now has — it's present in `quality_check.py`'s very
first commit, with no supporting note, `RUNBOOK.md`, or `PLAN-*.md` entry documenting a specific
UT or MI vote-count fix. Recommend a follow-up ticket running the same three-step diagnosis
(DB query → live-API query → fork/upstream diff) against UT and MI before continuing to trust that
half of the comment. Not blocking or in scope for OPEN-27, whose AC list is FL-only throughout.

## References

- `OPEN-27-architecture-assessment-20260805.md` — full diagnosis, options considered, tradeoffs
- `notes/fl-tier2-500-bill-random-sample-20260803.md`, `notes/fl-tier2-250-bill-post-fix-sweep-20260803.md`
  — the two sweeps that surfaced this as an open item
- [openstates/openstates-scrapers#5751](https://github.com/openstates/openstates-scrapers/pull/5751)
  — the upstream contribution
- `RUNBOOK.md` "DDP commits on fork main" — PR #5's row, now updated
- `quality_check.py` `compare_bills()` — comment updated
