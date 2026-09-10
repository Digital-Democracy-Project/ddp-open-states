# Dockerfile fix ready: python:3.10-slim-bookworm, PR #233

Ramon's instruction: since Fargate/ECS is now the real production path (not Mac/prod-checkout
parity), and there's no genuine technical reason to stay on Python 3.9, upgrade Python and
regression test. Scoped with Ramon to **Python 3.10 only** (not further) -- Django 3.2.14
(pinned in `openstates-core/pyproject.toml`) is only officially supported through Python 3.10;
Django 4.1 is the first release to add 3.11 support, so going further would require its own
separate Django major-version upgrade, deliberately out of scope here.

**PR:** https://github.com/Digital-Democracy-Project/ddp-open-states/pull/233
(`fix/python310-bookworm-base` -> `main`, one file: `Dockerfile`)

## What changed

Both `FROM python:3.9-slim` lines -> `FROM python:3.10-slim-bookworm`. That's it -- no other
code changes. Fixes the root cause behind the poppler staleness we've been chasing all day:
`python:3.9-slim` pins Debian 11 "bullseye", which freezes every apt-installed package at
whatever bullseye had at its 2021 cutoff plus security-only backports. `poppler-utils
20.09.0-3.1` from that freeze is what's actually live in production today (confirmed earlier via
your EC2 check) and is 5 years stale. Bookworm (Debian 12) gets it to `22.12.0-2+deb12u3`.

## Verification already done (dev side, this session)

- `docker build --no-cache` succeeds end-to-end on this Mac (Apple Silicon/arm64 -- confirmed
  this matches production's actual Fargate target: `ecs.tf:34-35` sets
  `cpu_architecture = "ARM64"` specifically because it was built/verified on Apple Silicon, so no
  cross-arch gap between what I tested and what deploys)
- Image confirmed: Python 3.10.21, Debian 12 bookworm, poppler-utils 22.12.0-2+deb12u3
- Real Django ORM query against the Mac's 199,302-row `ddp_bill_version_document` Postgres table
  succeeds inside the new image
- `os-text-extract recompute-diff-order mi --dry-run` runs cleanly against real data inside the
  new image
- Full openstates-core pytest suite: **717 passed** inside the new image -- identical count to
  the same suite on the Mac's existing Python 3.9 venv, no regressions
- **Direct before/after fix confirmation, not just a version-number proxy**: pulled a real MA
  `is_error=True` PDF from S3 (one of the 676), confirmed it hits the exact xref/trailer
  signature from your earlier breakdown (`Couldn't find trailer dictionary` etc.) under a poppler
  build reconstructed to match what's actually live today (20.09.0-3.1, via archive.debian.org --
  the floating `python:3.9-slim` tag has itself since moved past bullseye upstream, so a fresh
  pull of it no longer reproduces what's actually deployed). That poppler produces **zero bytes**
  of extracted text on this document. The new image's poppler (22.12.0) extracts it cleanly:
  8,864 bytes, zero syntax errors/warnings. n=1, not a corpus-wide fix-rate claim, but it
  directly confirms the fix works on real previously-failing production content, not just that
  the package version number changed.
- Routed through pm-review twice (findings were real both rounds -- missing direct before/after
  proof, then unconfirmed architecture parity -- both addressed with the evidence above, not
  waved off). Round 2 verdict: approve / ship with caution.

## What I did NOT do (yours to pick up, or Ramon's)

- Did not merge -- this is my own PR, not merging it myself per the standing review-discipline
  rule
- Did not deploy to Fargate or push a new ECR image/task-definition revision -- no EC2/deploy
  access from this side
- Did not re-run the RDS backfill or lift its hold -- see the PR's "Release sequencing" section
  for a proposed go/no-go check (re-run `reextract ma --dry-run` post-deploy, confirm the
  specific MA document above now extracts cleanly with no new error classes, before resuming)

Once this merges and deploys, the RDS backfill hold (MI done, UT's `recompute-diff-order` step
held, FL/WA/VA/US not started) can be reconsidered per that same go/no-go check.
