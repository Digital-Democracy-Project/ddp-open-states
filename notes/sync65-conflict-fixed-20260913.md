# SYNC-65: fixed the Mac-only archiving conflict you found

Thanks for catching that before deploying -- real gap, my mistake for treating "OPENSTATES_
ARCHIVE_ENABLED is only true on the Mac" as settled when the ticket itself flagged it as an
unverified assumption.

**Fix: `ddp-sync` PR #148** (not merged yet -- want your read on it given you're the one who
found the conflict and have the production context I don't):
https://github.com/Digital-Democracy-Project/ddp-sync/pull/148

Adds a runtime check (`_mac_capable()`, gated on whether `CAMS_API_TOKEN` is configured -- true
on the Mac, false on the EC2 host per what you confirmed) so the archive-completion hook picks
the right path:
- Mac-capable: unchanged, in-process dispatch via `local_openstates_api_base`.
- Not Mac-capable (EC2): resolves sessions via `rds_openstates_api_base` instead, and dispatches
  each session over the Mac's WireGuard trigger endpoint -- reusing the `MAC_DDP_SYNC_BASE_URL`/
  `MAC_DDP_SYNC_API_KEY` plumbing you already wired and verified for SYNC-59, which I'd left in
  place unused after removing its original caller. Good thing you flagged that it was still
  there rather than something to clean up.

pm-review caught and I fixed a real bug in my first draft of the WireGuard-dispatch helper
itself (a response-shape edge case that could've broken its own never-raise contract) -- full
detail in the PR. Full ddp-sync suite: 1241 passed.

Two things I still need from you when you get a chance:
1. Does `rds_openstates_api_base` actually resolve to something real and reachable from that
   EC2 host today? (SYNC-59's own docstring called this a "known partial-rollout gap" months
   ago -- not sure if that's since been resolved.) If it's still unconfigured, the new code
   fails safe (logs a warning, skips -- doesn't crash the archive job), but obviously won't
   actually trigger anything either.
2. Whenever api-v3 PR #11 (`document_updated_since`) does get redeployed on this host's own
   api-v3 instance, can you confirm this fix's `_mac_capable()` branch actually works end-to-end
   for a real `us` archive run there?

Not merging this myself -- over to you or Ramon.
