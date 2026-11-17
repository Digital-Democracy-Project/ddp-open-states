# Reply to 125dc8505 (read only): v63 core drift check passes on EC2; revision 66 first runs follow

Written 16:07 UTC (date -u at write time). From the production EC2 host. Read only; nothing changed.

- **Step 2, drift check (16:07:39 UTC):** `check-core-pin-drift.py --image-core b5728c4326fea4bdc33b721738ecdbe5ac4d8b02 --container ddp-openstates-api-1` **exit 0**: image b5728c4326fea4bdc33b721738ecdbe5ac4d8b02 and the one api-v3 container on this host both run b5728c4326fea4bdc33b721738ecdbe5ac4d8b02, "OK: the scrapers image and 1 api-v3 container(s) all run core b5728c43...". The accepted gap from be6f951 is closed on EC2. I cannot read the Mac's api-v3 from this host.
- **Step 1 (revision 66 on the next launched task) and step 3 (each state's first run on revision 66):** not yet. At 16:07 UTC no scraper task is running on the cluster and none has started since 66 was registered. This host's role cannot read ECS task definitions, so I will read the revision from a running task's task definition. The next scheduled launches are WA 02:30, USA 03:00 and PA 04:00 UTC on 11-18; I will report each one's revision, status and failed count, and whether Massachusetts's next run is still a full run.
- The extra Oregon run is not authorized yet; I will not start one without Ramon's separate go.
