# GO (production write): `relabel-non-bills ma --commit --expect 3132` on RDS (OPEN-517). 2026-11-10, about 06:05 UTC (Mac side)

**Ramon's go, 2026-11-10, his word:** "GO". He gave it after seeing the dry-run result in `cf47d71`.

It covers **this one command for Massachusetts, session 194th, once**, plus the read-only checks around it.

## What it does
It relabels the 3,132 Massachusetts papers that are not bills:
* 1,538 become `report`;
* 998 become `communication`;
* 332 become `study request`;
* 264 become `order`.

Each paper's old label is saved in `extras["ddp_open517_original_classification"]`, so `--undo --commit` puts it back.

**Nothing is deleted.** `updated_at` does not move. The website does not change yet.

**Safety built into the command:**
* `--expect 3132` makes it write nothing if the count is anything else.
* Each row is written only if it is unchanged since it was read (same label, same extras, still no vote). Otherwise the whole run rolls back.

## Code
Same as the dry run, `cf47d71`:
* a throwaway `git worktree` of `/opt/ddp-open-states/openstates-core` at exactly **`1459c22e9c54b3f2360e11569d9dbf14b2af18a3`**, first on `PYTHONPATH`;
* the existing venv's Python and `os-text-extract`;
* `DATABASE_URL` from the environment only.

Remove the worktree afterwards, and leave the host's core checkout untouched.

## Gates (all must pass; stop and report if one does not)
* **G1, code:** the same import check as the dry run prints the worktree path, `True` and `ddp_open517_original_classification`.
* **G2, quiet:**
  * no Massachusetts scrape, archive or text extract is running;
  * there was no ddp-sync job for Massachusetts in the last 15 minutes;
  * it is not inside 02:00 to 04:30 UTC.
* **G3, rollback point:** if you can read it, the RDS latest restorable time. The command's own `--undo` is the planned rollback, so if you cannot read it, say so and continue.
* **G4, baseline:** the dry-run baseline SQL (classification counts, total, saved-label count). Expect 9,015 / 2,896 / 11,911 / 0. If a Massachusetts bill was added since, say so and continue: `--expect` guards the count that matters.
* **G5, fresh dry run:** `os-text-extract relabel-non-bills ma --session 194th --dry-run`. It must show `relabelled=3132 already_labelled=0`. **If it shows any other number, stop and report; do not commit.**

## The write
```
os-text-extract relabel-non-bills ma --session 194th --commit --expect 3132 --list /home/bitnami/ops/open517-20261110/relabel-ma-commit.csv
```
Expected first line: `ma: [COMMITTED] relabelled=3132 already_labelled=0 skipped_amendment_paper=158 skipped_has_recorded_votes=8`, then the same seven `old -> new` lines as the dry run.

## After (read-only)
1. **The baseline SQL again.** Expect:
   * `{bill}` 8,440 and `{proposed bill}` 339;
   * `{report}` 1,538, `{communication}` 998, `{study request}` 332, `{order}` 264;
   * total unchanged;
   * saved-label key on **3,132** rows.
2. **`updated_at` did not move:**
   ```sql
   SELECT count(*) FROM opencivicdata_bill b JOIN opencivicdata_legislativesession s ON s.id = b.legislative_session_id
   WHERE s.jurisdiction_id = 'ocd-jurisdiction/country:us/state:ma/government' AND b.updated_at > now() - interval '30 minutes';
   ```
   Expect 0, unless a scrape ran, which it should not have.
3. **A second dry run** shows `relabelled=0 already_labelled=3132`.
4. **Other states unchanged:** the classification counts for any one other state (for example Utah) match a run of the same SQL before the write.

## Please report
* Each gate's lines.
* The exact command output.
* The four after-checks.
* The time of the write (UTC).

## Rollback (only on Ramon's go)
`os-text-extract relabel-non-bills ma --session 194th --undo --commit`, from the same worktree. It restores each saved label and removes the key.

## Not authorized
* `--undo` (unless Ramon asks), or any other state.
* A run without `--session 194th` or without `--expect 3132`.
* A second commit.
* `recompute-diff-order`, a scrape, an archive, a text extract, a refresh, or a LegBot run.
* Pulling the ddp-open-states tip, or changing the host's core checkout or installs.
* Building, registering or deregistering any scrapers image or task definition. **v53 is registered by Ramon after this.**
* Any change to ddp-sync, the broker or api-v3.

## What I check on the Mac side
Once the replica catches up, I check:
* the same counts on the Mac replica;
* that a sample of real bills, and the 8 voted papers, still read `bill`;
* that the Mac api-v3 serves the new labels (`/bills?jurisdiction=ma&classification=report` totals 1,538).

Then I tell Ramon v53 can be registered.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
