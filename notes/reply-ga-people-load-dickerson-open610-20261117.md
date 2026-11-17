# Reply to a71312432: Georgia people load for Sen. Dickerson done (OPEN-610, people #26), gate met

Written 15:46 UTC (date -u at write time). From the production EC2 host. User's words in session: pop-up answer "Yes, run it now".

- **Step 1:** people checkout /opt/ddp-open-states/people fast-forwarded f6a7e832be -> 824bd8c8a3 at 15:45:17 UTC; 824bd8c8 (people #26) is main's tip, one file changed (Jason-Dickerson-...yml, 1 line), checkout clean.
- **Step 2, --safe first** (container os-people, ga, 15:45:19-15:45:35): "processed 594 person files, 0 created, 1 updated", the one update being Jason Dickerson's file; no "went missing" or retirement line; "ran in safe mode, no changes were made".
- **Step 3, the real load** (15:45:48-15:46:03, rc 0): the same line, "processed 594 person files, 0 created, 1 updated", the updated file again Jason Dickerson's. Gate met: Dickerson updated, **0 created**, no went-missing or retirement line.
- Read back from RDS: Jason Dickerson's other names now include "Jason T. Dickerson" (alongside "J. Dickerson", "Dickerson, J." and "DICKERSON, 21ST", among others).
- No Georgia scrape was triggered; the next Georgia run is the Sunday 11-22 batch. No scrape, image, manifest, ddp-sync, broker or other data change.

## Also read: 984f0bfdd (scrapers image v63 request)
It waits on Ramon registering v63 and posting a GO naming the revision, so I have nothing to run yet. When that GO arrives I will check the latest active revision and DDP_CORE_COMMIT (b5728c43), run check-core-pin-drift.py (expect exit 0 on EC2), and do one Oregon run only on the GO's word. Note: this host's role cannot read ECS task definitions, so I read the revision from a running task, not from the task-definition list.
