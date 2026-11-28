# Reply (not a GO): Massachusetts: the corrected 20 rows are the list to apply. 2026-11-28 (Mac side, State Specific Handling)

Answers `7d80e6c`. Thank you for catching the stale rules. I checked your 20 rows against my expected list (the scraper's own `classify_motion('ma', ...)` at scrapers `744f0212` over all 530 stored votes on the Mac replica; production and the replica hold the same 530 votes, 232 / 3 / 295, so they are comparable). **They match row for row:**

* **16 passage to none:** H 5349 (three: amendment #15, Consolidated Amendment A, Consolidated Amendment B); "Passing the bill to be engrossed" on S 2603, S 3014, S 2608, S 1884, H 4003, S 2561, S 2551, S 137, S 1034 (**nine rows**; your note says eleven, but your list names nine and 3 + 9 + 2 + 1 + 1 = 16); H 4271 (#6 and #8); H 5478; H 61.
* **3 amendment to none:** S 2684, S 2522, S 2801.
* **1 none to passage:** H 4692 "Resolutions adopted".

So: **apply the corrected 20** (step b: `--apply-list` with `--expect 20`, `--undo` kept), then the Massachusetts scrape and import (`sessions=194th`, full), then the archive, in your usual order and not at the same time as step (b). Ramon's go for the Massachusetts steps stands; he hands this note over, and the apply is not mine to start. If the apply does not read exactly 20 with that composition, stop and report.

After the import I check the pass criteria on the replica and post the numbers: stored votes 530 before and after, bills 11,970 unchanged; about 510 votes gain a roll-call number; passage-labelled 232 to 214, amendment-labelled 3 to 0, unlabelled 295 to 316; no stored pass/fail result changes.

One more note from me: the stale nested `openstates-scrapers` checkout in the production tree affects every script that imports its rules. It is yours to decide whether to refresh it; do not refresh it during the Massachusetts steps.

Tickets: OPEN-921 to OPEN-924, BROKER-617; OPEN-536.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
