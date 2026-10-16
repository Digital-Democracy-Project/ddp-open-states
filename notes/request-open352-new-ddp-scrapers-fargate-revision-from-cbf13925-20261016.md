# REQUEST: OPEN-352, a new `ddp-scrapers` image and task-definition revision built from openstates-core `cbf13925` (Mac side, 2026-10-15 EDT / 2026-10-16 UTC)

**For:** whoever has ECS and ECR access (Ramon chose the ddp-infra session on 2026-10-15). The prod agent on the EC2 host cannot do this: its role is denied `ecs:DescribeTaskDefinition`, as it said in `reply-open352-golive-preflight-part1-read-only-20261016.md`.

**STATUS: GO to build, test and register one new revision.** Ramon asked for this request (Mac session, 2026-10-15). It does **not** need to wait for the OPEN-352 stored-data updates (`go-open352-deploy-and-recompute-nc-wa-mi-al-az-20261016.md`): they run from a temporary copy of the code on the prod agent's host and do not use Fargate. If a HOLD note from Ramon appears on this branch, follow it instead. A failed check is not permission to improvise: stop and report.

## 1. What and why

The weekly scrape and archive of new bills run as the Fargate task `ddp-scrapers`, which carries our openstates-core code. Today the latest ACTIVE revision is **36**, image **v33**, built from openstates-core **`14cc6a5`** (OPEN-351: the Utah fixes). That code decides which documents count as versions, their order, and how diffs are made.

Since then these merged into openstates-core `main` (now **`cbf13925`**), and none of them is in v33:
* Alabama: amendment excerpts excluded (OPEN-367, #61) and a pre-diff cleaner (OPEN-372, #66);
* North Carolina: stage rules for `Edition N` / `Ratified` / `SL <year>-<N>`, `A<n>: Amendment` stamp pages excluded (OPEN-366, #62), and a pre-diff cleaner (OPEN-371, #65);
* blank (whitespace-only) extractions are no longer treated as text (OPEN-365, #63);
* Washington: introduced `Resolution` / `Joint Memorial` / `Joint Resolution` / `Concurrent Resolution` get the introduced stage (OPEN-373, #67).

**Effect of deploying:** only data archived from then on. The next scheduled runs are the weekly scrape **Sunday 2026-10-18 02:00 UTC** and Utah's archive **Monday 05:00 UTC**. **Effect of not deploying:** those runs archive new data under the old rules (for example North Carolina stamp pages would get diffs again) and a later `recompute-diff-order` has to fix it. Nothing already stored changes either way.

## 2. What to do

1. **Build a new image from openstates-core exactly at `cbf13925`** (`cbf13925934ac852f3883a4d186e27c5517e7640`), the same way v33 was built for OPEN-351 (you or the dev side know the build and registry steps; I do not). Tag it as the next version after v33 and keep the old image.
2. **Prove the code before registering anything.** In the new image, with its own Python, this must print `OK` and the `openstates` path must be inside the image:
```python
import openstates
from openstates.utils.version_ordering import (
    is_procedural_document as p, version_sort_key as k, note_stage, STAGE_INTRODUCED)
from openstates.cli.text_extract import _has_text, _clean_nc_text, _clean_al_text
assert p("North Carolina", "A1: Amendment") and not p("North Carolina", "A1: ABR-9-V-1")
assert k("Filed", "") < k("Edition 1", "") < k("Edition 2", "") < k("Ratified", "") < k("SL 2025-14", "")
assert p("Alabama", "Judiciary 1st Amendment") and not p("Alabama", "Judiciary 1st Substitute")
assert note_stage("Joint Memorial")[0] == STAGE_INTRODUCED and note_stage("Resolution")[0] == STAGE_INTRODUCED
assert not _has_text("\n \n") and _has_text("A")
assert _clean_nc_text("  A BILL TO BE ENTITLED\n  Section 1.") == "Section 1."
assert _clean_al_text("SB1\nJPKGJNN-1\nSYNOPSIS:\nx\nA BILL\nTO BE ENTITLED\nAN ACT\nBody.") == "SB1\nBody."
assert p("Utah", "Comparison to Sub #1") and not p("Utah", "Amended 2/12/2026 10:02:409")   # the Utah fixes are still in
print("OK", openstates.__file__)
```
3. **Register one new task-definition revision** of `ddp-scrapers` that differs from revision 36 **only** in the image (copy 36, change the image). Do not deregister 36. That makes the new revision the latest ACTIVE one, which is what the weekly job and ddp-sync's `openstates-backfill` endpoint (OPEN-268) pick up.
4. **Confirm:** `aws ecs describe-task-definition --task-definition ddp-scrapers` shows the new revision number, the new image tag and digest, and that the only change from 36 is the image.
5. **Rollback (record it):** `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:<new revision>` makes 36 the latest ACTIVE again.

Do this before **Sunday 2026-10-18 01:00 UTC** so the weekly scrape picks it up.

## 3. Optional proof (read-only), by the prod agent

Once the new revision is ACTIVE, one dry run through the existing endpoint launches a Fargate task from it and writes nothing:
`POST http://localhost:8001/ddp-sync/v1/trigger/openstates-backfill/nc?subcommand=recompute-diff-order&mode=dry-run` (as in the OPEN-351 note). It must print `nc: [DRY RUN] 2338 bills checked | unchanged=2588 corrected=3550 nulled=54` (the same line the prod agent got from a worktree at `cbf13925`). With the old image it cannot print that. **POST once;** the endpoint has no overlap lock. Not required for this request to be done.

## 4. Reply

A `reply-open352-fargate-...` note: the image tag and digest, the printed `OK` line, the new revision number and its difference from 36, the rollback command, and the times.

## 5. Not authorized

Running any task other than the optional dry run above; deregistering revision 36 or any other revision; changing any schedule, flag, role or secret; touching RDS; a `--commit` of any recompute (that is the other note); any scrape, archive, embedding or LegBot run.
