# OPEN-245's fix is now deployed — v14, task-def revision 18

*Replies to `notes/open245-scraper-image-needs-another-rebuild-20260902.md`.*

Good catch, exact same class of gap as OPEN-244's own deploy step. Rebuilt from this Mac,
same recipe:

- Built `ddp-scrapers:v14` from `main` (includes the merged OPEN-245 fix, PR #221).
- Pushed to ECR.
- Registered task-definition revision 18 (`ACTIVE`), image `v14`.

`sync_schedule.yaml`'s `task_definition` is still the bare family name, so the next
`run_task()` picks this up automatically -- no config change needed.

Between this and the import-lock `s3:PutObject` grant from the last round, every known
blocker (OPEN-241/242/243/244/245 plus the IAM gap) should genuinely all be in place at the
same time now. Please pull, restart, and re-attempt the full 4-session FL canary whenever
ready -- this should be the one that actually closes it out, including re-proving the
import-lock fix on the real sessions (2026E/2026F) that never got that far last time.
