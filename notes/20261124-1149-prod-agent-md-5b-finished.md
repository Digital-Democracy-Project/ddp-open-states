# status: MD 5b re-import finished on v86 (rev 88), 11:48 UTC; PA nightly done + archive by hand

## Maryland 5b (full=true, sessions 2026,2026s1)
- md-642ae0758dc6 (session 2026): started 09:50:41, collection done 11:37:23, "done" 11:45:10, 6,868 s, no error lines. md-a67649d24040 (session 2026s1): 11:45:10 to 11:48:22, 191 s. Both then logged "no usable filing figures" (markers missing, as for MS).
- Read-only RDS counts, 11:49 UTC: bills 2026 = 2,671, 2026s1 = 6. Person votes 2026 = 264,469 and 2026s1 = 3,478, **0 with no voter** (voter_id null) in both. Votes by "Speaker"/"President" names: 2,731, 0 without a voter. Versions: 5,059, 0 with a blank note, **0 "Racial Equity Impact Note"** versions.
- Not comparable to your lines: your "unmatched votes 2,733 → 2 (the 2 Harlan votes)" and "versions about 0% (was 74.8%)". My unmatched count is voter_id null = 0, so I see 0 where you expect 2; I did not check the 2 Harlan votes by name. I have no "stage" measure for versions here, only blank notes. Please verify on the replica.
- Archive: not started by me yet. The md pipeline lock is still held at 11:49 (locks md, pa); I'm watching whether the md archive starts by itself before I start one.

## PA nightly pa-44ff521cb05c (resumed after my 04:57 rebuild)
- Collection done 11:03:25, "done" 11:18:39, 22,894 s. No archive started by itself; I triggered openstates-archive/pa by hand at 11:29:23 (202). Fargate task done in 151.2 s; archiver_triggered_legbot_wireguard_accepted for PA session 2025-2026, run legbot-session-35c398181921 (waiting for its result).

Next on v86: 5d ME, then NM (a1c833f), OK 2025+2026, IA 2026 then 2025. MS stale-document removal and the v87 core rollout wait for Ramon's go.
