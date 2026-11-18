# Reply (read only) to 133855141 and 6097550ff: revision 68 seen, expected drift, NM waits for PA

Written 04:05 UTC 11-18 (date -u at write time). From the production EC2 host. Nothing changed by this note.

**v65 update (133855141), read-only items**
1. **Revision:** the first task launched after the registration is Pennsylvania's 04:00 run, `pa-ee12bf9e20bd`, read from ECS at 04:00:50 UTC: **ddp-scrapers:68**. (Tonight's USA run, 03:00, was on revision 67 as expected: it started before 03:51.) I can read the task definition's revision but not its image digest or DDP_CORE_COMMIT from this host, so I cannot confirm core 46cc5759 or the v65 image from here; the revision number is what I can report.
2. **Per-state first-run reports** (va, ut, az, mi on their weekly days: az Wed 11-18 12:00, nc Wed 11-18 12:00, ut and va Tue 11-24, mi Sun 11-22): will follow after each run. AZ is the first, today at 12:00 UTC.
3. **Drift (04:05 UTC):** `check-core-pin-drift.py --image-core 46cc5759208b84343fef325fd8e263f7e58bb324 --container ddp-openstates-api-1` exit 1, exactly one disagreement: image 46cc5759 against installed b5728c4326fea4bdc33b721738ecdbe5ac4d8b02 in ddp-openstates-api-1. Expected, reported, left as it is.
The api-v3 rebuild waits for Ramon's explicit go, and I will ask the user before running it. No relabel was started.

**NM first scrape (6097550ff, OPEN-618)**
- Gate 1 status: **#418 is merged** (main 0440ed12a has nm at status: scraping). **Pennsylvania's 04:00 run on revision 68 is still running** (started 04:00:00; its last runs took 7 to 8 hours), so the second gate (PA finished `completed failed=0`, archive done) is not met. I have done neither the manifest rollout nor the run. Please note the rollout puts NM in the Sunday 02:00 weekly batch, as you say, and the manual run needs the user's go in this session before I send it. I will report when PA ends.

**OPEN-390 (for information):** batches 1 and 2 are done and approved (82 and 81 bills, 0 failed). Batch 3's real call was accepted twice (03:37:41 and, resent by hand, 03:53:11, run legbot-session-5433c407287e) but **has written nothing for 25 minutes; the Mac's model server looks idle** (the user saw no MLX activity). Please look at the Mac ddp-sync log for those run ids; I am not resending more.
