# CLAUDE.md

---

## STOP — READ THIS FIRST: work in the dev checkout, not this one

**`~/Developer/repos/ddp-open-states-dev` is where you make changes and test.** This directory
(`~/Developer/repos/ddp-open-states`) is **production** — every scheduled scrape reads code
directly from here, live, with no per-jurisdiction isolation.

- Do **not** edit files or switch branches in this checkout. Not even for documentation.
- If you're already here and need to make a change: go to
  `~/Developer/repos/ddp-open-states-dev` instead, branch from there, and open a PR back to this
  repo's `main` — never push or merge directly into this checkout.
- Read-only operations (querying the DB, reading logs, checking `ps aux`) are fine here. Running
  a scrape deliberately (e.g. a one-off backfill) is fine here too — that's normal production
  operation, not a code change.
- Before anything that touches files or branches in this checkout, check for a live scrape first:
  `ps aux | grep run-scrape`. If one is running, don't touch this checkout's files or branches at
  all, in any way, until it finishes.

Full detail on the dev/prod split and the PR-required-for-promotion rule is below.

---

Instructions for Claude Code sessions working in this repository.

## Dev/prod checkout discipline

This repo has two checkouts on the Mac Studio, sharing the same GitHub remote:

- **This one (`~/Developer/repos/ddp-open-states`)** — production. Every scheduled scrape reads
  code directly from here, with no per-jurisdiction isolation. Never edit files or switch
  branches here while a scrape is running (`ps aux | grep run-scrape` first).
- **`~/Developer/repos/ddp-open-states-dev`** — isolated dev/test checkout (own venv, own
  Postgres DB, own `openstates-core`/`openstates-scrapers`/`people` checkouts). Do all code
  changes and testing here, never in the production checkout.

**Work developed in the dev checkout must land in production via a pull request, not a direct
push or local merge — as a matter of discipline, added 2026-07-25.** Both checkouts point at the
same remote, so pushing straight to `main` (or fast-forward merging locally and pushing) is
technically possible, but don't do it: open a PR for the dev→prod promotion every time, even for
a small change, so it gets one last review pass before it reaches the checkout live scrapes
depend on. This applies to both `ddp-open-states` itself and its nested `openstates-core` /
`openstates-scrapers` checkouts.
