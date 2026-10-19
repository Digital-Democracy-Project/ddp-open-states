# REPLY: OPEN-399 Part 1 (read-only) done on the EC2-broker host. All gates pass; nothing changed. Waiting for GO on Part 2 (2026-10-19 UTC)

Run 15:50 to 15:52 UTC on Monday 2026-10-19, after the NC load and the Monday archives had settled. Quiet check at 15:50:33: no scrape/archive/text-extract process, no in-flight Fargate record, no Mac writes in 10 minutes, no scheduler job in the last 20 minutes. Nothing was written, committed, rejected or regenerated.

## G1 (code): PASS
Throwaway worktree of `openstates-core` at exactly `4f023bec60c0d9425472ead0927b7f82234cc936` (kept at the job's scratch folder for Part 2, `--detach`), first on `PYTHONPATH`, the existing `/opt/ddp-open-states/.venv` Python, no installs touched. `g1_code_proof.py` printed `OK <worktree>/openstates/__init__.py`. I did not run it on the old code (the note says it fails there). The host's own core checkout stays at `5c79b47d`.

## G2 (rollback point and quiet)
RDS `ddp-openstates` latest restorable time **2026-10-19T15:46:53Z** (read at 15:50). Window for Part 2: the host is quiet now; Virginia's archive is Wednesday 2026-10-21 05:00 UTC, NC's is Thursday 05:00 UTC, the weekly secondary job Sunday 2026-10-25 02:00 UTC. Anything from now until about Wednesday 04:00 UTC is clear of those by more than an hour.

## G3 (baseline on RDS, read-only)
`docs_with_marker_line` = **2,736** (Mac replica 2,738; production is 2 lower, not higher). The broker has **511** Virginia `bill_changelog` rows.

## Dry run (writes nothing; `--dry-run` in the G1 environment)
`va: [DRY RUN] 4388 bills checked | unchanged=22767 corrected=2790 nulled=0`
Gate: **`nulled=0`** and **`corrected` 2,790** vs about 2,792 (replica 4,380 bills; production has 8 more bills): PASS. Full output: `/home/bitnami/ops/open399-part1-dryrun-20261019.txt` on this host.

## The exact changelog list (step 5)
Join of production's Virginia `bill_changelog` rows to `VA_changed_docs.csv` on (bill's `primary_openstates_id`, new version note): **77 affected changelogs on 54 bills**, all `complete` + `approved`. This is the low end of your range (77 to 185): of the 511 Virginia changelogs, 83 sit on bills with a changed document and 77 of those are on a changed version. **All 77 artifact ids in `VA_affected_changelogs_snapshot.csv` are still present with the same status** (77 of 77 same). File: `notes/open399-va-recompute-20261019/VA_affected_changelogs_production.csv` (attached to this commit; columns as in the snapshot's: artifact_id, state, session, gov_id, new_version_note, status, review_status). I did not recompute the `marker_is_a_changed_line` flag; the snapshot's flag column covers the same 77 ids.

## Not checked
The `marker_is_a_changed_line` split for the production list; HB 979's api-v3 diff (that is the Part 2 check); the broker's NC row of 1 `bill_changelog` (unrelated). Part 2 and Part 3 not started and not authorized. **Waiting for Ramon's GO for Part 2.**

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
