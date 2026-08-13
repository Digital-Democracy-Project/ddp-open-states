# Architecture Assessment: OPEN-59 — Verify and configure `eligible_for_scorecard` rules for Michigan

## Architectural Question

This ticket's phase 1 (the only phase this repo can do) is a verification task, not a build task:
what is the right, evidence-grade method to confirm — or refute — that the Virginia-shaped
`eligible_for_scorecard` tally regex and `DEFINITE_YES`/`DEFINITE_NO` tag rules (`BROKER-47`) hold
for Michigan? This is the sixth jurisdiction this exact question has been asked for this sprint
(US Congress/OPEN-60, Arizona/OPEN-57, Florida/OPEN-58, Utah/OPEN-61, Washington/OPEN-62, Virginia
breadth/OPEN-64) — the real architectural decision is **methodology**, not code, and the method
itself is now well-established local precedent, not something to reinvent.

**The ticket's own premise needs a caveat before it can be trusted, based on direct local
precedent:** OPEN-59 asserts a specific prior finding — "Michigan's `amendment-passage`-tagged
actions were already found (2026-08-11) to read literally 'AMENDMENT(S) ADOPTED' with NO vote
tally in the text at all, across all 15 instances sampled." **No notes doc dated 2026-08-11
documenting this exists anywhere in this repo's `notes/` directory or git history**, checked
directly (`grep -rn "AMENDMENT(S) ADOPTED"`, `git log --all --oneline | grep -i "michigan\|OPEN-59"`
— both empty). This is the *exact* situation `OPEN-57-architecture-assessment-20260812.md` already
hit for Arizona's ticket, which asserted an equally unsourced "already found (2026-08-11)" claim
about AZ's `amendment-passage` shape. OPEN-57's resolution was correct and is the template here:
don't refuse to proceed, and don't blindly cite a document that doesn't exist — **independently
re-verify the claim against live data**, and only carry it forward once confirmed. Live queries run
below do exactly that, and the claim checks out — but two things beyond the ticket's own citation
also surfaced live that materially change what phase 2 needs to build (see Diagnosis).

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Data source | Django ORM models (`openstates-core/openstates/data/models/bill.py`) over Postgres | `BillAction` → `opencivicdata_billaction` (482,212 rows prod-wide) |
| DB access | Direct `psycopg2` against `DATABASE_URL` (`activate.sh:8`) | `postgresql://openstates:openstates_dev@localhost:5433/openstates` — the real replica, port `5433` |
| Known footgun #1 | `postgres` MCP tool | Defaults to the `cams` DB, a different service on port 5432 — wrong DB entirely unless explicitly pointed at the replica connection string above; flagged in every prior sibling doc |
| Known footgun #2, reconfirmed live this session | `source activate.sh \| tail -N` (or any pipe) | Piping a `source` command spawns a subshell for the left side of the pipe — `export DATABASE_URL=...` happens in that subshell and is discarded when the pipe closes, silently leaving the *calling* shell's pre-existing `DATABASE_URL` in place (in this session, that was a stray `cams:5432` asyncpg URL from an unrelated ambient env). Confirmed by reproducing it directly this session. Must `source activate.sh` as its own, unpiped statement. |
| Known footgun #3 (from OPEN-58/FL) | Loose jurisdiction filters (`name ILIKE`) | Checked and **does not apply to Michigan** — `SELECT id, name, classification FROM opencivicdata_jurisdiction WHERE name ILIKE '%michigan%'` returns exactly one row, `ocd-jurisdiction/country:us/state:mi/government`, no municipal collision |
| Handoff artifact format | Markdown notes doc, repo `notes/` dir | Established, repeated format: Context → Method → Result (numbered per AC) → Conclusion w/ recommended config → References |
| Target repo for phase 2 | `ddp-broker-py`, `common/models/JurisdictionEligibilityConfig.py` / `JurisdictionEligibilityRule.py`, migration + tests, branch `fix/BROKER-47-agent`, PR #295 | Not reachable from this checkout. Other `ddp-broker-py` directories exist elsewhere on this machine (other CodeBot sessions' disposable workspaces, and a human dev checkout under `~/Developer/repos/`) — per this repo's `repo.path` discipline and the CLAUDE.md dev/prod-checkout rule, none of those are in scope for this ticket; only this workspace's own clone is |
| Prior art (this repo) | `notes/open-60-us-congress-eligibility-verification-20260812.md`, `notes/open-64-virginia-eligibility-breadth-verification-20260812.md`, `notes/ut-open-61-eligibility-verification-20260812.md`, `notes/open-62-washington-eligibility-verification-20260812.md`, `notes/open-57-arizona-eligibility-verification-20260812.md`, `notes/fl-open-58-eligibility-verification-20260812.md` | Six prior tickets in the identical family; between them they've found every outcome shape this ticket could land in (see Diagnosis) |
| Data-integrity note, unrelated to this ticket's scope | `notes/ut-open-61-eligibility-verification-20260812.md` is stored on disk as a single base64-encoded line (`file` reports "ASCII text ... with no line terminators"), not plain markdown — confirmed by decoding it (`base64 -D -i ... `), which reproduces the exact, coherent content shown in the GitHub-rendered doc. Git history on that file shows two "repair truncated push" commits, suggesting a prior push mangled it. Not a prompt-injection concern (decoded content is benign and on-topic) and out of scope to fix here, but worth flagging since it means `grep`/`cat` against that file will silently return garbage to any future agent who doesn't know to decode it. |

## Diagnosis (evidence, not hypothesis)

Ran the same live, read-only queries the six sibling docs establish as this family's method,
scoped to Michigan (`opencivicdata_jurisdiction.id = 'ocd-jurisdiction/country:us/state:mi/government'`,
one clean jurisdiction match, single session `2025-2026`, 3,910 bills, 25,324 `billaction` rows),
specifically to check the ticket's own citation and its two unchecked ACs (global regex breadth,
other dual-meaning tags).

**1. Classification breakdown (25,324 total MI billaction rows):**

| classification | count |
|---|---|
| *(untagged, `[]`)* | 8,091 |
| referral-committee | 4,951 |
| introduction | 4,284 |
| reading-1 | 2,608 |
| passage | 1,989 |
| committee-passage | 1,882 |
| reading-2 | 654 |
| reading-3 | 614 |
| executive-signature | 95 |
| executive-receipt | 95 |
| amendment-failure | 46 |
| **amendment-passage** | **15** |

**2. The ticket's citation checks out, exactly:** all 15 `amendment-passage` rows, across 15 distinct
bills (HB 4135, HB 4420, SB 23, SB 3, SB 462, SB 463, SB 465, SB 466, SB 483, SB 532, SB 596, SB 599,
SB 700, SB 723, SB 878), read the literal string `"AMENDMENT(S) ADOPTED"` — zero variation, zero
embedded tally. **New finding beyond the ticket's own citation:** all 15 rows' `acting_org` is
`Senate`, including for the two House-originated bills (HB 4135, HB 4420) — this tag fires only when
the Senate adopts a floor amendment on a bill currently in its own possession (own bill or a House
bill it's currently considering), never as a cross-chamber concurrence marker. Full context for
`SB 878` confirms the shape: `AMENDMENT(S) DEFEATED` (order 12, `amendment-failure`) →
`AMENDMENT(S) ADOPTED` (order 13, `amendment-passage`) → `PASSED ROLL CALL # 78 YEAS 19 NAYS 18...`
(order 14, `passage`, the chamber's own real floor vote, immediately after). **`amendment-passage`
is single-purpose for Michigan — same-chamber floor-amendment adoption, never a real vote itself,
never dual-meaning the way VA/UT's own `amendment-passage` tag is.** `amendment-failure` (46 rows)
is equally clean: 100% read `"AMENDMENT(S) DEFEATED"`, same same-chamber shape, no ambiguity.

**3. Global tally regex — confirmed 0% match, same failure mode as US Congress/Washington/Florida,
not Virginia/Utah:**

```
\(\s*\d+\s*-\s*Y\s+\d+\s*-\s*N(?:\s+\d+\s*-\s*A)?\s*\)
```

Tested against all 1,989 `passage`-classified rows: **0 matches.** Michigan's real tally text is
never parenthesized and never uses `Y`/`N`/`A` letter suffixes. Real examples:
`"passed; given immediate effect Roll Call #156 Yeas 57 Nays 45 Excused 0 Not Voting 8"`,
`"PASSED ROLL CALL # 6 YEAS 34 NAYS 0 EXCUSED 3 NOT VOTING 0"` (case varies — mixed-case and
all-caps forms both occur, seemingly by era or chamber). A Michigan-shaped regex,
`Roll Call\s*#\s*\d+\s+Yeas\s+\d+\s+Nays\s+\d+\s+Excused\s+\d+\s+Not Voting\s+\d+` (case-insensitive),
matches **1,021/1,989 (51%)**. The remaining 968 non-matches are legitimate no-tally content, not a
format gap: `"ADOPTED"`/`"adopted by unanimous standing vote"` (voice-vote/unanimous resolutions),
and a same-bill, same-classification **duplicate-notification row** — e.g. `HB 4284` has its real
tally at order 10 (`"passed; given immediate effect Roll Call #2 Yeas 63 Nays 46..."`) and then, at
order 12, a second `passage`-tagged row reading only `"PASSED BY HOUSE WITH IMMEDIATE EFFECT"` — a
cross-chamber transmittal notice carrying no tally of its own, the same "real vote recorded once,
notification recorded again nearby with no numbers" shape OPEN-60 found for Congress.

**4. New finding, beyond what the ticket asked directly — where Michigan's real cross-chamber
concurrence votes actually live:** searched all 388 `billaction` rows containing "concur"
case-insensitively. **100% (388/388) carry `classification = []`** — untagged, the same shape
Washington's and Congress's concurrence votes have (OPEN-62, OPEN-60). Of those 388, the
overwhelming majority (382, 98%) are voice-vote-style with no tally at all (`"SUBSTITUTE (S-1)
CONCURRED IN"`, `"HOUSE SUBSTITUTE (H-1) CONCURRED IN"`, etc.) — but **6 rows, across 5 real bills
(HB 4961, SB 158, SB 240 ×2, SB 241, SB 690), carry a real, embedded roll-call tally directly in the
untagged text**, e.g. `"HOUSE AMENDMENT(S) CONCURRED IN ROLL CALL # 118 YEAS 36 NAYS 1 EXCUSED 1 NOT
VOTING 0"` (SB 241), `"Senate amendment(s) concurred in Roll Call #248 Yeas 102 Nays 7 Excused 0 Not
Voting 1"` (HB 4961). **These 6 real, tallied cross-chamber votes are currently unreachable by any
classification-tag-based rule at all** — not a dual-meaning-tag problem like VA/UT, and not a
wrong-format problem like the `passage` tag's own regex gap — a genuinely new-rule gap, the same
shape Congress needed a text-pattern rule for its own untagged concurrence/cloture votes (OPEN-60).

## Approaches Evaluated

### Approach A: Replicate the OPEN-57/58/60/61/62/64 methodology exactly, scoped to Michigan

**How it works:** Direct `psycopg2` queries (read-only) against the replica, exactly as run above:
classification breakdown, full action list for at least one real bill, global-regex breadth check,
and a systematic check for any tag meaning more than one thing depending on context — extended here,
per the Diagnosis, to also check where real votes land when a tag is *absent* (the WA/Congress
lesson: absence of `amendment-passage` doesn't mean absence of a real vote to find). Write the notes
doc in the established `notes/` format, citing the real bills and action text surfaced above.

**Pros:**
- Directly reuses a methodology validated six times this sprint on the identical mechanism, across
  every outcome shape found so far (dual-meaning tag needing a `requires_pattern` gate — VA, UT;
  tag absent, real vote lands in a same-date re-tagged action — WA; tag absent, real vote never
  retagged, needs a wholly new text-pattern rule — Congress; tag present but context-/adjacency-
  dependent with vote-count-only tallies — AZ). Michigan's real shape combines two of these: a
  single-purpose, safely-excludable `amendment-passage` (closer to WA's "no override needed" case
  for that specific tag) **and** a Congress-shaped untagged-concurrence gap requiring a new rule.
  The method is exactly what surfaced this combination; a narrower method would likely have stopped
  at "the ticket's citation checks out" and missed the concurrence-tally gap entirely.
- No new tooling, no new DB connection pattern, no new risk surface. Read-only, already-scoped.
- Satisfies every AC as literally written: real bill IDs (HB 4284, SB 878, HB 4961, SB 241, and
  more), real action text, grouped classification counts, explicit breadth check beyond the 15
  `amendment-passage` rows, explicit check for other dual-meaning tags (found none — `amendment-
  failure` is equally single-shape).

**Cons:**
- Michigan has only one session persisted locally (`2025-2026`, 3,910 bills) — same "this is the
  complete corpus, not a subsample" caveat OPEN-61 (Utah) had to state plainly rather than implying
  broader coverage than the data supports.

**Standards alignment:** Principle of least privilege (read-only queries against a replica, never a
write path); reproducibility/evidentiary rigor (real bill IDs, real action text, sample completeness
stated plainly — the bar every sibling doc in this family holds itself to); "verify before assuming"
(`efficiency.md`) — directly exercised by refusing to cite the ticket's unsourced 2026-08-11 claim
without independent confirmation.

### Approach B: Query via the public `v3.openstates.org` API instead of the DB replica

**How it works:** Use `OPENSTATES_API_KEY` (already used by `quality_check.py`) to pull Michigan
bills and their `actions[]` from the public API instead of SQL rows.

**Pros:** No DB credentials needed; matches what an external consumer of OpenStates data would see.

**Cons:** `bill-actions-persisted-verification-20260811.md` already confirmed local DB rows match
the public API exactly, field-for-field, spot-checked on this exact jurisdiction (MI SB 1136) — so
this approach produces the same answer at strictly worse cost (rate limits, pagination, no
server-side `GROUP BY classification`). The ticket's AC explicitly requires querying
`opencivicdata_billaction` directly — this approach doesn't satisfy the AC as written, and it cannot
efficiently answer Diagnosis §4 (a full-table "concur" text search across 25,324 rows), which is
exactly the kind of query a single SQL statement handles and paginated API calls do not.

**Standards alignment:** None gained over Approach A; adds an avoidable external dependency for data
already proven identical (12-Factor: prefer the most direct backing service).

### Approach C: Use the `postgres` MCP tool for the queries

**How it works:** Use the connected `postgres` MCP tool instead of a standalone script.

**Pros:** No script-writing overhead; interactive.

**Cons:** Confirmed, named footgun in every prior notes doc in this repo — defaults to the `cams`
database, not the OpenStates replica on port 5433. This session independently reconfirmed a *second*,
related footgun (piping `source activate.sh` through another command silently discards the exported
`DATABASE_URL`, leaving whatever `cams`-shaped URL was already ambient) — the MCP tool's default-DB
risk and this session's own near-miss are the same class of failure: an easy, silent way to query
the wrong database and produce a notes doc with false findings.

**Standards alignment:** Fails "verify before assuming" (`efficiency.md`) — this exact assumption
has now burned or nearly burned multiple investigations in this repo.

## Tradeoff Matrix

| Dimension | A: Direct replica query (established method) | B: Public API | C: `postgres` MCP tool |
|-----------|---|---|---|
| Complexity | Low | Medium (pagination, rate limits) | Low, but hides a real footgun |
| Time to implement | Fast (proven script pattern, already run above) | Slower (network, pagination) | Fast, but risk of silent wrong-DB result |
| Correctness risk | Low (independently confirmed against public API in a prior doc) | Low, but doesn't answer full-table scans efficiently | High unless target DB explicitly overridden |
| Satisfies AC as written | Yes (explicitly requires the replica table) | No | Technically yes, if overridden |
| Surfaces jurisdiction-specific gaps beyond the ticket's own framing | Yes — found the untagged-concurrence-tally gap the ticket didn't ask about directly | Unlikely — same data, worse ergonomics for exploratory full-table scans | Same as A, if used correctly |
| Alignment with codebase precedent | Exact match (6 sibling tickets) | None | Explicitly warned against six times already |

## Recommendation: Approach A — direct replica query, established methodology, extended to check "where do real votes land when a tag is absent"

**Why this approach:**
- It's the only approach that satisfies the AC's literal requirement to query
  `opencivicdata_billaction` directly, grouped by classification, with real bill citations.
- It's the only approach efficient enough to run the exploratory full-table text searches
  (Diagnosis §4's "concur" scan across 25,324 rows) that surfaced the actual, non-obvious finding —
  a gap the ticket itself didn't name.
- Per `reuse-before-reinvent.md`, the notes-doc format and query approach are an established
  six-ticket-deep convention in this repo; this ticket doesn't need a new method, only faithful
  execution of the existing one, extended with the "check where votes land when a tag is missing"
  step OPEN-60/62 already validated as necessary.

**Why not the alternatives:**
- Approach B is strictly dominated — same underlying data (proven identical to the DB in a prior
  doc), higher cost, doesn't satisfy the AC as written, and is a poor fit for full-table exploratory
  scans.
- Approach C has two independently confirmed failure modes in this exact repo/session (the MCP
  tool's DB default, and this session's own piped-`source` near-miss) with no compensating benefit.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Citing the ticket's "already found (2026-08-11)" claim without independent verification, the way a prior agent might have for Arizona | Was live until checked this session | Medium — would ship a notes doc built on an unsourced claim | Independently re-ran the query; confirmed true (all 15 rows, exact text), documented that no supporting notes doc exists in this repo (mirrors `OPEN-57-architecture-assessment-20260812.md`'s handling of the identical situation) |
| Treating Michigan's `amendment-passage` verification as "done" once the 15-row check passes, missing that the real cross-chamber vote lives elsewhere entirely | Medium — this is exactly the kind of gap a narrower check (just re-confirm the cited claim) would miss | High — would ship a `verified=True` config with an empty ruleset while 6 real, scoreable votes stay permanently unreachable | Extend the query to search for "concur" text across all classifications (not just `amendment-passage`), the same check OPEN-60/62 ran for their own jurisdictions; already run above, gap found |
| Connecting to the wrong DB (the `cams`/MCP footgun, or the piped-`source` footgun reconfirmed this session) | Low now that both are named explicitly here | High if it happens | `source activate.sh` as its own unpiped statement; verify `echo $DATABASE_URL` shows the `:5433/openstates` replica before running any query; do not use the `postgres` MCP tool for this ticket |
| Michigan's single persisted session (`2025-2026`) reads as thin compared to VA/US's larger corpora | Certain (structural) | Low — doesn't undermine validity, just needs framing | State explicitly in the notes doc that this is the complete local MI corpus, not a subsample, the same framing OPEN-61 used for Utah's two-session corpus |

**Prerequisites:** None. `DATABASE_URL` is already exported by `activate.sh` (sourced correctly,
not through a pipe); the query pattern is directly copyable from this assessment's own Diagnosis
section and from OPEN-57/60/61/62/64's method sections.

**Tech debt created:** None. Phase 1 is read-only research producing a single notes doc; no code
changes land in this repo. Phase 2's migration, tests, and config land in `ddp-broker-py` and are
out of this repo's scope entirely — including the new text-pattern rule the Diagnosis found is
needed for Michigan's 6 untagged-but-tallied concurrence votes, which phase 2 will need to design
(likely mirroring however Congress's own concurrence/cloture text-pattern rule ends up implemented,
per OPEN-60's own note that this isn't visible from this repo).

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| OWASP Top 10 | N/A | Read-only research against an internal replica, no user input, no write path |
| Least privilege | Addressed | Read-only queries only; no `postgres` MCP tool |
| Reproducibility / evidentiary rigor | Addressed | Real bill IDs, real action text, full counts (not samples) shown for every classification checked, matching the sibling docs' bar |
| Reuse before reinvent | Addressed | Directly reuses the six prior tickets' methodology and notes-doc format rather than inventing a new one |
| Verify before assuming | Addressed | The ticket's own unsourced "already found (2026-08-11)" citation was independently re-verified rather than trusted, mirroring OPEN-57's identical situation for Arizona |
| Multi-tenancy | N/A | Not a multi-tenant application concern; jurisdiction filtering is a query predicate, not a tenancy boundary |
| Idempotent migrations | N/A here | This repo does no migration work; phase 2's migration idempotency is `ddp-broker-py`'s concern |

## Next Step

Proceed directly to writing `notes/mi-open-59-eligibility-verification-<date>.md` in the established
format, using the Diagnosis section above as the evidence base (it already satisfies every AC:
classification breakdown, a full real-bill action list, the global-regex breadth check, and the
dual-meaning-tag check — extended to the untagged-concurrence-tally gap). The notes doc should
recommend, for phase 2's `JurisdictionEligibilityConfig` (iso2 `"MI"`):
1. **Override `tally_pattern`** to the Michigan-shaped roll-call regex (51% match on real `passage`
   rows, remaining rows legitimately tally-free).
2. **No `JurisdictionEligibilityRule` needed for `amendment-passage`/`amendment-failure`** —
   confirmed single-purpose, always-same-chamber, never a real vote; safe to leave at defaults
   (excluded by the corrected `tally_pattern` simply never matching them).
3. **A new rule (text-pattern-based, not classification-based) for the 6 untagged concurrence votes**
   carrying a real roll-call tally — the same shape as Congress's own concurrence/cloture gap
   (OPEN-60), which phase 2 should reuse the structure of.

Cite `HB 4284` (duplicate-notification passage shape), `SB 878` (clean amendment-adopted →
same-chamber-passage sequence), and `HB 4961`/`SB 241` (the untagged-but-tallied concurrence gap) as
the regression-test bill candidates.
