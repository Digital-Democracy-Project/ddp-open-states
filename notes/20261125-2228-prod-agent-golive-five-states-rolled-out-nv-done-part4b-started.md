# checkpoint (done): go-live of HI, RI, ND, KY (#494) and MO (#495) rolled out on EC2 at 22:27 UTC; NV re-import done; Part 4b (ME, MD, MS second passes) STARTED 22:22:09 UTC

Ramon's gos in my session: pop-up ~22:20 "Go" for Part 4b; pop-up ~22:25 **"Yes, all five"** for the go-live (he saw that main carried #495 too, the dry run showing five states and nothing else, and named both notes by their PRs).

## Go-live rollout (requests ecaa7ea and 2fedcb1; `bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync --skip-ecs-check`)
- **Gate read before rolling out (per-state diff of the deployed copy against origin/main):** exactly **hi, ky, mo, nd, ri**, each `status scraping -> live` and `embedding`, `search_refresh`, `api_smoke_test`, `qa_sweep` false -> true; **no other state changes.** (origin/main had both #494 `7ca0b1ce` and #495 `020b5606e`; the script pulls all of main.) ECS gate checked by hand: 0 tasks for these five states.
- Dry run (22:23 UTC, nothing changed): valid, "every list compared agrees (30 jurisdictions)". Real run 22:27:44: /opt/ddp-open-states 38e5b31be -> **020b5606e**; "OK: 30 jurisdiction(s) valid"; "every list compared agrees"; md5 of the checkout file, the api-v3 copy and the file inside the container all **9f417e8d1d621a8b9565f6db0a65c80f** (the copy was f9af3003... before); api-v3 healthy, no restart. NOTE printed: openstates-core was not checked, so quality.diff_cleaner was not compared with the code.
- Checks: **check-core-pin-drift exit 0** (all on a7035d68); ddp-sync /schedule **35 jobs**; ddp-sync's own read of the manifest: hi, ri, nd, ky, mo each `status live`, embedding / search_refresh / smoke / qa True, **replica_routing False, legbot_replica False**, `state_loads_on_fargate` False; **az is still the only True**; nm unchanged (live, replica on). 0 ddp-sync Tracebacks.
- Watch to come: the first embedding and search-refresh passes for the five states (HI 6,728 bills, MO 3,161, RI 3,011, KY 1,737, ND 1,106) in ddp-sync's process; **no ddp-sync restart while a state holds a pipeline lock with no collection task** (my narrow rule); smoke test and QA sweep results by state. I will post when each finishes.

## Part 4: Nevada DONE; AL and AZ still collecting
- **NV (v95, rev 97):** session 2025Special36 collection done 21:55:36, load done 21:55:46 (312.9 s); session 84 collection done 22:16:32, load done 22:16:47 (1,260.5 s); archive 121.2 s at 22:18:50; `openstates_pipeline: done archived=True duration_seconds=1697.3 failed=0 sessions=2 status=completed`. Your pass lines are yours to read; its recompute dry run (and, on a second go, the commit) is next.
- AL (2026rs, since 21:50:32) and the AZ full load (since 21:37:04) collecting.

## Part 4b: started 22:22:09 UTC, all on **ddp-scrapers:97, v95** (describe-tasks at +25 s)
- `me?full=true&sessions=132R1,132R2,132S1`, `md?full=true&sessions=2026,2026s1`, `ms?full=true&sessions=2026,20261E`: all 202, "full": true. Fresh launches (not resumed), so each should archive and run its follow-ups itself. Host before: load 1.33 / 0.94 / 1.16, 7.3 of 15.7 GB. Your pass lines are yours.
- Read edcd8bc, 36bcd77 (NV verified, recompute numbers measured) and 2fedcb1: thanks.
