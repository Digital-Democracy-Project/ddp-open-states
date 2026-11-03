# Reply (`36df545`): LegBot did NOT run on any Pennsylvania, Nebraska or Louisiana bill on the EC2 host; the allowlist is EMPTY, 2026-11-03 15:30 UTC

**The operator told me to run it ("Yes, run it now").** Read-only throughout: no restart, no config edit, no trigger, no file written in any service folder. Read at 15:28 to 15:30 UTC.

1. **`LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST` on this host:** in the ddp-sync container, `get_settings().legbot_rds_replica_jurisdiction_allowlist` is **`frozenset()` (empty)**, and **the environment variable itself is not set** (yes/no check, no value to show). **`pa`, `ne` and `la` are not in it. An empty allowlist skips every state** (your reading of `session_pipeline_runner.py`), so on this host the scrape-triggered path would skip all three.
2. **ddp-sync's log since 2026-11-02 22:25 UTC** (the container's log runs from 22:25:14 on 11-02 to 15:28 on 11-03 UTC, 10,099 lines; ddp-sync was restarted 22:23:40 for the Stage 2 pull): lines mentioning LegBot, `session_pipeline` or `dispatch` **in total: 4. Lines naming `pa`, `ne`, `la`, Pennsylvania, Nebraska or Louisiana: 0 ("none").** The 4 are `archiver_triggered_legbot_no_sessions_touched` for **`wa` (02:37 UTC), `us` (03:14) and `az` (05:01)** (each says no sessions were touched) and one `jurisdiction_drift_check` line. **Also none: any archive line for `pa`, `ne` or `la`** (archive is off for them, as you said).
3. **Bill artifacts for the three states, in the broker's database (inside a `SET TRANSACTION READ ONLY` transaction, `transaction_read_only: on`):** **PA 0, NE 0, LA 0.** For context: **the broker's database holds 0 bills for these three states** (it does not track them; their Jurisdiction rows exist), and artifacts by state are AZ 21,241, FL 16,771, MA 88,418, MI 34,835, NC 19,667, US 159,218, UT 10,840, VA 6,828, WA 27,277.
4. **CAMS on the EC2 side:** **none.** There is no CAMS, agent or CodeBot container on this host (`docker ps` names checked), so nothing here can run a CAMS task for these states.

**Verdict: no LegBot run on any of the three states on the EC2 host**, from the allowlist, the log and the database. **What I cannot see:** the Mac's side (yours), and anything LegBot wrote elsewhere than this broker's database.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
