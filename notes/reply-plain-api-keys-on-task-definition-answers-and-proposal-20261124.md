# REPLY to `79ac0c9` (Ramon's question): why `VA_API_KEY` and `CONGRESS_GOV_API_KEY` are plain values on the task definition. Answers, and a proposal for Ramon. Nothing for you to do. 2026-11-24 ~23:45 UTC (Mac side, Onboard New States)

**Not a GO.** I changed nothing and found no value to repeat.

## The three answers
1. **Who set them first: I don't know, and no repo step does it.** I found nothing in the deploy script, `cloud_collector.py`, `cloud_loader.py` or `cloud_archiver.py` that sets either name; the only mentions are docs (OPEN-126, 08-22: Virginia's key "in `.env`", Secrets Manager was not on the scrape path then). They were almost certainly on an early hand-registered revision of `ddp-scrapers`, and `deploy-scrapers-image.sh` copies every entry forward, as you read. **How they reached `ddp-scrapers-db`:** its first revision was a console copy of `ddp-scrapers:74` (OPEN-639 comment, 11-19), so it inherited both.
2. **Are both needed on the db family: no.** Only scraper code reads them: `scrapers/va/bills.py` (Virginia's bill scrape) and `scrapers/usa/events.py` (the federal events scrape). Nothing in openstates-core, the loader or the archiver reads either. So `ddp-scrapers-db` (load and archive) should carry **neither**. The collection family `ddp-scrapers` does need them for the Virginia and US scrapes.
3. **Older revisions: I can't list them either** (no ECS access from an agent session). Treat every earlier ACTIVE revision of both families as holding both values. Deregistering a revision does not erase its contents, so **rotating the two keys is the only real fix**, and it is Ramon's call.

## Proposal (a small ticket, not built, not filed)
* **Drop both from `ddp-scrapers-db`:** a new variable in `deploy-scrapers-image.sh` that removes named entries from the db family only. Safe, because nothing in a load or archive task reads them.
* **Move both on `ddp-scrapers` into `secrets`:** each key stored in Secrets Manager, a `secrets` entry with `valueFrom` set by a `TASK_*` variable, the plain entries dropped. That needs **two new secrets and a permission for the collection family's execution role** (the old `ddp-scraper-ecs-execution-role`; a production change for Ramon), and the same discipline the RDS login got in OPEN-639: no collection task ever holds the database login.
* **Rotation** of the two keys goes with it.
* **Timing:** I would **not delay step 2** (the v91 release in `9ad05ee`) for this. Step 2 copies both entries forward unchanged; the cleanup is the next release.
* I will file it (OPEN-633's neighbour: scraper task secrets) and hand it to a builder on Ramon's word.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
