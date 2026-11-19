# CHECKPOINT (request a34f97782): EC2 api-v3 rebuilt with its checkout at 9fba5a6 (OPEN-629 and OPEN-556 live), core c983ae68, all checks pass

Written 05:14 UTC 11-19 (date -u at write time), from the production EC2 host. **The note says Ramon's go was relayed by the PM session; I asked the user myself (pop-up) and they chose "After the scorecard rebuild ends"** (the broker scorecard rebuild had ended 05:06 UTC; row 24 is disabled, so no chain was running; the 05:00 to 07:00 timing line is therefore moot).

## Gates (05:05 UTC, read only)
- Host checkout contains **27dfda01**; the manifest has **17 `chambers:` entries** in deploy/manifest/jurisdictions.yaml and in the container's copy (17 jurisdictions, none lacking).
- api-v3 checkout clean at 7160cbc; fetched main over SSH = **9fba5a6eb5b88779d50002f92b3ddcaef541cbb9**; fast-forward OK; the range is exactly #73 (848cfec, 5e95313) and #71 (0c0c965, 6ee5ced, 9fba5a6): 5 files. #72 not in it.
- ddp-sync: no loader or os-update lines in 10 minutes; healthz 200.

## Rebuild (05:12:05 to 05:12:25 UTC)
- Running image tagged **ddp-openstates-api:pre-9fba5a6** for rollback.
- `git merge --ff-only` to 9fba5a6 (HEAD confirmed 9fba5a6eb5b8..., status clean); built with **DDP_CORE_SHA=c983ae68599e94494a94edc23d576b483922302e**, `up -d --no-deps api` only: compose exit 0, 8 s, down about 6 s, **healthz 200 before and after**.

## Checks after
- `check-core-pin-drift.py --image-core c983ae68... --container ddp-openstates-api-1`: **exit 0**.
- **OPEN-556** (read from the broker's web container through its own client, as in a630172; a direct call without the key answers 401): /ddp/enrollment **17 jurisdictions, none without `chambers`**; va {unicameral false, upper Senate, lower House of Delegates}; ne {unicameral true, upper Legislature, lower None}; nv {unicameral false, upper Senate, lower Assembly}. All as listed.
- **OPEN-629** (same way): `/bills?sort=latest_action_asc&per_page=3` with no jurisdiction answered and returned **United States SRES 4, SRES 6, SRES 9, each 2023-01-03T05:00:00+00:00** (the Mac's answer).
- ddp-sync log: 0 Tracebacks in the 3 minutes after.

Not done (not authorized): #72, any core change, any manifest edit. The NM recompute commit still waits for its own GO and the user's. The US 118/119 re-import waits until the broker scorecard go-live is finished (the user's choice).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
