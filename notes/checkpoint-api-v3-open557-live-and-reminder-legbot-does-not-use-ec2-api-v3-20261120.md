# CHECKPOINT (request 900139843, OPEN-557) and a REMINDER from Ramon: LegBot does not read from api-v3 on this EC2 host

Written 04:55 UTC 11-20 (date -u at write time), from the production EC2 host. I read your GO note 07bde0554 and this request in full.

## REMINDER from Ramon (relayed by me, 11-20 ~04:52 UTC, in session)
**"legbot does not read from api-v3 on this EC2 instance; I believe that only the broker uses api-v3 here to pull the latest bill updates."** Please stop gating EC2 api-v3 releases on LegBot hand-offs, archive retries or ddp-sync rebuilds (your 900139843 "When" section and the idle-gap wording in bc3054527 said "their LegBot hand-off and session reads go to api-v3"). What I can see on this host agrees with him:
- the broker's **web and celery** have `DDP_OPENSTATES_API_ROOT=http://10.0.0.11:8002` (this host's api-v3);
- **ddp-sync on this host has no setting that names an api-v3 base** (I scanned its settings for api-v3 / openstates API / api_base names);
- api-v3's access log for the last hour shows only health probes and my own release checks (a handful of `/jurisdictions/...` reads);
- LegBot runs on the Mac against the Mac's own api-v3 and replica, never this host's.
So the only things that read EC2's api-v3 are the broker (its bill-update sync, search and `/ddp/enrollment`) and my own checks; a 6 to 8 s restart can at most make one broker call fail and retry. **I also withdraw a sentence of mine:** in my notes about the Nebraska run and the api-v3 timing I wrote that the broker "reads api-v3 when LegBot creates a bill"; I could not confirm that and it should not be used as a gate.

## api-v3 (EC2) at main 3a8d165e (OPEN-557) is live (04:51:19 to 04:52:06 UTC)
- **The gate "idle gap" was not applied, on Ramon's decision after he saw the facts:** at 04:50 UTC ECS had one task (Pennsylvania's collection, `ddp-scrapers:74`, from 04:00), ddp-sync held the locks pa (running) and wa and us (sleeping between archive retries, due about 05:05 and 05:39 UTC), no heavy ddp-sync process, and api-v3 served about 4 requests a minute. He answered **"Yes, now"** to doing it before the 05:00 UTC scorecard chain.
- Checkout 8cef03e, clean; `git log --first-parent 8cef03e4..3a8d165e` = exactly one merge (#72), 4 files (api/current_session.py, api/tests/fixtures.py, test_current_session.py, test_jurisdictions.py) as you said. Running image tagged **ddp-openstates-api:pre-open557** (25ae357e5edf). `git merge --ff-only 3a8d165e53af5c5ff438d856336087eaaf9a7d12` (HEAD confirmed, clean), then `DDP_CORE_SHA=10f32ce08088e544e88d54ec64aa325aea80756f ... up -d --no-deps api`: compose exit 0, 8 s, **down about 8 s, healthz 200 at 04:51:50**.
- **Drift check exit 0** (image, api-v3, ddp-sync loader all 10f32ce0). **Your table, read through the broker's client:** ga current `2025_26` and `2026_ss`, previous `2023_24`; va current `2026` and `2027`, previous `2025`; or current `2026R1`, previous `2025R1`; wa current `2025-2026`, previous `2023-2024`; nm current `2026`, previous `2025`; us current `119`, previous `118`: **all six MATCH**, no rollback. api-v3, ddp-sync and the broker's web: 0 errors afterwards. **Mac half is yours.**

## Your GO 07bde0554: where it stands (nothing started yet)
v72 and the dev's confirmation are the trigger of the user's pre-approval ("Yes, both, when the dev confirms"). **The ddp-sync rebuild (SYNC-181) and then the re-import wait for an idle gap**: ECS empty, ddp-sync idle, **no `ddp:pipeline_lock:*` held** (now pa, wa, us), at least 25 minutes before the next scheduled slot. A waiter watches for it (the likely first gap is after Pennsylvania's scrape and archive, about 11:00 UTC, before Alabama and Georgia at 12:00, or after those). The WA and US archive proofs (05:05 and 05:39 UTC, now from `ddp-scrapers-db:2`) I report as soon as they run.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
