# GO: OPEN-381 Parts 2 and 3, deploy api-v3 `ba0b6468` and recompute Arizona (written by the Mac session at Ramon's instruction, 2026-10-16)

**Ramon said GO for Part 2 and Part 3 of `request-open381-arizona-final-recompute-HOLD-until-ramon-says-go-20261016.md` (`dc6da59`).** Thank you for Part 1 (`reply-open381-preflight-part1-read-only-az-dry-run-20261016.md`).

## Conditions, all met
* Your dry-run line `az: [DRY RUN] 2190 bills checked | unchanged=6934 corrected=1982 nulled=17` equals the Mac's line from its replica with the same code. **That line is the gate.**
* The Mac's api-v3 is on `ba0b6468` (`1ad153c`, `6dcf3f3`).
* `ddp-scrapers` revision 38 (image v35, core `53feef5b`) is registered (`reply-open381-fargate-v35-revision-38-registered-20261016.md`).

## What to do, in order, as written in `dc6da59` Parts 2 and 3
1. **Part 2:** tag the current api-v3 image `pre-open381` (rollback), `git pull --ff-only` in `/opt/ddp-open-states/api-v3` to `ba0b6468`, build and swap only the `api` container, check. Then an Arizona bill (for example `HB 2014`, 2026 2nd regular) must list `House Engrossed Version` after `HOUSE - Natural Resources, Energy & Water` and `HOUSE - Appropriations` and before `SENATE - Natural Resources`.
2. **Part 3:** record the RDS latest restorable time just before. Quiet host (no scrape, archive or text-extract). Same temporary worktree at exactly `53feef5bdde1f277195719a9144f88f6c38fe4dc` and the same gates as Part 1:
   * `recompute-diff-order az --dry-run` must print **exactly** the line above. If it differs, stop and report.
   * `recompute-diff-order az --commit` must print the same three numbers.
   * A second `--dry-run` must print `corrected=0 nulled=0`.
   * Recheck: failed-amendment documents with a diff **0** (was 16); blank documents with a diff **0**.
3. Remove the worktree afterwards.

Do it any time before **Sunday 2026-10-18 01:00 UTC**, and finish the recompute at least an hour before that mark.

## Stop conditions
If the commit differs from the dry run, errors, or stops partway: stop and report. No retry and no rollback without authorization.

## Reply
A `reply-open381-part2-part3-...` note: the api-v3 deploy result and the Arizona version-order check, the restorable time, the three lines (dry run, commit, second dry run), the recheck numbers, times, and that the worktree was removed.

## Not authorized
Any state but Arizona, `recompute-diff-order all`, any flag or schedule change, any scrape, archive, embedding or LegBot run, changes to existing installs or the Fargate task definition, `delete_orphans`, rollbacks without authorization, and the regeneration of Arizona's summaries (OPEN-383, a separate GO).
