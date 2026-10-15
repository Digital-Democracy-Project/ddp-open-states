# Follow-up (third note): the 2026-10-15 overnight runs on the fork's people data (OPEN-342): clean, with the log gap closed

From: prod agent (EC2 broker host), 2026-10-15 UTC, 19:33. Follows `45b09b5`. The operator asked for this check. **Read-only; nothing was changed.** The broker's celery container had not restarted since 2026-10-14 14:33 UTC, so its log of the 04:00 UTC run exists this time; I saved a compressed copy of the 03:45 to 05:15 UTC window (about 419,000 lines) at `/home/bitnami/ops/log-archive/ddp-broker-py-celery-1-20261015T0345-0515Z.log.gz` (7.9 MB).

## The 03:00 UTC people pull (ddp-sync): PASS
`openstates_people_pull: starting` then `done head_after=cbc7825d0250336887c462a533bb53f6533626ed` at 03:00:00 UTC on 2026-10-15: the fork's `main`, and the folder is still `cbc7825d02`.

## The 04:00 UTC roster step (broker celery): ran, and the log is clean on the markers you named
- It read the people repo from **04:00:11 to 04:15:33 UTC** (the span of its log lines); `Role` rows were re-saved up to 04:15:52.
- In the log window 03:45 to 05:15 UTC: **`No YAML on disk`: 0; `Conformity delete`: 0; `BLOCKED`: 0; `Traceback`: 0; `ImportError`: 0; `IntegrityError`: 0.**
- Role counts: total **4,283**, open (no end date) **1,332**, **0 created** since 04:00 UTC today (the same as after the 10-14 run); 3,966 re-saved. Nothing grew or shrank; I cannot prove no row was deleted, only that the total is unchanged.
- The 9 roles created on 10-14 trace **exactly** to the fork's fixes: the three Florida ones are Campbell (Daryl), Cassel (Hillary) and Massullo (Ralph E.), and the six Arizona ones are Miranda (Catherine, 1), Gowan (David, 3) and Gabaldón (Rosanna, 2); all nine files are among the fork's 13 changed files (the other changed legislator files are McCluskie, Hofeld and Tinnin; they created no roles).

## Error and warning kinds in the window (what each is, and whether the fork switch could cause it)
Recurring **every hour all day** (so unrelated to the nightly run): `Jurisdiction with iso2 PR does not exist` (22 per hour), **`Jurisdiction with iso2 DC does not exist`** (112 per hour; same class as the PR line, I had not noticed the DC one before), and `Error processing Voatz statement ... 'NoneType' object has no attribute 'webUrl'` (20 per hour), plus ERROR-level `Cache miss for districts_with_tallies_*` lines.
Seen **only in the nightly windows** (the two to look at):
1. **`URL collision in people repo`: 679 warnings, all between 04:00:11 and 04:15:33 UTC** (the roster step), covering **96 distinct Ballotpedia URLs** that map to two person ids each ("keeping first"). **Not caused by the fork:** the number of Ballotpedia URLs appearing on more than one person record is **38 at `d5cc49a9e5` and 38 at `cbc7825d02`** (before and after the switch), and **0 of the 96** colliding URLs appear in the fork's changes.
2. **`BROKER-88`: 54 errors, all between 05:01:17 and 05:04:59 UTC** (the scorecard step). Example: Ileana Garcia (id 1225) is a Florida state **senator** (her roles are `state_upper` only: FL0037U to 2022-11-08, FL0036U from 2022-11-08); the voter alias `Garcia` on Florida House motions (for example SB1526, HB9B) resolves to her, and the guard skips those votes "rather than attribute it to the wrong chamber". That is the guard working as designed; none of the fork's changed files is hers.
**One limit:** the logs of earlier nights are gone, so I cannot say whether these two kinds were already there before the switch; I can only say that the data show the fork's changes do not explain them.

## What is left
Nothing for you on OPEN-342 from my side. The container-log request (`0f04a208`) is still yours. I have not changed any flag, remote or folder.
