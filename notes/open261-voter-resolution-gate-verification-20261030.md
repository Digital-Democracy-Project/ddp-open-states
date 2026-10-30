# OPEN-261 — unresolved-voter-attribution gate: what shipped and what's unverified against real data

Builds the gate the plan's 2026-08-27 addendum named: for the sampled sessions, what fraction of
`opencivicdata_personvote` rows carry a `voter_name` but no resolved `voter_id`, and the top
offending names -- wired into `verify-jurisdiction` and `quality_check.py`.

## Gate-letter correction: J, not I

The ticket's AC text ("gates A-H become A-I") is stale. **OPEN-397 already shipped gate I**
(`run_gate_i` / `GATE_ORDER["I"]`, `verify-jurisdiction`) for vote `dedupe_key` collisions -- a
different check, and already the uniqueness assertion this ticket's own "related, worth carrying
into the same gate design" aside (OPEN-179's duplicate-roll-call parsing) asked for. This ships as
**gate J** instead. See `OPEN-261-architecture-assessment-20261030.md` (this branch) for the full
reasoning.

## What was built

- `verify-jurisdiction`: `run_gate_j(conn, st, session, active_sessions)` -- advisory
  (non-blocking), samples the probed session plus up to `MAX_EXTRA_SESSIONS` other active
  sessions (same policy as gate I), queries already-imported `opencivicdata_personvote` rows via
  `opencivicdata_personvote.vote_event_id -> opencivicdata_voteevent.id -> ...bill_id -> ...bill
  -> ...legislativesession -> ...jurisdiction`. PASS when nothing is unresolved, WARN with
  counts/fraction/top-10 names otherwise, WARN (inconclusive) when the sample has zero
  `personvote` rows, SKIP when no database is configured (same as gate H). `GATE_ORDER["J"] = 9`.
- `quality_check.py`: `check_voter_resolution(report, conn, jurisdiction, session)` -- required,
  not advisory. FAILs on **any** unresolved row (no hard-coded 95% in code; that threshold is the
  human sign-off convention applied when reading the output, same as Tier 1 coverage's
  FAIL-on-any-real-gap). Wired into all three Tier-2-bearing entry points so it cannot be skipped
  regardless of path: `run_coverage_check` (live API), `run_govbot_coverage_check` (govbot-backed),
  `run_tier2_only_check` (standalone `--tier2`).
- `RUNBOOK.md` and `verify-jurisdiction`'s own docstring updated for gate J's existence, its
  Fargate/`--from-dir` behavior, and the required Tier 2 line's sign-off convention.
- Unit tests in `test_verify_jurisdiction.py` and `test_quality_check.py` cover: clean pass,
  unresolved rows with correct fraction/percentage/top-name formatting, zero-rows-in-sample,
  session-sampling cap, the `us`-exact-match-vs-state-`LIKE` scoping split, SKIP with no database,
  and that all three `quality_check.py` entry points actually call the check.

## AC #4 — real FL/MI data verification: blocked in this environment, substituted with a pinned synthetic fixture

This ticket's AC #4 asks to confirm the gate flags the known-bad concentration in an
already-onboarded state's real data (OPEN-178: FL, 3,369/69,445 rows across 43 names, 94% in
five; OPEN-174: MI, 1,427 rows across 154 names). This CodeBot workspace clone has **no reachable
OpenStates database**: `DATABASE_URL` in this environment points to an unrelated `cams` dev
database (`postgresql+asyncpg://cams:cams_dev@localhost:5432/cams`, not this project's schema),
and `localhost:5432` refused the connection outright. No replica or dev DB with real FL/MI scrape
history was reachable to run `verify-jurisdiction fl` or `quality_check.py --tier2 fl <session>`
against.

In place of the real run, `test_check_voter_resolution_flags_the_known_fl_and_mi_concentrations`
(`test_quality_check.py`) pins `check_voter_resolution`'s FAIL/percentage/top-names output against
the exact, already-quantified OPEN-178 and OPEN-174 numbers via a synthetic fixture, so the
calculation itself is proven correct against the real-world shape this gate exists to catch --
but this is **not** a substitute for AC #4's own real-data requirement.

**Follow-up needed:** run `verify-jurisdiction fl --session <session>` (or `mi`) and
`quality_check.py --tier2 fl <session>` with `DATABASE_URL` pointed at a database that actually
holds FL or MI's real scrape history (e.g. the human's `ddp-open-states-dev` checkout, which has
its own Postgres DB per `CLAUDE.md`) to close out AC #4 for real, and record the result here or in
a follow-up comment on OPEN-261.

## Out of scope, not forgotten

- `billsponsorship` resolution (OPEN-174/NC's note covered both; this ticket's text is
  `personvote`-only) -- a natural follow-up ticket, same shape.
- `PLAN-push-button-onboarding.md`'s §4.4 table and the "A-H become A-I" ticket text live in the
  separate `ddp-infra` repo and cannot be edited from this repo's PR -- needs its own follow-up
  there to correct "A-H become A-I" to "A-I become A-J".
