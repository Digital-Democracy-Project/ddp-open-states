# status: MS 5a re-import finished on v86 (rev 88); two numbers measured, one pass line NOT met

Facts only, read-only queries on RDS at ~07:09 UTC. I have not diagnosed the gap.

- Run ms-db46462c03cc (full=true, sessions 2026,20261E): started 05:05:07, collection done 06:49:15, "cloud_scrape: done" 06:57:19, duration 6,732 s. No error lines.
- At 06:57:20 a second run started by itself, ms-90c44cf164ae (I did not trigger it): collection done 06:59:21, "done" 06:59:27, duration 127 s. Both scrape keys then logged "no usable filing figures" (markers ms_session_2026.imported and ms_session_20261E.imported missing under /opt/ddp-open-states/logs/last-run).
- Sponsors, session 2026: 7,673 sponsorships, 110 with no person = 1.4% (your pass line: about 1.4%). Session 20261E: 8 bills, 8 sponsorships, 0 unmatched.
- Version notes, session 2026 (13,609 MS documents across both sessions): **"Current version" is still on 8,012 documents** (about 59%), the next notes being As Introduced 2,661, As Passed the lower 536, Committee Amendment No 1 (Adopted) (Voice Vote) 476. Your 5a pass line says no "Current version" and about 0% without a stage. Not met as measured now.
- Documents are still being updated about 60 per minute (07:04-07:09), after both runs reported done. I do not know which process does that (text extraction or archive?).
- Not started: any other load. I wait for your reading before MD (people load, then 5b), ME, NM.
