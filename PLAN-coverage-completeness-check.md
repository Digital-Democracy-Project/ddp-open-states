# PLAN: Coverage & Completeness Checks Against Public OpenStates

**Status:** IMPLEMENTED (Tier 1 + Tier 2) 2026-07-28 — `quality_check.py --coverage
JURISDICTION SESSION`, per §8's implementation order. First real run against MA found a large,
genuine coverage gap — see §10.

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

## 10. First Real Run — MA 194th, 2026-07-28: a large, genuine coverage gap

**Triggered by:** the api-v3 stale-database investigation (`PLAN-open-states.md` §8.1a) — once
that bug was fixed and MA's votes/FL's 2023 session were confirmed actually being served
correctly, a direct diff against live `v3.openstates.org` still showed a smaller vote-count
mismatch on one MA bill (16 vs 18 votes), prompting "how widespread is this" — this coverage
check is the answer.

**Command:** `OPENSTATES_API_KEY=<key> python3 quality_check.py --coverage ma 194th
--tier2-limit 150`. Full output: `logs/quality-check/ma_194th.log`.

**Tier 1 (coverage) result:**
```
live=18542  local=10959  missing=7583  extra=0  both=10959
```
**7,583 of MA's 18,542 live bills for the 194th session (~41%) are missing from the local
replica entirely** — not scraped-and-incomplete, never scraped at all. Zero `extra` (nothing
locally that isn't also live) — so this isn't a phantom-bill or renumbering artifact, purely a
one-directional gap.

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

**Not yet root-caused as of this entry** — see `notes/` for the follow-up investigation into
MA's scraper logs (network rejections vs. a pagination/limit bug in
`scrape_bill_list()`'s single-shot fetch from `malegislature.gov/api/GeneralCourts/{session}
/Documents`, which has no visible pagination handling).

**Not yet done:** running this same Tier 1 check against the other 7 tracked jurisdictions to
determine whether this is MA-specific or a systemic gap across the whole replica. Given the
size of this one finding, that comparison should happen before deciding how broadly to invest
in a fix.
