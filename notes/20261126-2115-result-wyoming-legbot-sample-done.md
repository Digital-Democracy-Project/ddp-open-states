# Result 11-26 21:15 UTC: Wyoming's 100-bill LegBot sample DONE (Oregon's is in my 19:55 note)

## Wyoming (`legbot-session-1b1442a4c176`, session `2026`)
* Accepted 19:49:22 UTC; **completed 20:59:05**: `success: true`, **100 bills considered and 100 processed**, not truncated, **4,182 s (69.7 min), of which 29 min 43 s was the stall** reported in my 20:35 update (the stall is the bug ticket you were asked to file). Without it the run took about 40 minutes, against Oregon's 59 for 100 bills.
* **Artifacts written for Wyoming bills since 19:45 UTC: 834 across 100 distinct bills; 758 complete, 76 failed.** All 834 `origin: ai_generated`.
* **Every failure has the same cause: `generation` / `insufficient_information` (76 of 76).** By type: `bill_opposing_orgs` 63, `bill_pros_cons` 6, `bill_impact_analysis` 4, `bill_supporting_orgs` 3. No crashes or other kinds; no failed summary or vote-frame artifacts.
* Read from the broker's artifact table (the Mac's run record gives only totals). I have not read any summary; judging quality is yours. For comparison, Oregon: 919 artifacts, 844 complete, 75 failed, also all `insufficient_information` (opposing orgs 46, pros and cons 21).
* No retry (`retry_failed` false), no org research, no policy-statement step, no switch changed, nothing public changes from this.
