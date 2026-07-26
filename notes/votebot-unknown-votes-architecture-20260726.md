# Architecture Assessment: OPEN-2 — VoteBot relays a bulk of legislator votes as "Unknown"

> **Ticket source note:** `atlassian` and `github` MCP auth are not available in this session
> (no `project.toml` in this repo either), so this assessment is grounded entirely in the ticket
> title given on the command line plus direct codebase/data-flow investigation — not a fetched
> Jira/GitHub description. If OPEN-2 has acceptance criteria beyond "figure out why," reconcile
> them against this doc before planning.

## Architectural Question

Where in the FL/VA/IA/etc. → OpenStates → VoteBot pipeline do individual legislator votes lose
their identity, and what's the right layer to fix it: the scrapers, the shared importer, a
one-time data backfill, or VoteBot itself?

## Tech Stack Context

| Layer | Technology | Notes |
|---|---|---|
| Scrapers | `openstates-scrapers` (Python, `pupa`/`spatula`-style scrape classes) | Per-jurisdiction; each emits raw `voter` strings via `VoteEvent.vote()` |
| Import/ETL | `openstates-core` (Django ORM, PostgreSQL) | `VoteEventImporter` + shared `BaseImporter.resolve_person()` resolve scraped names to `Person` rows |
| Data store | PostgreSQL, `opencivicdata_personvote` (`voter_name` text + nullable `voter` FK) | This repo owns the DB; `people` YAML repo owns canonical legislator identity |
| Downstream consumer | `votebot` (separate repo/service, EC2, not checked out here) | Reads vote data via the OpenStates v3 API; renders "Unknown" for a legislator it can't identify |
| Adjacent consumers | `ddp-broker-py`, `ddp-sync` | Same API, but look up sessions/data differently — per `PLAN-open-states.md` §8.3, VoteBot's resolution issues are **VoteBot/pipeline-specific**, not shared by the other two |

## What I found tracing the pipeline

1. **Scrapers emit free-text voter names, not IDs**, and the format varies by state:
   - FL (`openstates-scrapers/scrapers/fl/bills.py:562-565`) parses **surname-only** strings off
     roll-call PDFs: `r"\s*(Y|N|EX|AV)\s+(.*?)-\d{1,3}\s*"` → `vote.vote(vtype, member)` where
     `member` is just e.g. `"Smith"`.
   - VA (`openstates-scrapers/scrapers/va/bills.py:394-397`) and IA
     (`openstates-scrapers/scrapers/ia/votes.py:220`) pass a fuller `MemberDisplayName`/`voter`
     string from structured API/table data — but there's no guarantee its "Last, First M." or
     "First M. Last" shape matches the canonical `name` field in the `people` YAML repo.
   - `VoteEvent.vote()` (`openstates-core/openstates/scrape/vote_event.py:77-88`) stores whatever
     string it's given as both `voter_name` and a name-based pseudo-ID — there is no per-scraper
     normalization step before this.

2. **Resolution happens once, centrally, and is strict-match by design.**
   `BaseImporter.resolve_person()` (`openstates-core/openstates/importers/base.py:567-651`) is the
   single chokepoint used by vote, bill-sponsor, and event-participant resolution alike. For a
   name-only pseudo-ID it tries, in one query:
   `Q(name__iexact=name) | Q(other_names__name__iexact=name) | Q(family_name__iexact=name)`,
   scoped to the jurisdiction, chamber (`org_classification`), and a membership date-range filter.
   - **No match** → `errmsg = "no people returned for spec"`, logged via `self.error(...)`
     (plain Python logging — `base.py:137-141`), and `voter_id` is set to `None`.
   - **Multiple matches** with more than one *currently serving* candidate (e.g. two same-surname
     legislators in the same chamber) → `"multiple people returned for spec"`, same `None` outcome.
   - Either way, `PersonVote.voter` is a nullable FK (`SET_NULL` on delete —
     `openstates-core/openstates/data/models/vote.py:92-98`), so the row is still imported with
     `voter_name` intact but no linked `Person`. This is almost certainly what VoteBot sees as
     "Unknown": it has a name string but no resolved legislator record to enrich/attribute.

3. **No metric exists for how often this happens.** The only signal is a log line per failure
   during a multi-hour scrape run (`run-scrape.sh`) — there's no audit script, dashboard, or
   `quality_check.py` check for voter-resolution rate today (`quality_check.py` currently checks
   vote *counts* matching upstream, not resolution — see its `local_votes`/`live_votes` comparison
   around line 213-237). Nobody currently knows the real "how bulk is bulk" number without
   grepping historical scrape logs.

4. **People data refreshes weekly, scrapes run daily.** `run-people-refresh.sh` pulls the `people`
   YAML repo and reloads the DB only on Sundays; FL/WA/US scrapes run daily during session
   (`PLAN-open-states.md` §9.1). A newly-seated legislator, a name change, or a missing
   `other_names` alias can lag up to a week behind the votes referencing them — a secondary,
   time-boxed contributor on top of the format-mismatch problem above.

5. **This repo already has an established remediation pattern for exactly this shape of problem.**
   `audit-motion-texts.py` (read-only, per-jurisdiction Markdown report) paired with
   `backfill-motion-classification.py` (`--dry-run`-capable, idempotent, re-applies corrected logic
   to existing DB rows without re-scraping) was used to fix a prior data-quality gap
   (motion classification). The same shape — audit script, then backfill script — fits this
   problem well and keeps consistency with how the team has solved this class of issue before.

## Approaches Evaluated

### Approach A: Improve `resolve_person()` matching (fix at the chokepoint)
**How it works:** Extend the shared resolver in `openstates-core` — normalize case/punctuation/
whitespace more aggressively, strip honorifics ("Rep.", "Sen.", "Del."), detect and handle
"Last, First" ordering, and add a bounded fuzzy-match fallback (e.g. `rapidfuzz`) that only fires
when it collapses to **exactly one** current-member candidate within the already-scoped
jurisdiction+chamber+date-range query set (never guesses between ambiguous same-surname
candidates — that would trade a visible "Unknown" for a silently wrong attribution, which is worse).

**Pros:** Fixes the problem once, for every jurisdiction and every downstream consumer
(VoteBot, and any future consumer), not just votes — sponsor and event-participant resolution use
the same function and share the same gap. Matches the DRY/single-source-of-truth shape of the
existing pipeline.
**Cons:** Touches shared, well-tested importer code used by every import path; fuzzy matching has
to be conservative to avoid mis-attribution; doesn't help until the next scrape+import cycle for
already-imported rows.
**Standards alignment:** Single Responsibility / separation of concerns (name resolution is the
pipeline's job, not each consumer's); avoids duplicating fallback logic in three separate services.

### Approach B: Audit + backfill scripts (fix existing data, reuse established pattern)
**How it works:** Add `audit-unresolved-votes.py` (read-only, connects directly to Postgres like
`audit-motion-texts.py` does) reporting per-jurisdiction/session counts and % of
`opencivicdata_personvote` rows with `voter_id IS NULL`, plus the distinct unmatched `voter_name`
values so it's obvious whether each is a true "no match" or an ambiguous same-surname case. Pair
it with `backfill-voter-resolution.py` (`--dry-run` flag, idempotent, modeled directly on
`backfill-motion-classification.py`) that re-runs the (improved, per Approach A) resolver against
existing rows to backfill `voter_id` without a full re-scrape. For names the resolver still can't
safely resolve, maintain a small manually-curated alias map (jurisdiction + session + raw name →
person OCD ID) as an explicit, reviewable escape hatch — same spirit as the `people` repo's own
`other-names.yml` convention.

**Pros:** Directly matches a pattern the team has already used successfully for this exact class of
problem; low blast radius (standalone scripts, not shared importer code); gives immediate,
quantified visibility into scope before any code changes ship; retroactively fixes already-scraped
history, which Approach A alone does not.
**Cons:** Doesn't prevent new unresolved votes going forward on its own — needs Approach A (or at
least improved matching logic reused inside the backfill script) alongside it to stop the bleeding.
**Standards alignment:** Matches the "idempotent, re-runnable, dry-run-first" migration-safety
standard already used for the motion-classification backfill; observability — turns a silent log
line into a measured, reportable data-quality metric.

### Approach C: Make VoteBot fall back to `voter_name` when unresolved
**How it works:** Change VoteBot's rendering so that when a vote has no resolved person, it
displays the raw `voter_name` string instead of "Unknown."

**Pros:** Cheapest, fastest, immediately reduces user-visible "Unknown" counts; VoteBot already
has the raw name available via the API.
**Cons:** Out of scope for this repo (VoteBot is a separate, not-checked-out codebase) — would need
its own ticket/team. More importantly, it **masks** the underlying data-quality gap rather than
fixing it: sponsor and event-participant resolution have the same silent-`None` failure mode, and
any future consumer (ddp-broker-py, ddp-sync, analytics) would rediscover the same gap
independently and likely re-implement its own inconsistent fallback. Doesn't address the
"which legislator actually cast this vote" question VoteBot presumably needs answered for
downstream features (constituent lookups, voting-record pages, etc.) — a raw string isn't a
substitute for a linked Person record with party/district/chamber.
**Standards alignment:** Fails the single-source-of-truth principle — pushes a data problem into
presentation logic in one specific consumer.

## Tradeoff Matrix

| Dimension | A: Fix resolver | B: Audit + backfill | C: VoteBot fallback |
|---|---|---|---|
| Complexity | Medium (shared code, needs care) | Low–Medium (standalone scripts) | Low |
| Time to implement | Medium | Low (proven pattern to copy) | Low (but different repo/team) |
| Fixes existing (already-scraped) data | No, on its own | Yes | N/A (display-only) |
| Fixes future scrapes | Yes | No, on its own | N/A |
| Maintainability | High (one chokepoint) | High (matches existing convention) | Low (masks root cause) |
| Risk of *wrong* (not just missing) attribution | Low if fuzzy match is conservative | Same, inherits Approach A's logic | None (no attribution attempted) |
| Observability improvement | None by itself | High (new audit report) | None |
| Alignment with codebase conventions | High | Very high (direct precedent) | Low (wrong repo) |

## Recommendation: A + B together, B first

Ship the **audit script first** (Approach B's audit half) to get a real, quantified picture of
scope — jurisdiction-by-jurisdiction unresolved-vote counts and which specific names are failing —
before writing any resolver changes. That data should drive how conservative the fuzzy-matching
threshold in Approach A needs to be, and will surface whether this is dominated by FL's
surname-only ambiguity, VA/IA's name-order mismatches, the weekly people-refresh lag, or something
else entirely. Then:

1. Land the audit script, run it, and read the results.
2. Improve `resolve_person()` (Approach A) based on what the audit shows, biased hard toward
   "leave it unresolved" over "guess wrong" whenever more than one current-member candidate
   remains after normalization.
3. Land the backfill script (Approach B's other half) reusing the improved resolver logic, to fix
   already-imported history without a full re-scrape.
4. Leave Approach C (VoteBot's own fallback rendering) as a separate, VoteBot-team decision —
   worth suggesting to them as a defense-in-depth UX improvement, but not a substitute for fixing
   resolution here.

**Why this ordering and not A-first:** Every existing precedent in this repo for a data-quality
fix of this shape (motion classification) measured first, then fixed, then backfilled. Guessing at
a fuzzy-match strategy before knowing whether the problem is "same surname, multiple legislators"
(where fuzzy matching can't help and could actively hurt) versus "name-order mismatch" (where it
trivially helps) risks building the wrong fix.

**Why not C as a primary fix:** it's not actually available to build from this repo, and even as a
VoteBot-side change it would leave the same root-cause gap for every other consumer of person
resolution (sponsors, event participants) to rediscover independently.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Fuzzy matching resolves a vote to the *wrong* legislator (same surname) | Medium if implemented naively | High (data integrity) | Only fuzzy-match when normalization collapses candidates to exactly one; otherwise leave `None` and log distinctly from "no match at all" |
| Backfill script mutates already-correct rows | Low | Medium | `--dry-run` first, matching existing convention; only touch rows where `voter_id IS NULL` |
| Audit script query is expensive against the live scrape DB | Low | Low | Read-only, run off-peak, matches existing `audit-motion-texts.py` footprint |
| People-repo lag (weekly refresh) still causes transient Unknowns right after redistricting/turnover | Medium | Low (self-resolves within a week) | Document as a known, time-boxed limitation; not worth solving with more frequent refreshes unless the audit shows it's a major contributor |

**Prerequisites:** None blocking — the audit script can be written and run today against the
existing DB schema with no upstream changes.

**Tech debt created:** A manually-curated alias map (for names the resolver still can't safely
resolve) is a small, explicit, reviewable form of debt — analogous to the `people` repo's own
`other-names.yml` — not hidden debt. No other debt anticipated.

## Standards Checklist

| Standard | Status | Notes |
|---|---|---|
| Single Responsibility / separation of concerns | Addressed | Resolution logic centralized in `resolve_person()`, not duplicated per consumer |
| DRY (without premature abstraction) | Addressed | Reuses the existing shared resolver rather than building VoteBot-specific or per-scraper matching |
| Idempotent, safe backfills | Addressed | Backfill script to be modeled on `backfill-motion-classification.py`'s `--dry-run`, re-runnable design |
| Observability | Addressed | New audit script turns a silent log line into a measured, reportable metric |
| Data integrity over convenience | Addressed | Fuzzy-match design explicitly biased against guessing between ambiguous candidates |
| Multi-jurisdiction scoping | Addressed | All queries/scripts scoped per jurisdiction, matching `JURISDICTION_MAP` precedent |
| OWASP Top 10 | N/A | No user input, auth, or network-facing surface in this pipeline segment |

## Next Step

Run `/plan-ticket` to break the audit script into implementable tasks — it has no design
dependencies (no new tables, no cross-service contract changes), so `/design-feature` isn't needed
first. Once the audit results are in, a short follow-up planning pass can size the resolver
improvements and backfill script based on real numbers.
