# OPEN-285: real clean run confirmed -- all 9 states, first time ever. Close it.

Pulled `openstates-core` PR #46 in via a full `--no-cache` rebuild of `ddp-sync`'s image
(openstates-core is cloned fresh at image build time, not bind-mounted -- needed the `--no-cache`
to force a real re-clone rather than reusing a cached layer). Clean restart, no in-flight
Fargate tasks at the time, scheduler back up with 16 jobs, no errors.

Re-triggered `openstates_people_refresh` for real. **Confirmed via Redis flow-status**:
```
{"flow": "openstates_people_refresh", "started_at": "...17:53:40Z", "completed_at":
"...17:59:36Z", "status": "completed", "duration_seconds": 355.6}
```
Zero `ERROR:` lines in this run's log section (checked directly). Arizona's real person-merge
went through cleanly this time -- 13 people consolidated via merge, no crash. The "went missing
from source data" cases (9 in AZ, 1 in AL) are now correctly logged as informational and left
alone, exactly per Ramon's instruction, instead of failing the whole run.

**This is the first time `openstates_people_refresh` has ever completed successfully on this
host.** Every original OPEN-285 item is now resolved:
- Path bug, missing git, venv mismatch, silent-failure masking, DATABASE_URL wiring (x2),
  purge policy, AZ schema crash -- all fixed and now verified together in one real clean run.
- Legacy crontab entry: confirmed removed (Ramon, directly).
- IAM EventBridge/Scheduler visibility: closed by Ramon's direct confirmation, no grant needed.

Recommend closing OPEN-285 (and OPEN-193 right behind it, per its own stated closure rule).
