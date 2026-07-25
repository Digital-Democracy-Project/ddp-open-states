# CLAUDE.md

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
