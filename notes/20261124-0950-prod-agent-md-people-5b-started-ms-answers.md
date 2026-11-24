# reply to f23fed3 and cc1b14d: MD people loaded, 5b MD started 09:50 UTC; answers on ms-90c44cf164ae and the markers

Ramon's go for the re-imports is the pop-up answer from ~05:05 UTC (MS, MD, ME, NM, OK, IA). No new go needed for these. Waiting on his go, not started: MS remove-stale-documents, the v87 core rollout (cc1b14d), ND refresh-extraction.

## Maryland people (step 4), ddp-sync container, people checkout 05d7e4cc
- Safe run: "updated person from .../md/legislature/Alex-Harlan-39fb5148-7e60-4df3-b538-3bee07dd8a68.yml", "1 removed via merge: ocd-person/d30780ed-e435-48cd-bfa9-8e197d3ebe81 => ocd-person/39fb5148-7e60-4df3-b538-3bee07dd8a68", "processed 468 person files, 0 created, 1 updated" (exit 1 is the safe mode's own "no changes were made").
- Real run: the same three lines, 0 created, 1 updated, exit 0. Only Harlan changed, as you expected.

## 5b MD
- POST openstates-scrape/md?full=true&sessions=2026,2026s1 at 09:50:40 UTC, 202 with "full": true, rev 88 (v86). Counts to follow when it ends.

## Your two questions about Mississippi
1. ms-90c44cf164ae: the log shows it was the second session of my own request. Its stall-check line carries the label "ms session=20261E"; the first run (6,732 s) was session 2026. It started 1 s after the first run's "done" (06:57:19 "cloud-owned -- triggering Fargate collection", 06:57:20 run id). I did not find a schedule or retry line. That is what I observed; I did not read the code path to confirm it is one run per session.
2. "no usable filing figures": the markers ms_session_2026.imported and ms_session_20261E.imported are absent under /opt/ddp-open-states/logs/last-run on this host. This host has no local-import step for cloud runs, so I expect it, but I have not checked it against earlier cloud runs (e.g. RI, ID).
