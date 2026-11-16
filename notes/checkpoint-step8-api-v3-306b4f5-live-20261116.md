# Checkpoint: step 8, api-v3 `306b4f5` LIVE on EC2, all checks pass. 2026-11-16 07:35 UTC (prod agent)

Answers `52fcaf51` (final step 8) and `4cf58cb3`. **User's words in session (pop-up): deploy it "After the scorecard chain (~07:00 UTC)".** It ran 07:32 to 07:34, after the chain ended and after nc and ne had finished.

- **Gates:** scorecard chain ended (0 active); **ddp-sync quiet for 10 minutes** (nc's pipeline ended 07:21:41; quiet read 07:31:54); 0 running `ddp-scrapers` tasks; api-v3 checkout clean at `8214db7`; ddp-open-states checkout at `e38af9c3` (the pull was already done by the state-list rollout `036052a4`). **Your check:** `grep -n ddp-openstates-core.txt deploy/Dockerfile.ddp` finds the `COPY` (line 32) and the `-r` (line 34).
- **Tag:** the running image tagged **`ddp-openstates-api:pre-306b4f5` = `7de2aed5fcff`**; old api log gzipped to `/home/bitnami/ops/log-archive/ddp-openstates-api-pre-306b4f5-*.log.gz`.
- **Pull:** `git merge --ff-only 306b4f5b0b7d6bb3b44c55b5bacc1e408a60f303` (merges #61, #62, #64, #63, #65, #66), HEAD `306b4f5`, clean.
- **Build** (before any restart; live container untouched): 07:32:22 to 07:32:34, **exit 0**, image `8543c984cbb5`; **the pinned core was fetched** (`openstates 6.26.5` installed from the `96445eb26` tarball). pip printed its dependency warnings about the fork's declared versions against api-v3's older locked ones (`chardet`, `pytz`, `scrapelib`, `six`, `textract`, `urllib3`, `pytest`); the pin file says it deliberately leaves them. **Before restarting I tested the new image in throwaway containers (no network, dummy settings):** `openstates.utils.version_ordering`, `.transformers` and `openstates.metadata` import from `/usr/local/lib/python3.9/site-packages/openstates/...`; `api.version_ordering` is gone (as #64 intends); `api.bills` and `api.main` import cleanly.
- **Restart:** `api` service only (`api-deploy.sh`: `up -d --no-deps api`), 07:33:16 to 07:33:27, **down about 5 s**, healthy 07:33:50. Nothing else recreated.
- **Checks (your list):**
  - `docker exec ddp-openstates-api-1 python -c "import openstates.utils.version_ordering as v; print(v.__file__)"` prints **`/usr/local/lib/python3.9/site-packages/openstates/utils/version_ordering.py`** (the same path as your Mac).
  - `/ddp/enrollment` **200, 13 states, `newest_first` us only** (`0c5c944` had run: `036052a4`), 0 `voatz` keys.
  - `/bills?jurisdiction=pa&per_page=1` **200**. A PA bill detail with `include=versions` **200**; the version carries **`is_full_text`, `current_document_id`, `is_bill_version`, `version_stage`** (all present; keys: archived_document_id, archived_updated_at, classification, current_document_id, date, id, is_bill_version, is_full_text, links, note, version_ordinal, version_stage).
  - `/ddp/search?q=education&jurisdiction=pa` **200, 20 results** (SB 315, HB 1505, HB 2167); `q=precondition` **12 results, HB 2625 absent**.
  - **0 tracebacks, errors or 5xx** in the api log since the restart; ddp-sync log: 0 `jurisdiction_manifest_unusable` / `..._disagrees`.
- **Not done, as you said:** `rollout-manifest.sh` (not part of this step), migration 0051's stamping pass, a search rebuild, any other service.
- **Rollback (not needed):** retag `ddp-openstates-api:pre-306b4f5` as `:local` and recreate `api` only.
