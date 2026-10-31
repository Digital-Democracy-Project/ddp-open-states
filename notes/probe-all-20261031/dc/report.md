# Onboarding Probe — dc (DC)

**Classification:** RED
**Run at:** 2026-10-31T18:40:06.079913+00:00  |  **Wall clock:** 0.0s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

Ran on Fargate: the people and database gates (G, H) were not run, so H shows SKIP. A RED here is final; a YELLOW is provisional. Finish on the Mac: download this run's folder (`probe/dc/probe-dc-20261031/`), un-tar `sample.tar.gz` inside it, then run `verify-jurisdiction dc --from-dir <that folder>`.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | FAIL | could not import scraper module 'dc': KeyError: 'DC_API_KEY' |

## Details

### Gate A

**FAIL** (blocking) — could not import scraper module 'dc': KeyError: 'DC_API_KEY'

## Recommendation

WAF/structural — needs a human scoping conversation before any fix ticket is filed (PLAN-push-button-onboarding.md §5 Stage 0's explicit red-state instruction).
