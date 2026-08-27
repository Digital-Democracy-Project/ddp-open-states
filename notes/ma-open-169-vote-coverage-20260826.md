# MA 194th vote coverage: what the 205 "failures" actually were (OPEN-169)

**2026-08-26.** Investigation and fix for OPEN-169, following a full Tier 1 coverage run of MA
194th on 2026-08-25 (`quality_check.py --coverage ma 194th`, ~2h45m, 11,406 bills, 45,338 checks).

## Summary

The run reported `44973/45338 passed | 160 warnings | 205 failures`. **Two separate things were
hiding in that number, and neither is what the summary line implies.**

1. **181 of the 205 "failures" were our own client giving up**, not data defects — HTTP 429 and read
   timeouts against `v3.openstates.org`, spread across **145 distinct bills** (one bill can fail
   several checks, which is why 181 failures map to 145 bills). Those bills were *never compared at
   all*. Fixed here.
2. **The 24 real failures are at least two problems, not one.** Our replica holds zero House roll
   calls across all 24 bills (the public API holds 50) — but 4 of those bills have no House vote in
   either source, and 6 are missing Senate votes too. Details in Part 2.

## Part 1 — the 181 were a client defect, and it is fixed

`fetch_bill()` had no retry. A single transient error became a permanent `{"_error": ...}` for that
bill, which `compare_bills()` then recorded as a FAIL. So **88% of the reported failures were
throttling**, and worse, the bills behind them went unchecked while looking accounted-for.

`fetch_bill()` and `fetch_person()` now go through `_get_with_retry()`: four attempts, exponential
backoff, `Retry-After` honoured when the server sends one, and **non-transient errors raise
immediately** rather than burning retries on a 404 that will never change.

### Measured result

Re-running the 145 distinct bills behind those 181 errors:

| | Before | After |
|---|---|---|
| Bills that failed to compare | 145 | **0** |
| New data failures found among them | unknown | **0** |

First pass cleared 139 of 145 and left 6 persistent 429s; those 6 passed on a second run after a
short pause. **So the true count of data-comparison failures is 24 — the throttled bills concealed nothing.**
(Scoped deliberately: retries remove *transient* API failures from the data-quality count, which is
correct for reading coverage. A run that still could not reach the API would be a failed run even
with zero mismatches.)

That matters beyond the number: before this fix, a coverage run's failure count was partly a
function of how hard the API was throttling us that day, which makes it useless as a release gate.

### Also fixed here: the API key was written to the logs in cleartext

`requests` builds its exception message from the full request URL, and the key travels as a query
parameter — so every recorded error wrote the live key into the log. **21 files under
`logs/quality-check/` already carry it.** Since this change rewrites the exact line that leaks it,
leaving it would mean knowingly shipping a secret leak, so `_redact()` scrubs it at the single point
where an exception becomes recorded text. Verified in a real run: zero occurrences of the key,
`apikey=<redacted>` in its place.

**This does not close OPEN-170**, which still owns scrubbing the 21 existing files and deciding
whether to rotate the key.

## Part 2 — the 24 real failures are mostly, but not only, missing House roll calls

**This section was wrong twice before it was right; the numbers below are the ones to trust.** The
first pass classified votes by tally size (MA House 160 seats, Senate 40). Review challenged the
heuristic, and chasing it found the API returns the chamber outright as
`organization.classification` (`lower`/`upper`). Re-measuring with that field corrected the claim
once. Review challenged the corrected version too, and checking *that* corrected it again.

**Every vote record in both sources carried a `lower` or `upper` classification — zero were missing
or unclassifiable — so nothing below rests on inference or on a dropped bucket.**

### The measurement

| Across all 24 bills | House (`lower`) | Senate (`upper`) |
|---|---|---|
| **Our replica** | **0** | 40 |
| **Public OpenStates** | 50 | 24 |

### What that actually means, bill by bill

The aggregate table invites a tidy story — "we are missing the House" — and the per-bill numbers do
not support it:

- **20 of the 24 bills** have at least one live House vote we lack. This is the dominant pattern and
  the 50 House votes sit here.
- **4 bills have no House votes in either source** — H 4001, H 4683, S 2947, S 3029. Their failure
  cannot be a House gap, because there is no House vote to be missing.
- **6 bills are missing *Senate* votes as well**: H 4001, H 4683, H 4843, H 58, S 2947, S 3029 all
  have fewer `upper` votes locally than live (e.g. H 58: local 1, live 4).

**So there are at least two distinct problems here, not one.** A House-side gap covering most of the
set, and a Senate-side gap on six bills that the House story completely hides. An earlier draft of
this note claimed "we are missing one chamber, and only one" — that was wrong, and acting on it
would have sent someone to fix the House scraper and declare victory with six bills still broken.

The clearest single case of the House gap is H 4240's budget veto overrides — the public API has 17
House votes dated 2025-10-08 ("Shall item 7061-9010 … stand"); we have 16 Senate votes covering the
same items dated 2025-10-23 ("Item 7061-9010 passed over veto"), and no House votes at all.

### On the Senate, stated no more strongly than the evidence allows

We hold **more Senate roll calls by count** in this 24-bill set (40 vs 24), and that is where many of
the run's 74 `local has MORE votes than live` warnings come from. **That is a count, not a quality
finding** — these were not reconciled per vote by bill, date and question, so the surplus could
include duplicates, differently-attributed votes, or votes the public API deliberately omits. Do not
promote it to "our Senate coverage is better" without that reconciliation, and note that six bills
in this very set have *fewer* Senate votes than live.

### Scope

All of the above describes **the 24 bills that failed comparison**, not MA 194th as a whole. Nothing
here establishes how many House roll calls are missing across the full session — only that on the
bills where we already knew something was wrong, the House is absent 20 times out of 24.

### Answered, later the same day

The scraper was run against these bills, and both questions have answers.

**The House gap was neither a fetch failure nor a parse failure — the scraper never tried.** House
votes were only created when an action description contained `"Supplement"`, and Massachusetts
stopped using that word. Across the 24 bills, `"Supplement"` occurs **0** times while
`"YEA and NAY"` occurs **57** and `"Roll Call"` — the Senate trigger — occurs **41**. The Senate
branch matched reality and the House branch matched nothing, which is exactly why the symptom read
as "Senate votes but no House votes" rather than an obvious blank.

Behind it, a second bug: the House roll-call URL interpolated the session as `194th`, giving a 404
that `urlretrieve` saved, `convert_pdf` turned into junk, and a bare `return` reported as success —
so a vote event was yielded with correct counts and zero voters. Tallies looked right while every
individual House vote was dropped.

**The six "Senate-side gaps" were not gaps.** All 14 of live's extra Senate vote events on those
bills are empty — no counts, no voters. We held the real roll calls; live held placeholders. The
coverage check counted vote events rather than content, which is a defect in the check and is now
fixed. The four bills with no House vote in either source collapse entirely into this, so what
looked like three problems was one.

### The number that actually measures completeness

This is the part worth keeping, because it is not the coverage run.

**The coverage check cannot measure this class of gap at all.** It compares us against live, and
public OpenStates has both of the same bugs — verified against their `main`. So a bill where both
sides lack the House votes never fails a check. The 24 that failed were only the ones where live
happened to have the votes from some other route.

The real measure is internal: *how many MA bills cite a House roll call in their actions, and how
many actually hold one?*

```
                                       before      after
bills citing a House roll call            117        117
bills holding a House vote                 66        122
bills still missing them                   51          0
```

293 House vote events and 40,649 individual voter records, none of which were being collected.
Contributed upstream as openstates/openstates-scrapers#5776, since the bug affects every consumer
of the public scraper and encodes no DDP-specific tradeoff.

## Reproducing

```bash
# the 145 previously-uncompared bills
python3 quality_check.py --bill-ids ma 194th "$(paste -sd, bills.txt)"

# chamber classification: fetch each bill from both APIs with include=votes
# and read each vote's organization.classification ("lower" / "upper")
```
