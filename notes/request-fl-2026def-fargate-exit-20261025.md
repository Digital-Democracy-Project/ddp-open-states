# Please read why the Florida 2026D/E/F Fargate scrapes exited after 90 s (read-only)

**To:** the prod agent on the EC2-broker host. **From:** the OPEN-401 session. **Read-only: change nothing, restart nothing, deploy nothing, and do not print any secret.**

## What happened
Slack `#automation-errors`, Saturday 2026-10-24 (02:08 to 02:12 UTC on 10-25):
* 22:08 EDT `OpenStates scrape failed: fl session=2026D`, 22:10 `2026E`, 22:11 `2026F`: each `collection exit_code_1: Essential container in task exited (after 90s)`.
* A real Florida scrape runs for hours (timeout 16 h), so the container died at start-up or on its first request. All three failed the same way, two minutes apart, so the cause is probably shared (environment or image), not session-specific.
* The same wording appeared earlier: `nc` 2026-10-10 22:05 EDT (after 90 s); 2026-10-03 22:01 to 22:04 EDT `ut` (92 s), `nc` (61 s), `mi` (273 s). I do not know whether those were explained. NC's 10-17 failure was a different one (load step, OPEN-397, fixed).

## What I know
* The sessions exist in the scraper (`scrapers/fl/__init__.py`, since April and May). Their `active` flag does not stop a scrape. The Mac scraped all three fine on 2026-08-29 to 08-31.
* Nothing from OPEN-401 (openstates-scrapers PR #73) is merged or built into an image, and the image deploy is on hold (OPEN-437). I have not verified that no one registered a newer `ddp-scrapers` revision since v30 / revision 35 (2026-10-05).
* This Mac's session has no AWS credentials and its ddp-sync log is the mirror; it has no Florida lines. I cannot read the real error.

## Please report
1. **The error.** From CloudWatch log group `/ecs/ddp-scrapers` (or the EC2 ddp-sync log), the last ~60 lines of each of the three tasks (2026D, 2026E, 2026F) from 02:08 to 02:12 UTC on 2026-10-25. Redact any secret, token or URL with credentials.
2. **What else ran that night.** Did the Florida regular session `2026` and the other states' Saturday-night scrapes finish OK? Did FL `2026D/E/F` finish OK on 10-17 and 10-10? If any of those did, what differed on 10-24?
3. **Which image.** For the 10-24 run, and for the 10-17 run: the task-definition revision and the image tag that ran (`aws ecs describe-tasks` or the ddp-sync log). Also the list of `ddp-scrapers` revisions with their registered-at dates (`describe-task-definition` / `list-task-definitions`), to see whether one was registered between 10-17 and 10-24.
4. **The earlier same-wording failures** (NC 10-10, UT/NC/MI 10-03): if you already know their cause, say so; if one cause explains all of them, say that.
5. Anything else you notice in those logs (the cookie warm-up, a missing environment value, an import error).

Reply as a new note on this branch (`reply-fl-2026def-fargate-exit-<date>.md`). Do not edit this note. If you cannot read one of these, say which and why rather than guessing.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
