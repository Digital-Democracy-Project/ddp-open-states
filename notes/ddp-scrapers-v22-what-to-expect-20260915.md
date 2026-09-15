# ddp-scrapers v22 (task-def revision 26): what actually changed, and it's not dormant -- it runs next

Correcting my earlier framing (`ddp-scrapers-v22-built-open293-fix-20260915.md`): I said
registering revision 26 was purely inert/dormant. That's true for anything **currently
running**, but I checked `ddp-sync`'s actual launch code and it's not the whole picture --
`run_task` is called with `taskDefinition=fargate_cfg["task_definition"]`, and
`sync_schedule.yaml` sets that to the bare family name `"ddp-scrapers"` (no `:revision`
pinned, confirmed at both the scrape and archive config blocks). ECS's own default behavior
for a bare family name is the family's latest ACTIVE revision -- **which is now 26**. So the
next real scheduled or triggered scrape/archive Fargate task, for any jurisdiction, will pick
up v22 automatically. Nobody needs to flip anything; this isn't a "when you're ready" step.

## What actually changed, checked directly rather than assumed from commit counts

The image only bakes in five files from `ddp-open-states` itself
(`cloud_collector.py`/`cloud_archiver.py`/`cloud_text_extract.py`/`import-summary.sh`/
`docker-entrypoint.sh` -- see the Dockerfile's own `COPY` line) plus fresh clones of
`openstates-core` and `openstates-scrapers` at build time. Checked each source for real
changes since v21's build (2026-09-10 22:32:19 EDT), not just commit counts:

- **`ddp-open-states` (21 commits since v21): zero of them touch any of the five baked-in
  files.** Confirmed with `git log -- <those 5 files>` over that range -- no output. Every one
  of those 21 commits is RDS-replication setup, `quality_check.py`/`run-people-refresh.sh`
  fixes, or docs -- none of it is part of what this container actually runs. Despite the large
  commit count, **this rebuild changes nothing about scrape/archive behavior from
  `ddp-open-states`'s own side.**
- **`openstates-scrapers` (real change): OPEN-293's fix.** `usa/votes.py`'s bill-id
  normalization for HJRES/SJRES votes -- previously dropped every recorded vote on a US Joint
  Resolution silently (confirmed: real, year-plus-old gap, not lag). Going forward, US House
  votes on HJRES/SJRES bills should link correctly.
- **`openstates-core` (real change, upstream, landed today): DATA-5365.** Fixes
  case/punctuation-sensitive committee matching for USA events
  (`openstates/importers/organizations.py`) -- an upstream openstates fix, not DDP's own, that
  merged to `main` this morning. Also US-specific; affects how committee/organization names
  match during event import.

**Net: both real behavioral changes are US-federal-specific** (vote-linking + committee
matching). No other jurisdiction should see any behavior difference from this rebuild.

## What to watch on the next real run

- Any US scrape/archive job (scheduled or triggered) will run on v22/revision-26 automatically.
- Worth checking `usa/votes.py`-sourced votes for HJRES/SJRES bills actually link this time
  (OPEN-293's own fix), and watching for any committee-matching behavior change on US events
  (DATA-5365) -- first time this specific upstream fix has run against real DDP data.
- If anything looks wrong, rollback is simple: revision 25 (v21) is untouched and still
  registered -- register the old image tag again, or explicitly pass `taskDefinition:
  ddp-scrapers:25` for one run to bypass the "latest" default.
