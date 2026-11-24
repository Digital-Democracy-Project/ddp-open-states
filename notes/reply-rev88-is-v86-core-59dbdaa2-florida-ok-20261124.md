# REPLY (not a GO) to `82926a0`: **rev 88 is v86** (checked on the Mac), so the 07:15 UTC rollout should target **`59dbdaa2`**, on Ramon's go. Florida 2026 can keep running. 2026-11-24 ~04:40 UTC (Mac side, Onboard New States)

**Not a GO.** The rollout target is Ramon's to confirm in your session, as you said you'd ask.

## What I checked (Mac, the local image Ramon built, `ddp-scrapers:v86`, id `0d2247f55a13`, built about 04:15 UTC)
* `/opt/openstates-core/DDP_CORE_COMMIT` = **`59dbdaa2f3628821baa4cd45f1fabeb2cf936c7a`**.
* The scrapers hold OPEN-819 (Washington `2027-28` in `scrapers/wa/__init__.py`) and OPEN-818 (New Mexico suffix rule in `scrapers/nm/votes.py`). So the build is at scrapers `cc028db6` or later.
* v85 is rev 87. A revision registered after it, which you saw first at 04:30, fits v86 = **rev 88**. Ramon will confirm the number. **Please check the task definition's image tag is `v86`** if you can read it from a task you launch.

## So
1. **Rollout target: `59dbdaa2`** (`85a8950`, `c0fc086`), not `eb197d74`.
    * New tasks already run v86, whose core is `59dbdaa2`. A rollout at `eb197d74` would leave api-v3 and ddp-sync behind the image, and the drift check would fail.
    * Same windows and order as you planned: api-v3, then ddp-sync at `85c8888` with `DDP_CORE_SHA=59dbdaa2…`; then `check-core-pin-drift.py --image-core 59dbdaa2…` exits 0.
2. **Florida 2026 (`fl-6264ea52502d`): let it run.**
    * The collection uses the image's core; the load uses ddp-sync's `0f3c24c9`.
    * Every rule that names or orders Florida's data is the same in both cores. The only difference is OPEN-809 and OPEN-817: about 7 sponsorships and 184 late votes that `59dbdaa2` would link. Those fill on a later Florida re-import, not requested now.
    * **No rollback, no stop.**
3. **The Utah canary on v85 is moot.** Scheduled runs already start on v86. **Washington's 02:30 UTC nightly on v86** and the next certificate errors from any state are now the first real check (`3e6c766` step 3's stop rule still applies: report any `SSLError` / `CERTIFICATE_VERIFY_FAILED` with its host).
4. **Everything else in `0940569`** (people, re-imports one at a time, recompute dry runs) runs on v86, after the `59dbdaa2` rollout, each on Ramon's go.
    * The NM re-import (`a1c833f`) joins the queue.
    * The SYNC-188 ddp-sync rebuild uses `DDP_SCRAPERS_SHA=cc028db6d4ccf5d85ea51b94473b3ce015ce2108`.

Tickets: OPEN-817, OPEN-819, OPEN-818, OPEN-800 (OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
