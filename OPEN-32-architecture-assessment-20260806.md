# Architecture Assessment: OPEN-32 — `compare_bills()` per-voter diff + same-date blast-radius helper

## Architectural Question

`compare_bills()` (`quality_check.py:281-419`) already detects a vote-tally mismatch
(`tally(lv) != tally(rv)`, line ~398-404) but only ever prints the two aggregate `counts` dicts —
finding the *specific* differing voter, and sizing how many other bills share the same date's
discrepancy, both currently require a throwaway one-off script (as OPEN-26 and OPEN-28 each did).
The question is **where the per-voter diff and blast-radius logic should live relative to
`compare_bills()`'s existing DB-free, pure-diff design, and how the blast-radius check should
source its data (local DB vs. live API) without blowing the file's own 250-req/day budget.**

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Script | `quality_check.py` (repo root) | Single-file CLI, no framework; `psycopg2` (raw SQL, no ORM) + `requests` |
| Local DB | Postgres `:5433`, OCD schema (`opencivicdata_bill`, `opencivicdata_voteevent`, `opencivicdata_personvote`) | Django models in `openstates-core/openstates/data/models/vote.py` |
| Local API | `localhost:8002` (api-v3, fixed dev key) | Serves the same OCD data as JSON |
| Live API | `v3.openstates.org` (`OPENSTATES_API_KEY`) | Rate-limited, 250 req/day license tier |
| Vote JSON shape | `api-v3/api/schemas.py:337-358` | `VoteEvent.votes: List[PersonVote]` (`{option, voter_name}` — per-voter) vs. `VoteEvent.counts: List[VoteCount]` (`{option, value}` — aggregate, what `tally()` already reads) |
| Output | `Report` class (`quality_check.py:79-102`) | ✓/✗/~/`-` line-per-check; PRIMITIVES.md: reuse for any new comparison output, don't hand-roll prints |
| Tests | None exist for `quality_check.py` today | Greenfield — `psycopg2`/`pytest` (9.0.3) both importable in this environment |

**Key schema fact driving the design:** each vote event object already carries both fields side by
side — `v["counts"]` (what `tally()` diffs today) and `v["votes"]` (the per-voter list the ticket
wants diffed: `{"voter_name": "...", "option": "..."}`). No new fetch is needed — `local`/`live`
already contain everything the per-voter diff needs; the existing `fetch_bill(..., include=[...,
"votes", ...])` call already requests it.

## Approaches Evaluated

### Approach A: Extend `compare_bills()`'s signature with optional `conn`/jurisdiction/session params; per-voter diff stays pure, blast-radius is a separate local-DB-only helper called from the same branch

**How it works:**
- Inside the existing `if lc != rc:` block (line ~402), before/alongside the existing
  `report.record(WARN, ...)` call, diff `lv["votes"]` against `rv["votes"]` as sets of
  `(voter_name, option)` tuples. The symmetric difference (`local_only`, `live_only`) names exactly
  which voter(s) differ and on which option — this is pure Python, no I/O, testable with plain
  dicts.
- Add a new standalone function, e.g. `count_shared_date_signature(conn, jurisdiction_code,
  session, date, voter_signature, exclude_identifier)`, that runs **one parameterized SQL query**
  against the already-open local Postgres connection, joining
  `opencivicdata_bill → opencivicdata_voteevent → opencivicdata_personvote`, scoped to the same
  jurisdiction/session/date, matching any `(voter_name, option)` in `voter_signature`, excluding the
  bill already being compared, returning `COUNT(DISTINCT bill.id)`. This is exactly OPEN-26's
  Step 3 (page the local corpus checking every 2026-02-17 vote for Bennett-Parker's presence) —
  just expressed as one indexed join instead of 182 paginated live-API requests.
- `compare_bills()` gains three **optional, default-`None`** parameters (`conn=None,
  jurisdiction_code=None, session=None`). When `lc != rc` and all three are supplied, call the
  helper and append its count to the *same* `report.record(WARN, ...)` detail string (not a new
  `report.record` call) — satisfying AC #3's "additive detail on an existing WARN, not a new
  check" literally. When they're `None` (e.g. a future caller/test that only wants the per-voter
  diff), the blast-radius portion is silently skipped — the per-voter diff still fires.
- All three call sites (`main()`'s bill loop, `run_coverage_check()`, `run_tier2_only_check()`)
  already hold an open `conn` and already know their jurisdiction short-code and session as plain
  strings in scope (`jcode`/`"us"` in `main()`; the `jurisdiction`/`session` parameters in the other
  two) — no new lookups, no re-deriving jurisdiction from `OCD_TO_CODE` (which doesn't even cover
  `va`, the jurisdiction that motivated this ticket and is deliberately excluded from
  `JURISDICTIONS`/`OCD_TO_CODE` today — see "Residual finding" below).

**Pros:**
- Keeps the per-voter diff itself DB-free and trivially unit-testable (plain dicts in, string out).
- The blast-radius query costs zero live-API budget — pure local Postgres, respecting the file's
  own documented 250 req/day ceiling and `run_coverage_check()`'s existing rate-consciousness
  (`time.sleep(0.5)` between live calls).
- Matches the ticket's own wording precisely: AC #2 says "checks other **local** bills," not "live
  bills" — this is the literal OPEN-26 Step 3 method, not OPEN-26 Step 4's separate live spot-check.
- Additive-only signature change (new params default `None`) — no existing caller breaks.
- Reuses the `us`/`state:` jurisdiction split every other local-DB helper in this file already uses
  (`fetch_all_local_identifiers`, `sample_local_bills_for_session`) rather than inventing a fourth
  copy of that branch.

**Cons:**
- Touches `compare_bills()`'s signature and all 3 call sites (small, mechanical diff, but real).
- If the same signature repeats across many bills in one run (as OPEN-26's 266-bill blast radius
  would), the identical query re-runs once per affected bill unless memoized — cheap per call, but
  worth a simple cache (see Risks table).

### Approach B: Per-voter diff inline (per AC #3), blast-radius as a fully separate, manually-invoked CLI mode (new `--blast-radius` flag), decoupled from `compare_bills()`

**How it works:** `compare_bills()` only grows the per-voter diff. The blast-radius helper becomes
a standalone function wired to a new `argparse` mode (mirroring `--tier2`/`--coverage`'s existing
"separate opt-in mode" pattern), invoked by a human after they notice a WARN and want to size it —
e.g. `quality_check.py --blast-radius va 2026 2026-02-17 "Elizabeth B. Bennett-Parker" yes`.

**Pros:** Zero signature change to `compare_bills()`; cleanest possible separation; matches how
`--tier2`/`--coverage` are already separate, deliberately-invoked modes in this file.

**Cons:**
- Doesn't actually automate the thing OPEN-26/OPEN-28 did by hand — it automates the *counting*
  step but still requires a human to notice the WARN, read off the date/voter/option by hand, and
  re-invoke the tool with them as CLI args. The ticket's own framing ("automating the blast-radius
  sizing both OPEN-26 and OPEN-28 did by hand") is explicitly about removing that manual step, not
  just the SQL-writing step.
- Since the query is a single cheap local-only SQL join (no API budget consumed), there's no real
  resource justification for deferring it to manual invocation the way `--coverage`'s expensive
  full-corpus live pagination genuinely does.

### Approach C: Fully automated, including a live-API blast-radius verification (replicate OPEN-26's Steps 3 *and* 4 automatically)

**How it works:** Same as Approach A, but after counting local matches, also re-fetch a sample of
the newly-found bills from the live API to confirm the pattern generalizes (OPEN-26's Step 4).

**Pros:** Most thorough — closest to fully reproducing OPEN-26's complete investigation
automatically.

**Cons:**
- Directly contradicts AC #2's own scope ("checks other **local** bills... reports a count" — no
  mention of live re-verification).
- Consumes live-API budget non-deterministically and unboundedly per WARN encountered — a single
  Tier-2 sweep that hits the OPEN-26 pattern would try to re-verify against live for some slice of
  266 bills, on top of whatever budget the sweep itself already spent, directly violating the
  250 req/day ceiling this file's own docstring and `run_coverage_check()`'s pacing exist to
  protect.
- Over-scoped vs. the ticket; the live spot-check remains a valuable *manual* follow-up step for a
  human to run once, deliberately, as OPEN-26 did — not something to fire automatically and
  repeatedly inside a routine sample sweep.

## Tradeoff Matrix

| Dimension | A: inline pure diff + local-DB helper | B: diff inline, blast-radius as separate CLI mode | C: also auto-verify via live API |
|---|---|---|---|
| Complexity | Low-Med | Low | Medium-High |
| Time to implement | Low-Med | Low | Medium |
| Fully automates the by-hand process | Yes | Partial (still requires manual re-invocation) | Yes, but over-scoped |
| API budget impact | None (local DB only) | None | Unbounded, per-WARN |
| Matches AC #2's literal scope ("local bills... a count") | Exact | Under-delivers vs. ticket's own framing | Over-scoped |
| Matches AC #3 ("additive detail on existing WARN") | Exact | Exact (for the diff half only) | Exact (for the diff half only) |
| Testability | High (diff is pure; helper is one mockable query) | High | Lower (live-call paths need more elaborate mocking) |
| Alignment with codebase (`us`/`state:` split, `Report` reuse, parameterized SQL) | High | High | High |

## Recommendation: Approach A

**Why this approach:**
- It is the literal reading of both ACs: AC #2 asks for a **local**-bills count, which is exactly
  OPEN-26's Step 3 method expressed as one SQL join instead of 182 paginated API calls; AC #3 asks
  for the diff to land as detail on the **existing** WARN, which Approach A does by extending the
  same `report.record()` call's detail string rather than adding a second one.
- Reuses this file's own established conventions rather than inventing new ones (`reuse-before-
  reinvent.md`): the `us`/`state:` LIKE-pattern split already exists twice
  (`fetch_all_local_identifiers`, `sample_local_bills_for_session`) and should become a third,
  not a fourth, near-identical branch; `Report`'s ✓/✗/~/`-` convention is reused unchanged
  (`PRIMITIVES.md` explicitly calls this out for any new comparison tooling).
- Zero live-API cost keeps the new check safe to leave *on* by default inside every routine sweep
  (`--tier2`, `--coverage`, the plain sample run) — the whole point of automating this is that the
  next Bennett-Parker/mass-vote-day pattern gets sized the moment it's first seen, not on a second,
  manually-triggered pass.
- Optional/default-`None` parameters mean the signature change is additive, not breaking — any
  existing or future caller (including tests) that doesn't care about blast-radius sizing is
  unaffected.

**Why not the alternatives:**
- **Not B** — it satisfies AC #3 but only partially satisfies AC #2's actual intent. The ticket's
  context section is explicit that the pain point was the *manual* trigger-and-size loop, not the
  arithmetic; making the count-helper itself automatic-but-manually-invoked still leaves that loop
  in place, just with less typing.
- **Not C** — directly exceeds AC #2's stated scope (local bills, a count) and reintroduces the
  exact rate-limit risk this file was designed around from its first line of its own docstring.
  The live spot-check remains valuable as a deliberate, human-triggered follow-up (as OPEN-26 did
  it) — not something to run unattended inside a routine sweep.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Same signature repeats across many bills in one run (OPEN-26's pattern was 266 bills), each re-running an identical query | High whenever this exact pattern recurs | Low (each query is cheap/indexed, just redundant) | Memoize by `(jurisdiction_code, session, date, frozenset(voter_signature))` within a single run — a plain dict cache local to the run, not a new persistence layer |
| New raw SQL introduces a SQL-injection surface (voter names come from API data, not a fixed literal) | Low if done correctly, but worth being explicit about | High if done wrong | Use `%s` parameter placeholders for every value (jurisdiction pattern, session, date, voter_name, option, excluded identifier) exactly as every existing query in this file already does — never f-string a value into the SQL text, only the query *shape* (e.g. the `us`/`state:` branch), matching `database.md`'s parameterized-query rule and OWASP A03:2021 |
| `votes`/`counts` keys missing or malformed on one side (partial API response) | Low — same defensive-`.get()` pattern already used everywhere else in this file | Low (would raise on `.get()` chains if not guarded) | Use the same `local.get("votes") or []` defensive pattern already used for `local_votes`/`live_votes` earlier in `compare_bills()` — don't assume the key exists |
| `conn`/jurisdiction_code/session not passed by some future caller | Low | None — by design | Default all three to `None`; blast-radius portion is skipped, per-voter diff still runs |

**Prerequisites:** None — no schema, migration, or dependency changes; `psycopg2` and the local
Postgres connection are already established in every call site that needs to pass them down.

**Tech debt created:** None net-new. The per-run memoization mentioned above is a small addition,
not deferred debt — recommend building it in from the start given OPEN-26 already demonstrated the
duplicate-query case is not hypothetical (266 bills, same signature).

**Residual finding (not blocking, flag for awareness):** `OCD_TO_CODE`/`JURISDICTIONS` both
explicitly exclude `va` (`quality_check.py:41-55`, comment: "va blocked"). Approach A sidesteps
this by having every call site pass its already-known jurisdiction short-code directly rather than
re-deriving it from `OCD_TO_CODE`, so the new code works correctly even for `va` if someone invokes
`quality_check.py --jurisdiction va ...` (bypassing the `JURISDICTIONS` default list, which the
`--jurisdiction` flag already supports doing today). No change to `va`'s blocked status is in scope
here or proposed.

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| OWASP A03:2021 Injection | Addressed | New SQL helper must use `%s` parameter placeholders for all values, matching every existing query in this file — no f-string interpolation of API-sourced data (voter names, options) into SQL text |
| Reuse before reinvent (`reuse-before-reinvent.md`) | Addressed | Reuses the existing `us`/`state:` LIKE-split pattern, the `Report` class, and already-in-scope call-site variables instead of a fourth jurisdiction-mapping branch or a new output mechanism |
| Defensive response parsing (`adapter-patterns.md`) | Addressed | Per-voter diff must use the same `.get(...) or []` guard already used for `local_votes`/`live_votes`, not assume `votes`/`counts` keys are always present |
| Testing — mock external dependencies (`testing.md`) | Addressed | Per-voter diff is pure (plain dicts, no mocking needed); blast-radius helper is a single-query function, mockable via a fake `conn.cursor()` — no live Postgres required for the test suite (confirmed: this workspace has no reachable local Postgres on `:5433`, so tests must not depend on one) |
| Multi-tenancy | N/A | Not a multi-tenant system — internal single-operator data-quality tooling |
| Idempotent/reversible changes (`artifacts.md`) | Addressed | Purely additive read-only reporting logic; no writes, no migrations, trivially revertible |
| Rate limiting / resource budget (`adapter-patterns.md` rate-limiting guidance, applied to this file's own 250 req/day live-API ceiling) | Addressed | Blast-radius helper deliberately queries local Postgres only, consuming zero live-API budget |

## Next Step

No new data model or cross-module design is needed — this is a same-file, same-schema extension.
Recommend skipping `/design-feature` and going straight to `/plan-ticket` (or directly to
`/implement-ticket`, since this assessment already specifies the concrete shape: extend
`compare_bills()`'s signature with `conn=None, jurisdiction_code=None, session=None`; add the pure
per-voter diff inline in the `if lc != rc:` branch; add
`count_shared_date_signature(conn, jurisdiction_code, session, date, voter_signature,
exclude_identifier)` as a new parameterized-SQL helper with a per-run memo cache; thread the three
new params through `main()`'s bill loop, `run_coverage_check()`, and `run_tier2_only_check()`; add
`test_quality_check.py` at repo root covering both the pure diff and the mocked-DB helper).
