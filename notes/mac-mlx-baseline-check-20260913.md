# Mac MLX/CAMS baseline check (first update, Ramon's monitoring ask)

`cams status` right now:
- CAMS server: up, no active tasks (expected -- the FL 2026E run already finished).
- Real finding: two MLX-related background heartbeats show `possibly stuck`, both ~19
  days stale --
  - `legbot_mlx_idle_watcher`: last heartbeat 19d 2h ago.
  - `legbot_mlx_pool`: last heartbeat 19d 2h ago, its last real memory snapshot dated
    2026-08-20 22:43 (`active=26.87 GB cache=0.04 GB peak=26.90 GB`).

This doesn't look like MLX itself is broken -- the FL 2026E run that just finished clearly
used it for real (the 10 new `bill_changelog` rows + 22 `ConceptStatementSet` rows are
proof of that). It looks like whatever's supposed to keep these two specific heartbeats
current hasn't fired in 19 days, independent of whether MLX itself is being used. Haven't
dug into why yet -- flagging as observed, not yet root-caused.

No unusual CPU/memory on the main CAMS process right now (0.1% CPU, ~240MB RSS, idle).
Will keep checking periodically and post here if anything changes or if a future test run
shows real resource pressure.
