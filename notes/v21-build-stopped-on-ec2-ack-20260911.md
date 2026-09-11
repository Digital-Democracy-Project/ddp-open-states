# Stopped the v21 build on this host — acknowledged

Caught your note in time. The `v21` build had been running here ~25 minutes (arm64 under
QEMU emulation — pip install alone took ~18 min), still in the final stage (playwright
Chromium download, not yet at the poppler-utils/chown steps). Killed the client-side
`docker build` process; confirmed `buildkitd` dropped back to idle CPU afterward (not just
disconnected while still building server-side), so there's no orphaned build consuming
resources. No image was ever produced — nothing to clean up on that front. Cleaned up the
local clone at `/tmp/ddp-open-states-deploy`.

No harm done beyond the CPU/memory it burned for ~25 min alongside the nightly `ddp-broker`
job — not ideal timing, but nothing broke. Standing by for your new `v21` tag / task-def
revision number once you've built and registered it on the Mac. Once that lands I'll run the
supervised dry-run canary via the `ddp-sync` trigger endpoint.

Still separately holding `fl`'s `recompute-diff-order --commit` for the same nightly
resource-pressure reason (unrelated to this).
