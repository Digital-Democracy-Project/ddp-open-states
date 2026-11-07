# Request: `recompute-diff-order ma --flags-only` on RDS (OPEN-498). **Part 1 (read-only dry run) now. Part 2 (the commit) HOLDS until a note from Ramon on this branch says GO for `ma --flags-only`.** Replaces the Massachusetts part of `b51597b`. 2026-11-07 (Mac side)

Reply to `39723c1` (your dry run stopped on `nulled=291`) and my `0b4fe09`. **The switch exists now and is live.**

**Code.** openstates-core fork `main` **`138fa3df`** (PR #85, `--flags-only`, on top of the title rule `250de777`). Image **`ddp-scrapers:v48`**, digest `sha256:0fbc5f7d155c462fe04135477c553c716a5d1635140a4d83d8bc14938aa345d0`, **task-definition revision 50** (registered by Ramon 2026-11-07 about 05:00 UTC; the revision before it was 49 on v47, which the OPEN-500 session registered). v48 carries OPEN-500 (PA, NE and LA scrapers accept `start=`) as well. In the image I checked: `recompute-diff-order --help` lists `--flags-only`; the Pennsylvania scraper signature has `start`; the Utah smoke scrape passed. **Pennsylvania's next nightly (04:00 UTC 11-08) will therefore run v48 / revision 50**; please read the launch as you did before.

**What the switch does.** It sets and corrects only `is_bill_version`; it never computes or writes a diff (the query-level test shows no UPDATE names the diff column). Its first output line reads `ma: [DRY RUN] N bills checked | diffs untouched (--flags-only)`; there is no `unchanged=`, `corrected=` or `nulled=` on it. This keeps Ramon's OPEN-370 rule (2026-10-15): the 291 stored Massachusetts diffs are the only record of which bill became which law and are never nulled.

## 1. Part 1: read-only (do now)
1. **G1 (code).** The environment you run from carries `138fa3df` (or is the v48 image); say which, with the proof. The flag must appear in `recompute-diff-order --help`. **Do not run the command without `--flags-only`.**
2. **G2 (quiet).** The same gates as before (RDS restorable time, nothing in flight, clear of 02:00, 02:30, 03:00 UTC and the Saturday 05:00 archive). Last time's dry run was 39 seconds; report this one's.
3. **G3 (baseline, read-only)**, the query from `b51597b` for Massachusetts, **plus this line**, so the diffs can be shown unchanged afterwards:
```sql
SELECT count(*) FILTER (WHERE d.diff_from_previous_version IS NOT NULL) AS with_diff,
       md5(string_agg(d.id::text || ':' || md5(d.diff_from_previous_version), ',' ORDER BY d.id)
           FILTER (WHERE d.diff_from_previous_version IS NOT NULL)) AS diff_fingerprint
FROM ddp_bill_version_document d JOIN opencivicdata_bill b ON b.id=d.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id=s.jurisdiction_id WHERE j.name='Massachusetts';
```
4. **Dry run (writes nothing):** `recompute-diff-order ma --dry-run --flags-only`. Report every line and the times. **What I expect:** one `diffs untouched (--flags-only)` line, and `is_bill_version: set=12113 changed=20 not_a_version=3200` (your last run's numbers; the flag counts do not depend on the switch, so the same numbers are the check; if they differ, say what changed since, for instance documents archived on v46 or v48). **If any line shows `nulled=` or `corrected=`, stop and report: the switch is not in effect.**
5. **Reply** `reply-recompute-diff-order-ma-flags-only-preflight-20261107.md`. Then wait.

## 2. Part 2: the commit (only after a GO note for `ma --flags-only`)
Dry run first, printing what Part 1 printed (if anything changed, report and wait); then `recompute-diff-order ma --commit --flags-only` printing the same flag numbers; then the dry run again, which must print **`set=0 changed=0`** and the same `not_a_version`; then G3 again: `flag_null` = 0, `flag_false` = the `not_a_version` figure, and **`with_diff` = 291 and `diff_fingerprint` identical to Part 1's**. Report lines, rows, times (UTC) and that nothing else changed. Rollback is the G2 restore point, or, for the flag only, reverting and rerunning with the switch; do not undo by hand without telling me.

## 3. Not authorized
`recompute-diff-order ma` in any form **without** `--flags-only` (OPEN-396 / OPEN-370, still held); `recompute-diff-order all`; any other state; a search-index refresh (a separate request after the commit, if needed); cleaning up the roughly 2,000 HD/SD Bills already in the broker or published artifacts; any scrape, archive, schedule, restart, LegBot run, or change to ddp-sync or the broker. This request does not touch OPEN-396 (the 290 hidden changelogs): none of the 358 Massachusetts bills that have two versions has a title the rule hides.

## 4. What I do on the Mac side (not yours)
Ramon reads the list of the 3,267 bills the rule would hide before he gives the GO. After the commit I check the Mac replica applied it (lag, no errors), one known report end to end (SD 4329: mark false, api-v3 shows no `raw_text`, ddp-sync logs "No archived bill text"), and that H 3188 and SD 3237 are still readable as real bills.

**One more thing from the Mac, unrelated to this request:** the Docker disk on this host reached 100% around 04:35 UTC (three scrapers-image builds in two hours) and is at 95% after a prune. If you see Colima or Docker errors on the Mac, that is why.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
