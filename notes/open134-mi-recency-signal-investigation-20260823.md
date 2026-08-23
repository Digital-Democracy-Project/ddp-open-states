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

**No such parameter is exposed anywhere in the cached evidence.** (Deliberately worded that way —
see the caveat at the end of this section. Cache evidence cannot prove a negative about the
server.)

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
cost argument, and it holds. The coverage argument does not — see next.

### Step 2b — but how much of the gap do journals actually recover? **About 57%, and the
### remainder is structural**

The volume figures above are suggestive, not evidence that the bills journals name are the bills
we are missing. So this was measured directly, against the production database (read-only) and
the cache.

Method: take MI bills whose last action is later than their first — the class `dateFrom` cannot
return — and check whether the bill is named in a journal for its own last-action date. **2,842**
MI bills match that class from 2025 onward; a 400-bill sample was tested, of which **253** have a
cached journal for their exact last-action date.

```
named in that day's journal: 146/253 = 57%
```

**Recall is 57%, not near-complete.** And the misses are not random — pulling the actual actions
behind them shows exactly one pattern:

| Bill | Last action | Classification |
|---|---|---|
| HB 4864 | reported with recommendation with substitute (H-1) | `committee-passage` |
| HB 4894 | reported with recommendation for referral to Committee on Rules | `committee-passage` |
| HB 5518 | reported with recommendation for referral to Committee on Rules | `committee-passage` |
| HB 6127 | bill electronically reproduced 06/24/2026 | *(none — administrative)* |

**Journals carry floor business. Committee reports and administrative rows are simply not in
them.** Verified this is not a chamber artifact: both the House and Senate journals for
2026-06-25 are cached, and these bills appear in neither.

And non-floor activity is the *majority* of MI bill activity. All MI actions dated 2026-06-25:

| Classification | Count |
|---|---|
| *(none — administrative)* | 143 |
| `referral-committee` | 42 |
| `passage` | 37 |
| `introduction` | 29 |
| `committee-passage` | 25 |
| `reading-3` | 23 |
| `reading-1` | 21 |
| `reading-2` | 13 |

Roughly 210 non-floor rows against 94 floor ones on a single day. So journals are a **partial**
recovery mechanism, and the committee surface the ticket listed as a maybe is in fact the larger
half of the problem.

## Step 3 — Interaction with OPEN-132

OPEN-134 warns that widening the result set makes one-match windows rarer and so partially masks
OPEN-132's single-match-redirect bug. Worth recording that **this is no longer a concern**:
OPEN-132's fix merged on 2026-08-23, with a regression test built on the 2026-07-25 response that
originally dropped a bill. The masking risk is moot because the bug is fixed rather than hidden.

---

## Recommendation

**Journals are a real signal and worth building, but they are not the whole fix.** Stated in that
order because the volume numbers alone read more encouragingly than the recall measurement
justifies.

Keep `dateFrom` — it is not *wrong* about newly introduced bills, only blind to later activity on
older ones — and add journals alongside it:

1. Per chamber, track the last-seen journal sequence number.
2. Each run, walk forward from it until a 404, fetching each new journal.
3. Extract `House|Senate Bill No. N` references.
4. Scrape the union of the `dateFrom` results and the journal-named bills.

Expected recovery on the measurement above: **roughly 57% of the missed class**, i.e. the
floor-action half. That is a large improvement on today's zero and it is cheap, so it is worth
doing on its own — but it must not be described as closing OPEN-134.

### The committee surface is now the critical unknown, not a footnote

The ticket listed committee reports as a maybe. The recall measurement promotes them to the
larger half of the problem: `committee-passage` and unclassified administrative rows outnumber
floor actions roughly two to one on a sitting day, and journals contain none of them.

Nothing could be established about them here — no committee-report document appeared in the cache
under any recognisable path, so there was nothing to read without network access. **That is the
next investigation, and it should happen before anyone commits to an architecture**, because if
committee reports turn out to be unavailable or unparseable then the honest options narrow back
toward a periodic full walk, and the design changes shape entirely.

### Other open questions for whoever implements the journal half

- **Checkpoint semantics.** Advancing the last-seen sequence number before the journal-derived
  bills have actually been scraped would make a failed run skip those bills permanently. Only
  advance after successful processing, or keep the pending set durable.
- **A premature 404 must not be treated as authoritative.** If a gap in the server's own numbering
  ever exists, stopping at the first miss silently truncates every future run. Probe a small
  number past the first 404 before concluding, and log where it stopped.
- **Bill-number to identifier mapping.** Journals say `House Bill No. 4123`; the scraper works in
  `HB 4123` / `2025-HB-4123`. `_mi_bill_id_to_no()` already normalises this shape — reuse it
  rather than writing a second parser.
- **Sequence-number bootstrap.** The first run has no last-seen number, and the cache is not a
  complete record (it only holds journals a bill page happened to link to). Seeding from the
  highest cached number avoids a walk from 001 but may skip journals never fetched.
- **Resolutions.** The regex catches `Resolution`/`Joint Resolution`/`Concurrent Resolution`, but
  mapping those to HR/SR/HJR/SJR/HCR/SCR needs the same care as bills.
- **WAF guardrails.** Whatever ships needs a hard request cap, adherence to the 10 rpm limit, no
  retry escalation on a WAF-shaped failure (OPEN-53), a config kill switch, and a dry-run mode
  that logs what it *would* fetch. MI is the one jurisdiction where an implementation bug costs
  more than the bug it fixes.
- **Measure the residual.** Re-run OPEN-89's own method after shipping and report recovered
  count, residual misses, and which categories remain — the 57% figure above is the baseline to
  beat, and the number that says whether the committee work is still needed.

### This note does not close OPEN-134

Said plainly because the ticket is a fix ticket, and pm-review's first observation on this note
was that merging it must not be mistaken for completing the work. The bug is live: MI is still
losing bills every week. What this note establishes is *what to build and what not to bother
trying*, plus a measured ceiling on how much the buildable half recovers.

OPEN-134 should stay open until code lands and the ~80/week figure is re-measured.

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
