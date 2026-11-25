# checkpoint (done): Arizona canary step 4 (#488): manifest rolled out on EC2 at 02:15 UTC; ddp-sync reads `load_on_fargate` true for az and for no other state

Ramon's go in my session (pop-up ~01:55 UTC "Yes, roll out the manifest"). **Ramon then approved the wider scope explicitly** (pop-up ~02:13 UTC, "Roll out all of it"), because main at 38e5b31 carried more than #488, which I had not described to him until the dry run showed it.

## What the rollout brought (per-state diff of the deployed copy against main, read before the rollout)
- **az:** `scrape.load_on_fargate` false -> true (#488).
- **nm:** status scraping -> **live**, and enrollment search_refresh, embedding, api_smoke_test and qa_sweep false -> true (#480, the PM's merge). **That was not in your request for this step; Ramon approved it in session.** NM's first embedding run will be longer (first pass).
- **ga:** `quality.diff_cleaner` none -> clean_ga_text (#489, OPEN-842). **mt:** diff_cleaner none -> clean_montana_text (OPEN-827). No other state changed (4 states in all).

## The rollout (bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync --skip-ecs-check)
- A first attempt at 01:55 UTC stopped by itself: "within 10 minutes of the 2:00 job". Dry run at 02:11 (valid, agrees), real run at 02:15.
- /opt/ddp-open-states 3d1801a4a -> **38e5b31be**. "OK: 30 jurisdiction(s) valid", "OK: every list compared agrees with jurisdictions.yaml (30 jurisdictions)". NOTE printed: openstates-core was not checked (no --openstates-core-root), so quality.diff_cleaner was not compared with the code. md5 of the checkout file, the api-v3 copy and the file inside the container: **f9af30039095e7d94ce53f4361a1a1b1** (the copy was 513f2dd6... before). api-v3 healthy, no restart, no other change.
- Gate: no az task or run was running (ECS check done by hand: 0 az tasks; no az pipeline lock).

## Checks
- check-core-pin-drift --image-core a7035d68...: exit 0. ddp-sync /schedule: 35 jobs. 0 Tracebacks.
- **ddp-sync's own `state_loads_on_fargate(st, "/opt/ddp-open-states")`: True for az; False for ga, mt, nm, ok, hi, ri, ut, fl.** (It reads the file by modification time, so no restart was needed.) The scrape-block `rds_from_task_secret` is already true since the 01:30 restart; the archive block's stays false.
- Not read: /ddp/enrollment (no key on this host); the three matching md5s and healthy api-v3 stand in, as before.

## Arizona "before" counts (recorded 02:00 UTC, read only; ops/az-before-counts-20261125.txt)
bills 2,190; actions 14,428; versions 4,869; documents 9,186; sponsorships 8,075; vote events 1,760; person votes 75,720.

## Next
- Arizona's first Fargate load is its scheduled run, **Wed 12:00 UTC** (or a manual run on Ramon's go). I will check your pass rules 1-7 for that run_id and report with the evidence I can read from here: the in-flight record's `load_task_arn`, the load task's ECS record (exit code, `RUNNER_SCRIPT`, whether the overrides list DATABASE_URL; I can read ECS stopped-task records but not CloudTrail), the S3 `prod/az/_import_lock` state, and the counts above. Rollback: az back to false in the manifest and roll out; nothing is done without telling Ramon.
