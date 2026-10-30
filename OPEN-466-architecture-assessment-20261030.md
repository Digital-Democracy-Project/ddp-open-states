# Architecture Assessment: OPEN-466 — Docs sweep: stale state lists (survey section C)

## Architectural Question

This ticket is framed as a pure find-and-replace ("replace each stale list with a pointer to the
manifest or the endpoint that serves the real list"), but two things make it worth a real
architectural pass rather than a blind edit:

1. **This repo already solved this exact problem once, for code.** `jurisdictions.yaml` (OPEN-221)
   plus `check-jurisdiction-drift.py` (OPEN-318/327) exist specifically because hard-coded
   jurisdiction lists drifted apart before (the manifest's own header: "NC was on 8 of ~25 and
   missing from 6"). The real question isn't "what do we replace the text with" — it's **whether
   the fix should just be editorial (swap stale prose for a pointer phrase) or whether it should
   extend the same CI-enforced discipline that already covers code lists to prose**, so this
   exact ticket doesn't recur as OPEN-5xx once the next jurisdiction is promoted.
2. **This workspace only has one of the ticket's six repos checked out.** The ticket bundles rows
   across `ddp-next`, `ddp-design-system`, `ddp-scorecard-react`, `ddp-open-states`, `ddp-broker-py`,
   `ddp-sync`, and a `ddp-infra`-owned plan document. Confirmed via directory listing: this
   workspace clone contains only `ddp-open-states` (and its nested `openstates-core`/
   `openstates-scrapers`/`api-v3` checkouts). So the second real question is **what this session can
   legitimately scope to**, independent of the first.

## Tech Stack Context

| Layer | What it is | Relevant to this ticket |
|---|---|---|
| `jurisdictions.yaml` (repo root) | Manifest, single source of truth for tracked jurisdictions since OPEN-221; now **10 entries** (`us fl wa va mi ut az ma nc al`) | The thing every stale list/count should point to instead of repeating a snapshot |
| `validate_jurisdictions.py` | Schema validator for the manifest | Not directly relevant to prose docs, but is what makes the manifest trustworthy enough to point at |
| `check-jurisdiction-drift.py` (CI-gated via `.github/workflows/validate-jurisdictions.yml`) | Compares **hard-coded code lists** (this repo's scripts, `ddp-sync`'s config) against the manifest; fails CI on disagreement (OPEN-318) | **Does not look at prose** — markdown text and YAML/compose comments are invisible to it. This is the actual gap OPEN-466 is patching, one layer up from where OPEN-318 stopped |
| `quality_check.py`'s `OCD_TO_CODE` | Used to be a hand-typed dict; now `{_ocd_id(c): c for c in _MANIFEST}` (OPEN-327) | Confirms the *code* side of this is already fixed — `PRIMITIVES.md:532`'s prose description of it as a fixed 7-state list is now describing code that no longer exists |
| `PRIMITIVES.md`, `RUNBOOK.md` | Prose documentation | Two confirmed stale instances in `PRIMITIVES.md` (lines 464, 532); the ticket's cited `RUNBOOK.md` line ranges (~103–108, ~905–909) no longer contain jurisdiction-list prose at those lines (confirms the ticket's own "line numbers move" caveat) — but a different, real stale claim was found at `RUNBOOK.md:30` (see Findings) |
| `deploy/docker-compose.ddp.yml` | Compose file, prose comments | Two confirmed "all 8" references (lines ~69, ~83), inside a longer incident-precondition comment block that should otherwise stay intact |
| Repos not in this workspace | `ddp-next`, `ddp-design-system`, `ddp-scorecard-react`, `ddp-broker-py`, `ddp-sync`, `ddp-infra` (owns `PLAN-push-button-onboarding.md`) | None of these are reachable from here — confirmed by directory listing, not assumed |

## Findings (verified directly, not re-trusting the survey's line numbers)

The ticket explicitly says the survey's rows are "not independently re-read; line numbers move."
Re-reading them for the `ddp-open-states` rows only, before recommending an approach:

- **`PRIMITIVES.md:464`** — "`all 7 tracked jurisdictions`" in `start-os-api.sh`'s description.
  Confirmed stale: the manifest now has 10 entries. Confirmed this is exactly the scenario the
  ticket warns about — **NC was promoted to `status: live` on 2026-10-22, eight days before this
  ticket was filed** (`jurisdictions.yaml:359`) — so a fixed count would have gone stale within the
  same sprint it might have been "fixed" to a new number.
- **`PRIMITIVES.md:532`** — not in the ticket's row list, but the same defect: describes
  `OCD_TO_CODE` as a hand-typed `fl wa mi ut al ma az` + `us` mapping. The code it describes was
  rewired to read the manifest under OPEN-327; the prose was never updated to match. Same fix
  shape as the row above — flagging so it isn't missed by a grep that only targets the ticket's
  literal quoted phrases.
- **`RUNBOOK.md:30`** — also not in the ticket's row list: "`Note: AL not tracked by DDP — omitted
  from nightly runs`." This is now actively misleading, not just stale: AL *is* tracked
  (`jurisdictions.yaml:408`, `status: paused`, on the archive/people-refresh/QA lists) — only its
  bill-scraping is paused. The ticket's cited RUNBOOK.md ranges (~103–108, ~905–909) don't contain
  jurisdiction-list prose at those lines today; this is likely what the survey agent actually meant,
  at a line number that has since moved.
- **`deploy/docker-compose.ddp.yml` lines ~69, ~83** — "`all 8 DDP jurisdictions`" / "`all 8
  jurisdictions`", confirmed stale for the same NC-promotion reason. These sit inside a long,
  carefully-reasoned incident-precondition comment (the EC2 `api-v3` cutover gate) — the fix must
  swap only the count reference, not touch the surrounding precondition logic.
- **`RUNBOOK.md:244`** already does this correctly today: "`jurisdictions.yaml` is the one place
  that says which jurisdictions are on which list, and `check-jurisdiction-drift.py` keeps every
  list that still exists in step with it." This is the house style to replicate at the other sites,
  not a new pattern to invent.

## Approaches Evaluated

### Approach A: Editorial fix — replace each stale count/list with a pointer phrase, no new tooling
**How it works:** At each confirmed site, replace the hard-coded number or list with prose that
names the manifest (and, where a command already exists, the command that reads it) instead of a
snapshot value — mirroring the existing `RUNBOOK.md:244` phrasing. No code changes, no new CI check.
**Pros:** Matches the ticket's stated scope exactly ("Docs-only: can close on merge," "Nothing
breaks"). Zero risk — these are comments and markdown prose with no runtime effect. Fast: this
repo's rows are four small edits. Directly satisfies the stated acceptance criteria (grep for the
old phrases returns nothing; each row fixed/removed/recorded).
**Cons:** Doesn't prevent the *next* prose drift — nothing stops someone from writing a new
hard-coded count in a future PR. Purely relies on writing the replacement so it has nothing left to
go stale (i.e., naming the manifest instead of a number), not on any enforcement.
**Standards alignment:** Single-source-of-truth / DRY — stop repeating a value that already has one
authoritative home. Matches this repo's own prior resolution of the identical problem for code
(OPEN-318's rationale applied to prose).

### Approach B: Extend `check-jurisdiction-drift.py` (or a new lightweight check) to lint prose for stale counts
**How it works:** Add a regex-based scan of tracked `.md` files and YAML/compose comments for
jurisdiction-count-shaped phrases ("all N jurisdictions", "N tracked jurisdictions", explicit state
lists), and fail CI if the number/list doesn't match the manifest.
**Pros:** Would have caught this exact ticket's rows automatically, and would catch the next one
the moment NC-style promotions happen again instead of waiting for a future survey.
**Cons:** Materially larger scope than this ticket — a prose linter has a much higher false-positive
surface than `check-jurisdiction-drift.py`'s current code-list comparisons (free text has no fixed
schema to parse against). Not requested by the ticket ("Docs-only," "Nothing breaks," explicitly
scoped to fixing/recording rows). Building it now, inside a ticket whose own acceptance criteria
don't mention tooling, is scope expansion the ticket didn't ask for and the survey didn't flag as a
gap in `check-jurisdiction-drift.py` itself (OPEN-318's own docstring lists what it deliberately does
and doesn't compare, and prose was never in scope there either).
**Standards alignment:** Would strengthen the same single-source-of-truth principle, but at the cost
of `reuse-before-reinvent.md`'s caution against building enforcement for a problem that has only
been observed once in prose form — the code-list version of this (OPEN-318) only got CI enforcement
after it had already drifted across ~25 lists; prose hasn't shown that same repeat-offender pattern
yet.

### Approach C: Fix only the ticket's literally-quoted rows, leave everything else (including the two extra findings above) alone
**How it works:** Grep for the exact phrases quoted in the ticket, fix only those, close.
**Pros:** Minimal effort, technically satisfies "grep for the old phrases... shows none" if read
narrowly.
**Cons:** Fails the ticket's own acceptance criterion in spirit — "nothing breaks; the risk is that
a stale list looks authoritative" applies just as much to `PRIMITIVES.md:532` and `RUNBOOK.md:30` as
to the rows the survey happened to quote. The ticket itself says the survey's rows weren't
independently re-read; treating the quoted phrases as the complete set contradicts that caveat.

## Tradeoff Matrix

| Dimension | A: Editorial pointer fix | B: Extend drift checker to prose | C: Fix only quoted phrases |
|---|---|---|---|
| Complexity | Low | Medium-High | Low |
| Time to implement | Low | Medium | Low |
| Matches ticket's stated scope | Exact match | Scope creep | Technically matches, substantively under-delivers |
| Prevents recurrence | Indirectly (no number left to go stale) | Directly (CI-enforced) | No |
| Risk of false positives/maintenance burden | None | Real (prose has no fixed schema) | None |
| Alignment with codebase convention | Matches `RUNBOOK.md:244`'s existing style | Extends `check-jurisdiction-drift.py`'s role | N/A |
| Satisfies "grep shows none" + "each row fixed/removed/recorded" | Yes, fully | Yes, fully, plus ongoing | Only for the literal quoted rows |

## Recommendation: Approach A — editorial pointer fix, with the two extra findings folded in

**Why this approach:** It matches the ticket's explicit scope ("Docs-only: can close on merge," "one
docs PR per repo") and the acceptance criteria as written, which ask for rows fixed/removed/recorded
and a clean grep — not new tooling. Replacing each hard-coded count/list with a reference to
`jurisdictions.yaml` (and, where a reader would want a live view, `check-jurisdiction-drift.py
--matrix`) removes the staleness at the source without inventing anything: there's no number left in
the prose to drift. This also follows `reuse-before-reinvent.md` — the fix pattern already exists at
`RUNBOOK.md:244`; apply it, don't invent a new one.

**Why not the alternatives:** Approach B solves a real future problem but is not this ticket — it
would add a prose-scanning mechanism with a much fuzzier match surface than the structured code-list
comparisons `check-jurisdiction-drift.py` does today, for a drift pattern that (unlike the pre-OPEN-
318 code lists) has only been observed once so far. Worth naming as a candidate future ticket, not
worth building inside a ticket whose own description calls it "cosmetic or documentation drift."
Approach C technically satisfies a narrow reading of the acceptance criteria but ignores the ticket's
own caveat that the survey rows aren't exhaustive or re-verified — `PRIMITIVES.md:532` and
`RUNBOOK.md:30` are real instances of the identical defect sitting one grep away from the rows the
ticket already names.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Replacement prose still implies a frozen count (e.g., "see jurisdictions.yaml's 10 jurisdictions") | Medium | Medium — recreates the exact bug one edit later | Phrase replacements as "the jurisdictions in `jurisdictions.yaml`" with no number at all, mirroring `RUNBOOK.md:244`'s existing wording |
| Compose-file edit disturbs the surrounding incident-precondition comment (EC2 cutover gate) at `docker-compose.ddp.yml` | Low | Medium (that comment block is load-bearing operational context, not decoration) | Edit only the "all 8" token in each of the two sentences; leave the rest of the precondition paragraph untouched |
| Fixing only what was found here leaves the other 5 repos' rows and the plan's consumer table unfixed, and the ticket looks "closed" by this PR alone | High (structural, not a mistake) | Low if flagged, high if not | This assessment explicitly scopes to `ddp-open-states` only; each other repo's rows (and the `ddp-infra` plan doc's consumer table) need a separate session with that repo checked out — call this out in the PR description and the ticket comment, don't imply full closure |
| A future state promotion (like NC's, 8 days before this ticket) reintroduces a hard-coded count somewhere not swept today | Medium | Low (docs-only, no runtime effect) | Not fully preventable under Approach A; name Approach B as a follow-up candidate rather than silently accepting the risk |

**Prerequisites:** None. `jurisdictions.yaml`, `check-jurisdiction-drift.py`, and the four confirmed
edit sites all already exist and are readable in this workspace.

**Tech debt created:** None net-new. Approach B (CI-enforced prose linting) is named as a legitimate
future ticket candidate if this pattern repeats a second time, consistent with how OPEN-318 itself
was only built after the code-list version of this problem had already drifted repeatedly — not
built now, just named so it isn't rediscovered from scratch.

## Standards Checklist

| Standard | Status | Notes |
|---|---|---|
| OWASP Top 10 | N/A | Pure documentation/comment edit, no runtime or auth surface touched |
| DRY / single source of truth | Addressed | Core of the recommendation — stop repeating a value `jurisdictions.yaml` already owns |
| `reuse-before-reinvent.md` | Addressed | Reuses `RUNBOOK.md:244`'s existing pointer phrasing rather than inventing new wording or tooling |
| `tech-debt.md` governance | Addressed | No debt introduced; Approach B named as a possible future ticket, not silently deferred |
| `artifacts.md` (persistent vs. ephemeral) | Addressed | Docs changes are persistent, project-scoped artifacts, committed as a normal PR per repo |
| `project-config.md` / repo-scope discipline | Addressed | This workspace's scope explicitly limited to `ddp-open-states`; other 5 repos and the plan doc called out as out-of-reach here, not silently skipped or attempted anyway |
| Multi-tenancy | N/A | Not applicable to this repo/ticket |

## Next Step

This is a small, low-ambiguity docs ticket — recommend skipping `/design-feature` (no data model or
schema involved) and going straight to `/plan-ticket` or directly to `/implement-ticket` for the
`ddp-open-states`-scoped fix: the four confirmed sites (`PRIMITIVES.md:464`, `PRIMITIVES.md:532`,
`RUNBOOK.md:30`, `deploy/docker-compose.ddp.yml` ~69/~83), each rewritten to point at
`jurisdictions.yaml` with no embedded count, opened as one docs-only PR. The other five repos' rows
and the `ddp-infra` plan document's consumer table are out of reach from this workspace and need
separate sessions with those repos checked out — report that boundary on the ticket rather than
treating this PR as closing OPEN-466 in full.
