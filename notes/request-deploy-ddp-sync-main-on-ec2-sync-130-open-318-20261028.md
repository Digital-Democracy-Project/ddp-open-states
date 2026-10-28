# Request: deploy ddp-sync `main` on the EC2 host (pull and restart) after the 00:30 UTC review (SYNC-130, OPEN-318)

2026-10-28 (about 00:30 UTC). **This is the go for the writes below**, given by Ramon in this session. It covers one thing only: pull ddp-sync to `main` on this host and restart it. **Stop and report if anything does not look as described; do not retry a failed step. Do not print any key, token or secret value.**

## Why
* SYNC-130: ddp-sync #245 (Florida runs once with no session argument, so it follows the scrapers image's active flags; the hand-kept session list is gone) is merged and has to run on this host, because Florida is cloud-owned and scheduled from here. Its two pre-merge checks passed on 10-27 (image `v38` has FL 2027 active with session_number 126; no bare `fl` marker in the scraper-memory bucket) and the Arizona canary on `v38` finished clean.
* OPEN-318: restarting ddp-sync clears the old `jurisdiction_manifest_unusable ... 'scheduled'` warning now that this host's manifest has the field.
* The host is on `af6b098`. `main` is ahead by 10 commits: #245 (FL), #246 (SYNC-135, removes the weekly `session_pipeline_batch` job), #249 (SYNC-134, reads the bill-topics list from the broker at run time instead of a copied file), and docs only otherwise.

## Please do, in this order
1. **Wait for the 00:30 UTC cadence review to finish** and report what it did to the `ddp:scrape_cadence:az` key (you said you would). Then **restart only if** the in-flight record is empty and no scheduled launch is due in the next 10 minutes (WA is 02:30 UTC, USA 03:00). If something is running, wait; do not interrupt a scrape.
2. **Before pulling:** the host checkout must be clean (no local edits; `sync_schedule.yaml` had none on 10-22) and `git fetch` must show `main` fast-forwardable from `af6b098`. Report the current HEAD, and the list of scheduler jobs the live app has now (names only).
3. **Pull ddp-sync to `main` (`334f2df` or newer), fast-forward only.** Report the new HEAD. Do not edit the host's `.env` or the secret; the drift-check variable stays as it is (off) for now.
4. **Restart ddp-sync** the way this host normally does it, and report the restart time.
5. **Verify (read-only):** it comes up healthy with no traceback; the jurisdiction manifest line reads `jurisdiction_manifest_agrees` and the `missing field 'scheduled'` warning is gone; the live job list has lost `session_pipeline_batch` and has no Florida session list in its config; the broker's bill-topics endpoint answered when ddp-sync read the topics list (report the status only, or the log line saying it fell back, if it did); no unexpected scrape launched.
6. **Do not run Florida by hand and do not trigger anything.** The first Florida batch on the new code is Sunday 2026-11-01 02:00 UTC; Ramon will say if he wants it earlier.

## Rollback
If ddp-sync does not come up healthy: `git checkout af6b098` in the ddp-sync checkout, restart, and report. Do not change anything else.

## Report
Commands (secrets removed), old and new HEAD, the restart time, the verification results, and anything that did not match.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
