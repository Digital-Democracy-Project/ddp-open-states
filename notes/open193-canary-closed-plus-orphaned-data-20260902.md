# OPEN-193 item 4 closed — clean 4/4 canary run — plus one real finding: 123 orphaned objects from tonight's debugging

*Replies to `notes/open248-toolchain-bundled-fix-pr118-20260902.md`.*

## The good news: PR #118 confirmed working, canary closes clean

One more environment gap before it ran, worth recording: this host's Docker (20.10.5) had no
`buildx` plugin at all, so `docker compose build` couldn't satisfy the Dockerfile's
`additional_contexts` requirement (`unsupported frontend capability
moby.buildkit.frontend.contexts`) even after the PAT was added. Installed
`docker-buildx-plugin` (apt, Docker's own repo, already configured) and created a real
`docker-container`-driver builder for both my user and root (systemd runs `ddp-sync.service` as
root, separate buildx registry from a regular user) -- confirmed zero impact on any other
running container (`ddp-broker`/`api-v3` uptimes unchanged throughout).

Rebuilt, verified `os-update --help` runs cleanly inside the container directly, then
re-triggered the full FL canary:

```
{"status": "completed", "sessions": ["2026","2026D","2026E","2026F"], "total": 4, "failed": 0,
 "results": [
   {"success": true, "session": "2026",  "duration_seconds": 223.1, "cloud_run_id": "fl-7aaacd9efe64"},
   {"success": true, "session": "2026D", "duration_seconds": 97.7,  "cloud_run_id": "fl-08efefa30348"},
   {"success": true, "session": "2026E", "duration_seconds": 98.5,  "cloud_run_id": "fl-674854f411f4"},
   {"success": true, "session": "2026F", "duration_seconds": 98.9,  "cloud_run_id": "fl-5f6382899537"}
 ]}
```

**Clean 4/4. Every bug this entire thread found (OPEN-241/242/243/244/245/248, the import-lock
IAM grant, the stale OPEN-187 lock) is confirmed resolved together, for real, on a genuine
end-to-end run.** This should close OPEN-193 item 4.

## The thing worth flagging before calling it fully done: 123 orphaned objects from tonight's own debugging

Wanted to independently verify data actually landed, not just trust the success status -- spot
check via api-v3 showed FL's most recent `updated_at` predates today entirely. Dug in: three
collection runs *from earlier tonight's debugging* found and staged real data, but their load
step failed before the relevant fix had landed yet -- and since collection and load are
separate steps, each of those collections still advanced FL's incremental watermark. This
final clean run correctly found nothing new for any session, because from the watermark's
perspective, this data was already "seen":

| run_id | session | objects found | why the load failed at the time |
|---|---|---|---|
| `fl-1f280053977b` | 2026D | 17 (6 bills, 3 orgs, 7 vote events, 1 jurisdiction) | `openstates_root` mount not yet added |
| `fl-9237033aa89b` | 2026E | 82 | import-lock IAM `AccessDenied` (not yet granted) |
| `fl-c10699ea2180` | 2026F | 24 | import-lock IAM `AccessDenied` (not yet granted) |

All three manifests are still live in S3 (`working-tier/fl/<run_id>/_manifest.json`,
confirmed by direct fetch) -- nothing is actually lost, just not loaded, and not something a
future normal incremental run will rediscover on its own since the watermark has already moved
past this window.

`cloud_loader.py <source> <run_id> [key=value ...]` is a clean, purpose-built interface for
exactly this case -- fetches a manifest by run_id and loads it, no re-scrape needed. Flagging
rather than running it myself: this means writing real data into production RDS based on
intermediate state from a debugging session, and that's a call for whoever owns this data, not
something to do unilaterally. If it's worth recovering: `cloud_loader.py fl fl-1f280053977b
session=2026D`, `cloud_loader.py fl fl-9237033aa89b session=2026E`, `cloud_loader.py fl
fl-c10699ea2180 session=2026F`, run from inside the now-working `ddp-sync` container (or
wherever's most appropriate).

`ddp-sync` is left running, healthy, `cloud_path.enabled: true` / `jurisdictions: ["fl"]` as the
proven-working end state. No further action taken on the orphaned data pending a decision.
