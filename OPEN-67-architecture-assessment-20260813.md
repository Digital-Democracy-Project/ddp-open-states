# Architecture Assessment: OPEN-67 — Utah House/Senate chamber swap, 2026-03-05 to 2026-04-26

## Architectural Question

OPEN-67 asks "what changed in the Utah scraper/pipeline between 2026-04-26 and 2026-06-15 that
fixed the chamber-assignment bug, and is any other field affected?" — framed as if the fix
necessarily lives in this repo's Utah scraper. Before answering that literally, the real
question this assessment needs to settle is: **does the evidence actually support a scraper-side
fix, and if the investigation can't be completed from inside `ddp-open-states` alone, what's the
right way to say so and hand off the rest?**

## Tech Stack / Investigation Context

| Layer | What it is | Relevant to this ticket |
|---|---|---|
| `ddp-open-states` (this repo) | DDP's local "shadow" OpenStates pipeline — scrape/import orchestration, quality-check tooling | Repo root only; everything else is gitignored (see below) |
| `openstates-scrapers/` | Vendored checkout, DDP fork of `openstates/openstates-scrapers` (formal fork since 2026-07-03) | Contains `scrapers/ut/bills.py` — the actual Utah vote/chamber-assignment code |
| `openstates-core/` | Vendored checkout, DDP fork of `openstates/openstates-core` (formal fork since 2026-08-01) | Contains the Vote/Bill importer and Utah chamber metadata (`metadata/data/ut.py`) |
| `api-v3` | Local mirror of the real OpenStates `api-v3`, served on `:8002` | Not what production reads (see finding below) |
| `ddp-broker-py` | **Not present in this repo/workspace** — a separate service | Where the reported bug and its evidence actually live |

**Critical scope finding, confirmed from this repo's own docs (`RUNBOOK.md:10-13`, `README.md:4-8`):**
> "A shadow pipeline that runs OpenStates scrapers locally... Production services (ddp-broker-py,
> ddp-sync, votebot) still point at `v3.openstates.org`." / "DDP's production services still read
> from the public API — this pipeline exists for validation against it."

So during the entire bug window (2026-03-05 through 2026-06-15+), `ddp-broker-py` was reading
Utah data from the **real, public `v3.openstates.org`**, run on OpenStates' own infrastructure —
not from anything in this Mac Studio checkout. (The gradual per-jurisdiction cutover to DDP's own
replica for `ddp-broker-py` didn't even begin until a read-scoped key was issued 2026-06-25,
*after* the ticket's fix date, per `RUNBOOK.md:1181-1198`.) Per `project.toml`'s `repo.path` rule
(`project-config.md`): this repo is the only directory to investigate in, and `ddp-broker-py` not
being present here is itself a real finding to report, not something to route around by looking
for a stray broker checkout elsewhere on the machine.

## Investigation Performed

Rather than guess, I did the git archaeology the ticket asks for, against both this fork and the
real upstream project (added a temporary read-only `upstream` remote pointing at
`github.com/openstates/openstates-scrapers`, fetched full history back through 2025, removed the
remote when done — no repo state changed).

**Every commit touching `scrapers/ut/bills.py` from 2025-10-06 through 2026-08-12 (upstream, full
history, not just this fork's shallow local clone):**

| Date | Commit | What it touched |
|---|---|---|
| 2025-10-06 | `1ee0e37d1` | Special session slug handling, legal citations |
| 2025-10-30 (×2) | `7f1be1ebf`, `96f1da6b5` | Committee names in referrals, doc URL handling |
| 2025-11-12 | `eda6f6e97` | Committee as related entity on actions |
| 2025-12-30 (×2) | `5de27ceeb`, `e8773c1d7` | HTML header tag / lint fix |
| **2026-01-01 → 2026-04-12** | **(none)** | **No changes to this file for ~3.5 months** |
| 2026-04-13 | `a10522814` | SSL verification bypass only (`verify=False` on 4 `self.get()` calls) — no chamber logic |
| **2026-04-14 → 2026-06-15** | **(none)** | **No changes** |
| 2026-06-16 | `5e345a2d0` | **The only candidate — see below** |

**Every chamber-mapping site in this file, at every point in its history, maps the same way —
House → `lower`, Senate → `upper` — with no reversed version ever committed:**
- `scrape()`: bill-id prefix `H`/`S` → chamber (unchanged since file's earliest visible history)
- `scrape_bill_details_from_api()`: action `owner`/`description` starting `"House"`/`"Senate"` →
  `lower`/`upper` (unchanged)
- `parse_status()`: action text split on `"House"`/`"Senate"` → `lower`/`upper` (unchanged)
- `SPONSOR_HOUSE_TO_CHAMBER = {"H": "lower", "S": "upper"}` (unchanged)
- `openstates-core`'s `metadata/data/ut.py` (`lower=House`, `upper=Senate`) — one commit ever,
  unrelated, long predates this window

**The one real change, commit `5e345a2d0` (merged 2026-06-16, one day after the ticket's
confirmed fix boundary):**

```python
# before: dead code — a generator function created but never iterated, so nothing inside
# it ever ran. Zero votes, zero sponsorships-from-votes, nothing, for every 2025+ (API-
# rendered) Utah session bill, since this code was first written.
self.scrape_bill_details_from_api(bill, url, session_slug)

# after:
yield from self.scrape_bill_details_from_api(bill, url, session_slug)
```
...plus, inside that function, **brand-new** vote-emission code with correct chamber logic from
day one (`"lower" if action_data["voteHouse"] == "H" else "upper"`) — there is no prior version
of this specific code to have been reversed, because it never existed before this commit.

The PR title says exactly what it fixed: *"UT: fix votes not scraped for 2025+ sessions
(API-rendered bills)"* — a **missing-votes** bug, not a **swapped-chamber** bug. It's a deliberate,
well-documented fix, but for a different, adjacent problem.

## The Gap This Leaves

The evidence supports "Utah's 2025+-format session bills had **zero** votes scraped by OpenStates
until 2026-06-16" — not "votes existed with the chamber reversed." That's a real discrepancy with
the ticket's own finding (real votes, on real bills, with chamber backwards, every day from
2026-03-05 to 2026-04-26). Two explanations remain open, and neither can be resolved from inside
this repo:

1. **`ddp-broker-py` (or something between it and `v3.openstates.org`) derives `origin_chamber`
   itself** — e.g. inferring it from the vote/bill identifier or motion text rather than trusting
   OpenStates' `Vote.chamber` field verbatim — and that derivation, not this scraper, is where the
   swap and its fix actually live. This is the most likely candidate given the scraper evidence is
   otherwise clean.
2. **A code path this assessment couldn't fully rule out**: whatever OpenStates' *actual deployed*
   production scraper looked like during March–April (it need not exactly match what's merged to
   `main` today if there was an intermediate revert/rewrite not visible even in the full upstream
   history, though none was found), or a bulk-data/import layer on OpenStates' side not covered by
   `scrapers/ut/bills.py` or `openstates-core`'s metadata.

Both require access this session doesn't have: real `v3.openstates.org` history/API key, and/or
`ddp-broker-py`'s own codebase (not present in this workspace, and per `project-config.md`, not
something to go looking for elsewhere on the machine even if a checkout exists).

## Approaches Evaluated

### Approach A: Treat this fork's own commit history as sufficient
**How it works:** Answer the ticket from `git log` on `ddp-open-states` and its nested checkouts
as currently synced, without reaching for real upstream history.
**Pros:** Fastest, zero external dependency.
**Cons:** This repo's own top-level history only starts 2026-08-02; the nested `openstates-scrapers`
checkout is whatever's currently on fork `main` — a shallow local clone doesn't show the full
timeline of what shipped when. Would have missed that `a10522814` (the only other UT-touching
commit in the window) is SSL-only and irrelevant, and would have had no way to confirm the
chamber-mapping logic has *never* been reversed anywhere in this file's history.

### Approach B: Exhaustive upstream git archaeology (what this assessment did)
**How it works:** Add a temporary, read-only `upstream` remote at the real
`openstates/openstates-scrapers` (and equivalent for `openstates-core`), fetch full history,
trace every commit touching the relevant files across the whole window plus enough of a margin
before and after to rule out edge effects.
**Pros:** Authoritative for "what has this codebase ever done" — complete, free, read-only, fully
within `repo.path` (these are the tracked-by-reference vendored checkouts this ticket is scoped
to). Directly answers whether the *scraper's* chamber logic was ever wrong (it wasn't) and
identifies the one real change in the window (`5e345a2d0`).
**Cons:** By itself, proves a negative (the swap isn't in this scraper) but can't complete AC1/AC2,
which implicitly assume the fix lives here.

### Approach C: Cross-boundary verification — the missing piece
**How it works:** Two concrete, low-cost steps to close the actual gap:
1. Reuse the existing `quality_check.py` primitive (see `PRIMITIVES.md:217-225` — built exactly
   for local-vs-live diffing against `v3.openstates.org`) with a real `OPENSTATES_API_KEY` to check
   what the real production API says today (and, if OpenStates exposes any revision history for
   these bills/votes, historically) for the cited bills (HB392, HB223, HB136, HB68, HB32, HB209,
   HB479, SB189, SB234, SB194, SB153) — this determines whether the swap ever existed
   *upstream of* `ddp-broker-py`, or whether it's purely a `ddp-broker-py`-side artifact.
2. Hand the `ddp-broker-py`-side half explicitly to whoever owns that repo — its own Motion
   sync/chamber-derivation code and its deploy history around 2026-06-15 — rather than have this
   ticket silently under-deliver on AC1/AC2/AC4. `PRIMITIVES.md`'s own "Cross-repo?" checklist
   (item 7) already anticipates exactly this: *"If the work touches how ddp-sync, ddp-agents/CAMS,
   or ddp-broker-py consume this repo's output, check their own PLAN docs too."*
**Pros:** Actually closes the investigation instead of stopping at a plausible-looking but
unconfirmed correlation. Respects the repo boundary (`project-config.md`) instead of quietly
reaching outside it. Reuses an existing tool (`reuse-before-reinvent.md`) instead of writing a new
one-off diff script.
**Cons:** Requires a real API key (operator-supplied, not present in this session) and requires
someone with `ddp-broker-py` access to finish the loop — this assessment can't fully execute step 2
itself.

## Tradeoff Matrix

| Dimension | A: fork-only | B: upstream archaeology | C: cross-boundary verification |
|---|---|---|---|
| Completeness | Low | Medium (rules out scraper, can't confirm broker) | High (closes the actual gap) |
| Cost | Trivial | Low (read-only, done) | Low–Medium (needs API key + broker-repo owner) |
| Confidence in conclusion | Low | High for what it covers | High, once executed |
| Respects `repo.path` boundary | Yes | Yes | Yes (explicitly hands off rather than reaching outside) |
| Answers ticket ACs as scoped | Partially, unreliably | Answers AC1/AC4 partially, AC2/AC3 incompletely | Only path that can fully answer all four ACs |

## Recommendation: Approach C, built on Approach B's findings

**Why this approach:** The ticket's own acceptance criteria assume the fix is knowable from "the
Utah scraper/pipeline" — Approach B (already performed, in full, for this assessment) shows that
assumption doesn't hold: the scraper's chamber logic has never been wrong, and the one real change
in the window fixed a different (missing-votes) bug that only coincidentally lines up in time.
Reporting that finding *as* the answer — the way Approach A would, taking the correlation with
`5e345a2d0` at face value — would be a plausible-looking but unconfirmed conclusion, which is
exactly what "never rubber-stamp" and the ticket's own explicit AC2 ("confirm whether the fix was
deliberate or a side effect") are guarding against here.

**Why not the alternatives for this specific ticket:** Approach A is what produces a wrong answer
convincingly (the commit really is one day off from the ticket's boundary, and it really is the
only relevant commit in the window — it's an easy trap). Approach B alone is honest but
incomplete — it tells you where the bug *isn't*, not where it *is*.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `quality_check.py` run reveals `v3.openstates.org` itself never had the swap either | Medium | Confirms root cause is 100% `ddp-broker-py`-side; scope this ticket's remaining ACs to a `ddp-broker-py` ticket | Already the leading hypothesis given the evidence above |
| No historical/versioned data available from `v3.openstates.org` to check March–April state | Medium-High | Can only confirm current-state correctness, not historical swap | Still valuable — rules out an ongoing bug; pair with `ddp-broker-py`'s own logs/deploy history for the historical question |
| `ddp-broker-py` owner unavailable / no immediate access | Medium | AC1/AC2/AC4 stay open | Document the finding precisely (this assessment) so the handoff is a five-minute read, not a re-investigation |

**Prerequisites:** A real `OPENSTATES_API_KEY` (operator-supplied, per `quality_check.py`'s own
usage docs) to run step 1; access to `ddp-broker-py`'s repo/history for step 2.

**Tech debt created:** None. This is a diagnostic step, not a code change.

## Standards Checklist

| Standard | Status | Notes |
|---|---|---|
| Root-cause discipline (don't stop at first correlated change) | Addressed | This is the core finding of this assessment — the June 16 commit correlates in time but doesn't match the reported symptom |
| System/repo boundaries (`project-config.md` `repo.path`) | Addressed | Explicitly did not go looking for a `ddp-broker-py` checkout elsewhere on the machine; flagged its absence as a finding instead |
| Reuse before reinvent (`reuse-before-reinvent.md`) | Addressed | Recommends reusing `quality_check.py` rather than writing a new diff script |
| Cross-repo dependency documentation (`PRIMITIVES.md` item 7) | Addressed | Matches this repo's own established checklist for exactly this situation |
| OWASP Top 10 | N/A | No code/endpoint change proposed |
| Multi-tenancy | N/A | Not applicable to this investigation |
| Idempotent migrations | N/A | No migration involved (the follow-up broker-side dedup ticket the reporter already scoped will need this) |

## Next Step

This ticket's four ACs can't be fully closed from `ddp-open-states` alone. Recommended sequence:
1. Run `quality_check.py` against `v3.openstates.org` for the cited Utah bills (needs a real
   `OPENSTATES_API_KEY` — ask the operator).
2. Comment on OPEN-67 with this assessment's findings (the clean chamber-logic history, the
   `5e345a2d0` correlation-but-not-cause, and the `ddp-broker-py` boundary) so the remaining
   investigation can be hemmed to `ddp-broker-py`'s own Motion-sync code and 2026-06-15 deploy
   history rather than restarting from scratch there.
3. Separately: flag `5e345a2d0`'s Yeas/Nays heading-selector change
   (`page.xpath("//b")[1:]` → `page.xpath('//font[@face="Arial"][@size="5"]')` in
   `parse_html_vote`) as a partial answer to AC3 — vote tallies/rosters for Utah, not just chamber,
   were touched by the same commit, independent of whatever caused the chamber swap itself.

If the operator confirms cross-repo access is available, run `/plan-ticket` next scoped to
steps 1–2 above; otherwise this may need a `CODEBOT_QUESTION`-style handoff to whoever owns
`ddp-broker-py`.
