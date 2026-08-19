# Vote misattribution backfills: record of everything run, 2026-08-19

A single record of every same-surname vote misattribution found and corrected in the
`opencivicdata_personvote` table (the DDP OpenStates replica) on 2026-08-19, spanning
OPEN-110 through OPEN-116. All were run for real, with a follow-up `--dry-run` after
each confirming zero rows remained.

## Where this started

A GitGuardian alert on a leaked API key led to auditing recent Florida vote data,
which surfaced Carlos Smith's public-facing scorecard showing 100+ votes that were
never his (OPEN-110). Root-causing that led to a real, live bug in `openstates-core`
(OPEN-112: `resolve_person()`'s cache key omitted chamber, letting one chamber's
lookup poison another's within the same import run) and a systematic
cross-jurisdiction audit for the same shape (OPEN-111), which surfaced four more
affected groups (OPEN-113 through OPEN-116).

## OPEN-110: Florida House votes misattributed to the wrong Smith

**PR:** [#134](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/134)
(merged)

423 Florida House ("lower") votes carried `voter_name = "Smith"` but `voter_id`
pointing to **Carlos Smith** (`ocd-person/df1d6ab6-b2cd-4a6f-b7cc-aa5a63d8011f`, FL
Senate) instead of **Dave Smith** (`ocd-person/e4bf077a-8468-49a6-a75c-24ee5076352e`,
FL House) -- unrelated same-surname legislators in different chambers, no seat
succession.

| Change | Rows |
|---|---|
| Carlos Smith -> Dave Smith (FL House) | 423 |

## OPEN-112: the code fix (openstates-core)

**PR:** [#25](https://github.com/Digital-Democracy-Project/openstates-core/pull/25)
(merged)

Root cause: `BaseImporter.resolve_person()`'s cache key was `(psuedo_person_id,
start_date, end_date)` -- it omitted `org_classification` (chamber). Since both
chambers of a state legislature share one `LegislativeSession` (identical
start/end dates), a bare-name lookup for one chamber and the identical lookup for
the other chamber, within the same import run, produced the same cache key --
whichever chamber resolved first silently poisoned the cache for the other for the
rest of that run. Fix: chamber is now part of the cache key. No data change; this
is why new scrapes stop producing this bug going forward.

## OPEN-111: the audit that found the rest

**PR:** [#135](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/135)
(merged)

Used OPEN-112's confirmed mechanism to scan every tracked jurisdiction: 153
same-surname/cross-chamber candidate groups, 64,612 bare-surname vote rows checked
against a fresh, post-fix `resolve_person()` call, 4,709 disagreements found across
7 groups -- 4 more wrongly-attributed groups (filed as OPEN-113/114/115) and 3
blank-`voter_id` groups (filed as OPEN-116).

## OPEN-113: Washington Cortes and Valdez, Senate votes

**PR:** [#136](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/136)
(merged)

Both pairs share an identical row count and date range (2025-02-05 to
2026-03-12) -- one shared root incident, not two independent problems.

| Change | Rows |
|---|---|
| Julio Cortes (House) -> Adrian Cortes (Senate) | 1,101 |
| Michelle Valdez (House) -> Javier Valdez (Senate) | 1,101 |

## OPEN-114: Michigan Outman, Senate votes

**PR:** [#137](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/137)
(merged)

Rick Outman held a Michigan House seat 2011-2016, left, and returned in the Senate
continuously since 2019 -- a chamber change, no relation to Pat Outman beyond the
shared surname.

| Change | Rows |
|---|---|
| Pat Outman (House) -> Rick Outman (Senate) | 430 |

## OPEN-115: Florida Smith, the reverse direction

**PR:** [#138](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/138)
(merged)

The mirror image of OPEN-110, on the other chamber: OPEN-110 only backfilled
House-side rows; this covers Senate-side rows, confirming the OPEN-112 cache-bleed
bug corrupted this exact pair's data in both directions.

| Change | Rows |
|---|---|
| Dave Smith (House) -> Carlos Smith (Senate) | 623 |

## OPEN-116: blank votes, filled in only where date-anchored unambiguous

**PR:** [#139](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/139)
(merged)

A materially different shape from the other five: these rows had `voter_id = NULL`
-- never resolved to anyone, not resolved to the wrong person -- with no
bioguide-style identifier to anchor confidence in a fill. Investigated rather than
assumed: directly checked `opencivicdata_membership` for how many people with each
surname held a matching-chamber seat on each vote's own real date. Verified
comprehensively across all 41 (Garcia) + 22 (Hunt) + 9 (Greene) distinct dates
involved -- exactly one candidate every time, zero ambiguous.

| Filled in | Rows |
|---|---|
| (blank) -> Ileana Garcia (FL Senate) | 955 |
| (blank) -> Victoria Hunt (WA Senate) | 455 |
| (blank) -> Chedrick Greene (MI Senate) | 46 |

## Total

**5,134 vote records corrected, across 3 states and 11 legislators**, run for real on
2026-08-19. Every script's post-run `--dry-run` confirmed zero rows remaining in its
scope.

| Ticket | Rows |
|---|---|
| OPEN-110 | 423 |
| OPEN-113 | 2,202 |
| OPEN-114 | 430 |
| OPEN-115 | 623 |
| OPEN-116 | 1,456 |
| **Total** | **5,134** |

Legislators affected (misattribution corrected, 8 people): Carlos Smith, Dave
Smith, Julio Cortes, Adrian Cortes, Michelle Valdez, Javier Valdez, Pat Outman,
Rick Outman.

Legislators affected (blank votes filled in, 3 people): Ileana Garcia, Victoria
Hunt, Chedrick Greene.

## Scripts, for reference

- `fix-open110-fl-smith-vote-misattribution.py`
- `fix-open113-wa-cortes-valdez-vote-misattribution.py`
- `fix-open114-mi-outman-vote-misattribution.py`
- `fix-open115-fl-smith-senate-vote-misattribution.py`
- `fix-open116-blank-voter-id-same-surname-backfill.py`

All five are safe to re-run (each re-checks its own preconditions and matches only
rows still in the wrong state), and all five now report zero affected rows as of
this writing.
