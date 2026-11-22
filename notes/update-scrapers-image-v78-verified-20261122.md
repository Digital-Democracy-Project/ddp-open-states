# UPDATE to `77bda86` and `0c7ed8f`: image v78 is built and checked. It holds scrapers main `f0ac9ef8` exactly (#214–#218, on top of v77's #208–#213), at core `7f531958`. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO** for any run. This only reports what is in the image.

## What was checked (read only, on the Mac)
* **The image:** `ddp-scrapers:v78`, digest `sha256:b040ffc448f7…`, built 2026-11-22 19:55 UTC (Ramon).
* **Task definitions `ddp-scrapers:80` and `ddp-scrapers-db:7`** both name `ddp-scrapers:v78`.
* **Core** inside the image is `7f5319583f9d30684ef3f042ea308554f1cc0676`, unchanged.
* **Scrapers:** the image's whole `/opt/openstates-scrapers/scrapers` tree was compared file by file with `git archive f0ac9ef8 scrapers`: **0 differences**. So it holds:
  * OK by filing year #214;
  * RI 2021 #215;
  * KY/MT/IA vote keys #216;
  * NE "*" names #217;
  * MS 20093E #218;
  * everything in v77.
* **Not in it:**
  * OPEN-765, North Carolina's 2025 end date (scrapers #219, open);
  * BROKER-579, the PA/NE/LA veto overrides (being built).
* The build's own check passed: the Utah one-bill run exited 0 (PM session).

## What this frees (each still on Ramon's go)
* **Kentucky's first scrape** (ddp-sync `30ae9df`): the vote-key fix it waited for (#216) is here.
* **First scrapes of Oklahoma, Rhode Island, Idaho and Wyoming:** the image they waited on is here. They are requested by Onboard New States.
* **Nebraska "*" names (OPEN-761):** the code is live with v78. The stored session-109 votes change only after an NE 109 rescrape or re-import, on Ramon's go.
* **Confirm each run uses revision 80 or later.**

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
