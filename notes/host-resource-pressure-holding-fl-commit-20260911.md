# Holding fl --commit — real resource pressure on this host from the nightly ddp-broker run

Ramon caught this before I ran `recompute-diff-order fl --commit`: this EC2 host is
genuinely under real memory/CPU pressure right now, coinciding with what looks like the
nightly `ddp-broker` pipeline.

Checked directly:
- `free -h`: 429MiB free / 1.8GiB "available" out of 7.7GiB total
- `uptime`: load average 1.64, 1.80, 1.50
- `docker stats`: `ddp-broker-py-celery-1` at 56.83% CPU, 1.4GiB memory, with very large
  cumulative network I/O (734GB in / 306GB out) and `ddp-broker-py-redis-1` similarly large
  (1.18TB/2.8TB cumulative) — consistent with an active, heavy nightly job, not idle
  baseline.

Fresh dry-run for `fl` (against the real pulled `v20` image, `--platform linux/arm64`) had
already completed and matched exactly (`7685 bills checked | unchanged=17325 corrected=2712
nulled=1`, identical to the throwaway-build dry-run and the earlier spot-checked sample).
Ramon has given the go-ahead to commit. **Holding the actual `--commit` run purely on
resource-contention grounds** — the fl commit container pegs ~95% CPU under QEMU arm64
emulation (this host is x86_64), and running that alongside the nightly broker job risks
either starving/OOM-affecting the broker pipeline or having the commit container itself get
throttled/killed mid-write, which is a bad time for a real RDS write to get interrupted.

**Plan: wait until the nightly run completes, then run `fl --commit`** (no need to re-verify
dry-run again immediately before, since it just ran clean minutes ago — will re-check
resource load is actually clear first, not just that time has passed). Will report back once
committed. Not touching `va`/`wa`/`us` until `fl` is done and verified.
