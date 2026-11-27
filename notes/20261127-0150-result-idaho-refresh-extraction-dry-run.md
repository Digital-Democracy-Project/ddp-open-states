# Result 11-27 01:50 UTC: Idaho `refresh-extraction` DRY RUN (OPEN-895); nothing committed

* Gate: no Idaho task or lock; no ddp-sync job in the last 10 minutes; "now" 01:27:48 UTC is the restore point. **The code that ran: openstates-core `647bb3994ed819ba4194820b379147f525219479`**, read from the container's own `DDP_CORE_COMMIT` file (`/opt/openstates-core/DDP_CORE_COMMIT`); scrapers copy `d0bd1826` (not used by this tool).
* `os-text-extract refresh-extraction id --dry-run` (ran 01:27:53 to 01:30:01, exit 0), the exact line: **`id: [DRY RUN] bills_with_stale_docs=400 stale_docs=438 diffs_would_change=23 docs_skipped=0 docs_refused=0`.**
* Your expected **438 changed** matches `stale_docs=438` (400 bills carry them; the tool prints no "unchanged" figure, so I cannot confirm 486 unchanged from this line); **0 errors** matches `docs_refused=0` and `docs_skipped=0`. It also reports **23 diffs would change** (the diffs recomputed for those bills).
* **Not committed.** The commit step waits for a go note naming the refresh commit (your step 3); after it, the recompute dry run. Nothing else changed.
