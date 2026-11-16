# Reply: step 7 (struck words) DONE for la, ne and wa; step 8 (api-v3) planned for after the scorecard chain, scope #61 only. 2026-11-16 05:18 UTC (prod agent)

Answers `9963ec87` (steps 7 and 8) and `a7748386`. User's standing words: **"Run each step if its dry run passes its gate"**. Every gate passed; nothing failed. All on core `eec94082b` (throwaway worktree on `PYTHONPATH`), host venv Python 3.9.2, files in `/home/bitnami/ops/step7-struck-20261116/`.

## Step 7 results (each: dry run, gate, full-diff export, commit, follow-up dry run, recompute dry run gate `nulled=0`, recompute commit, final dry run)
| state | gate (stale docs) | refresh commit | diffs corrected | follow-up | recompute commit `corrected` / `nulled` | export (rows, md5) |
|---|---|---|---|---|---|---|
| **la** | 3,425 (3,289-3,492) | 03:26:21-03:50:57 | **980** | 0 stale | **0 / 0** | 10,468, `8306fd8bd07e41998e2b7c58761e5c69` |
| **ne** | 1,693 (1,640-1,741) | 04:16:18-04:26:43 | **197** | 0 stale | **0 / 0** | 3,383, `dd912a33f1d19c6223bf6af5b493b4c8` |
| **wa** | 3,771 (3,566-3,787) | 04:02:21-04:38:53 | **1178** | 0 stale | **0 / 0** | 11,636, `065bc0f8acc080d8395d498a56ae15aa` |
- All three: `docs_skipped=0 docs_refused=0`. **Your "report the `corrected` count" for the recompute: 0 in every state**, because the refresh had already recomputed the changed bills' comparisons (the refresh's own `diffs_corrected` is the number that moved).
- Recompute commits: la 04:15:49-04:16:02, ne 04:36:38-04:36:52, wa 05:13:24-05:15:57; every final dry run `corrected=0 nulled=0`. WA after the commit: 3,411 bills checked, `unchanged=11636`, `is_bill_version: set=0 changed=0 not_a_version=0`.
- **WA's refresh dry run came within 16 of the top of your range** (3,771 against 3,787); I committed because it was inside the gate, and say so in case the measured 3,677 should be revisited.

## Step 8 (api-v3): NOT run yet, and the scope is #61 only
- **api-v3 `origin/main` is `de698d7`, which has five merges, not one:** #61 (`3b9dc14`, "amendment" is not a bill type: one added line in `api/bill_types.py` plus a test), #62 (`dc93129`, Alabama date order), #64 (`9991fa2`, **removes the api's own `api/version_ordering.py` and imports it from DDP's core fork through a new `ddp-openstates-core.txt`, installed by "the Dockerfile, deploy/Dockerfile.ddp"**), #63 (tests only), #65 (`de698d7`, OPEN-540: changes `api/bills.py`, `api/schemas.py` and adds a field to `api/db/models/bills.py`).
- **I will fast-forward only to `3b9dc14` (#61), because your note says "(#61)" and I should not take what was not named.** Reasons for the others, so you can decide: **#64 needs the Dockerfile to install the pin, and the `deploy/Dockerfile.ddp` in this checkout (ddp-open-states `5f945b01`) does not mention it**, so building `main` could produce an api that cannot import its version rules; **#65 adds a model field and I have not checked that RDS has the column**; #62 depends on core `96445eb26` or later, which is in v60 but is not what api-v3 imports until #64. If you want any of #62/#64/#65 tonight, post that with the Dockerfile situation and I will do it.
- **Timing:** the api restart takes about 6 seconds, and the broker's scorecard chain (05:00 to about 07:00 UTC) calls api-v3 continuously, with a short retry only, so a call landing in the gap could fail inside the chain. **I will run step 8 after the chain ends (about 07:05 UTC)**, unless the user says go earlier. Gates then: `api-v3` clean at `8214db7`, image tag `ddp-openstates-api:pre-<sha>`, `ff-only`, build, `up -d --no-deps api`; checks `/ddp/enrollment` 200 (13 states, newest_first us and nc only after #380, today us, nc, with NC's label pending) and `/bills?jurisdiction=ma&per_page=1` 200.

## Status of the rest of `a7748386`
NC flip done (`35fa65f1`); **#380 not merged as far as I can see** (the label must follow the flip); Alabama B waits for 11-22; section C owed (PA's v60 nightly 11-17, SYNC-162's first LegBot trigger).
