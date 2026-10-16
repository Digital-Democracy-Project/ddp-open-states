# REQUEST: OPEN-381, Arizona's second recompute-diff-order. Part A is a read-only dry run (OK now); everything that writes or deploys is HOLD until Ramon says go (Mac side, 2026-10-16)

**STATUS: Part A is read-only. Part B is HOLD. Nothing in this note authorizes a write, a deploy, or a commit until a separate GO note from Ramon appears on this branch.** If a HOLD or GO note from Ramon appears here first, follow it instead.

Thank you for Part 3 (`reply-open352-golive-part3-recompute-nc-wa-mi-al-az-done-20261016.md`): its Arizona line (`corrected=3697 nulled=131`, second dry run clean) is the starting point of this one.

## Why a second Arizona run

Three more Arizona fixes merged after the code Part 3 ran (`cbf13925`). All three change which version each Arizona diff is taken against, so stored diffs need one more `recompute-diff-order az`:

* OPEN-368: committee and floor-action versions (`HOUSE - ` / `SENATE - `) ordered by the site's document number (openstates-core #68, api-v3 #30).
* OPEN-379: failed floor amendments (`... flr amend (...) failed`, 16 versions) no longer take a diff and are not a baseline (core #69).
* OPEN-382: House/Senate Engrossed Versions placed among the action documents by the bill's origin chamber (core #70, api-v3 #31). Measured against azleg.gov's own document ids on 605 bills: backward pairs 1,182 -> 40.

Merged heads: openstates-core `main` = `53feef5b`; api-v3 `main` = `ba0b6468`.

## What the Mac side expects (read-only dry run, Mac replica, new code)

On the Mac's copy of the production replica (`openstates_rds_repl_20260911`, which already shows Part 3: 0 blank pages with a diff, newest write 2026-10-16 03:14 UTC) with core `53feef5b`:

`az: [DRY RUN] 2190 bills checked | unchanged=6934 corrected=1982 nulled=17`

Breakdown of the 1,982 "corrected": 1,247 action documents, 658 Engrossed versions, 82 Chaptered (their predecessor changed), 4 Conference Committee, 8 other. Breakdown of the 17 "nulled": the 16 failed-amendment documents, plus 1 explained one: SR 1036's `SENATE - Kavanagh flr amend (ref Resolution) adopted` is now the first version in that bill's lineage (the bill has no Introduced Version), so it has nothing to diff against. The Mac numbers matched your numbers exactly for the five states last time; the same is expected here, but your line is the one that counts.

## Part A (OK now, read-only): the dry run on production

Same method as Part 3: a separate throwaway `git worktree` of `/opt/ddp-open-states/openstates-core` at exactly `53feef5bdde1f277195719a9144f88f6c38fe4dc` (`git -C <dir> rev-parse HEAD` must print it), first on `PYTHONPATH`, the existing venv's Python and `os-text-extract`, `DATABASE_URL` from the environment only (never printed). Existing installs untouched; remove the worktree afterwards. Preflight, in that environment; it must print `OK` and `openstates.__file__` must be inside the new worktree:

```python
import openstates
from openstates.utils.version_ordering import is_procedural_document as p, origin_chamber, version_sort_key as k
assert p("Arizona", "SENATE - Ortiz flr amend (ref Bill) failed")              # OPEN-379
assert not p("Arizona", "SENATE - Ortiz flr amend (ref Bill) adopted")
assert origin_chamber("HB 2014") == "house" and origin_chamber("SCR 1049") == "senate"      # OPEN-382
assert k("HOUSE - Education", "", [], "house") < k("House Engrossed Version", "", [], "house") < k("SENATE - Government", "", [], "house")
assert k("HOUSE - B", "", ["https://apps.azleg.gov/BillStatus/GetDocumentPdf/9"]) < k("HOUSE - A", "", ["https://apps.azleg.gov/BillStatus/GetDocumentPdf/10"])   # OPEN-368
from openstates.cli.text_extract import _has_text                                # OPEN-365
print("OK", openstates.__file__)
```

Then, quiet host (no scrape/archive/text-extract process), one command:

`... recompute-diff-order az --dry-run`

Report the exact output line and the time. **Before** it, record the G3 numbers for the "after" comparison: Arizona blank pages with a diff (expect 0), and Arizona documents whose note ends in `failed` with a diff (expect 16; it should be 0 after a commit).

**How to read it:** the line equals the Mac line above, `corrected=1982 nulled=17`: report it and stop; the commit waits for the GO. A different line: report it and stop; do not commit, Ramon and the Mac side will compare.

## Part B (HOLD until a GO note from Ramon): deploy and commit

Only after a separate GO note on this branch:

1. **api-v3 `ba0b6468` on your instance** (it sorts the `versions` array too, so API order must match the stored diffs). The Mac's own api-v3 and the new `ddp-scrapers` image/revision from `53feef5b` are the Mac side's and Ramon's to do, and the GO note will say when they are confirmed.
2. The commit: `recompute-diff-order az --commit` on the same worktree and gates as Part 3 (record the RDS latest restorable time just before; one state; never `all`), then a second `--dry-run` that must print `corrected=0 nulled=0`, then the G3 recheck (failed-amendment documents with a diff: 0; blank pages with a diff: still 0).

## Not authorized

`--commit` or any deploy before the GO note, `all`, any other state, any flag or schedule change, any scrape/archive/embedding/LegBot run, changes to existing installs or the Fargate task definition, and the regeneration of Arizona's summaries (OPEN-383, a separate decision).

## Reply on this branch

A `reply-open381-...` note with: the commit used and how provided, the preflight `OK` line and `openstates.__file__`, the G3 numbers, the exact dry-run line and its time, and that the worktree was removed.
