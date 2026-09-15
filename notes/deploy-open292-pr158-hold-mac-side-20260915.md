# Deploy instructions: ddp-sync PR #158 (OPEN-292, LegBot lock lease renewal) -- hold the Mac-side restart

Merged to `ddp-sync` main. Not deployed anywhere yet.

## What it does

Replaces the LegBot overlap lock's flat 4-hour TTL with a renewed lease (10min TTL,
renewed every 2min while a dispatch is genuinely still running). Fixes a real gap: a
full-session sweep (like the MI run currently in progress) has no natural duration
bound, so the old flat TTL left long runs with zero overlap protection for most of
their own runtime once it expired.

## Important: only the Mac restart actually matters, and it would kill the current MI run

`trigger_scraper_session_pipeline` (what this PR changes) only ever executes
successfully on the Mac -- CAMS/LegBot access is Mac-only by construction, and the
code 503s rather than running this logic on a host without it. EC2's automated
trigger just relays to the Mac over WireGuard; it never runs this lock/heartbeat code
itself. So **deploying to EC2 alone accomplishes nothing real for this fix** -- it
only takes effect once live on the Mac specifically.

The Mac's `ddp-sync` (the same process, port 8001) is currently running the real
full-session MI LegBot dispatch discussed in the recent notes -- ~1,390+ bills in as
of this morning, still going. A restart there (`sudo launchctl kickstart -k
system/com.ddp.ddp-sync`) would kill that in-flight run.

**Ramon's call, and the reasoning holds**: at the current pace (~106/hr average),
that run should finish comfortably before MI's next scheduled Thursday archive run
(05:00 UTC / ~01:00 EDT) -- 13-20+ hours of margin either way. So: **please hold the
Mac-side deploy/restart until the current MI dispatch finishes.** EC2 can deploy now
if useful for consistency (harmless, but not urgent on its own per the above) --
same steps as before:

```bash
cd /home/ubuntu/ddp-sync
git pull origin main
source .venv/bin/activate
pip install .
sudo systemctl restart ddp-sync
```

**Mac, once the current MI run is confirmed finished:**
```bash
cd /Users/agentsmith/Developer/repos/ddp-sync && git pull origin main
sudo launchctl kickstart -k system/com.ddp.ddp-sync
curl -s http://localhost:8001/ddp-sync/v1/schedule
```

The one residual risk this doesn't cover in the meantime: a manual one-off archive
trigger for MI before the run finishes (the same kind that started this whole
investigation on 9/14) would still hit the old, unpatched lock behavior -- please
hold off on any manual MI archive triggers until either the LegBot run finishes or
this ships, whichever comes first.
