# MI incremental date signal — `dateFrom=` semantics, OPEN-89, 2026-08-22

`RUNBOOK.md:626` has carried "**Unverified**: may filter by intro date, not last-action date"
for MI's incremental signal since 2026-06-22, and `PLAN-incremental-scraping.md:157` has carried
the matching "semantics still unverified" note. The ticket's prescribed method is a forced full MI
scrape diffed against a normal incremental run. **That run was not authorised and was not
performed** — MI is the fleet's most WAF-sensitive jurisdiction (OPEN-52/53/54), and a full scrape
is exactly the traffic that resilience work exists to make safe.

**Requests made to `legislature.mi.gov` while producing this note: zero.** Deliberately. Every
finding below comes from the production checkout's on-disk scrapelib cache
(`openstates-scrapers/_cache/`), the production `openstates` database, and `logs/scraper.log`
archives — all read-only, all already-paid-for traffic.

## Bottom line

**The signal is introduction date, not last-action date.** The caveat's bad case is the real one.
This was settled offline, without the scrape, because the cache already contains the diff the
ticket asked for: one full-scrape search response and six real incremental search responses.

Consequence, measured against production data: an MI incremental window silently skips roughly
**80 bills per week** (median 88, worst observed week 165) whose only change since the cutoff is a
later action. Over 22 weekly windows, **59.7%** of all bill-weeks with real activity would be
missed.

A **second, separate defect** turned up on the way (see below): when an MI search matches exactly
one bill, the site serves that bill's page instead of a results page, the scraper's xpath matches
nothing, and the run reports a clean no-op. This has already happened once in production
(2026-07-25).

The full-scrape experiment is therefore no longer needed to *answer* the question. It is still the
right confirmation step before shipping a fix, and §"Verification plan" below makes it concrete and
safe. It has not been run.

## Where the parameter came from

Worth stating plainly, because it explains why nobody ever knew the semantics: **DDP never chose
this parameter.** Upstream's `13d29d20f` ("MI: New website", 2024-03-29) hardcoded the full search
URL with an empty `&dateFrom=&dateTo=` already in it. DDP's `8db6514f5` (2026-06-22) simply filled
the existing blank in:

```python
date_from = ""
if start:
    try:
        dt = dateutil.parser.parse(start)
        date_from = dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
search_url = f"https://legislature.mi.gov/Search/ExecuteSearch?...&dateFrom={date_from}&dateTo=&contentFullText="
```

That is still the shape today at `scrapers/mi/bills.py:227-234`. Nothing downstream reads or
reveals the semantics: `scrape()` consumes only `td[1]/a` from the results table (`:261-268`), so
the scraper never sees a date at all. The results table's columns are `Document | Type |
Description` — no date column — which is why no amount of reading the scraper could settle this.
Two recent MI changes were checked and neither touches it: OPEN-81's `bill_no=` filter sits
downstream at `:266`, and OPEN-52/53/54's `mi_waf_get`/`_waf_circuit_breaker.py` work is
transport-layer only.

## Evidence — why "introduction date" is settled

`_cache/` retains every distinct search URL MI's scraper has fetched, keyed by query string. That
includes the full-scrape response (`dateFrom=` blank, 3,752 results) and six real incremental
responses. Parsed with the scraper's own xpath:

| cached `dateFrom=` | fetched | results | of those, intro date ≥ cutoff | intro date < cutoff |
|---|---|---|---|---|
| *(blank — full)* | 2026-06-27 | 3752 | — | — |
| 2026-06-28 | 2026-07-11 | 96 | **96** | 0 |
| 2026-07-12 | 2026-07-18 | 37 | **37** | 0 |
| 2026-07-19 | 2026-07-25 | 0 † | — | — |
| 2026-07-26 | 2026-08-08 | 27 | **27** | 0 |
| 2026-08-09 | 2026-08-15 | 14 | **14** | 0 |
| 2026-08-16 | 2026-08-22 | 0 | — | — |

† not a genuinely empty result — see "Second defect" below.

**174 of 174 returned bills were introduced on or after the cutoff. Zero exceptions.** Intro date
is taken from each bill's own `INTRODUCED%` history row on its cached bill page, not from the
minimum action date — MI's history tables are not strictly chronological (see SR 135 below), and
using `min(date)` produces one spurious exception.

That alone is suggestive rather than conclusive: a last-action filter would also return only
recently-introduced bills *if* no older bill happened to see activity. So the complementary check
matters more.

**Eight weeks of incremental runs never revisited a single pre-existing bill.** Across all four
non-empty incremental runs, 172 bill pages were fetched. The earliest introduction date among all
172 is **2026-06-30** — two days after the first cutoff. Not one bill introduced before its
window's cutoff was ever returned:

```
fetched 2026-07-11: n=94  earliest intro 2026-06-30   (cutoff 2026-06-28)
fetched 2026-07-18: n=37  earliest intro 2026-07-15   (cutoff 2026-07-12)
fetched 2026-08-08: n=27  earliest intro 2026-07-29   (cutoff 2026-07-26)
fetched 2026-08-15: n=14  earliest intro 2026-08-11   (cutoff 2026-08-09)
```

Under last-action semantics this is essentially impossible. 38% of MI's 2025-2026 bills have action
streams spanning more than 7 days, and the per-week figures below show 80-165 older bills picked up
new actions in a typical week. Under a last-action filter those bills would dominate each result
set; observed count over eight weeks is **zero**.

**The 29 apparent counter-examples in the database all decompose.** Production shows 201 MI bills
whose latest action postdates the 2026-06-28 full scrape, of which 29 were introduced before it.
Both groups are explained, and neither is an incremental pickup:

- **13 bills (HB 6130-6142)** — introduced 2026-06-25, "last action" 2026-06-30. That row is
  `bill electronically reproduced 06/25/2026`, an administrative entry MI *forward-dates*. It was
  already present on the page fetched 2026-06-28. Nothing re-fetched these.
- **16 bills** (HB 4023, HB 4100, HB 4101, HB 4187, HB 4208, HB 4724, HB 4750, HB 5233, HB 5249,
  HB 5697, SB 105, SB 133, SB 205, SB 418, SB 716, SB 966) — last action 2026-07-29. These are
  exactly the 16 bills of the OPEN-30/OPEN-81 manual vote backfill
  (`notes/mi-open-30-open-81-vote-backfill-20260815.md`), recovered via targeted `bill_no=`, not
  via the incremental search. HB 4023's cached full-scrape page still ends at 2025-06-10 while the
  database now holds 27 actions through 2026-07-29 — the later actions came from the backfill.

201 − 29 = 172, matching the incremental fetch count exactly. The accounting closes with nothing
left over.

**SR 135 corroborates directly.** The `dateFrom=2026-07-19` search returned Senate Resolution 135
of 2026, whose only actions are `RULES SUSPENDED` and `ADOPTED`, both dated **2026-07-03** —
sixteen days *before* the cutoff. Its `INTRODUCED BY SENATOR JOHN CHERRY` row is dated 2026-07-29.
The only field on that bill at or after the cutoff is the introduction date, so that is what the
filter matched. (Both dates are odd — an introduction later than the adoption, and later than the
2026-07-25 fetch — but that is MI's own data quality, not a parse artefact.)

### Cross-check against production

Independently reproduced against the live `openstates` database (`ddp-openstates-postgres-1`, not
dev), which agrees with the cache to within one bill:

```
mi_bills | span_gt_7d | span_gt_30d | median_span_days
    3924 |       1481 |        1158 |                5
```
(cache-derived: 3924 / 1480 / 1157 / 5)

## Risk if the answer is bad — it is bad

Per weekly window, over the region where full history is complete (2026-01-03 → 2026-06-27, before
the last full scrape, so no post-scrape blind spot skews it):

| window start | bills with activity | would be missed | % |
|---|---|---|---|
| 2026-01-10 | 62 | 46 | 74.2 |
| 2026-01-17 | 79 | 58 | 73.4 |
| 2026-01-24 | 70 | 38 | 54.3 |
| 2026-01-31 | 81 | 48 | 59.3 |
| 2026-02-07 | 60 | 50 | 83.3 |
| 2026-02-14 | 103 | 46 | 44.7 |
| 2026-02-21 | 181 | 72 | 39.8 |
| 2026-02-28 | 183 | 124 | 67.8 |
| 2026-03-07 | 166 | 117 | 70.5 |
| 2026-03-14 | 215 | 98 | 45.6 |
| 2026-03-21 | 57 | 44 | 77.2 |
| 2026-04-11 | 170 | 90 | 52.9 |
| 2026-04-18 | 210 | 88 | 41.9 |
| 2026-04-25 | 183 | 117 | 63.9 |
| 2026-05-02 | 16 | 6 | 37.5 |
| 2026-05-09 | 176 | 87 | 49.4 |
| 2026-05-16 | 173 | 93 | 53.8 |
| 2026-05-23 | 6 | 6 | 100.0 |
| 2026-05-30 | 167 | 112 | 67.1 |
| 2026-06-06 | 168 | 124 | 73.8 |
| 2026-06-13 | 192 | 129 | 67.2 |
| 2026-06-20 | 225 | 165 | 73.3 |

**22 windows · 2,943 bill-weeks with real activity · 1,758 would be missed · 59.7% · mean 80/week ·
worst 165.**

"Missed" here means the bill had at least one action inside the window and was introduced before it,
so an intro-date filter cannot return it. What is lost is the action itself — amendments, committee
reports, floor votes, gubernatorial signature — on bills DDP already tracks. Votes are the sharpest
edge: OPEN-30's 16-bill vote gap needed a hand-built `bill_no=` mechanism to recover precisely
because no weekly incremental run would ever have revisited those bills. That was treated as a
one-off backfill; on this evidence it is the normal steady state.

MI has run incremental-only since 2026-06-28. Every action recorded on a pre-2026-06-28 bill since
then is missing from production unless a targeted backfill happened to catch it.

## Second defect found (not in scope, should be its own ticket)

The `dateFrom=2026-07-19` search did not return an empty result set. It returned **SR 135's bill
page** — `<title>Senate Resolution 135 of 2026 - Michigan Legislature</title>`, no
`tableScrollWrapper` element at all. MI redirects a single-match search straight to the bill. The
scraper's xpath (`//div[contains(@class,'tableScrollWrapper')]/table[1]/tbody/tr/td[1]/a`) matches
zero elements, the loop body never executes, and the run reports success:

```
[2026-07-25 22:00:00] Starting scrape: mi  (incremental cutoff=2026-07-19T01:01:01)
[2026-07-25 22:00:03] === SCRAPE SUMMARY: mi  | mode=incremental | bills_scraped=0 | no changes since cutoff (no-op) ===
```

Three seconds, clean exit, one bill silently dropped. Corroborated independently: no bill page in
`_cache/` has an mtime of 2026-07-25. SR 135 was recovered a week later only because its
introduction date (2026-07-29) also cleared the *following* cutoff — luck, not design. Compare the
2026-08-16 run, which is a genuine empty result (a real results page, header row only). Any
incremental window matching exactly one bill loses it. Same "quietly wrong, not loudly broken"
class; distinct root cause; deserves a separate ticket.

## Verification plan (ready to execute — NOT run)

The remaining value of the full-scrape diff is confirmation before a fix ships, not discovery. Note
one constraint the ticket's own suggested method does not survive: a bare `dateFrom=` probe is not
available. Every MI request routes through `mi_waf_get`'s cookie/UA identity handling
(`bills.py:236-241`), and a request without those warmed cookies gets a WAF block, not an answer.
The experiment must run through the real scraper.

**Preconditions**

1. OPEN-52/53/54 resilience work landed and exercised on MI. `logs/scraper.log` shows twelve
   `Starting scrape: mi` lines between 2026-07-31 and 2026-08-04 with no matching
   `SCRAPE SUMMARY` — a mix of scheduled and manual attempts, none of which completed. Confirm
   that period's instability is resolved before adding a multi-hour full scrape on top of it.
2. `MI_COOKIE_PROVIDER` warm-up confirmed healthy — one cheap already-scheduled incremental run
   completing normally is sufficient evidence.
3. No concurrent MI scrape or archive step. Check `ps aux` and the import lock.
4. Run from the **dev** checkout (`ddp-open-states-dev`, `activate-dev.sh`) so nothing writes the
   production database, and assert `SELECT current_database()` before and after (per OPEN-41's
   Approach B). The comparison is over scraped counts, not imported rows.

**Window** — MI's own scheduled slot, 22:00 local, immediately *after* a normal weekly incremental
completes, so the day's MI traffic is one contiguous block rather than two. Prefer a recess week:
the 2026-05-02 and 2026-05-23 windows above show near-zero legislative activity, which also makes
the diff cleaner.

**Steps**

1. Capture the incremental baseline from the normal scheduled run: its `SCRAPE SUMMARY`
   `bills_scraped=N`, its cutoff, and its cached search response in `_cache/`.
2. Force the full scrape by moving the cutoff marker aside — `run-scrape.sh` treats a missing
   `.ts` as first-run and drops `start=` entirely (`run-scrape.sh:31-45`):
   ```
   mv logs/last-run/mi.ts logs/last-run/mi.ts.open89-bak
   ./run-scrape.sh mi
   mv logs/last-run/mi.ts.open89-bak logs/last-run/mi.ts   # restore immediately after
   ```
   Restoring matters — leaving it absent makes the *next* scheduled run full as well. That exact
   mistake is on record for FL (`notes/fl-open-41-waf-vote-gap-verification-20260808.md`).
3. Diff the two cached search responses on bill identifier, not count:
   `full_set − incremental_set`, then partition by introduction date relative to the cutoff.

**Decision rule**

- Bills in `full − incremental` with intro < cutoff **and** an action ≥ cutoff →
  **introduction-date filter confirmed.** Expect ~80 for a 7-day window on these figures.
- That set empty (every bill with an action ≥ cutoff also appeared in the incremental set) →
  **last-action-date filter**, caveat closes, `RUNBOOK.md:626` updated to "verified".
- Anything else — e.g. the full set missing bills the incremental found — means the search endpoint
  is not stable across calls, and the diff is inconclusive rather than negative.

**Cost** — the 2026-06-27 full run took **3h02m** for 3,752 bills (22:00:00 → 01:02:06). That
predates OPEN-21's `MI_SCRAPELIB_RPM=10` cap (`089191b04`, 2026-08-02), which is live now with no
env override, so pacing alone is ~6.3h for 3,752 bills; with `http_resilience_mode`'s 1-3s jitter,
budget **7-8h** and roughly 3,800 requests. That is the real price of this ticket, and the reason
the cache evidence above is worth more than the run.

## What remains unknown

- **Which field MI matches, exactly.** The evidence establishes the *behaviour* (bills are selected
  by introduction date) but not the underlying column. It may be an introduction date, a document
  date, or an initial-filing date; SR 135's introduced-2026-07-29/adopted-2026-07-03 record shows
  the field is not always sane. Functionally equivalent for DDP's purposes; it would matter to
  anyone writing a fix that tries to keep using `dateFrom=`.
- **Whether `dateTo=` behaves symmetrically.** Never populated, never tested.
- **The precise production shortfall since 2026-06-28.** The 59.7% figure is derived from windows
  before the last full scrape, where history is complete. The actual count of actions missing from
  production *today* cannot be measured without fetching the bills whose actions were missed — that
  is the full scrape, and it is unrun. The 80/week mean is the honest estimate, not a count.
- **Whether a fix should keep `dateFrom=` at all.** `PLAN-incremental-scraping.md:1080` already
  names the fallback (filter per-bill on the History table), which trades the server-side win for
  ~3,800 per-bill fetches. Choosing between them is a separate scoping decision, deliberately not
  made here.

## References

- `openstates-scrapers/scrapers/mi/bills.py:227-234` (`dateFrom=` construction), `:236-241`
  (`mi_waf_get`, why a bare probe is unavailable), `:261-268` (results parsing — no date column read)
- `8db6514f5` — DDP filled in the blank; `13d29d20f` — upstream introduced the empty parameter
- `RUNBOOK.md:626` — the caveat, unchanged since 2026-06-22
- `ddp-infra/PLAN-incremental-scraping.md:157` (status), `:193`, `:1075-1080` (the plan's own
  "must verify" note and per-bill fallback)
- `notes/mi-open-30-open-81-vote-backfill-20260815.md` — the 16-bill backfill this note reuses as
  evidence
- `notes/fl-open-41-waf-vote-gap-verification-20260808.md` — the dev/prod database assertion
  pattern, and the cutoff-restore failure mode
- OPEN-52/53/54 — WAF resilience work this ticket's full scrape must be sequenced behind
- Evidence sources, all read-only: `openstates-scrapers/_cache/` (7 `ExecuteSearch` responses,
  3,924 bill pages), `ddp-openstates-postgres-1` / `openstates`, `logs/scraper.log*`
