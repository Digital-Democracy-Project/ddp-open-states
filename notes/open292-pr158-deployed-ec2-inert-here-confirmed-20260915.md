# PR #158 (OPEN-292) deployed on EC2 -- confirmed inert here by reading the code, real fix still needs the Mac-side restart

Deployed via the real process (`systemctl restart ddp-sync`, git pull -> rebuild -> `-p ddp-sync`
compose recreate). Quiet window confirmed first (no in-flight Fargate tasks, next scheduled job
~9.5h out). Clean restart, 17 jobs, health green, `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED`
still `true` post-restart.

Before deploying, verified your note's claim independently rather than just trusting it: read
the actual diff. The lock/heartbeat renewal logic lives entirely inside
`trigger_scraper_session_pipeline()` (`scraper_triggered_legbot.py`) -- that function contains no
host-capability check or WireGuard relay of its own. EC2's archive-completion hook never calls it
directly; it always takes the separate `_trigger_legbot_session_via_mac_wireguard` branch instead
(confirmed `_mac_capable()` is `False` here, as established earlier this thread). So this PR's
actual changed code is genuinely unreached on this host today -- deploying it here is real (the
new code is live, config wired through the same override-loop pattern OPEN-290 already fixed for
its siblings, correctly extended here too), just inert in effect, exactly as you said. Confirms
rather than just repeats your analysis.

**Still true**: the real fix only takes effect once live on the Mac, which means a restart there
-- still holding on that per your instruction, until the current MI full-session dispatch
finishes.
