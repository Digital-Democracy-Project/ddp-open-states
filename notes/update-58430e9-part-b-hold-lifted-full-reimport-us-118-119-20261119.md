# UPDATE to `58430e9`: the hold on Part B is lifted. Part B runs as written in `5836c52`. 2026-11-19 (Mac side, State Specific Handling)

**Not a GO.** Part B still waits on Ramon's go, as `5836c52` says.

* **Decision:** Ramon chose the **full re-import of the 118th and 119th Congresses** (OPEN-638, comment 21552): "i think it's right to re-import all the federal bills, so that we have the best data on companion bills".
* **What that means for `5836c52`:**
  * Part B runs as written: every bill of both Congresses, no `bill_no` list.
  * Part C runs unchanged, C2's counts by Congress included.
* **What stays from `58430e9`:**
  * v69 = `ddp-scrapers:v69`, revision 72, `sha256:4c73d6a35fa941b7562a2fc3673fc90a3875fa7ea30038a5a107ee1b138e8ce6`.
  * The Fargate task must report revision 72 or later.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
