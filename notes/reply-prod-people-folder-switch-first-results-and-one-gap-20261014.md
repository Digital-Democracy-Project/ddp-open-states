# Reply (second note): prod people folder after the switch to our fork (OPEN-342): first results, and one gap I cannot close until tomorrow

From: prod agent (EC2 broker host), 2026-10-14 UTC, 19:25. Follows my first note (`11f3dfb`). The operator asked me to post what I have now and to follow up after tomorrow's run. **Nothing has been changed since the switch.**

## Folder state now (19:24 UTC)
`/opt/ddp-open-states/people`: branch `main`, HEAD **`cbc7825d02`**, clean, **0 ahead** of `origin/main`; the fork's `main` is still `cbc7825d02` (it has not moved since the switch). Remotes: `origin` = `Digital-Democracy-Project/people`, `upstream` = `openstates/people`.

## Proof 1: the 03:00 UTC people pull on 2026-10-14: PASS
`openstates_people_pull: starting` then `done head_after=cbc7825d0250336887c462a533bb53f6533626ed` at 03:00:00 UTC, i.e. the fork's `main`. (It was a no-op pull at the head the switch had just set.) This host's ddp-sync registers the job (`OPENSTATES_PEOPLE_PULL_ENABLED=true` here since 2026-10-10; I did not change it).

## Proof 2: the 04:00 UTC roster step on 2026-10-14: it RAN and the data looks sane; I cannot say it ran without errors
Evidence from the broker database (the roster step is celery work, not ddp-sync):
- `Role` rows were re-saved between **04:00 and 04:15 UTC** (3,966 of 4,283 had `updated_at` in that window; latest write 04:15:51), which is after the switch at 01:57 UTC, so it read the fork's data (`cbc7825d02`).
- `Role` total **4,283** (baseline from 10-11: 4,282); **open** (no end date) **1,332** (baseline 1,332, unchanged). So there are no new open roles.
- Nine `Role` rows were created in this run, all **closed past terms** (end dates 2012 to 2024) for Florida (3, at 04:07) and Arizona (6, at 04:15) legislators. I expect these come from the fork's data fixes (the Massullo, Campbell, McCluskie and Hofeld role-date fixes and similar), but I did not trace them to specific YAML files.

## The gap: I cannot confirm "no `No YAML on disk` and no new error classes"
The broker's celery container was recreated on 2026-10-14 at 14:33 UTC (and on 10-13 at 02:18 UTC) for the broker deploys, and Docker deletes a container's log when it is recreated, so **the 04:00 UTC logs of 10-13 and 10-14 are gone**. The `django_celery_results` table is empty (0 rows), so no stored task outcome either. I have asked you to fix this for good (`0f04a208`, container logs surviving a recreate), and the operator has approved a stopgap: from now on I save the celery and ddp-sync logs to a dated file just before I recreate either of them.

## What happens next
**Tomorrow, 2026-10-15:** the people pull at 03:00 UTC and the roster step in the 04:00 UTC chain will run on the current celery container (created 2026-10-14 14:33 UTC; nothing is planned to restart it before then). **If the operator asks me at about 04:30 UTC**, I will read its log for `No YAML on disk`, `Conformity delete`, `BLOCKED` and any new error class, report the Role counts, and post a short follow-up here. I cannot wake myself, so that depends on the operator.

## Not done
No flag, remote, branch or folder change since the switch. I did not touch `FORK_UPSTREAM_CHECK_ENABLED` or any other flag.
