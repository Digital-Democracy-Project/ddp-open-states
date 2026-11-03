# Request (read-only): did LegBot run on any Pennsylvania, Nebraska or Louisiana bill, and what is the EC2 allowlist? 2026-11-03

**Ramon asked this directly (2026-11-03): "was there a legbot run on any of these bills? hopefully not, because we have that gated off until we can complete the text pre-processing of the raw_text for these bills."** The first full scrapes of `pa`, `ne` and `la` loaded 1,847 (NE), 2,616 (LA) and 5,270 (PA) bills into production RDS between 2026-11-02 22:25 and 2026-11-03 05:34 UTC. **LegBot must not have run on any of them.**

**This is a read-only request. Change nothing: no restart, no config edit, no trigger, no file write in any service folder.** Please do not post any `.env` value other than what is asked below.

## What I already checked on the Mac (not production)
* The Mac's ddp-sync has no LegBot bill-processing line for these states since 2026-11-02 (its last run ended 2026-11-01 07:50 UTC, 2,190 bills), and the Mac's `LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST` is `mi,ut,fl,va,wa,us,ma,az,nc` (no `pa`, `ne`, `la`). The CAMS log on the Mac has no LegBot line naming these states.
* The code skips any state not on the allowlist (`session_pipeline_runner.py`, log line `session_pipeline_bill_skipped_jurisdiction_not_on_rds_replica_allowlist`), and an empty allowlist skips every state.
* **That is the Mac. Production (the EC2 host) is not verified.** The manifest has `legbot_replica: false` for all three.

## Please read, on the EC2 host, and reply with
1. **The value of `LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST` in the ddp-sync container's environment** (the state codes only; it is a list of state codes, not a secret). Say whether `pa`, `ne` or `la` is in it, or whether it is empty or unset.
2. **ddp-sync's log since 2026-11-02 22:25 UTC:** every line that mentions LegBot, `session_pipeline` or `dispatch` together with `pa`, `ne`, `la`, Pennsylvania, Nebraska or Louisiana. Give the count and paste up to 10 lines (redacted); say "none" if there are none.
3. **Any LegBot output for the three states** (read-only): in the broker's database, the count of bill artifacts (summaries, pros and cons and so on) whose bill belongs to Pennsylvania, Nebraska or Louisiana. Expected: 0. Use a read-only transaction.
4. **Any CAMS task on the EC2 side** that names these states since 22:25 UTC, if CAMS runs there; if not, say so.

## Stop and tell me
If any of the three counts is not 0, or `pa`, `ne` or `la` is on the allowlist: **change nothing**, report what you found, and wait for Ramon. Do not delete anything.

Reply with a note on this branch. No other action is needed.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
