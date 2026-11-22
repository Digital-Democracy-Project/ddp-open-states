# UPDATE to `abe29b8` (the next scrapers image after v75): it now also carries OPEN-646 (Virginia) and OPEN-749 (Montana). Scrapers main is `fd234747`. 2026-11-21 (Mac side, State Specific Handling)

**Not a GO.** Everything in `d4fa3f5` and `abe29b8` stands: AL #195, MA #197 (watch the first full MA run, about +5 h), IA #196 and #198, Maine #199 (its broker half #801 is a separate `/broker-deploy`). Core is unchanged at `7f531958`.

## Added since `abe29b8` (scrapers main now `fd2347473476089663ced147fbe3d76455d6d5dc`)
| Merge | What |
|---|---|
| #200 (OPEN-749, `84bbbac2`, from Onboard New States) | Montana's November 2017 special session (`2017s1`). Montana is probing and not scheduled; that session gets one named scrape afterwards, on Ramon's go, requested by Onboard New States |
| #204 (OPEN-646, `fd234747`) | **Virginia stores the links its bill summaries state:** "identical to" as a companion (Ramon, "Yes, same rule"); "incorporates", "was incorporated into" and "identical to relevant provisions of" as related; Virginia's words as the label |

## Virginia after registering
* **Scorecard gate approved?** The list is on OPEN-646 (comment 22380). On a dev copy it found **0 scorecard changes**, plus one new broker companion link (SB 749 → HB 217, polled) that moves no score.
* **The re-import of Virginia 2026** (the only session with polled bills) gets its own request, after the image.
* **Expected go/no-go after it:** about 552 companion links on 548 bills, and 89 related, on the replica and through api-v3.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
