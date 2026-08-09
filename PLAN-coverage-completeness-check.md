# PLAN: Coverage & Completeness Checks Against Public OpenStates

**Status:** IMPLEMENTED (Tier 1 + Tier 2) 2026-07-28 — `quality_check.py --coverage
JURISDICTION SESSION`, per §8's implementation order. First real run against MA found a large,
genuine coverage gap — see §10. **Audited again 2026-08-02: §10's proposed fix was built, but
in a script that's no longer the production driver. See §11 — and then §12: §11's own framing
("the underlying bug is still live") doesn't hold up either. Filed and closed as
[OPEN-24](https://digitaldemocracyproject.atlassian.net/browse/OPEN-24), not a real defect —
`session=None` is deliberate, load-bearing behavior for jurisdictions with more than one active
session, not a bug. See §12 before acting on §11's "what needs to happen" list.** **Re-checked
against all relevant repos 2026-08-03: no code progress on any of §12's four open items, but a
new, previously undocumented MA scrape-reliability bug surfaced from prod's own logs — see §13.**
**Later the same day: Tier 1 finally run against every tracked jurisdiction for the first time —
8 of 9 real jurisdiction/session pairs came back clean, and a real, previously-undetected bug
was found (and fixed) in the tool itself: Tier 1 had never actually been able to check US federal
coverage at all. `--tier2-random` also added for representative Tier 2 sampling. See §14.**

**Goal:** Make sure the DDP fork's scrapers never *silently* miss data that exists in the
public `v3.openstates.org` API — not "does our data match public data" (we fork precisely
because public data has quality problems we're fixing, so exact parity is neither expected
nor desired), but "is there anything upstream has that we don't." This is a **recall** problem
(catch false negatives — things we're missing), not a **precision** problem (things that
differ on purpose). Two concrete past incidents motivate this: the WA F5 WAF cookie bug and
the MA broken vote-scraping chain both left bills looking complete while silently missing
their vote data — exactly the failure mode a correctness-only check would have missed too,
since the bill "existed" and had *plausible* content, just incomplete.

---

## 1. What Already Exists — Don't Rebuild This

Two pieces of relevant infrastructure already sit in this repo, unused or underused. Both
matter for scoping the new work correctly.

### 1a. `quality_check.py` (repo root) — partial solution, real blind spot

This has been in the repo since the initial commit. It does real, useful work:

- Samples N random bills **from the local DB** per jurisdiction (`opencivicdata_bill` joined
  through `opencivicdata_legislativesession`/`opencivicdata_jurisdiction`)
- Fetches that same bill (by jurisdiction + session + identifier) from **both** local `api-v3`
  (`localhost:8002`, container `ddp-openstates-api-1` — confirmed up/healthy) and the **live**
  `v3.openstates.org` API (needs `OPENSTATES_API_KEY`)
- Diffs title, latest-action text, vote-event count, first vote's tallies, and sponsorship count
- **Already encodes the exact intentional-divergence handling this project needs** —
  `compare_bills()` treats `local > live` vote counts as a `WARN` ("our fix, not yet merged
  upstream") and `live > local` as a `FAIL` ("we're missing votes — the real problem"). This is
  precisely recommendation #3 from the earlier discussion, already built and battle-shaped —
  reuse this pattern rather than re-inventing it.

**The blind spot: it samples *from the local DB first*.** It can only compare bills we already
know about — it never asks the live API "what bills exist for FL 2023 that I haven't seen at
all." A bill that was never scraped is invisible to this tool by construction. This is exactly
the gap this plan needs to close (§2).

It's also never been run on a schedule — no reference to it in `run-scrape.sh`,
`apply-local-patches.sh`, or the `ddp-sync` scheduler. It's a manual, ad-hoc tool today.

### 1b. `scraper-audit/` (repo root) — structural validity, not coverage

A clone of `openstates/scraper-audit` (upstream's own tool, last synced 2025-05-29). It merges
raw scraped JSON (`_data/<state>/bill*.json` — the same layout `run-scrape.sh` already produces
via `$SCRAPED_DATA_DIR`) into DuckDB and runs SQLMesh audits (`audits/bill.sql`,
`audits/event.sql`) checking internal shape — nulls, malformed dates, schema violations. It has
**never been run here** — no `_data/`, `merged_entities.json`, or `.duckdb` artifacts exist
inside it, and nothing schedules it. This checks a different thing entirely (is this bill
well-formed) from both `quality_check.py` (is this bill's content plausible vs. a second
source) and the new coverage check below (does this bill exist at all vs. a second source).
All three are complementary, not redundant.

---

## 2. The Real Gap — True Coverage Enumeration (Tier 1)

**This is the headline deliverable.** For a given jurisdiction + session, get the full set of
bill identifiers from the **public API's list endpoint** (not a single-bill lookup) and diff
against the full set of local identifiers.

```python
# New: get every bill identifier the public API has for a session (paginated, no identifier filter)
def fetch_all_public_identifiers(jurisdiction, session, api_key):
    identifiers = set()
    page = 1
    while True:
        r = requests.get(f"{LIVE_API}/bills", params={
            "jurisdiction": jurisdiction, "session": session,
            "page": page, "per_page": 50, "apikey": api_key,
        }, timeout=15)
        r.raise_for_status()
        data = r.json()
        identifiers.update(b["identifier"] for b in data["results"])
        if page >= data["pagination"]["max_page"]:
            break
        page += 1
    return identifiers

# Local side: one cheap query, no pagination needed
def fetch_all_local_identifiers(conn, jurisdiction_ocd_id, session):
    cur = conn.cursor()
    cur.execute("""
        SELECT b.identifier FROM opencivicdata_bill b
        JOIN opencivicdata_legislativesession ls ON b.legislative_session_id = ls.id
        WHERE ls.jurisdiction_id = %s AND ls.identifier = %s
    """, (jurisdiction_ocd_id, session))
    return {row[0] for row in cur.fetchall()}
```

```
missing = public_ids - local_ids   # THE headline number — bills we don't have at all
extra   = local_ids - public_ids   # informational only — see §4, not automatically a failure
```

**Cost:** a ~1,900-bill session paginates in ~40 requests at 50/page — trivial against the
licensed 30,000/day tier (see §6). Confirmed against the local schema directly
(`opencivicdata_bill.identifier` → `legislative_session_id` FK → `opencivicdata_legislativesession`
→ `jurisdiction_id`), tested live against the current DB (e.g. FL 2024 session currently holds
1,902 local bills, matching the backfill's own `DONE (count=1902:full)` marker).

**Note:** the public API's exact pagination response shape (`pagination.max_page` above) is
inferred from `v3.openstates.org`'s documented conventions, not verified against a live
response in this analysis — confirm the actual field names during implementation (§9).

**Reuse `quality_check.py`'s `OCD_TO_CODE` mapping, don't add a fourth OCD-jurisdiction map.**
A real `--coverage <state> <session>` CLI takes a short code (`fl`), but the public API and the
local schema's `jurisdiction_id` both key on the full OCD URI
(`ocd-jurisdiction/country:us/state:fl/government`). `quality_check.py` already has this exact
mapping (`OCD_TO_CODE`, inverted for lookup) for the 7 non-US states it tracks, and
`backfill-motion-classification.py` has a second, slightly different one (`JURISDICTION_MAP`,
also includes `va`). Per `PRIMITIVES.md`'s discipline checklist item 6: check both existing maps
before writing a third — `OCD_TO_CODE` is the natural one to import here since this work is
extending `quality_check.py` directly anyway.

**Logging location:** `PRIMITIVES.md`'s cross-cutting conventions are explicit that a new
script's output belongs under `logs/` in one of the existing shapes, not stdout-only and not a
new top-level directory. `quality_check.py` today only prints to the console (it's a manual,
ad-hoc tool) — once it's run on any kind of schedule per §7, its `Report` output should also be
written to something like `logs/quality-check/<jurisdiction>_<session>.log`, following the same
pattern `logs/backfill/` already uses for `backfill-fl-historical.sh`'s per-item output.

---

## 3. Tier 2 — Sub-Record Completeness on Bills Present in Both

This is **already mostly implemented** — `quality_check.py`'s `compare_bills()` does vote-event
count, first-vote tally, and sponsorship-count comparison with the correct WARN/FAIL split.
The only change needed: **what selects which bills to check**, not the comparison logic itself.

Today it selects "N random bills from the local DB." For this plan, add a second selection mode:
- **All bills in a just-completed backfill/session** (the highest-value moment — right after a
  historical backfill lands is exactly when "did we get everything, including every vote" needs
  an answer, per the FL 2024 vote-count bug that motivated this whole conversation)
- **All bills touched by last night's incremental scrape** (for ongoing nightly coverage,
  cheaper than a full-session sweep)

No changes needed to `compare_bills()` itself — just call it in a loop over the identifiers
gathered from §2 instead of `sample_bills()`'s random sample.

---

## 4. Handling "Extra" Bills (Local Has It, Public Doesn't)

`local_ids - public_ids` is **not automatically a failure** and needs its own categorization,
distinct from `missing` (§2):

- A bill upstream later merged/withdrew/renumbered (real, expected, low concern)
- A bill from a DDP-only historical backfill that hasn't propagated to the public index for
  some reason (worth knowing, not urgent)
- A genuine local bug producing a phantom bill (would want to know)

Recommendation: report `extra` as a separate, non-failing section of the output — visible, but
not gating — rather than folding it into the same pass/fail count as `missing`. Revisit if it
ever turns out to hide a real problem.

---

## 5. Wire Up `scraper-audit` (Structural Validity — Complementary Track)

Separate from the coverage/correctness work above, since it checks a different thing (internal
JSON shape, not agreement with a second source):

1. `cd scraper-audit && poetry install` (never done — verify Python 3.9+ compat with the repo's
   `.venv`, since it's a separate Poetry-managed environment, not the shared `.venv`)
2. Pull latest from upstream `openstates/scraper-audit` first — this clone is a year stale
   (last synced 2025-05-29); its own audit rules may have improved since
3. Point it at `$SCRAPED_DATA_DIR/<state>/` right after a scrape completes (before import, so a
   structural failure can gate the import rather than corrupt data silently landing)
4. `poetry run python main.py --entity bill` and `--entity event`, parse the SQLMesh audit
   output for warnings/errors, surface pass/fail the same way `quality_check.py`'s `Report` does
5. Decide gating: hard-fail the import on a `scraper-audit` error, or just log/alert? Recommend
   starting as **log/alert only** (like the coverage check) until it's been observed for a few
   real runs — false positives from a stale, never-run tool are likely on the first pass

---

## 6. Rate Limits — Resolved

Not a discrepancy after all — two different tiers, confirmed 2026-07-24: OpenStates offers a
**free tier (250 calls/day)** and a **licensed tier (30,000 calls/day, 2 calls/second)**.
**The `OPENSTATES_API_KEY` this project actually uses is the licensed key (30,000/day).**
`quality_check.py`'s own docstring undersells this — its "stay within 250 req/day" framing was
either written against the free tier or just chosen as an extra-conservative default for ad-hoc
sampling, not a reflection of the real budget available. With 30,000/day and 2/sec, a Tier 1
coverage sweep (~40-100 requests/session, §2) or even a full Tier 2 sub-record check across
every bill in a session is comfortably affordable, including running it across all 8
jurisdictions the same day if needed. Cadence in §7 has room to be more aggressive than
originally scoped if that's ever useful (e.g. nightly Tier 1 sweeps are now a real option, not
just the historical-backfill/monthly cadence recommended below).

**Contradicted empirically, 2026-08-09 — see §19.** A full Tier 1+2 sweep hit sustained `429`s
and connection timeouts after roughly 2,000-2,500 total requests, nowhere near the 30,000/day
this section says should apply, and recovered only after retries with multi-minute cooldowns.
Either the account's limits changed since 2026-07-24, or something distinct from the daily quota
(a burst/concurrency limiter, or contention from another process sharing the same API key) is
being tripped. Don't plan a same-day full sweep against the assumption this section states as
settled fact — budget hours, not minutes, until this is re-confirmed with whoever manages the
OpenStates account.

---

## 7. Recommended Cadence

| Check | When | Cost |
|---|---|---|
| `scraper-audit` (structural) | Every scrape run, before import | Cheapest — local only, no API calls |
| Tier 1 coverage (§2) | After every historical backfill (mandatory gate before calling a session "done"); monthly sweep across all actively-tracked sessions | ~40-100 API requests per session |
| Tier 2 sub-record (§3) | Same trigger as Tier 1, using the bill set Tier 1 just enumerated | Proportional to session size — comfortably within the 30,000/day licensed budget (§6) even at full-session scale |

Not recommended: running Tier 1/2 nightly for every jurisdiction regardless of whether
anything changed — most nights only a handful of bills move, and the historical-backfill /
monthly-sweep cadence already catches drift before it compounds.

---

## 8. Implementation Order

1. Confirm the public API's actual pagination response shape (§2's open item) — a quick lookup
   that unblocks everything else (rate limit is now confirmed, §6)
2. Add `fetch_all_public_identifiers()` + `fetch_all_local_identifiers()` and the coverage diff
   (§2) as a new mode in `quality_check.py` (e.g. `--coverage <jurisdiction> <session>`) rather
   than a new script — reuse its `Report`, DB connection, and API-key handling
3. Add the "all bills in a session" selection mode for Tier 2 (§3), reusing `compare_bills()`
   unmodified
4. Run both against the FL 2024 backfill that just completed (1,902 bills) as the first real
   test — a good stress test since it's the freshest, highest-stakes data
5. Categorize `extra` bills (§4) once real examples exist to categorize
6. `scraper-audit` (§5) — lower priority, independent track, can happen in parallel with 1-5
7. Wire into the cadence in §7 once 1-6 have been run manually at least once and proven out

---

## 9. Open Questions

- ~~What's the real pagination response shape from `v3.openstates.org/bills`~~ — **confirmed
  2026-07-28**: `pagination.page`/`max_page`/`total_items`/`per_page`, exactly as assumed.
  `per_page` caps at 20 (`per_page=100` errors "invalid per_page, must be in [1, 20]") — matches
  local `api-v3`'s own `max_per_page = 20`, so `fetch_all_public_identifiers()` uses 20.
- Should Tier 1 coverage checks also run against jurisdictions not currently in
  `active_jurisdictions` (e.g. `al`, which `quality_check.py` already samples but `ddp-sync`
  doesn't track as active) — or scope strictly to the 7 tracked states + USA federal?
- Does a coverage gap on a jurisdiction currently paused (e.g. FL's weekly scraper is paused
  during the 2023/2024 backfill — see `PLAN-fork-management.md`'s sibling context) need special
  handling, or does "run after every backfill" already cover that case naturally?

---

## 10. First Real Run — MA 194th, 2026-07-28: a real but much smaller coverage gap than first measured

**Triggered by:** the api-v3 stale-database investigation (`PLAN-open-states.md` §8.1a) — once
that bug was fixed and MA's votes/FL's 2023 session were confirmed actually being served
correctly, a direct diff against live `v3.openstates.org` still showed a smaller vote-count
mismatch on one MA bill (16 vs 18 votes), prompting "how widespread is this" — this coverage
check is the answer.

**Command:** `OPENSTATES_API_KEY=<key> python3 quality_check.py --coverage ma 194th
--tier2-limit 150`. Full output: `logs/quality-check/ma_194th.log`.

**Tier 1 (coverage) raw result:**
```
live=18542  local=10959  missing=7583  extra=0  both=10959
```

**Correction, same day — the raw 7,583/41% headline number is real as a literal
identifier-set diff, but materially overstates the actual gap.** MA's legislative process
gives every bill two identifiers over its life: a **docket number** (`HD`/`SD` prefix,
assigned when first filed) and a **bill number** (`H`/`S` prefix, assigned once formally read
in). Confirmed directly against live `v3.openstates.org`: `HD 2050` and `H 3444` exist as **two
separate, permanent bill records** with the identical title ("An Act relative to s-license
compliance") — upstream's own scraper never merges or supersedes the docket-stage record once
the bill-stage one exists. Our own scraper (`scrapers/ma/bills.py`: `bill_id = row["BillNumber"]
or row["DocketNumber"]`) deliberately keeps only **one** canonical identifier per bill, so it
never creates a duplicate docket-stage shadow record. Breaking the raw identifier sets down by
prefix confirms this is where nearly all of the gap actually is:

| Prefix | Live | Local | Gap |
|---|---|---|---|
| `H` (House bill) | 5,603 | 5,542 | 61 |
| `S` (Senate bill) | 3,225 | 3,124 | 101 |
| `HD` (House docket) | 5,849 | 1,084 | 4,765 |
| `SD` (Senate docket) | 3,865 | 1,209 | 2,656 |

**The real, meaningful gap is the `H`/`S` rows: ~162 actual bills (61+101) out of 8,828 live
bill-numbered items (~1.8%) — not 41%.** The other ~7,421 "missing" identifiers are live's
permanent docket-stage duplicates of bills we already have correctly under their bill number,
not independent missing content. Zero `extra` locally still holds (nothing phantom on our
side).

**This is a real methodology gap in the coverage-check tool itself, not just a one-off MA
quirk** — a naive identifier-set diff assumes one canonical identifier per bill per source,
which doesn't hold for any jurisdiction with a multi-stage identifier lifecycle like MA's. Any
jurisdiction with a similar docket→bill-number (or equivalent) pattern would produce the same
kind of inflated headline number. **Not yet fixed in the tool** — the right fix is probably to
normalize/exclude docket-stage identifiers from the Tier 1 diff when a jurisdiction's own data
provides a `BillNumber`/docket-linkage the way MA's does, rather than treating every raw
identifier as independently meaningful. Flag this before running Tier 1 against any other
jurisdiction (§11 below) so the same misreading doesn't happen again.

The ~162-bill real gap is still consistent with — and doesn't change — the starvation root
cause below: MA hasn't completed a fresh full scrape since 2026-06-16, so new bills introduced
since then (real ones, under real bill numbers) would show up exactly as this kind of small,
genuine `H`/`S` gap.

**Tier 2 (sub-record completeness) result, on 150 of the 10,959 bills we do have:**
```
599/601 passed | 1 warnings | 1 failures | 0 skipped
```
The single "failure" recorded is the Tier 1 headline number itself (folded into the same
report); the actual Tier 2 sub-record checks were **599/600 clean** — only one bill had a
stale `latest_action` text (a timing/staleness difference, not a structural problem). Titles,
vote-event counts, and sponsorship counts all matched. **This reframes the finding: it is not
a data-quality problem on bills we've scraped — it's specifically a coverage problem.**
Something is causing MA's scraper to silently stop well short of the full bill list, upstream
of any vote-serving or database-layer bug.

**Root-caused 2026-07-28 — not network rejections. MA has not completed a single full scrape
since 2026-06-16, over six weeks ago, and every weekly attempt since has silently failed to
finish.** Grepped every available log (current `logs/scraper.log` plus both `.gz` archives)
for MA's own completion markers:

```
[Tue Jun 16 18:30:21 EDT 2026] Scrape done: ma. Starting import...
[Tue Jun 16 18:35:06 EDT 2026] Import done: ma.
```

**That is the only successful completion in the entire log history available.** Every
subsequent weekly attempt (2026-06-22, 06-24, 06-27, 06-29, 07-11, 07-18, 07-25 — confirmed via
their own `Starting scrape: ma` markers) has **zero** matching `Scrape done: ma.`/`Import done:
ma.` anywhere in the logs. Our local replica's ~10,891-10,959 MA bills are frozen at whatever
the June 16th run captured; every "weekly MA scrape" since has been silently running and never
finishing, not silently dropping bills mid-flight.

**Two compounding root causes, both confirmed directly in the code and logs:**

1. **MA never actually gets incremental mode, despite having it implemented.**
   `run-scrape.sh` computes its incremental-cutoff lookup key as
   `SCRAPE_KEY=$(echo "${STATE}${SESSION_ARG:+ $SESSION_ARG}" | tr ' =' '__')` — when
   `run-all-scrapes.sh` invokes MA's weekly run with no explicit session argument (`bash
   run-scrape.sh "$state"` inside the `for state in va mi ma ut az` loop), `SESSION_ARG` is
   empty, so `SCRAPE_KEY="ma"` and the script looks for `logs/last-run/ma.ts` — **which does
   not exist and never has.** The file that *does* exist,
   `logs/last-run/ma_session_194th.ts` (last written 2026-07-03), is an orphan from some
   earlier manual/explicit-session invocation and is never consulted by the automated weekly
   run. Net effect: every weekly MA run silently falls back to a **full** scrape (confirmed —
   every `Starting scrape: ma` log line says `(full)`, never `(incremental cutoff=...)`, unlike
   every other jurisdiction in the same batch), restarting from bill #1 every single week.
2. **A full MA scrape is far too slow to complete in the time it's actually given.** MA's own
   government API (`malegislature.gov/api/GeneralCourts/194/Documents`) currently returns
   **11,406** documents in one response (212 of them docket-only placeholders with no bill page
   yet — a separate, minor, ~2% issue, not the main gap). The scraper then fetches each
   individual bill's detail page one at a time; timestamps in the 2026-07-25 log show roughly
   one bill every 4-10 seconds (each bill needs two sequential HTTP round-trips — a `scrapelib`
   fetch of the bill page immediately followed by a `requests` fetch of the same URL). At that
   rate, a full ~11,000+ bill pass is on the order of **12+ hours** — and because of bug #1
   above, MA never gets to skip that cost on a second run; it pays the full multi-hour cost
   every single week, and apparently never finishes before something (the next scheduled batch,
   a restart, etc.) supersedes it.

**Not network rejections** — the logs show a normal-looking, slowly-progressing scrape (only 2
"Server Error" warnings found, both for the docket-only-placeholder bills in finding #2 above,
not a mass rejection pattern). This is a **starvation** problem: a full scrape that's too slow,
combined with a caching bug that guarantees it can never benefit from being faster on a repeat
run.

**Fix, scoped but not yet implemented:**
1. Fix `run-all-scrapes.sh`'s MA invocation to pass an explicit `session=194th` argument (the
   same pattern FL's own invocation already uses for its multiple sessions), so `SCRAPE_KEY`
   correctly resolves to `ma_session_194th` and the existing (if stale) incremental
   infrastructure actually engages.
2. That alone doesn't fix the *first* full pass, which still needs to complete once to
   establish a real cutoff — worth running as a one-off, monitored, long-running backfill
   (matching the pattern already used for FL's historical backfill) rather than hoping a
   routine weekly cron window is long enough.
3. Once incremental mode is actually engaging, confirm subsequent weekly runs are fast (only
   bills that changed) and finally complete — the `MI`'s "semantics unverified" caveat
   (`PLAN-incremental-scraping.md`) is a reminder to actually verify the date-signal MA's
   incremental mode uses (`PrimarySponsor.ResponseDate` — already flagged there as a "weak
   proxy") once this is unblocked, not just assume it's correct.

**Not yet done:** running this same Tier 1 check against the other 7 tracked jurisdictions to
determine whether this specific bug (missing session arg in the weekly batch invocation) or
this general shape of problem (a scrape too slow to complete before being superseded) affects
anyone else. `run-all-scrapes.sh`'s invocations for `va`, `mi`, `ut`, `az` all have the same
"no explicit session" shape as MA's — worth checking whether they simply have small enough
sessions that it never mattered, or whether they have the same latent bug.

**Before running Tier 1 against another jurisdiction, check for the same docket/bill-number
duplication pattern first** (§10's correction above) — inspect the raw headline `missing` count
by identifier prefix before reporting it as a real gap. Not every jurisdiction has a multi-stage
identifier lifecycle like MA's, but assume nothing until checked; a raw diff can look far worse
than reality for any jurisdiction that does.

---

## 11. Follow-up audit, 2026-08-02 — §10's fix landed in dead code

**Correction, 2026-08-03 (§12): this section's framing that the underlying behavior is itself
"the real bug" is wrong** — `session=None` is deliberate, correct behavior for jurisdictions
with more than one currently-active session (VA, UT), not an oversight. The factual findings
below (where the code actually runs, what the logs show) still stand; the "what needs to
happen" fix proposals do not — see §12 before acting on them.

**§10's proposed fix (item 1: pass an explicit `session=194th` argument for MA) was built —
[`ddp-open-states` commit `a139ca2`](https://github.com/Digital-Democracy-Project/ddp-open-states/commit/a139ca2)
(2026-07-28), changing `run-all-scrapes.sh` to invoke
`bash run-scrape.sh ma "session=194th"`.** Confirmed still present in the file today. On its own
terms, this is exactly the fix §10 asked for.

**But `run-all-scrapes.sh` is no longer the production scheduler for secondary-state scrapes.**
`ddp-sync/config/sync_schedule.yaml` states outright: *"Replaces the ad-hoc
run-all-scrapes.sh launchd job."* The real driver is `ddp-sync`'s own
`run_secondary_scrapes_job()` (`ddp-sync/src/ddp_sync/pipelines/openstates_scrape.py:589-608`),
which fans out over `secondary.jurisdictions` (`va, mi, ma, ut, az`,
`sync_schedule.yaml:263-268` — no `sessions:` key for this block, unlike `fl`/`usa`, which do
have one) via `asyncio.gather(*[_run_scrape(j, None, openstates_root) for j in jurisdictions])`
— **`None` is passed as the session arg unconditionally, for every jurisdiction in that list,
including MA.** `_run_scrape` (same file, ~line 210-225) only appends a session argument
`if session_arg:` — so the live, actually-scheduled path still invokes MA bare, exactly the
behavior §10 diagnosed as the root cause. **The fix in `a139ca2` never had a chance to run in
production** — `run-all-scrapes.sh` is dead code as far as the real weekly schedule is
concerned.

**What this means concretely, re-checked against real logs:**
- MA did complete a full scrape on 2026-08-01 (`logs/scraper.log`: `bills_scraped=1597`,
  `Scrape done: ma.`/`Import done: ma.`) and a real incremental run followed the same day
  (45 bills, correct `cutoff=` applied) — so MA is no longer frozen at June 16th, and
  incremental mode is genuinely engaging now.
- But it's engaging under cache key `ma` (`logs/last-run/ma.ts`), not the `ma_session_194th`
  key §10's diagnosis was built around — that keyed file still doesn't exist. The mechanism
  works today only because `_run_scrape`'s `session_arg=None` path happens to produce a stable,
  reusable key of its own (`ma`), not because §10's fix engaged.
- Two attempts that *did* pass an explicit session (`logs/scraper.log`, 2026-07-30) both
  **failed** (`ERROR: scrape/import failed for ma`) — so the "correct per §10" invocation shape
  is, ironically, the one that's actually broken right now. Root cause of that failure not yet
  investigated — flagged here, not solved.
- **1,597 bills for a full MA pull is well short of the ~11,406 documents** §10's own
  investigation measured live for the 194th session. Not reconciled — could be a real residual
  coverage gap, a scope difference (e.g. docket-only placeholders correctly excluded per §10's
  own HD/SD finding), or something else. Needs a fresh Tier 1 coverage run to actually quantify,
  not assumed either way here.

**Still open, unchanged from §10 as of this audit:**
- `quality_check.py`'s Tier 1 diff still has no HD/SD docket-duplicate normalization — any
  future coverage run against MA (or any jurisdiction with a similar multi-stage identifier
  lifecycle) will still overstate the real gap the same way the initial 41%-vs-1.8% headline did.
- Tier 1 has not been run against VA/MI/UT/AZ — ~~to check whether they share MA's
  no-explicit-session shape in the code path that actually matters~~ **superseded by §12: this
  is no longer the right reason to run it.** Still worth running for its own sake (real coverage
  data on 4 more jurisdictions), just not as a bug hunt for this non-bug.
- `scraper-audit` (§5) — still completely untouched, zero commits since the initial clone.

~~**Not decided here:** whether the real fix belongs in `_run_scrape`'s caller (thread each
jurisdiction's session through `sync_schedule.yaml`'s `secondary.jurisdictions` list, the same
way `fl`/`usa` already carry an explicit `sessions:` block) or in `run_secondary_scrapes_job`
itself defaulting each jurisdiction to its current session via the same lookup
`list_current_session_bill_candidates` uses elsewhere. Either fixes the real bug; `a139ca2`'s
fix to the now-bypassed `run-all-scrapes.sh` does not, for any of the five secondary
jurisdictions, not just MA.~~ **Neither of these should be built — see §12.**

---

## 12. Correction, 2026-08-03 — §11 was wrong: `session=None` is deliberate, load-bearing
behavior, not a bug. Closed as [OPEN-24](https://digitaldemocracyproject.atlassian.net/browse/OPEN-24)

**Filed as a Jira ticket (OPEN-24) with §11's "what needs to happen" list as the proposed fix.
Investigated before building either option — both would have been regressions.**

`openstates-core`'s `do_scrape()` (`cli/update.py:108-125`) has an explicit, deliberate
fallback: when no session is passed, it scrapes **every currently-active session** for that
jurisdiction (`for session in active_sessions:`), where "active" comes from each jurisdiction's
own scraper module (`check_session_list()`, same file, ~lines 319-337). This is documented
behavior, not an incidental artifact of omitting an argument.

**Checked what's actually active right now, from real scrape logs** (correlating
`Starting scrape: <state>` with the immediately-following `no session provided, using active
sessions: {...}` line):

| Jurisdiction | Active sessions right now |
|---|---|
| VA | `2026S1` **and** `2027` — two, simultaneously |
| UT | `2026` **and** `2025S2` — two, simultaneously |
| AZ | `57th-2nd-regular` — one |
| MI | `2025-2026` — one |
| MA | `194th` — one |

**VA and UT each have two sessions active at once, confirmed directly against
`openstates-scrapers/scrapers/va/__init__.py` and `.../ut/__init__.py` (two `"active": True`
entries each).** Either fix §11 proposed — hardcoding one session per jurisdiction into
`sync_schedule.yaml`, or dynamically resolving "the current session" and passing just one —
would silently stop scraping whichever second active session didn't get picked, for VA and UT
specifically. **The current `session=None` behavior isn't a bug for those two; it's the only
thing today that scrapes both of their active sessions in a single pass.**

For AZ/MI/MA (one active session each right now), hardcoding wouldn't lose anything, but it
also wouldn't fix anything real: MA is already confirmed reliably engaging incremental caching
under the bare `ma` cache key since 2026-08-01 (§11 above), and the cache key not being
session-scoped isn't causing any observed failure — it's not reset per-session, but nothing
currently depends on it being reset either.

**Net: there is no real defect here as §10/§11 scoped it.** Both docs assumed "no explicit
session arg" was itself the problem, without checking what that fallback actually does for
jurisdictions with more than one simultaneously active session. It isn't a problem — it's
necessary, correct behavior for VA/UT today, and harmless (if redundant) for AZ/MI/MA.
**OPEN-24 closed without a code change.**

**If a real, narrower problem surfaces later** — e.g. specifically wanting the cache key to be
session-aware without restricting which sessions get scraped — that needs its own ticket scoped
around that distinction, not a return to either option §11 proposed.

---

## 13. Repo audit, 2026-08-03 — no progress on §12's open items, but a new MA reliability bug found

**Checked:** this repo plus nested `openstates-core`/`openstates-scrapers`/`people`, the
`ddp-sync-dev` checkout, and prod `ddp-open-states`'s live logs (read-only) for anything
relevant to this plan since §12 was written.

**§12's four open items are all still exactly where they were — no commits have touched any of
them:**
- **HD/SD docket-duplicate normalization** — `quality_check.py` unchanged since `4025d31`
  (2026-07-29). Still a raw identifier-set diff; nothing added to exclude a jurisdiction's
  docket-stage duplicates the way MA's `H`/`S` vs `HD`/`SD` split needed.
- **Tier 1 against VA/MI/UT/AZ** — never run. Prod's `logs/quality-check/` still contains only
  `ma_194th.log`, last written 2026-07-28.
- **`scraper-audit` (§5)** — still zero commits since the initial clone, and the directory isn't
  even present in this checkout's working tree right now (it's `.gitignore`d and was never
  actually cloned here, consistent with "never run," not a regression).
- **Cadence wiring (§7)** — still nothing scheduled; the tool remains manual/ad-hoc.

**One genuine confirmation, from `ddp-sync-dev`:** commit `6008660` ("docs: explain why
session_arg=None is deliberate in run_secondary_scrapes_job", merged same day as §12 via PR #22)
adds a 7-line comment directly above `run_secondary_scrapes_job`'s `asyncio.gather(*[_run_scrape(j,
None, ...)])` call in `openstates_scrape.py`, spelling out verbatim the VA/UT two-active-session
finding from §12. Good outcome — §12's conclusion is now load-bearing in the code itself, not
just this doc, which lowers the odds of OPEN-24 getting re-litigated by someone who hasn't read
this plan.

**New finding: the two 2026-07-30 MA scrape failures §11 already noted, plus a third on
2026-07-31 that §11 didn't mention, all share one previously-undiagnosed root cause.** Re-reading
prod's `logs/scraper.log` around each `ERROR: scrape/import failed for ma` line shows all three
are the same class of bug — an **uncaught network exception propagating all the way up through
`do_scrape()` and killing the entire multi-hour run outright**, not three unrelated incidents:

```
2026-07-30 20:55:10  ReadTimeout       fetching a Senate roll-call PDF   scrape_senate_vote (ma/bills.py:517)
2026-07-31 16:11:53  ReadTimeout       fetching a Senate roll-call PDF   scrape_senate_vote (ma/bills.py:517)
2026-07-31 22:16:42  ConnectionError   fetching /Bills/194/S404/CoSponsor  get_as_ajax (ma/bills.py:569)
```

`ma/bills.py`'s main per-bill fetch (`scrape_bill`, line ~178) already wraps its `self.get(...)`
call in `try/except requests.exceptions.RequestException`, logging a warning and skipping the
bill rather than crashing — but `scrape_senate_vote`'s `self.urlretrieve(vurl)` (line 517) and
`get_as_ajax`'s `s.get(url)` (line 569, called from `scrape_cosponsors`) have no equivalent
guard, so a single transient timeout hitting either of those two call sites takes down the whole
run. The scraper's own `self.raise_errors = False` (set in `__init__`) doesn't help here — that
setting suppresses `scrapelib` re-raising on bad HTTP status codes, not connection-level
exceptions like `ReadTimeout`/`ConnectionError`, which propagate regardless.

**Why this matters for §10's starvation diagnosis:** §10 already established that a full MA
scrape takes ~12+ hours and, at the time, couldn't benefit from incremental caching due to the
session-key bug (since resolved in production per §11's re-check). This finding adds a second,
independent reason full MA scrapes kept failing to complete even after the cache-key situation
stabilized: **a single transient network hiccup anywhere in an 11,000+ document, multi-hour pass
is fatal, with no partial-progress checkpoint** — every failure means restarting from bill #1
again. The run that finally succeeded (2026-08-01 00:04:19 → 05:44:58, ~5h40m,
`bills_scraped=1597`) did so because it happened not to hit a transient network error in that
particular window, not because anything was fixed.

**Still not reconciled, now with a partial (negative) lead:** 1,597 bills for that clean, fully
completed run is still far short of both the ~11,406 live documents §10 measured and even the
~8,828 live `H`/`S` bill-numbered items alone (i.e. excluding docket duplicates, per §10's own
correction) — a >5x gap. Checked and ruled out chunking as the explanation:
`ma/bills.py scrape()`'s `scrape_chunk_number` parameter defaults to `None` (unchunked full
scrape), confirmed directly in source, and `run-scrape.sh`/`ddp-sync`'s invocation never passes
it. The network-failure pattern above doesn't explain it either, since this specific run
completed with no errors logged. **A fresh, dedicated Tier 1 run against current MA data is the
only way to actually quantify this** — flagged here, not solved.

**Recommendation, not yet implemented (an `openstates-scrapers` fix, not a `quality_check.py` /
coverage-tooling one — outside this plan's own scope, but directly explains why this plan's own
MA measurements keep landing on incomplete, restarting runs):** wrap `scrape_senate_vote`'s
`urlretrieve` call and `get_as_ajax`'s `s.get` call in the same
`try/except requests.exceptions.RequestException` pattern `scrape_bill` already uses two hundred
lines above them in the same file — skip the one vote/cosponsor record on a transient failure
rather than aborting the entire session's scrape.

---

## 14. Tier 1 finally run against every tracked jurisdiction, 2026-08-03 — closes §13's item #2,
and finds a real bug that predates this whole plan

Same day as §13, immediately after: ran `quality_check.py --coverage <jurisdiction> <session>
--tier2-limit 1` against every currently-tracked jurisdiction+session pair — AL, AZ, FL, MA, MI,
UT (both active sessions), VA (both active sessions), and US — closing the open item §11/§13 kept
carrying forward ("Tier 1 has never been run against VA/MI/UT/AZ"). Full raw results committed to
`notes/tier1-coverage-all-jurisdictions-20260803.md` (PR #68); summarized here:

| Jurisdiction | Session | Live | Local | Missing | Extra |
|---|---|---|---|---|---|
| AL | 2026rs | 1507 | 1507 | 0 | 0 |
| AZ | 57th-2nd-regular | 2190 | 2190 | 0 | 0 |
| FL | 2026 | 1931 | 1897 | 34 | 0 |
| MA | 194th | 18604 | 11094 | 7510 | 0 |
| MI | 2025-2026 | 3884 | 3884 | 0 | 0 |
| UT | 2026 | 1016 | 1016 | 0 | 0 |
| UT | 2025S2 | 5 | 5 | 0 | 0 |
| VA | 2026 | 3637 | 3637 | 0 | 0 |
| VA | 2026S1 | 300 | 300 | 0 | 0 |
| US | 119 | 18052 | 0 → **bug, see below** | 18052 → **bug, see below** | 0 |

**8 of 9 real (non-US) jurisdiction/session pairs came back completely clean.** FL 2026 has a
small, real, unexplained gap (34/1931, ~1.8%) — not investigated further here, consistent with
normal drift rather than a systemic problem. MA 194th's ~40% headline is presumed still dominated
by the same HD/SD docket-vs-bill-number duplication artifact §10 diagnosed on 2026-07-28 (that
run: 41% raw / ~1.8% real after the prefix breakdown) — **not re-confirmed by prefix on today's
numbers**, so treat as unconfirmed, not restated as fact, until someone actually re-runs that
breakdown against today's `missing` set.

**The US row surfaced a real bug in the coverage-check tool itself, not a coverage gap.**
`fetch_all_local_identifiers()` (the function Tier 1 uses to query the local side) filtered on
`j.id LIKE '%/state:{jurisdiction_code}/%'` — every state jurisdiction's OCD id has a `state:`
component, but US federal's (`ocd-jurisdiction/country:us/government`) doesn't, so the query
silently matched zero rows for `jurisdiction_code="us"` no matter how much data actually existed
locally. A direct SQL query against the same DB, bypassing the tool, confirmed local `us`/`119`
actually holds exactly 18,052 bills — matching live exactly. **This means Tier 1 has never once
been able to correctly check US federal coverage since it was built on 2026-07-28** — every
mention in this plan (including §9's own open question and the "8 tracked jurisdictions: 7 states
+ USA federal" framing) assumed US was checkable the same way the 7 states are, and it silently
never was. `sample_bills()`/`sample_bills_us()` (used by the tool's older, non-`--coverage`
sample-based mode) already special-case US the exact same way for the exact same reason —
`fetch_all_local_identifiers()` had simply never been given the same treatment when it was
written.

**Fixed same day** — [PR #69](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/69):
`fetch_all_local_identifiers()` now branches on `jurisdiction_code == "us"` and does an exact
match on the federal OCD id, mirroring `sample_bills_us()`'s existing approach, instead of trying
to force US through the state-shaped `LIKE` pattern. Verified directly (not yet re-run through the
full paginated `--coverage us 119` CLI path, to avoid re-paginating live's ~900 pages twice in one
day): `fetch_all_local_identifiers(conn, "us", "119")` now returns 18052, matching live exactly;
`fetch_all_local_identifiers(conn, "mi", "2025-2026")` still correctly returns 3884, confirming no
regression on the unchanged state-jurisdiction path.

**Also added same day** — [PR #67](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/67):
a new `--tier2-random` flag. `--tier2-limit N` on its own has always taken the first N identifiers
in sorted order, which for almost every jurisdiction means the earliest-filed, lowest-numbered
bills every single time — not a representative sample of a session's overall health. Combined
with `--tier2-limit`, `--tier2-random` samples N bills at random from the both-APIs set instead.
`--tier2-limit`'s original first-N behavior is unchanged when `--tier2-random` isn't passed.

**Operational note for next time:** running a Tier 2 sample concurrently with a separate Tier 1
sweep still in progress (done today, testing `--tier2-random` against MI while the US federal
Tier 1 run was still finishing) produced a run of live-API `429 Too Many Requests` errors —
plausibly the combined request rate from two independent processes, each individually
rate-limiting itself to the licensed tier's 2 req/sec, but not coordinating with each other,
briefly exceeding it. Not investigated further or fixed here (this is a manual-invocation
footgun, not a cadence-automation concern per §7, since nothing today runs two of these
concurrently on a schedule) — just flagged so a future concurrent manual run isn't surprised by
spurious `live API error` failures that are rate-limit noise, not real Tier 2 findings.

**First real use of `--tier2-random`, same day: MI, 500-bill random sample.** Run directly against
the fixed script (`quality_check.py --coverage mi 2025-2026 --tier2-limit 500 --tier2-random`),
overlapping with the tail end of the Tier 1 sweep above (hence the 429s noted above). Result:
`1996/2073 passed | 46 warnings | 31 failures`. Of the 31 failures, 23 are the rate-limit `429`
noise described above — the remaining **8 are genuine `local is MISSING votes vs live` findings**,
the exact failure mode this whole plan exists to catch, on a real, randomly-sampled cross-section
rather than the lowest-numbered bills a first-N sample would always return:

| Bill | Local votes | Live votes |
|---|---|---|
| HB 4023 | 1 | 2 |
| HB 4187 | 1 | 3 |
| HB 4750 | 1 | 3 |
| HB 5233 | 1 | 2 |
| HB 5249 | 1 | 2 |
| HB 5697 | 1 | 3 |
| SB 205 | 2 | 3 |
| SB 716 | 1 | 2 |

8 of 500 (~1.6%) MI bills sampled are missing at least one vote event compared to live — every
one under-counts by exactly 1, never over-counts, and none are `title`/`latest_action`/
`sponsorship` mismatches (those checks passed clean on all 8). **Not yet root-caused** — could be
a systemic gap (e.g. a specific vote type MI's scraper misses) or independent per-bill drift;
worth a follow-up look at what these 8 bills' missing votes have in common before writing this
off as random noise. This is the first Tier 2 finding from this plan on any jurisdiction other
than MA, and the first ever from a properly random (rather than first-N or MA-only) sample.

**Still open after today, updated from §13's list:**
- HD/SD docket-duplicate normalization (§10/§12/§13) — still not built.
- `scraper-audit` (§5) — still untouched.
- Cadence wiring (§7) — still nothing scheduled.
- MA's docket/bill-number prefix breakdown — needs to be re-run against *today's* numbers, not
  just assumed to match the 2026-07-28 pattern.
- The 8 MI vote-count gaps above — not root-caused.
- A real Tier 2 sweep at a meaningful sample size (not `--tier2-limit 1`) has now been run against
  one jurisdiction other than MA (MI, 500 bills, above) — AL/AZ/FL/UT/VA/US still only have the
  placeholder 1-bill Tier 2 check from today's sweep.

## 15. Full Tier 2 sweep, a real vote-comparison bug found and fixed, and a 250-bill
re-verification, 2026-08-03

Later the same day as §14: PR #70 decoupled Tier 2 from Tier 1 (a standalone `--tier2` flag,
sampling straight from the local DB via `sample_local_bills_for_session()` instead of paying
Tier 1's full-pagination cost first), closing out §14's last open item — a real 500-bill
`--tier2-random` sweep was then run against *every* tracked jurisdiction/session (AL, AZ, FL, MA,
MI, US, UT×2, VA×2 — 10 pairs). Full results in `notes/*-tier2-500-bill-random-sample-20260803.md`
(PRs #71/#72). Headline: AL/US/both UT sessions/VA's special session came back clean; AZ, FL, MA,
MI, and VA's regular session all showed real or apparent issues — but the single largest warning
category **in every jurisdiction** was "first vote counts differ" (557 instances total: AZ 113,
FL 87, MA 3, MI 29, US 2, UT×2 174, VA×2 149).

**Root cause: `compare_bills()` compared vote tallies by list position, not by identity.**
`local_votes[0]` vs. `live_votes[0]` — whichever vote event happened to be first in each side's
list — breaks the instant the two APIs order or paginate a bill's vote events differently, which
turned out to be common. Several of the original writeups already suspected this (vote *event
counts* matched in most flagged bills; only the "first" one's tally looked wrong).

**Fixed in two steps, PR #73:**
1. Group vote events by calendar date (`start_date[:10]` — both APIs return a full ISO timestamp
   like `2026-02-25T03:28:00-05:00`, but only the date portion is reliable to match on) and
   compare tallies only within a shared date, instead of by list position.
2. That alone left same-day multi-vote bills (companion votes, committee + floor, or a
   "vote-a-rama" of amendments all dated the same day) still misordered one level deeper — same
   fix, applied within a date via `zip()`. Since `identifier` is blank on both APIs for every
   jurisdiction checked, group same-date votes by `motion_text` (e.g. "Passed", "do pass amended")
   first, falling back to positional pairing only for whatever's left unmatched.

**Verified against a 156-bill stratified sample** of previously-flagged bills (all of MA/US/UT
2025S2/VA 2026S1, plus 30-bill random samples of AZ/FL/MI/UT 2026/VA 2026 — done at reduced scale
because the live API was answering in ~13-15s/request that day from cumulative sweep volume, not
its normal sub-second speed): 88 of 156 fully resolved by date-matching alone; the motion_text
step resolved most of the rest. **Only 9 of 156 (5.8%) held up as genuine local-vs-live tally
disagreements** under every possible same-date pairing — e.g. VA HB 973 (94 vs. 93 "yes" votes),
MI SB 501 (32/0/5 vs. 36/0/0). One residual, confirmed-unfixable case: VA HB 30, whose ~15
same-day amendment votes all share the identical generic motion_text "Adopt Governor's
Recommendation R" — no field in the data distinguishes "amendment #7 of 15" from any other, so
this bill will keep surfacing spurious warnings indefinitely; it's a data-modeling limit, not a
bug. Full methodology in `notes/quality-check-vote-date-matching-fix-20260803.md`.

**Re-ran the full 10-jurisdiction sweep post-fix at 250 bills** (`notes/*-tier2-250-bill-post-fix-sweep-20260803.md`,
branch `notes/tier2-250-bill-post-fix-sweep-20260803`, not yet PR'd):

| Jurisdiction | Pass rate | Warnings: 500-bill run → 250-bill post-fix run |
|---|---|---|
| AL 2026rs | 100% | 0 → 0 |
| AZ 57th-2nd-regular | 94.3% | 119 → 28 |
| FL 2026 | 97.1% | 112 → 18 ("first vote counts differ" 87 → 0) |
| MA 194th | 97.7% | 12 → 6 |
| MI 2025-2026 | 96.4% | 61 → 16 ("first vote counts differ" 29 → 4) |
| US 119 | 98.9% | 0 → 0 |
| UT 2026 | 99.1% | 173 → **0** |
| UT 2025S2 | 100% | 1 → 0 |
| VA 2026 | 93.7% | 254 → 98 |
| VA 2026S1 | 95.4% | 1 → 26 (all 26 trace to the single VA HB 30 case above) |

**New finding surfaced by the re-sweep, not by the fix itself:** 20 of VA 2026's 36 remaining
vote-tally warnings share one exact signature — all dated 2026-02-17, all local "yes" count
exactly one higher than live, every other tally field matching — consistent with one shared
floor "block vote" roll call (VA runs bills through en-bloc passage days) missing or gaining a
single member's vote, applied identically across ~20 bills at once rather than 20 independent
bugs. VA HB 973 (flagged "genuine" during the 156-bill verification) is part of this same pattern,
not an isolated case. Not root-caused further.

**Still open after today:**
- Everything carried forward from §14 (HD/SD dedup, `scraper-audit`, cadence wiring, MA prefix
  re-check, MI's 8 vote-count gaps — now possibly related to the same class of finding as VA's
  2026-02-17 block vote, worth reconciling together).
- ~~VA's 2026-02-17 block-vote single-vote discrepancy (~20 bills) — not root-caused; would need
  to identify which specific member's vote differs and cross-check against VA's own record.~~
  **Resolved, see §17.**
- FL's "local has MORE votes than live (our fix not merged?)" pattern (18-25 instances across
  runs) — still not diagnosed, flagged as a possible undocumented local fix or vote-duplication
  artifact in both the original FL writeup and this section's fix, never followed up.
- The `notes/tier2-250-bill-post-fix-sweep-20260803` branch (10 notes docs + this plan update) is
  not yet opened as a PR.

## 16. OPEN-28 root-caused, 2026-08-05 — MI's 8 vote-count gaps are a single mass-vote-day capture
failure (2026-07-03), distinct from OPEN-19/21/22/23's staleness pattern

Follow-up on §14/§15's open item. Full writeup:
`notes/mi-open-28-missing-vote-root-cause-20260805.md`. Headline findings:

- **All 8 original bills still show the identical gap, unchanged, 8 days later** — re-checked
  directly against local api-v3 (`localhost:8002`) and live `v3.openstates.org`. Every missing vote
  on every bill is dated **2026-07-03**.
- **A fresh 90-bill sample of vote-bearing MI bills found 9 more (10%)** — 8 new, all also missing
  only a 2026-07-03 vote. Combined: 17 missing-vote instances, 17/17 dated 2026-07-03, spanning
  House Roll Calls #288–334 and Senate Roll Calls #190–225 — a single chamber-wide floor day (almost
  certainly a pre-July-4th-recess mass passage day), not scattered independent drift.
- **Not the same mechanism as OPEN-19/21/22/23.** Those tickets' pattern (documented starting
  2026-08-01) is whole-bill staleness: a currently-active WAF block fails the main bill-page fetch,
  freezing title/latest_action/votes together. This finding is narrower and older: as of the
  original 2026-07-28 snapshot, the 8 bills' title/latest_action/sponsorship all matched live —
  only votes were affected. (Re-checking today, those same 8 bills' `latest_action` *has* since
  drifted stale too — the general pattern has now separately started affecting them sometime after
  07-28, layering a second, newer problem on top of the old one.)
- **Root cause, confirmed by code + git history + test coverage:** `scrapers/mi/bills.py`'s
  `parse_roll_call()` (called from `scrape_votes()`) silently catches
  `scrapelib.HTTPError`/`WafBlockDetected` on its per-vote journal-document fetch, logs a warning,
  and returns `None` — dropping that one vote with no other signal. Unlike `scrape_bill()`'s
  main-page fetch and `events.py`'s fetch, this catch never registers with
  `MIWafCircuitBreakerMixin`, so it's invisible to the consecutive-block counter, `ScrapeError`
  aborts, and OPEN-22's escalation history. Confirmed via `git log -L`: none of OPEN-17/18/19/21/22/23
  ever touched this except-block's logic (only OPEN-23 touched the surrounding function at all, to
  add the matched-UA parameter). Confirmed via `test_bills.py`: zero test coverage of
  `scrape_votes`/`parse_roll_call`'s failure path.
- A plausible (not confirmed) trigger: a general, all-jurisdiction 4-day nightly-scrape outage,
  2026-07-04→07-08 (`notes/mi-cams-headed-browser-spec-20260802.md` §3), immediately followed
  2026-07-03's mass vote day — but a transient outage alone doesn't explain 33+ days of permanence;
  that's `parse_roll_call`'s silent-swallow doing the actual damage on every retry since.

**Disposition:** OPEN-28 closed with this conclusion (not folded into OPEN-19/21/22/23 — genuinely
different mechanism). [OPEN-30](https://digitaldemocracyproject.atlassian.net/browse/OPEN-30) was
filed for the `parse_roll_call` fix itself (register with `MIWafCircuitBreakerMixin`, stop silently
swallowing, add test coverage) — mirrors how OPEN-18's investigation spawned OPEN-21/OPEN-22 as
separate tickets rather than bundling a fix into the investigation.

**Still open after today:**
- Everything else carried forward from §14/§15 (HD/SD dedup, `scraper-audit`, cadence wiring, MA
  prefix re-check, ~~VA's 2026-02-17 block-vote discrepancy~~ **resolved, see §17**, FL's "local
  has MORE votes" pattern, the not-yet-PR'd `tier2-250-bill-post-fix-sweep-20260803` branch).
- [OPEN-30](https://digitaldemocracyproject.atlassian.net/browse/OPEN-30) (the `parse_roll_call`
  fix) itself — not yet implemented, just filed.
- Whether other single-day mass-vote gaps exist elsewhere in MI's session besides 2026-07-03 — this
  investigation's 90-bill sample only surfaced the one date.

## 17. OPEN-26 root-caused, 2026-08-05 — VA's 2026-02-17 vote gap is one legislator's House vote,
dropped by live's own ingest, not our bug

Follow-up on §15's open item ("VA's 2026-02-17 block-vote single-vote discrepancy... not
root-caused"). Full writeup: `notes/va-open-26-bennett-parker-vote-root-cause-20260805.md`.
Headline findings:

- **One shared event, confirmed by a direct local-vs-live per-voter diff** (not just aggregate
  `counts`) — HB 1030 and HB 973 (two independent 2026-02-17 roll calls) each show exactly one
  voter present in local's data and absent from live's, and it's the same person both times:
  **Elizabeth B. Bennett-Parker**. A same-day `/architect-ticket` pass in a sandbox without local
  DB/API access had pointed at Kirk McPike instead, via a roster-comparison method that couldn't
  distinguish "missing because dropped" from "missing because not yet seated" — McPike's own
  `people` record postdates this vote entirely, an unrelated false lead.
- **Local is correct; live is missing a real vote.** Bennett-Parker won a VA Senate special
  election 2026-02-10 and was sworn in 2026-02-18 — one day *after* this vote — so she was still a
  sitting Delegate on 2026-02-17. Checking her presence across every one of HB 1030's votes (not
  just 2026-02-17) shows every other shared date matches exactly between local and live; **only
  2026-02-17 disagrees** — isolated to this one date, not a general "drop transitioned members"
  policy, consistent with a narrow ingest/snapshot-timing glitch in live's own pipeline.
- **Blast radius: 266 of 3,637 local VA 2026 bills, not ~20.** A full-corpus scan (all 3,637
  bills, paginated) found 338 bills with a 2026-02-17 vote, 266 sharing this exact signature; a
  fresh random 8-bill sample of the newly-found bills confirmed the pattern directly against live.
- **Not actionable on our end** — the gap is entirely in `v3.openstates.org`'s own data, a system
  this project doesn't control; our scraper and import already have this correct.

**Disposition:** OPEN-26 closed with this conclusion. [OPEN-32](https://digitaldemocracyproject.atlassian.net/browse/OPEN-32)
was filed (mirroring how OPEN-28's investigation spawned OPEN-30 rather than bundling a fix into
the diagnostic ticket) proposing extending `compare_bills()` with a per-voter diff and same-date
blast-radius helper — this is the second "one shared date, many bills" finding this quarter (after
OPEN-28/MI) that needed ad hoc, by-hand analysis to name the specific voter and size the blast
radius; the tool itself still can't do either as first-class output.

**Still open after today:**
- Everything else carried forward from §14/§15/§16 (HD/SD dedup, `scraper-audit`, cadence wiring,
  MA prefix re-check, FL's "local has MORE votes" pattern, the not-yet-PR'd
  `tier2-250-bill-post-fix-sweep-20260803` branch, OPEN-30 itself).
- [OPEN-32](https://digitaldemocracyproject.atlassian.net/browse/OPEN-32) (the `compare_bills()`
  per-voter-diff/blast-radius tooling ticket) itself — not yet implemented, just filed.
- Whether live's same ingest issue recurs for other mid-session chamber transitions — not checked
  beyond Bennett-Parker's case.

---

## 18. OPEN-42, 2026-08-08 — HD/SD dedup finally built (generalized, not MA-only), and the
§13 scraper-crash root cause finally fixed — both still awaiting a live re-run

**Ticket:** [OPEN-42](https://digitaldemocracyproject.atlassian.net/browse/OPEN-42), scoped by
`OPEN-42-architecture-assessment-20260808.md` (this repo) as Approach C: fix the two
already-diagnosed defects blocking AC1-AC3 (§10, §13 above), and generalize the HD/SD fix instead
of hand-coding a MA-only branch — rather than re-running the backfill against the same unfixed
defects a fourth time (§10's fix was flagged but not built; §11 and §14 both re-confirmed it was
still open).

**1. `openstates-scrapers/scrapers/ma/bills.py` — §13's root cause fixed.** `scrape_senate_vote`'s
`self.urlretrieve(vurl)`, `get_as_ajax`'s `s.get(url)`, and (found during implementation, same
unguarded-`urlretrieve` shape, not previously flagged by §13's specific log lines but confirmed by
direct code read) `get_house_pdf`'s `self.urlretrieve(vurl)` now all catch
`requests.exceptions.RequestException`, log a warning, and signal failure (`None`/`False`) to their
callers instead of letting the exception propagate up through `do_scrape()` and killing the entire
multi-hour run — mirroring `scrape_bill`'s existing skip-and-continue pattern two hundred lines
above them in the same file. Every caller (`scrape_cosponsors`, `get_action_page`/`scrape_actions`,
the Senate/House roll-call branches in `scrape_action_page`, `scrape_house_vote`) now checks for
that sentinel and skips the one affected vote/cosponsor/action-page record rather than crashing or
yielding malformed data. New tests: `openstates-scrapers/tests/test_ma_bills.py` (13 cases,
confirmed to fail against the pre-fix code and pass against the fix).

**2. `quality_check.py` — §10's methodology gap fixed, generalized rather than MA-only.** Added
`DOCKET_PREFIX_MAP` (a plain dict next to the existing `OCD_TO_CODE`, currently `{"ma": {
"docket_prefixes": ("HD", "SD")}}`) plus `split_missing_by_docket_prefix()`, which
`run_coverage_check()` now calls on the raw Tier 1 `missing` set before deciding pass/fail: an
identifier under a jurisdiction's registered docket prefixes is reported as an informational
`docket_duplicate` (WARN) rather than folded into the FAIL headline. `breakdown_by_prefix()` prints
the same kind of H/S/HD/SD table §10 built by hand, generically, for any jurisdiction's Tier 1
output going forward — not just MA's. Jurisdictions absent from `DOCKET_PREFIX_MAP` (the other 6:
FL, WA, MI, UT, AL, AZ, plus US) get byte-identical `missing`/pass-fail behavior to before this
change — confirmed by the new tests treating "unmapped jurisdiction" as an explicit case, not just
an assumption. New tests: 5 cases added to `test_quality_check.py` (22 total in the file now,
all passing), covering the MA-shaped split, the unmapped-jurisdiction passthrough, an
unrecognized-identifier-shape edge case, and the prefix-breakdown helper directly.

**What this does and doesn't close:** both fixes are merged-to-branch code, verified with unit
tests run in an ad hoc local venv (this workspace has no Postgres/live-API access) — they remove
the *causes* §10 and §13 diagnosed, but neither one is the same thing as AC1/AC2/AC3 actually being
satisfied against production data. Per the architecture assessment's own Prerequisites section,
still explicitly open, not done here, and not to be read as done by a future skim of this doc:

- **AC1 (full MA backfill completes) / AC2 (162-bill gap closed, `quality_check.py --coverage ma
  194th` re-run):** requires running the actual multi-hour backfill against the production
  checkout's live Postgres + MA's live government API, which this workspace cannot do. The
  scraper fix removes the specific crash cause §13 found in the 2026-07-30/07-31 failures, but
  §13's *other*, still-unreconciled finding — the one clean 2026-08-01 run only captured 1,597
  bills, >5x short of the ~8,828 live `H`/`S` figure, for a reason that isn't network failure or
  chunking — is **not** explained or fixed by this ticket's changes. A fresh backfill's bill count
  needs to be checked against that ~8,828 figure directly, not just against a clean exit code.
- **AC3 (identifier anomaly broken out by prefix, explained or fixed):** the mechanism is now
  built and durable (won't need re-litigating a fourth time the way §10→§11→§14 did), but the
  actual current numbers still need a live `--coverage ma 194th` run to print the real, current
  `missing_by_prefix` breakdown — today's fix has only been verified against synthetic test data,
  not a live MA diff.
- **AC4 (215/348 org/person numbers refreshed):** unchanged by this ticket; requires the fresh
  full import from AC1 before there's anything new to count.
- **AC5 (plan docs updated):** this section closes the part of AC5 that's actually in this repo.
  The other half — `ddp-infra/PLAN-open-states.md` §8.1a and
  `ddp-infra/PLAN-local-openstates-migration.md` §1.4 — lives in a different repo (moved
  2026-08-07; this repo's own `PLAN-open-states.md` is now a stub pointing there) and needs its
  own PR against `ddp-infra`, not a change bundled into this one.

**Still open after today:**
- Both items above (AC1/AC2's actual execution, AC3's live re-run) — operational actions against
  the production checkout, next.
- §13's unreconciled 1,597-bill mystery — still not root-caused; flagged again here so it isn't
  lost between this doc update and whoever runs the next backfill.
- The `ddp-infra` doc update (AC5's other half).
- Everything else already carried forward from §14/§15/§16/§17 that this ticket didn't touch
  (`scraper-audit`, cadence wiring, FL's "local has MORE votes" pattern, OPEN-30/32, etc.).

---

## 19. Full Tier 1+2 sweep across every tracked jurisdiction, 2026-08-09 — AL dropped, rate
limits contradicted §6, MA's real gap confirmed small

**What ran:** `quality_check.py --coverage <jurisdiction> <session>` against all 10 currently
tracked jurisdiction/session pairs (AL excluded on request — nothing scrapes it), against the
real production DB (`ddp-openstates-postgres-1`, port 5433) and the live `v3.openstates.org` API.
Full writeup, per-jurisdiction ranking table, and raw logs:
`notes/tier1-tier2-quality-check-all-jurisdictions-20260809.md`.

**Headline results:** 7 of 10 pairs have a perfectly clean Tier 1 diff (0 real missing bills);
the other 3 have small, specific, named gaps — WA (2 bills), MA (124 bills, after the §18
docket-prefix correction — not the raw 7,521), and FL (34 bills, plus a 7.6% Tier 2
vote-completeness gap on the sampled bills, reconfirming the still-open OPEN-27 WAF bug). Full
per-jurisdiction numbers are in the notes doc, not repeated here.

**Rate limits did not behave like §6 describes.** See the correction appended directly to §6
above. First attempt (Tier 2 sample=15) hit `429` on the 4th of 10 pairs. A second attempt (Tier
2 sample=500, per this session's direction) got through only 5 of 10 before every subsequent
jurisdiction crashed repeatedly despite 5 retries with 90-second cooldowns. A third, more patient
pass (7-minute cooldowns, 100-bill sample) finally got the remaining 5 through. Total elapsed
time across all three attempts: roughly 4.5 hours, for what §6 describes as a same-day,
comfortably-affordable sweep. This needs resolving with whoever manages the OpenStates account
before the cadence in §7 can be trusted at face value.

**New tool-accuracy finding, not yet fixed:** during Tier 2 sampling, individual per-bill live
fetches that hit `429`/`502`/timeout get recorded by `compare_bills()` as a generic FAIL ("live
API error"), indistinguishable at a glance from an actual content mismatch. On the jurisdictions
hit hardest by rate limiting (VA 2026S1, FL, AZ), this inflated the raw FAIL count by 28-38
per pair — real content failures had to be manually separated from infra noise by grepping for
the "live API error" string and excluding those bills from both the numerator and denominator.
Worth a tool fix: give live-API infra errors their own report symbol (or an explicit `SKIP`)
instead of overloading `FAIL`, so a rate-limited run doesn't look like a data-quality regression
at a glance.

**Also found, unrelated to this plan, filed separately:** a stray, 46-day-stale duplicate
`openstates` database living inside an unrelated project's Postgres container (`ddp-agents`'s
`cams` container, port 5432) — created, best guess, by some past tool run against
`quality_check.py`'s default `DATABASE_URL` with no explicit port, silently colliding with
whatever else was already listening on 5432. Filed as Jira `AGENTS-5`, not acted on beyond that
(read-only investigation only).

**Not run:** `scraper-audit` (§1b/§5) — still never executed, still the one check in this plan's
three-check model (§7) with zero real runs to date.
