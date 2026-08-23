# OPEN-134: what signal can MI actually give us for "recently acted on"?

**Date:** 2026-08-23
**Ticket:** OPEN-134 — MI incremental scrapes miss ~80 bills a week
**Predecessor:** OPEN-89 (`notes/open89-mi-date-signal-verification-plan-20260822.md`, PR #154)
**Requests made to legislature.mi.gov: zero.**

OPEN-134 sets out three investigation steps before any fix, and a hard constraint: read the cache
first, the way OPEN-89 did. All three steps are answered below from the scrapelib cache alone
(105,347 entries, 2.7 GB), with no network traffic against the fleet's most WAF-sensitive site.

---

## Step 1 — Does MI's search accept a last-action-date parameter?

**No.**

The results page re-renders the search form, so a cached `ExecuteSearch` response contains the
form itself. Every field it offers:

| Field | Type |
|---|---|
| `chamber` | hidden |
| `docTypes` | hidden |
| `sessions` | hidden |
| `sponsor` | hidden |
| `number` | hidden |
| `dateFrom` | hidden |
| `dateTo` | hidden |
| `contentFullText` | hidden |
| `searchWithin` | text |

Nothing matching `action`, `status`, `updated`, `modified`, `last` or `change`. The only date
parameters are `dateFrom`/`dateTo`, and OPEN-89 established those filter on **introduction**
date — which is the bug.

**Caveat, stated rather than buried:** these are all `hidden` inputs echoing the submitted query,
so this proves what the form *offers*, not the full set the server would *accept*. An
undocumented parameter cannot be ruled out from cache. Confirming that would take live probing
against a WAF-sensitive endpoint for a speculative payoff, which is not obviously worth it — but
it is the one stone left unturned here, and a few paced requests would settle it if someone wants
certainty before committing to the design below.

So this is **not** the small change the ticket hoped for in step 1.

## Step 1b — Could we filter locally instead?

Also no. The results table carries three columns:

```
COLUMNS: ['Document', 'Type', 'Description']
row count: 3752
```

No date of any kind. So MI's search surface can express "recently acted on" **neither as a filter
nor in its output**. Fetching the full result list and selecting recent bills locally is not
available.

## Step 2 — Is there a cheaper "recently acted on" surface?

**Yes: the daily journals, and they look genuinely suitable.**

The cache holds **191** journal documents already, fetched incidentally by the existing roll-call
scraper. URL shape:

```
legislature.mi.gov/documents/2025-2026/Journal/House/htm/2025-HJ-01-08-001.htm
                                        └ chamber        └ year └ MM-DD └ session-day sequence
```

### They name the bills acted on, parseably

Bills appear as `House Bill No. 4123` / `Senate Bill No. 512`. Parsed all 191:

| | |
|---|---|
| Total bill mentions | 4,907 |
| Median per session day | 21 |
| Busiest session day | 93 |

Busiest twelve days ranged 56–93 distinct bills. Michigan sits roughly two to three days a week,
so a week's journals name on the order of 40–200 bills — the right order of magnitude to cover
the **~80 bills/week** (median 88, worst case 165) OPEN-89 measured as unreturnable.

### The URLs are enumerable without an index

No index page appeared in the cache, and the trailing sequence number is a session-day counter
that cannot be derived from a date. But it **rises monotonically with date**, verified across all
four chamber-years present:

```
2025 HJ: 71 cached, seq 001..117   monotonic with date: True
2025 SJ: 50 cached, seq 008..114   monotonic with date: True
2026 HJ: 43 cached, seq 001..052   monotonic with date: True
2026 SJ: 27 cached, seq 004..058   monotonic with date: True
```

So "remember the last sequence number per chamber, walk forward until a 404" works, and costs
about one request per new session day plus one miss. (The gaps in the cached sequences are
journals we never fetched, not journals that do not exist — the existing scraper only fetches the
ones a bill page links to.)

### What this costs, against the alternative

| Approach | Requests per weekly run |
|---|---|
| Today (`dateFrom`, broken) | 1 search + N new bills |
| **Journals** | **1 search + ~2–6 journals + N changed bills** |
| Drop the date filter, walk everything | **~3,752 bill pages, ~6.3 h at the 10 rpm cap** |

Roughly a **600-fold** difference in requests against the site that WAF-blocks us. That is the
whole argument.

## Step 3 — Interaction with OPEN-132

OPEN-134 warns that widening the result set makes one-match windows rarer and so partially masks
OPEN-132's single-match-redirect bug. Worth recording that **this is no longer a concern**:
OPEN-132's fix merged on 2026-08-23, with a regression test built on the 2026-07-25 response that
originally dropped a bill. The masking risk is moot because the bug is fixed rather than hidden.

---

## Recommendation

Replace `dateFrom` as the change signal with a journal-derived set of recently-acted bills:

1. Per chamber, track the last-seen journal sequence number.
2. Each run, walk forward from it until a 404, fetching each new journal.
3. Extract `House|Senate Bill No. N` references.
4. Scrape the union of (bills the existing `dateFrom` search returns — still correct for genuinely
   *new* bills) and (bills named in journals since the last run — the ones being missed today).

Keeping the existing search rather than replacing it matters: `dateFrom` is not wrong about newly
introduced bills, it is only blind to later activity on older ones. The journals fill exactly that
hole, so the two are complementary and the change is additive.

### Open questions for whoever implements it

- **Committee reports.** The ticket also names these. Not investigated here: no committee-report
  documents appeared in the cache under a recognisable path, so there was nothing to read without
  network access. Journals alone may not cover committee action that never reaches the floor —
  worth checking before assuming full coverage.
- **Bill-number to identifier mapping.** Journals say `House Bill No. 4123`; the scraper works in
  `HB 4123` / `2025-HB-4123`. `_mi_bill_id_to_no()` already normalises this shape, so it should
  reuse that rather than inventing a second parser.
- **Sequence-number bootstrap.** First run after this ships has no last-seen number. Seeding from
  the highest number already in the cache avoids a walk from 001.
- **Resolutions.** The regex above catches `Resolution`/`Joint Resolution`/`Concurrent
  Resolution`, but the mapping from those to our identifiers (HR/SR/HJR/SJR/HCR/SCR) needs the
  same care as bills.

### What was not done, and why

OPEN-134's evidence bar requires a live MI incremental run over a window containing a
floor-action-only bill, verified against production, plus a re-measurement of the ~80/week figure.
Neither is possible in a read-only session, and a full-scrape comparison is the 7–8 hour /
~3,800-request run the ticket explicitly says to coordinate rather than fire off. This note is the
investigation the ticket asks for before the fix; the implementation and its live validation are
the remaining work.

`RUNBOOK.md:626` still carries the original unverified caveat about MI's date semantics. OPEN-89
settled the semantics and this note settles what to do about it — worth updating that line when
the fix lands, not before.
