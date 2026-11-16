# Update to step 8 of `9963ec8`: api-v3 goes to **main `306b4f5`** (not just #61). 2026-11-16 (Mac side)

**Ramon, 2026-11-16 (pop-up): "Deploy current main"** for both api-v3 copies. Step 8 said "ff-only to api-v3 main (#61)". Main has since gained:
* **#62** OPEN-569: Alabama date-first ordering, synced;
* **#64** OPEN-538: version rules now come from openstates-core, pinned in `ddp-openstates-core.txt` to core **`96445eb26`**, the same core as v60. The Dockerfile installs it at build time, **so the build needs GitHub access**;
* **#63** OPEN-558: a test only;
* **#65** OPEN-540: new optional per-version fields on bill detail. The gate is accepted by Ramon ("Accept all");
* **#66** OPEN-577: search orders versions with the state name.

**Checks on the Mac:** the api-v3 suite on main gives 558 passed. The Mac api-v3 has been on `306b4f5` since about 05:25 UTC: healthy; enrollment, bill list and search all 200; NC HB 116 versions carry `current_document_id`, `is_bill_version`, `is_full_text` and `version_stage`; 0 tracebacks.

## What I need from you (step 8, revised)
1. **Gates:** as step 8; after step 7 (Washington) is finished.
2. Tag the running image `ddp-openstates-api:pre-306b4f5`. Run `git merge --ff-only` to **`306b4f5`**, then build. **If the build cannot fetch the pinned core from GitHub, stop and report.** Then `up -d --no-deps api` only.
3. **Checks:**
   * `/ddp/enrollment` 200, newest-first **us only** (after `0c5c944`'s rollout) or us+nc if that hasn't run yet; say which;
   * `/bills?jurisdiction=pa&per_page=1` 200;
   * one bill detail with `include=versions` shows `is_full_text` / `current_document_id`;
   * `/ddp/search?q=education&jurisdiction=pa` 200 with results;
   * 0 tracebacks.

**Rollback:** the tag `pre-306b4f5`.

**Not authorized:** a search rebuild; any other service.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
