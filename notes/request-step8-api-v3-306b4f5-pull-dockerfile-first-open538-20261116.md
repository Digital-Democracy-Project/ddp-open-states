# Request: step 8 (api-v3 to main `306b4f5`), answers to your `327f774`. **Pull ddp-open-states first**, or the new api builds and then cannot start. 2026-11-16 05:25 UTC (Mac side)

**Ramon, 2026-11-16 (pop-up): "Deploy current main"** for api-v3 (both copies). That is why `4cf58cb` widened step 8 from #61 to main. Your reasons to hold back #62/#64/#65 were good catches. Answers below. **Your timing (after the scorecard chain, about 07:05 UTC) is right. Keep it.**

## What I need from you (step 8, final; replaces `4cf58cb`'s numbered list)
1. **Gates:** as `4cf58cb` (scorecard chain finished, no ddp-sync job line in the last 10 min). api-v3's checkout clean at `8214db7`.
2. **Pull ddp-open-states first:** `git -C /opt/ddp-open-states merge --ff-only origin/main`. This brings #377 (merge `f4731db8`, commit `8852dd6`), which makes `deploy/Dockerfile.ddp` install `ddp-openstates-core.txt`. **Check:** `grep -n ddp-openstates-core.txt /opt/ddp-open-states/deploy/Dockerfile.ddp` finds the `COPY` and `-r` lines. **If it doesn't, stop.** Why: with your checkout's file (`5f945b01`) the build **succeeds**, but the container fails when it starts, because api-v3 #64 deleted `api/version_ordering.py`. Nothing rolls back by itself.
   * This pull also brings `jurisdictions.yaml` with NC labelled oldest first (#380). **Only pull it. Don't run `rollout-manifest.sh` here.** The label rollout is `0c5c944`'s job. If you have already done `0c5c944`, this pull is a no-op.
3. Tag the running image `ddp-openstates-api:pre-306b4f5`. Run `git merge --ff-only 306b4f5` in api-v3, then build. **If the build cannot fetch the pinned core from GitHub, stop.** Then `up -d --no-deps api` only.
4. **Checks (report each):**
   * **`docker exec ddp-openstates-api-1 python -c "import openstates.utils.version_ordering as v; print(v.__file__)"`** prints a path. Use this, not the package version: upstream 6.26.5 carries the same version string. The Mac printed `/usr/local/lib/python3.9/site-packages/openstates/utils/version_ordering.py`.
   * `/ddp/enrollment` 200. Newest first is **us only** if `0c5c944` has run, us+nc if not; say which.
   * `/bills?jurisdiction=pa&per_page=1` 200. One bill detail with `include=versions` shows `is_full_text` / `current_document_id`.
   * `/ddp/search?q=education&jurisdiction=pa` 200.
   * 0 tracebacks since the restart.

## Answers to `327f774`
* **#65 does not need a new column on RDS.** The new model field `diff_baseline_id` is deferred, and api-v3 reads it only after `information_schema` shows it exists (`api/bill_version_flag.py`, `baseline_column_present`, the same guard `is_bill_version` has always used). Without OPEN-539's migration `0051`, api-v3 answers exactly as before. **Mac proof:** the replica has no `diff_baseline_id` column (count 0), and the Mac api-v3 has run `306b4f5` since about 05:25 UTC with enrollment, bill list, bill detail and search all 200, and 0 tracebacks. **Don't apply `0051`; it isn't part of this step.**
* **#62** needs core `96445eb26` or later. #64's pin is exactly that, installed by step 2's Dockerfile.
* **Step 7:** received, thanks. WA at 3,771 inside the gate is accepted. I verify LA/NE/WA on the replica separately.

**Rollback:** the tag `pre-306b4f5`. The ddp-open-states pull needs no rollback for the api: the old api image ignores it.

## Not authorized
* `rollout-manifest.sh` as part of this step.
* Migration `0051`.
* A search rebuild.
* Any other service.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
