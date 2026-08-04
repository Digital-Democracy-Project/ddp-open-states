# Architecture Assessment: OPEN-29 — VA vote events never get a real identifier; source URLs break to `.../None`

## Architectural Question
Given that the ticket's author has already traced the bug to two specific lines in
`VaBillScraper.add_votes()` and proposed an exact diff, the real architectural question is
narrower than "how do we fix this": **is the proposed one-line-per-bug diff the right shape of
fix, or does correctly satisfying this ticket's verification-heavy acceptance criteria (confirm
the hypothesis against raw API data, re-scrape, regression-check other bills) call for something
structurally different — e.g. extracting a helper, adding fixture-based unit tests, or touching
the shared importer/dedupe logic?**

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Scraper framework | `openstates-core` (`openstates.scrape.Scraper/Bill/VoteEvent`) | Nested git repo, own history |
| Target scraper | `openstates-scrapers/scrapers/va/bills.py` (`VaBillScraper`) | Plain `requests` calls against VA LIS `lis.virginia.gov` REST API, no ORM/DB access at scrape time |
| Import pipeline | `openstates-core/openstates/importers/vote_events.py` (`VoteEventImporter`) | Django ORM-backed; matches scraped JSON to DB rows via `get_object()` |
| Schema validation | `openstates-core/openstates/scrape/schemas/vote_event.py` (jsonschema) | `identifier` is `{"type": "string"}` — no format/uniqueness constraint |
| Test framework | plain `unittest`/pytest-style, e.g. `openstates-scrapers/tests/test_mi_bills.py`, `test_classify_motion.py` | No existing `test_va_bills.py` — VA scraper currently has zero unit test coverage |
| Verification tooling | `quality_check.py` (repo root) — local-vs-live api-v3 diff tool used in recent Tier 2 sweeps | Referenced in ticket as the downstream beneficiary, not part of this fix |
| Auth | `VA_API_KEY` env var, required for any live call to VA LIS API | **Not set in this workspace** (checked: `VA_API_KEY` is empty here) |

## Approaches Evaluated

### Approach A: Apply the ticket's proposed diff as-is (two one-line changes, inline)
**How it works:** Add `identifier=str(row["VoteID"])` to the `VoteEvent(...)` constructor call;
change `if "BatchNumber" in row: ... else: ...` to `row.get("BatchNumber") or row["VoteID"]`.
No new functions, no new files.

**Pros:**
- Matches the existing file's established pattern exactly — every prior VA fix in git history
  (`fa68c80`, `f3f49df`, `65363ef`) is a small, surgical, in-place diff with an explanatory comment
  where the "why" isn't obvious from the code (see the incremental-skip comment at
  `bills.py:139-149` for the house style).
- Minimal blast radius: touches only `add_votes()`, only affects VA, doesn't touch shared
  `openstates-core` importer/schema code.
- `identifier` becomes populated but the import-time *matching* behavior is unchanged: VA already
  sets `v.dedupe_key` a few lines below (`bills.py:383`), and `VoteEventImporter.get_object()`
  (`openstates-core/openstates/importers/vote_events.py:46-58`) checks `dedupe_key` **before**
  `identifier` and replaces the whole spec when present — so this fix is purely additive data,
  not a change to how existing VA votes get matched/deduped on import. Confirmed by reading the
  importer, not inferred.
- Directly satisfies AC #1 and #2 verbatim.

**Cons:**
- Adds zero test coverage — consistent with the file's current state (no VA tests exist at all)
  but doesn't reduce the regression risk called out in AC #5.
- The `BatchNumber` truthiness check is inline, not named — a future reader has to reconstruct
  "why `or` instead of `in`" from the diff/PR alone unless a comment is added.

### Approach B: Same fix, plus a small fixture-based regression test (`test_va_bills.py`)
**How it works:** Everything in Approach A, plus a new `openstates-scrapers/tests/test_va_bills.py`
that feeds `add_votes()` a hand-built `row` dict (or a captured `getvotebyidasync` fixture) covering
three cases: `BatchNumber` present and truthy, `BatchNumber` key present but `None`, `BatchNumber`
key absent entirely — asserting `identifier` and the resulting source URL in each case.

**Pros:**
- Turns AC #3 (confirm `BatchNumber` is present-but-`None`, not just absent) into a permanent,
  fast, offline regression test instead of a one-time manual check — the exact kind of case that's
  easy to silently regress later (e.g. someone "cleans up" the `or` back to `in` for readability).
- Follows `testing.md`'s TDD guidance and gives AC #5 ("no regression... spot-check a handful of
  other VA bills") a cheap, repeatable mechanical backstop that doesn't depend on VA_API_KEY or
  network access.
- Matches the repo's own existing test pattern (`test_mi_bills.py`) — reuse, not reinvention, per
  `reuse-before-reinvent.md`.

**Cons:**
- `add_votes()` is a generator that does a live `requests.get()` internally with no seam for
  injecting a fake HTTP response — as written, it can't be unit-tested without either (a) monkeypatching
  `requests.get`, or (b) refactoring the row-processing loop body into a separate, testable
  function. That refactor is a bit more change than the ticket asked for, though it's small and
  contained.
- Slightly more upfront work; ticket's own ACs frame verification as live-API-driven, not
  unit-test-driven — this is additive, not a substitute for AC #3/#4's live checks.

### Approach C: Restructure identifier/dedupe matching in `VoteEventImporter` to prefer `identifier`
**How it works:** Beyond the scraper fix, reorder `get_object()`'s spec-selection priority so a
populated `identifier` (not just `dedupe_key`) is preferred for matching across *all* jurisdictions,
directly enabling the ticket's mentioned downstream `quality_check.py` improvement.

**Pros:** Would generalize the "real identifier" benefit beyond VA immediately.

**Cons:**
- Touches shared `openstates-core` import logic used by every one of the ~50 jurisdiction
  scrapers found with `VoteEvent(` calls — none of which currently pass `identifier` (confirmed:
  grepped `VoteEvent(` construction across `mn/vote_events.py`, `ny/bills.py`, `ca/bills.py`,
  `tx/votes.py`, `oh/bills.py`, `il/bills.py`, `wi/bills.py` — all leave `identifier` at its
  default `""`). Changing matching priority here risks re-matching or duplicating vote events
  for every other state, for a ticket scoped explicitly to VA.
  Massively out of proportion to the ticket's stated scope, and the ticket itself calls the
  `quality_check.py` extension "a separate follow-up, not blocking this ticket."
- No corresponding AC covers this; would require its own architecture/design pass and regression
  testing across all jurisdictions.

## Tradeoff Matrix

| Dimension | A: Inline diff only | B: Diff + fixture test | C: Importer-wide reorder |
|---|---|---|---|
| Complexity | Low | Low-Med | High |
| Time to implement | Minutes | ~30-60 min | Multi-day, cross-jurisdiction |
| Maintainability | Good (matches house style) | Better (regression-proofed) | Risky (shared code, no tests today) |
| Scalability/generality | VA-only (matches scope) | VA-only (matches scope) | All jurisdictions (over-scoped) |
| Regression risk | Low, but AC #5 relies on manual spot-check only | Low, AC #5 partially mechanized | High — every jurisdiction's vote matching |
| Alignment with ticket scope | Exact | Exact + extra safety margin | Scope creep beyond stated ACs |
| Alignment with codebase (git history) | Exact match to `fa68c80`/`f3f49df`/`65363ef` pattern | Extends pattern (new but analogous test file) | No precedent for importer-wide behavior change from a single-jurisdiction ticket |

## Recommendation: Approach B (Approach A's diff, plus a small fixture-based unit test)

**Why this approach:**
- It's the same two-line fix the ticket's own root-cause analysis already nailed down (satisfies
  AC #1 and #2 exactly as specified) — there's no case here for inventing a different code shape;
  the ticket's diagnosis is correct and confirmed by direct reading of both `bills.py` and
  `VoteEvent.__init__`.
- Adding a small, offline unit test directly targets the two most falsifiable ACs in this ticket
  (#3: "confirm the hypothesis rather than infer it" and #5: "no regression") with something that
  doesn't depend on network access or `VA_API_KEY` availability — which matters concretely here,
  since **this workspace has no `VA_API_KEY` set**, and a live VA LIS re-scrape can only happen from
  wherever that key lives (see Risks below). A fixture test is the one piece of verification this
  ticket needs that's fully achievable regardless of that constraint.
- This is squarely within `testing.md`'s TDD guidance and doesn't conflict with any existing
  convention — VA has zero test coverage today, so adding one file doesn't "break" a pattern, it
  starts one, the same way `test_mi_bills.py` already did for another jurisdiction.

**Why not the alternatives:**
- **Not A alone** — it satisfies the letter of AC #1/#2 but leaves AC #5 ("no regression") resting
  entirely on manual spot-checks that won't survive the next unrelated edit to this function. Given
  this exact file has already needed three prior bug fixes (`fa68c80`, `f3f49df`, `65363ef`), a
  cheap regression test pays for itself.
- **Not C** — it would fix a problem nobody has reported yet (`quality_check.py`'s identifier-based
  matching is explicitly future/optional per the ticket) by editing shared code that every other
  jurisdiction's scraper depends on, with no test suite backing today's importer matching logic to
  catch a regression. The ticket description itself flags this as out of scope — respecting that
  boundary is the correct call, not a shortcut.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `VA_API_KEY` unavailable in this disposable workspace, blocking AC #3/#4's live-verification requirement | High (confirmed: unset here) | Blocks live re-scrape/API-dump verification steps specifically | Flag during implementation: either (a) the key exists in an environment this workspace can reach (ask, don't assume), or (b) fall back to a previously-captured raw response dump if one exists elsewhere, or (c) treat this as a genuine blocker per `codebot-question.md` and pause with `CODEBOT_QUESTION` rather than fabricating a "verified" result |
| `add_votes()` has no seam for injecting a fake HTTP response, so the fixture test must monkeypatch `requests.get` or refactor the loop body | Medium | Slightly larger diff than a pure 2-line fix | Prefer monkeypatching `requests.get` over refactoring — keeps the change contained to test code, no production code restructuring |
| `row.get("BatchNumber") or row["VoteID"]` silently falls back on *any* falsy `BatchNumber` (e.g. `0`, `""`), not just `None` | Low (`BatchNumber` is a URL path segment / vote batch code, never legitimately `0` or empty-but-meaningful based on the two known URL formats in the code comment) | Low | No action needed — ticket explicitly specifies truthiness semantics; note in PR description for the next reader |

**Prerequisites:**
- Confirm whether `VA_API_KEY` is reachable from this workspace or must be requested from the
  human operator before attempting AC #3/#4's live verification — check before assuming either way.
- None for the code change itself (AC #1/#2 need no new dependencies or schema changes).

**Tech debt created:**
- None. This is the first VA scraper test file, which pays down existing debt (zero test coverage
  on this jurisdiction) rather than adding to it.

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| OWASP Top 10 | N/A | No user input, auth, or web-facing surface touched — this is an internal batch scraper reading a third-party government API |
| SOLID (single responsibility) | Addressed | Fix stays within `add_votes()`'s existing responsibility (vote construction); doesn't introduce a new abstraction the file doesn't already have |
| DRY / no premature abstraction | Addressed | Approach A/B deliberately avoid extracting a helper function the ticket didn't ask for and no other jurisdiction needs yet |
| Defensive parsing of third-party API responses (`adapter-patterns.md`) | Addressed | `row.get("BatchNumber") or row["VoteID"]` is exactly the "check truthiness, not presence" defensive-parsing pattern this rule calls for |
| Test coverage (`testing.md`) | Addressed by recommendation | Adds fixture coverage where none existed; Approach A alone would leave this at N/A |
| Idempotent/reversible changes (`artifacts.md`) | Addressed | Pure code fix, no migrations, trivially revertible via git |
| Multi-tenancy | N/A | Not a multi-tenant SaaS concern — this is a per-jurisdiction civic data scraper |

## Next Step
This ticket is small and well-scoped enough to skip `/design-feature` (no data model or schema
changes). Recommend going straight to `/plan-ticket` to sequence: (1) apply the two-line fix,
(2) add the fixture test, (3) resolve the `VA_API_KEY`/live-verification prerequisite, (4) re-scrape
and spot-check per AC #4/#5.
