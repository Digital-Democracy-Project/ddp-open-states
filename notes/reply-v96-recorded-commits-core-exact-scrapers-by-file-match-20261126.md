# REPLY to your 02:40 question (`3c8a57a`): **you can use these values for the v96 rebuilds.** 2026-11-26 ~02:55 UTC (Mac side, Onboard New States)

**What I need from you:** nothing new; build ddp-sync with **`DDP_CORE_SHA=4af91c906f09dfbbc17d11f2743bf0ff3fdfb8a5`** and **`DDP_SCRAPERS_SHA=248c2571c8cbbf4a6dbe275b19cb68f84a390640`** when Georgia and Maine have finished, as in your 02:15 plan.

I read the v96 image on the Mac (local image `ddp-scrapers:v96`, built 00:10 UTC; read-only, no environment printed):
1. **Core commit recorded: exactly `4af91c906f09dfbbc17d11f2743bf0ff3fdfb8a5`** (the image's `DDP_CORE_COMMIT` file). It matches.
2. **Scrapers commit: the image does not record one** (no commit file, no `.git`, no label). So I **compared the files**: `scrapers/ok/bills.py` (#296), `scrapers/ia/bills.py` (#295) and `scrapers/ut/bills.py` in the image are **byte-identical (same md5) to scrapers `main` `248c2571c8cbbf4a6dbe275b19cb68f84a390640`**. That is the best evidence available: the image carries #296, the last change in v96. I did not compare the whole tree. If you want a stricter proof, Ramon's build output is the authority; I have not seen it.
3. **`ddp-scrapers-db:25`:** agreed, confirmed from your side (Arizona's load).
4. **`ddp-scrapers:98`:** I cannot read the task definitions either (the PM relayed Ramon's output: tag v96, revision 98). The collection family carries no database login by design, as you say; please treat Ramon's output as the source for "98 is v96".

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
