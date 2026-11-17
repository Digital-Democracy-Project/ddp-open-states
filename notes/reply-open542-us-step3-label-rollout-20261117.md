# Reply to 1fc0d674: step 3 (US label rollout) done at 02:32 UTC, with two gates overridden on the user's word

Written 02:33 UTC (date -u at write time). From the production EC2 host.

## What ran
`deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync --state us`, exit 0 at 02:32:40 UTC, about one second.
- Gates overridden on the user's explicit word ("if we orphan the WA run, i'll accept that responsibility"): the cloud-task gate with `--skip-ecs-check`, and the time gate with `ROLLOUT_NOW_UTC=02:45`. At 02:32 the Washington run `wa-4af1a468d4b1` (task 8922f1b1cc27..., ddp-scrapers:65) was RUNNING. Without the overrides the script refused (10-minute rule around 02:30).
- The script never touches ddp-sync, the broker or any .env and restarts nothing here, so the WA run was not touched. I had wrongly told the user earlier that it recreates ddp-sync.
- The pull took the checkout from e38af9c3 to 8afea0a1 (43 commits, 23 files), which is more than the label: va `qa_sweep` true (#384), ma `votes_scraper` false (OPEN-592), and ga, nv, or at status `scraping` (#395/#396). The user chose "Roll out all of it" before the run.

## Gate results
- 16 jurisdictions valid; combined drift check: every list agrees (16). openstates-core was not compared against the code (no root given).
- md5 23c165c4fdbb48667844369b54f514db equal in the checkout, api-v3's copy, the api container and the ddp-sync container. api container healthy, directory mount, no recreate.
- `/ddp/enrollment` read from the broker at 02:33 UTC: 16 jurisdictions, `newest_first` true for none (us is now false). `voatz` keys 0.
- List now: live az fl ma mi nc us ut va wa; scraping al ga la ne nv or pa.

## Not done / open
- Whether ddp-sync needs a restart to schedule ga, nv, or: not checked (its log showed no manifest line in the 3 minutes after). I will not restart it under a running scrape; I will look after the WA and US runs end.
- The broker's own re-read of the list (about 1 hour cache): report owed.
- Step 5 (03:00 US run on revision 65): WA's revision read already shows 65 live. US report follows.
- Virginia OPEN-593 and step 7 (ga/nv/or) are NOT started; both need the user's separate go, which I will ask for after the 03:00 US run.
