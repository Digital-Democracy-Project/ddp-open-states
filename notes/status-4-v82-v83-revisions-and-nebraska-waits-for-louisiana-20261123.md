# STATUS 4 (2026-11-23 17:26 UTC): your v82/v83 notes read; revisions observed; Nebraska waits for Louisiana

- **Read:** `14c6c24`, `98d2c18`, `ee5f997`, `96b9b91`, `caddf6b`, `a5531512` (UPDATE 4: v83), `a2bd7eba` and ddp-sync `0f2e655`. Nothing is unanswered.
- **Your request "confirm the newest registered revision is 84" (`96b9b91`):** from ECS I can only see revisions of tasks I launch. New runs since 16:49 UTC show **ddp-scrapers:84**: Louisiana `la-90b6159abadb`, Montana `mt-9bbf779af061`, Iowa `ia-a4202f577129`, Maryland `md-9b5b1f118106` (the other eight runs have no task yet, see `15598baa`/`fdaa1f21`). I cannot read task definitions or image tags, so rev **85** (v83) I will only see on Nebraska's task after I launch it.
- **Nebraska 109 part B (v83 = rev 85, `a2bd7eba`):** Ramon's overnight pre-approval covers it. Your `df508b7` says **one heavy load at a time**, so it **starts after Louisiana's re-import loads** (Louisiana `la-90b6159abadb` is still collecting). I will then trigger `POST openstates-scrape/ne?full=true&sessions=109`, check the task shows rev 85 or later, take the Part C counts and report.
- **My unverified guess on the eight pipelines with no task yet** (hi, me, ms, mo, nm, id, ri, ok): ddp-sync appears to launch from about 8 worker threads. Nothing re-triggered.
- **Not started:** recompute commits (KY, OK), anything not in Ramon's list.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
