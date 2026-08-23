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

**`dateFrom=` behaves as an introduction-date-like filter. It is definitively not a last-action
filter.** The caveat's bad case is the real one. This was established offline, without the scrape,
because the cache already contains the diff the ticket asked for: one full-scrape search response
and six real incremental search responses.

The negative half of that claim — not last-action — is as close to nailed down as observational
evidence gets (see below). The positive half is a behavioural description, not a field name: bills
are selected on something that tracks introduction, and DDP cannot see which column from outside.
For every purpose DDP has, the two are equivalent; the distinction only matters to someone writing
a fix that tries to keep using the parameter.

Consequence, estimated against production data: an MI incremental window cannot return roughly
**80 bills per week** (median 88, worst observed week 165) whose only change since the cutoff is a
later action — **59.7%** of all bill-weeks with activity over 22 windows. Excluding MI's
administrative `electronically reproduced` rows, which are arguably not user-visible changes, it is
**67/week and 55.6%**. The conclusion is not sensitive to that choice; both are estimates of
opportunity, not counts of confirmed-missing rows.

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

## Evidence

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

**Row count reconciliation.** The table's non-empty windows sum to 174 result rows, while 172
distinct bill pages were fetched. The gap is overlap, not loss: `2026-SCR-0015` appears in both the
2026-06-28 and 2026-07-12 windows, and `2026-SR-0135` in both 2026-06-28 and 2026-07-26. 174 rows =
172 distinct bills. Checked directly — of the 96 bills in the 2026-06-28 window, zero have a cached
page older than that cutoff, so no row was ever served from a stale cache entry instead of being
fetched. Every count below is over distinct bills.

**Eight weeks of incremental runs never revisited a single pre-existing bill.** Across all four
non-empty incremental runs, 172 distinct bill pages were fetched. The earliest introduction date
among all 172 is **2026-06-30** — two days after the first cutoff. Not one bill introduced before
its window's cutoff was ever returned:

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

**22 windows · 2,943 bill-weeks with activity · 1,758 unreturnable · 59.7% · mean 80/week ·
worst 165.**

MI's `bill electronically reproduced` rows (2,270 of 25,629 MI action rows) are administrative and
arguably not user-visible changes. Excluding them: **2,667 bill-weeks · 1,482 unreturnable · 55.6% ·
mean 67/week · worst 151.** The estimate is not sensitive to that judgement call, so the headline
figure keeps them in and this is the conservative floor.

"Missed" here means the bill had at least one action inside the window and was introduced before it,
so an intro-date filter cannot return it. It is a count of *opportunities to miss* derived from
complete history, not a verified count of rows currently absent from production. What is lost is the action itself — amendments, committee
reports, floor votes, gubernatorial signature — on bills DDP already tracks. Votes are the sharpest
edge: OPEN-30's 16-bill vote gap needed a hand-built `bill_no=` mechanism to recover precisely
because no weekly incremental run would ever have revisited those bills. That was treated as a
one-off backfill; on this evidence it is the normal steady state.

**Boundary and inclusion rules**, so the table is reproducible: a window is `[start, start+7)` on
action `date::date`, local dates throughout, no timestamps. "Activity" = at least one action row
dated inside the window. "Missed" = that, and an `INTRODUCED%` row dated strictly before
`start`. Bills with no `INTRODUCED%` row at all (1 of 3,924) are excluded. Three windows in the
series are absent from the table (2026-01-03, 03-28, 04-04) because they contain no action rows at
all — legislative recess, not filtered data.

MI has run incremental-only since 2026-06-28. It follows that actions recorded on pre-2026-06-28
bills since then are very likely absent from production unless a targeted backfill caught them —
but that is an inference from the mechanism, not a measurement. Confirming it means fetching the
bills whose actions were missed, which is the unrun full scrape.

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

**Preconditions (all four are go/no-go, not advisory)**

1. OPEN-52/53/54 resilience work landed and exercised on MI. `logs/scraper.log` shows twelve
   `Starting scrape: mi` lines between 2026-07-31 and 2026-08-04 with no matching
   `SCRAPE SUMMARY` — a mix of scheduled and manual attempts, none of which completed. Confirm
   that period's instability is resolved before adding a multi-hour full scrape on top of it.
2. The two most recent scheduled MI incrementals each produced a `SCRAPE SUMMARY` line, and
   `grep -c "WafBlockDetected\|WAF block" ` over their log windows returns 0. One clean run is
   weak evidence; two consecutive is the bar.
3. No concurrent MI scrape, archive step, or import. Check `ps aux | grep -i "os-update\|run-scrape"`
   and that `logs/last-run/` has no live import lock.
4. Run from the **dev** checkout (`ddp-open-states-dev`, `activate-dev.sh`). Assert
   `SELECT current_database()` in the same shell immediately before and after (OPEN-41 Approach B) —
   it must read `openstates_dev`, never `openstates`.

**Window** — MI's own scheduled slot, 22:00 local, immediately *after* a normal weekly incremental
completes, so the day's MI traffic is one contiguous block rather than two. Prefer a recess week:
the 2026-05-02 and 2026-05-23 windows above show near-zero legislative activity, which also makes
the diff cleaner.

**Cache handling — read this before running anything.** The whole offline finding above rests on
`_cache/` retaining responses, which cuts both ways: the blank-`dateFrom=` full search URL is
*already cached* from 2026-06-27, and so are 3,924 bill pages. A full scrape against a warm cache
would compare a fresh incremental against a fourteen-month-stale full response and prove nothing.
So:

- Use the **dev checkout's own `_cache/`**, not production's. Confirm which directory is live before
  starting (`os-update` resolves it relative to the invoking checkout).
- Delete or move aside just the two MI search entries — the blank-`dateFrom=` one and the target
  cutoff's — so both sides of the diff are fetched during the experiment. Leave the 3,924 bill-page
  entries in place: the diff is over *search result sets*, the bill pages are not part of it, and
  re-fetching them is the entire 7-8h cost.
- Prove freshness afterwards: both search entries' mtimes must fall inside the run window.

**Steps**

1. Capture the incremental baseline. It must come from the **same checkout and code revision** as
   the full run — do not diff a production scheduled run against a dev full run. Either re-run the
   incremental in dev with the production cutoff passed explicitly (`start=<cutoff>`), which costs
   only the one search request plus its handful of bills, or run both legs in dev back to back.
   Record: the cutoff used, `bills_scraped=N`, and the path + mtime of the cached search response.
2. Force the full scrape by moving the cutoff marker aside. `run-scrape.sh` treats a missing `.ts`
   as first-run and drops `start=` entirely (`run-scrape.sh:31-45`). Use a trap so an interrupted
   shell cannot leave the marker absent — the FL precedent
   (`notes/fl-open-41-waf-vote-gap-verification-20260808.md`) is exactly this failure, where a
   cleared cutoff silently turned a later scheduled run into a full scrape:
   ```
   TS=logs/last-run/mi.ts
   cp -p "$TS" "$TS.open89-bak"
   trap 'mv -f "$TS.open89-bak" "$TS"; ls -la "$TS"' EXIT INT TERM
   mv "$TS" "$TS.open89-hidden"
   ./run-scrape.sh mi
   ```
   Then confirm by hand that `mi.ts` is back and its contents match the pre-run value.
3. Validate response shape on **both** cached search responses before diffing anything. The
   single-match redirect above is precisely the trap here — an xpath that matches nothing looks
   identical to an empty result set. For each response assert: `<title>` contains
   `Search Results`, exactly one `tableScrollWrapper` div exists, and its header row reads
   `Document | Type | Description`. If either response fails, the run is inconclusive — do not
   proceed to the diff, and treat a redirect as a hit on the second defect instead.
4. Diff on normalised bill identifier, not count. Extract `objectName=` from each result row's href
   (the same field `make_bill_url()` uses) rather than link text, which carries zero-padding
   variance — `_mi_bill_id_to_no()` exists for exactly that reason. Compute
   `full_set − incremental_set`, then for each bill in that difference read its intro date from its
   `INTRODUCED%` history row (not `min(date)` — MI's tables are not chronological) and its action
   dates, and partition on `intro < cutoff AND max(action) >= cutoff`.

**Decision rule**

- Difference set contains bills with `intro < cutoff` **and** an action `>= cutoff` →
  **introduction-date behaviour confirmed.** Expect ~80 for a 7-day window on these figures; an
  order of magnitude fewer would contradict the estimate and is itself worth investigating.
- Difference set contains no such bill, i.e. every bill with an action `>= cutoff` also appeared in
  the incremental set → **last-action behaviour**, this note is wrong, the caveat closes and
  `RUNBOOK.md:626` becomes "verified".
- Either response failed step 3's shape check, or the full set is *missing* bills the incremental
  found → **inconclusive**, not negative. The endpoint is not stable across calls and the diff
  cannot be interpreted either way.

**Abort criteria during the run** — stop and restore the cutoff immediately on any of: the WAF
circuit breaker firing (`MIWafCircuitBreakerMixin` aborts the scrape by design, so this shows up as
a failed run); more than a handful of `WafBlockDetected` re-warms in the log; or the run exceeding
12h wall clock. A partial full scrape is not a usable diff input — the difference set would be
indistinguishable from a real filtering gap. Record the abort and retry no sooner than the next
week's slot.

**Cost** — the 2026-06-27 full run took **3h02m** for 3,752 bills (22:00:00 → 01:02:06). That
predates OPEN-21's `MI_SCRAPELIB_RPM=10` cap (`089191b04`, 2026-08-02), which is live now with no
env override, so pacing alone is ~6.3h for 3,752 bills; with `http_resilience_mode`'s 1-3s jitter,
budget **7-8h** and roughly 3,800 requests — and that assumes mostly clean responses. Every
`WafBlockDetected` adds a Playwright cookie re-warm plus a retry, so on a bad night this can run
considerably longer, which is what the 12h abort exists for. That is the real price of this ticket,
and the reason the cache evidence above is worth more than the run.

**After the run** — confirm production was untouched: `mi.ts` restored to its original contents,
production `_cache/` mtimes unchanged, and the production `openstates` database's MI bill/action
counts identical to a baseline taken before starting.

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
