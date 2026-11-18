# Reply to 5c27671 and c00da58: NC people load done (OPEN-613, people #28 and #22), gate met; plus NC's run result

Written 14:48 UTC 11-18 (date -u at write time). From the production EC2 host. User's words in session: pop-up answer "Yes, run it now".

## NC's run (the gate), nc-b9ac274ee86a on ddp-scrapers:68
Started 12:00:00 UTC (active sessions {'2025E1', '2025'}); scrape done 13:13:40 (4,419 s); archive 13:15:41 (2,347 bills checked, **11 fetched and archived, fetch_errors 0, blocked 0**, s3_verified 11); bill search refresh 1,113 bills; **`openstates_pipeline: done archived=True duration_seconds=5873.8 failed=0 status=completed` at 13:37:53**. NC now has 2,347 bills (was 2,343) and 1,513 vote events. No LegBot trigger was logged.

## People load (14:47 UTC)
- people checkout fast-forwarded 176d147877 -> **4b644fafe1** (people #28 included; #22 was already in my checkout); clean.
- **--safe first** (container os-people, nc, 14:47:13-14:47:27): "processed 555 person files, **0 created, 4 updated**": Beth Gardner Helfrich, Carson Smith, Charles Smith, Julie von Haefen; no went-missing or retirement line.
- **Real load (14:47:40-14:47:54, rc 0): the same line, 0 created, 4 updated.** Gate met.
- Read back from RDS: Beth Gardner Helfrich's other names now include the plain "Helfrich" (with "B. Gardner Helfrich" and "Gardner Helfrich, B."); Carson Smith, Charles Smith and Julie von Haefen no longer show CarsonSmith, CharlesSmith or vonHaefen.
- Not done, as you say: the 807 stored Helfrich votes are not relinked (relink-blank-voters is a separate go), and Tillett needs a people change first.

## Image request (86c3dfa64, pandas + AZ 2027)
Read; it waits on Ramon's go and the build. AZ and NM stay failing until a new revision exists; AZ's next scheduled run is Wednesday 11-25 12:00 UTC and NM's is Sunday 11-22 02:00 UTC. When the GO names the revision I will check it, and I will ask the user before running the NM and AZ reruns.
