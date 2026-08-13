# Architecture Assessment: OPEN-58 — Verify and configure `eligible_for_scorecard` rules for Florida

## Architectural Question

This is the third occurrence of the same investigation shape: OPEN-60 ran it for US Congress,
OPEN-64 ran a breadth check of it for Virginia, and OPEN-58 asks for it again for Florida. The
methodology is no longer novel — it's an established convention with two real precedents in this
repo (`notes/open-60-us-congress-eligibility-verification-20260812.md`,
`notes/open-64-virginia-eligibility-breadth-verification-20260812.md`). So the real architectural
questions aren't "how do we investigate this" in the abstract; they're narrower:

1. **Does the OPEN-60/OPEN-64 methodology transfer directly to Florida**, or does FL's action data
   have a shape (like Congress's letter-free tallies, or VA's same-day-multiple-votes case) that
   needs a different investigative approach before it can even be trusted?
2. **Which tool reaches the real data** — this workspace has both a direct-Postgres pattern (used
   by every prior note) and an MCP `postgres` tool available now that wasn't necessarily checked
   before. Picking wrong doesn't fail loudly; it produces a confident, wrong answer.
3. **What is this session's actual deliverable**, given the ticket bundles two phases in two repos
   and this workspace only has one of them checked out?

## Tech Stack Context

| Layer | Technology | Version | Notes |
|---|---|---|---|
| DB access pattern | Direct `psycopg2` script | 2.9.x | Convention set by `bill-actions-persisted-verification-20260811.md`, reused verbatim by OPEN-60 and OPEN-64 |
| Target DB | Postgres, dedicated OpenStates replica | — | `postgresql://openstates:openstates_dev@localhost:5433/openstates` (`activate.sh:8`, `DATABASE_URL`) |
| Schema | `openstates-core` Django models | — | `opencivicdata_billaction` → `opencivicdata_bill` → `opencivicdata_legislativesession` → `opencivicdata_jurisdiction` |
| Existing audit tooling in this repo | `quality_check.py` (`Report` class, `OCD_TO_CODE`), `audit-motion-texts.py` | — | Precedent for read-only, one-off/repeatable audit scripts against this same DB |
| Phase 2 target (not in this workspace) | `ddp-broker-py`, Django migrations, `fetch/tests/` | PR #295, `fix/BROKER-47-agent` | Confirmed absent from this checkout (see Environmental Constraint below) |

## Environmental constraint (blocks phases 5–8 in this workspace, not phase 1)

Checked for `ddp-broker-py` anywhere on this machine — it isn't part of this CodeBot workspace
clone (only `ddp-open-states`, plus its nested `openstates-core`/`openstates-scrapers`/`api-v3`
checkouts, are present). The ticket's own description already anticipates this: *"CodeBot only has
OpenStates replica access from ddp-open-states"*. Per `project-config.md`'s `repo.path` discipline,
this session's only legitimate output is Phase 1: the findings notes doc. Steps 5–8 (the
`JurisdictionEligibilityConfig`/`JurisdictionEligibilityRule` migration, the regression test,
`verified=True`, and the `validate_scorecards`/`reconcile_scorecards` before/after run) require a
`ddp-broker-py` checkout and genuinely cannot be executed here — not a gap to route around, a
boundary to report. This assessment (and the resulting `/plan-ticket`) should scope to Phase 1
only; Phase 2 is a separate ticket-lifecycle pass in a `ddp-broker-py` session, feeding from this
session's notes doc the same way OPEN-60 and OPEN-64's notes already fed real, merged
`ddp-broker-py` migrations (`0052` for VA is confirmed to exist and be referenced from OPEN-64's
own note).

## Approaches Evaluated — DB access method

### Approach A: Direct `psycopg2` script against the dedicated replica (the established convention)
**How it works:** A short standalone script (or REPL session) connects with `DATABASE_URL` from
`activate.sh`, runs the classification-breakdown query, pulls one full bill's action list, tests
the tally regex in Python against every real `passage`-tagged row, and searches action text for
concurrence-shaped language the way OPEN-60 did for "concur"/"cloture".
**Pros:** Exactly what OPEN-60 and OPEN-64 did — same connection string, same schema path, same
verification already proven correct against the public v3 API in the original persistence check.
Zero new tooling risk. Output maps directly onto the required notes-doc format.
**Cons:** One-off script, not committed as reusable infra (same tradeoff prior tickets accepted).
**Standards alignment:** `reuse-before-reinvent.md` (reuse a proven pattern rather than inventing
a new one); read-only, no mutation of production data.

### Approach B: Use the `postgres` MCP tool
**How it works:** Run the classification/regex/amendment-passage queries through the connected
`postgres` MCP tool instead of a standalone script.
**Pros:** No script-writing overhead, queries run inline.
**Cons — confirmed, not hypothetical:** ran `SELECT current_database()` through this tool live and
it returned `cams`, not `openstates`. This is exactly the trap `bill-actions-persisted-verification-
20260811.md` already documented ("not the `cams` DB the `postgres` MCP tool defaults to") and that
OPEN-60/OPEN-64 both explicitly avoided. The tool's schema takes only `sql` — no way to point it at
a different connection string per call — so it cannot reach `opencivicdata_billaction` on the
dedicated :5433 replica at all in this workspace's current MCP configuration. Using it here would
silently produce either empty results or, worse, results against unrelated `cams` tables that
happen to share a name.
**Standards alignment:** Fails on its own — this isn't a tradeoff, it's a wrong-database risk that
was pre-empted by prior notes and reconfirmed live.

### Approach C: Build a reusable jurisdiction-eligibility audit script (generalize past this ticket)
**How it works:** Extract the OPEN-60/64 query shapes into a small reusable script (in the spirit
of `audit-motion-texts.py`), parameterized by jurisdiction name, so the remaining untouched
jurisdictions (`wa`, `mi`, `ut`, `al`, `ma`, `az` — the other 6 in `quality_check.py`'s
`OCD_TO_CODE`) don't each require hand-rolling the same queries a fourth, fifth, sixth time.
**Pros:** This is now a 3-for-3 recurring pattern; a real primitive would pay for itself if BROKER-
47-style verification continues rolling out jurisdiction by jurisdiction, and `reuse-before-
reinvent.md` explicitly favors this once a pattern repeats rather than being copy-pasted again.
**Cons:** Not asked for by this ticket, whose explicit scope is Florida only ("Out of scope:
changing the global defaults or any other jurisdiction's config"). Building shared infra now is
unrequested scope expansion for a ticket whose actual deliverable is a notes doc + one jurisdiction's
config, and risks over-engineering a tool before its second/third caller's exact needs are known
(only 3 jurisdictions verified so far, all via ad hoc scripts that were each a little different in
what they sampled).

## Tradeoff Matrix

| Dimension | A: Direct psycopg2 (established) | B: `postgres` MCP tool | C: New reusable audit script |
|---|---|---|---|
| Complexity | Low | Low | Medium |
| Time to implement | Low | Low (but wrong) | Medium-High |
| Correctness risk | None — proven 2x already | High — confirmed wrong DB | None, but adds untested new code path |
| Maintainability | Fine for one-off research | N/A | Good, if the pattern really recurs |
| Alignment with codebase convention | Exact match | Breaks convention | Extends convention prematurely |
| Fit with ticket's stated scope | Exact fit | N/A | Scope creep |

## Recommendation: Approach A — direct `psycopg2` script against the dedicated replica, same shape as OPEN-60/OPEN-64

**Why this approach:** It's the proven, twice-executed convention in this exact repo, connecting
to the exact same schema, and its output format (classification table, one full real bill's action
list, a regex-match count with a categorized sample of non-matches, a targeted search for how
cross-chamber/concurrence votes are actually tagged if `amendment-passage` is confirmed empty) maps
directly onto every acceptance criterion in this ticket. Following `reuse-before-reinvent.md`, there
is no reason to invent a new method when one is already sitting in `notes/` twice over, verified
against the live public API in the original persistence check.

**Why not the alternatives:** Approach B is not a stylistic preference away from correct — it was
tested live in this session and returned the wrong database (`cams`, not the `openstates` replica),
which would make every downstream finding fabricated against the wrong table set. Approach C solves
a real future problem but isn't this ticket's problem; building shared infra before Florida is even
verified risks guessing wrong about what the 4th–7th jurisdiction's script actually needs, and the
ticket's own "out of scope" line is explicit that this pass should stay FL-only.

**Risks and mitigations:**
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| FL's real regex-match rate looks low and gets misread as a bug | Medium | Medium | OPEN-60 and OPEN-64 both already show low match rates are usually explained by legitimate voice-vote/ceremonial noise — categorize a sample of non-matches before concluding anything, exactly as both precedents did |
| `amendment-passage` really is zero for FL, and the wrong substitute tag gets picked without evidence | Medium | High (feeds directly into phase 2's `requires_pattern` gate) | Mirror OPEN-60's text-search step (`concur`, cross-chamber language) across *all* FL classifications, not just a guessed one, before recommending a tag |
| Investigation quietly drifts into also touching `ddp-broker-py` config/tests | Low | High (this workspace can't safely do that work or open that PR) | Explicitly stop at the notes doc; hand off per the Environmental Constraint section above |
| Findings doc doesn't cite real bill IDs / real text, making phase 2 unable to write a real regression test | Low | High (blocks the AC that mandates real bill-specific tests) | Follow OPEN-60's format exactly — one full real bill's action list with real IDs, real dates, real classifications |

**Prerequisites:** None — `psycopg2`, `activate.sh`'s `DATABASE_URL`, and the notes/ directory
convention are all already present and working in this workspace.

**Tech debt created:** None net-new. Optionally worth flagging Approach C (a shared jurisdiction-
eligibility audit script) as a candidate for a future ticket once a 4th jurisdiction needs this same
treatment — not created now, just named so it isn't rediscovered from scratch next time.

## Standards Checklist

| Standard | Status | Notes |
|---|---|---|
| OWASP Top 10 | N/A | Read-only research against an internal replica, no user input/auth surface |
| Reuse before reinvent (`reuse-before-reinvent.md`) | Addressed | Core of the recommendation — reuse OPEN-60/64's exact method rather than a new tool or new script |
| `repo.path` / workspace scope discipline (`project-config.md`) | Addressed | Phase 2 explicitly reported as out of reach in this workspace rather than attempted or silently skipped |
| Read-only/reversible actions (`artifacts.md`) | Addressed | Entire phase 1 is read-only queries against a replica; nothing to roll back |
| Data validation at the boundary (`database.md`) | Addressed | Regex and tag findings will be validated against real rows before being handed to phase 2, not assumed from VA's defaults |
| Tech debt governance (`tech-debt.md`) | Addressed | No debt introduced; Approach C named as a possible future ticket, not silently deferred |
| Multi-tenancy | N/A | Not a multi-tenant SaaS concern |

## Next Step

No data model design needed here — this is a research task with an already-proven method, not a
schema decision. Recommend going straight to executing Phase 1 (or `/plan-ticket` first if you want
a formal task breakdown): connect via `psycopg2` to the dedicated replica, run the classification
breakdown for FL, pull one full real bill's action list, test the tally regex against real
`passage`-tagged rows with a categorized non-match sample, and determine FL's actual
`amendment-passage` count plus (if zero) what tag real cross-chamber concurrence votes use instead
— then write `notes/fl-open-58-eligibility-verification-20260812.md` in the same format as
`notes/open-60-us-congress-eligibility-verification-20260812.md`. Phase 2 (the `ddp-broker-py`
migration, test, and `validate_scorecards`/`reconcile_scorecards` run) is out of scope for this
workspace and should be picked up in a session with that repo checked out, using this notes doc as
its handoff artifact.
