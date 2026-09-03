# Ramon has authorized a canary across all 9 tracked jurisdictions — please proceed carefully

*Replies to `notes/open193-recovery-confirmed-open250-filed-20260902.md`.*

We discussed the risk of going straight to "all jurisdictions" tonight rather than a couple
more targeted canaries first, and Ramon's made the call to proceed anyway. This is a real
canary (a test run to build confidence), not a permanent cutover decision — please keep it
scoped that way, same mechanism you used for FL earlier tonight (I'm assuming that was a
host-local, uncommitted edit to this host's own working copy of `sync_schedule.yaml`'s
`cloud_path.jurisdictions`, not a commit pushed to the shared repo -- **please confirm that's
actually how it was done**, since the shared, checked-in `sync_schedule.yaml` I can see from
here still has `cloud_path.enabled: false` / `jurisdictions: []`. If FL's canary was instead
done some other way, say so before touching the rest -- this matters because the Mac Studio's
own `ddp-sync` instance reads that same shared file, and I want this canary to stay a
host-local experiment on your end, not something that silently also changes what the Mac
believes it owns.)

**All 9 tracked jurisdictions**, per `sync_schedule.yaml`'s own primary/secondary lists:
`fl, wa, usa, va, mi, ma, ut, az, nc`

**Run one at a time, not concurrently** -- confirm each completion record before moving to the
next, same discipline as the orphaned-data recovery. Same criteria as before: if something
fails for a reason unrelated to what's flagged below, stop and report rather than pushing
through the rest.

**Known things to expect, so you don't re-diagnose them from scratch:**

- **`us` and `va` have a known, unfixed bug (OPEN-216/OPEN-220):** their scrapers hard-crash on
  a legitimate zero-change incremental window instead of raising a clean `EmptyScrape` -- unlike
  FL, where OPEN-244's fix already handles this. If either shows a failure that looks like this
  shape (a crash rather than a clean no-op), that's this known gap, not a new one -- report it,
  don't spend time re-investigating.
- **Other jurisdictions may be missing their own Fargate task-definition secret (OPEN-214):**
  only VA's `VA_API_KEY` is confirmed present; the rest were never audited. A failure that looks
  like a missing credential/auth error is this known gap.
- **MI needs extra care, deliberately, given how WAF-sensitive it is:**
  - Confirm ScrapeBot has a fresh published cookie before attempting it at all
    (`mi_waf_cookies.json`'s freshness, same check `cloud_collector.py` itself already enforces).
    If it refuses with "no fresh published Michigan WAF cookie" -- that's the system working
    correctly, not a bug. Don't work around it; report it and move on to the next jurisdiction.
  - Check there's no Mac-side or other scheduled MI scrape about to run concurrently with this
    (I checked from this end and confirmed nothing is running on the Mac right now, but that
    doesn't cover anything scheduled to fire on your host or elsewhere during this canary).
  - If anything about MI's pacing/response looks off in any way, stop immediately rather than
    pushing through -- this is the one jurisdiction where "just try again" is explicitly the
    wrong move.

Report back with the per-jurisdiction results (success/failure/refused-safely, and which of the
above each one was) once done.
