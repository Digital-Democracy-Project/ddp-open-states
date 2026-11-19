# CHECKPOINT (request 2b0abe4f2): Utah's stored history committed: `relabel ut` (1,412 actions, 0 bills) and `fix-ut-vote-chamber.py` (1,172 actions on 696 bills); both second dry runs 0

Written 16:10 UTC 11-19 (date -u at write time), from the production EC2 host. **The user's words (pop-ups, 11-18 about 22:50 UTC, recorded in memory):** step 1 `relabel ut` approved **if the dry run shows exactly 1,412 actions and 0 bills changed** (list md5 c16df52e...); step 2 `fix-ut-vote-chamber.py` approved **if the dry run matches the reviewed list of 1,172 actions on 696 bills** (md5 fe186ec9...). Both conditions were met exactly; step 2 only after step 1. No other state, no scrape.

## Gates (16:01 to 16:09 UTC)
1. SYNC-180: ddp-sync rebuilt at c983ae68, drift check exit 0 (checkpoint 0dc982505). 2. Utah's broker switch (#767) is live in 81cce950 (Utah re-judged 00:14 UTC). 3. **ECS 0 running tasks** (checked before each step), no ut process in ddp-sync, today is Thursday (Utah's run is Tuesday 12:00 UTC). 4. /opt/ddp-open-states at 20815be5b (contains 2bb68bf2).
Tools: core = a throwaway worktree at **c983ae68** (contains 5c1455e1); the Utah scraper = a throwaway worktree at **dca8e7a6**. **Note on the chamber script:** `fix-ut-vote-chamber.py` puts `<its own folder>/openstates-scrapers/scrapers` first on sys.path, and the host's nested checkout is at 338ebffb5 (PR #45), which has no `voting_chamber`, so the first dry run died with `ImportError: cannot import name 'voting_chamber'` (nothing written; read-only mode). I ran a **byte-identical copy of the script** (cmp equal) from a scratch folder whose `openstates-scrapers` points at the dca8e7a6 worktree, instead of changing the production checkout.

## Part 1: dry runs (read only, PGOPTIONS default_transaction_read_only=on), 16:08 to 16:09
- **A. `os-text-extract relabel ut --dry-run`:** `ut: [DRY RUN] actions changed=1412 unchanged=35928 | bills changed=0 unchanged=0`; passage -> (none) 1,088; (none) -> passage 230; failure -> (none) 51; executive-receipt -> (none) 36; "amendment-failure, failure" -> "amendment-failure" 7; computed fields: first_action_date 0, latest_action_date 0, latest_action_description 0, **latest_passage_date 555**. List 1,412 rows, **md5 c16df52ec9f754d32f89132ddd3f1158 = the reviewed list on your branch.**
- **B. chamber fix:** 37,340 Utah actions read; per rule House 3rd reading 522, House concurs 129, House refuses 11, House conference final passage 10, Senate 3rd reading 258, Senate 2nd & 3rd/suspension 150, Senate concurs 85, Senate refuses 4, Senate conference final passage 2, Senate failed 1; **1,172 actions on 696 bills**; list md5 **fe186ec9c7ef3a253d3f9231cb73bbc4 = the reviewed list; the same 1,172 action ids.**

## Part 2: relabel ut COMMITTED (16:09:25 to 16:09:33, exit 0, 0 errors)
`os-text-extract relabel ut --commit --expect 1412 --list /home/bitnami/ops/step-utah-20261119/relabel-ut-committed.csv`: `[COMMITTED] actions changed=1412 unchanged=35928 | bills changed=0`, same breakdown, latest_passage_date changed on 555 bills. **Second dry run: `actions changed=0 unchanged=37340 | bills changed=0`, every computed field 0.**

## Part 3: fix-ut-vote-chamber.py COMMITTED (16:09:49 to 16:09:50, exit 0, 0 errors)
reviewed md5 checked first, then `fix-ut-vote-chamber.py --apply-list notes/open622-ut-vote-chamber-dry-run-20261118.csv --commit --expect 1172 --list /home/bitnami/ops/step-utah-20261119/fix-ut-committed.csv`: **"Done. Moved 1,172 actions." on 696 bills**, list 1,172 rows. **Second dry run: "would move 0 actions", 0 bills.**
Rollback, only if the user asks: `os-text-extract relabel ut --undo .../relabel-ut-committed.csv --commit --list .../relabel-ut-undone.csv` and `fix-ut-vote-chamber.py --undo .../fix-ut-committed.csv --commit --list .../fix-ut-undone.csv` (same scratch copy).

## After (read only; owed, not yet done)
Both runs moved `updated_at` on the touched bills (555 and 696), so the broker's next Utah sync re-reads them. The scorecard chain's first run on the new code is **05:00 UTC 11-20**; after it I will run `validate_scorecards --jurisdiction UT --all`, `--bills` and `reconcile_scorecards` for UT and report HB 136's bill score (expected 50) and any Utah scorecard entry that changed. I have not run `validate_bill_stages` (the BROKER-490 input) and will not unless asked.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
