# OPEN-351: Utah diff recompute: full-scale rehearsal, and the procedure for the real run on RDS

Date: 2026-10-14. The rehearsal ran against a throwaway copy of a Mac database; nothing live was written. **The real run on RDS has not been done and needs Ramon's explicit authorization** (the ticket says so, and `PLAN-rds-data-quality-backfill.md` §4 is the standing process this follows). Follows OPEN-349 (audit, `notes/open349-utah-version-document-audit-20261013.md`), OPEN-350 and OPEN-361 (openstates-core `14cc6a5`), SYNC-110 (ddp-sync `0f473b1`).

## Answer

`os-text-extract recompute-diff-order ut --commit` does what OPEN-351 needs, with **no code change**. At full Utah scale on a copy of the data it reports `unchanged=5137 corrected=1627 nulled=2607`, takes about half a minute, changes nothing outside Utah, and is idempotent. The expected numbers on RDS are the same, because RDS's Utah data matches (the prod agent confirmed 9,371 / 762 / 6,765 / 2,239 / 368 on 2026-10-14).

## What was rehearsed, and how

- **Substrate.** `CREATE DATABASE openstates_rehearsal_351 TEMPLATE openstates` (11 s, 4.1 GB). `openstates` is the legacy Mac database; its Utah data is identical to the RDS replica's that LegBot reads (same document, note and diff counts). `openstates_dev` was not usable: it holds 24 Utah documents. The scratch copy was dropped afterwards.
- **Code.** openstates-core `14cc6a5` (OPEN-350 and OPEN-361 in), run from the dev checkout's `os-text-extract`, `DATABASE_URL` pointed at the scratch copy. Before running, a snapshot of every Utah document's diff (id, md5, `updated_at`) and a checksum of all 189,931 non-Utah documents were taken inside the copy.
- **Sequence.** dry run, then `--commit`, then a second dry run.

| Step | Output | Time |
|---|---|---|
| Dry run (scratch copy) | `ut: [DRY RUN] 1021 bills checked \| unchanged=5137 corrected=1627 nulled=2607` | 23.5 s |
| Same dry run on the legacy database and on the live RDS replica (read-only) | identical to the line above, both | about 25 s each |
| `--commit` (scratch copy) | `ut: [COMMITTED] 1021 bills checked \| unchanged=5137 corrected=1627 nulled=2607` | 28.6 s |
| Second pass | `ut: [DRY RUN] 1021 bills checked \| unchanged=9371 corrected=0 nulled=0` | |

The commit's counts equal the dry run's, and 5,137 + 1,627 + 2,607 = 9,371, every Utah document.

## What was verified afterwards (independently of the command under test)

A separate script re-implemented the archiver's lineage rules from openstates-core's own `note_stage`, `version_sort_key` and `is_procedural_document`, and compared with what was stored.

| Check | Result |
|---|---|
| Documents nulled / corrected / newly given a diff | 2,607 / 1,627 / **0** |
| `Comparison to …` and `Amended Excerpts …` documents still carrying a diff | **0** and **0** (2,239 and 368 before) |
| Utah documents with a diff | 4,158 (6,765 − 2,607) |
| Independent replay vs stored diffs | disagrees on **0** documents in presence, **0** in text |
| The same replay on the live replica *before* the run | disagrees on 2,607 in presence and 1,627 in text: exactly the dry run's nulled and corrected counts, so two separately written computations agree on which documents are wrong |
| Non-Utah documents changed (diff or `updated_at`), of 189,931 | **0** |
| Utah documents whose `updated_at` changed | **0** |
| Bills with two or more stamped `Amended` versions whose lineage order matches the file timestamps | 73 of 74 (same as OPEN-361) |
| Bills with versions in the lineage sharing a sort key | **0** of 1,021 (471 before OPEN-350) |

**`updated_at` is not bumped** because the command saves with `update_fields=["diff_from_previous_version"]`, so Django's `auto_now` does not fire. That matters operationally: ddp-sync's archive hook (`document_updated_since`) and the knowledge-base ledger both key on `updated_at`, so **this run will not look like new work to either**. Logical replication still carries the change to the Mac replica, because it replicates any updated column.

**The two bills named in the 2026-10-13 report**, after the run (lineage order; each diff's baseline):
- HB 438 (2026): Introduced; `Substitute #1` against Introduced; `#2` against `#1`; `#3` against `#2`; `#4` against `#3`; `#5` against `#4`. All 14 `Comparison to …` documents have no diff. (Before: one real transition of five.)
- HB 8 (2026): Introduced; `Substitute #1` against Introduced; `Enrolled` against `Substitute #1`. Its `Comparison to Original Bill` has no diff.

**What it does for the changelogs.** Running the SYNC-110 rule (ddp-sync `_diff_baseline_index`) over this data, ddp-sync would build **2,042** changelog transitions after the run, **all between two real drafts** (586 consecutive `Substitute` pairs; the report found 6), with 0 skipped for a media-type split. On today's stored data it builds only **606**, and skips **2,968** for a media-type split, because the redline PDFs still sit in the PDF lineage. **So SYNC-111 (regenerating Utah's changelogs) must wait for this run.**

## Procedure for the real run (prod agent, after Ramon's explicit go)

This is `PLAN-rds-data-quality-backfill.md` §4 applied to Utah. The same command was run on RDS for Utah on 2026-09-12/13 (OPEN-224's 563 nulled, 429 corrected).

**Preflight, all read-only; record each result in the `notes/ops-handoff` reply:**
1. **Code revision.** The `os-text-extract` used must include OPEN-350 and OPEN-361. The plan found two installs on the host (`/opt/ddp-open-states/.venv/bin/os-text-extract` and the one bundled in ddp-sync's container, OPEN-248); name which one you use and its commit, and pull openstates-core to `14cc6a5` or later `main` if needed. Check with that install's Python:
   ```python
   from openstates.utils.version_ordering import is_procedural_document as p, version_sort_key as k
   assert p("Utah", "Comparison to Sub #1") and p("Utah", "Amended Excerpts 2/12/2026 10:02:409")
   assert not p("Utah", "Amended 2/12/2026 10:02:409")
   assert k("Amended 2/9/2026 11:02:713", "") < k("Amended 3/3/2026 19:03:587", "")
   print("OK")
   ```
2. **Quiet window.** No Utah scrape, archive or load in flight. Utah's scrape is in the Sunday 02:00 UTC weekly job and its archive runs Mondays 05:00 UTC; stay clear of both.
3. **Rollback point.** A recent automatic RDS backup exists (`infra/rds/README.md`); note its time.
4. **Baseline:** the five-number query (docs, distinct notes, with a diff, comparison, excerpt) = 9,371 / 762 / 6,765 / 2,239 / 368.

**Dry run, then commit:** `DATABASE_URL=<RDS> os-text-extract recompute-diff-order ut --dry-run`, expected `1021 bills checked | unchanged=5137 corrected=1627 nulled=2607`. After the go, the same command with `--commit` must report the same three numbers; then a second `--dry-run` must report `unchanged=9371 corrected=0 nulled=0`. **Never `all`**; name `ut`.

**After:** on RDS, Utah documents with a diff = **4,158**, comparison and excerpt documents with a diff = **0**. Then, on the Mac replica (read-only, I will do this): the same two numbers, the order of a Utah bill's stamped `Amended` versions through the Mac api-v3, and the changelog-transition count (2,042).

**Abort and report, do not commit, if:** the dry run's numbers differ from the above (RDS may legitimately differ a little, but say so and wait); the command errors; the code check fails; or the commit's counts differ from the dry run's.

## Limits of the rehearsal

- **Replication was not rehearsed** (the scratch copy is not a subscriber). The change is a plain `UPDATE` of an existing column on a table that is already replicated (`ddp_bill_version_document`, state ready), so it should flow; the verification above on the replica is what confirms it.
- **RDS timing is unmeasured.** About 4,200 single-row updates ran in about 29 s locally; over the network to RDS expect more, but the same order. Each document is saved on its own, so an interrupted run leaves some bills updated and some not; re-running is safe, because it is deterministic from the stored text.
- **Same-hour ties:** the 1 bill of 74 whose two `Amended` versions share a date and hour cannot be ordered from the note (OPEN-361's documented limit); the run does not change that.
- The expected numbers on RDS are inferred from the replica (a copy of RDS's rows) and the prod agent's matching counts, not from running the command on RDS.
