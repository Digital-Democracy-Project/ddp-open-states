# Architecture Assessment: OPEN-65 — Does Arizona need a fallback-only fix, or a non-text vote-evidence mechanism?

## Architectural Question

OPEN-57 phase 1 established that no `tally_pattern` regex can ever match Arizona's vote-tally text
(it doesn't exist — 0 digits anywhere, full-table). Every Arizona motion is therefore permanently
`UNCLEAR` in `ddp-broker-py` and already falls back to the votes feed's own raw classification
(`voteevent.motion_classification` containing `'passage'`, informally called `own_passage_flag` in
this ticket — no such literal column exists in this schema, confirmed below). The question this
ticket has to answer, with real evidence rather than assumption, is: **is that existing fallback
trustworthy enough to leave alone, or does `eligible_for_scorecard` need a genuinely different kind
of evidence check for Arizona** — and if the latter, is a votecount-based mechanism (Path 2) or a
same-day/adjacent-day amendment-passage pattern (Path 3) the more promising foundation?

This is not a "how do we build X" architecture question in the usual sense — it's a "which of these
already-competing designs does the data actually support" question, evaluated the same way OPEN-57's
own architecture assessment evaluated its three approaches: against full-population evidence from
the live replica, not samples or assumptions.

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Data source | PostgreSQL (OpenStates replica) | `postgresql://openstates:openstates_dev@localhost:5433/openstates` — **not** the `cams` DB the `postgres` MCP tool defaults to (confirmed at the start of this session: `SELECT current_database()` via the MCP tool returns `cams`) |
| Query access | Direct `psycopg2` connection via `Bash`/Python | Read-only; consistent with every prior phase-1 doc's method in this repo |
| Schema (this repo) | `openstates-core` Django models → `opencivicdata_billaction`, `opencivicdata_voteevent`, `opencivicdata_votecount`, `opencivicdata_organization` | No column named `own_passage_flag` (or containing `flag`/`passage` besides `latest_passage_date` on `opencivicdata_bill`) exists anywhere in this schema — confirmed by querying `information_schema.columns`. The ticket's "own_passage_flag" is a plain-language name for `voteevent.motion_classification` containing `'passage'`, not a literal field |
| Consumer (out of reach) | `ddp-broker-py`, `Motion.eligible_for_scorecard`, `motion_eligibility.compute_eligibility()` | Not present in this workspace — same repo-boundary limitation OPEN-57/OPEN-60 both flagged. Whether `Motion` is built from `voteevent`/`votecount` directly or from `billaction.classification` text cannot be confirmed from here, and that unknown is exactly what determines whether Path 3's finding is actionable (see Diagnosis) |
| Precedent | `notes/open-57-arizona-eligibility-verification-20260812.md`, `notes/open-60-us-congress-eligibility-verification-20260812.md`, `OPEN-57-architecture-assessment-20260812.md` | Establish the DB-connection caveat, the notes-doc format, and the "is the raw passage flag reliable" question shape this ticket extends |

## Diagnosis (evidence, not hypothesis)

All queries ran directly against the live replica; full detail, per-path breakdowns, and every real
bill citation are in `notes/open-arizona-fallback-research-20260812.md` (this assessment's
companion deliverable). Summary of what the data actually shows:

**Session coverage caveat that undercuts one planned analysis axis:** the `opencivicdata_legislativesession`
table lists 34 Arizona sessions back to 2009, but only one — `57th-2nd-regular` — has any bills
loaded in this replica (2,190 bills; every other session has 0). This directly contradicts OPEN-57's
own phase-1 doc, which stated billaction rows span "sessions 49th ... through 57th." That claim does
not hold against the current snapshot. Practically, this means Path 2's "does the votecount gap
correlate with older vs. recent sessions" question cannot be answered as asked — there is only one
session to look at. The correlation that *is* answerable (by calendar month within that one session)
turned out to be more informative anyway (see below).

**Path 1 — is `own_passage_flag` reliable?** Full-population check (not the 50-row sample the AC
asked for as a floor — ran against all 2,089 AZ voteevents tagged exactly `['passage']`) against the
bill's own same-day `billaction` PASSED/FAILED record: **2,064/2,089 (98.8%) agree; 25/2,089 (1.2%)
contradict**, every one with the identical signature (`motion_text = 'failed to pass'`,
`result = 'pass'`, contradicted by a same-day `FAILED` billaction, consistent with the real
`votecount` showing a simple-majority "yes" that still falls short of Arizona's required
full-membership or supermajority threshold). The gap is one-directional — 0 of 97 `fail`-result rows
misfire the other way. Separately, no voteevent ever compounds `committee-passage` and `passage`
into one row (confirmed: only three distinct `motion_classification` values exist in the entire AZ
table), so the floor vote is always cleanly, independently self-tagged — it never needs the
`amendment-passage` billaction tag to be found. And zero committee-motion-text votes (`'do pass'`/
`'do pass amended'`) ever self-tag `'passage'`, full population, confirming the 536 amendment-passage
rows with no same-day vote are never mistakenly promoted.

**Path 2 — is `votecount` viable as a wholesale replacement signal?** 79.7% of the 2,089 passage
votes have a real nonzero votecount; 20.3% are all-zero (never fully missing — every vote has *some*
votecount row). The gap doesn't correlate meaningfully with chamber (House 77.2% vs. Senate 82.5%,
a modest ~5-point difference) but does correlate with time: it's worst in May–June, the session's
highest-volume end-of-session period (626 of 2,089 total passage votes — 30% — fall in June alone,
at 65% nonzero, versus February's 91%). A votecount-based mechanism would be least reliable exactly
when the most votes are being decided.

**Path 3 — does the same-day/adjacent-day pattern generalize?** Broadened to all 1,286
`amendment-passage` rows with a ±1-day window and a same-chamber check: 299 (23%) same-day, 176
(14%) adjacent-day, 811 (63%) no match at all — **and zero cross-chamber coincidences in either
window, across the full population.** The pattern is reliable wherever it fires. But Path 1's finding
that the floor vote is always independently self-tagged means this pattern is likely **moot as an
identification mechanism** — if `Motion` reads `voteevent` data directly (unconfirmed from this
repo), you don't need `amendment-passage` adjacency to find the real floor vote at all.

**Path 4 — is this Arizona-only?** Washington, Michigan, and Utah were all checked full-population:
all three embed real digits pervasively (Washington and Michigan's `voteevent.motion_text` are
100% digit-containing, with explicit `"yeas X nays Y"` / `"Roll Call #N Yeas X Nays Y"` tallies; Utah
is 84.6%). None shows Arizona's zero-digit shape. This is not evidence of a broader multi-jurisdiction
problem — at least not among the three checked.

## Approaches Evaluated

### Approach A: Leave `own_passage_flag` completely alone, document as verified

**How it works:** Accept the 98.8% full-population accuracy rate as sufficient; ship no change,
document Arizona's fallback as verified-trustworthy based on this research.

**Pros:** Zero implementation cost. The accuracy rate is genuinely high, and it's a full-population
result, not a sample extrapolation.

**Cons:** Silently accepts a **confirmed, understood, reproducible** 1.2% false-positive rate that
flips real bill failures into recorded passages — not a theoretical risk, but 25 specific, named,
already-identified real votes (HB 2457, HB 2095, SB 1512, SB 1152, HB 2812, and 20 more) that are
provably wrong today. Leaving this alone when the fix is cheap and the failure mode is fully
characterized is a worse trade than it looks.

**Standards alignment:** Fails a basic data-correctness standard — a known, reproducible defect with
an available fix should not ship as "verified, no changes needed."

### Approach B: Build a Path 2 votecount-based mechanism as Arizona's primary signal

**How it works:** Replace or supplement `own_passage_flag` with a check keyed on
`opencivicdata_votecount` having a real nonzero tally for the relevant vote event.

**Pros:** Uses the most granular, most "ground truth" data source available (actual per-member vote
tallies, not a derived classification).

**Cons:** Trades a 1.2%, fully-characterized, one-directional gap for a 20.3% gap that is *worse*
during the highest-volume voting period of the year (May–June, 30% of all passage votes). This is a
strictly worse reliability profile for a much larger implementation lift (a whole new signal source,
its own fallback logic for the incomplete 20%, and no existing precedent in this repo for consuming
`votecount` as a primary signal rather than a display/citation source).

**Standards alignment:** Evidence-based engineering would reject "replace a 98.8%-reliable signal
with an 79.7%-reliable one" absent a compelling reason the 1.2% gap can't be fixed more cheaply —
which Path 1's finding shows it can (see Approach D).

### Approach C: Build a Path 3 amendment-passage same-day/adjacent-day disambiguation rule

**How it works:** Mirror Virginia's `requires_pattern`-shaped rule, keyed on AZ's same-day/adjacent-day
`amendment-passage` + floor-`passage` pairing (OPEN-57 phase 1's original recommendation).

**Pros:** The pattern itself is real and reliable where it fires (zero cross-chamber coincidences,
full population).

**Cons:** Path 1's finding — the floor vote is *always* independently, unambiguously self-tagged,
with zero dependency on the `amendment-passage` billaction tag — makes this very likely moot as an
identification mechanism, provided `Motion` reads `voteevent` data directly rather than
`billaction.classification` text. Building disambiguation logic for a signal (`amendment-passage`)
that the real floor vote never needed in the first place is speculative effort against an unconfirmed
premise (`ddp-broker-py`'s actual construction path, out of reach from this repo).

**Standards alignment:** Building for a hedge that the evidence increasingly argues against is the
kind of premature complexity this repo's own precedent (OPEN-57's own Approach-A rejection) argues
against.

### Approach D (recommended): Leave `own_passage_flag` as primary signal; add a cheap same-day billaction cross-check for the confirmed 1.2% gap; treat Paths 2 and 3 as not currently justified

**How it works:** Document Arizona's fallback as trustworthy for ~98.8% of cases. For the confirmed
failure signature (`motion_text = 'failed to pass'` + `result = 'pass'` contradicted by a same-day
`billaction` `FAILED` record), recommend a lightweight guard: cross-check the vote's own `result`
against the bill's same-day `billaction` PASSED/FAILED classification before trusting `result` alone
— which was 100% populated for every one of the 2,089 votes checked, so this guard has no coverage
gap of its own. Do not build Path 2 (worse reliability profile, concentrated at the worst time) or
Path 3 (likely moot per Path 1's tag-cleanliness finding) as currently scoped.

**Pros:** Matches the actual evidence rather than either extreme (do-nothing despite a known bug, or
over-build a wholesale replacement signal that's less reliable than what it would replace). The guard
this recommends reuses data already fully available and already proven complete for this exact
purpose (§Path 1.1's cross-check). Directly answers all four of the ticket's research paths with a
concrete, evidence-backed ranking instead of leaving Path 2 vs. 3 as an open toss-up.

**Cons:** Still leaves one confirmed unknown that only `ddp-broker-py` visibility can resolve —
whether `Motion`'s construction reads `voteevent` directly (making Path 3 fully moot) or parses
`billaction.classification` text (in which case some version of Path 3's adjacency signal might still
matter for finding the floor vote, though not for validating its result). This doc names that
decision point explicitly rather than guessing, consistent with OPEN-57's own handoff practice.

**Standards alignment:** Evidence-based verification (matches this repo's established practice: full-
population checks, real bill citations, no invented examples); minimal/targeted remediation over
speculative rebuild (the guard fixes exactly the characterized defect, nothing more); least-surprise
handoff (the one genuinely unconfirmable piece is named, not assumed).

## Tradeoff Matrix

| Dimension | A: Leave alone | B: Build Path 2 (votecount) | C: Build Path 3 (amendment-passage rule) | D: Leave alone + cheap cross-check (recommended) |
|---|---|---|---|---|
| Complexity | None | High (new signal, own fallback needed) | Medium (new rule, likely for nothing) | Low |
| Correctness vs. real data | Ships a known 1.2% defect | Trades 1.2% known gap for 20.3% gap, worse at peak volume | Solves a problem Path 1 suggests may not exist | Closes the 1.2% gap with data already proven complete |
| Addresses confirmed defect | No | Indirectly, worse | No | Yes, directly |
| Risk of wasted effort | None, but risk is silent incorrectness | High — building on a less-complete signal | High — likely moot per Path 1 | Low |
| Alignment with OPEN-57/60 precedent | Contradicts "verify, don't assume" | N/A | Repeats OPEN-57's hedge without the new evidence | Extends the precedent correctly |
| Effort for any follow-up ddp-broker-py work | None needed, none possible | High | Medium, possibly wasted | Low, targeted |

## Recommendation: Approach D

**Why this approach:** It's the only one that treats every piece of evidence gathered here as
binding rather than picking a side before looking. The 98.8% base accuracy makes wholesale
replacement (B or C) hard to justify; the confirmed, reproducible 1.2% defect makes doing nothing (A)
an unjustifiable silent-acceptance of a known bug with an already-available fix.

**Why not the alternatives:** Approach A ignores 25 specific, real, already-identified vote
misclassifications this research surfaced — leaving them alone when the fix is a same-day
cross-check against data that's already 100% populated is not "verified," it's "known and ignored."
Approach B is disproven by its own completeness numbers: a 20.3% gap, concentrated in the highest-
volume voting period, is a worse foundation than the 98.8%-reliable signal it would replace.
Approach C chases a pattern that Path 1's tag-cleanliness finding suggests is unnecessary for its
stated purpose (finding the real floor vote) — building it now would be speculative work against an
unconfirmed premise about `ddp-broker-py`'s internals.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `ddp-broker-py`'s `Motion` construction parses `billaction.classification` text rather than reading `voteevent` directly, making Path 3 still relevant for *identification* (not just validation) | Unknown (repo boundary) | Medium | This doc names the decision point explicitly; a `ddp-broker-py` session should confirm before ruling Path 3 out entirely for identification purposes, even though it's moot for validation |
| The 1.2% `result`-field bug signature could evolve (e.g., Arizona's scraper gets fixed upstream, or a new failure signature emerges) | Low–Medium | Low | The cross-check is a cheap, re-runnable full-table query, not a one-time patch; same posture as OPEN-57's "cheap to re-run" note on its own digit-check |
| Session-coverage gap (only one session loaded) means the "does the votecount gap shrink over time" question is currently unanswerable | Certain (data limitation, not a design flaw) | Low | Documented plainly in the notes doc; re-check once more sessions are loaded into the replica, if that ever happens |

**Prerequisites:** None blocking this ticket's own deliverable. Any actual guard implementation is
`ddp-broker-py` work, out of scope here (confirmed: no `ddp-broker-py` checkout exists under this
workspace's tree, consistent with OPEN-57's own scoping).

**Tech debt created:** None from this research. If a future `ddp-broker-py` ticket confirms `Motion`
parses `billaction` text rather than `voteevent` data directly, that's pre-existing debt this
research surfaces, not new debt created here.

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| OWASP Top 10 | N/A | Read-only research against an internal replica; no user input, no new external-facing surface |
| Parameterized queries (OWASP A03 Injection) | Addressed | All queries in this session use `psycopg2` parameter binding for bill/date/classification filters, not string interpolation |
| Evidence-based documentation (this repo's own ADR-equivalent practice) | Addressed | Full-population queries (not samples) for every claim where the AC required it; every example cites a real bill identifier; the session-coverage discrepancy against OPEN-57's own doc is flagged directly rather than smoothed over |
| Tenant/scope isolation (multi-jurisdiction analog) | Addressed | All recommendations are scoped to Arizona-specific evidence; Path 4's breadth check is explicitly informational, not a basis for any other jurisdiction's config |
| Least-surprise handoff | Addressed | The one genuinely unconfirmable piece (`Motion`'s construction path in `ddp-broker-py`) is named as an open decision point, not guessed at, matching OPEN-57's own handoff practice |

## Next Step

Both of this ticket's deliverables are done: this assessment, and the full research doc
(`notes/open-arizona-fallback-research-20260812.md`) with every path's evidence, real bill
citations, and the full-table checks the ACs required. There's no `ddp-open-states` code or schema
work left here — this ticket is research-only, same as OPEN-57 phase 1. If Approach D's guard is
worth implementing, that's a `ddp-broker-py` ticket (a small, targeted fix — cross-check `result`
against same-day `billaction` PASSED/FAILED before trusting it), not a `ddp-open-states` change.
Recommend closing this ticket with these two docs as the handoff artifact, the same pattern OPEN-57
phase 1 used.
