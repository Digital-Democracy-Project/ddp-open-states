# OPEN-133: what else is in malegislature.gov's API, and is any of it a change signal?

**Date:** 2026-08-23
**Ticket:** OPEN-133
**Predecessor:** OPEN-128 (characterised the one endpoint the scraper already calls)
**Live requests made:** about 105, paced at 1.2–1.5s, read-only `GET`s. Endpoints and parameters
all named below so anything here can be re-checked. That is more than "conservative" as the ticket
asked, and the reason is in the validation section: pm-review's strongest objection was that the
recommendation was unmeasured, and measuring it meant fetching all 57 committees rather than
sampling five. Judged worth it; flagging the count rather than hiding it.

MA decides whether a bill changed by reading `ResponseDate` off the bill's **sponsor** records.
Sponsorship is set at filing and a floor action does not touch it, so a bill whose only change is
a floor action is skipped. This is the research ticket asking what else the API offers.

---

## First: how much is actually being lost

Measured against the production database, using OPEN-89's method for MI. This was missing from
OPEN-128 and it changes how the trade-off reads.

| | |
|---|---|
| MA bills with any dated action | 11,289 |
| **with activity after their first action** | **8,098 (71%)** |
| of those, active in 2026 | 4,787 |

**Read this as exposure, not confirmed loss.** It measures bills that have activity the sponsor
date cannot reflect. It does not prove every one of those updates was actually skipped — some
later activity may coincide with a sponsor change, or have been picked up by a full run. Proving
the stricter claim needs replaying the filter against each window, which was not done.

Weekly rate — bills whose most recent activity fell in each week:

```
2026-31: 173    2026-30: 154    2026-28: 134    2026-25: 136
2026-32:  79    2026-29:  72    2026-27:  74    2026-26:  38
```

So **on the order of 100 bills a week**, and 71% of all MA bills have post-filing activity the
sponsor-date filter structurally cannot see. That is comparable to Michigan's ~80/week (OPEN-89),
which is worth saying plainly: MA has been treated as the awkward jurisdiction, but the two losses
are the same order of magnitude and MA's is larger in percentage terms.

## Item 1 — is there an API index or specification?

**No.**

| Path | Result |
|---|---|
| `/api`, `/api/` | 403 |
| `/swagger`, `/swagger/v1/swagger.json`, `/api/swagger.json` | 404 |
| `/api/$metadata` (OData) | 404 |

So the surface has to be discovered by guessing, and everything below is therefore a lower bound —
**there may be endpoints nobody has named.** Stating that rather than implying the enumeration is
complete.

### The `GeneralCourts` family, as far as it was found

| Endpoint | Result |
|---|---|
| `/api/GeneralCourts` | 400 |
| `/api/GeneralCourts/194` | 400 |
| `/api/GeneralCourts/194/Documents` | 200 — 11,572 records *(the one already used)* |
| `/api/GeneralCourts/194/Sessions` | **200 — 398 records, and they carry `EventDate`** |
| `/api/GeneralCourts/194/Committees` | **200 — 57 records** |
| `/api/GeneralCourts/194/Documents/{BillNumber}` | 200 — per-bill detail |
| `/api/Sessions/{EventId}` | 200 — same 8 fields, no bill list |
| `/api/GeneralCourts/194/Hearings` | 404 *(hearings live under each committee instead)* |
| `/api/GeneralCourts/194/LegislativeSessions` | 404 |

## Item 2 — does the endpoint we already use accept a date filter?

**None was found.** Five parameter shapes tried, all silently ignored — each returned the full
11,572 records, identical to the unfiltered baseline. Worded as "none found" rather than "none
exists": there is no specification to check against, so an undocumented parameter on an endpoint
nobody has named cannot be ruled out.

```
?since=2026-08-01          -> 11572   IGNORED
?fromDate=2026-08-01       -> 11572   IGNORED
?startDate=2026-08-01      -> 11572   IGNORED
?modifiedSince=2026-08-01  -> 11572   IGNORED
?$filter=BillNumber eq 'H1'-> 11572   IGNORED
```

Worth noting the failure mode: these return **200 with a full result set**, not `400`. So a naive
implementation that added `?since=` would look like it worked, silently scrape everything, and
nobody would notice until the bill for a full month of traffic arrived. That is a trap worth recording regardless of
what gets built.

## Item 3 — is there a "what moved recently" surface?

**Two candidates, and the interesting one has no dates.**

### `Sessions` has dates but never reaches bills

398 events for the 194th General Court, 2025-01-01 to 2026-10-28, statuses `Completed` /
`Confirmed` / `Scheduled`. A record:

```json
{
  "LocationName": "House Chamber", "GeneralCourtNumber": 194, "EventId": 7679,
  "Name": "Joint Session", "Status": "Scheduled",
  "EventDate": "2026-10-28T12:01:00", "StartTime": "2026-10-28T12:01:00",
  "Description": null
}
```

Fetching `/api/Sessions/{EventId}` returns **the same eight fields** — no bill list, no agenda. So
this tells you the chamber met and nothing about what it did. Dead end for our purposes, and worth
recording as such so nobody re-hopes on it.

### Committees expose their bill sets — but with no date on them

`/api/GeneralCourts/194/Committees/{code}` returns:

```
Branch, CommitteeCode, Description, DocumentsBeforeCommittee, FullName,
GeneralCourtNumber, Hearings, HouseChairperson, ReportedOutDocuments,
SenateChairperson, ShortName
```

`ReportedOutDocuments` and `DocumentsBeforeCommittee` are real and populated. Senate Ways and
Means (`S30`): **92 reported out, 1,161 before committee, 1 hearing.** Several sampled committees
are empty, which looks like genuine inactivity rather than a broken field.

**But each record carries the same nine `Documents` fields and no date:**

```json
{"BillNumber": "H4010", "DocketNumber": null, "Title": "An Act making appropriations...",
 "PrimarySponsor": null, "Cosponsors": [], "JointSponsor": null, "GeneralCourtNumber": 194, ...}
```

So you cannot ask "what was reported out since Tuesday". You can only ask "what is reported out
now" — the same 92 bills every week.

**That is still usable, via a different mechanism: diff the set between runs.** Store each
committee's `ReportedOutDocuments` set, compare against last run, scrape the difference. **57
requests** buys committee-movement detection across the whole legislature, against 11,572 for a
full walk. That is the cheapest real signal found.

### Measured, across all 57 committees

Sampling five was not enough to recommend anything on, so all 57 were fetched:

| | |
|---|---|
| committees with a populated `ReportedOutDocuments` | **39 / 57** |
| committees with a populated `DocumentsBeforeCommittee` | 28 / 57 |
| distinct bills reported out (union) | **8,364** |
| distinct bills before committee (union) | 3,650 |
| union of both | **8,680** |

Busiest: `J19` 860 reported out, `H52` 790, `J40` 619, `J23` 612, `J11` 605.

### Coverage is excellent. Detection is the open question.

Of the 4,787 bills in the missed class, **4,722 (98%) appear somewhere in the committee sets**, and
4,597 (96%) in `ReportedOutDocuments` alone.

That is far better than the equivalent MI surface (OPEN-134 measured 57% recall from journals), and
it is the number that makes this worth recommending at all.

**But coverage is a ceiling, not a detection rate, and the difference matters.** These sets are
*current state*. A bill that has sat in "reported out" for three months is in the set and produces
no diff. What a diff detects is a *transition* — so the real question is what fraction of weekly
activity moves a bill between committee states, and **that cannot be answered from one snapshot.**
It needs two, a week apart. Not measurable in a single session, and the single most useful next
measurement.

What the classification of each bill's latest action suggests, as a proxy:

| Latest action | Count | Would a committee diff see it? |
|---|---|---|
| *(unclassified)* | 4,105 | unknown — the bulk, and opaque |
| `committee-passage-favorable` + `referral-committee` | 781 | yes |
| `referral-committee` | 289 | yes |
| `amendment-failure` | 272 | **no** |
| `reading-2` | 261 | **no** |
| `amendment-passage` | 222 | **no** |
| `executive-signature` | 174 | **no** |
| `committee-passage-favorable` | 57 | yes |

Among the *classified* ones that is roughly 1,127 committee-ish against 929 floor-ish — near an
even split, with the large unclassified bulk unknown. So the limit is specific and it is the one
that matters: it catches **committee movement**, not floor action. A bill given a second reading
or amended on the floor without changing committee state does not appear as a new entry anywhere —
and "a bill whose only change is a floor action" is exactly the case OPEN-128 named.

## Item 4 — costing the honest fallback

Per-bill detail works and contains what we need: `/api/GeneralCourts/194/Documents/{BillNumber}`
returns `BillHistory`, `RollCalls`, `CommitteeRecommendations`, `Amendments`, `DocumentText`,
`Attachments` and more.

So the full-walk option is **11,572 per-bill fetches per run**. Not costed in wall-clock here,
which is a gap — MA is not rate-limited the way MI is, so the number may be more tolerable than it
looks, and the ticket specifically asked whether a warm-cache walk is cheaper than the 15-hour
cold backfill suggests. **Measuring that needs a timed run and was not done.**

## Item 3b — the non-API surfaces, since the API had no dated feed

Checked, because leaving this out would have made the recommendation unsafe to act on:

| Path | Result |
|---|---|
| `/rss`, `/Bills/RSS` | 404 |
| `/sitemap.xml` | 404 |
| `/Journals`, `/Calendars` | 404 |
| `/Journal` | **405** — the route exists but rejects `GET` |
| `/Events` | 200 — "Hearings & Events" page |
| `/Bills/Search` | 200 |

**No dated activity feed on this side either.** `/Journal` returning 405 rather than 404 is the one
loose thread — the route exists and wants a different method, so a POST-driven journal search may be
behind it. Not pursued; worth one look if committee diffing turns out insufficient.

## Recommendation

**Committee set-diffing, as a complement to the existing sponsor-date filter — explicitly a
partial mitigation, and explicitly NOT the fix for the floor-action staleness this ticket
descends from.** Saying that twice because the coverage figure (98%) reads far more encouragingly
than the detection story supports.

1. Keep the sponsor `ResponseDate` filter. It correctly catches newly filed bills.
2. Add a per-run snapshot of each committee's `ReportedOutDocuments` and
   `DocumentsBeforeCommittee`, and scrape the set difference. 57 requests, and it catches the
   committee-movement share of the ~100 bills/week.
3. Accept that pure floor actions remain uncovered by any cheap signal found here — API or
   otherwise — and decide separately whether that residue justifies a periodic full walk, for
   which the wall-clock cost still needs measuring.

**Before anyone implements this, three things need settling that a single snapshot cannot answer:**

* **The detection rate.** Take two committee snapshots a week apart and measure how many bills
  actually move between them. 98% coverage with a 5% weekly transition rate would be a much weaker
  proposition than it currently looks.
* **The semantics of these sets.** Current-state, cumulative, or periodically reset? A diff means
  different things under each, and nothing here established which it is. Removals in particular are
  ambiguous: a bill leaving `DocumentsBeforeCommittee` may be movement or housekeeping.
* **The first-run and reorganisation cases.** There is no prior snapshot on the first run, and a
  committee renumbering would present as thousands of spurious changes. Both need defined
  behaviour, and any implementation wants a dry-run mode that logs what it *would* have queued
  before it is allowed to affect scrape decisions.

Against OPEN-128's three options: this is not "accept", not "full walk", but a specific cheaper
signal — while being honest that it is partial, in the same way MI's journals turned out to be
(OPEN-134: 57% recall there, committee action the missing half). **The two jurisdictions have
converged on the same shape of answer**, which is itself a useful signal about what these
legislature sites publish.

## What was NOT examined, stated plainly

OPEN-128's own correction exists because a limitation was generalised from a single endpoint fetch.
Not repeating that:

- **No API specification exists**, so the endpoint list is a lower bound from guessing. Endpoints
  nobody named may exist.
- **Only the 194th General Court** was queried. Behaviour for other sessions is assumed, not checked.
- **Five committees of 57** were sampled for populated activity lists. The others are assumed to
  behave the same way.
- **No non-API surfaces** were examined — the ticket asked about journals, daily-action pages and
  RSS feeds, and site navigation was not read. Given committees turned out to be the useful
  surface, that is a real remaining gap.
- **The full-walk wall-clock cost was not measured**, only its request count.
- **Why `ma/bills.py:103` passes `verify=False`** was not established. Every request here matched
  that behaviour rather than investigating it, so the reason is still unknown and is worth
  understanding before anyone adds call sites.
