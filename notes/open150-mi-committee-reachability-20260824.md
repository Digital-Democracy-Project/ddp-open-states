# OPEN-150: is MI committee activity reachable? Yes — and the answer makes the journal plan unnecessary

**Date:** 2026-08-24
**Ticket:** OPEN-150 (blocking OPEN-134)
**Live requests made:** **one.** Everything below except the final live measurement came out of
the existing scrapelib cache, per the ticket's own instruction to read the cache before touching
the network.

## Answer

**Yes, committee activity is reachable — but not from a committee-specific surface, and the
surface that does carry it is one we were already fetching.**

The `ExecuteSearch` results page carries **every bill's own last action, in the row next to its
link**. Committee reports, administrative rows and floor business all appear there. So one
unfiltered request describes the recency of the whole corpus, and OPEN-134 does not need journals,
committee pages, or a periodic full walk.

This supersedes the journal design. It is not an incremental improvement on it — it removes the
need for it.

## How the results page is structured

Verbatim from a cached response:

```html
<tr>
  <td><a href="/Home/GetObject?objectName=2025-SB-0001">SB 0001 of 2025</a></td>
  <td>Senate Bill</td>
  <td>Civil rights: public records; ... TIE BAR WITH: SB 0002'25
      <br />Last Action: referred to Committee on Government Operations</td>
</tr>
```

The bill link is `td[1]`, and `td[3]` ends with `Last Action: <text>`. One cached unfiltered sweep
contains **3,752** such rows — the entire session.

Note the example: *"referred to Committee on Government Operations"* is a committee action, present
on the search page. That is the class of action the journals do not carry.

## Why this beats journals, measured

Classifying every last action in a cached full sweep (3,718 rows parsed by an early regex; the
committed xpath extractor gets all 3,752):

| Last-action shape | Count |
|---|---|
| **committee-ish** | **1,547** |
| **administrative** | **1,432** |
| other / floor | 739 |

**80% of the corpus's last actions are committee or administrative** — precisely the two categories
OPEN-150 established that journals structurally cannot see, and precisely the reason journal recall
measured only 57%.

## The comparison is exact, not fuzzy

The site's last-action string and our stored action description are **the same string**. Checked
across the cached full sweep against the production database:

| | |
|---|---|
| exact text match after whitespace/case normalisation | **3,685 / 3,718 (99.1%)** |
| differed | 33 |
| bills on the page but absent from our database | **0** |

All 33 differences were cases where the **database was newer than the cache** — not disagreements
about the same moment. So a mismatch is a reliable "this bill moved" signal rather than a
formatting artefact, and no fuzzy matching is needed.

## Live confirmation, and the gap as it actually stands

One live request, through the warmed cookie path:

```
live sweep: HTTP 200, 2,514,365 bytes   (1 request)
bills on page : 3924
bills in db   : 3924
*** BILLS WHOSE LIVE LAST ACTION DIFFERS FROM OURS: 187 ***
    of which absent from our db entirely: 0
```

The 187 are exactly the class `dateFrom=` cannot return — and several matter a great deal:

| Bill | What we had | What the site says |
|---|---|---|
| HB 4042 | placed on order of third reading | **assigned pa 89'26** |
| HB 4062 | referred to committee on oversight | **assigned pa 74'26 with immediate effect** |
| HB 4103 | placed on order of third reading with substitute (s-1) | **assigned pa 43'26 with immediate effect** |
| HB 4085 | re-referred to committee on communications and technology | rep. ron robinson removed as cosponsor |

**`assigned pa NN'26` is a Public Act assignment — the bill became law.** We were holding these as
still in committee or awaiting a third reading. That is the concrete cost of the OPEN-134 bug, and
it is worse than "80 stale rows a week" makes it sound.

Zero bills were missing from our database, so this is pure action drift, not a collection hole.

## Committee-specific surfaces, for the record

They exist, and the cache reveals them without a single request — the results page's own navigation
links to:

| Path | Label |
|---|---|
| `/Committees/CBRs` | **Committee Bill Records** |
| `/Committees/Meetings` | Committee Meetings |

"Committee Bill Records" is very likely the per-committee, per-bill record OPEN-150 set out to look
for. **It was not probed, because it turned out not to be needed** — the search page already
answers the recency question for the whole corpus in one request, and probing a WAF-sensitive site
for a surface we have no use for is unjustified. Recorded here so nobody re-derives their existence
from scratch; if a future ticket needs committee *membership* or *meeting agendas* (as opposed to
"which bills moved"), that is where to start.

## Consequence for OPEN-134

The architecture question the ticket was blocked on is settled, and neither of the two options it
contemplated is the answer:

- **not** daily journals (57% recall, many requests, misses committee and administrative entirely)
- **not** a periodic full walk (~3,752 per-bill fetches, ~6.3h at the 10 rpm cap)
- **instead**: one unfiltered sweep per run, diff each row's last action against the previous run,
  re-scrape only what moved. One request plus the bills that actually changed.

## What was NOT examined, stated plainly

- **`/Committees/CBRs` and `/Committees/Meetings` were never fetched.** Their existence is read off
  a cached page's navigation; their content, per-bill granularity, and whether they carry dates are
  all unverified.
- **Only session 2025-2026** was examined. The row structure is assumed stable across sessions, not
  checked.
- **`contentFullText`** — the ticket asked whether it reaches committee-report text. Not
  investigated, because the last-action field made it moot.
- **The 33 cache-vs-database differences** were inspected by sampling, not exhaustively classified.
  They were all consistent with database-newer-than-cache, but that is a sample-based claim.
- **No measurement of how often the last-action text changes without a substantive change** (e.g. a
  site-side re-wording). If that happens, it costs one wasted bill fetch, never a miss — the
  asymmetry is in the safe direction, but the rate is unmeasured.
