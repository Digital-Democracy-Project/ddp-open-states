# OPEN-150: is MI committee activity reachable? Yes — and the answer makes the journal plan unnecessary

**Date:** 2026-08-24
**Ticket:** OPEN-150 (blocking OPEN-134)
**Live requests made:** **one.** Everything below except the final live measurement came out of
the existing scrapelib cache, per the ticket's own instruction to read the cache before touching
the network.

## Two row counts appear below, and they are not the same measurement

**3,752** is what the committed xpath extractor (`_extract_last_actions`) reads off the cached
sweep. **3,718** is what a throwaway regex read while exploring, before the extractor existed;
the regex missed 34 rows whose markup it did not anticipate. The classification and
database-comparison tables below were computed with the regex and so are stated over 3,718; the
extractor's own count is 3,752 and it is the number the implementation relies on. Neither figure
is wrong — they are different tools — but the tables are a 99.1% sample of the corpus rather
than all of it, and that is worth knowing before leaning on the percentages.

## Answer

**Yes, committee activity is reachable — but not from a committee-specific surface, and the
surface that does carry it is one we were already fetching.**

To be explicit about the acceptance criteria: **no per-day or per-committee surface was
verified.** OPEN-150 asked whether one exists, expecting that OPEN-134 would need it. It turns
out OPEN-134 does not: an already-fetched *global* search surface carries the committee movement,
so the per-committee question is moot for this purpose rather than answered.

The exact request, unfiltered — no `dateFrom`, no `dateTo`:

```
https://legislature.mi.gov/Search/ExecuteSearch
  ?chamber=
  &docTypesList=HB%2CSB&docTypesList=HR%2CSR
  &docTypesList=HCR%2CSCR&docTypesList=HJR%2CSJR
  &sessions=2025-2026
  &sponsor=&number=&dateFrom=&dateTo=&contentFullText=
```

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

Classifying every last action in a cached full sweep (the 3,718-row regex read — see the note on
row counts above):

| Last-action shape | Count |
|---|---|
| **committee-ish** | **1,547** |
| **administrative** | **1,432** |
| other / floor | 739 |

**Roughly 80% of last actions are committee or administrative** — the two categories OPEN-150
established that journals structurally cannot see, and the reason journal recall measured only
57%.

**The classification rule is crude, and the 80% rests on it, so here it is verbatim:** the text
was bucketed as committee-ish if it contained the substring `committee`; else administrative if
it contained `reproduced`, `assigned` or `printed`; else floor. Nothing more. That is good enough
to answer "do journals miss the majority" — the two buckets are separated by a wide margin, and
`referred to Committee on Government Operations` or `assigned pa 74'26` are not borderline — but
it is not a taxonomy. Borderline rows were not adjudicated, and a row mentioning a committee
incidentally would be miscounted. Treat 80% as an order-of-magnitude finding, not a statistic.

## The comparison is exact, not fuzzy

The site's last-action string and our stored action description are **the same string**. Checked
across the cached full sweep against the production database:

| | |
|---|---|
| exact text match after whitespace/case normalisation | **3,685 / 3,718 (99.1%)** |
| differed | 33 |
| bills on the page but absent from our database | **0** |

The 33 differences were **inspected by sampling, not exhaustively classified.** Every one sampled
was the **database being newer than the cache** — the cache predates a later import — rather than
a disagreement about the same moment. That is consistent with a reliable signal and no fuzzy
matching, but the exhaustive claim is not made: 33 rows were not individually adjudicated, so the
honest statement is "no counter-example was found in the sample", not "none exists".

What the 99.1% does establish firmly is the thing that matters: the two strings are drawn from
the same vocabulary and the same formatting, so a mismatch is not an artefact of comparing a
site rendering against a differently-shaped database field.

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
- **The inverse — a false NEGATIVE — is the one real hole in the design, and it is unmeasured.**
  If a bill's later substantive action renders to text identical to the one already stored, the
  diff sees nothing and the bill is skipped. Michigan plainly can repeat a string: "referred to
  Committee on Rules" could occur twice, and a re-referral to the same committee is a normal
  legislative event. Whether that ever happens as two *consecutive* last actions with no
  distinguishable row in between was not established, and the search row carries no date or
  sequence number to disambiguate it. The periodic full scrape is the backstop; this path is
  explicitly about the ~80/week the date filter made structurally invisible, not about
  guaranteeing every edit is seen.
- **The 3,924-to-3,924 live comparison was not proven as set equality in both directions.** What
  was checked is that no bill on the page was absent from the database, and that the two totals
  are equal. Together those imply set equality, but the reverse direction (a database bill
  missing from the page) was not tested directly.
- **The row structure is assumed to be unpaginated.** The sweep returns the whole session in one
  response, which is what makes the approach cheap; behaviour if the site introduces pagination,
  suppresses rows, or returns a partial response under WAF pressure was not tested. The
  implementation (`openstates-scrapers` #41) fails closed on this rather than assuming: if the
  page lists bills but fewer than 95% of them yield a parseable last action, it aborts without
  touching its baseline instead of concluding that nothing moved. It also refuses to run
  incrementally with no baseline, rather than seeding from the site and silently marking stale
  bills current.
