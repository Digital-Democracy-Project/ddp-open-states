# REQUEST: OPEN-352, run read-only `recompute-diff-order` DRY RUNS for NC, WA, AZ, MI, AL (Mac side, 2026-10-15 EDT)

**STATUS: dry runs only. Nothing in this note authorizes a write.** Ramon asked (2026-10-15, in the Mac session) for the production agent to run the dry runs and report the counts. The real runs (`--commit`) are a separate step that needs its own go from Ramon, after he has seen these numbers. If a HOLD note from Ramon appears on this branch before you start, follow it instead.

Jira: **OPEN-352** (audit; closed) and the fix tickets **OPEN-365** (blank text), **OPEN-366 + OPEN-371** (North Carolina), **OPEN-367 + OPEN-372** (Alabama), **OPEN-373** (Washington). Arizona's ordering fix (OPEN-368) is NOT merged and not part of this.

## 1. Why

The fixes below are merged but only change data archived from now on. Each state's already-stored `diff_from_previous_version` values change only when `recompute-diff-order` runs for that state (as OPEN-351 did for Utah). Before authorizing that, Ramon wants to see what each state would change. The command's dry run prints `unchanged / corrected / nulled` and writes nothing.

## 2. What code to run (gate G1, same logic as the OPEN-351 note)

The recompute applies **whatever openstates-core it runs on**. Run it on openstates-core `main` at **`cbf13925`** (PRs #61, #62, #63, #65, #66, #67 merged: Alabama exclusion, North Carolina stages and stamp-page exclusion, blank text, North Carolina and Alabama pre-diff cleaners, Washington resolution stages).

As before: **do not pull or change any existing install.** Use a separate checkout at exactly `cbf13925` (for example `git worktree add <new dir> cbf13925` after a `git fetch`, which touches refs only), with that directory first on `PYTHONPATH` and the existing venv's Python and dependencies, and the same `os-text-extract` executable you would use for a real run. Run this in that exact environment; it must print `OK`. It prints where `openstates` came from, which must be the new directory, and `git -C <new dir> rev-parse --short HEAD` must say `cbf13925`:

```python
import openstates
from openstates.utils.version_ordering import (
    is_procedural_document as p, version_sort_key as k, note_stage, STAGE_INTRODUCED)
from openstates.cli.text_extract import _has_text, _clean_nc_text, _clean_al_text
assert p("North Carolina", "A1: Amendment") and not p("North Carolina", "A1: ABR-9-V-1")
assert k("Filed", "") < k("Edition 1", "") < k("Edition 2", "") < k("Ratified", "") < k("SL 2025-14", "")
assert p("Alabama", "Judiciary 1st Amendment") and not p("Alabama", "Judiciary 1st Substitute")
assert note_stage("Joint Memorial")[0] == STAGE_INTRODUCED and note_stage("Resolution")[0] == STAGE_INTRODUCED
assert not _has_text("\n \n") and _has_text("A")
assert _clean_nc_text("  A BILL TO BE ENTITLED\n  Section 1.") == "Section 1."
assert _clean_al_text("SB1\nJPKGJNN-1\nSYNOPSIS:\nx\nA BILL\nTO BE ENTITLED\nAN ACT\nBody.") == "SB1\nBody."
print("OK", openstates.__file__)
```

If it does not print `OK`, stop and report. Do not touch any existing install to get past it.

## 3. The dry runs (read-only; nothing is written)

Use the exact executable and environment from G1. For each state, one command, one at a time:

`DATABASE_URL=<RDS, from the master secret as before; never paste it into a note or log> <that executable> recompute-diff-order <state> --dry-run`

States, in this order: **`nc`, `wa`, `az`, `mi`, `al`**. Name one state per command; **never `all`; never `--commit`.** If a state code is not accepted, report the error and what the command accepts; do not guess a different command.

Please also record the quiet window and that the dry runs were read-only (no Utah or other scrape, archive or load needs to be idle for a dry run, but say if one was running).

## 4. What I expect (Mac side, read-only counts through the replica's api-v3; rough, from OPEN-352's trial comment)

These are expectations to compare against, not gates. A dry run writes nothing, so a surprise is information, not a reason to stop partway.

| State | Fixes that apply | Expect, roughly |
| --- | --- | --- |
| `nc` | stage rules for Edition / Ratified / SL (OPEN-366), `A<n>: Amendment` stamp pages excluded, cleaner (OPEN-371) | **nulled about 53 to 54** (the stamp pages that carry a diff today); **corrected about 3,550** (Edition / Ratified / SL versions with no diff today gain one; the next versions after a stamp page are re-diffed) |
| `wa` | introduced resolution and memorial stage (OPEN-373) | small: **corrected about 20** (substitutes of resolutions gain a diff against the introduced form); nulled 0 |
| `az` | blank pages are not text (OPEN-365) | **nulled about 124 to 131** (blank PDFs carry a whole-document diff today); **corrected** = the next versions after each blank, re-diffed against the last real text |
| `mi` | blank pages (OPEN-365) | **nulled 2**; corrected a few (the version after each) |
| `al` | amendment excerpts excluded (OPEN-367), cleaner (OPEN-372) | **nulled 45**; **corrected** a few hundred: every Introduced to Engrossed (about 232) and Engrossed to Enrolled (about 155) diff changes because the cleaner removes the synopsis, tracking code, title and history lines, plus the versions that followed an excerpt (HB363, HB95, SB361) |

Alabama's scrape is off (data from 2026-06-14), so an Alabama run has no live effect today; the dry run is still wanted for the numbers.

## 5. Reply on this branch

Reply (a `reply-open352-...` note) with: the executable and how the code was provided, the printed `OK` line and `openstates.__file__`, the commit, the exact output line of each of the five dry runs, and the times. If anything stopped you, say what you saw. On the Mac side I will compare the numbers with the expectations above and give Ramon the result before any real run is authorized.

## 6. Not authorized

`--commit` for any state, `recompute-diff-order all`, any other jurisdiction (including Utah, Massachusetts and Arizona's ordering, which is a separate decision), pulling or changing any existing install, any flag or schedule, any scrape, archive or LegBot run, deploying api-v3 (a separate, later step), and the Massachusetts hide (OPEN-370, a separate note). Nothing here is urgent.
