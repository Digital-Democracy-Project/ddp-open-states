# REQUEST (not a GO): **Oklahoma's 2026 collection failed at about 07:10 UTC (alert in #automation-errors); please read its task log and, on Ramon's go, retry 2026 once.** 2026-11-25 ~09:55 UTC (Mac side, Onboard New States)

**What I need from you:**
1. **Read-only: the failing task's last log lines (no credentials)** for the Oklahoma **2026** collection that died about 636 s after it started (alert "OpenStates scrape failed: ok session=2026, collection exit_code_1 after 636s", 02:10 EST = 07:10 UTC). Is it the same `ConnectTimeout` to `webapps.oklegislature.gov` as the 11-24 2025 failure (`ok-1d84ac39c6ba`), or something else? Please say the error class and the run id; do **not** retry from this alone.
2. **On Ramon's go: ONE retry of `ok?full=true&sessions=2026` only** (2025 is already loaded on v95, so nothing else is needed), on the latest revision (v95 = 97 or later). **If it fails the same way again: stop and report; no third try.** No workaround from our side: no changed user agent, no bypass of any block, no certificate exception.
3. Please also post what you see of the v95 Oklahoma run's state (it was started 04:29 UTC; I read 2025 loaded at 06:59:57), and say whether the ddp-sync v95 restart and the PA nightly are as you expect. **The replica shows no load since 06:59 UTC and no note from you since 04:33 UTC.**

**What I see on the replica (so you can compare):** the 2025 half is verified (unmatched 44 on SB 920; all 4,613 roll-call numbers; the four 2025 labels from #292: HB 1491, SB 135, SCR 12, SR 13). The 2026 half did **not** load: HB 3749, SB 1806 and HCR 1027 are still unlabelled and their rows date from the 01:19 UTC load of the earlier run. Jira: OPEN-887 (the PM's ticket) carries this and the pattern.

**Pass lines after the 2026 retry (I read them on the replica):** all **seven** #292 labels live; person votes **331,234**; 2025 unmatched 44, 2026 unmatched 0; all **8,767** roll-call numbers; 0 double votes.

## Not authorized
A third retry; any workaround of the source's limits; any step on another state; touching the staged ddp-sync restart.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
