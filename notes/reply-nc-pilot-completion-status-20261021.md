# REPLY: where NC's pilot stands (OPEN-231), read-only, prod agent on the EC2-broker host, 2026-10-21 UTC

Nothing was started, retried, restarted or changed for this note. "Fresh" below means read just now; "earlier" means a read or note from earlier this week that I did not repeat. The saved database password in this host's `.env` stopped working at about 03:10 UTC today (password authentication failed; the live-resolved credential the scheduled loads use still works: the 03:05 USA load succeeded). So the RDS numbers below are from my reads between 10-19 and about 03:10 UTC today, not from a fresh query for this note; I did not try to work around it.

## 1. Clean scheduled cycles: none that I can show; the log I have starts 10-14
* The only saved ddp-sync log is `ddp-sync-ddp-sync-1-20261019T014524Z.log.gz` (**2026-10-14 15:04 to 10-19 01:45 UTC**) plus the live log since. **The 10-11 cycle (and 10-04, 10-08) is not in any log I have**, so I cannot say what it did.
* **10-18 02:00 UTC `secondary` run, NC `nc-4ad2eace2886` (fresh):** collection 02:00:01 to 02:55:40 (55 min), `cloud_scrape: load failed ... cloud_loader.py exited 1` at 02:59:19 (the vote-key collision, OPEN-397); the whole job ended 11:29:46 with `failed=1 total=6`. **Not clean.** No Slack alert line appears in the saved log around it (I did not look at Slack itself; I have no access).
* **10-19 04:32 UTC manual run `nc-51a2973c1231` (not a scheduled cycle):** task `ddp-scrapers:39` (v36), collection 04:32:32 to 05:28:12, load to 05:32:07, `cloud_scrape: done` in 3,574.7 s, no `DuplicateItemError`; `2025` still 774 votes / 774 keys / `id_hash 44906cf9927a198f81937675078aeed1`, `2025E1` 7 votes (earlier read, this morning). That is clean, but I triggered it by hand.
* **Earlier NC scrapes I know of:** the first load of `2025` was 09-13 about 03:01 UTC (all 2,338 bills created then; inferred from timestamps, no log); a 10-05 collection failure (`exit_code_1`, after 61 s) from the 10-05 note; the 09-17 LegBot dispatch failure (SYNC-66 note). **Next scheduled NC scrape: Sunday 2026-10-25 02:00 UTC.** No object counts or block signatures are in the logs I have.

## 2. Manifest status: still `probing`
`jurisdictions.yaml` line 261 in `/opt/ddp-open-states` (checkout HEAD `046c050462`): `status: probing  # OPEN-230 ...`; `origin/main` reads `probing` too (fresh). Nobody has flipped it.

## 3. OPEN-231 comments: I found none
A search of this branch's notes for OPEN-231, a NC `quality_check` or a Tier 2 re-run found only the 09-09 request and my 09-09 finding ("zero confirmed cycles, do NOT flip to live"), the 09-14 root-cause notes, your note of today and a few unrelated ones; none says Stage 6 is complete, and none records a VoteBot NC check or a `quality_check.py --coverage nc ...` re-run. That search is by keyword, not exhaustive, and **I have no Jira access**, so a ticket comment could exist that I cannot see.

## 4. NC `LegislativeSession`: yes, and #376 is in the running code
* **#376** (`f9467d8e`, merged 2026-09-27) **is an ancestor of the running broker commit `489c6578`** (and of the 10-19 release `1b9316ca`). Fresh.
* The production broker has `LegislativeSession` rows for **NC `2025`** (id 423, primary, 2025-01-11 to 2026-07-01) and **NC `2025E1`** (id 424, special), **both created 2026-09-29 02:32:44 UTC**, never updated since. I did not trace what created them (the timing is after #376 merged; the BROKER-159 self-heal in `ensure_bill` is a plausible creator, unproven).
* **A discrepancy:** the broker's `2025E1` row has dates 2025-11-17 to 2025-12-01, but the main database's `2025E1` is named "2026 Extra Session 1" with dates 2026-10-07 to 2026-10-08. I do not know which is right or whether it matters.
* LegBot did work on both sessions: 10-19 (5 bills, `2025E1`) and the full-session run of `2025` finished 03:02 UTC today (2,338 bills, 0 bill-level errors; the broker now holds 2,343 NC bills and 19,667 NC artifacts).

## 5. Archive: it works; the 10-08 run I cannot see
* **10-15 05:00 UTC (fresh, saved log):** the NC archive ran: Fargate task done in 91.1 s, `archiver_triggered_legbot_no_sessions_touched`, `bill_search_refresh_run ... refreshed=0`, job "executed successfully": a clean run that changed nothing. **10-08: not in any log I have.**
* **10-19 05:32 to 05:34 UTC:** the scrape-triggered archive ran (121.3 s, success) and LegBot then processed the 5 special-session bills.
* **`ddp_bill_version_document` holds NC rows (earlier read, today about 03:10 UTC):** `2025`: **6,192 documents, all created 2026-09-17 05:01 to 06:45 UTC** (the first Thursday archive), all with text, 0 errors; `2025E1`: 15 documents created 10-19 05:33. Zero rows on 09-14 fits (first rows 09-17).

## 6. Version-document recompute: committed (from my 10-16 note, not re-run)
`reply-open352-golive-part3-recompute-nc-wa-mi-al-az-done-20261016.md` (this branch): Ramon confirmed the go in that session (GO note `dc1d8542`, confirmation `3507c8a8`). NC: `nc: [DRY RUN] 2338 bills checked | unchanged=2588 corrected=3550 nulled=54`, **`[COMMITTED]` the same three numbers (28 s)**, second dry run `corrected=0 nulled=0`; G3: NC stamp pages with a diff 54 to 0, NC Edition/Ratified/SL with a diff 0 to 3,550. I did not re-run it today.

## Not checked, and other things you may want to correct in the plan
* Not checked: Jira and Slack; the 10-11 / 10-08 / 10-04 runs; object counts and block signatures; any quality read of NC's LegBot output.
* Beyond your list: the NC LegBot first full-session run is **done** (above) with **62.5% of `bill_opposing_orgs` rows failed (`insufficient_information`)**, which the plan may want listed; the OPEN-390 changelog count (923 complete) is unreconciled against its estimate (about 3,550 versions).
* The saved RDS password in this host's `.env` is stale as of today (reported, not fixed).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
