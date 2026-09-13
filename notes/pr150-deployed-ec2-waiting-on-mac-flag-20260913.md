# PR #150 merged and deployed on EC2 -- waiting on the Mac-side flag flip to retry FL 2026E

Ramon merged PR #150. Pulled (`b8d149c`), rebuilt, clean restart on this host (no in-flight
Fargate tasks at the time), no errors, scheduler back up with 16 jobs. Confirmed
`replica_freshness_content_check_enabled: True` (the default) is live here -- expected, this
check doesn't run on this host regardless.

Whenever you've set `REPLICA_FRESHNESS_CONTENT_CHECK_ENABLED=false` on the Mac and restarted
there, ping this thread and I'll retry the FL 2026E direct-session-dispatch (same approach as
before: `_trigger_legbot_session_via_mac_wireguard('FL', '2026E', ...)`, in-memory flag
override on this side only, no persistent EC2 config change).
