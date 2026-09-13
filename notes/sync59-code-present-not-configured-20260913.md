# SYNC-59: code is deployed on EC2, but the feature isn't actually active -- needs coordinating both sides

Ramon asked whether today's `ddp-sync` restarts pulled in SYNC-59 (cloud-owned scrape ->
LegBot trigger over WireGuard). Checked directly:

**Code: yes, present.** `aaf7295` (SYNC-59, #135) is confirmed in this host's current HEAD
(`d35bf80`, today's PR #145 pull) via `git merge-base --is-ancestor`.

**Feature: no, not actually active.** All three required config values are unset on this EC2
host right now:
- `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` -- unset, defaults to `False`
- `MAC_DDP_SYNC_BASE_URL` -- unset/empty
- `MAC_DDP_SYNC_API_KEY` -- unset/empty

Per the commit's own deployment note, this flag has to be turned on independently on **both**
the EC2 and Mac sides for a cloud-owned scrape's LegBot trigger to fire end-to-end -- and the
calling side treats an empty `MAC_DDP_SYNC_BASE_URL` as "feature off," not an error, so this
has been silently inert here, not failing loudly.

Ramon wants to coordinate with you before turning this on, rather than me flipping it
unilaterally from this side. What I'd need to actually enable it here:
1. Confirmation `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` is (or will be) turned on on the
   Mac's own `ddp-sync` instance too -- both sides need it independently.
2. The Mac's real WireGuard-reachable `ddp-sync` base URL (matching the pattern
   `10.0.0.8:8002`-style API-6 already uses for the Mac's local api-v3).
3. The Mac's own `DDP_SYNC_API_KEY` value (the Bearer token this EC2 process would present
   when calling the Mac) -- not this EC2 instance's own `api_key`, a different value.

Also worth confirming while coordinating: the commit's own documented partial-rollout gap --
VA/UT-shaped "ambiguous session" jurisdictions don't trigger LegBot yet regardless (pending a
real RDS-facing read replica, `rds_openstates_api_base` still unconfigured) -- only
explicit-session jurisdictions (fl/usa-shaped) would actually fire even once the three values
above are set. Worth knowing which of this host's cloud-owned jurisdictions fall into which
bucket before assuming full coverage once enabled.
