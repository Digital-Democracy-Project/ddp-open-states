---
name: OPEN-126 — where jurisdiction credentials live, and why DC's import breaks
description: Investigation record for OPEN-126. The decision itself is in PRIMITIVES.md ("Per-jurisdiction credentials"); this file is the evidence behind it, plus the parts of the ticket's premise that turned out to be wrong and two out-of-scope findings that should not be silently dropped.
type: assessment
---

# OPEN-126 — jurisdiction credentials

**Status: the durable half is decided and written down; the DC credential itself is parked.**
The decision lives in `PRIMITIVES.md`, in the `Per-jurisdiction configuration` section, so that a
future onboarding finds it next to the analogous config decisions (OPEN-120/121/124). This file
is the audit trail, not a second copy of the decision.

Nothing in DDP's live rotation is affected. `dc` has never been scraped.

## What the ticket asked, and what the answer turned out to be

| Question | Answer |
|---|---|
| Where do per-jurisdiction secrets live? | `ddp-open-states/.env`, loaded by `activate.sh:6`'s existing `set -a` source. No new mechanism. |
| Is DC's `KeyError` DDP's or upstream's? | **Upstream's, byte-for-byte.** Do not rewrite locally. |
| Is DC wanted? | Documented default is **no** — out of scope per `PLAN-push-button-onboarding.md`. Needs Ramon to confirm or revisit. |
| Can the credential be obtained here? | **No.** Needs a human to ask DC Council; there is no self-serve registration page. |

## Three things in the ticket's premise that were wrong

Worth recording because each one changed the shape of the answer.

1. **"DC would be the first jurisdiction DDP onboards that needs its own API key."** It wouldn't.
   `va` is in the live rotation, needs `VA_API_KEY`, and that key is in `.env` today —
   `run-all-scrapes.sh:32` documents it inline (`# va requires VA_API_KEY in .env`). The
   convention did not need inventing; it needed writing down. Four jurisdictions in current
   upstream code want a credential (`va`, `usa`, `in`, `ny`) before you get to `dc`.

2. **"`.env` vs `activate.sh` vs Secrets Manager" reads as three competing options.** The first
   two are one mechanism: `activate.sh` is the committed *loader*, `.env` is the gitignored
   *store*, and `activate.sh` has sourced `.env` since before this ticket. The real question was
   only ever whether Secrets Manager should displace them, and it can't — see below.

3. **"A missing key is a bare `KeyError` at import time" reads as one problem.** It is two.
   Needing a credential is shared by five jurisdictions; failing at *import* is unique to `dc`,
   and is caused by where the lookup sits in the file rather than by anything about credentials.

## Evidence

**The failure, reproduced live** against the production venv (read-only, `PYTHONDONTWRITEBYTECODE=1`
so the live checkout was not written to):

```
DC_API_KEY set in env? False
FAILED: KeyError 'DC_API_KEY'
frames: scrapers/dc/__init__.py:4 -> scrapers/dc/bills.py:15 -> scrapers/dc/bills.py:23
```

`__init__.py:4` is `from .bills import DCBillScraper`; `bills.py:15` is `class
DCBillScraper(Scraper):`; `bills.py:23` is `"Authorization": os.environ["DC_API_KEY"]` inside the
class-level `_headers` dict. A class body executes at import, which is the whole reason this is an
import failure. The second `DC_API_KEY` site — `__init__.py:89`, in `get_session_list()` — is
call-time and is not what breaks the import.

**Provenance — upstream-identical, so out of scope to fix here.**

```
$ git diff upstream/main -- scrapers/dc/__init__.py scrapers/dc/bills.py
(no output)
$ git log --oneline upstream/main..HEAD -- scrapers/dc/
cd7e60e20 Merge remote-tracking branch 'upstream/main' into merge/upstream-main-20260801
```

Both files match public `openstates/openstates-scrapers` exactly; the only DDP commit touching
`scrapers/dc/` is an upstream merge. `PLAN-fork-management.md`'s policy applies, and `PRIMITIVES.md`
already applies the same rule to `text_extract.py`'s FL/CA checks. **Not rewritten.**

The pattern the ticket wants already exists upstream at `scrapers/va/bills.py:70-74` — and is
*also* untouched by DDP (verified against `upstream/main`). Upstream carries both the good guard
and DC's bare lookup, so this is an upstream inconsistency. The correctly-placed fix is a small
upstream PR porting VA's guard to `dc`/`in`/`ny`; it is not filed, and is not needed for anything
DDP runs.

**Why Secrets Manager is not available here, rather than merely not preferred.** `~/.aws` is
root-owned with no readable credentials, no `AWS_*` is set in the shell, and AWS is reachable only
via the root-owned sudo-gated S3 proxies (`ddp-infra/Production_S3_Wrappers.md`), which move S3
objects, not secrets. Decisively: the fleet's own Secrets Manager consumers already degrade to
`.env` on this machine on purpose — `ddp-sync/src/ddp_sync/config.py:263-276` catches the failure,
logs `"Secrets Manager unavailable"`, and calls `_load_from_env()`, with `get_config_source()`
exposing which path was taken. So `.env` is the Mac-side half of the existing fleet convention,
not a departure from it.

**Credential inventory, and its shelf life.** The five-jurisdiction table in `PRIMITIVES.md` was
derived by grepping `scrapers/` for credential-shaped `os.environ`/`os.getenv` reads against
`upstream/main` at **`9a8ec1331` (2026-08-14)**, and is anchored to that ref in the doc because
this is a fork that periodically merges upstream — a later merge can add a sixth. The same grep is
what establishes that `docker-compose.yml`'s `AR_FTP_*` and `VIRGINIA_FTP_*` pass-throughs are
stale: no file under `scrapers/` reads either name.

**Consistency with OPEN-125.** `check-scraper-imports.sh` on `fix/OPEN-125-scraper-import-deps`
already separates `MISSING CREDENTIAL` from `MISSING MODULE`/`OTHER FAILURE` by inspecting the
exception at the caller, and deliberately exits 0 for a credential while exiting 1 for a real
break. Its guard is narrow on purpose (`ENV_VAR`-shaped name **and** genuinely absent from
`os.environ`), so a plain dict `KeyError` stays a hard failure. This ticket adds no second copy of
that logic — `PRIMITIVES.md` points at it and says don't duplicate it.

## What is actually blocked, and on whom

Only the credential, and only for a jurisdiction that is currently out of scope.

- **Needs a human, not an agent:** a project-owned DC API key, requested from DC Council / the
  LIMS operator. There is no public self-service registration page for
  `lims.dccouncil.gov/api/v2` (searched; upstream's repo documents nothing beyond passing
  `DC_API_KEY` through in `docker-compose.yml`). VA's own message warns registration "can take
  days", so DC's lead time is probably not short either. It must be a project credential, not an
  individual's.
- **Needs a decision first:** whether DC is wanted at all. `PLAN-push-button-onboarding.md`
  excludes DC and the territories from the 50-state goal and the broker does raise
  `NotImplementedError` for DC (`fetch/interfaces/OpenStates/openstates_util.py:71`) — though that
  specific refusal is congressional-district resolution, not council bill scraping, so it is
  adjacent evidence rather than a direct answer. **Recommendation: don't request the key.** Record
  DC as a known, understood blocker and leave it.

Note the convention is worth having regardless of how DC resolves: `in` is on the pilot shortlist
(`NC, GA, CO, OH, IN`) and needs `INDIANA_API_KEY`, so the first credentialed onboarding DDP
actually performs is more likely Indiana.

## Out of scope — found incidentally, not acted on

A fleet-wide survey of how secrets are stored ran as part of establishing the convention. Two
findings are unrelated to jurisdiction credentials and are explicitly outside this ticket ("any
wider secrets-management change for the fleet"). Recording them so they are not lost; **neither
was changed here**, and each deserves its own ticket and its own repo's judgement:

- **`ddp-next/.gitignore` does not ignore plain `.env`.** It covers `.env.local` and
  `.env*.local` but not `.env`, and a `.env` holding token-shaped variables exists there
  untracked. Nothing is leaked today; it is one `git add -A` from being committed. Same in
  `ddp-next-dev`. Cheapest real fix found.
- **`CAMS_API_TOKEN` falls back to a hardcoded literal** in `ddp-agents/src/cams/api/auth.py:17`
  and two client sites, so a failed `.env` load makes the API accept a known token instead of
  refusing to serve — failing open rather than loud.

No credential values were read, printed, or recorded during any of this; the survey collected
variable names, file paths and loader call sites only.

## `/pm-review` round 1 — `needs_revision`, folded in

The review caught a real error in the first draft, worth recording because it is the same
conflation the ticket itself makes. The draft's onboarding step said "add the key, confirm
`check-scraper-imports.sh` stops listing it as credential-gated, scrape" — but that check only
exercises **import-time** lookups, i.e. `dc` alone. `in` and `ny` import cleanly without a
credential and fail later, so for the Indiana case the draft's own recommended verification would
have gone green while proving nothing. Fixed by splitting the onboarding step by where the lookup
sits, and by narrowing the legibility claim to import-time explicitly rather than letting
"OPEN-125 handles it" imply more than it does.

Also folded in: the `.env`-is-shell-sourced quoting note; required-vs-optional in the inventory
table (`usa` is optional and degrades); the `upstream/main` ref anchor on the table; and the grep
evidence for the stale `docker-compose.yml` entries, which the draft asserted without showing.

**Deliberately not done**, with reasons:

- *"Cross-link this from the onboarding entry point."* Reasonable, but the entry point is
  `PLAN-push-button-onboarding.md` in **`ddp-infra`** — a different repo, so it cannot be part of
  this PR. Left for whoever next revises that plan; DC and credentialed states are not in its
  active pilot path today.
- *"Prefer file/function references over line numbers."* Declined: `PRIMITIVES.md` already cites
  line numbers throughout (`run-scrape.sh:140`, `activate.sh`, etc.) and every citation here is
  paired with quoted content or a symbol name, so drift is self-evident rather than silent.
  Matching the file's existing convention beats being locally tidier.
- *"Re-check placement after the base PRs settle."* No change needed — the block appends at the
  very end of the section it extends, so it does not interleave with #147/#153's content.
- Nothing was added in the way of tooling, a helper module, a credential registry, or enforcement.
  The review did not ask for any, and the deliverable stays a convention plus a corrected error
  story.

## Reference

- `PRIMITIVES.md` → `Per-jurisdiction configuration` → **Per-jurisdiction credentials** — the decision
- OPEN-125 — the missing-package sibling and the import check this feeds
- OPEN-50 — the ticket whose verification surfaced both
- `ddp-infra/PLAN-fork-management.md` — the don't-rewrite-upstream-identical-code policy
- `ddp-infra/PLAN-push-button-onboarding.md` — the DC/territories scope exclusion and pilot shortlist
- `ddp-infra/Production_S3_Wrappers.md` — why AWS is not directly reachable here
