# OPEN-230 — Phase 1 pilot candidate selection

PLAN-push-button-onboarding.md §6 (Pilot) / §5 Stage 0. All 5 shortlisted candidates were
probed with `verify-jurisdiction` (OPEN-222) against the isolated `ddp-open-states-dev`
checkout, with `--import` so gate H had real data to check against. No production database
writes, no scraper code changes, no tickets filed by the probe itself.

## Results

| State | Classification | Blocking gate failures | Notes |
|---|---|---|---|
| NC | YELLOW | H only | H fails only because of a known `verify-jurisdiction` limitation (below), not a real scraper defect |
| CO | YELLOW | C, H | C is a real gap: no extractor entry for `text/html` |
| GA | RED | A | `ModuleNotFoundError: No module named 'suds'` — missing dependency |
| OH | RED | A | `ModuleNotFoundError: No module named 'cloudscraper'` — missing dependency |
| IN | RED | A, D, H | `KeyError('INDIANA_API_KEY')` — missing credential |

Full reports: `notes/nc-onboarding-probe-20260831.md`, `notes/co-onboarding-probe-20260831.md`,
`notes/ga-onboarding-probe-20260831.md`, `notes/oh-onboarding-probe-20260831.md`,
`notes/in-onboarding-probe-20260831.md`.

Not all five failed (the §6 disqualification rule doesn't apply), so per §6 the choice is the
cleanest of the five, not just the first green/yellow one.

## Gate H caveat (applies to NC and CO alike)

Gate H failed for both YELLOW candidates despite `os-update --import` exiting 0. Investigated
directly (psycopg2 query against `openstates_dev`, plus reading the raw scraped JSON): real
version/document data exists in the dry-scrape sample, and `Jurisdiction` rows exist from
`os-initdb`'s static seed, but zero `LegislativeSession` rows exist for a never-before-imported
state. `os-update <st> --import` only invokes the bills importer; `LegislativeSession` rows are
created by a separate jurisdiction-level importer
(`openstates-core/openstates/importers/jurisdiction.py`) that path never triggers. This is a
real, deeper limitation of the probe's `--import` mechanism for genuinely virgin states — not
fixed here; deliberately scoped out as follow-up work, tracked separately so it doesn't block
this ticket's own scope (probe + select, not fix the probe further).

Because this caveat applies equally to NC and CO, it does not distinguish between them — CO's
extra Gate C failure does.

## Decision: NC

NC is the cleanest candidate: its only blocking-gate failure is the shared Gate H caveat above,
which is a probe-tooling gap rather than a defect in NC's own scraper. CO has that same caveat
plus a second, real blocking gap (Gate C, no `text/html` extractor). GA, OH, and IN are RED for
reasons requiring real fix work (two missing Python dependencies, one missing API credential) —
none of that is in scope for this ticket.

`jurisdictions.yaml`'s `nc` entry is set to `status: probing` with `onboarding.evidence`
pointing at NC's probe report. Per OPEN-230's own scope note, no Stage 1 fix-cycle epic is
filed here — NC has no real blocking gap for one to scope against yet.

## Next

OPEN-231 picks up from here: Stage 1 (fix cycle — expected to need zero tickets, since NC has
no real blocking gap) through Stage 6 (soak + handoff) for NC.
