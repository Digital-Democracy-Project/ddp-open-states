# Request (NOT a GO): a North Dakota run (session 69) for the five veto-override votes and SB 2158's House result (OPEN-901, scrapers #300 and #301), then the `validate_scorecards` North Dakota check. 2026-11-26 (Mac side, State Specific Handling)

**Not a GO.** Every step waits on Ramon's go in your session and on an image that carries #300 and #301 (Ramon builds the image).

## Why
Ramon approved North Dakota's counted-vote list on 2026-11-26 and asked these two items fixed before ND's switch-on; for the override votes he decided (2026-11-26, on OPEN-901): **"Totals only for now"** (counts only, no names; a Journal names reader is a later ticket).

* **#300** (merged `a2fd5b84`): the scraper stores the five whole-bill veto-override votes it did not store before, as count-only votes counted as votes on the bill (a bill with an item-veto action keeps `veto-override`, which does not count): HB 1540 House 04/25 45-48 (fail); SB 2160 Senate 05/01 31-15 (fail); SB 2261 Senate 03/27 45-2 (pass) and House 04/03 15-78 (fail); SB 2307 Senate 04/25 25-20 (fail). ndlegis.gov shows each only as an action row with its tally; there is no vote page, hence no names.
* **#301** (merged `4a71f199`): SB 2158's House vote of 04/04 (59-31) is stored failed because the scraper read the vote page's status line ("Failed in House", most likely the emergency clause's two-thirds result); its action row says "Second reading, passed, yeas 59 nays 31" and the governor signed it 04/15. The action row now decides the result when it states one with the same tally. It is the only one of the 2,170 stored North Dakota votes whose result disagrees with its action text. The six other failed votes with more yeas than nays (HB 1242, HB 1358, HB 1590, HCR 3012, HB 1457, HB 1594) really failed (constitutional-majority threshold; checked on the legislature's record), so they do not change.
* A scraper change reaches stored votes only by a re-import.

## Order (each step on Ramon's go)
1. **The image:** v98 (built from scrapers `aed388240`, 18:33 UTC) was built before #300 and #301 merged (16:54 and 16:58 EST), so it does **not** carry them. It needs the next image, built from a main that contains `4a71f199`.
2. **Gate:** the new tasks run that image's revision or later. Since an image does not print its scrapers commit, check the one fact the fix leaves in the code: `grep -c result_from_action_row` on the image's `scrapers/nd/bills.py` is not 0 (and ddp-sync's own copy, if the run is checked there). If it is 0, stop and report. `ddp:pipeline_lock:nd` empty first.
3. **The run:** `POST /ddp-sync/v1/trigger/openstates-scrape/nd?full=true&sessions=69` must answer 202 with `"full": true`. All 2,170 stored North Dakota votes already carry the dedupe key, so the run should add exactly the five and update SB 2158's result in place. Then the North Dakota archive (a resumed run does not start one by itself).
4. **Pass (I read it on the replica):**
   * stored North Dakota votes **2,170 -> 2,175** (session 69: 2,137 -> 2,142; 69S1 and 69S2 unchanged);
   * the five override votes present with the tallies above; SB 2158 House 04/04 result **pass**;
   * bills unchanged (1,106: 69 1,089, 69S1 12, 69S2 5); person votes and unmatched names unchanged;
   * no other stored vote's result, label or key changes;
   * counted bill-chambers (broker eligibility, offline) **1,778 before and after**, with five counted votes replaced by an override (four become failures: HB 1540 House, SB 2160 Senate, SB 2261 House, SB 2307 Senate).
   Anything else: stop and report.

## Then: the North Dakota release check (read-only, after the broker release that carries BROKER-606)
The broker's `validate_scorecards` crashed on North Dakota's lettered House subdistricts (`004B`); the fix is merged (BROKER-606, ddp-broker-py #846, `ba82c6ef`). The broker release carrying it (and BROKER-604's North Dakota rule) is the broker session's `/broker-deploy`, not this request. Once it is live and North Dakota's bills are in the broker: `validate_scorecards --jurisdiction ND --all` and `--bills --jurisdiction ND --all`, plus `reconcile_scorecards --jurisdiction ND`. **Expect "no discrepancies found" and 0 missing**; report the three outputs. This step needs the run above first.

## Not authorized
A North Dakota scorecard backfill or switch-on; any broker change; any other state's re-import; deleting a lock, S3 object or Redis key.

Tickets: OPEN-901, BROKER-604, BROKER-606 (OPEN-536, OPEN-146). Rollback: none needed for data (a re-import restores the stored values from the source).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
