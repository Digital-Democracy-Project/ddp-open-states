# OPEN-137: MI's single-match redirect, confirmed against the live site — and the dropped bill was never lost

**Date:** 2026-08-25
**Ticket:** OPEN-137 (split out of OPEN-132)
**Live requests:** **11**, paced, through the warmed WAF cookie path. Every URL is named below.

## Summary

All three items answered. Two of the three came out differently from how the ticket framed them, and
both differences matter more than the confirmations do.

| Item | Result |
|---|---|
| 1. A live one-match window returns its bill | **Confirmed** — but not reachable by `dateFrom` any more, and no longer reachable in production at all |
| 2. A genuinely empty window yields nothing, distinguishably | **Confirmed live** |
| 3. Recover `SR 135`, dropped 2026-07-25 | **No recovery needed — it was never missing** |

## Item 3 first, because it changes what this ticket is for

`SR 135` **is in the production database, and its data is complete.**

```
identifier : SR 135        session: 2025-2026
created_at : 2026-07-11 22:04:52 UTC
actions    : 3
```

Its three stored actions match the live bill page exactly, field for field:

| Stored | Live page |
|---|---|
| `2026-07-29  INTRODUCED BY SENATOR JOHN CHERRY` | `7/29/2026  INTRODUCED BY SENATOR JOHN CHERRY` |
| `2026-07-03  RULES SUSPENDED` | `7/03/2026  RULES SUSPENDED` |
| `2026-07-03  ADOPTED` | `7/03/2026  ADOPTED` |

The bill was created on **2026-07-11**, a fortnight *before* the 2026-07-25 incident. So what the
incident cost was an **update opportunity**, not the bill: that run failed to return `SR 135` from
its search, and had `SR 135` changed that day we would have missed the change. It did not, so
nothing was lost.

This is worth stating plainly because the ticket says "recover the bill dropped on 2026-07-25" and
the wording invites a re-scrape that would have been a no-op. Ramon approved a production write for
this; it turned out not to be needed and none was made.

Incidentally, note the ordering: `INTRODUCED` is dated 2026-07-29, *after* `ADOPTED` on 2026-07-03.
That is what the site itself publishes. It is the same date-versus-`order` disagreement OPEN-134 hit
(`order` is authoritative, dates are not monotonic), showing up on a second bill.

## Item 1 — the redirect is real, and the fixture premise still holds

**The window in the original fixture has healed.** `dateFrom=2026-07-19` returned exactly one bill on
2026-07-25; today it returns **41 rows**. So the incident cannot be replayed by re-issuing the
original URL, and any future attempt to do so will silently test nothing.

**No `dateFrom` value can produce a one-match window right now.** Probing the boundary:

| `dateFrom` | result rows |
|---|---|
| 2026-07-19 | 41 |
| 2026-08-05 | 14 |
| 2026-08-08 | 14 |
| 2026-08-10 | 14 |
| 2026-08-11 | 14 |
| 2026-08-12 | **0** |
| 2026-08-15 | 0 |
| 2026-08-20 | 0 |

The count falls 14 → 0 between 2026-08-11 and 2026-08-12 with no intermediate value, because all 14
of the most recent bills share a single introduction date. `dateFrom` has day granularity, so there
is no window between "14 bills" and "no bills".

**Narrowing by bill number instead reproduces it exactly** — and lands on the incident bill itself:

```
GET /Search/ExecuteSearch?...&docTypesList=SR&number=135&dateFrom=&dateTo=
  -> HTTP 200
  -> result rows: 0
  -> redirected to: /Bills/Bill?ObjectName=2026-SR-0135
  -> heading: "Senate Resolution 135 of 2026"
```

Zero result rows plus a bill page: precisely the shape OPEN-132's branch exists to handle, and
precisely what made 2026-07-25 look like a clean empty week.

**Our code resolves it correctly from that live response:**

```
_redirected_single_bill() -> ('SR 0135', 'https://legislature.mi.gov/Bills/Bill?ObjectName=2026-SR-0135')
_mi_bill_id_to_no('SR 0135') -> 'SR135'      # the incident bill
```

So the fix works end to end against the live site, not only against the cached fixture.

## Item 2 — an empty window is distinguishable, live

`dateFrom=2026-08-20` returns a **real results page with zero rows and no redirect**. That is the
third of OPEN-132's three cases, and the scraper logs it distinctly:

> `MI search returned a results page with no matching bills -- genuine empty result for this window`

Observed firing on a real run on 2026-08-24. So the three cases are separated in the log as OPEN-132
intended: redirect-to-bill, genuine-empty, and unrecognised-page.

## The finding that outlives this ticket

**OPEN-134 has made this branch unreachable in production.**

That fix removed `dateFrom` from the scraper's search entirely — every run now sweeps the whole
corpus unfiltered and diffs last-action text instead. An unfiltered search returns ~3,924 rows, so
`links` is never empty, so `_redirected_single_bill()` never runs.

The branch is still **correct**, still **tested**, and still guards a **live site behaviour** proven
above. But its production coverage is now zero, and that has two consequences worth recording rather
than discovering later:

* **The tests are the only thing keeping it honest.** OPEN-132 shipped 11 tests, 10 of which fail
  against unfixed code. Those are now the sole protection; production traffic will not exercise this
  path again unless something re-narrows the search server-side.
* **Do not delete it as dead code.** It is one `dateFrom=` away from being load-bearing again, and
  the behaviour it handles is live today. A future change that reintroduces any server-side narrowing
  — a date filter, a chamber filter, a `number=` lookup — walks straight back into the 2026-07-25
  failure without it.

## Request budget

11 live requests total:

* 1 — `SR 135` bill page, to compare against the database
* 8 — `dateFrom` boundary probes (2026-07-19, 08-05, 08-08, 08-10, 08-11, 08-12, 08-15, 08-20)
* 2 — number-narrowed searches (`number=135` across `HR,SR`, then `SR` alone)

All 200s, no WAF blocks, no retries, paced with 7-8s gaps. Well inside the ticket's "smallest number
of requests that answers the question", and far inside the ~3,800-request full scrape it forbids.

## What was NOT done

* **No production write.** Approved but unnecessary — see item 3.
* **No full scrape**, per the ticket's hard constraint.
* **The one-match case was not driven through `run-scrape.sh` end to end.** It was proven at the two
  levels that matter — the site still redirects, and `_redirected_single_bill()` resolves the bill
  from that live response — but not by a full scraper invocation, because post-OPEN-134 no scraper
  invocation can produce a one-match page. Driving it would have meant temporarily reintroducing the
  very `dateFrom` filter OPEN-134 removed.
* **Whether 14 bills sharing one introduction date is normal for MI** was not investigated. It is
  what made a one-match `dateFrom` window unobtainable today; it may well be obtainable during a
  quieter part of the session.
