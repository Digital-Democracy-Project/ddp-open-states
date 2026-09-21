# Need a direct DB check: why does resolve_person() fail on a *correct, unique* bioguide identifier for same-surname House members?

**Date:** 2026-09-21
**Thread:** VOTEBOT-7 / OPEN-2. Follow-up to `hr9576-vote-party-unknown-followup-questions-20260921.md`
and `us-legbot-trigger-request-better-error-logging-20260921.md`'s HR9576 side-note (both this branch).
**Ask:** run the queries below directly against the RDS `openstates` database (or via Django shell
if that's more available) and report back the raw results. This is the one thing blocking closing
out the House half of VOTEBOT-7/OPEN-2.

## What's confirmed so far (full chain, so this doesn't need re-deriving)

* The deployed `ddp-scrapers:v25` image (pulled and inspected directly) has the fully correct,
  current code for both `openstates-core` (`resolve_person()` incl. the OPEN-112 cache-key fix)
  and `openstates-scrapers` (bioguide/lis_id passthrough for House/Senate). Not a code or deploy
  problem.
* The **Senate** case is fully explained already (separate note, not what this one's about): no
  `lis`-scheme `PersonIdentifier` rows exist for senators at all, and the name-matching fallback
  can't work either since Senate voter names are `"Lastname (Party-State)"`.
* The **House** case is different and still open: the ~95-97 always-unresolved voters on every
  House floor vote checked (spanning 2026-06-04 through 2026-09-16, 3.5+ months, identical name
  list each time) are exactly and only the members who share a surname with another sitting
  member. Verified this isn't bad data for at least two of them:
  - Aaron Bean: bioguide `B001314` stored correctly (`/people?jurisdiction=us&name=Bean` via
    api-v3), matches `clerk.house.gov/evs/2026/roll309.xml`'s real `name-id="B001314"` for
    "Bean (FL)" exactly.
  - Buddy Carter: bioguide `C001103`, same result — matches the real Clerk XML exactly.

So the identifier itself is unique, correct, and present. Something about `resolve_person()`'s
actual query — `Person.objects.filter(Q(identifiers__identifier=identifier) & common_spec)` in
`openstates/importers/base.py` — still doesn't resolve to exactly one person for these two,
despite that. Can't go further without seeing the real query result, which needs DB access this
host doesn't have from here.

## The exact query to run (reproduces what resolve_person() does for Bean's House vote)

```sql
-- 1. Confirm B001314 maps to exactly one person (rule out a duplicate/reused identifier)
SELECT person_id FROM opencivicdata_personidentifier WHERE identifier = 'B001314';

-- 2. Reproduce resolve_person()'s actual filter for a House ("lower") vote on HR9576's session
--    (jurisdiction_id and lower-chamber org_classification are hardcoded for this jurisdiction/chamber;
--    swap in the real 119th-Congress session start_date/end_date if known, otherwise omit that AND clause
--    to see the unfiltered result first)
SELECT DISTINCT p.id, p.name, p.family_name
FROM opencivicdata_person p
JOIN opencivicdata_personidentifier pi ON pi.person_id = p.id AND pi.identifier = 'B001314'
JOIN opencivicdata_personmembership pm ON pm.person_id = p.id
JOIN opencivicdata_organization o ON pm.organization_id = o.id
WHERE o.jurisdiction_id = 'ocd-jurisdiction/country:us/government'
  AND o.classification = 'lower';

-- 3. If (2) returns more than one row/person, that's the smoking gun (ambiguous match despite a
--    unique identifier) -- also dump Bean's own membership rows to see why:
SELECT pm.id, o.name, o.classification, pm.start_date, pm.end_date
FROM opencivicdata_personmembership pm
JOIN opencivicdata_organization o ON pm.organization_id = o.id
WHERE pm.person_id = (SELECT person_id FROM opencivicdata_personidentifier WHERE identifier = 'B001314' LIMIT 1);
```

If direct SQL isn't available but a Django shell is (e.g. `os-update shell` or equivalent inside
the `ddp-scrapers` image against the real `DATABASE_URL`), the equivalent ORM call is even better
since it's the literal code path:

```python
from openstates.data.models import Person
from django.db.models import Q
list(Person.objects.filter(
    Q(identifiers__identifier="B001314") &
    Q(memberships__organization__jurisdiction_id="ocd-jurisdiction/country:us/government") &
    Q(memberships__organization__classification="lower")
).values("id", "name", "current_role"))
```

## Why this matters

If this returns >1 person, the fix is probably a `.distinct()` or a rework of how `common_spec`
combines two separate reverse relations in one filter. If it returns exactly 1, the bug is
somewhere else entirely (worth knowing before guessing at a fix) — possibly in how the pseudo-id
gets built or parsed for these specific votes, not in `resolve_person()`'s query at all.

Reply on this branch as usual — no urgency, just the next thing blocking closing this out.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
