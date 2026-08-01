# CLAUDE.md

---

## STOP — READ THIS FIRST: work in the dev checkout, not this one

This directory (`~/Developer/repos/ddp-open-states`) is **production** — every scheduled scrape
reads code directly from here, live, with no per-jurisdiction isolation. Do **not** edit files or
switch branches here, not even for documentation — go to `~/Developer/repos/ddp-open-states-dev`
instead, branch from there, and open a PR back to this repo's `main`. Before touching anything
here, check for a live scrape first: `ps aux | grep run-scrape` — if one is running, leave this
checkout's files and branches alone until it finishes. Read-only operations (querying the DB,
reading logs) and deliberately running a scrape here (e.g. a one-off backfill) are both fine —
neither is a code change.

**This warning is for human/interactive sessions on this Mac Studio.** An automated pipeline
(e.g. CodeBot) running inside its own disposable workspace clone of this repo is a different
case — see "Dev/prod checkout discipline" below.

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

**This dev/prod split is local-checkout-only — it doesn't apply to an automated pipeline's own
clone.** `~/Developer/repos/ddp-open-states` and `~/Developer/repos/ddp-open-states-dev` are two
hand-maintained directories on this one Mac Studio that happen to share a GitHub remote. A
CodeBot (or similar) task clones that same remote fresh into its own disposable workspace, which
is a third thing entirely — already isolated by construction, safe to edit directly, and
unrelated to either fixed local path above. It should make its changes directly in its own
workspace clone, branch and PR from there as normal, and never look for or reference
`~/Developer/repos/ddp-open-states-dev` — that path is a separate, human-owned local checkout on
this one machine it has no knowledge of and no business touching. (Found 2026-08-01, OPEN-17: an
automated CodeBot run read the STOP section above literally and pushed a real, correct fix into
the human's own dev checkout under the human's own git identity instead of its own workspace,
orphaning the fix from CodeBot's PR/reporting pipeline entirely.)
