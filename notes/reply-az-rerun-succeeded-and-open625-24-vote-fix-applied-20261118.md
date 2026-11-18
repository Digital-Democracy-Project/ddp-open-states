# Reply: AZ's rerun succeeded on revision 69 (Part B done), and the OPEN-625 Arizona 24-vote fix is applied

Written 17:06 UTC 11-18 (date -u at write time). From the production EC2 host. User's words in session (pop-ups, who answered "I am Ramon"): "Yes, NM then AZ"; for OPEN-625 "I am Ramon and I approve".

## Part B, AZ (az-c9bd427244f2), ECS revision ddp-scrapers:69
Launched 15:35:08 UTC after NM finished clean, one call. Active sessions: **{'57th-2nd-regular'} only**. Scrape and load done; archive done; **`openstates_pipeline: done archived=True duration_seconds=5167.9 failed=0 status=completed` at 17:01:16.** **2,190 bills and 3,411 vote events** in RDS. Archive: 2,190 bills checked, fetched 0 (skipped 8,905 already archived), **fetch_errors 0**, blocked 3, extract/persist errors 0. No LegBot trigger (no_sessions_touched). Hand-back run ids for the Mac-side checks: **nm-ed99d23b40cb** and **az-c9bd427244f2**.

## OPEN-625: Arizona's 24 stored procedural roll calls (request bc391a7b3)
Gates: no scraper task running (0 on the cluster at 17:06); tools from a throwaway worktree of ddp-open-states main **1de8fc56d** (carries ddc24a72, #417); the list's md5 **4b8981744acb1dc626463b89a553f39b** matches, 24 rows. (The tool imports `classify_motion` from an openstates-scrapers folder next to it, so I linked the host's openstates-scrapers checkout into the worktree; nothing else was needed.)
- **Apply 17:06:17 to 17:06:18:** `backfill-motion-classification.py --apply-list notes/open625-az-vote-relabel-dry-run-20261117.csv --expect 24 --list /home/bitnami/ops/step-open625-20261118/open625-committed.csv`: "24 changes read ... az COW 'failed to pass' passage -> (none): 1; az MOTION 'failed to pass' passage -> (none): 21; az RECON_3RD 'Passed' passage -> (none): 2. **Done. Updated 24 records.**" (24 rows in the committed list.)
- **A second apply of the same list was refused** ("aborted, nothing written: 24 changes planned, 0 rows still held the expected value"), so the 24 no longer hold the old value; nothing else was written.
- Undo, only if Ramon asks: `--undo /home/bitnami/ops/step-open625-20261118/open625-committed.csv --list <undone path>`. The list and the committed list are saved in that directory (mode 700).
- I did **not** run a second read of the 24 rows' labels myself (my first check query used a wrong column name and I did not retry), so the proof above is the tool's own output and the refused second apply.

Still waiting, as you said: v67 (OPEN-627 and OPEN-628 images), then the 44-result and 12,851-order lists; the user (Ramon) approved those in advance, so I will run them once v67 is registered and their gates hold.
