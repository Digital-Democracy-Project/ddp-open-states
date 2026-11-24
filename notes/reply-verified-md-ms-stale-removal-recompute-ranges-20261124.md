# REPLY-VERIFIED to `de1c390`: **the MD and MS stale-document removals are on the Mac replica.** Recompute ranges measured: **Maryland needs none; Mississippi has a range.** 2026-11-24 ~18:10 UTC (Mac side, Onboard New States)

## Verified (Mac replica, read only)
* MD archive documents **5,128** and MS **17,073**: both equal your "after" lines.

## The recompute dry runs, measured on the replica at core `59dbdaa2` (the live core), in a read-only session
| State | Summary lines I got | What it means |
|---|---|---|
| **MD** | `2677 bills checked \| unchanged=5128 corrected=0 nulled=0`; `is_bill_version set=0 changed=0 not_a_version=0`; `diff_baseline_id set=0 changed=0 cleared=0` | **Nothing to recompute.** The re-import already stored the right comparisons. **Skip Maryland's recompute commit.** If you run its dry run anyway, it must show exactly this |
| **MS** | `4014 bills checked \| unchanged=15198 corrected=453 nulled=1422`; `is_bill_version set=0 changed=1429 not_a_version=1429`; `diff_baseline_id set=0 changed=453 cleared=1422` | Amendment papers and amendment reports become not-a-version (core `2013b4a0`'s rule) and lose their comparisons; 453 comparisons are corrected |

* **Mississippi expected range at `59dbdaa2`:** `corrected` 440–470, `nulled` 1,400–1,450, `not_a_version` 1,410–1,450, `set` 0, `cleared` 1,400–1,450, no error. **Stop and report if the dry run is outside it.** The commit waits on Ramon's second go after he has seen your dry-run numbers.
* The 4,014 old "Current version" rows kept by the removal don't take part: they match no current version name.
* **How I measured:** `os-text-extract recompute-diff-order <st> --dry-run` in a read-only database session (`default_transaction_read_only`), core `59dbdaa2` on the path; the list files are on the Mac (`scratchpad/rc/`).

Tickets: OPEN-674, OPEN-669 (OPEN-146).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
