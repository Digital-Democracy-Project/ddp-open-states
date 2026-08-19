# OPEN-111: cross-jurisdiction audit for the Carlos/Dave Smith misattribution shape

Generated 2026-08-19, after OPEN-112 confirmed the underlying mechanism (a cache-key
bug in `openstates-core`'s `resolve_person()` -- see that ticket for the root cause
and code fix). This ticket used that confirmed mechanism as its audit methodology,
per OPEN-112's own recommendation, rather than a vaguer "look for stale data" sweep.

## Methodology

1. Across every tracked jurisdiction, found every `family_name` shared by two or more
   people who have each held a role in a *different* chamber classification (`upper`
   vs `lower`) at some point, current or historical -- the structural precondition
   for the cache-bleed bug to matter. **153 such (jurisdiction, surname) groups**
   were found (Alabama, Arizona, Florida, Massachusetts, Michigan, US Congress, Utah,
   Virginia, Washington).
2. For each group, found every `opencivicdata_personvote` row in that jurisdiction
   whose `voter_name` is a **bare** surname exactly matching the group's shared
   name (not a state/chamber-qualified string like `"Smith (NE)"`, which isn't
   vulnerable to this specific collision) -- **64,612 rows** across all 153 groups.
3. For each row, called the *current*, already-fixed (OPEN-112) `resolve_person()`
   fresh and in isolation -- using that row's own vote_event's real
   `org_classification` and legislative-session dates -- and compared the result
   against the row's actual stored `voter_id`. A disagreement is the same signal
   that caught OPEN-110's Carlos/Dave Smith case: a fresh, correct resolution
   doesn't match what was actually written.

## Results

**4,709 of the 64,612 checked rows (7.3%) disagree**, across **7 distinct
(jurisdiction, surname) groups**. These split into two different shapes:

### Shape 1: wrongly attributed to a real, specific, different person (the OPEN-110 disease)

| Jurisdiction | Surname | Rows | Currently attributed to | Should be | Chamber | Dates |
|---|---|---|---|---|---|---|
| Washington | Cortes | 1,101 | Julio Cortes (House) | Adrian Cortes (Senate) | upper | 2025-02-05 .. 2026-03-12 |
| Washington | Valdez | 1,101 | Michelle Valdez (House) | Javier Valdez (Senate) | upper | 2025-02-05 .. 2026-03-12 |
| Florida | Smith | 621 | Dave Smith (House) | Carlos Smith (Senate) | upper | 2025-02-11 .. 2026-04-29 |
| Michigan | Outman | 430 | Pat Outman (House) | Rick Outman (Senate) | upper | 2025-01-29 .. 2026-07-03 |

Every one of these four groups shows the identical pattern found in OPEN-110: a
single, consistent (wrong-person -> right-person) pair across every affected row
(confirmed via `Counter` over distinct pairs -- exactly 1 pair per group, not a
scatter of unrelated mismatches), and the wrongly-credited person is *always* the
House member while the real voter is *always* the Senate member, for a Senate
(`upper`) vote. Checked each pair's own membership history directly: none of the
six people involved have ever shared a seat or succeeded one another -- these are
unrelated same-surname legislators, the same shape as Carlos/Dave, not seat
successions like Grijalva's.

**Notably, Washington's Cortes and Valdez findings share an identical row count
(1,101) and identical date range (2025-02-05 to 2026-03-12)** -- strong evidence
these both trace to the same underlying incident (very likely one or a few WA
Senate bulk-import runs where multiple surname collisions got cache-poisoned
together), not two independent problems.

**FL Smith is the mirror image of OPEN-110.** That ticket's backfill only touched
House (`lower`) rows wrongly attributed to Carlos; this audit found a separate set
of Senate (`upper`) rows wrongly attributed to Dave that OPEN-110 never covered,
confirming the cache-bleed bug corrupted data in *both* directions for this same
pair.

### Shape 2: never resolved at all (a different observed data shape -- root cause not established)

| Jurisdiction | Surname | Rows | Fresh resolution would be | Chamber | Dates |
|---|---|---|---|---|---|
| Florida | Garcia | 955 | Ileana Garcia (Senate) | upper | 2023-02-08 .. 2023-11-08 |
| Washington | Hunt | 455 | Victoria Hunt (Senate) | upper | 2026-01-21 .. 2026-03-12 |
| Michigan | Greene | 46 | Chedrick Greene (Senate) | upper | 2026-06-03 .. 2026-06-25 |

These three groups' rows have `voter_id = NULL` in the stored data -- they were
never resolved to *anyone*, not resolved to the wrong person. This is a different
*observed shape* from Shape 1 (an unresolved-name gap, the same general category
OPEN-2's Congress-specific bioguide/lis backfill addresses), but *why* these
specific rows were never resolved hasn't been established here -- it isn't
necessarily the OPEN-112 cache-bleed mechanism, but this audit didn't rule it out
either. Called out separately rather than folded into the misattribution tickets
below because the fix, if any, is different in kind: OPEN-112 already prevents
future *wrong* resolutions; whether it's safe to *fill in* a currently-blank
resolution is a distinct question this audit doesn't answer. Confirmed: across
all 4,709 disagreements found, these were the only two shapes that occurred --
every row was either a real, different stored `voter_id` (Shape 1, 3,253 rows) or
a `NULL` stored `voter_id` (Shape 2, 1,456 rows). No other disagreement pattern
(e.g. a stored id that no longer exists in the DB, or a fresh resolution that
itself came back ambiguous) turned up.

## What this audit does NOT do

Per this ticket's own scope: no backfill scripts were written or run here. Each
Shape 1 finding is provable and narrow enough to follow the OPEN-110/Grijalva
precedent (a scoped, reviewable backfill script per pair); Shape 2 is a materially
different problem needing its own investigation into whether backfilling a blank
`voter_id` from a bare surname is even safe (unlike OPEN-2's Congress case, there's
no stable identifier like bioguide backing these resolutions -- worth scrutiny
before writing anything that fills in a value with real confidence, not just "some
resolve_person call happened to return this today").

## Follow-up tickets filed

- OPEN-113: Washington Cortes/Valdez Senate votes misattributed to the wrong
  House member (Shape 1)
- OPEN-114: Michigan Outman Senate votes misattributed to the wrong House member
  (Shape 1)
- OPEN-115: Florida Carlos Smith's real Senate votes misattributed to Dave Smith
  (Shape 1, the reverse direction of OPEN-110)
- OPEN-116: investigate whether the Shape 2 blank-`voter_id` rows (FL Garcia, WA
  Hunt, MI Greene) should be backfilled, and how to do so safely without a stable
  identifier to anchor on

## Coverage caveat

This audit only checked bare-surname rows against the 153 groups that share a
surname split across `upper`/`lower` specifically. It does not cover: collisions
within the *same* chamber (e.g. two same-surname state Representatives); a
surname collision where one side's own membership history was simply never
captured in our replica at all (as opposed to a *retired* legislator with a
membership row, who the candidate query does include -- the "current or
historical" wording in the methodology means the query has no date/current-role
filter, so any captured membership counts); or jurisdictions/organizations
classified outside `upper`/`lower` (e.g. unicameral Nebraska, `legislature`-
classified bodies). Scoped this way deliberately, matching OPEN-112's confirmed
mechanism exactly rather than expanding into a broader, less-targeted sweep.

## Reproducibility

Checked against the production OpenStates replica as of 2026-08-19, using
`resolve_person()` from the `fix/open-112-resolve-person-cache-key-chamber`
branch (openstates-core PR #25, not yet merged at time of writing) -- i.e. the
fixed version, not `main`. The audit query and comparison logic are described in
full in the Methodology section above; no script was committed to this repo,
matching this project's existing convention for investigation write-ups (see the
Grijalva and OPEN-110 docs, which document their queries in prose rather than as
a checked-in script). Re-running against a later DB snapshot or after further
`resolve_person` changes could change these counts.
