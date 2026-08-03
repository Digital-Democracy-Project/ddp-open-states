# PLAN: Coverage & Completeness Checks Against Public OpenStates

**Status:** IMPLEMENTED (Tier 1 + Tier 2) 2026-07-28 — `quality_check.py --coverage
JURISDICTION SESSION`, per §8's implementation order. First real run against MA found a large,
genuine coverage gap — see §10. **Audited again 2026-08-02: §10's proposed fix was built, but
in a script that's no longer the production driver. See §11 — and then §12: §11's own framing
("the underlying bug is still live") doesn't hold up either. Filed and closed as
[OPEN-24](https://digitaldemocracyproject.atlassian.net/browse/OPEN-24), not a real defect —
`session=None` is deliberate, load-bearing behavior for jurisdictions with more than one active
session, not a bug. See §12 before acting on §11's "what needs to happen" list.**

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
