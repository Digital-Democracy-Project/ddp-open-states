# status: ME 5d finished (18:04:45 UTC), 3 sessions, 0 failed; OK and IA still collecting

- Maine pipeline (ddp-sync log): "openstates_pipeline: done archived=True duration_seconds=22480.1 failed=0 sessions=3 status=completed". Started 11:50:05 UTC. Session runs: 132R1 and 132R2 on rev 88 (v86); 132S1 (me-9c24de62c00b) on rev 90 (v88): collection done 18:00:38, load done 18:02:44 (7,498.3 s in all). Archive task 121.2 s, "archive_after_scrape_succeeded attempt=1". No error lines.
- Read-only checks of the Maine data are yours (three sessions, as you said). I have not measured anything on RDS for ME.
- Host at 18:29 UTC: load 1.88 / 1.63 / 1.37; runs now: ok (2025+2026) and ia (2026,2026s1) only. NM done earlier, FL archive done.
- Not started (Ramon's go needed): the v88 core rollout, WY/KY batch, v89, MS recompute commit. IA 2025 follows IA 2026 when it ends.
