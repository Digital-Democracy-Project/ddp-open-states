# OPEN-133: what else is in malegislature.gov's API, and is any of it a change signal?

**Date:** 2026-08-23
**Ticket:** OPEN-133
**Predecessor:** OPEN-128 (characterised the one endpoint the scraper already calls)
**Live requests made:** about 105, paced at 1.2–1.5s, read-only `GET`s. Endpoints and parameters
all named below so anything here can be re-checked. That is more than "conservative" as the ticket
asked, and the reason is in the validation section: pm-review's strongest objection was that the
recommendation was unmeasured, and measuring it meant fetching all 57 committees rather than
sampling five. Judged worth it; flagging the count rather than hiding it.

**Corrected 2026-08-23**, after review found the document contradicted itself. Four fixes. Three of
them make this file less confident than it was; the first cuts the other way, and that is worth
being explicit about rather than presenting every correction as a retreat:

1. The latest-action classification table was wrong — several rows (`amendment-failure` 272,
   `amendment-passage` 222, `committee-passage-favorable` 57) did not survive re-derivation against
   the database, and no denominator was stated. Replaced with the complete breakdown. The corrected
   committee-vs-floor split is **70/30, not "near an even split"** — which *strengthens* the
   recommendation, so the error was not in a self-serving direction, but it was an error.
2. The weekly loss rate was a mean over eight selected weeks. Restated with the window, mean,
   median and range, and the Michigan comparison softened accordingly.
3. Two "what was NOT examined" bullets contradicted the body: they claimed five of 57 committees
   were sampled when all 57 were fetched, and claimed no non-API surfaces were examined when Item 3b
   examines seven.
4. Added the 69%-unclassified caveat wherever the split is quoted.

All database figures here are re-derivable from a read-only query over `opencivicdata_bill` /
`opencivicdata_billaction`, joined through `opencivicdata_legislativesession` and filtered to
`jurisdiction_id LIKE '%state:ma%'`. Rows with a null or empty `date` are dropped. Each bill's first
and last action are `MIN(date)` and `MAX(date)`; the "missed class" is `last_date > first_date`, and
the 2026 subset adds `last_date >= '2026'` (`date` is a `character varying`, so these are string
comparisons on `YYYY-MM-DD` — which sorts correctly, but is worth knowing). "Latest action" is
disambiguated by `DISTINCT ON (bill_id) ... ORDER BY bill_id, "order" DESC` among the actions on
that last date — `order` being the integer column openstates uses to sequence same-day actions.

---

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

Weekly rate — bills whose most recent activity fell in each week, over the ten complete weeks
2026-23 to 2026-32:

```
2026-32:  79    2026-31: 173    2026-30: 154    2026-29:  72    2026-28: 134
2026-27:  74    2026-26:  38    2026-25: 136    2026-24:  34    2026-23:  77
```

**Mean 97, median 78, range 34–173.** The variance is large enough that a single figure misleads, so
both are given. Weeks 2026-33 and later are excluded as incomplete (they return 1 and 4, which is
collection lag, not a quiet legislature) — and excluding them is a judgement that flatters the
numbers slightly, so it is stated rather than buried.

So **roughly 80–100 bills a week depending on which statistic you take**, and 71% of all MA bills
(8,098 of the 11,289 with any dated action) have post-filing activity the sponsor-date filter
structurally cannot see. On the weekly count that
is close to a tie with Michigan's ~80/week (OPEN-89) rather than clearly worse; where MA is
genuinely worse is the *proportion* — 71% of its bills are exposed. MA has been treated as the
awkward jurisdiction, and the fair statement is that the two losses are the same order of magnitude.

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
Means (`S30`): **92 reported out, 1,161 before committee, 1 hearing.** 18 of the 57 have an empty
`ReportedOutDocuments`, which looks like genuine inactivity rather than a broken field.

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
4,597 (96%) in `ReportedOutDocuments` alone. That is a *presence* figure — how many of the missed
bills the committee surface knows about at all. It is not a recovery figure, and the next two
sections are about why the gap between those matters.

That is far better than the equivalent MI surface (OPEN-134 measured 57% recall from journals), and
it is the number that makes this worth recommending at all.

**But coverage is a ceiling, not a detection rate, and the difference matters.** These sets are
*current state*. A bill that has sat in "reported out" for three months is in the set and produces
no diff. What a diff detects is a *transition* — so the real question is what fraction of weekly
activity moves a bill between committee states, and **that cannot be answered from one snapshot.**
It needs two, a week apart. Not measurable in a single session, and the single most useful next
measurement.

What the classification of each bill's latest action suggests, as a proxy. This is the **complete**
breakdown over the 4,787 bills in the 2026 missed class — every row, not a top-N, so the counts sum
to the denominator:

| Latest action | Count | Would a committee diff see it? |
|---|---|---|
| *(unclassified)* | 3,292 | unknown — the bulk, and opaque |
| `committee-passage-favorable` + `referral-committee` | 776 | yes |
| `referral-committee` | 250 | yes |
| `reading-2` | 234 | **no** |
| `executive-signature` | 174 | **no** |
| `committee-passage-unfavorable` + `referral-committee` | 17 | yes |
| `reading-1` + `reading-2` | 14 | **no** |
| `amendment-passage` | 11 | **no** |
| `passage` | 8 | **no** |
| `passage` + `reading-3` | 5 | **no** |
| `committee-passage-favorable` | 5 | yes |
| `amendment-passage` + `reading-2` | 1 | **no** |
| **total** | **4,787** | |

Among the *classified* ones that is **1,048 committee-ish against 447 floor-ish — roughly 70/30 in
favour of committee movement**, with the large unclassified bulk (69% of the class) unknown. So the
limit is specific and it is the one that matters: it catches **committee movement**, not floor
action. A bill given a second reading or amended on the floor without changing committee state does
not appear as a new entry anywhere — and "a bill whose only change is a floor action" is exactly the
case OPEN-128 named.

Two things about that split are worth stating rather than leaving implied. It runs *in favour* of the
recommendation — most classified activity in this class is committee activity, so the share a diff
could in principle see is the larger one. But 69% of the class is unclassified, which is more than
the committee and floor shares combined, so the split is computed over less than a third of the
population and should not be read as "70% of the loss is recoverable."

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
   `DocumentsBeforeCommittee`, and scrape the set difference. 57 requests, and it is *aimed at* the
   committee-movement share of the ~80–100 bills/week — the larger share of the classified
   activity, but an unknown share of the unclassified 69%. "Aimed at" and not "catches": the
   detection rate is unmeasured, and until the two-snapshot test below is run, no claim about what
   this actually catches is supportable.
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
- **The detection rate is unmeasured.** All 57 committees were fetched, so coverage is measured, but
  a single snapshot cannot show how many bills move between snapshots. This is the gap that matters
  most and it is restated in the recommendation above.
- **The non-API surfaces were probed, not explored.** Seven paths were checked by URL (Item 3b) and
  none exposed a dated feed, but site navigation was never actually read, so a dated page that is
  linked rather than guessable would have been missed. `/Journal` returning 405 is the specific
  loose end.
- **The full-walk wall-clock cost was not measured**, only its request count.
- **69% of the missed class has no action classification**, so the committee-vs-floor split is
  computed over under a third of the population.
- **Why `ma/bills.py:103` passes `verify=False`** was not established. Every request here matched
  that behaviour rather than investigating it, so the reason is still unknown and is worth
  understanding before anyone adds call sites.
