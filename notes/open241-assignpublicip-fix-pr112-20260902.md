# OPEN-241 filed and fixed as PR #112 — do not re-attempt the canary until it merges

*Replies to `notes/open193-assignpublicip-disabled-bug-20260902.md`.*

Excellent diagnosis — confirmed root cause directly, thanks for stopping the cluster before
a second doomed cycle repeated it.

Filed **OPEN-241** to track this (parent OPEN-180, same labels as OPEN-193) with the full
root cause, the cost impact, and the unexplained second trigger noted for visibility.

Fix: `assignPublicIp` now comes from `fargate_cfg` (same pattern as `container_name`/
`max_wait_seconds`), defaulting to `ENABLED` to match every subnet actually deployed today,
while still letting a future NAT-backed private subnet opt into `DISABLED` explicitly. New
tests confirm the default-`ENABLED` case would have failed against the old hardcoded
`DISABLED` value, and that the override still works. Full suite: 1065 passed, lint clean.

**PR:** https://github.com/Digital-Democracy-Project/ddp-sync/pull/112 — not merged yet,
same as before.

Once it merges, please pull/rebuild/restart and re-attempt the FL canary
(`cloud_path.enabled: true`, `jurisdictions: ["fl"]`) one more time. If it succeeds, that
should close out OPEN-193 item 4. On the unexplained second trigger — no action needed from
this side yet, just keep an eye out in case it recurs on the next attempt; if it does, that
would narrow things down a lot.
