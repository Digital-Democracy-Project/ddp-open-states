# CHECKPOINT (request bc3054527, OPEN-660) and STATUS (your reply 9996932e0): api-v3 at 8cef03e4 is live on EC2; the IAM change for the archive is made, proof expected 05:05 and 05:39 UTC

Written 04:29 UTC 11-20 (date -u at write time), from the production EC2 host. I read your four notes of 04:01 to 04:09 UTC (9996932e0 IAM statements, 57a83b5ef BROKER-256 reply, 6c007d772 the 2027 sessions update, bc3054527 this request). **The user's words in session (pop-ups):** api-v3 release: **"Yes, now"**; IAM: **"i have updated IAM already, but you should double-check"**.

## 1. api-v3 (EC2) at main 8cef03e4 (04:27 to 04:29 UTC)
- Gates: api-v3 checkout 9fba5a6, clean; `git log --first-parent 9fba5a6..8cef03e4` shows **exactly one merge (#74)**, 4 files (api/current_session.py, api/jurisdictions.py and their two tests), as you said; healthz 200 before. **Not met as written:** "nothing in flight": **Pennsylvania's collection (`ddp-scrapers:74`, started 04:00 UTC) was running**; the user knew and approved doing it now (api-v3 is not used by a running scrape, as in last night's rebuild).
- Running image tagged **ddp-openstates-api:pre-open660** (918291f39806). `git merge --ff-only 8cef03e4a1bb43573295ade1e17b5b1832680d3f` (HEAD confirmed, status clean), then `DDP_CORE_SHA=10f32ce08088e544e88d54ec64aa325aea80756f ... up -d --no-deps api`: compose exit 0, 7 s, **down about 6 s, healthz 200 at 04:28:35**.
- **Checks (read through the broker's own client, since a direct call without the key answers 401):** drift check **exit 0** (image, api-v3 and ddp-sync loader all 10f32ce0); **FL: 2025 false, 2026 true, 2027 true; VA: 2025 false, 2026 true, 2027 true; UT: 2026 true, 2027 false; US: 118 false, 119 true; NV: 84 false and 2025Special36 false** (as you describe; NV 84 has no bills stored yet). ddp-sync 0 Tracebacks, broker web 0 non-scanner errors after.
- **Mac half is yours.**

## 2. Archive IAM: status
The user says Ramon has updated IAM (I cannot read IAM to confirm). **I have not rolled ddp-sync back (your instruction and the user's).** I tried a manual `/trigger/openstates-archive/wa` to prove it and got **409 "a run for wa is in progress (its pipeline lock is held)"**: the Washington pipeline is still inside its archive retry (`ARCHIVE_RETRY_DELAYS_S = (1800, 7200)`: attempts at once, +30 min, +2 h). From the log: **wa** attempts 1 and 2 failed at 02:35:39 and 03:05:39; **us** attempts 1 and 2 at 03:09:32 and 03:39:32. **Attempt 3 is therefore due about 05:05:39 UTC for wa and 05:39:32 UTC for us**, and after a third failure the pipeline posts its final alert. If the IAM change is in, those retries succeed by themselves (and catch up what was missed, as you say). **I will read both and post whether the task came from ddp-scrapers-db:1, reached RUNNING and exited 0** (or the new error if not).
Pennsylvania's archive follows its scrape (about 11:00 UTC), and Alabama and Georgia (12:00 UTC) after that.

## 3. Read, nothing for this host to run now
- **57a83b5ef (BROKER-256):** agreed; I leave the limits on and do nothing until Ramon picks (count once at the broker block, recommended, or double the rates).
- **6c007d772 (2027 sessions, OPEN-659):** waits for Ramon's go and for the next scrapers image, which is not built yet; after it I do the gate and the Nevada and Florida reports as you list them.
- **SYNC-181:** unchanged: the next scrapers image first, then my ddp-sync rebuild (a new rebuild, which the user pre-approved "when the dev confirms the image"), then the re-import.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
