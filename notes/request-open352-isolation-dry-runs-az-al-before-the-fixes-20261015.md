# REQUEST: OPEN-352, two more read-only dry runs to explain Arizona's and Alabama's "corrected" counts (Mac side, 2026-10-15 EDT)

**STATUS: dry runs only. Nothing in this note authorizes a write.** Ramon asked (2026-10-15, Mac session) for these. Thank you for the five dry runs (`reply-open352-recompute-dry-runs-nc-wa-az-mi-al-20261015.md`): nulled counts matched for all five states; North Carolina (3,550), Washington (40 = 20 versions x 2 documents) and Michigan (32) are explained. Two numbers are not:

- **Arizona corrected = 3,697** (nulled 131 matched). The blank-page fix explains only the 131 and the version after each.
- **Alabama corrected = 918.** Plausible (the new cleaner changes every pair that involves an Introduced version), but not verified.

The question this answers: **is the large "corrected" number caused by the fixes we merged, or is it older drift in stored diffs that any recompute would pick up?** Same command, run on the code from *before* the fixes, answers it.

If a HOLD note from Ramon appears on this branch before you start, follow it instead.

## 1. The code to run

Same method as the last request (separate `git worktree`, existing installs untouched, existing venv's Python on `PYTHONPATH`).

**Run A (the main test): openstates-core `14cc6a5`.** That is `main` before any of the OPEN-352 fixes (it contains the Utah fixes OPEN-350/361, which do not touch Arizona or Alabama). Preflight, in that exact environment; it must print `OK` and `openstates.__file__` must be the new directory, `git -C <dir> rev-parse --short HEAD` = `14cc6a5`:

```python
import openstates
from openstates.utils.version_ordering import is_procedural_document as p
assert p("Utah", "Comparison to Sub #1") and not p("Utah", "Amended 2/12/2026 10:02:409")
assert not p("Alabama", "Judiciary 1st Amendment")          # Alabama fix (OPEN-367) NOT present
try:
    from openstates.cli.text_extract import _has_text        # blank-page fix (OPEN-365) NOT present
    raise SystemExit("WRONG CODE: _has_text exists")
except ImportError:
    pass
print("OK", openstates.__file__)
```

Same executable and `DATABASE_URL` handling as before (environment only, masked, never written).

## 2. The dry runs

Run A (`14cc6a5`), one state per command, nothing else:

`... recompute-diff-order az --dry-run`
`... recompute-diff-order al --dry-run`

Report the exact output lines. For comparison, at `cbf13925` they printed `az: [DRY RUN] 2190 bills checked | unchanged=5105 corrected=3697 nulled=131` and `al: [DRY RUN] 1507 bills checked | unchanged=1960 corrected=918 nulled=45`.

**How to read it (so we agree before the result):**

- Arizona at `14cc6a5` shows **corrected about 3,6xx and nulled 0**: the corrected number is **older drift, not caused by the fixes**. Report it; stop; Ramon decides whether an Arizona recompute should also apply that backlog.
- Arizona at `14cc6a5` shows **corrected near 0**: one of the merged fixes causes it. Then do **Run B**.
- Alabama: the same reading. `al` at `14cc6a5` should print **nulled 0**; corrected is expected to be much smaller than 918 (the cleaner, OPEN-372, is what adds to it), which would explain the 918.

**Run B (only if Arizona at `14cc6a5` is near 0):** openstates-core **`fe868e7b`** (`14cc6a5` plus Alabama's exclusion #61 and the blank-page fix #63; nothing else). Preflight must print `OK`, and `_has_text` must be importable. Run `recompute-diff-order az --dry-run` only. If it prints about 3,6xx, the blank-page change (OPEN-365, `_has_text` in the baseline logic) causes it and Arizona stays on hold; if not, the cause is in a later merge and Ramon and I will look. Do not go further.

Record the quiet window and that the runs were read-only, as before.

## 3. Reply on this branch

A `reply-open352-isolation-...` note with: the commit(s) used and how provided, each preflight's printed `OK` line and `openstates.__file__`, the exact output line of each dry run, the times, and that the temporary directories were removed.

## 4. Not authorized

`--commit` for any state, `all`, any other state or commit, pulling or changing any install, any flag or schedule, any scrape/archive/LegBot run, deploying api-v3, and the Massachusetts hide (OPEN-370). Nothing here is urgent.
