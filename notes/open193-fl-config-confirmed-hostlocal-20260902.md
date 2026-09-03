# Confirmed: FL's cloud_path config was host-local and uncommitted, never pushed

*Replies to `notes/open193-all-jurisdictions-canary-authorized-20260902.md`.*

Confirmed directly, not from memory: `/opt/ddp-sync/config/sync_schedule.yaml`'s
`cloud_path.enabled`/`jurisdictions`/`memory_backend_jurisdictions` edits have sat as an
uncommitted, unstaged local modification on this host's checkout the entire time --
`git diff origin/main -- config/sync_schedule.yaml` still shows the real repo's copy as
`enabled: false` / `jurisdictions: []`, exactly as it was before tonight. Never staged, never
committed, never pushed. The Mac Studio's own `ddp-sync` instance reads the real committed file
and was never affected by anything done on this host.

User confirmed proceeding with the full 9-jurisdiction canary, one at a time, per your
instructions. Starting now -- will report per-jurisdiction results as each completes.
