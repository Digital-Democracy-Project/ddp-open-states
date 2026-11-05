# Reply: `recompute-diff-order` for Nebraska and Louisiana, Part 1 (read-only) done. The four dry-run lines match yours exactly. Part 2 (the commit) is NOT run and holds. Written 2026-11-05 01:08 UTC.

Run at the user's go in this session ("Yes, run Part 1 and post the preflight; hold Part 2 (Recommended)", about 01:00 UTC). The dry runs wrote nothing (proved below). No scrape, archive, flag, schedule, restart or other state was touched, and nothing was pulled or changed in the host's openstates-core checkout.

## G1: the code is exactly `978fa96c`
- **Method:** a **throwaway git worktree** of the host's openstates-core clone at `978fa96c49adc3fb6304fccda8237b24caea0cd5` (fetched from `origin`, whose `main` is exactly that commit), put first on `PYTHONPATH`, with the host's own venv (`/opt/ddp-open-states/.venv`) and its `os-text-extract` command, the same method as OPEN-399. I did **not** use the v43 image.
- **Proof:** `git rev-parse HEAD` in the worktree prints **`978fa96c49adc3fb6304fccda8237b24caea0cd5`**; with that `PYTHONPATH`, `openstates.__file__` is `<job scratch>/o486/wt/openstates/__init__.py` and `openstates.cli.text_extract.__file__` is `<job scratch>/o486/wt/openstates/cli/text_extract.py` (the worktree, not the host checkout); migration `0049_billversiondocument_is_bill_version.py` is in that tree. The host's own openstates-core checkout is **untouched at `5c79b47d`**. The worktree is under the job's scratch directory and can be removed after Part 2.
- The database address is read live from Secrets Manager, passed to the command in its environment and replaced by `<DATABASE_URL>` in the saved output; it is never printed.

## G2: rollback point and quiet
- **RDS latest restorable time: `2026-11-05T00:57:45Z`** (instance `ddp-openstates`, backup retention 7 days). I will read it again right before any commit.
- **Quiet at 01:04 UTC:** no ECS task, nothing in flight (the in-flight key is empty), no ddp-sync job in the last 10 minutes; no scrape, archive, load, LegBot relay or backfill that I know of. The ddp-sync scheduler's next run is **02:30 UTC**.
- **Proposed window for Part 2** (only after Ramon's GO note and the user's own go for the state): the daily jobs are the 02:30 and 03:00 UTC runs, **Sunday 02:00** (secondary batch, now including `pa`, `ne`, `la`), and the **archives, one state a day at 05:00 UTC** (`config/sync_schedule.yaml`: Mon fl+ut, Tue az, **Wed wa+va, Thu mi+nc**, Fri ma, Sat al, Sun us). Your note says "the Wednesday archive window", which I read as that 05:00 UTC window on the day. **A clean gap is 03:15 to 04:45 UTC on any day except Sunday** (or 01:15 to 01:55 UTC if it is needed tonight); the commit itself takes seconds, but it updates about 4,000 rows (Nebraska) and 8,500 (Louisiana) streaming to the Mac. Tell me which you prefer.

## G3: baselines on RDS (read-only, the query from your note)
| state | docs | flag_null | flag_false | with_diff |
|---|---|---|---|---|
| Louisiana | **10,468** | **10,468** | **0** | 7,772 |
| Nebraska | **3,382** | **3,382** | **0** | 1,535 |
As expected: Nebraska 3,382 all null; Louisiana 10,468 all null; 0 false. `ddp_bill_version_document` total **224,112**; flags set anywhere in the table **0**.

## The four dry-run lines (`recompute-diff-order ne --dry-run`, then `la`; each exit 0; full output in `notes/recompute-ne-la-20261105/dryrun-ne-output.txt` and `dryrun-la-output.txt`)
```
ne: [DRY RUN] 1847 bills checked | unchanged=1955 corrected=637 nulled=790
ne: [DRY RUN] is_bill_version: set=3382 changed=0 not_a_version=790
la: [DRY RUN] 2599 bills checked | unchanged=6318 corrected=919 nulled=3231
la: [DRY RUN] is_bill_version: set=10468 changed=0 not_a_version=3328
```
**Identical to your expected lines, character for character.** After the dry runs I read the baseline again: **0 of 224,112 flags set**, Nebraska and Louisiana counts and `with_diff` unchanged (1,535 and 7,772). Ran 01:04:41 to 01:05:06 UTC (about 25 seconds for both).

## What I will not do without more
Part 2 is not authorised yet: it needs **Ramon's GO note for the state on this branch** and **the user's own go in my session**, Nebraska first and Louisiana only after Nebraska is verified. I have not asked the user for the commit.
