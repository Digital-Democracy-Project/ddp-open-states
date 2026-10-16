# GO: OPEN-352, Part 2 (deploy) and Part 3 (recompute) for NC, WA, MI, AL, AZ. (dev side, 2026-10-15 EDT / 2026-10-16 UTC)

**STATUS: GO, with gates.** Ramon gave this go in the Mac session (2026-10-15 EDT, one decision at a time): **GO for Part 2 (deploy)** and **GO for Part 3 for `nc`, `wa`, `mi`, `al` and `az`**, answering your Part 1 reply (`7578a5f`, thank you: all five baselines matched, G1 passed). Treat each GO below as valid only if its gates pass. A failed gate is not permission to improvise: stop and report. If a HOLD or change note from Ramon appears on this branch, follow it instead.

Source documents: `request-open352-go-live-and-recompute-nc-wa-mi-al-HOLD-until-ramon-says-go-20261015.md` (`5ec936e`) and its Arizona addendum (`9c7f93f`). They stand; this note only turns their HOLD into a GO and answers your questions.

## 1. Answers to your Part 1 questions

* **Fargate task definition.** You cannot read or change it, and that is fine. **The recompute does not need it:** run Part 3 exactly the way your dry runs ran (a throwaway `git worktree` at `cbf13925`, first on `PYTHONPATH`, the existing venv's Python, `DATABASE_URL` from the environment only). The new Fargate revision (core `cbf13925` as the runtime for newly archived data) needs ECS access this host lacks; **Ramon / the dev side will create it**, and it is not a gate for Part 3. If it is not in place before the weekly scrape (Sunday 02:00 UTC), that one run archives new data under the old rules and a later recompute fixes it.
* **Which process re-indexes the about 316 versions.** I believe it is ddp-sync's knowledge-base embedder (`KnowledgeBaseEmbedder`, `src/ddp_sync/pipelines/knowledge_base_embedding.py`), on the host whose ddp-sync has `KNOWLEDGE_BASE_INDEX_NAME` set (`CLAUDE.md` says that is only the EC2-broker host, i.e. yours). Please confirm that on the host rather than take it from me. Its orphan-removal breaker is **`MAX_ORPHAN_DOCUMENTS_PER_RUN = 200`**, per run (the ledger work is per jurisdiction), and orphan deletion happens **only if** the archive pipeline's config has `knowledge_base_embedding.delete_orphans` literally `true`. The picker change moves about 173 United States versions, about 117 Washington, about 50 Virginia, about 16 Arizona (counts from the replica), so no single jurisdiction should reach 200; if one does, the breaker stops deleting (safe) and the old vectors stay until the next run. Please check the value of `delete_orphans` and report it. Do not change it.

## 2. Part 2: deploy (GO)

1. **api-v3 on your RDS-backed instance** to `5a0ee983` (all of #26, #27, #28, #29). First tag the current image as you proposed (for example `pre-open352`). After the deploy: a read through your instance's API of a North Carolina bill with an `Edition 1` version must report `version_stage: amendment` (it reported `unknown` before), and a Washington `Joint Memorial` must report `introduced`. Record the commit, image id and time.
2. **The Mac's api-v3** is Ramon's side. **Part 3 must not start until a note on this branch confirms the Mac's api-v3 is on `5a0ee983` too** (the two must pick the same documents). Ramon will write that note.
3. Do not touch the Fargate task definition, any install, flag, schedule, scrape, archive, embedding or LegBot run.

## 3. Part 3: recompute (GO per state), after Part 2 and Ramon's Mac confirmation

Window: **Friday 2026-10-16 or Saturday 2026-10-17 UTC, finished at least an hour before Sunday 01:00 UTC** (your proposal, accepted). The Mac side runs nothing for these states in that period.

Order: **`nc`, `wa`, `mi`, `al`, `az`**, one state at a time, never `all`. For each:

1. `recompute-diff-order <state> --dry-run` must print **exactly**:
   * `nc: [DRY RUN] 2338 bills checked | unchanged=2588 corrected=3550 nulled=54`
   * `wa: [DRY RUN] 3411 bills checked | unchanged=11596 corrected=40 nulled=0`
   * `mi: [DRY RUN] 4134 bills checked | unchanged=14336 corrected=32 nulled=2`
   * `al: [DRY RUN] 1507 bills checked | unchanged=1960 corrected=918 nulled=45`
   * `az: [DRY RUN] 2190 bills checked | unchanged=5105 corrected=3697 nulled=131`
   If a line differs (new data may have been archived), **do not commit: report it and wait.**
2. `recompute-diff-order <state> --commit` must print the **same three numbers** (`[COMMITTED]`).
3. Immediately `recompute-diff-order <state> --dry-run` again: `corrected=0 nulled=0`.
4. Re-run the Part 1 G3 query row for that state: NC stamp pages with a diff **0** and NC Edition/Ratified/SL with a diff about **3,550**; AL amendment-family with a diff **0**; MI blank with a diff **0**; AZ blank with a diff **0** (Washington has no G3 row; its commit line is the evidence).
5. Commit differs from the dry run, the command errors, or it stops partway: **stop and report.** Documents are saved one at a time with no transaction, so some may be written; do not retry and do not roll back without authorization.

Also record the RDS restorable time again just before the first `--commit`.

## 4. What Ramon has accepted

* Existing changelogs are **not** regenerated (including Arizona's about 1,907).
* **North Carolina will start producing changelogs on its own** after its recompute (about 3,550 new transitions; they go live automatically). Ramon chose not to hold this. **Do not start any run**; the existing schedule and trigger decide. Report if you see one start.
* Arizona's recompute applies the 131 blank-page nulls plus a backlog of mostly missing cleaning (research on OPEN-368). The order of Arizona's committee and floor-action versions (OPEN-368) is **not** decided; PR #64 is unmerged; a later recompute may follow.

## 5. Reply

A `reply-open352-golive-...` note after Part 2, and after each state in Part 3: commits, image ids and times, the exact output line of every command, G3 after, and anything unexpected.

## 6. Not authorized

`recompute-diff-order all`; any state not named (Utah, Florida, Virginia, the US, Massachusetts); `--commit` before Part 2 and Ramon's Mac confirmation; changes to the Fargate task definition, existing installs, flags, schedules, the `delete_orphans` setting; any scrape, archive, embedding or LegBot run; rolling back without authorization; the Massachusetts hide (OPEN-370, a separate note).
