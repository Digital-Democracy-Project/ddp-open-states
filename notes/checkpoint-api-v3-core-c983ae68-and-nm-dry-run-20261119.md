# CHECKPOINT (addendum 2 to 05a7643, Part B1 and B3 dry run): EC2 api-v3 rebuilt at core c983ae68, NM dry run matches; the commit waits for a GO

Written 04:50 UTC 11-19 (date -u at write time), from the production EC2 host. **The user's words in session (pop-up):** about the api-v3 rebuild and the dry run, "why wouldn't we just do this now? the scorecard build chain is not related to api-v3 or the New Mexico run on fargate" (I read it as the go for the rebuild and the dry run only, not the commit, and told the user so). The US 118/119 re-import (5836c52 Part B): the user chose **after the broker scorecard go-live finishes**; not started.

## Gates
- **v69 revision:** I cannot read task definition 72 from this host (the IAM role has no ecs:DescribeTaskDefinition), so I relied on your update note 58430e9 (v69 = ddp-scrapers:v69, revision 72, sha256:4c73d6a3...). I did not verify the image's recorded core myself. The one ECS task running at 04:38 UTC is **pa-0056a13b3399 on revision 71** (the 04:00 nightly); no NM task.
- ddp-sync: no loader or os-update lines in its log in the last 10 minutes. api-v3 healthz 200 before.
- core: fetched openstates-core over SSH; c983ae68599e94494a94edc23d576b483922302e is a commit that **contains 5c1455e1**; the difference is 4 files (version_ordering.py and 3 test files), as in your note.

## B1: api-v3 rebuilt (04:38:54 to 04:39:30 UTC)
- Running image tagged **ddp-openstates-api:pre-v69** (image 3258cf1cdbe0) for rollback: retag it as :local and recreate api only.
- Built with **DDP_CORE_SHA=c983ae68599e94494a94edc23d576b483922302e** (docker-compose.rds.yml), `up -d --no-deps api` only: compose exit 0, 24 s, down about 9 s, **healthz 200 before and after**. api-v3 checkout unchanged (main 7160cbc).
- `check-core-pin-drift.py --image-core c983ae68... --container ddp-openstates-api-1`: **exit 0**, "OK: the scrapers image and 1 api-v3 container(s) all run core c983ae68...".
- The container imports version_ordering and `_PROCEDURAL_DOCUMENT_NOTES` holds both Virginia and **New Mexico**.
- ddp-sync log: 0 Tracebacks in the 4 minutes after. (NM HB 4 version order not read through api-v3 yet.)

## B3: NM backup and dry run (read only; nothing written to RDS)
- **Backup (before):** /home/bitnami/ops/step-open635-637/nm-before.csv, md5 51da907a6cff393d6482c03349a18307, one row per NM version document: id, bill_id, version_note, is_bill_version, diff_baseline_id, diff_from_previous_version. RDS baseline read at the same time: **1,113 documents in 812 bills, 171 with a comparison, 0 marked not-a-version** (matches your table).
- **Dry run:** host venv (Python 3.13) with a throwaway core worktree at c983ae68 (confirmed: version_ordering.py is that worktree's file and holds the New Mexico entry), `os-text-extract recompute-diff-order nm --dry-run --list /home/bitnami/ops/step-open635-637/nm-dry.csv`, not --flags-only, 5 s, exit 0, 0 errors:
  - `nm: [DRY RUN] 812 bills checked | unchanged=899 corrected=129 nulled=85`
  - `nm: [DRY RUN] is_bill_version: set=0 changed=85 not_a_version=85`
  - `nm: [DRY RUN] diff_baseline_id: set=129 changed=0 cleared=85`
  - change list 214 documents, md5 **aa8f03e964de4348328a4c7a444905ba** (nm-dry.csv, 215 lines with the header; raw output nm-dry-raw.txt).
- **Gates:** corrected 129 (100 to 175 OK), cleared 85 (70 to 100 OK), is_bill_version changed 85 OK, only NM touched, 0 errors. **All pass.**
- **The exact split you asked about:** the 129 corrected are all version_note "Final Version" (each gains a "new" comparison against the introduced version, e.g. SM 21 doc 246459 against 246458); the 85 cleared are all version_note "Amendments in Context" (old comparison removed, is_bill_version false). **No comparison was reported as corrected-in-place instead of cleared**: comparisons 171 + 129 - 85 = 215, as your table says.

## Not done, waiting
- **The commit** (`--commit --list ...`): waits for your GO note **and the user's own go in session** (their earlier approval was for the v68 core and "0 nulled"; this run has 85 nulled by design, so I will ask them again). Then the second dry run must give corrected=0 and nulled=0. Best before NM's Sunday 11-22 02:00 UTC run.
- No search-index refresh, no LegBot, no other state.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
