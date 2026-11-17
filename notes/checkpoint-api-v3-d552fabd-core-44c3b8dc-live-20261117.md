# Checkpoint: EC2 api-v3 rebuilt from main d552fabd on core 44c3b8dc (reply to 9d8566db7), all gates pass

Written 03:51 UTC (date -u at write time). From the production EC2 host. The user's word in session: asked whether to run it now or after PA's launch, they chose "Run now".

## Done 03:50:15-03:50:43 UTC
- Checks first: api-v3 main exactly d552fabd8b1ebb659d23138e708fbb35bfc5fd04; core main exactly 44c3b8dc82a0f296b68c3bf2a2e6e2454e5b29b9 (both read with ls-remote).
- api-v3 checkout 306b4f5 -> d552fabd (fast-forward). ddp-open-states stays at 8afea0a1 (tonight's rollout).
- **Rollback tag differs from the GO:** `ddp-openstates-api:pre-306b4f5` already existed on an older image (7de2aed5fcff). I did not overwrite it. The running image 8543c984cbb5 is tagged `ddp-openstates-api:pre-d552fabd`. To roll back: retag pre-d552fabd as :local and recreate api only.
- Build and `up -d --no-deps api` only: compose exit 0, 13 s; healthz 200 before and after; the api answered again after about 6 s down.

## Gates
- Container imports openstates.utils.version_ordering: ok. Health: healthy (read at 03:51:01; it showed "starting" for the first seconds).
- `check-core-pin-drift.py --image-core 44c3b8dc... --container ddp-openstates-api-1`: exit 0. "OK: the scrapers image and 1 api-v3 container(s) all run core 44c3b8dc82a0f296b68c3bf2a2e6e2454e5b29b9."
- Postgres: not touched (this host uses RDS; no database container).
- /ddp/enrollment through the broker: 200, 16 jurisdictions, actions present, newest_first true for none.
- Virginia HB 1432 (2026) versions in the order served: Introduced, Criminal Subcommittee Substitute, Courts of Justice Substitute, Delegate Mehta Substitute (latest = Mehta). Matches.

## Not done
api-v3 #70 and a manifest rollout (not authorized here); no data change; ddp-sync and the broker untouched. At the time: or and ga scrapes still running, PA due at 04:00; nothing failed because of the 6 s api gap that I have seen (I will report if the PA launch read or any step logs an error).
