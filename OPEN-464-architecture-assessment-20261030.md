# Architecture Assessment: OPEN-464 — WAF handling is hard-coded for Michigan and Florida in several places and the manifest's waf.profile is not compared with them; add it to the drift check

## Architectural Question

`jurisdictions.yaml` already carries `waf.profile` (`none` / `cookie_provider` / `custom`), and the
comment block at the top of the manifest already documents that it is supposed to correspond to
`openstates-core`'s `RESILIENCE_PROFILES` dict — but `check-jurisdiction-drift.py` never actually
checks that correspondence, and a second, narrower hard-coded set (`verify-jurisdiction`'s
`FARGATE_REFUSED_STATES = {"mi"}`) encodes a distinction `waf.profile` cannot express at all. The
question is two-layered: **(1)** how does `waf.profile` get wired into the drift check so a
`cookie_provider` state with no code behind it fails loudly, and **(2)** can the probe's Michigan-only
Fargate refusal actually become manifest-driven, given that Florida has the *identical*
`waf.profile: cookie_provider` value and must **not** be refused?

## Tech Stack Context

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Manifest | `jurisdictions.yaml` + `validate_jurisdictions.py` | — | Hand-authored YAML, schema-checked (`WAF_FIELDS`, `WAF_PROFILE_VALUES`) |
| Drift check | `check-jurisdiction-drift.py` | — | Compares manifest-derived sets against each repo's own hard-coded lists; **statically parses** other repos' Python source with `ast` rather than importing it (`python_int_table`), deliberately avoiding a dependency on `ddp-sync`'s own package being installed |
| WAF/cookie code | `openstates-core/openstates/utils/resilience_profiles.py` | — | `RESILIENCE_PROFILES: Dict[str, WafResilienceProfile]`, keyed by jurisdiction code (`mi`, `fl`), each holding a `CookieProvider`, rate limit, circuit-breaker threshold |
| Cookie acquisition | `openstates-core/openstates/utils/{mi,fl}_cookies.py`, `cookie_provider.py` | — | Two structurally different mechanisms (see below) sharing one `CookieProvider` class |
| Cloud orchestration | `cloud_collector.py`, `cloud_archiver.py` (this repo) | — | Subprocess-based runners; never import `openstates` as a library, so MI's cookie gate is hand-duplicated as `if state == "mi"` rather than read from `RESILIENCE_PROFILES` |
| Onboarding probe | `verify-jurisdiction` (this repo) | — | `FARGATE_REFUSED_STATES = {"mi"}`, a second, independent hard-coded set; already has a documented (if unused for this) convention of reading manifest fields via `jurisdiction-field.sh` |
| Out-of-repo WAF touchpoints | `ddp-agents/config/scrapebot_jurisdictions.yaml`, `ddp-sync/mi_cookie_publish.py` | — | Different repos/deployables; not available in this checkout at all |
| Tests | `pytest`-style files (`test_check_jurisdiction_drift.py`, `test_verify_jurisdiction.py`) | — | This repo already has an established "break the real thing, assert the checker catches it" idiom (see below) |

### The fact that breaks the naive approach

MI and FL are **not** the same kind of `cookie_provider` underneath, and the difference is exactly
what the Fargate refusal cares about:

- **MI** (`mi_cookies.py`, Barracuda WAF): the cookie can only be reliably minted by a real browser
  running from an IP with good reputation. That has to be the Mac — ScrapeBot/CAMS mints it on a
  schedule (`ddp-sync`'s `mi_cookie_publish.py`, monthly) and *publishes* it to the shared memory
  store; `cloud_collector.py`/`cloud_archiver.py` (`if state == "mi"`, ~line 627 / ~274) refuse to run
  at all without a fresh *published* cookie — they never mint their own. This is why Fargate (a cold,
  possibly reputation-tainted IP, per `verify-jurisdiction`'s own refusal message) is refused for MI.
- **FL** (`fl_cookies.py`, F5 BIG-IP ASM WAF): the WAF only checks a User-Agent signature, which a
  Playwright warm-up run **in-process, wherever the scraper runs** (Fargate included) can satisfy
  on the spot. There is no Mac-only mint-and-publish step, no `ddp-sync` job, nothing in
  `cloud_collector.py`/`cloud_archiver.py` for FL at all.

`waf.profile: cookie_provider` is true for both. **OPEN-419 already discovered and recorded this
exact gap** for a sibling list (`scrapebot_fallback`, MI-only in `ddp-sync`): *"The manifest's
existing waf.profile does not predict it (FL has the same profile and is not on the list), so it
cannot be derived."* `FARGATE_REFUSED_STATES` is the same shape of problem, one ticket later.

## Approaches Evaluated

### Approach A: Add a narrow manifest field (`waf.fargate_safe: bool`) and make the probe read it; drift-check `waf.profile` against `RESILIENCE_PROFILES` via static parse

**How it works:**
1. `check-jurisdiction-drift.py` gets a new check, in the same family as `repo_checks()`: statically
   parse `openstates-core/openstates/utils/resilience_profiles.py`'s `RESILIENCE_PROFILES` dict
   literal with `ast` (a `python_dict_keys(path, name)` sibling to the existing `python_int_table()`
   — no import of `openstates-core`, so the checker stays free of Django/scrapelib as a dependency,
   matching why `sync_checks()` parses `ddp-sync`'s source instead of importing it). Compare that key
   set against `where(manifest, lambda e: e["waf"]["profile"] != "none")`, reported exactly like
   every other field (`DRIFT waf.profile: ...` both directions — code has a profile the manifest
   doesn't declare, or vice versa). This alone satisfies "a state declared `waf.profile:
   cookie_provider` that no code handles fails the drift check."
2. Add one new boolean to `WAF_FIELDS` in `validate_jurisdictions.py`: `fargate_safe` (required,
   `false` only for `mi` today) — named for the actual question the probe asks ("can this state's
   WAF cookie be produced from an arbitrary cloud IP"), not for today's one mechanism, so a future
   jurisdiction refused for a *different* reason (not a Mac-mint cookie at all) still fits the field
   without renaming it.
3. `verify-jurisdiction`'s `fargate_refusal()` drops `FARGATE_REFUSED_STATES` and instead reads
   `manifest[st]["waf"]["fargate_safe"]` (the manifest is already loadable in-repo via
   `validate_jurisdictions.load_and_validate`, the same loader `check-jurisdiction-drift.py` already
   uses) — refusing when it is `False`.
4. `ddp-agents/scrapebot_jurisdictions.yaml` and `ddp-sync/mi_cookie_publish.py` are untouched
   (different repos, not in this checkout) — they get OPEN-419's by-design-note treatment (point 3
   below), not a code change here.

**Pros:**
- The only approach where "the probe's refusal and the manifest agree for every state" is true *by
  construction* (one read, no second set to drift from) — matching this repo's own stated design
  philosophy almost verbatim: `cloud_collector.py`'s OPEN-188 comment says a WAF-cookie-dependent run
  "must be impossible by construction, not convention," precisely because a hand-maintained set
  (`FARGATE_REFUSED_STATES`) is convention, not construction.
- Minimal schema surface: one boolean, required only because `WAF_FIELDS` is already
  all-required-per-entry (matches the `ENROLLMENT_FIELDS` convention exactly).
- Both new checks (drift-check comparison, and `fargate_refusal` reading the field) are unit-testable
  the same way every existing check in `check-jurisdiction-drift.py`/`verify-jurisdiction` is, and the
  mutation-check idiom already exists in this file to copy
  (`test_a_hand_typed_list_coming_back_is_an_error`, `test_a_script_that_stops_reading_the_manifest_is_an_error`)
  — write the `waf.profile` equivalents of those two tests, not a new testing technique.

**Cons:**
- A real schema change (one more required field on every manifest entry), which needs a one-time
  backfill of `jurisdictions.yaml` (cheap — `false` on every entry but `mi`).
- Superficially resembles OPEN-419's withdrawn proposal ("six new required manifest booleans"),
  inviting a reviewer to reflexively reject it on "rule of three" grounds; the distinction (below)
  has to be made explicitly.

### Approach B: Leave `FARGATE_REFUSED_STATES` hard-coded; treat it exactly like OPEN-419's `scrapebot_fallback` by-design note

**How it works:** Record, in OPEN-419's by-design note (or a sibling paragraph in the same
PRIMITIVES.md section), that `FARGATE_REFUSED_STATES` cannot be derived from `waf.profile` for the
same reason `scrapebot_fallback` cannot (FL shares the profile value), and that it stays a hard-coded,
rule-of-three set until a second state needs refusing. Add only a one-directional invariant to the
drift check or a standalone test: every code in `FARGATE_REFUSED_STATES` must have
`waf.profile != "none"` in the manifest (so an *unrelated* state can never be silently refused), but
do not attempt full agreement.

**Pros:**
- No schema change; smallest possible diff.
- Directly reuses a precedent the team set three weeks ago in this exact subsystem (OPEN-419,
  2026-10-22), for what looks like an identical shape of fact.

**Cons:**
- **Does not satisfy the ticket's own acceptance criterion.** "The probe's refusal and the manifest
  agree for every state" is a two-directional claim; the one-directional invariant above only
  catches a refusal that shouldn't exist — it says nothing about a new `cookie_provider` state that
  *should* be refused (needs a Mac-minted cookie) silently defaulting to allowed, because nothing in
  the manifest says otherwise. That is precisely the failure class `cloud_collector.py`'s OPEN-188
  comment and `verify-jurisdiction`'s own "never Michigan" framing exist to prevent — a WAF-blocked
  run proceeding because a hand-maintained list wasn't updated, laundered as a "measured zero"
  (OPEN-152/153, cited directly in that file). A by-design note that reproduces this gap rather than
  closing it is the wrong lesson to take from OPEN-419: OPEN-419's field was genuinely scheduler
  rollout policy (`ddp-sync`'s own domain, per PRIMITIVES.md's explicit rule that "anything a
  scheduler decides goes in `sync_schedule.yaml`"); the Fargate refusal is this repo's own onboarding
  safety gate, not another repo's scheduling decision, so the same "wait for a second instance"
  reasoning doesn't transfer as cleanly as it first appears to.

### Approach C: Move the Fargate-safety bit into `RESILIENCE_PROFILES` (`openstates-core`) instead of the manifest, and have `verify-jurisdiction` read that

**How it works:** Add a field to `WafResilienceProfile` (e.g. `requires_published_cookie: bool`) next
to `cookie_provider`, `requests_per_minute`, etc. — it is already the validated, tested, single
source of truth for "how does this jurisdiction's WAF get handled." `verify-jurisdiction` reads it
(by import, since the Fargate image already has `openstates-core` installed editable — confirmed in
`Dockerfile`'s multi-stage build — or by the same `ast`-static-parse technique used elsewhere) instead
of `FARGATE_REFUSED_STATES`.

**Pros:**
- Keeps "genuinely code" WAF behavior entirely in code, consistent with OPEN-318's own explicit
  scoping note: *"Out of scope here: per-state behaviour that is genuinely code (MI-specific
  archiver path, RESILIENCE_PROFILES, per-state eligibility rules, timeouts)."*
- `RESILIENCE_PROFILES` is already exactly the right shape (one dataclass instance per jurisdiction)
  for a field like this, and it's the only place today that already distinguishes MI from FL
  structurally (different `CookieProvider` instances, different warm-up functions).

**Cons:**
- **Does not satisfy the literal acceptance criterion either** — "the probe's refusal and the
  manifest agree" asks specifically about the manifest; routing the decision through
  `RESILIENCE_PROFILES` instead just relocates the two-source-of-truth problem one hop over (now it's
  "does `verify-jurisdiction`'s read of `RESILIENCE_PROFILES` agree with the manifest's
  `waf.profile`?" — which is Approach A's drift-check half, done anyway, for no added benefit).
  `RESILIENCE_PROFILES`'s own docstring scopes itself to "the scraper base/mixin path and the
  archiver's fetch path" — bolting the onboarding probe on as a third reader conflates a
  scraper-runtime concern with an onboarding-safety concern that happens to correlate with it today.
- Couples a lightweight onboarding script (`verify-jurisdiction`, also run stand-alone on the Mac) to
  importing `openstates-core`'s full dependency chain, or duplicating the AST-parse machinery against
  a second file, for a property that belongs with the manifest's other per-jurisdiction onboarding
  facts (`onboarding.epic`, `onboarding.evidence`, `api_keys`) more naturally than with scraper
  runtime tuning (`requests_per_minute`, `circuit_breaker_max_consecutive_blocks`).

## Tradeoff Matrix

| Dimension | A: Manifest field + static-parse drift check | B: Hard-coded + by-design note | C: Move into RESILIENCE_PROFILES |
|-----------|-----------|-----------|-----------|
| Complexity | Medium (1 schema field, 1 new drift check, 1 call-site swap) | Low | Medium (dataclass field + probe import/parse) |
| Time to implement | Medium | Low | Medium |
| Maintainability | High — one field, one reader, no duplicate truth | Medium — note explains a gap, doesn't close it | Medium — still two sources of truth (manifest + profiles) |
| Scalability (3rd WAF state) | New state just sets `fargate_safe` + a `RESILIENCE_PROFILES` entry | Requires revisiting the by-design note and possibly redoing this ticket | New state needs a `RESILIENCE_PROFILES` field, no manifest visibility |
| Security/safety posture | High — refusal is structural, matches OPEN-188's "impossible by construction" philosophy | Low — reproduces the exact silent-drift risk this ticket exists to close | Medium — structural, but not manifest-visible to onboarding operators reading `jurisdictions.yaml` |
| Testing ease | High — same idiom as existing `check-jurisdiction-drift.py`/`verify-jurisdiction` tests | High (less to test) but tests what doesn't matter | Medium — needs either an import in test fixtures or a second AST parser |
| Reversibility | High — one field, trivial to remove later | High | Medium |
| Alignment with codebase | High (OPEN-327's "derive, don't duplicate" pattern; OPEN-188's "impossible by construction") | Partial (reuses OPEN-419's words, not its actual reasoning) | Partial (matches OPEN-318's "leave genuine code alone" but ignores that this bit isn't scraper behavior) |

## Recommendation: Approach A — add `waf.fargate_safe: bool`, drift-check `waf.profile` against `RESILIENCE_PROFILES` via static parse, and make `verify-jurisdiction` read the manifest field directly

**Why this approach:**

- It is the only one of the three that makes "the probe's refusal and the manifest agree for every
  state" true *by construction* rather than by a second comparison that can itself drift — the same
  reasoning `check-jurisdiction-drift.py`'s own `derived_from_manifest()` already applies to this
  repo's shell scripts (OPEN-327): once a consumer reads the manifest directly, there is no longer a
  second list to disagree with it.
- It follows this codebase's own explicitly-stated safety principle for this exact subsystem almost
  word for word: `cloud_collector.py`'s OPEN-188 comment insists a WAF-dependent run "must be
  impossible by construction, not convention... exactly what produced the block and the laundered
  'measured zero' on 2026-08-24." `FARGATE_REFUSED_STATES` as a hand-maintained set is convention;
  reading `manifest[st].waf.fargate_safe` is construction.
- The new drift check reuses an existing, proven technique in the same file
  (`python_int_table()`'s `ast`-based static parse of another module's dict literal) rather than
  introducing a new dependency (importing `openstates-core`, which pulls in Django/scrapelib —
  exactly the kind of heavy coupling `sync_checks()` was written to avoid for `ddp-sync`).

**Why not the alternatives, for this codebase specifically:**

- Approach B reuses OPEN-419's *words* ("rule of three," "cannot be derived from `waf.profile`")
  without checking whether its *reasoning* transfers. OPEN-419's field was deliberately left out of
  the manifest because it is `ddp-sync` scheduler policy — PRIMITIVES.md states that rule explicitly.
  `FARGATE_REFUSED_STATES` lives in this repo's own onboarding-safety script, not in a scheduler's
  config, so the "that's a different repo's decision" escape hatch Step 3 of this ticket describes
  doesn't apply to it. Applying OPEN-419's conclusion here anyway produces a documented gap, not a
  closed one — and this repo has already paid for exactly that gap twice (OPEN-152/153).
- Approach C solves a problem this ticket doesn't have (keeping scraper-runtime WAF tuning out of the
  manifest, which OPEN-318 already settled) while leaving the one the ticket's AC actually names
  (manifest agreement) unsolved, and adds a second code-reading mechanism (import or AST parse of
  `resilience_profiles.py` from `verify-jurisdiction`) that Approach A doesn't need, because Approach
  A puts the only new comparison in the one place (`check-jurisdiction-drift.py`) that already parses
  other repos' source for exactly this purpose.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `waf.profile: custom` (declared in the schema, unused today) has no defined drift-check rule | Low (no state uses it yet) | Low | Treat any `waf.profile != "none"` as requiring a `RESILIENCE_PROFILES` entry (covers `custom` the moment it's used, no extra schema work now) — call this out explicitly in `/plan-ticket` so it isn't silently assumed |
| A reviewer reflexively rejects `fargate_safe` as "another OPEN-419" | Medium | Low (review friction, not a defect) | Cite the by-design-note vs. same-repo-safety-gate distinction above directly in the PR description |
| Backfilling `fargate_safe: false` on every existing entry is a one-time manifest edit touching every jurisdiction | Low | Low | Mechanical, schema-validated change; `validate_jurisdictions.py` will reject a missing field immediately |
| Static `ast` parse of `RESILIENCE_PROFILES` breaks if the dict literal's shape changes (e.g. built programmatically later) | Low | Medium (checker goes blind, not loud) | Mirror `python_int_table()`'s existing discipline: raise `SourceError` (exit 2, not a silent pass) if the expected literal shape isn't found — already this file's stated rule ("a checker that quietly checks nothing is how the staleness watchdog went blind") |

**Prerequisites:**
- None blocking — `RESILIENCE_PROFILES`, `jurisdictions.yaml`, `check-jurisdiction-drift.py`, and
  `verify-jurisdiction` are all in this checkout today.
- Confirm with Ramon whether the OPEN-419 by-design note should be *extended* (same paragraph, since
  it's the same underlying "manifest can't distinguish MI from FL" fact) or given a sibling paragraph
  — this ticket's own Step 3 points at "OPEN-419's by-design note," singular, suggesting extension.

**Tech debt created:**
- None net-new. This closes an existing gap (manifest comment promising a comparison that was never
  wired up) and replaces a hard-coded set with a manifest read, rather than adding a new kind of
  debt. The one open judgment call (`custom` profile's drift-check rule) should be written into
  `/plan-ticket`'s output explicitly rather than left implicit in the code.

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| OWASP Top 10 | N/A | No new user input, auth, or data-exposure surface; this is internal configuration/CI tooling |
| SOLID principles | Addressed | Single responsibility preserved: the manifest states *that* a jurisdiction needs Fargate exclusion, `RESILIENCE_PROFILES` states *how* its WAF is handled — the drift check is the one place that asserts they agree, not a third copy of either |
| 12-Factor | Addressed | Config (`fargate_safe`) stays in the versioned manifest, not an environment variable or a second hard-coded constant |
| DRY / fail-closed drift detection | Addressed | Directly extends this repo's own established pattern (`derived_from_manifest`, `python_int_table`) rather than inventing a new mechanism; new checks raise `SourceError` (never a silent pass) on an unparsable source, matching the file's own stated rule |
| Accessibility | N/A | No UI involved |
| Multi-tenancy | N/A | Not a multi-tenant system |
| Idempotent migrations | N/A | No database migration involved; manifest edit is the only "migration," and it's schema-validated on every run |

## Next Step

Run `/plan-ticket` to turn this into an implementation plan — it should enumerate: the
`check-jurisdiction-drift.py` change (new `ast`-based `RESILIENCE_PROFILES` key check), the
`validate_jurisdictions.py` schema addition (`fargate_safe`), the `jurisdictions.yaml` backfill, the
`verify-jurisdiction` call-site swap (`FARGATE_REFUSED_STATES` → manifest read), the two new tests in
`test_check_jurisdiction_drift.py` (a happy-path agreement test and a mutation-style test copying
`test_a_hand_typed_list_coming_back_is_an_error`'s shape), the `test_verify_jurisdiction.py` update to
`test_fargate_refusal_refuses_michigan` (and a companion asserting Florida is *not* refused despite
sharing `waf.profile: cookie_provider`), and the PRIMITIVES.md / OPEN-419 by-design-note update for
the two touchpoints this repo cannot reach (`ddp-agents/scrapebot_jurisdictions.yaml`,
`ddp-sync/mi_cookie_publish.py`).
