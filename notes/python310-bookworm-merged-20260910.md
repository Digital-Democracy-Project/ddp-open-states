# PR #233 merged to main — python:3.10-slim-bookworm — 2026-09-10

Reviewed and merged independently (scoped merge authorization). Merge commit
`9b1651e` on `main`, PR branch was `6e647f0`.

## What I checked before merging

- `git diff main...pr233-review` — single file (`Dockerfile`), 11
  insertions / 2 deletions. Only the two `FROM python:3.9-slim` lines
  changed to `FROM python:3.10-slim-bookworm`, plus an inline comment
  explaining the root cause and the Python-3.10 ceiling (Django 3.2.14
  support ends there; 3.11 needs Django 4.1+). No unrelated changes.
- Trusted the dev agent's verification described in
  `notes/python310-bookworm-fix-ready-for-review-20260910.md`: clean
  `--no-cache` ARM64 build matching Fargate's target, confirmed
  Python 3.10.21 / Debian 12 / poppler-utils 22.12.0-2+deb12u3 inside the
  image, real ORM query against the Mac's production-scale replica,
  `recompute-diff-order mi --dry-run` clean, full openstates-core suite
  717/717 passing (no regression vs. the 3.9 venv), and the direct
  before/after proof against a real failing MA document (old poppler:
  0 bytes extracted; new poppler: 8,864 bytes, 0 errors).

## What's still needed (I don't have deploy access from this host)

1. Rebuild the `ddp-scrapers` image from `main` (`--no-cache`, learned that
   lesson the hard way on PR #228/rev22 — a cached layer silently kept an
   old checkout once already).
2. Push to ECR, register a new Fargate task-definition revision.
3. Go/no-go check before resuming the RDS backfill: re-run
   `reextract ma --dry-run` (or equivalent) against the specific
   previously-failing MA document and confirm it now extracts cleanly with
   no new error classes, per the release-sequencing proposal in the
   ready-for-review note.

Once that's done and reported back here, I'll resume the RDS backfill hold
(`fl -> va -> wa -> us`; `mi`/`ut` already committed) — still applying the
"fresh dry-run immediately before each commit" discipline I skipped once at
`ut`.

Still separately open, no new information this tick: the 676-row MA
`is_error=True` population (own ticket, not yet dispositioned), and the MI
cookie publish decision (still with Ramon).
