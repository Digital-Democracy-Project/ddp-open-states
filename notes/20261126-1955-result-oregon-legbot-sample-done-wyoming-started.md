# Result 11-26 19:55 UTC: Oregon's 100-bill LegBot sample DONE; Wyoming's started

Ramon's scope: a random sample of 100 bills each (OPEN-897 wave 1). Flow: the automated trigger's (nine artifact types, concept statements on, org research off, no policy-statement step), run on the Mac's ddp-sync, writing to production.

## Oregon (`legbot-session-bccd617bfe5d`, session `2026R1`)
* Accepted 18:45:45 UTC; **completed 19:45:06**: `success: true`, **100 bills considered and 100 processed**, not truncated, **3,561 s (59 min)**, peak memory 771 MB. The Mac's run record gives only the totals (`results` is a count, not per-bill detail), so the rest comes from the broker's artifact table, read-only.
* **Artifacts written for Oregon bills since 18:44 UTC: 919 across 100 distinct bills; 844 complete, 75 failed.** All 919 `origin: ai_generated`.
* **Every failure has the same cause: `generation` / `insufficient_information` (75 of 75).** No crashes or other failure kinds. By type: `bill_opposing_orgs` 46, `bill_pros_cons` 21, `bill_impact_analysis` 3, `bill_supporting_orgs` 2, `bill_summary` 1, `bill_vote_no_frame` 1, `bill_vote_yes_frame` 1.
* This is the same shape as the earlier states' LegBot runs (opposing-orgs and pros-cons are the usual "not enough information" types). I have not read any summary; judging quality is yours. The artifacts are in production but nothing public reads them until a state's other switches are on.

## Wyoming (`legbot-session-1b1442a4c176`, session `2026`)
* Started 19:49:20 UTC, accepted; running (at 19:51 it had touched 3 bills, 2 failed `insufficient_information`, as a first look). I will report its totals the same way when it finishes (about an hour).

## Not done
No retry of any failed artifact (`retry_failed` false); no org research; no policy-statement step; no other state; no switch change.
